"""Independent post-run verifier; read exact selected originals, never remote I/O."""
from pathlib import Path
import argparse,hashlib,json,math

def sha(raw):return hashlib.sha256(raw).hexdigest()

def qualify(plan_raw, originals, observation):
    plan=json.loads(plan_raw);o=observation
    assert o['job_sha256']==plan['job_sha256'] and o['plan_sha256']==sha(plan_raw)
    assert o['exit']['phase']=='passed' and o['exit']['exit']==0 and o['independent_cleanup_complete']
    assert all(v['original_absent'] for v in o['processes'].values())
    source=json.loads(originals['source-map.json']);assert not source['missing']
    assert len(source['copied'])+1==len(originals)
    for row in source['copied']:
        raw=originals[row['filename']];assert sha(raw)==row['sha256'] and len(raw)==row['bytes']
    coordinator=json.loads(originals['coordinator-report.json']);assert coordinator['phase']=='passed' and sha(originals['coordinator-report.json'])==o['coordinator_report_sha256']
    roles={}
    for role in ['dbs','hisdbs']:
        key='normal-'+role;run=plan['run_ids']['normal'][role]
        report=json.loads(originals[key+'-report.json']);assert report['phase']=='passed' and len(report['tests'])==13 and all(v['passed'] for v in report['tests'])
        case=next(iter(report['roles'].values()));identity=case['fixture_identity'];lock=json.loads(originals[key+'-controlled-lock.json']);work=json.loads(originals[key+'-native.json'])
        assert case['initial_controls']==case['final_controls'] and len(case['final_controls'])==8
        assert case['own_pod_removed'] and case['own_leaf_absent'] and case['own_parent_absent']
        assert lock['phase']=='passed-negative-diagnostic-only' and lock['run_id']==run and lock['worker_seconds']==120 and lock['lock_seconds']==8 and lock['auxiliary_originals_absent']
        assert lock['worker_sha256']==plan['source_sha256']['tests/vendor-soak-load.py']
        assert lock['lock_holder_exit']==0 and len(lock['lock_holder_backend_pids'])==1 and lock['lock_holder_backend_pids'][0]>1
        holder=lock['lock_holder_backend_pids'][0];assert 8<=lock['lock_exec_elapsed_seconds']<=22 and lock['lock_requested_monotonic']<lock['lock_ended_monotonic']
        a,b=lock['observer_host_instance'],lock['worker_host_instance'];assert a['pid']!=b['pid'] and all(p['start_ticks']>0 for p in [a,b])
        assert a['entry']=='/tmp/crg-wait-timeline-'+run+'.py' and b['entry']=='/tmp/crg-soak-load-'+run+'.py'
        assert all(any(v['pid']==p['pid'] and v['start_ticks']==p['start_ticks'] and v.get('entry')==p['entry'] for v in identity['processes']) for p in [a,b])
        assert work['phase']=='failed' and lock['worker_exit']!=0 and work==lock['workload']
        assert work['requested_duration_seconds']==120 and work['elapsed_seconds']>=120 and work['threads_stopped'] and work['payload_integrity'] and work['primary_not_restarted'] and not work['interrupted']
        assert work['criteria']=={'sql_period_seconds':2,'api_period_seconds':5,'maximum_seconds':5,'p95_upper_bound_seconds':1,'maximum_errors':0,'minimum_scheduled_samples_fraction':.98}
        api=work['api'];assert api['errors']==0 and api['max_seconds']<=5 and api['p95_bucket_upper_seconds']<=1 and api['sample_coverage']>=.98
        events=work['failure_diagnostics']['events'];assert len(events)==work['sql']['errors']>0 and all(e['kind']=='sql' for e in events)
        assert work['failure_diagnostics']['collection_errors']==work['failure_diagnostics']['dropped_events']==0
        for e in events:
            assert e['stage']=='sql_query' and e['reason'] in ['sql_readiness_deadline','sql_result_deadline','sql_socket_deadline'] and e['elapsed_seconds']>=4.99
            assert e['request_started_monotonic_seconds']<=lock['lock_ended_monotonic'] and e['request_finished_monotonic_seconds']>=lock['lock_requested_monotonic']
        raw=originals[key+'-timeline.log'];assert raw.endswith(b'\n') and len(raw)<=4194304 and all(len(line)+1<=16384 for line in raw.splitlines()) and sha(raw)==lock['timeline_sha256']
        lines=[json.loads(line) for line in raw.splitlines()];head,terminal=lines[0],lines[-1];samples=lines[1:-1]
        assert head['kind']=='header' and head['source_sha256']==plan['source_sha256']['tests/wait-timeline.py'] and head['worker_sha256']==plan['source_sha256']['tests/vendor-soak-load.py']
        assert head['pid1_start_ticks']==identity['init_start_ticks'] and head['group_inode']>0 and head['group_device']>0
        assert identity['group'].startswith('/sys/fs/cgroup/') and head['membership_sha256']==sha(('0::'+identity['group'][len('/sys/fs/cgroup'):]+'\n').encode())
        assert terminal==lock['timeline_terminal'] and terminal['phase']=='complete' and terminal['reason']=='explicit_own_stop_file' and terminal['failure'] is None and lock['observer_exit']==0
        assert terminal['backend_query_errors']==0 and terminal['samples']==len(samples)<=900 and all(s['kind']=='sample' and s['sequence']==i+1 and s['backend_query_phase']=='complete' for i,s in enumerate(samples))
        span=samples[-1]['sample_finished_monotonic']-samples[0]['sample_started_monotonic'];assert span>=120 and len(samples)>=span/2*.9
        assert all(0<b['sample_started_monotonic']-a['sample_started_monotonic']<=8 for a,b in zip(samples,samples[1:]))
        capabilities=terminal['pressure_capabilities'];assert len(capabilities)==6
        for s in samples:
            for scope in ['group','host']:
                for resource in ['cpu','memory','io']:
                    pressure=s[scope][resource+'_pressure'];assert pressure['phase']==capabilities[scope+'_'+resource]
                    if pressure['phase']=='unavailable':assert pressure=={'phase':'unavailable','reason':'kernel_interface_absent','errno':2}
                    else:assert pressure['phase']=='available' and pressure['counters']
            assert s['group']['memory_current']>=0 and 'usage_usec' in s['group']['cpu_stat'] and 'anon' in s['group']['memory_stat'] and s['group']['io_stat'] and s['host']['vmstat']
        matches=[]
        for e in events:
            found=[{'sequence':s['sequence'],'waiter_pid':v['pid'],'holder_pid':holder} for s in samples if s['sample_started_monotonic']<=e['request_finished_monotonic_seconds'] and s['sample_finished_monotonic']>=e['request_started_monotonic_seconds'] for v in s['backends'] if v['wait_type']=='Lock' and v['wait_event']=='relation' and holder in v['blocking_pids'] and v['pid']!=holder]
            assert found;matches.append({'SQL_attempt':e['attempt'],'matches':found})
        assert lock['counter_after_lock']>lock['counter_before_lock']
        assert all(lock['final_memory_events'][k]==samples[0]['group']['memory_events'][k] for k in ['oom','oom_kill'])
        stop=json.loads(originals[key+'-observer-stop.json']);assert stop['schema']=='crg-owned-wait-stop-v1' and stop['run_id']==run and stop['pid1_start_ticks']==head['pid1_start_ticks'] and stop['membership_sha256']==head['membership_sha256']
        assert samples[0]['sample_started_monotonic']<=stop['requested_monotonic']<=samples[-1]['sample_finished_monotonic']+8
        roles[role]={'phase':'passed-negative-diagnostic-only','checks':13,'workload_phase_expected_failed':work['phase'],'workload_elapsed_seconds':work['elapsed_seconds'],'SQL_errors':work['sql']['errors'],'SQL_max_seconds':work['sql']['max_seconds'],'SQL_coverage':work['sql']['sample_coverage'],'API_errors':api['errors'],'API_max_seconds':api['max_seconds'],'API_coverage':api['sample_coverage'],'holder_backend_pid':holder,'lock_exec_seconds':lock['lock_exec_elapsed_seconds'],'timeline_samples':len(samples),'timeline_bytes':len(raw),'timeline_span_seconds':span,'timeline_backend_errors':0,'pressure_capabilities':capabilities,'event_to_actual_holder':matches,'counter_before_lock':lock['counter_before_lock'],'counter_after_lock':lock['counter_after_lock'],'eight_controls_unchanged':True,'auxiliaries_and_all_own_objects_absent':True}
    return {'schema':'crg-controlled-lock-independent-v3','phase':'passed-negative-diagnostic-only','roles':roles,'total_diagnostic_and_startup_checks':26,'indexed_originals':len(originals),'indexed_bytes':sum(len(v) for v in originals.values()),'job_sha256':plan['job_sha256'],'plan_sha256':sha(plan_raw),'source_revision':plan['source_revision'],'cleanup_independent':True,'registered_process_records_checked':o['registered_process_instances_absent'],'original18_full600_accepted':False,'old1761_failure_cause':'unknown','pressure_measurement_qualified':all(v=='available' for r in roles.values() for v in r['pressure_capabilities'].values()),'stable_release_accepted':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--observation',type=Path,required=True);p.add_argument('--download',type=Path,required=True);p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    receipt=json.loads(a.observation.read_bytes());assert receipt['exit']==0 and not receipt['stderr'];o=json.loads(receipt['stdout']);download=json.loads(a.download.read_bytes());originals={}
    for row in download['result']['files']:
        assert Path(row['filename']).name==row['filename'];raw=(a.directory/row['filename']).read_bytes();assert sha(raw)==row['sha256']==row['download_sha256'] and len(raw)==row['bytes'];originals[row['filename']]=raw
    result=qualify(a.plan.read_bytes(),originals,o)
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(result))
