"""Independently inspect terminal original600 comparison selected originals.

This verifier never changes a workload result, contacts a host, or grants formal18.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,math

def sha(raw):return hashlib.sha256(raw).hexdigest()
def epoch(text):return datetime.datetime.fromisoformat(text.replace('Z','+00:00')).timestamp()
def counts(a,b):
    keys=set(a)|set(b)
    return {k:b.get(k,0)-a.get(k,0) for k in sorted(keys)}
def counter_window(samples):
    a,b=samples[0],samples[-1]
    return {'cpu_stat_delta':counts(a['group']['cpu_stat'],b['group']['cpu_stat']),
      'memory_events_delta':counts(a['group']['memory_events'],b['group']['memory_events']),
      'memory_current_first_last':[a['group']['memory_current'],b['group']['memory_current']],
      'file_dirty_first_last':[a['group']['memory_stat'].get('file_dirty'),b['group']['memory_stat'].get('file_dirty')],
      'file_writeback_first_last':[a['group']['memory_stat'].get('file_writeback'),b['group']['memory_stat'].get('file_writeback')],
      'io_stat_delta_by_device':{d:counts(a['group']['io_stat'].get(d,{}),b['group']['io_stat'].get(d,{})) for d in sorted(set(a['group']['io_stat'])|set(b['group']['io_stat']))},
      'host_vmstat_delta':counts(a['host']['vmstat'],b['host']['vmstat'])}

def qualify(plan_raw,originals,o):
    p=json.loads(plan_raw);assert o['job_sha256']==p['job_sha256'] and o['plan_sha256']==sha(plan_raw)
    assert o['exit']['phase'] in ['passed','failed'] and o['exit']['exit']==(0 if o['exit']['phase']=='passed' else 1)
    assert o['independent_cleanup_complete'] and all(v['original_absent'] for v in o['processes'].values())
    sm=json.loads(originals['source-map.json']);assert len(sm['copied'])+1==len(originals)
    assert len({r['filename'] for r in sm['copied']})==len(sm['copied'])
    for r in sm['copied']:assert sha(originals[r['filename']])==r['sha256'] and len(originals[r['filename']])==r['bytes']
    co=json.loads(originals['coordinator-report.json']);assert sha(originals['coordinator-report.json'])==o['coordinator_report_sha256'] and co==o['coordinator_report'] and co['phase']==o['exit']['phase']
    order=['enforce-dbs','enforce-hisdbs'];assert list(co['roles'])==order[:len(co['roles'])]
    cells={}
    for key,row in co['roles'].items():
        arm,role=key.split('-',1);run=p['run_ids'][arm][role];raw=originals[key+'-report.json'];r=json.loads(raw)
        assert sha(raw)==row['report_sha256'] and len(r['tests'])==row['recorded_checks'] and sum(v['passed'] for v in r['tests'])==row['passed_checks']
        assert row['phase']==('passed' if row['exit']==0 and r['phase']=='passed' and len(r['tests'])==row['passed_checks']==11 else 'failed')
        assert len(r['roles'])==1;c=next(iter(r['roles'].values()));identity=c['fixture_identity'];cell={'phase':row['phase'],'recorded_checks':len(r['tests']),'passed_checks':row['passed_checks'],'failed_checks':[v['name'] for v in r['tests'] if not v['passed']],'unexecuted_checks':11-len(r['tests']),'error':c.get('error'), 'full600_completed':False,'normal_business_passed':False,'auxiliary_diagnostics_passed':False}
        assert c['own_pod_removed'] and c['own_leaf_absent'] and c['own_parent_absent']
        config_name=key+'-config.json'
        if config_name in originals:
            config=json.loads(originals[config_name]);assert config==p['configurations'][arm] and originals[config_name].decode()==p['configuration_exact_utf8_by_arm'][arm]
        if c.get('initial_controls'):
            assert c['initial_controls']==c['final_controls'] and len(c['final_controls'])==8
            cell['eight_controls_unchanged_during_window']=True
            if arm=='observe':assert c['initial_controls']==c['pre_gate_controls']
            else:
                assert c['initial_controls']['cpu.max']=='720000 100000' and c['initial_controls']['memory.high']=='20001980416'
                lines=[dict(v.split('=') for v in line.split()[1:]) for line in c['initial_controls']['io.max'].splitlines() if line.strip()]
                assert lines and all(x.get('rbps')=='67108864' and x.get('wbps')=='67108864' and x.get('riops')=='4096' and x.get('wiops')=='4096' for x in lines)
        if arm=='observe' and c.get('initial_controls'):
            absent=next(x for x in sm['expected_absent_observe_journals'] if x['role']==role);assert absent['observed_absent'] and key+'-journal.json' not in originals and c['journal_absent_in_observe']
        elif c.get('initial_controls'):
            j=json.loads(originals[key+'-journal.json']);assert {v['file'] for v in j['mutations'].values()}=={'cpu.max','memory.high','io.max'}
        workload_name=key+'-native.json';session_name=key+'-wait-session.json';campaign_name=key+'-campaign-report.json';timeline_name=key+'-timeline.log'
        work=json.loads(originals[workload_name]) if workload_name in originals else None
        campaign=json.loads(originals[campaign_name]) if campaign_name in originals else None
        session=json.loads(originals[session_name]) if session_name in originals else None
        engine_name=key+'-engine-0.json'
        if engine_name in originals:
            engine=json.loads(originals[engine_name]);er=engine['roles'][role]
            cell['engine_exec_probe_diagnostic']=er.get('exec_probe_diagnostic')
            cell['engine_probe_boundary']='Separate kubectl-exec diagnostic, including its original5s flag, is preserved verbatim. The original frozen engine mode requires the successful native workload to surround the content cycle; no universal latency or CRG causality claim.'
        samples=[]
        if timeline_name in originals:
            traw=originals[timeline_name];assert len(traw)<=4194304 and traw.endswith(b'\n') and all(len(line)+1<=16384 for line in traw.splitlines());values=[json.loads(line) for line in traw.splitlines()];head=values[0];samples=[x for x in values if x['kind']=='sample'];term=values[-1] if values[-1]['kind']=='terminal' else None
            assert head['kind']=='header' and head['source_sha256']==p['source_sha256']['tests/wait-timeline.py'] and head['worker_sha256']==p['source_sha256']['tests/vendor-soak-load.py']
            assert head['pid1_start_ticks']==identity['init_start_ticks'] and head['membership_sha256']==sha(('0::'+identity['group'][len('/sys/fs/cgroup'):]+'\n').encode())
            assert all(x['sequence']==i+1 and x['sample_started_monotonic']<=x['sample_finished_monotonic'] and x['backend_query_phase'] in ['complete','failed'] for i,x in enumerate(samples))
            assert all(0<b['sample_started_monotonic']-a['sample_started_monotonic'] for a,b in zip(samples,samples[1:]))
            if session and session['phase']=='passed-diagnostic-only':
                assert term and term==session['timeline_terminal'] and term['phase']=='complete' and term['reason']=='explicit_own_stop_file' and term['failure'] is None and term['backend_query_errors']==0 and term['samples']==len(samples)<=900
                span=samples[-1]['sample_finished_monotonic']-samples[0]['sample_started_monotonic'];assert span>=600 and len(samples)>=span/2*.90 and all(b['sample_started_monotonic']-a['sample_started_monotonic']<=8 for a,b in zip(samples,samples[1:]))
                assert session['timeline_sha256']==sha(traw) and session['timeline_bytes']==len(traw) and session['observer_exit']==0 and session['observer_original_absent'] and len(session['checks'])==2 and all(v['passed'] for v in session['checks'])
                a,b=session['observer_host_instance'],session['worker_host_instance'];assert a['pid']!=b['pid'] and a['entry']=='/tmp/crg-wait-timeline-'+run+'.py' and b['entry']=='/tmp/crg-soak-load-'+run+'.py'
                assert all(any(v['pid']==x['pid'] and v['start_ticks']==x['start_ticks'] for v in identity['processes']) for x in [a,b])
                stop=json.loads(originals[key+'-observer-stop.json']);assert stop['run_id']==run and stop['membership_sha256']==head['membership_sha256'] and stop['pid1_start_ticks']==head['pid1_start_ticks']
                assert samples[0]['sample_started_monotonic']<=stop['requested_monotonic']<=samples[-1]['sample_finished_monotonic']+8
                caps=term['pressure_capabilities'];assert len(caps)==6
                for s in samples:
                    assert s['backend_query_phase']=='complete'
                    for scope in ['group','host']:
                        for resource in ['cpu','memory','io']:
                            pressure=s[scope][resource+'_pressure'];assert pressure['phase']==caps[scope+'_'+resource]
                            if pressure['phase']=='unavailable':assert pressure=={'phase':'unavailable','reason':'kernel_interface_absent','errno':2}
                            else:assert pressure['phase']=='available' and pressure['counters']
                cell.update(auxiliary_diagnostics_passed=True,timeline_samples=len(samples),timeline_bytes=len(traw),timeline_span_seconds=span,pressure_capabilities=caps,pressure_measurement_qualified=all(v=='available' for v in caps.values()))
            else:cell['timeline_partial_or_auxiliary_failed']=True
        if work:
            assert work['run_id']==run and work['requested_duration_seconds']==600 and work['test_phase']=='smoke' and work['criteria']=={'sql_period_seconds':2,'api_period_seconds':5,'maximum_seconds':5,'p95_upper_bound_seconds':1,'maximum_errors':0,'minimum_scheduled_samples_fraction':.98}
            full=work.get('elapsed_seconds',0)>=600 and work.get('threads_stopped') and not work.get('interrupted');cell.update(full600_completed=bool(full),workload_phase=work['phase'],workload_elapsed_seconds=work.get('elapsed_seconds'),sql=work['sql'],api=work['api'],failure_diagnostics=work['failure_diagnostics'])
            if work['phase']=='passed':
                assert full and work['payload_integrity'] and work['primary_not_restarted']
                assert all(work[k]['errors']==0 and work[k]['max_seconds']<=5 and work[k]['p95_bucket_upper_seconds']<=1 and work[k]['sample_coverage']>=.98 for k in ['sql','api'])
                assert work['failure_diagnostics']['collection_errors']==0 and not work['failure_diagnostics']['events']
            if campaign and campaign['phase']=='passed':
                assert work['phase']=='passed' and campaign['worker_sha256']==p['source_sha256']['tests/vendor-soak-load.py'] and campaign['campaign_script_sha256']==p['source_sha256']['tests/vendor-soak-campaign.py']
                assert campaign['requested_seconds']==600 and len(campaign['backups'])==1 and campaign['roles'][role]['workload']==work
                cycle=campaign['backups'][0];assert cycle['phase']=='passed' and cycle['native_workload_validation']=='passed-with-entire-campaign'
                assert epoch(work['started_utc'])<=cycle['content_started_epoch']<=cycle['content_ended_epoch']<=epoch(work['measurement_finished_utc'])
                engine=json.loads(originals[key+'-engine-0.json']);er=engine['roles'][role];assert len(er['checks'])==10 and all(x['passed'] for x in er['checks']) and er['own_fixture_schema_restore_database_snapshot_removed'] and er['native_campaign_validation_pending']
                cell['normal_business_passed']=True
            if samples:
                if cell['auxiliary_diagnostics_passed'] and full:
                    assert epoch(samples[0]['observed_utc'])<=epoch(work['started_utc']) and epoch(samples[-1]['observed_utc'])>=epoch(work['measurement_finished_utc'])
                    assert all(samples[-1]['group']['memory_events'][k]==samples[0]['group']['memory_events'][k] for k in ['oom','oom_kill'])
                    cell['timeline_surrounds_entire_native_window']=True
                cell['window_counters']=counter_window(samples);matches=[]
                for e in work['failure_diagnostics']['events']:
                    overlaps=[s for s in samples if s['sample_started_monotonic']<=e['request_finished_monotonic_seconds'] and s['sample_finished_monotonic']>=e['request_started_monotonic_seconds']]
                    before=[s for s in samples if s['sample_started_monotonic']<=e['request_started_monotonic_seconds']];after=[s for s in samples if s['sample_finished_monotonic']>=e['request_finished_monotonic_seconds']]
                    window=([before[-1]] if before else [])+overlaps+([after[0]] if after else [])
                    matches.append({'event':e,'overlapping_samples':[s['sequence'] for s in overlaps],'actual_backend_waits':[{'sequence':s['sequence'],'backends':s['backends']} for s in overlaps], 'surrounding_counter_window':counter_window(window) if len(window)>=2 else None,'causality':'unknown; observations are sampled and non-atomic'})
                cell['event_correlations']=matches
        if row['phase']=='passed':assert cell['normal_business_passed'] and cell['auxiliary_diagnostics_passed'] and cell['full600_completed'] and len(r['tests'])==11
        original=[t for t in r['tests'] if t.get('scope')!='auxiliary-diagnostic'];aux=[t for t in r['tests'] if t.get('scope')=='auxiliary-diagnostic']
        expected=['candidate1-'+role+'-manual64-'+suffix for suffix in ['real-path-original-startup-manual-budget-without-calibration', 'manual-plan-exact-and-own-mode-specific-controls', 'original-CCG-mount-stays-readonly', 'original-cache-independent-enforce', 'only-three-resource-controls-and-other-values-preserved', 'daily-logs-report-v2-before-business-campaign', 'one-current-Agent-cache-and-mode-specific-journal', '600s-native-and-backup-sync-independent-restore', 'normal-engine-real-PG-owner-start-stop-cleanup-diagnostics']]
        assert [t['name'] for t in original]==expected[:len(original)] and len(original)<=9 and len(aux)<=2
        assert r['formal_original18_acceptance'] is False and r['scope']=='fixed one-pair mode comparison with original600 and extra own wait diagnostics; not formal original18 acceptance'
        cell['raw_driver_legacy_scope_and_false_acceptance_retained']=True
        cell['raw_driver_metadata_boundary']='Reused per-role comparison driver cannot itself grant the aggregate formal18. Its legacy label/false remain unchanged. The separately pre-frozen formal coordinator/plan and exact original9 names per role determine aggregate acceptance after fresh complete600 and independent verification.'
        cell['original_checks_recorded']=len(original);cell['original_checks_passed']=sum(t['passed'] for t in original);cell['auxiliary_checks_recorded']=len(aux);cell['auxiliary_checks_passed']=sum(t['passed'] for t in aux)
        if row['phase']=='passed':assert len(original)==9 and len(aux)==2 and all(t['passed'] for t in original+aux)
        cells[key]=cell
    passed=not sm['missing'] and len(cells)==2 and all(v['phase']=='passed' for v in cells.values());assert (co['phase']=='passed')==passed
    return {'schema':'crg-fresh-formal18-plus4-independent-v2','phase':'passed-formal18-plus4-only' if passed else 'failed-or-partial-formal18-retained','cells':cells,'recorded_checks':sum(v['recorded_checks'] for v in cells.values()),'passed_checks':sum(v['passed_checks'] for v in cells.values()),'planned_checks':22,'original_business_checks':18,'auxiliary_checks':4,'missing_selected_originals':sm['missing'],'indexed_originals':len(originals),'indexed_bytes':sum(len(v) for v in originals.values()),'job_sha256':p['job_sha256'],'plan_sha256':sha(plan_raw),'source_revision':p['source_revision'],'cleanup_independent':True,'registered_process_records_checked':o['registered_process_instances_absent'],'formal_original18_accepted':passed,'old1761_failure_cause':'unknown','one_fixed_order_pair_proves_causality':False,'new_long_started':False,'stable_release_accepted':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ['plan','observation','download','directory','output']:parser.add_argument('--'+n,type=Path,required=True)
    a=parser.parse_args();receipt=json.loads(a.observation.read_bytes());assert receipt['exit']==0 and not receipt['stderr'];o=json.loads(receipt['stdout']);d=json.loads(a.download.read_bytes());originals={}
    for row in d['result']['files']:
        assert Path(row['filename']).name==row['filename'];raw=(a.directory/row['filename']).read_bytes();assert sha(raw)==row['sha256']==row['download_sha256'] and len(raw)==row['bytes'];originals[row['filename']]=raw
    result=qualify(a.plan.read_bytes(),originals,o)
    with a.output.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print(json.dumps({'phase':result['phase'],'cells':{k:{n:v[n] for n in ['phase','recorded_checks','passed_checks','full600_completed','normal_business_passed','auxiliary_diagnostics_passed']} for k,v in result['cells'].items()},'indexed_originals':result['indexed_originals'],'indexed_bytes':result['indexed_bytes']}))
