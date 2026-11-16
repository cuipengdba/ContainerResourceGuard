#!/usr/bin/env python3
"""Read-only source37 aged-v2 result audit. No workload or controller mutations.

Synthetic fixtures test this gate; only actual source-pinned files and a trusted
terminal receipt can qualify the real component. Overall release remains separate.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path,PurePosixPath
import re
import stat
import subprocess
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
EXECUTOR_SHA='56cdb1cd7dc289c84ae0b256f65f67a31020c9fd1e66ca5063704023465de606'
if hashlib.sha256((HERE/'executor-v2.py').read_bytes()).hexdigest()!=EXECUTOR_SHA:raise ValueError('EXACT_EXECUTOR_V2_SOURCE')
spec=importlib.util.spec_from_file_location('source37_aged_evidence_v2',HERE/'executor-v2.py')
e=importlib.util.module_from_spec(spec);sys.modules[spec.name]=e;spec.loader.exec_module(e)
gate=e.gate;require=e.require;Rejected=e.Rejected;B=e.lineage.BINDING;C=e.CONTRACT
ENTRY='/var/tmp/crg-aged1952-tools-20261116/tests/live-capacity-aged-v1/executor-v2.py'
RECEIPT='/var/tmp/crg-aged-source37-runner-v2-20261116/exit.json'
COMMANDS=['quiesce','binary-install','binary-rollback','binary-install','enable','quiesce','binary-rollback','enable']
STATES=['quiesced','installed','rolled_back','installed','enabled','quiesced','rolled_back','enabled']
SUFFIXES=['aged-reopen-original-start-and-three-controls','aged-reopen-one-current-Agent-fresh-cache-readonly-CCG',
 'aged-journal-rollover-before-data-check','actual-aged64MiB-and-final-counter-reopened','aged-schema-logical-backup-readable',
 'independent-database-restores-aged-payload-and-counter','same-data-new-Pod-original-start-and-three-controls',
 'same-data-new-Pod-one-current-Agent-fresh-cache-readonly-CCG','new-ID-journal-PG-restart-and-same-aged-data',
 'aged-state-online-install-previous-high-compatible-preview','aged-state-immediate-rollback',
 'aged-state-previous-Agent-managed-with-same-PID1-PG-cache','aged-state-current-Agent-resumed-after-rollback',
 '600s-native-and-all-eight-maintenance-intervals-covered','aged-payload-counter-after-native-maintenance',
 'disable-restores-new-runtime-originals-and-no-OOM','same-aged-directories-config-private-inputs-and-program-restored',
 'daily0600-logs-retain-original-prefixes-and-append']


def expected_checks():return [r+'-'+s for r in ['dbs','hisdbs'] for s in SUFFIXES]


def native(value,run_id):
    require(value['schema']=='crg-vendor-soak-v1' and value['phase']=='passed'
        and value['run_id']==run_id and value['test_phase']=='smoke'
        and type(value['requested_duration_seconds']) is int and value['requested_duration_seconds']==600
        and gate.audit.number(value['elapsed_seconds']) and value['elapsed_seconds']>=600
        and value['interrupted'] is False and value['threads_stopped'] is True
        and value['payload_integrity'] is True and value['primary_not_restarted'] is True
        and value['primary_start_time_initial']==value['primary_start_time_final'], 'NATIVE_COMPLETION')
    before,after=value['initial_checksum'],value['final_checksum']
    require(len(before)==len(after)==5 and before[:3]==[16384,134225920,67108864]
        and before[:4]==after[:4], 'NATIVE_PAYLOAD')
    require(value['criteria']=={'sql_period_seconds':2,'api_period_seconds':5,'maximum_seconds':5,
        'p95_upper_bound_seconds':1,'maximum_errors':0,'minimum_scheduled_samples_fraction':.98},'NATIVE_CRITERIA')
    bounds=[.001,.005,.01,.02,.05,.1,.25,.5,1,2,5,'over-5']
    require(value['latency_bucket_upper_seconds']==bounds,'NATIVE_BUCKETS')
    for kind,period in [('sql',2),('api',5)]:
        v=value[kind];n=v['attempts'];hist=v['histogram']
        require(type(n) is int and n>=600/period*.98 and type(v['successes']) is int
            and v['successes']==n and type(v['errors']) is int and v['errors']==0,'NATIVE_SAMPLES')
        require(gate.audit.number(v['max_seconds']) and 0<=v['max_seconds']<=5,'NATIVE_MAXIMUM')
        require(len(hist)==12 and all(type(x) is int and x>=0 for x in hist) and sum(hist)==n,'NATIVE_HISTOGRAM')
        cumulative=0;p95=None
        for upper,count in zip(bounds,hist):
            cumulative+=count
            if p95 is None and cumulative>=n*.95:p95=upper
        require(gate.audit.number(p95) and p95<=1 and p95==v['p95_bucket_upper_seconds'],'NATIVE_P95')
        require(gate.audit.number(v['sample_coverage']) and abs(v['sample_coverage']-n/(600/period))<1e-9,'NATIVE_COVERAGE')
    start=gate.audit.timestamp(value['started_utc']);end=gate.audit.timestamp(value['measurement_finished_utc'])
    require(end>=start,'NATIVE_WINDOW');return start,end


def managed(active,original,status,identity):
    require(set(active)==set(original)==set(gate.CONTROLS) and all(isinstance(x,str) for x in active.values()),'CONTROL_SET')
    require(original['cpu.max']=='800000 100000' and original['memory.max']=='21474836480'
        and original['memory.high']=='max' and original['io.max']=='','RUNTIME_ORIGINALS')
    require(active['cpu.max']=='720000 100000' and active['memory.high']=='20001980416'
        and re.fullmatch(r'[0-9]+:[0-9]+ rbps=67108864 wbps=67108864 riops=4096 wiops=4096',active['io.max'])
        and all(active[n]==original[n] for n in ['memory.max','memory.swap.max','pids.max','cpu.weight','io.weight']), 'MANAGED_HIGH_EXTERNAL_CONTROLS')
    items=status['items']
    require(status['state']=='managed' and status['plan']['environment']['identity']==identity
        and len(items)==3 and {i['file'] for i in items}=={'cpu.max','memory.high','io.max'}
        and all(i['state']=='applied' for i in items),'FRESH_MANAGED_STATUS')


def one_process(rows,source):
    require(len(rows)==1 and len(rows[0])==3 and type(rows[0][0]) is int and rows[0][0]>1
        and type(rows[0][1]) is int and rows[0][1]>0 and rows[0][2]==source,'UNIQUE_QUALIFIED_PROCESS')


def enforced_journal(j,identity):
    require(type(j['version']) is int and j['version']==1 and j['identity']==identity
        and len(j['mutations'])==3 and {v['file'] for v in j['mutations'].values()}=={'cpu.max','memory.high','io.max'}
        and all(not v.get('pending') and not v.get('conflict') for v in j['mutations'].values()),'ENFORCED_HIGH_JOURNAL')


def audit(report,report_digest,authority_digest,component,inputs,seal,receipt):
    require(report['schema']=='crg-source37-aged-execution-report-v2' and report['phase']=='passed'
        and report['mode']=='seven-day-postflight' and report['source_revision']==C['source_revision']
        and report['binary_sha256']==C['binary_sha256'] and report['embedded_version']=='v1.0.0'
        and report['executor_sha256']==EXECUTOR_SHA and report['contract_sha256']==e.CONTRACT_SHA
        and report['authority_sha256']==authority_digest and report['criteria']==C['criteria']
        and report['immutable_template_sha256']==C['original_template_sha256'],'REPORT_SOURCE_AND_CONTRACT')
    require(report['user_rollback_scope']==C['user_rollback_scope'] and report['original_legacy_managed_resume_accepted'] is False
        and report['maintenance_scope']==C['previous']['scope'],'USER_HIGH_ONLY_SCOPE')
    require(report['P10_complete'] is False and report['release_accepted'] is False
        and report['postflight_executed'] is True and report['namespace_absent'] is True
        and report['aged_fixture_retained'] is True and not any(report.get(k) for k in ['reason','cleanup_error','local_exec_cleanup_forced']), 'TERMINAL_AND_CLEANUP')
    require([t['name'] for t in report['tests']]==expected_checks()
        and all(t['passed'] is True for t in report['tests']),'EXACT_ORIGINAL36_CHECKS')
    require(component['phase']=='component-accepted' and report['readiness']['component']==component
        and report['readiness']['postflight_allowed'] is True
        and report['readiness']['authority_sha256']==authority_digest
        and report['readiness']['contract_sha256']==e.CONTRACT_SHA,'ORIGINAL_LONG_AND_PREFLIGHT')
    wanted={'binding_sha256':e.lineage.BINDING_SHA256,'long_plan_sha256':B['long_plan_sha256'],
        'baseline_report_sha256':component['reports']['baseline']['sha256'],
        'enforce_report_sha256':component['reports']['enforce']['sha256']}
    require(seal['schema']=='crg-aged-lineage-seal-v1' and seal['seal_is_not_acceptance'] is True
        and seal['plan_sha256']==e.lineage.BINDING_SHA256 and seal['fresh_three_phase_binding']==wanted
        and seal['launch']==inputs[1] and seal['source_revision']==C['source_revision']
        and seal['binary_sha256']==C['binary_sha256'] and set(seal['roles'])=={'dbs','hisdbs'},'ACTUAL_SEAL_BINDING')
    require(receipt['schema']=='crg-source37-aged-exit-v2' and type(receipt['exit']) is int and receipt['exit']==0
        and receipt['entry']==ENTRY and receipt['executor_sha256']==EXECUTOR_SHA
        and receipt['authority_sha256']==authority_digest and receipt['contract_sha256']==e.CONTRACT_SHA
        and receipt['report_sha256']==report_digest and type(receipt['pid']) is int and receipt['pid']>1
        and type(receipt['start_ticks']) is int and receipt['start_ticks']>0
        and gate.audit.number(receipt['elapsed_seconds']) and receipt['elapsed_seconds']>=1200, 'ACTUAL_EXIT_RECEIPT')
    ended=gate.audit.timestamp(report['ended_utc']);require(gate.audit.timestamp(receipt['ended_utc'])>=ended,'TERMINAL_RECEIPT_ORDER')
    require(set(report['roles'])=={'dbs','hisdbs'},'ROLE_SET')
    all_ids=set();all_uids=set();all_groups=set();role_summary={}
    for role in ['dbs','hisdbs']:
        item=report['roles'][role];sealed=seal['roles'][role]
        require(set(sealed['directories'])==set(gate.DIRECTORIES)
            and set(sealed['files'])==set(gate.immutable_files(role)),'SEALED_MEMBER_SET')
        require(item['phase']=='postflight-component-passed' and len(item['boots'])==2,'TWO_BOOTS')
        first,second=item['boots']
        for boot,phase in zip(item['boots'],['aged-reopen','same-data-new-Pod']):
            require(boot['phase']==phase and boot['network_isolated_before_start'] is True
                and gate.audit.number(boot['ready_seconds']) and 0<=boot['ready_seconds']<=300
                and gate.audit.number(boot['cache_after_ready_seconds']) and 0<=boot['cache_after_ready_seconds']<=45,'STARTUP_CACHE_BUDGETS')
            managed(boot['active_controls'],boot['runtime_original_controls'],boot['managed_status'],boot['identity'])
            one_process(boot['agents'],C['binary_sha256']);one_process(boot['caches'],C['cache_sha256'])
            require(isinstance(boot['pid1_start_ticks'],str) and boot['pid1_start_ticks'].isdigit()
                and int(boot['pid1_start_ticks'])>0,'PID1_IDENTITY')
            cid=boot['container_id'];uid=boot['pod_uid'];group=PurePosixPath(boot['cgroup'])
            require(re.fullmatch('[0-9a-f]{64}',cid) and re.fullmatch('[0-9a-f-]{36}',uid)
                and cid not in all_ids and uid not in all_uids and str(group) not in all_groups
                and group.is_relative_to('/sys/fs/cgroup') and group.name=='cri-containerd-'+cid+'.scope'
                and uid.replace('-','_') in group.parent.name,'NEW_POD_CONTAINER_GROUP_IDENTITIES')
            all_ids.add(cid);all_uids.add(uid);all_groups.add(str(group))
        require(first['identity']!=second['identity'] and first['identity']!=sealed['journal_identity']
            and first['primary_start']!=second['primary_start']
            and item['first_previous_journal']['identity']==sealed['journal_identity']
            and item['second_previous_journal']['identity']==first['identity'],'JOURNAL_AND_PG_ROLLOVER')
        enforced_journal(item['first_previous_journal'],sealed['journal_identity'])
        enforced_journal(item['second_previous_journal'],first['identity'])
        before=item['before'];after=item['after'];aged=inputs[3]['roles'][role]['workload']['final_checksum']
        checksum='|'.join(str(x) for x in aged)
        require(before['aged_native_final_checksum']==aged and item['aged_checksum_reopened']==checksum
            and item['aged_checksum_after_maintenance']==checksum and item['restore_evidence']['restored_checksum']==checksum
            and item['restore_evidence']['source_checksum']==checksum
            and item['restore_evidence']['database']=='crg_aged_restore_'+C['run_id'],'ACTUAL_AGED_RESTORE_AND_COUNTER')
        require(item['logical_backup']['digest']['size']>0
            and 'TABLE DATA crg_soak_'+B['seven_day_run_id']+' fixture' in item['logical_backup']['listing'],'ACTUAL_LOGICAL_BACKUP')
        require(before['directories']==sealed['directories']==after['directories']
            and before['immutable_files']==after['immutable_files']
            and before['immutable_files']=={k:v for k,v in sealed['files'].items() if k!='crg/crg'}
            and after['program_sha256']==C['binary_sha256'],'UNCHANGED_AGED_INPUTS')
        require(before['log_prefixes']==after['preserved_log_prefixes'] and len(after['log_files'])>=7
            and sum(v['size'] for v in after['log_files'].values())<=1_000_000_000
            and all(re.fullmatch(r'crg-[0-9]{4}-[0-9]{2}-[0-9]{2}\.log',n) and v['mode']==0o600 for n,v in after['log_files'].items())
            and all(n in after['log_files'] and after['log_files'][n]['size']>=v['size'] for n,v in before['log_prefixes'].items())
            and any(after['log_files'][n]['size']>v['size'] for n,v in before['log_prefixes'].items()),'DAILY_LOG_PRESERVATION')
        start,end=native(item['native'],C['run_id']+('0' if role=='dbs' else '1'))
        require(start>=second['ready_epoch'] and end<=ended
            and item['native']['primary_start_time_initial']==second['primary_start'],'NATIVE_AFTER_SECOND_BOOT')
        evidence=item['maintenance_evidence'];fixed=evidence['before'];final=evidence['after'];intervals=item['maintenance_intervals']
        require(fixed['controls']==second['active_controls'] and fixed['pid1_start_ticks']==second['pid1_start_ticks']
            and fixed['caches']==second['caches'] and fixed['primary_start']==second['primary_start']
            and fixed['aged_checksum']==checksum,'MAINTENANCE_INITIAL_IDENTITIES')
        require([x['command'] for x in intervals]==COMMANDS and len(evidence['resumptions'])==2,'EXACT_EIGHT_MAINTENANCE_OPERATIONS')
        last=start
        for i,(row,state) in enumerate(zip(intervals,STATES)):
            require(gate.audit.number(row['started_epoch']) and gate.audit.number(row['ended_epoch'])
                and last<=row['started_epoch']<=row['ended_epoch']<=end,'MAINTENANCE_INTERVAL_ORDER')
            last=row['ended_epoch']
            expected=C['previous']['sha256'] if i in [1,3,4,5] else C['binary_sha256']
            require(row['result']['state']==state and row['program_sha256']==expected
                and all(row[k]==fixed[k] for k in ['controls','journal_sha256','pid1_start_ticks','caches']),'MAINTENANCE_RAW_RESULTS')
        for row,index,expected in zip(evidence['resumptions'],[4,7],[C['previous']['sha256'],C['binary_sha256']]):
            b,a=row['status_stamp_before_enable'],row['status_stamp_after_resume'];one_process(row['agents'],expected)
            require(row['expected_sha256']==expected and b==intervals[index]['status_stamp_before_enable']
                and isinstance(b,list) and isinstance(a,list) and len(b)==len(a)==3
                and all(type(n) is int and n>0 for n in b+a) and a[1]>b[1]
                and intervals[index]['ended_epoch']<=row['observed_epoch']<=end
                and row['journal_sha256']==fixed['journal_sha256'] and row['controls']==fixed['controls'],'FRESH_RESUMPTION_EVIDENCE')
            managed(row['controls'],second['runtime_original_controls'],row['managed_status'],second['identity'])
        require(all(final[k]==fixed[k] for k in ['controls','journal_sha256','pid1_start_ticks','caches'])
            and final['memory_events']['oom_kill']=='0','MAINTENANCE_FINAL_IDENTITIES')
        disabled=item['disable_evidence'];j=disabled['journal'];s=disabled['result']
        require(s['state']=='restored' and s['mode']=='disable' and s['plan']['environment']['identity']==second['identity']
            and not s.get('error') and len(s['items'])==3 and {x['file'] for x in s['items']}=={'cpu.max','memory.high','io.max'}
            and all(x['state']=='restored' for x in s['items'])
            and disabled['actual_controls']==second['runtime_original_controls'] and disabled['memory_events']['oom_kill']=='0'
            and type(j['version']) is int and j['version']==1 and j['identity']==second['identity']
            and j['mutations']=={},'DISABLE_ALL8_RESTORED_NO_OOM_EMPTY_JOURNAL')
        role_summary[role]={'original_named_checks':18,'native_seconds':item['native']['elapsed_seconds'],
            'new_boots':2,'maintenance_intervals':8,'fresh_managed_resumptions':2,'actual_aged_restore_counter_matched':True}
    return {'phase':'passed-postflight-report-only','roles':role_summary,'original_named_checks':36,
        'actual_disk_and_cleanup_verified':False,'P10_complete':False,'release_accepted':False,
        'legacy_max_rejected_by_user_scope':True,'two_released_minors_accepted':False}


def retained_disk(report,seal):
    require(gate.namespace(C['namespace']) is None and gate.namespace(B['namespace']) is None,'ACTUAL_NAMESPACES_ABSENT')
    e.no_other_mounts([Path(B['component_root'])/'fixture'/(r+'-business') for r in ['dbs','hisdbs']])
    for role,item in report['roles'].items():
        folder=Path(B['component_root'])/'fixture'/(role+'-business');sealed=seal['roles'][role]
        for boot in item['boots']:
            group=gate.path_clean(boot['cgroup']);require(not group.exists() and not group.parent.exists(),'ACTUAL_NEW_GROUP_AND_PARENT_ABSENT')
        for name,value in sealed['directories'].items():require(gate.directory(folder/name)==value,'ACTUAL_DIRECTORY_IDENTITY')
        for name,value in item['after']['immutable_files'].items():require(gate.digest(folder/name)==value,'ACTUAL_IMMUTABLE_INPUT')
        require(gate.digest(folder/'crg/crg')['sha256']==C['binary_sha256'],'ACTUAL_CURRENT_BINARY_RESTORED')
        for prefixes in [sealed['log_prefixes'],item['before']['log_prefixes']]:
            for name,value in prefixes.items():require(gate.digest(folder/'log/crg'/name,value['size'])==value,'ACTUAL_LOG_PREFIX')
        logs=list((folder/'log/crg').glob('crg-*.log'))
        require(len(logs)>=7 and sum(p.stat().st_size for p in logs)<=1_000_000_000
            and all(re.fullmatch(r'crg-[0-9]{4}-[0-9]{2}-[0-9]{2}\.log',p.name)
                and gate.digest(p)['mode']==0o600 for p in logs),'ACTUAL_DAILY_LOGS')
        require(gate.read_json(folder/'resource-state/journal.json')[0]==item['disable_evidence']['journal'],'ACTUAL_DISABLED_JOURNAL')
        require(gate.read_json(folder/'resource-state/journal.previous.json')[0]==item['second_previous_journal'],'ACTUAL_PREVIOUS_JOURNAL')
        marker=gate.read_json(folder/'resource-state/disabled.json')[0]
        require(marker['version']==1 and marker['identity']==item['boots'][1]['identity'],'ACTUAL_DISABLE_MARKER')
        archive=folder/'postgresql/basebackup'/('crg-aged-'+C['run_id']+'.dump')
        require(gate.digest(archive)==item['logical_backup']['digest'],'ACTUAL_BACKUP_DIGEST')
        load=folder/'postgresql/basebackup'/('crg-soak-'+C['run_id']+('0' if role=='dbs' else '1'))/'load.json'
        require(gate.read_json(load)[0]==item['native'],'ACTUAL_NATIVE_REPORT')


def qualify(authority=None,authority_sha=None,receipt=None,receipt_sha=None):
    e.checked_contract();state,inputs=e.lineage.component()
    if state['phase']=='pending':return dict(state,postflight_result_accepted=False,actual_disk_and_cleanup_verified=False)
    require(state['phase']=='component-accepted','ORIGINAL_LONG_NOT_ACCEPTED')
    report_path=Path(C['work_root'])/'report.json'
    if not report_path.exists():return {'phase':'pending','reason':'POSTFLIGHT_REPORT_ABSENT','postflight_result_accepted':False}
    report,report_digest=gate.read_json(report_path)
    if report.get('phase') in ['preparing','testing-dbs','testing-hisdbs']:
        return {'phase':'pending','reason':'POSTFLIGHT_STILL_RUNNING','postflight_result_accepted':False}
    require(report.get('phase')=='passed','POSTFLIGHT_NOT_PASSED')
    if not all([authority,authority_sha,receipt,receipt_sha]):
        return {'phase':'pending','reason':'TRUSTED_ACTUAL_PROOFS_REQUIRED','postflight_result_accepted':False}
    require(Path(receipt)==Path(RECEIPT) and re.fullmatch('[0-9a-f]{64}',receipt_sha),'RECEIPT_PATH_AND_SHA')
    a=e.checked_authority(authority,authority_sha);seal,digest=gate.read_json(Path(a['seal_path']))
    require(digest==a['seal_sha256'],'ACTUAL_SEAL_DIGEST')
    exit_value,actual=gate.read_json(receipt);require(actual==receipt_sha,'ACTUAL_RECEIPT_DIGEST')
    result=audit(report,report_digest,authority_sha,state,inputs,seal,exit_value)
    require(not gate.proc(exit_value['pid'],exit_value['entry'],exit_value['start_ticks'])['live'],'EXECUTOR_NOT_TERMINAL')
    retained_disk(report,seal)
    require(gate.digest(report_path)['sha256']==report_digest,'REPORT_CHANGED_DURING_REVIEW')
    result.update(phase='passed-postflight-component-only',postflight_result_accepted=True,
        actual_disk_and_cleanup_verified=True,report_sha256=report_digest,authority_sha256=authority_sha,receipt_sha256=receipt_sha)
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--authority',type=Path);p.add_argument('--authority-sha256')
    p.add_argument('--receipt',type=Path);p.add_argument('--receipt-sha256');a=p.parse_args(argv)
    if bool(a.authority)!=bool(a.authority_sha256) or bool(a.receipt)!=bool(a.receipt_sha256):p.error('supply each actual path with its trusted digest')
    try:
        require(sys.platform=='linux' and os.geteuid()==0,'LINUX_TEST_NODE_ROOT_REQUIRED')
        result=qualify(a.authority,a.authority_sha256,a.receipt,a.receipt_sha256)
    except Rejected as error:result={'phase':'rejected','reason':str(error),'postflight_result_accepted':False}
    except (OSError,TypeError,KeyError,AttributeError,ValueError,RecursionError,subprocess.SubprocessError):
        result={'phase':'rejected','reason':'INPUT_SHAPE_READ_OR_INVENTORY','postflight_result_accepted':False}
    result.update(P10_complete=False,release_accepted=False);print(json.dumps(result,indent=2))
    return 2 if result['phase']=='pending' else 1 if result['phase']=='rejected' else 0


if __name__=='__main__':sys.exit(main())
