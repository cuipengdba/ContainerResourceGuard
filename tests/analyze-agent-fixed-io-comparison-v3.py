#!/usr/bin/env python3
"""Offline review of byte-exact fixed-IO Agent activity evidence; never signal.

Eligibility comes from full native/engine/activity/diagnostic/cleanup evidence,
before looking for the frozen ABBA error pattern. This is not release acceptance.
An eligible diagnostic arm may retain a failed business phase and SQL/API errors;
eligibility never converts those errors into a business SLA pass.
"""
import argparse
import collections
import datetime
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path

EXECUTOR = '664a922a37eba975dc093883cae6d1d3f636881eedaf3b8d1e35adbf28ba3631'
PLAN = 'ac6b79dd4f957684135294ab49398852af143912e849321edb2fbd0cd962de28'
ACTIVITY = 'bd11d8617637336f6ed30c291764550657158d94db0d1cbff43bb86a982b569f'
ELF = 'dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8'
FIRST = 'de22658443d470023fd97f123ddc012445af5a5ecf1fbcac00b2243c95f0c0bd'
FIRST_REPORT = '6a2c971a8c906a7e84334f719f5bf6505d2322623b73564d4667057a1c8236da'
FIRST_COMPARISON = '96d83fe9c3f3a4414bc610b7eb88b8e82d463ca2608d1832241f74f6cb907c0f'
ARMS = [('a1',False),('b1',True),('b2',True),('a2',False)]
FIXED = {'cpu.max':'720000 100000','memory.max':'20001980416',
         'io.max':'253:0 rbps=64700080 wbps=37470104 riops=83 wiops=135'}
CONTROLS = set(FIXED) | {'pids.max','cpu.weight','io.weight','memory.high','memory.swap.max'}
CRITERIA = {'sql_period_seconds':2,'api_period_seconds':5,'maximum_seconds':5,
            'p95_upper_bound_seconds':1,'maximum_errors':0,'minimum_scheduled_samples_fraction':.98}
ENGINE_NAMES = ['fixture_initial_rows','physical_backup_finished','streaming_new_rows_and_checksum',
                'standby_in_recovery','independent_restore_initial_checksum','independent_restore_is_writable',
                'independent_restore_does_not_modify_primary','logical_restore_initial_rows',
                'primary_did_not_restart','probe_monitor_stopped']


def need(value, reason):
    if not value:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def bounded(path, limit):
    need(path.is_file() and not path.is_symlink(), 'REGULAR_ARTIFACT_REQUIRED')
    with path.open('rb') as stream:
        raw=stream.read(limit+1)
    need(len(raw)<=limit,'READ_BOUND')
    return raw


def read_evidence(path):
    if path.is_dir():
        manifest=json.loads(bounded(path/'manifest.json',1024*1024))
        independent_raw=bounded(path/'independent.json',4*1024*1024)
        files={}
        for name in manifest['files']:
            need(not name.startswith('/') and '\\' not in name and all(v not in ['', '.', '..'] for v in name.split('/')), 'RELATIVE_NAME')
            file=path/name;need(file.resolve().is_relative_to(path.resolve()),'ARTIFACT_PATH')
            files[name]=bounded(file,32*1024*1024)
    else:
        compressed=bounded(path,8*1024*1024)
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
            raw=stream.read(64*1024*1024+1)
        need(len(raw)<=64*1024*1024,'EXPANSION_BOUND')
        bundle=json.loads(raw);need(bundle['schema']=='crg-agent-fixed-io-exact-evidence-v2','BUNDLE_SCHEMA')
        manifest=bundle['manifest'];independent_raw=bundle['independent_exact_utf8'].encode()
        need(sha(independent_raw)==bundle['independent_sha256'],'INDEPENDENT_DIGEST')
        files={name:value['exact_utf8'].encode() for name,value in bundle['files'].items()}
    need(manifest['schema']=='crg-agent-fixed-io-exact-files-v2' and set(files)==set(manifest['files']) and 1<=len(files)<=96, 'MANIFEST_MEMBERS')
    need(sum(map(len,files.values()))<=64*1024*1024,'TOTAL_BOUND')
    for name,raw in files.items():
        item=manifest['files'][name];need(len(raw)==item['bytes'] and sha(raw)==item['sha256'],'FILE_DIGEST:'+name)
    independent=json.loads(independent_raw)
    need(independent['schema']=='crg-agent-fixed-io-independent-v2' and independent['all_recorded_instances_independently_gone'] and
         all(v['original_instance_gone'] for v in independent['instances'].values()),'INDEPENDENT_INSTANCES')
    need(sha(files['comparison-snapshot.json'])==independent['comparison_sha256'] and
         files['comparison-snapshot.json']==independent['comparison_snapshot_exact_utf8'].encode(),'SNAPSHOT_BINDING')
    return files,independent


def frozen(files):
    need(sha(files['sources/vendor-agent-fixed-io-comparison-v3.py'])==EXECUTOR and
         sha(files['sources/vendor-agent-activity-session.py'])==ACTIVITY and
         sha(files['tools/comparison-plan.json'])==PLAN,'FROZEN_EXECUTOR_AND_PLAN')
    plan=json.loads(files['tools/comparison-plan.json'])
    need(plan['executor_sha256']==EXECUTOR and plan['activity_source_sha256']==ACTIVITY and plan['pins']['binary']==ELF and
         plan['fixed_numeric']==FIXED and [(v['name'],v['pause_Agent']) for v in plan['arms']]==ARMS and
         plan['native_seconds']==600 and plan['payload_bytes']==67108864 and plan['engine_content_checks']==10 and
         plan['all_four_structural_and_cleanup_eligibility_before_pattern'] is True,'FROZEN_DESIGN')
    need(sha(files['first/executor.py'])==FIRST and sha(files['first/a1-report.json'])==FIRST_REPORT and
         sha(files['first/comparison.json'])==FIRST_COMPARISON,'FIRST_FAILURE_DIGESTS')
    first=json.loads(files['first/a1-report.json']);comparison=json.loads(files['first/comparison.json'])
    need(first['phase']=='failed' and first['reason']=='ValueError' and first['namespace_absent'] and
         first['original_config_bytes_and_profile_absence_restored'] and set(comparison['arms'])=={'a1'} and
         not first['roles']['dbs']['boots'][0].get('agent_activity'),'FIRST_PREPARATION_FAILURE')
    gates=json.loads(files['tools/gates.json'])
    need(gates['phase']=='passed' and len(gates['observations'])==15 and gates['no_business_executed'] and
         gates['target_and_four_namespaces_absent'] and gates['plan_sha256']==PLAN,'READONLY_AND_DENIAL_GATES')
    for name,item in gates['files'].items():
        raw=files['sources/'+name];need(len(raw)==item['bytes'] and sha(raw)==item['sha256'],'QUALIFIED_SOURCE:'+name)
    need(sha(files['sources/error-boundary-qualification.json'])=='22e9b62081cc57017ef8db06e7f8f21a6d140a8e4bf3d66959e559ce7582e14f','FROZEN_ERROR_BOUNDARY_CHECKS')
    boundary=json.loads(files['sources/error-boundary-qualification.json'])
    need(boundary['phase']=='passed' and boundary['v3_source_sha256']==EXECUTOR and len(boundary['tests'])==24 and all(v['passed'] for v in boundary['tests']),'ACTUAL_ERROR_BOUNDARY_CHECKS')
    prior=plan['v2_failure']
    need(prior['executor_sha256']=='383c5b0a5184edcd3aee73b1b017888a6c50d449e44b5e43bcd3275afabecbc4' and prior['a1_report_sha256']=='2124c64cb82309ee2c67e3983595dfd7d223d5115fd4e659d930fab68286f3ac' and prior['source_and_failure_preserved'] is True,'PRIOR_V2_FAILURE_PLAN_BINDING')
    snapshot=json.loads(files['comparison-snapshot.json']);metadata=snapshot['source_manifest']
    need(snapshot['baseline_frozen_before_any_arm'] and set(snapshot['clones'])=={n for n,_ in ARMS} and
         metadata['entries']==25383 and metadata['metadata_sha256']=='6742736a82a016a5d5f5d80dfe325f9e279562a10397c656bb8c47fcd44f202c' and
         all(v['metadata_sha256']==metadata['metadata_sha256'] and v['critical_content_sha_verified'] and v['distinct_regular_file_inodes'] for v in snapshot['clones'].values()),'FULL_FOUR_COLD_CLONE_EVIDENCE')
    return plan


def original_data_reader():
    path=Path(__file__).with_name('analyze-write-iops-arm.py')
    need(sha(bounded(path,128*1024))=='457fdf382bedadd6fcd628d1174dccb7d359acb9f7848821e869c6962b57bc38','PURE_COUNTER_READER_CHANGED')
    spec=importlib.util.spec_from_file_location('fixed_activity_counter_reader',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def timestamp(value):
    return datetime.datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()


def source_and_cleanup(independent, name, report):
    expected={'crg-config/config.json':'08ed1a0de3a2b9f74e3af3608600e9716ecc80c36921148c2cb21d9c9de46550',
              'crg/crg':ELF,'ccg/bin/containercacheguard':'757ba385a0ee4bdadc968b96b5c3e69fd44353060e5ab28520fd6f73a59902de',
              'crg/optional-agent.sh':'f7e7208f58bac7066d75d49cb17199b720e3d05bb5953e2a7a7800f881b54b79'}
    need(independent['v2_full600_failure_preserved'] is True,'PRIOR_V2_FAILURE_INDEPENDENT_READBACK')
    row=independent['arms'][name]
    need(row['executed'] and row['namespace_independently_absent'] and row['cgroups'] and
         all(not v['exists'] and not v['parent_exists'] for v in row['cgroups']),'ARM_NAMESPACE_AND_CGROUP_CLEANUP')
    for key in ['source',name]:
        value=independent['source_and_clone_readbacks'][key]
        need(value['sha256']==expected and value['profile_absent'] and value['postmaster_pid_absent'],'SOURCE_OR_CLONE_RESTORATION')
    need(independent['source_clean_shutdown'] and independent['source_pg_control_sha256']=='383369440339bcc6a5a403530190b64ba5236e76719cc3140bc4197a63868218' and
         independent['first_preparation_failure_preserved'] and report['namespace_absent'] and report['original_config_bytes_and_profile_absence_restored'],'SOURCE_AND_RECORDED_CLEANUP')


def review_arm(files, independent, name):
    plan=frozen(files);prefix='arms/'+name+'/';report_raw=files[prefix+'report.json'];report=json.loads(report_raw)
    snapshot=json.loads(files['comparison-snapshot.json'])
    need(independent['scope']==name and sha(report_raw)==independent['arms'][name]['report_sha256']==snapshot['arms'][name]['report_sha256'], 'ARM_REPORT_BINDING')
    need(report['schema']=='crg-agent-fixed-io-arm-v3' and report['executor_sha256']==EXECUTOR and report['arm']==name and
         report['pause_Agent']==dict(ARMS)[name] and report['plan_sha256']==PLAN and report['binary_sha256']==ELF,'ARM_IDENTITY')
    need(report['phase'] in ['passed','failed'],'ARM_TERMINAL')
    source_and_cleanup(independent,name,report)
    namespace=next(v['namespace'] for v in plan['arms'] if v['name']==name)
    need(namespace==independent['arms'][name]['namespace'],'EXACT_ARM_NAMESPACE')
    keys=['dbs/native/load.json','dbs/native-diagnostics.json','dbs/devices.json','dbs/threads.json','dbs/engine/business-backup.json']
    missing=[key for key in keys if prefix+key not in files]
    if missing:
        return {'arm':name,'eligible':False,'phase':report['phase'],'reason':report.get('reason'),'missing_complete_evidence':missing,'stable_release_accepted':False}
    native_raw=files[prefix+'dbs/native/load.json'];native=json.loads(native_raw);diagnostic_raw=files[prefix+'dbs/native-diagnostics.json'];diagnostics=json.loads(diagnostic_raw)
    need(sha(native_raw)==snapshot['arms'][name]['native_report_sha256'],'EXACT_NATIVE_REPORT_BINDING')
    devices=json.loads(files[prefix+'dbs/devices.json']);threads=json.loads(files[prefix+'dbs/threads.json']);engine=json.loads(files[prefix+'dbs/engine/business-backup.json'])
    boots=report.get('roles',{}).get('dbs',{}).get('boots',[]);need(len(boots)==1,'ONE_ORIGINAL_BOOT');boot=boots[0]
    record=boot.get('agent_activity',{});session=record.get('session',{});samples=record.get('samples',[]);activity=record.get('plan',{})
    if 'native' in boot:
        need(boot['native']==native,'NATIVE_BOOT_AND_RAW_EQUAL')
    else:
        # The original business exception leaves before assigning this duplicate.
        # The byte-exact raw native report remains bound to the frozen snapshot.
        need(report['phase']=='failed' and report.get('reason')=='NATIVE_COMPLETION_EXIT' and native['phase']=='failed','FAILED_NATIVE_RAW_REQUIRED_WITHOUT_DUPLICATE')
    identities={kind:{'pid':boot[kind]['observer_pid'],'start_ticks':boot[kind]['observer_start_ticks']} for kind in ['thread_observer','device_observer']}
    identities.update(native=boot['native_final_flush']['identity'],Agent=activity,PID1={'pid':activity['container_pid'],'start_ticks':activity['container_start_ticks']},helper=record['helper'],watchdog={'pid':session['watchdog_pid'],'start_ticks':session['watchdog_start_ticks']})
    need(set(independent['instances'])=={name+'-0-'+kind for kind in identities},'ALL_SEVEN_INDEPENDENT_ARM_IDENTITIES')
    for kind,identity in identities.items():
        actual=independent['instances'][name+'-0-'+kind]
        need(actual['pid']==identity['pid'] and actual['expected_start_ticks']==identity['start_ticks'] and actual['original_instance_gone'],'EXACT_CLEANUP_IDENTITY:'+kind)
    pause=dict(ARMS)[name];started=timestamp(native['started_utc']);finished=timestamp(native['measurement_finished_utc'])
    expected=dict(boot['runtime_original_controls'],**FIXED);counts=1 if pause else 0
    checks={
        'original_full600':native['phase'] in ['passed','failed'] and native['requested_duration_seconds']==600 and native['elapsed_seconds']>=600 and not native['interrupted'] and native['threads_stopped'] and finished-started>=600,
        'original_64MiB_and_same_primary':native['payload_integrity'] and native['primary_not_restarted'] and native['initial_checksum'][2]==67108864 and native['primary_start_time_initial']==native['primary_start_time_final'],
        'original_request_criteria':native['criteria']==CRITERIA,
        'fixed_original_numeric_values':record.get('fixed_controls')==expected and set(expected)==CONTROLS and all(v['actual_kernel_readbacks']==expected and v['same_processes'] for v in boot['samples']) and len(boot['samples'])>=10,
        'no_reload_or_pressure_substitution':boot['reload_intervals']==[] and report['derived_business']==plan['derived_business'] and report['original_release_acceptance_executed'] is False,
        'terminal_reason':report.get('reason') in [None,'NATIVE_COMPLETION_EXIT'],
        'all_recorded_checks_passed':bool(report['tests']) and all(v['passed'] for v in report['tests']),
        'ten_original_engine_content_checks':[v['name'] for v in engine['roles']['dbs']['checks']]==ENGINE_NAMES and all(v['passed'] for v in engine['roles']['dbs']['checks']) and boot['engine']==engine,
        'engine_cleanup':engine['roles']['dbs']['temporary_servers_stopped_and_copies_removed'] and engine['roles']['dbs']['own_fixture_schema_restore_database_snapshot_removed'],
        'engine_inside_native600':started<=boot['engine_interval']['started_epoch']<=boot['engine_interval']['ended_epoch']<=finished,
        'exact_activity_owner':activity.get('binary_sha256')==ELF and activity.get('argv')==['/opt/crg/crg','run','--config','/etc/crg/config.json'] and activity.get('cgroup')==boot['cgroup'] and activity.get('pid',0)>1 and activity.get('pid')!=activity.get('container_pid'),
        'activity_session_closed':session.get('phase')=='closed' and session.get('STOP_count')==session.get('CONT_count')==counts and (not pause or session.get('resumed_same_instance') is True) and not any(k in session for k in ['unwind_error','close_error','watchdog_still_running','watchdog_pipe_already_closed']),
        'same_watchdog_normal_close':session.get('watchdog_exit')==0 and session.get('watchdog',{}).get('CONT_count')==0 and session.get('watchdog',{}).get('reason')=='owner-completed',
        'full600_activity_envelope':record.get('effective_activity_started_epoch',float('inf'))<=started<=finished<=record.get('effective_activity_ended_epoch',0),
        'no_activity_or_diagnostic_errors':not boot.get('activity_error') and not boot.get('diagnostic_cleanup_errors') and not boot['device_observer'].get('integration_errors'),
    }
    parent=boot.get('activity_parent_observation',{});helper=record.get('helper',{})
    checks['actual_sourced_helper_identity']=bool(parent) and parent.get('Agent_pid')==activity.get('pid') and parent.get('Agent_start_ticks')==activity.get('start_ticks') and parent.get('helper_pid')==helper.get('pid') and parent.get('helper_start_ticks')==helper.get('start_ticks') and parent.get('helper_parent_pid')==parent.get('container_pid')==activity.get('container_pid') and parent.get('container_start_ticks')==activity.get('container_start_ticks') and parent.get('helper_is_not_container_PID1') is True and parent.get('helper_in_same_cgroup') is True and parent.get('helper_argv_sha256')==parent.get('supervisor_argv_sha256') and parent.get('helper_exe_sha256')==parent.get('supervisor_exe_sha256')
    initial=session.get('initial',{})
    checks['actual_session_initial_kernel']=set(initial.get('controls',{}))==CONTROLS and {k:v.strip() for k,v in initial.get('controls',{}).items()}==expected and initial.get('pid')==activity.get('pid') and initial.get('start_ticks')==activity.get('start_ticks')
    checks['matched_full_activity_samples']=len(samples)>=10 and all(v['pid']==activity['pid'] and v['start_ticks']==activity['start_ticks'] and v['controls']==initial['controls'] and v['control_values_preserved'] and v['all_threads_stopped']==pause and (v['state'] in ['T','t'])==pause and v['helper_state'] not in ['T','t','Z','X'] and (not pause or (v['user_ticks'],v['system_ticks'])==(initial['user_ticks'],initial['system_ticks'])) for v in samples)
    checks['activity_sample_gaps_and_endpoints']=len(samples)>=2 and samples[0]['epoch']<=started and samples[-1]['epoch']>=finished and all(0<=z['epoch']-a['epoch']<=120 for a,z in zip(samples,samples[1:]))
    need(sha(diagnostic_raw)==native['native_diagnostics']['report_sha256']==boot['native_request_pg']['raw_report_sha256'], 'NATIVE_DIAGNOSTIC_BINDING')
    need(diagnostics['schema']=='crg-native-request-pg-diagnostics-v2' and diagnostics['run_id']==native['run_id']=='202611114490' and diagnostics['worker_sha256']=='a9483aebec862e8254b6b6a144ad1e1889021252697a276922afbfd8459d5857','NATIVE_RUN_AND_WORKER')
    if prefix+'dbs/native/native-diagnostics.json' in files:need(files[prefix+'dbs/native/native-diagnostics.json']==diagnostic_raw,'DUPLICATE_DIAGNOSTIC_BINDING')
    requests=diagnostics['requests'];pg=diagnostics['pg_samples'];summary=native['native_diagnostics']
    checks['native_diagnostics_complete']=boot['native_request_pg']['phase']=='collected' and not boot['native_request_pg']['partial_not600s'] and summary['diagnostic_complete'] and summary['probe_thread_stopped'] and all(summary[k]==0 for k in ['dropped_requests','dropped_pg_samples','pg_errors','pg_wait_errors','pg_truncated_samples','recorder_internal_errors','business_signals_cancellations_or_control_writes']) and diagnostics['summary']['diagnostic_complete']
    checks['request_counts_and_schedule']=True
    for kind,period in [('sql',2),('api',5)]:
        rows=[v for v in requests if v['kind']==kind];item=native[kind]
        checks['request_counts_and_schedule'] &= type(item['attempts']) is int and item['attempts']>=600/period*.98 and len(rows)==item['attempts']==item['successes']+item['errors']==sum(item['histogram']) and len(item['histogram'])==12 and sum(not v['success'] or not v['within_original_5seconds'] for v in rows)==item['errors']
    checks['PG_coverage']=len(pg)>=588 and all(v['available'] and not v['truncated'] for v in pg) and all(0<=z['started_epoch']-a['started_epoch']<=3 for a,z in zip(pg,pg[1:]))
    for kind,rawdata,key in [('thread',threads,'thread_observer'),('device',devices,'device_observer')]:
        row=boot[key];data=rawdata['samples']
        need(sha(files[prefix+'dbs/'+('threads.json' if kind=='thread' else 'devices.json')])==row['raw_report_sha256'],'OBSERVER_RAW_BINDING:'+kind)
        need(rawdata['plan']['cgroup']==boot['cgroup'] and rawdata['plan']['pid']==threads['plan']['pid'] and rawdata['plan']['start_ticks']==threads['plan']['start_ticks'],'OBSERVER_TARGET_BINDING')
        checks[kind+'_complete']=row['phase']=='collected' and row['engine_and_reload_interval_envelopes_covered'] and rawdata['sample_count']==len(data)>=2 and all(0<=z['epoch']-a['epoch']<=3 for a,z in zip(data,data[1:])) and data[0]['epoch']<=boot['engine_interval']['started_epoch']<=boot['engine_interval']['ended_epoch']<=data[-1]['epoch']
    checks['device_no_KILL_or_control_writes']=boot['device_observer']['owned_observer_KILL_count']==0 and devices['block_device_opens_signals_and_control_writes']==0 and threads['target_signals_or_control_writes']==0
    reader=original_data_reader();errors=[v for v in requests if not v['success'] or not v['within_original_5seconds']]
    observations=reader.task_observations(threads['samples'],float('-inf'),float('inf'))
    stacks=[v['kernel_wait'].get('kernel_stack',{'available':False}) for sample in pg for v in sample['pg_wait']['targets']]
    activity_interval=None
    if len(samples)>=2:
        first,last=samples[0],samples[-1];seconds=last['epoch']-first['epoch'];ticks=last['user_ticks']+last['system_ticks']-first['user_ticks']-first['system_ticks']
        rate=independent.get('clock_ticks_per_second');cpu=ticks/rate if type(rate) is int and rate>0 else None
        process_io=reader.counter_delta(first.get('process_io'),last.get('process_io'))
        activity_interval={'seconds':seconds,'CPU_ticks_delta':ticks,'clock_ticks_per_second':rate,'CPU_seconds':cpu,
                           'process_io':process_io,'scope':'Agent sample endpoints include preparation and final collection; not exclusive native600 or device-owned IO'}
    return {'arm':name,'eligible':all(checks.values()),'checks':checks,'reasons':[k for k,v in checks.items() if not v],
            'phase':report['phase'],'reason':report.get('reason'),'native_phase':native['phase'],'actual_seconds':native['elapsed_seconds'],
            'SQL_errors':native['sql']['errors'],'API_errors':native['api']['errors'],'activity_samples':len(samples),'initial_actual_controls':initial.get('controls'),
            'engine_content_checks':len(engine['roles']['dbs']['checks']),'D_observations':len(observations),
            'D_descriptor_counts':dict(collections.Counter(v['wait_detail'].get('descriptor',{}).get('path','unknown') for v in observations)),
            'strict_D_samples_per_error':[len(reader.task_observations(threads['samples'],v['started_epoch'],v['ended_epoch'])) for v in errors],
            'PG_kernel_stack_unknown':sum(not v['available'] for v in stacks),'PG_samples':len(pg),'thread_samples':len(threads['samples']),'device_samples':len(devices['samples']),
            'report_sha256':sha(report_raw),'Agent_activity_sample_interval':activity_interval,'independent_instances_gone':len(independent['instances']),'stable_release_accepted':False}


def analyze(terminal, arm_paths):
    files,independent=read_evidence(terminal);plan=frozen(files);comparison=json.loads(files['comparison-snapshot.json'])
    need(independent['scope']=='terminal' and comparison['phase'] in ['diagnostic-completed','diagnostic-inconclusive','failed'] and
         independent['exit']['exit']=={'diagnostic-completed':0,'diagnostic-inconclusive':2,'failed':1}[comparison['phase']] and
         independent['exit']['timed_out'] is False and independent['exit']['executor_sha256']==EXECUTOR,'TERMINAL_COMPARISON')
    need(comparison['executor_sha256']==EXECUTOR and comparison['plan_sha256']==PLAN and
         comparison['baseline_frozen_before_any_arm'] and set(comparison['clones'])=={n for n,_ in ARMS},'ALL_FOUR_FROZEN_BASELINES')
    need(set(independent['arms'])=={n for n,_ in ARMS} and all(v['namespace_independently_absent'] for v in independent['arms'].values()),'ALL_FOUR_NAMESPACE_CLEANUP')
    rows={};expected_final_instances={}
    for filename,pid,ticks in [('launch.json',1869845,138002881),('worker.json',1869846,138002885)]:
        identity=json.loads(files['tools/'+filename])
        need((identity['pid'],identity['start_ticks'])==(pid,ticks),'ORIGINAL_COORDINATOR_IDENTITY:'+filename)
        expected_final_instances[filename]=(pid,ticks)
    for name,_ in ARMS:
        if name not in comparison['arms']:
            rows[name]={'arm':name,'eligible':False,'available':False,'reason':'not-executed'};continue
        need(name in arm_paths,'MISSING_ARM_EVIDENCE:'+name)
        values,proof=read_evidence(arm_paths[name]);raw=values['arms/'+name+'/report.json']
        need(sha(raw)==comparison['arms'][name]['report_sha256']==independent['arms'][name]['report_sha256'] and
             raw==files['arms/'+name+'/report.json'],'FINAL_ARM_BINDING:'+name)
        rows[name]=review_arm(values,proof,name)
        for key,item in proof['instances'].items():
            expected_final_instances[key]=(item['pid'],item['expected_start_ticks'])
    need(set(independent['instances'])==set(expected_final_instances),'ALL_FINAL_INDEPENDENT_IDENTITIES')
    need(all((independent['instances'][key]['pid'],independent['instances'][key]['expected_start_ticks'])==identity and independent['instances'][key]['original_instance_gone'] for key,identity in expected_final_instances.items()),'FINAL_IDENTITIES_MATCH_PER_ARM_EVIDENCE')
    need(independent['v2_full600_failure_preserved'] is True,'PRIOR_V2_FAILURE_FINAL_READBACK')
    # A qualified contrast requires all original arm criteria. Admission of an
    # unqualified observation never replaces an independent eligibility check.
    eligible=comparison['phase']=='diagnostic-completed' and all(v['eligible'] for v in rows.values())
    controls=[v.get('initial_actual_controls') for v in rows.values()]
    eligible=eligible and all(v==controls[0] for v in controls)
    counts=[rows[n]['SQL_errors']+rows[n]['API_errors'] for n,_ in ARMS] if eligible else None
    pattern=(counts[0]>0 and counts[1]==counts[2]==0 and counts[3]>0 and all(rows[n]['native_phase']=='passed' for n in ['b1','b2'])) if eligible else None
    return {'schema':'crg-agent-fixed-io-independent-review-v3','all_four_structurally_eligible':eligible,'arms':rows,
            'SQL_plus_API_errors':counts,'preplanned_A_error_B_zero_B_zero_A_error':pattern,
            'conclusion':('fixed-quota-Agent-activity-association-with-confounds' if pattern else 'preplanned-association-not-observed') if eligible else 'inconclusive',
            'coordinator_interpretation':comparison.get('interpretation'),'first_preparation_failure_preserved':True,
            'first_specific_assertion_unproven':True,'v2_full600_failure_preserved':True,'observational_followup_does_not_qualify_an_arm':True,'terminal_archive_sha256':sha(bounded(terminal,8*1024*1024)) if terminal.is_file() else None,
            'fixed_numeric':plan['fixed_numeric'],'shared_backend_cache_and_order_confounds_remain':True,
            'Agent_causality_or_product_defect_proven':False,'original32_two_role_acceptance_waived':False,
            'original32_accepted':False,'seven_day_accepted':False,'stable_release_accepted':False,'P10_complete':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--terminal',type=Path);group.add_argument('--arm-evidence',type=Path)
    p.add_argument('--arm',choices=[n for n,_ in ARMS]);p.add_argument('--output',type=Path)
    for name,_ in ARMS:p.add_argument('--'+name,type=Path)
    args=p.parse_args()
    try:
        if args.arm_evidence:
            need(args.arm is not None,'ARM_NAME_REQUIRED');files,proof=read_evidence(args.arm_evidence);result=review_arm(files,proof,args.arm)
        else:result=analyze(args.terminal,{n:getattr(args,n) for n,_ in ARMS if getattr(args,n) is not None})
        raw=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
        if args.output:
            with args.output.open('x',encoding='utf-8',newline='\n') as stream:stream.write(raw)
            print(json.dumps({'output':str(args.output),'eligible':result.get('eligible',result.get('all_four_structurally_eligible')),'conclusion':result.get('conclusion')}))
        else:print(raw,end='')
        return 0
    except (ValueError,KeyError,TypeError,OSError,EOFError) as error:
        print(json.dumps({'phase':'rejected','reason':str(error)}));return 1


if __name__=='__main__':
    raise SystemExit(main())
