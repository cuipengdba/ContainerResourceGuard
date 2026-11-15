from pathlib import Path
import datetime,hashlib,json,shutil,subprocess,time
w=Path('/var/tmp/crg-final1525-tools-20261115');root=Path('/var/tmp/crg-final1525-results-20261115');sha=lambda raw:hashlib.sha256(raw).hexdigest();praw=(w/'plan.json').read_bytes();plan=json.loads(praw);assert sha(praw)=='6b2a9f475eb68f1d8f64e6a949e96fa489ee7293029863c35d9fbbf8dae52759';assert {k:sha((w/k).read_bytes()) for k in plan['source_sha256']}==plan['source_sha256']
def proc(v):
    p=Path('/proc',str(v['pid']),'stat')
    try:
        fields=p.read_bytes().rsplit(b')',1)[1].split();absent=int(fields[19])!=v['start_ticks'];return dict(v,original_absent=absent,state=fields[0].decode(),expected_entry_matches=None if absent or not v.get('entry') else v['entry'].encode() in (p.parent/'cmdline').read_bytes().split(bytes([0])))
    except (FileNotFoundError,ProcessLookupError):return dict(v,original_absent=True)
read_retries=[]
def read_report(path):
    for attempt in range(20):
        raw=path.read_bytes();assert len(raw)<=8*1024*1024
        try:
            value=json.loads(raw)
            if raw==path.read_bytes():return raw,value
        except json.JSONDecodeError:pass
        read_retries.append({'path':str(path.relative_to(root)),'attempt':attempt+1});time.sleep(.05)
    raise RuntimeError('read-only report not stable after bounded one-second observation')
out={'node_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'processes':{},'node_available_memory_bytes':int(next(v.split()[1] for v in Path('/proc/meminfo').read_text().splitlines() if v.startswith('MemAvailable:')))*1024,'node_free_disk_bytes':shutil.disk_usage('/var/tmp').free,'phase':'no-report-yet','job_sha256':plan['job_sha256'],'plan_sha256':sha(praw)}
if (w/'launch.json').exists():out['processes']['launch']=proc(json.loads((w/'launch.json').read_bytes()))
if (root/'report.json').exists():
    raw,report=read_report(root/'report.json');out.update(phase=report['phase'],coordinator_report_sha256=sha(raw),coordinator_report=report)
    for role,row in report['roles'].items():
        if 'driver' in row:out['processes'][role+'-driver']=proc(row['driver'])
out['roles']={}
for role in ['dbs','hisdbs']:
    role_root=root/role;key='cli1525-'+role+'-manual64';p=role_root/'report.json'
    if p.exists():
        raw,v=read_report(p);item=v['roles'].get(key,{});value={'phase':v['phase'],'checks':v['tests'],'error':v.get('error'),'case_phase':item.get('phase'),'case_error':item.get('error'),'first_pg_ready_seconds':item.get('first_pg_ready_seconds'),'first_api_ready_seconds':item.get('first_api_ready_seconds'),'ready_and_managed_seconds':item.get('ready_and_managed_seconds'),'actual_three_controls':item.get('actual_three_controls'),'profile':item.get('profile'),'automatic_io':item.get('automatic_io'),'fixture_identity':item.get('fixture_identity'),'pod_delete_command':item.get('pod_delete_command'),'namespace_absent':v.get('namespace_absent')}
        value.update(CLI_commands=len(item.get('cli_supervisor_commands',[])),CLI_subchecks=len(item.get('cli_supervisor_checks',[])),CLI_subchecks_passed=sum(v['passed'] for v in item.get('cli_supervisor_checks',[])),CLI_status_observations=len(item.get('cli_status_observations',[])),natural_age_wait=item.get('natural_age_wait'));value['maintenance_commands']=len(item.get('maintenance_intervals',[]));value['writer_snapshots']=len(item.get('writer_snapshots',[]));value['last_resume_error']=item.get('last_resume_error')
        load=role_root/key/(role+'-business')/'postgresql/basebackup'/('crg-soak-'+plan['run_ids'][role])/'load.json'
        if load.exists():
            raw=load.read_bytes();assert len(raw)<=8*1024*1024;n=json.loads(raw);value['native']={k:n.get(k) for k in ['phase','elapsed_seconds','requested_duration_seconds','sql','api','interrupted','threads_stopped']}
        out['roles'][role]=value
if (w/'exit.json').exists():
    raw=(w/'exit.json').read_bytes();assert len(raw)<=16384;out['exit']=json.loads(raw);out['exit_sha256']=sha(raw)
if (w/'artifact-index.json').exists():
    raw=(w/'artifact-index.json').read_bytes();assert len(raw)<=65536;out.update(artifact_index_utf8=raw.decode(),artifact_index=json.loads(raw),artifact_index_sha256=sha(raw))
if out.get('exit') is not None and all(v['original_absent'] for v in out['processes'].values()):
    out['independent_cleanup']={}
    for role,row in out.get('coordinator_report',{}).get('roles',{}).items():
        ns=plan['namespaces'][role];q=subprocess.run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json'],capture_output=True,text=True,timeout=10,check=True);assert not q.stderr;parts=[]
        for v in row.get('cleanup',[]):
            identity=v['identity'];leaf=Path(identity['group']);parts.append({'leaf_absent':not leaf.exists(),'parent_absent':not leaf.parent.exists(),'processes':[proc(p) for p in identity.get('processes',[])]})
        out['independent_cleanup'][role]={'namespace_absent':not q.stdout.strip(),'fixtures':parts}
if out.get('exit') is not None:
    co=out['coordinator_report'];term=out['exit'];assert term['phase']==co['phase'] and term['exit']==(0 if co['phase']=='passed' else 1) and term['job_sha256']==co['job_sha256']==plan['job_sha256'] and term['plan_sha256']==co['plan_sha256']==sha(praw)
    clean=out.get('independent_cleanup',{})
    out['registered_process_instances_absent']=sum(len(r['processes']) for v in clean.values() for r in v['fixtures'])
    out['independent_cleanup_complete']=len(clean)==len(co['roles']) and all(v['namespace_absent'] and v['fixtures'] and all(r['leaf_absent'] and r['parent_absent'] and r['processes'] and all(p['original_absent'] for p in r['processes']) for r in v['fixtures']) for v in clean.values()) and all(v['original_absent'] for v in out['processes'].values())
out['read_only_report_retries']=read_retries;out['summary']={k:out.get(k) for k in ['node_utc','phase','processes','exit','independent_cleanup_complete','registered_process_instances_absent']};out['summary']['roles']={role:{**{k:v.get(k) for k in ['phase','error','case_phase','case_error','maintenance_commands','writer_snapshots','CLI_commands','CLI_subchecks','CLI_subchecks_passed','CLI_status_observations','natural_age_wait']},'checks':len(v['checks']),'passed_checks':sum(x['passed'] for x in v['checks']),'native':v.get('native')} for role,v in out['roles'].items()};print(json.dumps(out))
