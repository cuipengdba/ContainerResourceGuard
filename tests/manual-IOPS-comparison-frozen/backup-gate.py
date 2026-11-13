"""Read-only launch gate; never restart or change the original long-running job."""
from pathlib import Path
import hashlib,json,time

TOOLS=Path('/var/tmp/crg-high576-tools-20261112')
OUTPUT=Path('/var/tmp/crg-high576-seven-20261112')

def read_json(path):
    for attempt in range(5):
        raw=path.read_bytes()
        try:return json.loads(raw)
        except json.JSONDecodeError:
            if attempt==4:raise
            time.sleep(.1)

def live(row):
    try:
        p=Path('/proc',str(row['pid']));fields=(p/'stat').read_bytes().rsplit(b')',1)[1].split()
        return int(fields[19])==row['start_ticks'] and fields[0]!=b'Z' and row['entry'].encode() in (p/'cmdline').read_bytes().split(b'\0')
    except (FileNotFoundError,ProcessLookupError):return False

def evaluate(campaign,gate):
    if campaign.get('phase')!='measuring':raise ValueError('ORIGINAL_CAMPAIGN_NOT_MEASURING')
    found=[v for v in campaign.get('backups',[]) if v['run_id']==gate['required_successful_backup_run_id']]
    if not found:return None
    if len(found)!=1:raise ValueError('DUPLICATE_REQUIRED_BACKUP')
    row=found[0]
    if 'exit' not in row:return None
    if row['exit']!=0 or row.get('phase')!='content-passed-native-pending':raise ValueError('REQUIRED_BACKUP_FAILED')
    if row.get('offset_seconds',-1)<gate['minimum_backup_offset_seconds'] or not row.get('content_ended_epoch'):raise ValueError('REQUIRED_BACKUP_TIME_NOT_PROVEN')
    if set(row.get('roles',{}))!={'dbs','hisdbs'}:raise ValueError('REQUIRED_BACKUP_ROLES')
    for value in row['roles'].values():
        if value.get('checks')!=10 or value.get('cleanup') is not True or value.get('native_pending') is not True:raise ValueError('REQUIRED_BACKUP_NOT_COMPLETE_AND_CLEAN')
    return row

def snapshot(plan):
    gate=plan['long576_wait_gate'];launch=read_json(TOOLS/'launch.json');worker=read_json(TOOLS/'worker.json');report=read_json(OUTPUT/'report.json');campaign=read_json(OUTPUT/'campaign-acceptance/report.json')
    if launch['job_sha256']!=gate['job_sha256'] or hashlib.sha256((TOOLS/'acceptance-job.py').read_bytes()).hexdigest()!=gate['job_sha256']:raise ValueError('ORIGINAL_JOB_DIFFERENT')
    actual={'runner':launch,'worker':worker,'campaign':report['campaign_identity']}
    identities={}
    for name,row in actual.items():
        expected=gate[name]
        if any(row[k]!=expected[k] for k in ['pid','start_ticks','entry']) or not live(row):raise ValueError('ORIGINAL_PROCESS_MISSING_OR_DIFFERENT')
        identities[name]={k:row[k] for k in ['pid','start_ticks','entry']}
    if (TOOLS/'acceptance.exit.json').exists() or report.get('phase')!='seven-day-native-measurement':raise ValueError('ORIGINAL_LONG_JOB_TERMINAL')
    row=evaluate(campaign,gate)
    return {'node_epoch':time.time(),'same_original_processes':identities,'original_phase':report['phase'],'campaign_phase':campaign['phase'],'completed_backups':sum(v.get('exit')==0 for v in campaign.get('backups',[])),'required_backup':row,'gate_passed':row is not None,'not_seven_day_acceptance':True}

def previous_attempt(plan,namespace_absent,original_absent):
    prior=plan['previous_startup_attempt'];tools=Path(prior['tools']);root=Path(prior['output']);raw=(root/'report.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=prior['report_sha256']:raise ValueError('PRIOR_STARTUP_REPORT_DIFFERENT')
    report=json.loads(raw);terminal=read_json(tools/'exit.json');launch=read_json(tools/'launch.json')
    if terminal['phase']!='failed' or terminal['exit']!=1 or terminal['job_sha256']!=prior['job_sha256'] or terminal['plan_sha256']!=prior['plan_sha256'] or not terminal['artifact_index_complete']:raise ValueError('PRIOR_STARTUP_TERMINAL_NOT_PROVEN')
    if not original_absent(launch):raise ValueError('PRIOR_STARTUP_RUNNER_LIVE')
    if report['phase']!='failed' or set(report['cases'])!=set(prior['namespaces']):raise ValueError('PRIOR_STARTUP_CASES_NOT_PROVEN')
    counts={}
    for name,row in report['cases'].items():
        if not original_absent(row['driver']) or not namespace_absent(prior['namespaces'][name]):raise ValueError('PRIOR_STARTUP_CASE_LIVE')
        if row['phase']!='failed' or row['exit']!=1 or len(row['cleanup'])!=1:raise ValueError('PRIOR_STARTUP_FAILURE_OR_CLEANUP_DIFFERENT')
        for identity in row['cleanup']:
            if Path(identity['group']).exists() or Path(identity['pod_parent']).exists() or not identity['processes'] or not all(original_absent(v) for v in identity['processes']):raise ValueError('PRIOR_STARTUP_GROUP_OR_PROCESS_LIVE')
        counts[name]=sum(len(v['processes']) for v in row['cleanup'])
    return {'report_sha256':prior['report_sha256'],'all_four_prior_namespaces_groups_drivers_runner_and_registered_instances_absent':True,'registered_instances':counts,'prior_failure_not_overwritten':True}
