from pathlib import Path
import datetime,hashlib,importlib.util,json,os,re,stat,subprocess,sys,time,traceback
w=Path('/var/tmp/crg-final1615-tools-20261115');raw=(w/'plan.json').read_bytes();plan=json.loads(raw);sha=lambda b:hashlib.sha256(b).hexdigest();plan_sha=sha(raw);root=Path(plan['output']);assert root==Path('/var/tmp/crg-final1615-results-20261115') and not root.exists();os.umask(0o077)
for name,want in plan['source_sha256'].items():assert sha((w/name).read_bytes())==want
prior=plan['previous_full600'];pw=Path(prior['tools']);pr=Path(prior['output']);previous_raw=(pr/'report.json').read_bytes();previous=json.loads(previous_raw);terminal=json.loads((pw/'exit.json').read_bytes());assert sha(previous_raw)==prior['report_sha256'] and previous['phase']=='passed' and terminal['exit']==0 and terminal['artifact_index_complete'] and terminal['job_sha256']==prior['job_sha256'] and terminal['plan_sha256']==prior['plan_sha256']
def prior_absent(row):
 try:return int(Path('/proc',str(row['pid']),'stat').read_bytes().rsplit(b')',1)[1].split()[19])!=row['start_ticks']
 except (FileNotFoundError,ProcessLookupError):return True
assert prior_absent(json.loads((pw/'launch.json').read_bytes()));registered=0
for row in previous['roles'].values():
 assert row['phase']=='passed' and row['recorded_checks']==row['passed_checks']==10 and prior_absent(row['driver'])
 for record in row['cleanup']:
  identity=record['identity'];assert not Path(identity['group']).exists() and not Path(identity['pod_parent']).exists() and all(prior_absent(p) for p in identity['processes']+record['additional_processes']);registered+=len(identity['processes'])+len(record['additional_processes'])
for ns in prior['namespaces'].values():
 q=subprocess.run(['kubectl','get','namespace',ns,'--ignore-not-found','--request-timeout=8s','-o','json'],capture_output=True,text=True,timeout=12,check=True);assert not q.stdout.strip() and not q.stderr
assert registered==prior['registered_process_instances_absent']==71

over=plan['required_final_overhead'];ow=Path(over['tools']);raw=(Path(over['output'])/'report.json').read_bytes();r=json.loads(raw);assert sha(raw)==over['report_sha256'] and sha((ow/'overhead-plan.json').read_bytes())==over['plan_sha256'] and sha((ow/'overhead-job.py').read_bytes())==over['job_sha256'];assert r['phase']=='passed' and r['measurement_elapsed_seconds']>=1800 and json.loads((ow/'exit.json').read_bytes())['exit']==0 and prior_absent(json.loads((ow/'launch.json').read_bytes())) and prior_absent(json.loads((ow/'worker.json').read_bytes()))
for row in r['cases'].values():
 identity=row['fixture_identity'];assert row['passed'] and len(row['samples'])==181 and prior_absent(identity['main']) and prior_absent(identity['Agent']) and not Path(identity['group']).exists() and not Path(identity['pod_parent']).exists()
q=subprocess.run(['kubectl','get','namespace',over['namespace'],'--ignore-not-found','--request-timeout=5s','-o','json'],capture_output=True,text=True,timeout=8,check=True);assert not q.stdout.strip() and not q.stderr
assert not Path('/var/tmp/crg-final1396-results-20261115').exists()
for proc in Path('/proc').glob('[0-9]*'):
 try:
  args=(proc/'cmdline').read_bytes().split(bytes([0]));assert not any(arg.startswith(b'/var/tmp/crg-final') and arg.endswith((b'/business-driver.py',b'/maintenance-business.py',b'/vendor-soak-campaign.py')) for arg in args),'other final business measurement still live'
 except (FileNotFoundError,ProcessLookupError):pass

prior=plan['previous_binary_maintenance'];pw=Path(prior['tools']);pr=Path(prior['output']);raw=(pr/'report.json').read_bytes();report=json.loads(raw);term=json.loads((pw/'exit.json').read_bytes());assert sha(raw)==prior['report_sha256'] and report['phase']=='passed' and term['exit']==0 and term['artifact_index_complete'] and term['job_sha256']==prior['job_sha256'] and term['plan_sha256']==prior['plan_sha256'] and prior_absent(json.loads((pw/'launch.json').read_bytes()));maintenance_registered=0
for row in report['roles'].values():
 assert row['recorded_checks']==row['passed_checks']==20 and row['phase']=='passed' and prior_absent(row['driver'])
 for record in row['cleanup']:
  identity=record['identity'];assert not Path(identity['group']).exists() and not Path(identity['pod_parent']).exists() and all(prior_absent(p) for p in identity['processes']);maintenance_registered+=len(identity['processes'])
assert maintenance_registered==prior['registered_process_instances_absent']==64
for ns in prior['namespaces'].values():
 p=subprocess.run(['kubectl','get','namespace',ns,'--ignore-not-found','--request-timeout=8s','-o','json'],capture_output=True,text=True,timeout=12,check=True);assert not p.stdout.strip() and not p.stderr
prior=plan['previous_CLI_supervisor'];pw=Path(prior['tools']);pr=Path(prior['output']);raw=(pr/'report.json').read_bytes();report=json.loads(raw);term=json.loads((pw/'exit.json').read_bytes());assert sha(raw)==prior['report_sha256'] and report['phase']=='passed' and term['exit']==0 and term['artifact_index_complete'] and term['job_sha256']==prior['job_sha256'] and term['plan_sha256']==prior['plan_sha256'] and prior_absent(json.loads((pw/'launch.json').read_bytes()));output_registered=0
for row in report['roles'].values():
 assert row['recorded_checks']==row['passed_checks']==13 and row['phase']=='passed' and prior_absent(row['driver'])
 for record in row['cleanup']:
  identity=record['identity'];assert not Path(identity['group']).exists() and not Path(identity['pod_parent']).exists() and all(prior_absent(p) for p in identity['processes']);output_registered+=len(identity['processes'])
assert output_registered==prior['registered_process_instances_absent']==55
for ns in prior['namespaces'].values():
 p=subprocess.run(['kubectl','get','namespace',ns,'--ignore-not-found','--request-timeout=8s','-o','json'],capture_output=True,text=True,timeout=12,check=True);assert not p.stdout.strip() and not p.stderr
prior=plan['previous_failed_output'];pw=Path(prior['tools']);pr=Path(prior['output']);raw=(pr/'report.json').read_bytes();report=json.loads(raw);term=json.loads((pw/'exit.json').read_bytes());assert sha(raw)==prior['report_sha256'] and report['phase']=='failed' and term['exit']==1 and term['artifact_index_complete'] and term['job_sha256']==prior['job_sha256'] and term['plan_sha256']==prior['plan_sha256'] and prior_absent(json.loads((pw/'launch.json').read_bytes()));failed_output_registered=0
for row in report['roles'].values():
 assert row['recorded_checks']==row['passed_checks']==8 and row['phase']=='failed' and prior_absent(row['driver'])
 for record in row['cleanup']:
  identity=record['identity'];assert not Path(identity['group']).exists() and not Path(identity['pod_parent']).exists() and all(prior_absent(p) for p in identity['processes']);failed_output_registered+=len(identity['processes'])
assert failed_output_registered==prior['registered_process_instances_absent']==56
for ns in prior['namespaces'].values():
 p=subprocess.run(['kubectl','get','namespace',ns,'--ignore-not-found','--request-timeout=8s','-o','json'],capture_output=True,text=True,timeout=12,check=True);assert not p.stdout.strip() and not p.stderr

# Re-evaluate the exact frozen admission immediately before creating any fixture.
admission_process=subprocess.run([sys.executable,str(w/'tests/node-admission.py'),str(w/'plan.json')],capture_output=True,text=True,timeout=40,check=True);assert not admission_process.stderr;node_admission=json.loads(admission_process.stdout);assert node_admission['admitted'] and node_admission['fixtures_created']==False
early=plan['previous_early_output'];early_tools=Path(early['tools']);early_raw=(Path(early['output'])/'report.json').read_bytes();early_report=json.loads(early_raw);early_exit=json.loads((early_tools/'exit.json').read_bytes());assert sha(early_raw)==early['report_sha256'] and early_report['phase']=='failed' and early_exit['exit']==1 and early_exit['artifact_index_complete'] and early_exit['job_sha256']==early['job_sha256'] and early_exit['plan_sha256']==early['plan_sha256'];assert prior_absent(json.loads((early_tools/'launch.json').read_bytes()))
for row in early_report['roles'].values():assert prior_absent(row['driver']) and row['recorded_checks']==0
for ns in early['namespaces'].values():
 p=subprocess.run(['kubectl','get','namespace',ns,'--ignore-not-found','--request-timeout=8s','-o','json'],capture_output=True,text=True,timeout=12,check=True);assert not p.stdout.strip() and not p.stderr
sandboxes=json.loads(subprocess.run(['crictl','pods','-o','json'],capture_output=True,text=True,timeout=12,check=True).stdout);assert not any(v['id']==early['sandbox_id'] or v.get('metadata',{}).get('uid')==early['Pod_UID'] for v in sandboxes.get('items',[]))
assert not any(early['Pod_UID'] in str(p) or early['Pod_UID'].replace('-','_') in str(p) for p in Path('/sys/fs/cgroup').rglob('*'))
root.mkdir(mode=0o700);out={'schema':'crg-manual64-memory-high-coordinator-v1','phase':'running','plan_sha256':plan_sha,'job_sha256':plan['job_sha256'],'started_epoch':time.time(),'roles':{},'errors':[],'no_other_fixture_restart_or_resource_mutation':True}
def save():(root/'report.json').write_text(json.dumps(out,indent=2)+'\n')
def original_absent(row):
    p=Path('/proc',str(row['pid']),'stat');return not p.exists() or int(p.read_bytes().rsplit(b')',1)[1].split()[19])!=row['start_ticks']
def namespace_absent(ns):
    q=subprocess.run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json'],capture_output=True,text=True,timeout=15,check=True);assert not q.stderr;return not q.stdout.strip()
try:
    for role in ['dbs','hisdbs']:
        assert namespace_absent(plan['namespaces'][role]);row={'phase':'starting'};out['roles'][role]=row;out['phase']='testing-'+role;save()
        with (root/(role+'-driver.log')).open('xb') as log:
            child=subprocess.Popen([sys.executable,'-B',str(w/'maintenance-business.py'),role],stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=dict(os.environ,CRG_FINAL1615_BUSINESS='authorized-disposable-test-node-only'))
            row['driver']={'pid':child.pid,'start_ticks':int(Path('/proc',str(child.pid),'stat').read_bytes().rsplit(b')',1)[1].split()[19]),'entry':str(w/'maintenance-business.py'),'role':role};save();row['exit']=child.wait()
        row['driver_original_absent']=original_absent(row['driver']);row['namespace_absent']=namespace_absent(plan['namespaces'][role]);row['phase']='failed'
        report_path=root/role/'report.json'
        if report_path.exists():
            rr=report_path.read_bytes();assert len(rr)<=8*1024*1024;report=json.loads(rr);row['report_sha256']=sha(rr);row['recorded_checks']=len(report['tests']);row['passed_checks']=sum(v['passed'] for v in report['tests']);row['original_phase']=report['phase'];row['cases']=report['roles'];row['cleanup']=[]
            for case in report['roles'].values():
                identity=case.get('fixture_identity',{});leaf=Path(identity['group']) if 'group' in identity else None;cleanup={'identity':identity,'leaf_absent':leaf is not None and not leaf.exists(),'parent_absent':leaf is not None and not leaf.parent.exists(),'registered_processes_absent':all(original_absent(v) for v in identity.get('processes',[])),'has_recorded_processes':bool(identity.get('processes'))};row['cleanup'].append(cleanup)
            row['phase']='passed' if row['exit']==0 and report['phase']=='passed' and row['recorded_checks']==row['passed_checks']==plan['planned_checks_each_role'] else 'failed'
        save()
        assert row['driver_original_absent'] and row['namespace_absent'],'PREVIOUS_ROLE_NOT_TERMINAL_AND_CLEAN'
        assert len(row.get('cleanup',[]))==1 and all(v['leaf_absent'] and v['parent_absent'] and v['registered_processes_absent'] and v['has_recorded_processes'] for v in row['cleanup']),'PREVIOUS_ROLE_CLEANUP_UNPROVEN_NO_NEXT_FIXTURE'
    out['phase']='passed' if len(out['roles'])==2 and all(v['phase']=='passed' for v in out['roles'].values()) else 'failed'
except BaseException as exc:
    out['phase']='failed';out['errors'].append({'class':type(exc).__name__,'traceback':traceback.format_exc()})
finally:
    out['ended_epoch']=time.time();save()
export=root/'export';export.mkdir(mode=0o700);copied=[];missing=[]
def copy(source,name):
    if not source.exists() and not source.is_symlink():missing.append({'source':str(source.relative_to(root)),'export_name':name});return
    st=source.lstat();assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_size<=33554432
    fd=os.open(str(source),os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
    with os.fdopen(fd,'rb') as stream:
        opened=os.fstat(stream.fileno());assert (opened.st_dev,opened.st_ino)==(st.st_dev,st.st_ino);data=stream.read(33554433)
    after=source.lstat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) and len(data)==st.st_size;data.decode()
    with (export/name).open('xb') as dest:dest.write(data)
    copied.append({'source':str(source.relative_to(root)),'filename':name,'bytes':len(data),'sha256':sha(data)})
copy(root/'report.json','coordinator-report.json')
for role in ['dbs','hisdbs']:
    case=root/role/('output1615-'+role+'-manual64');folder=case/(role+'-business')
    for source,name in [(root/(role+'-driver.log'),role+'-driver.log'),(root/role/'report.json',role+'-report.json'),(root/role/('output1615-'+role+'-manual64-native.log'),role+'-native.log'),(folder/'postgresql/basebackup'/('crg-soak-'+plan['run_ids'][role])/'load.json',role+'-native.json'),(folder/'crg-config/config.json',role+'-config.json'),(folder/'resource-state/status.json',role+'-resource-status.json'),(folder/'resource-state/journal.json',role+'-resource-journal.json')]:copy(source,name)
    copy(folder/'crg-config/io-profile.json',role+'-io-profile.json')
    for i,path in enumerate(sorted((folder/'log/crg').glob('crg-*.log'))):
        assert i<3 and re.fullmatch(r'crg-[0-9]{4}-[0-9]{2}-[0-9]{2}\.log',path.name);copy(path,role+'-daily-'+str(i)+'.log')
(export/'source-map.json').write_text(json.dumps({'copied':copied,'missing':missing,'no_private_Pod_or_env_or_postgres_credentials_exported':True},indent=2)+'\n')
spec=importlib.util.spec_from_file_location('qualified_artifact_transfer',w/'artifact-transfer.py');transfer=importlib.util.module_from_spec(spec);spec.loader.exec_module(transfer);index=transfer.index_directory(plan['job_sha256'],plan_sha);(w/'artifact-index.json').write_text(json.dumps(index,indent=2)+'\n')
terminal={'exit':0 if out['phase']=='passed' else 1,'phase':out['phase'],'job_sha256':plan['job_sha256'],'plan_sha256':plan_sha,'artifact_index_complete':True,'started_epoch':out['started_epoch'],'ended_epoch':time.time()};(w/'exit.json').write_text(json.dumps(terminal,indent=2)+'\n');print(json.dumps(terminal));raise SystemExit(terminal['exit'])
