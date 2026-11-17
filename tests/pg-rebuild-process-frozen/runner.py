from pathlib import Path
import hashlib,importlib.util,json,os,stat,subprocess,sys,time,traceback
w=Path('/var/tmp/crg-rebuild1060-tools-20261113');raw=(w/'plan.json').read_bytes();plan=json.loads(raw);sha=lambda value:hashlib.sha256(value).hexdigest();root=Path(plan['output']);assert root==Path('/var/tmp/crg-rebuild1060-results-20261113') and not root.exists() and plan['cases']==['dbs-20'];os.umask(0o077)
for name,h in plan['source_sha256'].items():assert sha((w/name).read_bytes())==h
root.mkdir(mode=0o700);out={'schema':'crg-single-rebuild-PG-process-diagnostic-v1','phase':'preflight','job_sha256':plan['job_sha256'],'plan_sha256':sha(raw),'started_epoch':time.time(),'cases':{},'errors':[],'diagnostic_not_original_four_cell_acceptance':True};observer=None
def save():(root/'report.json').write_text(json.dumps(out,indent=2)+'\n')
def absent(row):
    try:fields=Path('/proc',str(row['pid']),'stat').read_bytes().rsplit(b')',1)[1].split();return int(fields[19])!=row['start_ticks']
    except (FileNotFoundError,ProcessLookupError):return True
def identity(child,entry):return {'pid':child.pid,'start_ticks':int(Path('/proc',str(child.pid),'stat').read_bytes().rsplit(b')',1)[1].split()[19]),'entry':str(entry)}
def namespace_absent(name):
    q=subprocess.run(['kubectl','get','namespace',name,'--ignore-not-found','-o','json'],capture_output=True,text=True,timeout=15,check=True);assert not q.stderr;return not q.stdout.strip()
try:
    previous=plan['previous_startup_attempt'];prior_root=Path(previous['output']);prior_tools=Path(previous['tools']);prior_raw=(prior_root/'report.json').read_bytes();prior=json.loads(prior_raw);terminal=json.loads((prior_tools/'exit.json').read_bytes());assert sha(prior_raw)==previous['report_sha256'] and prior['phase']=='failed' and set(prior['cases'])=={'dbs-20','hisdbs-20'} and terminal['phase']=='failed' and terminal['exit']==1 and terminal['artifact_index_complete'] and terminal['job_sha256']==previous['job_sha256'] and terminal['plan_sha256']==previous['plan_sha256']
    assert absent(json.loads((prior_tools/'launch.json').read_bytes())) and all(namespace_absent(ns) for ns in previous['namespaces'].values())
    count=0
    for value in prior['cases'].values():
        assert absent(value['driver']) and len(value['cleanup'])==2
        for row in value['cleanup']:
            assert not Path(row['group']).exists() and not Path(row['pod_parent']).exists() and row['processes'] and all(absent(p) for p in row['processes']);count+=len(row['processes'])
    assert count==107;out['previous1020_exact_terminal_and_later_cleanup']={'report_sha256':sha(prior_raw),'registered_instances_absent':count,'all_four_prior_namespaces_absent':True,'original_failures_not_changed':True}
    spec=importlib.util.spec_from_file_location('backup_gate',w/'backup-gate.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate);out['same_original_long_gate']=gate.snapshot(plan);assert out['same_original_long_gate']['gate_passed'];assert namespace_absent(plan['namespaces']['dbs-20']);save()
    with (root/'observer.log').open('xb') as log:
        observer=subprocess.Popen([sys.executable,'-B',str(w/'pg-process-observer.py'),str(w)],stdin=subprocess.DEVNULL,stdout=log,stderr=log);out['observer']=identity(observer,w/'pg-process-observer.py');save()
    with (root/'dbs-20-driver.log').open('xb') as log:
        child=subprocess.Popen([sys.executable,'-B',str(w/'startup-matrix-driver.py'),'dbs','20'],stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=dict(os.environ,CRG_REBUILD1060='authorized-disposable-test-node-only'));row={'phase':'running','driver':identity(child,w/'startup-matrix-driver.py')};out['cases']['dbs-20']=row;out['phase']='diagnosing-dbs-20';save()
        try:row['exit']=child.wait(timeout=plan['criteria']['case_outer_containment_seconds'])
        except subprocess.TimeoutExpired:
            row['outer_containment_timeout']=True;save();child.terminate();row['exit']=child.wait(timeout=180)
    row.update(driver_original_absent=absent(row['driver']),namespace_absent=namespace_absent(plan['namespaces']['dbs-20']),phase='failed',cleanup=[])
    path=root/'dbs-20/report.json'
    if path.exists():
        rr=path.read_bytes();assert len(rr)<=8*1024**2;report=json.loads(rr);row.update(report_sha256=sha(rr),recorded_checks=len(report['tests']),passed_checks=sum(v['passed'] for v in report['tests']),original_phase=report['phase'])
        for item in report['roles'].values():
            for start in item['starts']:
                row['cleanup'].append({k:start.get(k) for k in ['pod_uid','group','pod_parent','processes']})
        row['phase']='passed' if row['exit']==0 and report['phase']=='passed' and row['recorded_checks']==row['passed_checks']==36 and row['namespace_absent'] and row['driver_original_absent'] and not row.get('outer_containment_timeout') else 'failed'
    out['phase']=row['phase'];save()
except BaseException as error:out['phase']='failed';out['errors'].append({'class':type(error).__name__,'traceback':traceback.format_exc()})
finally:
    (root/'driver-terminal.json').write_text(json.dumps({'coordinator_phase':out['phase'],'epoch':time.time()})+'\n')
    if observer is not None:
        try:out['observer_exit']=observer.wait(timeout=20)
        except subprocess.TimeoutExpired:
            assert not absent(out['observer']);observer.terminate();out['observer_exit']=observer.wait(timeout=10)
        out['observer_original_absent']=absent(out['observer'])
    out['ended_epoch']=time.time();save()
export=root/'export';export.mkdir(mode=0o700);copied=[];missing=[]
def copy(source,name):
    if not source.exists() and not source.is_symlink():missing.append(name);return
    st=source.lstat();assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_size<=33554432
    fd=os.open(str(source),os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
    with os.fdopen(fd,'rb') as stream:
        opened=os.fstat(stream.fileno());assert (opened.st_dev,opened.st_ino)==(st.st_dev,st.st_ino);data=stream.read(33554433)
    after=source.lstat();assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) and len(data)==st.st_size;data.decode()
    with (export/name).open('xb') as dest:dest.write(data)
    copied.append({'filename':name,'bytes':len(data),'sha256':sha(data)})
for source,name in [(root/'report.json','coordinator-report.json'),(root/'pg-process-observer.json','pg-process-observer.json'),(root/'observer.log','observer.log'),(root/'dbs-20-driver.log','dbs-20-driver.log'),(root/'dbs-20/report.json','dbs-20-report.json')]:copy(source,name)
folder=root/'dbs-20/preview4-dbs-percent20-startup/dbs-business';copy(folder/'crg-config/io-profile.json','dbs-20-io-profile.json')
for i,path in enumerate(sorted((folder/'log/crg').glob('crg-*.log'))):
    assert i<3;copy(path,'dbs-20-daily-'+str(i)+'.log')
(export/'source-map.json').write_text(json.dumps({'copied':copied,'missing':missing,'no_business_config_cmdline_memory_or_fd_contents_exported':True},indent=2)+'\n')
spec=importlib.util.spec_from_file_location('transfer',w/'artifact-transfer.py');transfer=importlib.util.module_from_spec(spec);spec.loader.exec_module(transfer);index=transfer.index_directory(plan['job_sha256'],sha(raw));(w/'artifact-index.json').write_text(json.dumps(index,indent=2)+'\n')
terminal={'exit':0 if out['phase']=='passed' else 1,'phase':out['phase'],'job_sha256':plan['job_sha256'],'plan_sha256':sha(raw),'artifact_index_complete':True,'started_epoch':out['started_epoch'],'ended_epoch':time.time()};(w/'exit.json').write_text(json.dumps(terminal,indent=2)+'\n');print(json.dumps(terminal));raise SystemExit(terminal['exit'])
