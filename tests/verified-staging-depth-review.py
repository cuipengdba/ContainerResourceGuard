#!/usr/bin/env python3
"""Offline review of archived verified-staging CI receipts; never executes a package."""
from pathlib import Path,PurePosixPath
import argparse,base64,collections,gzip,hashlib,io,json,tempfile,zipfile
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--evidence',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);a=p.parse_args()
sha=lambda raw:hashlib.sha256(raw).hexdigest()
planraw=a.plan.read_bytes();assert sha(planraw)=='e416793d10490cb3f9c707340b49dfe716f1f47aa807754896ba6395d3abe5b1'
expected=json.loads(planraw)
assert a.evidence.stat().st_size<=4*1024**2
with gzip.open(a.evidence,'rb') as stream:raw=stream.read(16*1024**2+1)
assert len(raw)<=16*1024**2
e=json.loads(raw);assert e['schema']=='crg-exact-verified-staging-depth-artifacts-v1' and len(e['artifacts'])==2
runs={int(r['id']):r for r in e['runs']};assert len(runs)==2
for r in runs.values():
 assert r['status']=='completed' and r['conclusion']=='success' and r['run_attempt']==1
 assert r['head_sha']=='68a604af517869d03975301bceca73f8887a623e' and r['path']=='.github/workflows/verified-staging.yml' and r['event']=='workflow_dispatch'
rows=[]
with tempfile.TemporaryDirectory(prefix='crg-evidence-review-') as temporary:
 folder=Path(temporary)
 for entry in e['artifacts']:
  d=entry['download'];assert d['run_id'] in runs and d['artifact']['workflow_run']['id']==d['run_id']
  raw=base64.b64decode(entry['ZIP_base64'],validate=True);assert len(raw)<=4*1024**2 and d['artifact']['digest']=='sha256:'+sha(raw)
  dest=folder/str(d['artifact']['id']);dest.mkdir();(dest/'download.json').write_bytes((json.dumps(d)+'\n').encode());(dest/'artifact.zip').write_bytes(raw)
  root=dest/'files';root.mkdir()
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   infos=z.infolist();assert len(infos)==len({i.filename for i in infos})<=200 and sum(i.file_size for i in infos)<=16*1024**2
   for i in infos:
    n=PurePosixPath(i.filename);assert not n.is_absolute() and '..' not in n.parts and '\\' not in i.filename
    if i.is_dir():continue
    assert i.file_size<=2*1024**2
    path=root/i.filename;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(i))
 for dest in sorted(folder.iterdir()):
  if not dest.is_dir():continue
  d=json.loads((dest/'download.json').read_bytes());f=dest/'files';assert d['full_zip_digest_verified'] and d['artifact']['digest']=='sha256:'+sha((dest/'artifact.zip').read_bytes())
  assert all(sha((f/n).read_bytes())==v['sha256'] and (f/n).stat().st_size==v['bytes'] for n,v in d['members'].items())
  p=json.loads((f/'plan.json').read_bytes());r=json.loads((f/'results/report.json').read_bytes());e=json.loads((f/'environment.json').read_bytes())
  assert p==expected and r['plan_sha256']==sha((f/'plan.json').read_bytes())
  for n,key in [('stage-release.py','scripts/stage-release.py'),('verify-release.py','scripts/verify-release.py'),('verified-staging-v1.py','tests/verified-staging-v1.py')]:assert sha((f/n).read_bytes())==p['inputs'][key]
  assert r['driver_sha256']==p['inputs']['tests/verified-staging-v1.py']
  env=next(v for v in p['environments'] if v['runner']==e['runner']);arch=env['arch'];a=p['artifacts'][arch]
  assert r['arch']==e['arch']==arch and r['kernel']==e['kernel'] and r['kernel'].startswith(env['kernel_prefix'])
  assert e['source50_verified'] and int(e['run_id'])==d['run_id'] and int(e['attempt'])==1 and e['workflow_revision']==runs[d['run_id']]['head_sha'] and e['source_revision']==p['source_revision']
  assert r['phase']=='passed' and len(r['tests'])==75 and all(v['passed'] for v in r['tests'])
  assert not r['cleanup']['errors'] and len(r['staging'])==26
  counts=collections.Counter(v['name'] for v in r['staging']);assert all(v==1 for v in counts.values())
  for c in r['staging']:
   value=c['result'];assert not value['package_code_executed'] and not value['installed_agent_replaced'] and not value['cgroups_changed']
   if c['name'] in ['valid-candidate','restrictive-umask','valid-previous']:
    assert c['exit']==0 and value['state']=='staged' and value['published']
    h=a['previous_binary_sha256'] if c['name']=='valid-previous' else a['candidate_binary_sha256'];assert c['after']['crg_sha256']==value['binary_sha256']==h
   elif c['name'] in ['source-path-replaced','destination-created']:
    b=c['barrier'];assert b['temporary_still_present'] and b['named_delayed_fsync_trace'] and b['before_monotonic_ns']<b['after_monotonic_ns']
    trace=(f/'results'/(c['name']+'.strace')).read_text();assert any(b['temporary_name'] in line and b['first_file'] in line and 'fsync(' in line and 'DELAYED' in line for line in trace.splitlines())
    if c['name']=='source-path-replaced':assert c['exit']==0 and value['state']=='staged' and c['input_sha256_after']!=a['candidate_sha256'] and c['destination_after']['crg_sha256']==a['candidate_binary_sha256']
    else:assert c['exit']!=0 and value['state']=='rejected' and not value['published'] and c['destination_after']==b['destination_before_stager_publish']
   else:assert c['exit']!=0 and value['state']=='rejected' and not value['published'] and not value.get('cleanup_error') and c['before']==c['after']
  n=r['native'];m=r['maintenance'];orig=n['original_controls'];limited={**orig,'cpu.max':'50000 100000'}
  assert len(orig)==8 and n['main']['pid']>1 and all(v['controls'] in [orig,limited] for v in m)
  installs=[v for v in m if v['operation'][1]=='binary-install'];assert len(installs)==2 and installs[0]['exit']!=0 and installs[1]['exit']==0 and installs[1]['result']['state']=='installed'
  assert installs[1]['result']['candidate_sha256']==a['candidate_binary_sha256'] and installs[1]['result']['previous_sha256']==a['previous_binary_sha256']
  rollback=next(v for v in m if v['operation'][1]=='binary-rollback');assert rollback['exit']==0 and rollback['result']['state']=='rolled_back' and rollback['controls']==limited
  assert m[-1]['operation'][1]=='disable' and m[-1]['exit']==0 and m[-1]['controls']==orig
  ack=n['worker_acks'];assert len(ack)==3 and not any(v['fsync_failed'] for v in ack) and ack[1]['fsync_count']>ack[0]['fsync_count']
  oom=next(v for v in r['tests'] if v['name']=='native: observed cgroup OOM counters unchanged');assert all(oom['before'][k]==oom['after'][k] for k in ['oom','oom_kill','oom_group_kill'] if k in oom['after'])
  cleanup=next(v for v in r['tests'] if v['name']=='cleanup: exact container cgroup and observed processes gone');assert cleanup['container_absent'] and cleanup['cgroup_absent'] and cleanup['all_observed_dead']
  observed=cleanup['observed'];assert n['main'] in observed
  writers=[v for v in observed if v.get('sha256')];assert len(writers)==3 and [v['sha256'] for v in writers]==[a['previous_binary_sha256'],a['candidate_binary_sha256'],a['previous_binary_sha256']]
  depth=json.loads((f/'depth/depth-report.json').read_bytes())
  assert depth['phase']=='passed' and depth['owned_root_removed'] and depth['root_empty_before_cleanup']
  assert depth['arch']==arch and depth['kernel']==r['kernel'] and depth['python']==r['python']
  assert depth['plan_sha256']==r['plan_sha256'] and depth['candidate_sha256']==a['candidate_sha256']
  assert depth['baseline_sha256']==p['depth_regression']['baseline_sha256'] and depth['stager_sha256']==p['inputs']['scripts/stage-release.py']
  assert sha((f/'verified-staging-depth-v1.py').read_bytes())==p['inputs']['tests/verified-staging-depth-v1.py']
  assert not depth['package_code_executed'] and not depth['cgroups_changed']
  cases=depth['cases'];assert [v['name'] for v in cases]==['old-1100-directory','boundary-64-directory','boundary-64-file','reject-65-directory','reject-65-file','reject-1100-directory-late','reject-1100-directory-first']
  for c in cases:
   assert c['passed'] and c['owned_cleanup_verified']
   assert sha((f/'depth'/(c['name']+'.stderr')).read_bytes())==c['stderr_sha256']
   out=(f/'depth'/(c['name']+'.stdout')).read_bytes()
   if c['name'].startswith('old-'):
    assert c['depth']==1100 and c['exit']!=0 and not c['destination_present'] and c['private_residue_directories']==1 and c['private_residue_entries']>=1000
    assert c['unhandled_recursion_error'] and b'RecursionError' in (f/'depth'/(c['name']+'.stderr')).read_bytes() and c['result'] is None and not out.strip()
   else:
    assert json.loads(out)==c['result'] and not c['unhandled_recursion_error'] and not c['private_residue_directories']
    if c['name'].startswith('boundary-'):
     assert c['depth']==64 and c['exit']==0 and c['destination_present'] and c['result']['state']=='staged' and c['result']['binary_sha256']==a['candidate_binary_sha256']
    else:
     assert c['exit']!=0 and c['result']['state']=='rejected' and not c['destination_present'] and c['result']['private_files_written']==0 and not c['result']['published'] and not c['result'].get('cleanup_error')
     assert 'depth exceeds64' in c['result']['error']
  rows.append({'run_id':d['run_id'],'artifact_id':d['artifact']['id'],'ZIP_sha256':sha((dest/'artifact.zip').read_bytes()),'runner':e['runner'],'arch':arch,'kernel':r['kernel'],'python':r['python'],'checks':75,'staging_cases':26,'native_upgrade_and_rollback':True,'observed_cleanup_verified':True})
assert len(rows)==2 and {v['runner'] for v in rows}=={v['runner'] for v in expected['environments']}
print(json.dumps({'schema':'crg-offline-verified-staging-depth-review-v1','scope':expected['scope'],'plan_sha256':sha(planraw),'environments':rows,'total_checks':150,'depth_regression_cases':12,'old_defect_reproductions':2,'staging_cases':52,'full_original_task_closed':False,'stable_release_accepted':False},indent=2))
