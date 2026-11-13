from pathlib import Path
import hashlib,importlib.util,json,os,re,stat,subprocess,sys,time,traceback
w=Path('/var/tmp/crg-startup1008-tools-20261113');raw=(w/'plan.json').read_bytes();plan=json.loads(raw);sha=lambda data:hashlib.sha256(data).hexdigest();plan_sha=sha(raw);root=Path(plan['output']);assert root==Path('/var/tmp/crg-startup1008-results-20261113') and not root.exists();os.umask(0o077)
for name,digest in plan['source_sha256'].items():assert sha((w/name).read_bytes())==digest
root.mkdir(mode=0o700);out={'schema':'crg-high-percent-startup-matrix-coordinator-v1','phase':'waiting-for-original-long-backup','plan_sha256':plan_sha,'job_sha256':plan['job_sha256'],'started_epoch':time.time(),'cases':{},'errors':[],'gate_samples':[],'no_prior_fixture_restart_or_resource_mutation':True}
def save():(root/'report.json').write_text(json.dumps(out,indent=2)+'\n')
def original_absent(row):
    p=Path('/proc',str(row['pid']),'stat');return not p.exists() or int(p.read_bytes().rsplit(b')',1)[1].split()[19])!=row['start_ticks']
def namespace_absent(ns):
    q=subprocess.run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json'],capture_output=True,text=True,timeout=15,check=True);assert not q.stderr;return not q.stdout.strip()
try:
    spec=importlib.util.spec_from_file_location('backup_gate',w/'backup-gate.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate);deadline=time.monotonic()+plan['long576_wait_gate']['maximum_wait_seconds']
    while time.monotonic()<deadline:
        snapshot=gate.snapshot(plan);out['gate_samples'].append(snapshot);save()
        if snapshot['gate_passed']:out['passed_gate']=snapshot;break
        time.sleep(min(plan['long576_wait_gate']['poll_seconds'],max(0,deadline-time.monotonic())))
    else:raise RuntimeError('ORIGINAL_BACKUP_GATE_WAIT_EXPIRED_NO_FIXTURE_CREATED')
    for case_name in plan['cases']:
        role,pct=case_name.split('-');assert namespace_absent(plan['namespaces'][case_name]);row={'phase':'starting'};out['cases'][case_name]=row;out['phase']='testing-'+case_name;save()
        with (root/(case_name+'-driver.log')).open('xb') as log:
            child=subprocess.Popen([sys.executable,'-B',str(w/'startup-matrix-driver.py'),role,pct],stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=dict(os.environ,CRG_STARTUP1008='authorized-disposable-test-node-only'))
            row['driver']={'pid':child.pid,'start_ticks':int(Path('/proc',str(child.pid),'stat').read_bytes().rsplit(b')',1)[1].split()[19]),'entry':str(w/'startup-matrix-driver.py'),'case':case_name};save()
            try:row['exit']=child.wait(timeout=plan['criteria']['case_outer_containment_seconds'])
            except subprocess.TimeoutExpired:
                row['outer_containment_timeout']=True;save();child.terminate()
                try:row['exit']=child.wait(timeout=180)
                except subprocess.TimeoutExpired:raise RuntimeError('OWN_DRIVER_CLEANUP_NOT_TERMINAL_NO_NEXT_FIXTURE')
        row['driver_original_absent']=original_absent(row['driver']);row['namespace_absent']=namespace_absent(plan['namespaces'][case_name]);row['phase']='failed';row['cleanup']=[]
        path=root/case_name/'report.json'
        if path.exists():
            rr=path.read_bytes();assert len(rr)<=8*1024*1024;report=json.loads(rr);row.update(report_sha256=sha(rr),recorded_checks=len(report['tests']),passed_checks=sum(v['passed'] for v in report['tests']),original_phase=report['phase'])
            for item in report['roles'].values():
                for start in item['starts']:
                    leaf=Path(start['group']) if start.get('group') else None;row['cleanup'].append({'pod_uid':start.get('pod_uid'),'group':start.get('group'),'pod_parent':start.get('pod_parent'),'processes':start.get('processes',[]),'leaf_absent':leaf is not None and not leaf.exists(),'parent_absent':leaf is not None and not leaf.parent.exists(),'registered_processes_absent':all(original_absent(v) for v in start.get('processes',[])),'has_recorded_processes':bool(start.get('processes'))})
            row['phase']='passed' if row['exit']==0 and report['phase']=='passed' and row['recorded_checks']==row['passed_checks']==36 and not row.get('outer_containment_timeout') else 'failed'
        save()
        assert row['driver_original_absent'] and row['namespace_absent'],'PREVIOUS_CASE_NOT_TERMINAL_AND_CLEAN'
        assert row['cleanup'] and all(v['leaf_absent'] and v['parent_absent'] and v['registered_processes_absent'] and v['has_recorded_processes'] for v in row['cleanup']),'PREVIOUS_CASE_CLEANUP_UNPROVEN_NO_NEXT_FIXTURE'
    out['phase']='passed' if len(out['cases'])==4 and all(v['phase']=='passed' for v in out['cases'].values()) else 'failed'
except BaseException as error:out['phase']='failed';out['errors'].append({'class':type(error).__name__,'traceback':traceback.format_exc()})
finally:out['ended_epoch']=time.time();save()
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
for case_name in plan['cases']:
    role,pct=case_name.split('-');folder=root/case_name/('preview4-'+role+'-percent'+pct+'-startup')/(role+'-business')
    for source,name in [(root/(case_name+'-driver.log'),case_name+'-driver.log'),(root/case_name/'report.json',case_name+'-report.json'),(folder/'crg-config/io-profile.json',case_name+'-io-profile.json')]:copy(source,name)
    for i,path in enumerate(sorted((folder/'log/crg').glob('crg-*.log'))):
        assert i<3 and re.fullmatch(r'crg-[0-9]{4}-[0-9]{2}-[0-9]{2}\.log',path.name);copy(path,case_name+'-daily-'+str(i)+'.log')
(export/'source-map.json').write_text(json.dumps({'copied':copied,'missing':missing,'no_private_Pod_or_env_or_postgres_credentials_exported':True},indent=2)+'\n')
spec=importlib.util.spec_from_file_location('qualified_artifact_transfer',w/'artifact-transfer.py');transfer=importlib.util.module_from_spec(spec);spec.loader.exec_module(transfer);index=transfer.index_directory(plan['job_sha256'],plan_sha);(w/'artifact-index.json').write_text(json.dumps(index,indent=2)+'\n')
terminal={'exit':0 if out['phase']=='passed' else 1,'phase':out['phase'],'job_sha256':plan['job_sha256'],'plan_sha256':plan_sha,'artifact_index_complete':True,'started_epoch':out['started_epoch'],'ended_epoch':time.time()};(w/'exit.json').write_text(json.dumps(terminal,indent=2)+'\n');print(json.dumps(terminal));raise SystemExit(terminal['exit'])
