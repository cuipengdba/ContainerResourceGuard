#!/usr/bin/env python3
"""Offline review of exact native persistence receipts; never executes candidate."""
from pathlib import Path,PurePosixPath
import argparse,base64,gzip,hashlib,io,json,re,tempfile,zipfile
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--evidence',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);a=p.parse_args()
sha=lambda raw:hashlib.sha256(raw).hexdigest()
planraw=a.plan.read_bytes();assert sha(planraw)=='a49f0c8ae814fe134495f7988d2b65fc3deb170909eb9657fffa5f38aa29043e'
expected=json.loads(planraw)
assert a.evidence.stat().st_size<=4*1024**2
with gzip.open(a.evidence,'rb') as f:raw=f.read(16*1024**2+1)
assert len(raw)<=16*1024**2
e=json.loads(raw);assert e['schema']=='crg-exact-native-persistence-artifacts-v1' and len(e['artifacts'])==2
runs={int(r['id']):r for r in e['runs']};assert len(runs)==2
for r in runs.values():
 assert r['status']=='completed' and r['conclusion']=='success' and r['run_attempt']==1
 assert r['head_sha']=='611efbbb0598960bc6b482416033fdee31bf2260' and r['path']=='.github/workflows/persistence-faults.yml' and r['event']=='workflow_dispatch'
rows=[]
with tempfile.TemporaryDirectory(prefix='crg-persistence-review-') as temporary:
 folder=Path(temporary)
 for entry in e['artifacts']:
  d=entry['download'];assert d['run_id'] in runs and d['artifact']['workflow_run']['id']==d['run_id']
  raw=base64.b64decode(entry['ZIP_base64'],validate=True);assert len(raw)<=4*1024**2 and d['artifact']['digest']=='sha256:'+sha(raw)
  dest=folder/str(d['artifact']['id']);dest.mkdir();(dest/'download.json').write_bytes((json.dumps(d)+'\n').encode());(dest/'artifact.zip').write_bytes(raw)
  root=dest/'files';root.mkdir()
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   infos=z.infolist();assert len(infos)==len({i.filename for i in infos})<=200 and sum(i.file_size for i in infos)<=16*1024**2
   for i in infos:
    n=PurePosixPath(i.filename);assert not n.is_absolute() and '..' not in n.parts and not re.search(r'(^[A-Za-z]:|\\)',i.filename)
    assert n.as_posix()==i.filename.rstrip('/') and len(n.parts)<=64
    if i.is_dir():continue
    assert i.file_size<=2*1024**2
    path=root/i.filename;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(i))
 for dest in sorted(folder.iterdir()):
  if not dest.is_dir():continue
  d=json.loads((dest/'download.json').read_bytes());f=dest/'files'
  assert d['full_zip_digest_verified'] and d['artifact']['digest']=='sha256:'+sha((dest/'artifact.zip').read_bytes())
  assert all(sha((f/n).read_bytes())==v['sha256'] and (f/n).stat().st_size==v['bytes'] for n,v in d['members'].items())
  p=json.loads((f/'plan.json').read_bytes());r=json.loads((f/'results/report.json').read_bytes());e=json.loads((f/'environment.json').read_bytes())
  assert p==expected and r['plan_sha256']==sha((f/'plan.json').read_bytes())
  for n,key in [('driver.py','tests/persistence-faults-v1/driver.py'),('helper.go','tests/persistence-faults-v1/helper.go'),('workload.go','tests/legacy-restore-pressure-v1/workload.go')]:assert sha((f/n).read_bytes())==p['test_inputs_sha256'][key]
  assert r['driver_sha256']==p['test_inputs_sha256']['tests/persistence-faults-v1/driver.py']
  env=next(v for v in p['environments'] if v['runner']==e['runner']);arch=env['arch']
  assert r['arch']==arch and r['kernel']==e['kernel'] and r['kernel'].startswith(env['kernel_prefix'])
  assert e['machine'] in {'amd64':['x86_64'],'arm64':['aarch64','arm64']}[arch]
  assert e['source50_verified'] and int(e['run_id'])==d['run_id'] and int(e['attempt'])==1 and e['workflow_revision']==runs[d['run_id']]['head_sha']
  assert r['binary_sha256']==p['binary_sha256'][arch] and r['source_revision']==p['source_revision']
  assert r['phase']=='passed' and len(r['tests'])==60 and all(v['passed'] for v in r['tests'])
  assert not r['cleanup']['errors'] and r['cleanup']['owned_state_mounts_remaining']==0
  assert [c['name'] for c in r['cases']]==p['cases']
  observed=[]
  for c in r['cases']:
   name=c['name'];orig=c['original_controls'];limited={**orig,'cpu.max':'50000 100000'}
   assert len(orig)==8 and c['state_mount']['filesystem']=='tmpfs' and c['main']['pid']>1
   assert c['candidate_capabilities'] and all(not (int(v['effective'],16)&6) and not (int(v['bounding'],16)&6) and v['executable_sha256']==r['binary_sha256'] for v in c['candidate_capabilities'])
   initial=c['initial_journal']['mutations']['cpu.max:'];assert initial['original']==orig['cpu.max'] and initial['applied']=='50000 100000'
   final=c['restore'];assert final['exit']==0 and final['result']['state']=='restored' and final['controls']==orig and not final['journal']['mutations']
   actual=json.loads((f/'results'/name/'journal.json').read_bytes());assert actual==final['journal']
   clean=c['cleanup'];assert clean['container_absent'] and clean['cgroup_absent'] and clean['all_observed_dead']
   assert c['main'] in clean['observed_identities'];observed+=clean['observed_identities']
   commands={v['label']:v for v in c['commands']};assert len(commands)==len(c['commands'])
   texts={}
   for label,row in commands.items():
    out=(f/'results'/name/(label+'.stdout')).read_text();err=(f/'results'/name/(label+'.stderr')).read_text()
    assert sha((out+err).encode())==row['output_sha256'];texts[label]=out+err
   ack=c['worker_acks'];assert all(not a['fsync_failed'] for a in ack) and ack[-1]['command']=='quit' and ack[-2]['fsync_count']>ack[0]['fsync_count']
   oom=next(v for v in r['tests'] if v['name']==name+': observed OOM counters unchanged');assert all(oom['before'][k]==oom['after'][k] for k in ['oom','oom_kill','oom_group_kill'] if k in oom['after'])
   if name in ['full-state','permission-state','readonly-state']:
    assert c['fault_seconds']>=30 and len(c['samples'])>=20
    journal_hashes={v['journal_sha256'] for v in c['samples']};assert len(journal_hashes)==1
    assert all(v['controls']==limited and v['main_alive'] for v in c['samples'])
    assert max(v['elapsed_seconds'] for v in c['samples'])>=30
    reason={'full-state':'no space left on device','permission-state':'permission denied','readonly-state':'read-only file system'}[name]
    for label in ['baseline','retry-0','retry-1','retry-2']:assert commands[label]['exit']!=0 and reason in texts[label].lower()
    assert commands['recovered']['exit']==0
    if name=='readonly-state':assert c['readonly_overlay']['statvfs_readonly'] and len(c['readonly_overlay']['new_mount_rows'])==1 and 'ro' in c['readonly_overlay']['new_mount_rows'][0][5].split(',')
    if name=='full-state':assert c['fill']['errno']==28 and c['fill']['free_blocks']==0 and 0<c['fill']['bytes']<=4194304
   else:
    trace=(f/'results'/name/'persistence.strace').read_text();assert sha(trace.encode())==c['trace_sha256']
    assert any('fsync(' in line and 'DELAYED' in line and '/state' in line for line in trace.splitlines())
    cpu_writes=[line for line in trace.splitlines() if 'write(' in line and '/cpu.max>' in line and '75000 100000' in line]
    if name=='delayed-complete':assert commands['baseline']['exit']==0 and cpu_writes
    else:
     boundary=c['kill_boundary'];pending=boundary['journal']['mutations']['cpu.max:'];assert pending['pending']=='75000 100000'
     assert boundary['signal_monotonic_ns']>boundary['before_monotonic_ns'] and commands['baseline']['exit']!=0 and 'killed by SIGKILL' in trace
     desired='75000 100000' if name=='delayed-after-control' else '50000 100000'
     assert boundary['controls']=={**orig,'cpu.max':desired}
     assert bool(cpu_writes)==(name=='delayed-after-control')
  assert len({(v['pid'],v['start_ticks']) for v in observed})==len(observed)
  rows.append({'run_id':d['run_id'],'artifact_id':d['artifact']['id'],'ZIP_sha256':sha((dest/'artifact.zip').read_bytes()),'runner':e['runner'],'arch':arch,'kernel':r['kernel'],'checks':60,'cases':6,'sustained_real_filesystem_faults':3,'exact_SIGKILL_boundaries':2,'delayed_complete':1,'all_original8_restored':True,'own_cleanup_verified':True})
assert len(rows)==2 and {v['runner'] for v in rows}=={v['runner'] for v in expected['environments']}
print(json.dumps({'schema':'crg-offline-native-persistence-review-v1','scope':expected['scope'],'plan_sha256':sha(planraw),'environments':rows,'total_checks':120,'cases':12,'full_original_P09_3_closed':False,'physical_power_loss_tested':False,'hidden_uncommitted_state_originals_preserved':False,'stable_release_accepted':False},indent=2))
