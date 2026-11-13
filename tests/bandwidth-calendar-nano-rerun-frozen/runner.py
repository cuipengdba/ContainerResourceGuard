from pathlib import Path
import hashlib,importlib.util,json,os,stat,subprocess,sys,time,traceback

w=Path('/var/tmp/crg-bandwidth1190-tools-20261114');raw=(w/'plan.json').read_bytes();plan=json.loads(raw);sha=lambda value:hashlib.sha256(value).hexdigest();root=Path(plan['output']);assert root==Path('/var/tmp/crg-bandwidth1190-results-20261114') and not root.exists();os.umask(0o077)
for name,h in plan['source_sha256'].items():assert sha((w/name).read_bytes())==h
root.mkdir(mode=0o700);out={'schema':'crg-new-bandwidth-default-percent-matrix-v1','phase':'preflight','job_sha256':plan['job_sha256'],'plan_sha256':sha(raw),'started_epoch':time.time(),'cases':{},'errors':[],'default_resource_policy_changed':True,'not_original_failed_job_relabel':True,'new_source_percentage_matrix':True}

def save():(root/'report.json').write_text(json.dumps(out,indent=2)+'\n')

def absent(row):
    try:fields=Path('/proc',str(row['pid']),'stat').read_bytes().rsplit(b')',1)[1].split();return int(fields[19])!=row['start_ticks']
    except (FileNotFoundError,ProcessLookupError):return True

def identity(child,entry):return {'pid':child.pid,'start_ticks':int(Path('/proc',str(child.pid),'stat').read_bytes().rsplit(b')',1)[1].split()[19]),'entry':str(entry)}

def namespace_absent(name):
    q=subprocess.run(['kubectl','get','namespace',name,'--ignore-not-found','-o','json'],capture_output=True,text=True,timeout=15,check=True);assert not q.stderr;return not q.stdout.strip()

def cleanup_rows(report):
    rows=[]
    for item in report.get('roles',{}).values():
        for start in item['starts']:
            if start.get('group'):
                rows.append({k:start.get(k) for k in ['pod_uid','group','pod_parent','processes']})
    return rows

def cleanup_passed(rows):return bool(rows) and all(not Path(v['group']).exists() and not Path(v['pod_parent']).exists() and v['processes'] and all(absent(p) for p in v['processes']) for v in rows)

try:
    prior=plan['previous_diagnostic'];prior_tools=Path(prior['tools']);prior_raw=(Path(prior['output'])/'report.json').read_bytes();previous=json.loads(prior_raw);terminal=json.loads((prior_tools/'exit.json').read_bytes())
    assert sha(prior_raw)==prior['report_sha256'] and previous['phase']=='failed' and terminal['phase']=='failed' and terminal['exit']==1 and terminal['artifact_index_complete'] and terminal['job_sha256']==prior['job_sha256'] and terminal['plan_sha256']==prior['plan_sha256']
    assert absent(json.loads((prior_tools/'launch.json').read_bytes()))  and all(namespace_absent(ns) for ns in prior['namespaces'].values())
    count=0
    for value in previous['cases'].values():
        assert absent(value['driver']) and cleanup_passed(value['cleanup'])
        count+=sum(len(v['processes']) for v in value['cleanup'])
    assert count==31;out['previous1170_exact_terminal_and_later_cleanup']={'report_sha256':sha(prior_raw),'registered_instances_absent':count,'original_failure_unchanged':True}
    regression=subprocess.run([sys.executable,'-B',str(w/'daily-log-checks.py')],capture_output=True,text=True,timeout=15,check=True);assert not regression.stderr;out['daily_log_regression']=json.loads(regression.stdout);assert out['daily_log_regression']['count']==18 and out['daily_log_regression']['native_permissions_checked']
    spec=importlib.util.spec_from_file_location('backup_gate',w/'backup-gate.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate);out['same_original_long_gate']=gate.snapshot(plan);assert out['same_original_long_gate']['gate_passed'];assert all(namespace_absent(ns) for ns in plan['namespaces'].values());save()
    for case in plan['cases']:
        if out['cases'] and not all(v['driver_original_absent'] and v['namespace_absent'] and cleanup_passed(v['cleanup']) for v in out['cases'].values()):raise RuntimeError('PREVIOUS_MANUAL_CASE_NOT_TERMINAL_AND_CLEAN')
        role,arm=case.split('-');out['phase']='measuring-'+case;save()
        with (root/(case+'-driver.log')).open('xb') as log:
            child=subprocess.Popen([sys.executable,'-B',str(w/'startup-matrix-driver.py'),role,arm],stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=dict(os.environ,CRG_BANDWIDTH1190='authorized-disposable-test-node-only'));row={'phase':'running','driver':identity(child,w/'startup-matrix-driver.py')};out['cases'][case]=row;save()
            try:row['exit']=child.wait(timeout=plan['criteria']['case_outer_containment_seconds'])
            except subprocess.TimeoutExpired:
                row['outer_containment_timeout']=True;save();child.terminate();row['exit']=child.wait(timeout=180)
        row.update(driver_original_absent=absent(row['driver']),namespace_absent=namespace_absent(plan['namespaces'][case]),phase='failed',cleanup=[])
        path=root/case/'report.json'
        if path.exists():
            rr=path.read_bytes();assert len(rr)<=8*1024**2;report=json.loads(rr);row.update(report_sha256=sha(rr),recorded_checks=len(report['tests']),passed_checks=sum(v['passed'] for v in report['tests']),original_phase=report['phase'],cleanup=cleanup_rows(report))
            row['phase']='passed' if row['exit']==0 and report['phase']=='passed' and row['recorded_checks']==row['passed_checks']==36 and row['namespace_absent'] and row['driver_original_absent'] and cleanup_passed(row['cleanup']) and not row.get('outer_containment_timeout') else 'failed'
        save()
    out['phase']='passed' if set(out['cases'])==set(plan['cases']) and all(v['phase']=='passed' for v in out['cases'].values()) else 'failed'
except BaseException as error:out['phase']='failed';out['errors'].append({'class':type(error).__name__,'traceback':traceback.format_exc()})
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

copy(root/'report.json','coordinator-report.json')
for case in out['cases']:
    role,arm=case.split('-');copy(root/(case+'-driver.log'),case+'-driver.log');copy(root/case/'report.json',case+'-report.json');folder=root/case/('preview5-'+role+'-percent'+arm+'-startup')/(role+'-business')
    copy(folder/'crg-config/config.json',case+'-config.json')
    copy(folder/'crg-config/io-profile.json',case+'-io-profile.json')
    for i,path in enumerate(sorted((folder/'log/crg').glob('crg-*.log'))):
        assert i<3;copy(path,case+'-daily-'+str(i)+'.log')
(export/'source-map.json').write_text(json.dumps({'copied':copied,'missing':missing,'no_business_credentials_or_config_exported':True},indent=2)+'\n')
spec=importlib.util.spec_from_file_location('transfer',w/'artifact-transfer.py');transfer=importlib.util.module_from_spec(spec);spec.loader.exec_module(transfer);index=transfer.index_directory(plan['job_sha256'],sha(raw));(w/'artifact-index.json').write_text(json.dumps(index,indent=2)+'\n')
terminal={'exit':0 if out['phase']=='passed' else 1,'phase':out['phase'],'job_sha256':plan['job_sha256'],'plan_sha256':sha(raw),'artifact_index_complete':True,'started_epoch':out['started_epoch'],'ended_epoch':time.time()};(w/'exit.json').write_text(json.dumps(terminal,indent=2)+'\n');print(json.dumps(terminal));raise SystemExit(terminal['exit'])
