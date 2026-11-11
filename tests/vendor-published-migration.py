#!/usr/bin/env python3
"""Actual published old/current migration on disposable DBS/HISDBS paths.

Default is read-only. Manual replacement follows matching-old disable, verified
runtime restoration and private backup. It does not bypass binary-install's
protocol check or claim constant quotas during explicit restore operations.
"""
import argparse,hashlib,json,os,pathlib,signal,subprocess,sys
sys.dont_write_bytecode=True
FROZEN_PLAN = {'schema': 'crg-published-migration-plan-v1', 'work_root': '/var/tmp/crg-published-migration392-20261111', 'tool_root': '/var/tmp/crg-published-migration393-tools-20261111', 'namespace': 'crg-vendor-lab-published-migration392-20261111', 'run_id': '20261111392', 'programs': {'previous': {'release': 'v0.1.0-rc.3-preview.1', 'asset_id': 730823163, 'asset_name': 'containerresourceguard-v0.1.0-rc.3-preview.1-linux-amd64.tar.gz', 'archive_sha256': '65ad8e81d85249e7d4f96d216eaed8cc09b6e03b41d3b65342da9d62b6c9c45f', 'archive_bytes': 1708379, 'binary_sha256': 'f07973272313db26d359797dda4665145f7dd6490bac2a55f9084bd367faf361', 'binary_bytes': 3600544, 'binary_member': 'crg', 'optional_helper_sha256': 'f7e7208f58bac7066d75d49cb17199b720e3d05bb5953e2a7a7800f881b54b79'}, 'candidate': {'release': 'v1.0.0-preview.2', 'asset_id': 734233184, 'asset_name': 'containerresourceguard-v1.0.0-linux-amd64.tar.gz', 'archive_sha256': 'd6bdfc89d6699a92d70e46a7aa561ccc54ba581901aed382158eb2a24d72952f', 'archive_bytes': 2211930, 'binary_sha256': 'dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8', 'binary_bytes': 4022432, 'binary_member': 'crg', 'optional_helper_sha256': 'f7e7208f58bac7066d75d49cb17199b720e3d05bb5953e2a7a7800f881b54b79'}}, 'inputs_sha256': {'tests/vendor-soak-load.py': 'ba87ef2d646b723eb8419de25ffcd736f7a5b0925716f4b638761dff70bb2461', 'tests/vendor-soak-campaign.py': 'b49d5a73654c5cf7c93b04851f3409eea318b3a9c71c0e8f601f252a3dda07ea', 'tests/vendor-engine-smoke.py': 'b0d4fe313156743ff1424b46eb58c5ab5b8e1f2c91851420023f5f018dd08e5c', 'examples/optional-agent.sh': 'f7e7208f58bac7066d75d49cb17199b720e3d05bb5953e2a7a7800f881b54b79', 'identity-qualification.json': 'd293d2c400843b1a7765d38ef14aecd8c68333cfc29259b670e0bec8790ca77e', 'integration-qualification.json': '6c7500a860f5c1a633ca8f24ca1c8b3ada09b697bbbea0496bcb58183a45a634', 'overhead-qualification.json': '68f1c207bd7e8ba430163d2c8b0228339a707d81159369678b95a1db4230d720', 'business-qualification.json': 'f680f08aeeccb500c56655dfe5dbf07982e373928d70634fea400232e2090101', 'fault-qualification.json': 'b26dd6678137d9f25f5f21bd334b030805782bbb33441b68340c597df6b69ca5', 'binaries/previous': 'f07973272313db26d359797dda4665145f7dd6490bac2a55f9084bd367faf361', 'binaries/candidate': 'dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8'}, 'base_source_sha256': 'a5fdf31abc4e49472054b7d2e4d3e5999e36dcc7ed0a12500200411d1b80dec1', 'base_plan_sha256': '3e067d72321937e5fdcd4bfeeeca5f96b85e54fd3a019ec15a7acc128a7c5179', 'criteria': {'PG_API_managed_seconds': 300, 'cache_after_ready_seconds': 45, 'cache_also_within_startup_seconds': 300, 'native_seconds': 600, 'SQL_API_errors': 0, 'SQL_API_max_seconds': 5, 'p95_upper_bucket_seconds': 1, 'coverage_min': 0.98, 'all_operations_and_agent_resumes_fully_within_native600': True, 'final_disable_restores_true_runtime_originals': True, 'PID1_PG_cache_payload_and_original_ownership_preserved': True, 'other_five_controls_unchanged': True, 'three_active_controls_match_declared_disable_resume_phase': True}, 'budget': {'cpu_cores': 7.2, 'memory_max_bytes': 20001980416, 'read_write_bps': 67108864, 'read_write_iops': 4096}, 'expected_checks': 26, 'intentional_control_transitions': 'matching-old disable/restore returns to exact runtime originals before explicit replacement; each resumed Agent reapplies identical manual test budget; five unrelated controls unchanged', 'roles': ['dbs', 'hisdbs'], 'original_startup_cache_and_native600_SLA_unchanged': True, 'scope': 'actual two published asset versions, controlled disable/restore migration and rollback; not quiescent same-controls maintenance or two stable minor releases', 'original_quiescent_maintenance_criteria_waived': False, 'original32_percentage_and_all_historical_failures_retained': True, 'stable_release_accepted': False, 'derivation': [{'old': 'crg-realpaths71-20261111', 'new': 'crg-published-migration392-20261111', 'count': 1}, {'old': 'crg-r71-20261111', 'new': 'crg-published-migration393-tools-20261111', 'count': 1}, {'old': 'crg-vendor-lab-realpaths71-20261111', 'new': 'crg-vendor-lab-published-migration392-20261111', 'count': 1}, {'old': 'CRG_R71_MAINTENANCE', 'new': 'CRG_PUBLISHED_MIGRATION', 'count': 1}, {'old': '20261111071', 'new': '20261111392', 'count': 1}, {'old': '3f69370b2b0f04f447801212599d6f4596b280331ff83866a11260dc7fc8f8a9', 'new': 'f07973272313db26d359797dda4665145f7dd6490bac2a55f9084bd367faf361', 'count': 3}, {'old': '50671aa7c037679546d569846eccc5aacc5a34b7', 'new': '7638ee9f871287d1056e267034e0c4e46903b66e', 'count': 1}, {'old': 'unreleased protocol-advertising combined development build', 'new': 'published v0.1.0-rc.3-preview.1 exact official asset', 'count': 1}, {'old': 'unpublished exact v1.0.0 versioned candidate', 'new': 'published v1.0.0-preview.2 exact official asset', 'count': 1}, {'old': "  if info.get('revision')!=report['sources'][name]['revision'] or info.get('arch')!='amd64' or info.get('lock_protocol')!='cgroup-inode-flock+state-agent-lock-v1' or 1 not in info.get('journal_versions',[]):raise RuntimeError('source or maintenance protocol differs')", 'new': "  if info.get('revision')!=report['sources'][name]['revision'] or info.get('arch')!='amd64':raise RuntimeError('published source or architecture differs')\n  if name=='candidate' and (info.get('lock_protocol')!='cgroup-inode-flock+state-agent-lock-v1' or 1 not in info.get('journal_versions',[])):raise RuntimeError('candidate maintenance protocol differs')\n  if name=='previous' and ('lock_protocol' in info or 'journal_versions' in info):raise RuntimeError('old published protocol absence differs')", 'count': 1}, {'old': 'def run(a,check=True,timeout=60,**kw):', 'new': "report.update(schema='crg-published-migration-v1',plan_sha256=plan_sha256,published_programs=frozen_plan['programs'],\n scope='Actual published old/current controlled disable-restore migration and rollback, both original vendor paths; not quiescent same-limits install or two-minor stable acceptance')\ndef run(a,check=True,timeout=60,**kw):", 'count': 1}, {'kind': 'explicit block', 'old_sha256': '29aeb51142174fe2babb7a6fb6bac289f9861f26651de0c607a77c7fd80020ea', 'new_sha256': 'f5da78edeea8003a2f421e73cef5d3b53cabd7fd20fab3ef26c7ad53a6aeedf3', 'purpose': 'per-stage actual controls and original ownership; explicit bounded old/current commands and disabled writer checks; no status emulation'}, {'old': '     if found==[expected]:', 'new': "     if found==[expected] and all((cg/f).read_text()==v for f,v in expected_controls.items()) and not (folder/'resource-state/disabled.json').exists():", 'count': 1}, {'kind': 'explicit operation block', 'old_sha256': '6cdc194d835b4a8a1e7927267558cbd5a2e3314730021355949bef7a601789a1', 'new_sha256': 'e2cf1e6e1d0b6bf6e993219462ab5cb73a03a4359a75db4a1d7d5935629cb5f7', 'purpose': 'keep protocol refusal, then prescribed matching-old disable and controlled manual migration/rollback, not bypass installer'}, {'old': "   disabled=json.loads(cli('disable').stdout)", 'new': "   disabled=json.loads(cli_at('/opt/crg/crg','disable').stdout)", 'count': 1}, {'old': "except Exception as e:report.update(phase='failed',error=str(e),traceback=traceback.format_exc())", 'new': "except BaseException as e:report.update(phase='failed',error=str(e),traceback=traceback.format_exc())", 'count': 1}, {'old': "len(report['tests'])==22", 'new': "len(report['tests'])==26", 'count': 1}], 'unchanged_base_helpers_AST': ['run', 'create', 'ex', 'save', 'record', 'reserve', 'delete_pod'], 'original_quiescent_maintenance_reference_criteria': {'PG_API_managed_seconds': 300, 'cache_after_ready_seconds': 45, 'cache_also_within_startup_seconds': 300, 'native_seconds': 600, 'SQL_API_errors': 0, 'SQL_API_max_seconds': 5, 'p95_upper_bucket_seconds': 1, 'coverage_min': 0.98, 'all_operations_and_agent_resumes_fully_within_native600': True, 'PID1_PG_cache_payload_journal_originals_and_all_eight_controls_preserved_during_maintenance': True, 'final_disable_restores_true_runtime_originals': True}}

def run_migration(frozen_plan,plan_sha256):
 import pathlib,json,subprocess,time,traceback,hashlib,os,shutil,re,uuid,datetime
 root=pathlib.Path('/var/tmp/crg-published-migration392-20261111');source=pathlib.Path('/var/tmp/crg-business-20261110');candidates=pathlib.Path('/var/tmp/crg-published-migration393-tools-20261111');ns='crg-vendor-lab-published-migration392-20261111';created=False
 report={'resource_mode':'manual','declared_test_budget':{'cpu_cores':7.2,'memory_max_bytes':20001980416,'read_write_bps':67108864,'read_write_iops':4096},'phase':'waiting-for-automatic-calibration-checks','scope':'same container paths and read-only CCG mount as read-only deployment inventory; fresh private test-node backing directories and loopback DCS, no production data; original business/image/database parameters','roles':{},'tests':[]}
 report.update(schema='crg-published-migration-v1',plan_sha256=plan_sha256,published_programs=frozen_plan['programs'],
  scope='Actual published old/current controlled disable-restore migration and rollback, both original vendor paths; not quiescent same-limits install or two-minor stable acceptance')
 def run(a,check=True,timeout=60,**kw):
  r=subprocess.run(a,capture_output=True,text=True,timeout=timeout,**kw)
  if check and r.returncode:raise RuntimeError('test command failed, exit='+str(r.returncode))
  return r
 def create(o):
  r=subprocess.run(['kubectl','create','-f','-'],input=json.dumps(o),capture_output=True,text=True,timeout=30)
  if r.returncode:raise RuntimeError('fixture create failed')
 def ex(role,*a,**kw):return run(['kubectl','exec','-n',ns,role+'-business','-c',role,'--',*a],**kw)
 def save():(root/'report.json').write_text(json.dumps(report,indent=2))
 def record(name,passed,**extra):
  report['tests'].append(dict(name=name,passed=bool(passed),**extra));save()
  if not passed:raise AssertionError(name)
 def reserve(minimum=8):
  available=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
  if available<minimum*1024**3 or shutil.disk_usage(root).free<20*1024**3:raise RuntimeError('node reserve threshold reached')
  return available
 def delete_pod(role):
  m=json.loads(run(['kubectl','get','pod','-n',ns,role+'-business','-o','json']).stdout)
  if m['metadata']['labels'].get('managed-by')!='crg-vendor-test' or m['metadata']['namespace']!=ns:raise RuntimeError('cleanup ownership mismatch')
  run(['kubectl','delete','pod','-n',ns,role+'-business','--wait=true','--timeout=120s'],timeout=130)
 try:
  if os.geteuid()!=0 or os.uname().machine!='x86_64' or os.environ.get('CRG_PUBLISHED_MIGRATION')!='authorized-disposable-test-node-only':raise RuntimeError('explicit authorized native fixture required')
  expected={'tests/vendor-soak-load.py': 'ba87ef2d646b723eb8419de25ffcd736f7a5b0925716f4b638761dff70bb2461', 'tests/vendor-soak-campaign.py': 'b49d5a73654c5cf7c93b04851f3409eea318b3a9c71c0e8f601f252a3dda07ea', 'tests/vendor-engine-smoke.py': 'b0d4fe313156743ff1424b46eb58c5ab5b8e1f2c91851420023f5f018dd08e5c', 'examples/optional-agent.sh': 'f7e7208f58bac7066d75d49cb17199b720e3d05bb5953e2a7a7800f881b54b79', 'identity-qualification.json': 'd293d2c400843b1a7765d38ef14aecd8c68333cfc29259b670e0bec8790ca77e', 'integration-qualification.json': '6c7500a860f5c1a633ca8f24ca1c8b3ada09b697bbbea0496bcb58183a45a634', 'overhead-qualification.json': '68f1c207bd7e8ba430163d2c8b0228339a707d81159369678b95a1db4230d720', 'business-qualification.json': 'f680f08aeeccb500c56655dfe5dbf07982e373928d70634fea400232e2090101', 'fault-qualification.json': 'b26dd6678137d9f25f5f21bd334b030805782bbb33441b68340c597df6b69ca5', 'binaries/previous': 'f07973272313db26d359797dda4665145f7dd6490bac2a55f9084bd367faf361', 'binaries/candidate': 'dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8'}
  for name,digest in expected.items():
   if hashlib.sha256((candidates/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('frozen payload differs')
  for name,digest in {'fixture/containercacheguard': '757ba385a0ee4bdadc968b96b5c3e69fd44353060e5ab28520fd6f73a59902de', 'fixture/dbs/supervisor.sh': '4dce0b38e6c01a9effe08457dc31206a0abaf7ff14eb9ec59dace97a6f1c0211', 'fixture/hisdbs/supervisor.sh': '4dce0b38e6c01a9effe08457dc31206a0abaf7ff14eb9ec59dace97a6f1c0211'}.items():
   if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('original private helper/supervisor differs')
  identity=json.loads((candidates/'identity-qualification.json').read_text());ci=json.loads((candidates/'integration-qualification.json').read_text())
  if identity.get('phase')!='unpublished-versioned-candidate-built-and-local-package-checks-passed' or identity.get('version')!='v1.0.0' or identity.get('production_files_exactly_equal_to_d370')!=50 or ci.get('phase')!='passed' or ci.get('version')!='v1.0.0' or ci.get('controller_checks')!=88 or len(ci.get('CI',[]))!=4 or ci.get('all_eight_files_equal_Windows_each_cell') is not True or identity.get('source_revision')!='d3706f3ea7ad279fea818e5ad1aa62ac5d3f8710' or ci.get('source_revision')!='d3706f3ea7ad279fea818e5ad1aa62ac5d3f8710':raise RuntimeError('exact versioned artifact qualifications missing')
  if identity['file_sha256']['crg-linux-amd64']!=expected['binaries/candidate'] or identity['local_integrity_checks']['count']!=14 or not all(x['passed'] is True for x in identity['local_integrity_checks']['checks']) or identity['native_AMD64_build_identity_probe']['version_output']!='v1.0.0' or identity['native_AMD64_build_identity_probe']['binary_sha256']!=expected['binaries/candidate'] or identity['same_host_fresh_checkout_reproduction']['byte_equal'] is not True:raise RuntimeError('versioned package identity checks incomplete')
  for cell in ci['CI']:
   if cell['identity']['actual']['crg-linux-amd64']!=expected['binaries/candidate'] or cell['report']['phase']!='passed' or len(cell['report']['tests'])!=22 or not all(x['passed'] is True for x in cell['report']['tests']) or not all(x is True for x in cell['report']['cleanup'].values()):raise RuntimeError('versioned native cell incomplete')
  for name in ['overhead-qualification.json','business-qualification.json','fault-qualification.json']:
   value=json.loads((candidates/name).read_text())
   if value.get('phase')!='passed' or value.get('source_revision')!='d3706f3ea7ad279fea818e5ad1aa62ac5d3f8710' or value.get('binary_sha256')!=expected['binaries/candidate']:raise RuntimeError('own versioned runtime qualification differs')
  report['sources']={'previous': {'revision': '7638ee9f871287d1056e267034e0c4e46903b66e', 'binary_sha256': 'f07973272313db26d359797dda4665145f7dd6490bac2a55f9084bd367faf361', 'release_status': 'published v0.1.0-rc.3-preview.1 exact official asset'}, 'candidate': {'revision': 'd3706f3ea7ad279fea818e5ad1aa62ac5d3f8710', 'binary_sha256': 'dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8', 'release_status': 'published v1.0.0-preview.2 exact official asset'}};report['build_info']={};report['job_sha256']=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
  for name in ['previous','candidate']:
   info=json.loads(run([str(candidates/'binaries'/name),'build-info']).stdout)
   if info.get('revision')!=report['sources'][name]['revision'] or info.get('arch')!='amd64':raise RuntimeError('published source or architecture differs')
   if name=='candidate' and (info.get('lock_protocol')!='cgroup-inode-flock+state-agent-lock-v1' or 1 not in info.get('journal_versions',[])):raise RuntimeError('candidate maintenance protocol differs')
   if name=='previous' and ('lock_protocol' in info or 'journal_versions' in info):raise RuntimeError('old published protocol absence differs')
   if name=='candidate' and info.get('version')!='v1.0.0':raise RuntimeError('candidate version differs')
   report['build_info'][name]=info
  root.mkdir(mode=0o700,exist_ok=False);report['phase']='waiting-for-current-source-fault-acceptance-and-cleanup';save()
  deadline=time.monotonic()+5400
  while time.monotonic()<deadline:
   reserve();p=pathlib.Path('/var/tmp/crg-realpaths66-20261111/report.json');e=pathlib.Path('/var/tmp/crg-r66-20261111/faults.exit.json')
   if p.exists() and e.exists():
    d=json.loads(p.read_text());receipt=json.loads(e.read_text())
    if d.get('phase') in ['passed','failed']:
     if d.get('phase')!='passed' or d.get('namespace_absent') is not True or receipt.get('exit')!=0 or len(d.get('roles',{}))!=20 or len(d.get('tests',[]))!=108 or not all(x['passed'] for x in d['tests']) or d.get('sources',{}).get('v10',{}).get('revision')!='d3706f3ea7ad279fea818e5ad1aa62ac5d3f8710':raise RuntimeError('current faults not accepted; no maintenance Pod created')
     if d.get('job_sha256')!='f21f4b4bdb5e3f01316ad954b030d408310c6ac40b503fe9c620fca53461f289' or receipt.get('job_sha256')!=d['job_sha256'] or d.get('build_info',{}).get('version')!='v1.0.0' or d.get('sources',{}).get('v10',{}).get('binary_sha256')!=expected['binaries/candidate'] or len({x['name'] for x in d['tests']})!=108:raise RuntimeError('own exact versioned faults missing')
     business_path=pathlib.Path('/var/tmp/crg-realpaths64-20261111/report.json');business=json.loads(business_path.read_text());business_exit=json.loads(pathlib.Path('/var/tmp/crg-r64-20261111/business.exit.json').read_text())
     if business.get('job_sha256')!='4bb896692b38ddb6dd7c28a9e019c81b4727f2f0ebcd664ca2f2318331d2de77' or business_exit.get('job_sha256')!=business['job_sha256'] or business_exit.get('exit')!=0 or business.get('phase')!='passed' or len(business.get('tests',[]))!=12 or not all(x['passed'] is True for x in business['tests']) or d['business_prerequisite_report_sha256']!=hashlib.sha256(business_path.read_bytes()).hexdigest():raise RuntimeError('own versioned business chain differs')
     overhead_path=pathlib.Path('/var/tmp/crg-overhead-r63-20261111/report.json');overhead=json.loads(overhead_path.read_text());overhead_exit=json.loads(pathlib.Path('/var/tmp/crg-r63-20261111/overhead.exit.json').read_text())
     if overhead.get('job_sha256')!='e8937b2df8bff4bf6d2e2c7987c8de78cb2435e6d69539d3ebf9ebb5c7d12aa6' or overhead_exit.get('job_sha256')!=overhead['job_sha256'] or overhead_exit.get('exit')!=0 or overhead.get('phase')!='passed' or overhead.get('measurement_elapsed_seconds',0)<1800 or len(overhead.get('cases',{}))!=3 or not all(x['passed'] is True for x in overhead['cases'].values()) or not (d['overhead_prerequisite_report_sha256']==business['overhead_report_sha256']==hashlib.sha256(overhead_path.read_bytes()).hexdigest()):raise RuntimeError('own versioned overhead chain differs')
     overhead_namespace=run(['kubectl','get','namespace','crg-overhead-r63-20261111','--ignore-not-found','-o','json'],False)
     if overhead_namespace.returncode or overhead_namespace.stdout.strip():raise RuntimeError('own overhead namespace present')
     absent=run(['kubectl','get','namespace','crg-vendor-lab-realpaths66-20261111','--ignore-not-found','-o','json'],False)
     if absent.returncode or absent.stdout.strip():raise RuntimeError('fault namespace independently not absent')
     report['fault_prerequisite_report_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();break
   time.sleep(5)
  else:raise RuntimeError('current fault prerequisite not completed; no maintenance Pod created')
  for path,namespace in [('/var/tmp/crg-realpaths64-20261111','crg-vendor-lab-realpaths64-20261111'),('/var/tmp/crg-realpaths54-20261111','crg-vendor-lab-realpaths54-20261111')]:
   p=pathlib.Path(path)/'report.json';d=json.loads(p.read_text())
   if d.get('phase')!='passed' or d.get('namespace_absent') is not True:raise RuntimeError('prior qualified business or maintenance not passed and cleaned')
   absent=run(['kubectl','get','namespace',namespace,'--ignore-not-found','-o','json'],False)
   if absent.returncode or absent.stdout.strip():raise RuntimeError('prior namespace independently not absent')
  (root/'tools').mkdir(mode=0o700)
  for name in ['vendor-soak-load.py','vendor-soak-campaign.py','vendor-engine-smoke.py']:shutil.copyfile(candidates/'tests'/name,root/'tools'/name)
  report['phase']='preparing';save()
  gates=root/'gates';gates.mkdir(mode=0o700)
  aux=root/'aux';aux.mkdir(mode=0o700);shutil.copyfile('/usr/bin/etcd',aux/'etcd');(aux/'etcd').chmod(0o755)
  if run(['kubectl','get','namespace',ns],False).returncode==0:raise RuntimeError('namespace already exists')
  create({'apiVersion':'v1','kind':'Namespace','metadata':{'name':ns,'labels':{'managed-by':'crg-vendor-test'}}});created=True
  create({'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'deny-all','namespace':ns},'spec':{'podSelector':{},'policyTypes':['Ingress','Egress']}})
  images=json.loads((source/'vendor-import.json').read_text())['images']
  for index,role in enumerate(['dbs','hisdbs']):
   pod_created=False;nativejob=None;log=None;item={'phase':'preparing'};report['roles'][role]=item;save()
   try:
    available=reserve(28);folder=root/(role+'-business');folder.mkdir(mode=0o700)
    for n in ['postgresql','dbs','highgo','log','core','sql','hbp-runtime','resource-state','cache-state','etcd','ccg','crg','crg-config','recovery','staging']:(folder/n).mkdir(mode=0o700)
    for n in ['bin','scripts','config']:(folder/'ccg'/n).mkdir(mode=0o700)
    cachepath='/home/ccg-backups/dbs' if role=='dbs' else '/opt/PUC-784/ccg-backups/hisdbs'
    shutil.copyfile(source/'fixture'/role/'supervisor.sh',folder/'ccg/scripts/business-supervisor.sh')
    shutil.copyfile(source/'fixture/containercacheguard',folder/'ccg/bin/containercacheguard');(folder/'ccg/bin/containercacheguard').chmod(0o755)
    oldbin=candidates/'binaries/previous';newbin=candidates/'binaries/candidate'
    oldsha=hashlib.sha256(oldbin.read_bytes()).hexdigest();newsha=hashlib.sha256(newbin.read_bytes()).hexdigest()
    if oldsha!='f07973272313db26d359797dda4665145f7dd6490bac2a55f9084bd367faf361' or newsha!='dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8':raise RuntimeError('source-qualified test binary digest mismatch')
    shutil.copyfile(oldbin,folder/'crg/crg');(folder/'crg/crg').chmod(0o755)
    shutil.copyfile(newbin,folder/'staging/crg');(folder/'staging/crg').chmod(0o755)
    shutil.copyfile(candidates/'examples/optional-agent.sh',folder/'crg/optional-agent.sh')
    cache=json.loads((source/'fixture'/role/'cache.json').read_text());cache['state_file']=cachepath+'/status.json';(folder/('ccg/config/'+role+'.json')).write_text(json.dumps(cache))
    (folder/'crg-config/config.json').write_text(json.dumps({'resource_mode':'manual','limits':{'cpu_cores':7.2,'memory_max':'20001980416B','io_read_bps':'64MiB','io_write_bps':'64MiB','io_read_iops':4096,'io_write_iops':4096},'data_paths':['/opt/postgresql']}))
    env=json.loads((source/'fixture'/role/'env.json').read_text());secret=uuid.uuid4().hex
    env.update(MY_POD_NAMESPACE=ns,MY_POD_NAME=role+'-realpath-0',PGPASSWORD=secret,CCG_BIN='/opt/ccg/bin/containercacheguard',CCG_CONFIG='/opt/ccg/config/'+role+'.json',CRG_BIN='/opt/crg/crg',CRG_CONFIG='/etc/crg/config.json',CRG_HELPER_SCRIPT='/opt/crg/optional-agent.sh',YSP_PRODUCT_TYPE='PUC-DBS')
    pg=(source/'fixture'/role/'postgres.yml').read_text();pg=re.sub(r'(?m)^(\s+password:).*$',r'\1 '+secret,pg).replace('namespace: /crg-isolated/','namespace: /crg-realpaths/')
    (folder/'postgres.yml').write_text(pg);(folder/'postgres.yml').chmod(0o600)
    shutil.copyfile('/etc/localtime',folder/'localtime');(folder/'timezone').write_text('Asia/Shanghai\n')
    vols=[];mounts=[]
    def volume(name,path,target,readonly=False,file=False):
     vols.append({'name':name,'hostPath':{'path':str(path),'type':'File' if file else 'Directory'}});mounts.append({'name':name,'mountPath':target,'readOnly':readonly})
    for n,target,readonly in [('postgresql','/opt/postgresql',False),('dbs','/opt/dbs',False),('highgo','/opt/highgo',False),('log','/var/log',False),('core','/opt/local/tmp/core',False),('hbp-runtime','/var/run/.hbp',False),('cache-state',cachepath,False),('resource-state','/tmp/containerresourceguard',False),('ccg','/opt/ccg',True),('crg','/opt/crg',False),('crg-config','/etc/crg',False)]:volume(n,folder/n,target,readonly)
    volume('recovery',folder/'recovery','/recovery');volume('staging',folder/'staging','/staging',True)
    volume('pgconfig',folder/'postgres.yml','/home/config/postgres.yml',True,True);volume('localtime',folder/'localtime','/etc/localtime',False,True);volume('timezone',folder/'timezone','/etc/timezone',False,True)
    if role=='dbs':
     volume('sql',folder/'sql','/opt/dbs/sql');mounts.append({'name':'sql','mountPath':'/opt/sql'})
    else:
     vols.append({'name':'data','emptyDir':{}});mounts.append({'name':'data','mountPath':'/data'})
    for name,target,empty in [('shm','/dev/shm',{'medium':'Memory','sizeLimit':'1Gi'}),('hbp','/opt/hbp',{})]:vols.append({'name':name,'emptyDir':empty});mounts.append({'name':name,'mountPath':target})
    volume('gate',gates,'/network-gates',True)
    vols.extend([{'name':'aux','hostPath':{'path':str(aux),'type':'Directory'}},{'name':'etcd','hostPath':{'path':str(folder/'etcd'),'type':'Directory'}}])
    start='i=0; while [ ! -f "/network-gates/$CRG_TEST_POD_UID" ]; do i=$((i+1)); [ "$i" -lt 120 ] || exit 92; sleep 1; done; exec /bin/bash /opt/ccg/scripts/business-supervisor.sh'
    envs=[{'name':k,'value':v} for k,v in env.items()]+[{'name':'CRG_TEST_POD_UID','valueFrom':{'fieldRef':{'fieldPath':'metadata.uid'}}}]
    pod={'apiVersion':'v1','kind':'Pod','metadata':{'name':role+'-business','namespace':ns,'labels':{'managed-by':'crg-vendor-test'}},'spec':{'automountServiceAccountToken':False,'enableServiceLinks':False,'restartPolicy':'Never','terminationGracePeriodSeconds':30,'containers':[{'name':role,'image':images[role]['tag'],'imagePullPolicy':'Never','command':['/bin/bash','-c',start],'env':envs,'securityContext':{'privileged':True},'resources':{'requests':{'cpu':'100m','memory':'256Mi'},'limits':{'cpu':'8','memory':'20Gi'}},'volumeMounts':mounts},{'name':'isolated-dcs','image':images[role]['tag'],'imagePullPolicy':'Never','command':['/aux/etcd','--name','isolated','--data-dir','/isolated-etcd','--listen-client-urls','http://127.0.0.1:2379','--advertise-client-urls','http://127.0.0.1:2379','--listen-peer-urls','http://127.0.0.1:2380','--initial-advertise-peer-urls','http://127.0.0.1:2380','--initial-cluster','isolated=http://127.0.0.1:2380'],'resources':{'requests':{'cpu':'10m','memory':'32Mi'},'limits':{'cpu':'1','memory':'256Mi'}},'volumeMounts':[{'name':'aux','mountPath':'/aux','readOnly':True},{'name':'etcd','mountPath':'/isolated-etcd'}]}],'volumes':vols}}
    private=folder/'pod.json';private.write_text(json.dumps(pod));private.chmod(0o600);create(pod);pod_created=True
    run(['kubectl','wait','-n',ns,'--for=condition=Ready','pod/'+role+'-business','--timeout=90s'],timeout=100)
    meta=json.loads(run(['kubectl','get','pod','-n',ns,role+'-business','-o','json']).stdout);cid=next(x['containerID'].split('://')[1] for x in meta['status']['containerStatuses'] if x['name']==role)
    pid=json.loads(run(['crictl','inspect',cid]).stdout)['info']['pid'];run(['nsenter','-t',str(pid),'-n','--','ip','link','set','dev','eth0','down'])
    if 'state DOWN' not in run(['nsenter','-t',str(pid),'-n','--','ip','-o','link','show','dev','eth0']).stdout:raise RuntimeError('network gate not isolated')
    started=time.monotonic();(gates/meta['metadata']['uid']).write_text('isolated\n');item={'phase':'booting','resource_mode':'manual','candidate_branch':'protocol-advertising-combined-development-binaries','memory_reserve_before_bytes':available,'original_start_script_unmodified':True,'same_container_mount_paths':True,'original_ccg_readonly':True};report['roles'][role]=item;report['phase']='testing-'+role;save()
    deadline=time.monotonic()+300
    while time.monotonic()<deadline:
     reserve()
     try:
      q=ex(role,'su','-','postgres','-c','/opt/postgresql/pgsql/bin/pg_isready -h 127.0.0.1 -p 5432 -t 2',check=False,timeout=max(0.01,min(15,deadline-time.monotonic())))
      item['last_readiness_probe']={'exit':q.returncode,'output':(q.stdout+q.stderr)[-1500:]};save()
      status=folder/'resource-state/status.json'
      if q.returncode==0 and status.exists() and json.loads(status.read_text()).get('state')=='managed' and time.monotonic()<deadline:
       api="import urllib2,json; r=urllib2.urlopen(urllib2.Request('http://127.0.0.1:8090/test',data='{}',headers={'Content-Type':'application/json'}),timeout=3); assert r.getcode()==200; assert json.loads(r.read(1024))['Result']=='000'"
       a=ex(role,'python','-c',api,check=False,timeout=max(0.01,min(10,deadline-time.monotonic())))
       item['last_api_probe']={'exit':a.returncode};save()
       if a.returncode==0 and time.monotonic()<deadline:break
     except subprocess.TimeoutExpired:
      item['readiness_observation_timeouts']=item.get('readiness_observation_timeouts',0)+1;save()
     time.sleep(max(0,min(3,deadline-time.monotonic())))
    else:raise RuntimeError(role+' original PG/API readiness/managed budget not met within declared 300s')
    item['ready_and_managed_seconds']=time.monotonic()-started;state=json.loads(status.read_text());item['automatic_io']=state.get('automatic_io');save()
    record(role+'-real-path-original-startup-manual-accepted-budget',state['state']=='managed' and state.get('automatic_io') is None and not (folder/'crg-config/io-profile.json').exists())
    mountinfo=ex(role,'findmnt','-n','-o','OPTIONS','/opt/ccg').stdout.strip();record(role+'-original-CCG-mount-stays-readonly','ro' in mountinfo.split(','))
    cachefile=folder/'cache-state/status.json';cache_started=time.monotonic();cache_deadline=min(started+300,cache_started+45)
    while time.monotonic()<cache_deadline:
     if cachefile.exists() and json.loads(cachefile.read_text()).get('action')=='enforce':break
     time.sleep(min(1,max(0,cache_deadline-time.monotonic())))
    item['cache_enforce_observation_seconds']=time.monotonic()-cache_started
    record(role+'-original-cache-independent-enforce',cachefile.exists() and json.loads(cachefile.read_text()).get('action')=='enforce' and time.monotonic()<=started+300)
    statefile=folder/'resource-state/journal.json';held=statefile.read_bytes()
    cg=pathlib.Path('/sys/fs/cgroup')/next(x.split('::',1)[1].lstrip('/') for x in pathlib.Path('/proc/%s/cgroup'%pid).read_text().splitlines() if x.startswith('0::'))
    if cg.name!='cri-containerd-'+cid+'.scope':raise RuntimeError('online-upgrade target not own container leaf')
    controls={f:(cg/f).read_text() for f in ['cpu.max','memory.max','io.max','pids.max','cpu.weight','io.weight','memory.high','memory.swap.max']};pid1=ex(role,'cat','/proc/1/stat').stdout.split()[21]
    cachepids=[]
    for process in (cg/'cgroup.procs').read_text().splitlines():
     try:
      path=pathlib.Path('/proc')/process
      if pathlib.Path(os.fsdecode(path.joinpath('cmdline').read_bytes().split(b'\0')[0])).name=='containercacheguard':cachepids.append((process,path.joinpath('stat').read_text().split()[21]))
     except (FileNotFoundError,ProcessLookupError):pass
    if len(cachepids)!=1:raise RuntimeError('expected one original cache process')
    oom=int(dict(x.split() for x in (cg/'memory.events').read_text().splitlines())['oom_kill'])
    maintenance_active=False
    def check_measurement():
     return nativejob.poll() is None and loadfile.exists() and json.loads(loadfile.read_text()).get('phase')=='running' and time.time()<measurement_started_epoch+600
    def original_map():
     data=json.loads(statefile.read_bytes())
     return {k:(v['file'],v.get('device',''),v['original']) for k,v in data['mutations'].items()}
    held_originals=original_map();expected_controls=dict(controls)
    runtime_controls=dict(controls,**{'cpu.max':'800000 100000\n','memory.max':'21474836480\n','io.max':''})
    def same():
     return original_map()==held_originals and all((cg/f).read_text()==v for f,v in expected_controls.items()) and ex(role,'cat','/proc/1/stat').stdout.split()[21]==pid1 and all(pathlib.Path('/proc',p,'stat').read_text().split()[21]==ticks for p,ticks in cachepids)
    def operation(label,action):
     if maintenance_active and not check_measurement():raise RuntimeError('migration outside active600s native measurement')
     began=time.time();result=action();ended=time.time()
     if maintenance_active:
      if not check_measurement():raise RuntimeError('migration not completely covered by native600')
      item.setdefault('maintenance_intervals',[]).append({'command':label,'started_epoch':began,'ended_epoch':ended});save()
     return result
    def cli_at(executable,command,*a,**kw):
     expected_failure=kw.pop('expected_failure',False);kw['check']=False
     result=operation(executable+':'+command,lambda:ex(role,executable,command,'--config','/etc/crg/config.json',*a,**kw))
     if bool(result.returncode)!=expected_failure:
      try:failure=json.loads(result.stdout)
      except (ValueError,TypeError):failure={}
      item['last_maintenance_failure']={'command':command,'exit':result.returncode,'response':{k:failure[k] for k in ['schema','state','reason_code','error','business_action'] if k in failure},'stderr_tail':result.stderr[-2048:]};save()
      raise RuntimeError('unexpected migration command result: '+command)
     return result
    def cli(command,*a,**kw):return cli_at('/staging/crg',command,*a,**kw)
    def no_agent():
     found=[]
     for process in (cg/'cgroup.procs').read_text().splitlines():
      try:
       p=pathlib.Path('/proc',process);args=p.joinpath('cmdline').read_bytes().split(b'\0')
       if len(args)>1 and pathlib.Path(os.fsdecode(args[0])).name=='crg' and args[1]==b'run':found.append(process)
      except (FileNotFoundError,ProcessLookupError):pass
     return not found
    def atomic_switch(binary,want_current,want_new,label):
     def perform():
      check=json.loads(cli('upgrade-check').stdout)
      target=folder/'crg/crg'
      if not check['compatible'] or not check['quiescent_snapshot'] or not no_agent() or not same():raise RuntimeError('manual migration requires disabled identity, no writer, controls and original ownership')
      if target.is_symlink() or target.parent.resolve()!=folder/'crg' or hashlib.sha256(target.read_bytes()).hexdigest()!=want_current or hashlib.sha256(binary.read_bytes()).hexdigest()!=want_new:raise RuntimeError('manual migration binary path or digest differs')
      temporary=target.with_name('crg-'+label+'.new')
      with temporary.open('xb') as f:
       os.fchmod(f.fileno(),0o755);f.write(binary.read_bytes());f.flush();os.fsync(f.fileno())
      if not no_agent() or not same() or hashlib.sha256(target.read_bytes()).hexdigest()!=want_current:raise RuntimeError('manual migration pre-rename recheck')
      os.replace(temporary,target);fd=os.open(str(target.parent),os.O_RDONLY|os.O_DIRECTORY)
      try:os.fsync(fd)
      finally:os.close(fd)
      if hashlib.sha256(target.read_bytes()).hexdigest()!=want_new:raise RuntimeError('manual migration installed digest differs')
     return operation('explicit-manual-atomic-switch-'+label,perform)
    def wait_guard(expected,seconds=120):
     deadline=time.monotonic()+seconds
     while time.monotonic()<deadline:
      found=[]
      for process in (cg/'cgroup.procs').read_text().splitlines():
       try:
        path=pathlib.Path('/proc')/process;argv=path.joinpath('cmdline').read_bytes().split(b'\0')
        if len(argv)>1 and pathlib.Path(os.fsdecode(argv[0])).name=='crg' and argv[1]==b'run':found.append(hashlib.sha256(path.joinpath('exe').read_bytes()).hexdigest())
       except (FileNotFoundError,ProcessLookupError):pass
      if found==[expected] and all((cg/f).read_text()==v for f,v in expected_controls.items()) and not (folder/'resource-state/disabled.json').exists():
       if maintenance_active and not check_measurement():raise RuntimeError('Agent resume not covered by active native measurement')
       return True
      time.sleep(1)
     return False
    record(role+'-original-reader-is-source-qualified-and-managed',wait_guard(oldsha),previous_sha256=oldsha,candidate_sha256=newsha,previous_build_info=json.loads(ex(role,'/opt/crg/crg','build-info').stdout),candidate_build_info=json.loads(ex(role,'/staging/crg','build-info').stdout))
    runid='20261111392'+str(index);entry='/tmp/crg-upgrade-load-'+runid+'.py';worker=(root/'tools/vendor-soak-load.py').read_bytes()
    r=subprocess.run(['kubectl','exec','-i','-n',ns,role+'-business','-c',role,'--','/bin/bash','-c','set -Ce; umask 077; cat > '+entry+'; chmod 0444 '+entry],input=worker,capture_output=True,timeout=30)
    if r.returncode or ex(role,'sha256sum',entry).stdout.split()[0]!=hashlib.sha256(worker).hexdigest():raise RuntimeError('native worker copy verification failed')
    log=(root/(role+'-online-load.log')).open('xb');nativejob=subprocess.Popen(['kubectl','exec','-n',ns,role+'-business','-c',role,'--','su','-','postgres','-c','CRG_VENDOR_SOAK_TEST=disposable-loopback-only python '+entry+' --run-id '+runid+' --seconds 600 --test-phase smoke'],stdin=subprocess.DEVNULL,stdout=log,stderr=log)
    loadfile=folder/('postgresql/basebackup/crg-soak-'+runid+'/load.json');deadline=time.monotonic()+360
    while time.monotonic()<deadline:
     if nativejob.poll() is not None:raise RuntimeError('native worker ended before online-upgrade measurement')
     if loadfile.exists() and json.loads(loadfile.read_text()).get('phase')=='running':break
     reserve();time.sleep(2)
    else:raise RuntimeError('native measurement preparation deadline')
    measured=json.loads(loadfile.read_text());measurement_started_epoch=datetime.datetime.strptime(measured['started_utc'],'%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=datetime.timezone.utc).timestamp();maintenance_active=True
    item['phase']='online-upgrade-native-measurement';save()
    cli('quiesce');record(role+'-candidate-quiesce-stops-old-writer-and-retains-originals',same() and no_agent())
    rejected=cli('binary-install','--install-dir','/opt/crg','--backup-dir','/recovery/rejected-install','--previous-sha256',oldsha,'--candidate-sha256',newsha,expected_failure=True,timeout=90)
    rejection=json.loads(rejected.stdout);item['unsupported_protocol_rejection']={k:rejection[k] for k in ['state','reason_code','error'] if k in rejection};save()
    record(role+'-unadvertised-old-protocol-installer-refuses-without-replacement',any(x in str(rejection).lower() for x in ['protocol','journal']) and hashlib.sha256((folder/'crg/crg').read_bytes()).hexdigest()==oldsha and not (folder/'recovery/rejected-install').exists() and same())
    old_disabled=json.loads(cli_at('/opt/crg/crg','disable').stdout);expected_controls=dict(runtime_controls)
    record(role+'-matching-published-old-disable-restores-exact-runtime-controls',old_disabled['state']=='restored' and no_agent() and same())
    def private_backup():
     backup=folder/'recovery/old';backup.mkdir(mode=0o700)
     with (backup/'crg').open('xb') as f:
      os.fchmod(f.fileno(),0o755);f.write(oldbin.read_bytes());f.flush();os.fsync(f.fileno())
     fd=os.open(str(backup),os.O_RDONLY|os.O_DIRECTORY)
     try:os.fsync(fd)
     finally:os.close(fd)
     compatible=json.loads(cli('upgrade-check').stdout)
     if not compatible['compatible'] or not compatible['quiescent_snapshot']:raise RuntimeError('new reader rejects disabled old state')
     cli('state-backup','--output','/recovery/state-before-migration.json')
     snapshot=folder/'recovery/state-before-migration.json'
     if snapshot.is_symlink() or snapshot.stat().st_mode&0o777!=0o600 or not same():raise RuntimeError('private old-state backup not preserved')
     item['private_state_backup']={'bytes':snapshot.stat().st_size,'sha256':hashlib.sha256(snapshot.read_bytes()).hexdigest(),'raw_private_contents_not_published':True};save()
    operation('private-original-state-and-old-binary-backup',private_backup)
    atomic_switch(newbin,oldsha,newsha,'candidate')
    record(role+'-explicit-manual-migration-after-old-disable-and-private-backup',hashlib.sha256((folder/'crg/crg').read_bytes()).hexdigest()==newsha and no_agent() and same())
    expected_controls=dict(controls);cli('enable')
    record(role+'-published-current-Agent-resumes-on-original-helper-and-journal',wait_guard(newsha) and same())
    cli('quiesce');old_restored=json.loads(cli_at('/recovery/old/crg','restore').stdout);expected_controls=dict(runtime_controls)
    record(role+'-actual-published-old-reader-restores-current-three-resource-journal',old_restored['state']=='restored' and no_agent() and same())
    atomic_switch(folder/'recovery/old/crg',newsha,oldsha,'previous')
    expected_controls=dict(controls);cli_at('/opt/crg/crg','enable')
    record(role+'-published-old-Agent-resumes-after-explicit-manual-rollback',wait_guard(oldsha) and same())
    maintenance_active=False
    deadline=time.monotonic()+900
    while nativejob.poll() is None and time.monotonic()<deadline:reserve();time.sleep(3)
    if nativejob.poll() is None:raise RuntimeError('native completion deadline')
    log.close();native=json.loads(loadfile.read_text());item['native']=native;save()
    record(role+'-600s-native-SQL-API-across-upgrade-and-rollback',nativejob.returncode==0 and native['phase']=='passed' and same() and int(dict(x.split() for x in (cg/'memory.events').read_text().splitlines())['oom_kill'])==oom)
    disabled=json.loads(cli_at('/opt/crg/crg','disable').stdout)
    record(role+'-final-disable-restores-true-runtime-controls',disabled['state']=='restored' and (cg/'cpu.max').read_text().strip()=='800000 100000' and (cg/'memory.max').read_text().strip()=='21474836480' and (cg/'io.max').read_text().strip()=='' and all((cg/f).read_text()==controls[f] for f in ['pids.max','cpu.weight','io.weight','memory.high','memory.swap.max']) and ex(role,'cat','/proc/1/stat').stdout.split()[21]==pid1)
    item['phase']='short-acceptance-passed';save()
   except Exception as error:item.update(phase='failed',error=str(error),traceback=traceback.format_exc());save()
   finally:
    if pod_created:delete_pod(role);item['own_pod_removed']=True
    if nativejob is not None:
     try:nativejob.wait(timeout=20)
     except subprocess.TimeoutExpired:nativejob.terminate();nativejob.wait(timeout=15)
    if log is not None:log.close()
    save()
  report['phase']='passed' if all(v['phase']=='short-acceptance-passed' for v in report['roles'].values()) else 'failed'
 except BaseException as e:report.update(phase='failed',error=str(e),traceback=traceback.format_exc())
 finally:
  if created:
   m=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout)
   if m['metadata']['labels'].get('managed-by')!='crg-vendor-test':raise RuntimeError('namespace cleanup ownership mismatch')
   run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=150s'],False,160);absent=run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json'],False);report['namespace_absent']=absent.returncode==0 and not absent.stdout.strip()
  if root.exists():save()
 print(json.dumps({'phase':report['phase'],'checks':len(report['tests']),'error':report.get('error')}))

 raise SystemExit(0 if report['phase']=='passed' and report.get('namespace_absent') is True and len(report['roles'])==2 and len(report['tests'])==26 and all(x['passed'] for x in report['tests']) else 1)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=pathlib.Path,required=True);p.add_argument('--plan-sha256',required=True);p.add_argument('--execute',action='store_true');args=p.parse_args()
 try:
  if sys.platform!='linux' or os.geteuid()!=0:raise ValueError('LINUX_ROOT_REQUIRED')
  raw=args.plan.read_bytes();expected=dict(FROZEN_PLAN,executor_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest())
  if hashlib.sha256(raw).hexdigest()!=args.plan_sha256 or json.loads(raw)!=expected:raise ValueError('FROZEN_PLAN_MISMATCH')
  root=pathlib.Path(expected['work_root']);tools=pathlib.Path(expected['tool_root'])
  if os.path.lexists(root):raise ValueError('FRESH_TARGET_REQUIRED')
  q=subprocess.run(['kubectl','get','namespace',expected['namespace'],'--ignore-not-found','-o','json'],capture_output=True,text=True,timeout=15)
  if q.returncode or q.stdout.strip():raise ValueError('FRESH_NAMESPACE_REQUIRED')
  for name,want in expected['inputs_sha256'].items():
   path=tools/name
   if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('FROZEN_INPUT:'+name)
  if not args.execute:
   print(json.dumps({'phase':'ready','executed':False,'expected_checks':26,'stable_release_accepted':False}));return 0
  if os.environ.get('CRG_PUBLISHED_MIGRATION')!='authorized-disposable-test-node-only':raise ValueError('EXPLICIT_LAB_MARKER_REQUIRED')
  def interrupted(signum,frame):raise KeyboardInterrupt()
  signal.signal(signal.SIGTERM,interrupted)
  run_migration(expected,args.plan_sha256)
 except Exception as error:
  print(json.dumps({'phase':'rejected','reason':str(error) if isinstance(error,ValueError) else type(error).__name__,'executed':False,'stable_release_accepted':False}));return 1

if __name__=='__main__':raise SystemExit(main())
