from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess
w=Path('/var/tmp/crg-final1461-tools-20261115');expected={'binaries/crg-linux-amd64': '9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8', 'examples/supervisor.sh': '7a7428bee5cfaf1742467b7a25c098507f464d9ca85b632102806f98bef5aec9', 'examples/optional-agent.sh': 'f7e7208f58bac7066d75d49cb17199b720e3d05bb5953e2a7a7800f881b54b79', 'qualification.json': '64d9b042005006f0c3e2a551060d506c838c4b84cc69d889e1283ec7f53453a0', 'overhead-job.py': 'c7079e5877793a82bc62d0b5090433e1560f31f15f48ed002e80705554a21588', 'runner.py': '6bde3aa54ecddb2d0090508451e02cd3fa72ccb78d7184eb44ccb4a124d97ef4', 'overhead-plan.json': '6b39a50e93705bb7e139ffb0e79cb2ec3ace0fd1ae220d7af68a2665b2aafc83'};corrected={'tools': '/var/tmp/crg-final1465-tools-20261115', 'output': '/var/tmp/crg-final1465-results-20261115', 'job_sha256': '978ad3c2482cd2035189305d44efa20061dc96560345af3956a5b2c2894c33c7', 'plan_sha256': '1b5b9124b14d4e4f6a30eecfb9a68f4dff51d47b000326dfb94e723848d01af4', 'namespaces': ['crg-vendor-lab-final1465-normal-dbs-20261115', 'crg-vendor-lab-final1465-normal-hisdbs-20261115']};sha=lambda v:hashlib.sha256(v).hexdigest();prerequisites={}
for name,h in expected.items():assert sha((w/name).read_bytes())==h
p=json.loads((w/'overhead-plan.json').read_bytes());assert os.geteuid()==0 and not Path(p['output']).exists() and not any((w/name).exists() for name in ['launch.json','launch.guard','runner.log','worker.json','exit.json'])
def absent(v):
 try:return int(Path('/proc',str(v['pid']),'stat').read_bytes().rsplit(b')',1)[1].split()[19])!=v['start_ticks']
 except (FileNotFoundError,ProcessLookupError):return True
def ns_absent(ns):
 q=subprocess.run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json','--request-timeout=3s'],capture_output=True,text=True,timeout=6,check=True);assert not q.stderr;return not q.stdout.strip()
def coordinator(spec,phase,exitcode):
 tools=Path(spec['tools']);root=Path(spec['output']);raw=(root/'report.json').read_bytes();r=json.loads(raw);assert sha((tools/'plan.json').read_bytes())==spec['plan_sha256'] and sha((tools/'business-driver.py').read_bytes())==spec['job_sha256'];assert r['phase']==phase and r['job_sha256']==spec['job_sha256'] and r['plan_sha256']==spec['plan_sha256'] and json.loads((tools/'exit.json').read_bytes())['exit']==exitcode and absent(json.loads((tools/'launch.json').read_bytes())) and len(r['roles'])==2
 for row in r['roles'].values():
  assert row['phase']==phase and row['exit']==exitcode and row['recorded_checks']==row['passed_checks']==10 and absent(row['driver'])
  for c in row['cleanup']:
   fixture=c['identity'];assert not Path(fixture['group']).exists() and not Path(fixture['pod_parent']).exists() and all(absent(v) for v in fixture['processes']+c['additional_processes'])
 assert all(ns_absent(ns) for ns in spec['namespaces']);return sha(raw)
old=p['launch_requires_diagnostic_terminal_clean'];prerequisites['failed1448_report_sha256']=coordinator(old,'failed',1);assert prerequisites['failed1448_report_sha256']=='86ac9a71e30459bf74abdb6a848eb4c65be19388986a8601ac133a425a5e55c8';prerequisites['corrected1465_report_sha256']=coordinator(corrected,'passed',0)
ref=p['completed_lowIO_and_fault_reference'];tools=Path(ref['tools']);raw=(Path(ref['output'])/'report.json').read_bytes();assert sha(raw)==ref['report_sha256'];r=json.loads(raw);assert r['phase']=='passed' and json.loads((tools/'exit.json').read_bytes())['exit']==0 and absent(json.loads((tools/'launch.json').read_bytes())) and absent(json.loads((tools/'worker.json').read_bytes())) and ns_absent('crg-final1404-overhead-20261115')
for row in r['cases'].values():
 fixture=row['fixture_identity'];assert absent(fixture['main']) and absent(fixture['Agent']) and not Path(fixture['group']).exists() and not Path(fixture['pod_parent']).exists()
prerequisites['completed1404_report_sha256']=sha(raw)
assert ns_absent(p['namespace']) and not Path('/var/tmp/crg-final1396-results-20261115').exists()
for proc in Path('/proc').glob('[0-9]*'):
 try:
  args=(proc/'cmdline').read_bytes().split(bytes([0]));assert not any(str(w/name).encode() in args for name in ['runner.py','overhead-job.py']),'own entry already live';assert not any(b'/crg-final' in arg and arg.endswith((b'/business-driver.py',b'/vendor-soak-campaign.py')) for arg in args),'new final business fixture still active'
 except (FileNotFoundError,ProcessLookupError):pass
available=int(next(v.split()[1] for v in Path('/proc/meminfo').read_text().splitlines() if v.startswith('MemAvailable:')))*1024;free=shutil.disk_usage('/var/tmp').free;assert available>=8*1024**3 and free>=20*1024**3
ownargs=Path('/proc/self/cmdline').read_bytes().split(bytes([0]));launcher_sha=sha(ownargs[ownargs.index(b'-c')+1]);os.umask(0o077);guard=os.open(w/'launch.guard',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.write(guard,b'one authorized launch only\n');os.fsync(guard);os.close(guard)
with (w/'runner.log').open('xb') as log:
 child=subprocess.Popen(['python3','-B',str(w/'runner.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True);fields=Path('/proc',str(child.pid),'stat').read_bytes().rsplit(b')',1)[1].split();assert fields[0]!=b'Z';record={'pid':child.pid,'start_ticks':int(fields[19]),'entry':str(w/'runner.py'),'job_sha256':p['job_sha256'],'plan_sha256':sha((w/'overhead-plan.json').read_bytes()),'node_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'launcher_sha256':launcher_sha,'prerequisite_report_sha256':prerequisites}
 with (w/'launch.json').open('x') as stream:json.dump(record,stream);stream.write('\n');stream.flush();os.fsync(stream.fileno())
 assert str(w/'runner.py').encode() in Path('/proc',str(child.pid),'cmdline').read_bytes().split(bytes([0]));print(json.dumps({'phase':'two-effective-budget-overhead-launched-once','launch':record,'available_memory_bytes':available,'free_disk_bytes':free,'stable_release_accepted':False}))
