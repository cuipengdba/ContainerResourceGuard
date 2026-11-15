from pathlib import Path
import datetime,hashlib,importlib.util,json,os,re,stat,subprocess,sys,time,traceback
w=Path('/var/tmp/crg-final1429-tools-20261115');raw=(w/'plan.json').read_bytes();plan=json.loads(raw);sha=lambda b:hashlib.sha256(b).hexdigest();plan_sha=sha(raw);root=Path(plan['output']);assert root==Path('/var/tmp/crg-final1429-results-20261115') and not root.exists();os.umask(0o077)
for name,h in plan['source_sha256'].items():assert sha((w/name).read_bytes())==h
def absent(row):
 try:return int(Path('/proc',str(row['pid']),'stat').read_bytes().rsplit(b')',1)[1].split()[19])!=row['start_ticks']
 except (FileNotFoundError,ProcessLookupError):return True
def ns_absent(ns):
 q=subprocess.run(['kubectl','get','namespace',ns,'--ignore-not-found','--request-timeout=3s','-o','json'],capture_output=True,text=True,timeout=5,check=True);assert not q.stderr;return not q.stdout.strip()
for p in plan['prerequisites']:
 oldraw=(Path(p['output'])/'report.json').read_bytes();assert sha(oldraw)==p['report_sha256'];old=json.loads(oldraw);assert old['phase']=='passed' and json.loads((Path(p['tools'])/'exit.json').read_bytes())['exit']==0 and absent(json.loads((Path(p['tools'])/'launch.json').read_bytes()))
 for row in old['roles'].values():
  assert row['phase']=='passed' and absent(row['driver'])
  for c in row['cleanup']:
   identity=c['identity'];assert not Path(identity['group']).exists() and not Path(identity['pod_parent']).exists() and all(absent(v) for v in identity['processes'])
 assert all(ns_absent(n) for n in p['namespaces'])
p=plan['diagnostic_prerequisite'];pr=Path(p['tools']);oldraw=(pr/'result/report.json').read_bytes();assert sha(oldraw)==p['report_sha256'];old=json.loads(oldraw);assert old['phase']=='passed' and len(old['tests'])==14 and all(v['passed'] for v in old['tests']) and json.loads((pr/'exit.json').read_bytes())['exit']==0 and absent(json.loads((pr/'launch.json').read_bytes())) and ns_absent(p['namespace'])
for row in old['roles'].values():assert not Path(row['group']).exists() and not Path(row['pod_parent']).exists() and all(absent(v) for v in [row['init'],row['owner_exec'],*row['socket_owner_instances']])
p=plan['required_current_full600'];previous_raw=(Path(p['output'])/'report.json').read_bytes();assert sha(previous_raw)==p['report_sha256'];previous=json.loads(previous_raw);assert previous['phase']=='passed' and json.loads((Path(p['tools'])/'exit.json').read_bytes())['exit']==0 and absent(json.loads((Path(p['tools'])/'launch.json').read_bytes()))
for row in previous['roles'].values():
 assert row['phase']=='passed' and absent(row['driver'])
 for c in row['cleanup']:
  identity=c['identity'];assert not Path(identity['group']).exists() and not Path(identity['pod_parent']).exists() and all(absent(v) for v in identity['processes']+c['additional_processes'])
assert all(ns_absent(n) for n in p['namespaces'])
spec=importlib.util.spec_from_file_location('own_startup_reader',w/'tests/own-pg-startup-log.py');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
for role,expected in plan['reader_native_replay'].items():
 v=reader.collect(Path(expected['folder']),expected['run_id']);assert v['phase']=='complete' and v['source_sha256']==expected['source_sha256'] and v['records']==6 and 'Address already in use' in v['exact_utf8']
assert all(ns_absent(n) for arm in plan['namespaces'].values() for n in arm.values())
assert os.geteuid()==0 and os.uname().machine=='x86_64' and hasattr(os,'pidfd_open')
available=int(next(v.split()[1] for v in Path('/proc/meminfo').read_text().splitlines() if v.startswith('MemAvailable:')))*1024;assert available>=28*1024**3
root.mkdir(mode=0o700);out={'schema':'crg-port-conflict-and-full600-coordinator-v1','phase':'running','job_sha256':plan['job_sha256'],'plan_sha256':plan_sha,'started_epoch':time.time(),'roles':{},'errors':[],'product_changed':False,'no_other_fixture_restart_or_resource_mutation':True}
def save():(root/'report.json').write_text(json.dumps(out,indent=2)+'\n')
try:
 for arm in plan['arms']:
  (root/arm).mkdir(mode=0o700)
  for role in ['dbs','hisdbs']:
   key=arm+'-'+role;assert ns_absent(plan['namespaces'][arm][role]);row={'phase':'starting','arm':arm,'role':role};out['roles'][key]=row;out['phase']='testing-'+key;save()
   with (root/(key+'-driver.log')).open('xb') as log:
    child=subprocess.Popen([sys.executable,'-B',str(w/'business-driver.py'),role,arm],stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=dict(os.environ,CRG_FINAL1429_BUSINESS='authorized-disposable-test-node-only'));row['driver']={'pid':child.pid,'start_ticks':int(Path('/proc',str(child.pid),'stat').read_bytes().rsplit(b')',1)[1].split()[19]),'entry':str(w/'business-driver.py'),'role':role,'arm':arm};save();row['exit']=child.wait()
   row.update(driver_original_absent=absent(row['driver']),namespace_absent=ns_absent(plan['namespaces'][arm][role]),phase='failed');report_path=root/arm/role/'report.json'
   if report_path.exists():
    rr=report_path.read_bytes();assert len(rr)<=8*1024*1024;r=json.loads(rr);row.update(report_sha256=sha(rr),recorded_checks=len(r['tests']),passed_checks=sum(v['passed'] for v in r['tests']),original_phase=r['phase'],cases=r['roles'],cleanup=[])
    for case in r['roles'].values():
     identity=case.get('fixture_identity',{});events=case.get('engine_report',{}).get('roles',{}).get(role,{}).get('port_diagnostics',[]) if arm=='conflict' else case.get('engine_diagnostics',[]);additional=[]
     for event in events:
      for listener in event.get('sample',{}).get('listeners',[]):
       for owner in listener['owners']:
        if owner['same_cgroup']:additional.append({k:owner[k] for k in ['pid','start_ticks']})
     if case.get('holder_exec'):additional.append(case['holder_exec'])
     row['cleanup'].append({'identity':identity,'leaf_absent':'group' in identity and not Path(identity['group']).exists(),'parent_absent':'pod_parent' in identity and not Path(identity['pod_parent']).exists(),'registered_processes_absent':bool(identity.get('processes')) and all(absent(v) for v in identity['processes']),'additional_processes':additional,'additional_processes_absent':all(absent(v) for v in additional)})
    expected=plan['planned_checks'][arm+'_each_role'];row['phase']='passed' if row['exit']==0 and r['phase']=='passed' and row['recorded_checks']==row['passed_checks']==expected else 'failed'
   save();assert row['driver_original_absent'] and row['namespace_absent'] and len(row.get('cleanup',[]))==1 and all(v['leaf_absent'] and v['parent_absent'] and v['registered_processes_absent'] and v['additional_processes_absent'] for v in row['cleanup']),'PREVIOUS_FIXTURE_CLEANUP_UNPROVEN_NO_NEXT_FIXTURE'
  if not all(out['roles'][arm+'-'+role]['phase']=='passed' for role in ['dbs','hisdbs']):break
 out['phase']='passed' if len(out['roles'])==2 and all(v['phase']=='passed' for v in out['roles'].values()) else 'failed'
except BaseException as error:out.update(phase='failed');out['errors'].append({'class':type(error).__name__,'traceback':traceback.format_exc()})
finally:out['ended_epoch']=time.time();save()
export=root/'export';export.mkdir(mode=0o700);copied=[];missing=[]
def copy(source,name):
 if not source.exists() and not source.is_symlink():missing.append({'source':str(source.relative_to(root)),'filename':name});return
 st=source.lstat();assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_size<=33554432;fd=os.open(str(source),os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
 with os.fdopen(fd,'rb') as stream:opened=os.fstat(stream.fileno());assert (opened.st_dev,opened.st_ino)==(st.st_dev,st.st_ino);raw=stream.read(33554433)
 after=source.lstat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) and len(raw)==st.st_size;raw.decode()
 with (export/name).open('xb') as stream:stream.write(raw)
 copied.append({'source':str(source.relative_to(root)),'filename':name,'bytes':len(raw),'sha256':sha(raw)})
copy(root/'report.json','coordinator-report.json')
for key,row in out['roles'].items():
 arm,role=row['arm'],row['role'];case_root=root/arm/role/('candidate1-'+role+'-manual64');folder=case_root/(role+'-business');campaign=case_root/('campaign-'+role);engine=case_root/'conflict-engine'
 for p,n in [(root/(key+'-driver.log'),key+'-driver.log'),(root/arm/role/'report.json',key+'-report.json'),(folder/'crg-config/config.json',key+'-config.json'),(folder/'resource-state/status.json',key+'-status.json'),(folder/'resource-state/journal.json',key+'-journal.json')]:copy(p,n)
 if arm=='conflict':
  for p,n in [(root/arm/role/('candidate1-'+role+'-manual64-engine.log'),key+'-engine.log'),(engine/'business-backup.json',key+'-engine-report.json'),(engine/'own-startup-CSV.log',key+'-own-startup-CSV.log'),(engine/(role+'-business')/'standby-start.txt',key+'-standby-start.log'),(folder/'postgresql/basebackup'/('crg-acceptance-'+plan['run_ids'][arm][role])/'standby.log',key+'-PG-standby.log')]:copy(p,n)
 else:
  for p,n in [(root/arm/role/('candidate1-'+role+'-manual64-campaign.log'),key+'-campaign.log'),(campaign/'report.json',key+'-campaign-report.json'),(folder/'postgresql/basebackup'/('crg-soak-'+plan['run_ids'][arm][role])/'load.json',key+'-native.json')]:copy(p,n)
  for i,p in enumerate(sorted(campaign.glob('backup-*/business-backup.json'))):assert i<2;copy(p,key+'-engine-'+str(i)+'.json')
 for i,p in enumerate(sorted((folder/'log/crg').glob('crg-*.log'))):assert i<3 and re.fullmatch(r'crg-[0-9]{4}-[0-9]{2}-[0-9]{2}\.log',p.name);copy(p,key+'-daily-'+str(i)+'.log')
(export/'source-map.json').write_text(json.dumps({'copied':copied,'missing':missing,'no_private_Pod_or_env_or_postgres_credentials_exported':True},indent=2)+'\n');spec=importlib.util.spec_from_file_location('exact_transfer',w/'artifact-transfer.py');transfer=importlib.util.module_from_spec(spec);spec.loader.exec_module(transfer);index=transfer.index_directory(plan['job_sha256'],plan_sha);(w/'artifact-index.json').write_text(json.dumps(index,indent=2)+'\n');exit={'exit':0 if out['phase']=='passed' else 1,'phase':out['phase'],'job_sha256':plan['job_sha256'],'plan_sha256':plan_sha,'artifact_index_complete':True,'started_epoch':out['started_epoch'],'ended_epoch':time.time()};(w/'exit.json').write_text(json.dumps(exit));print(json.dumps(exit));raise SystemExit(exit['exit'])
