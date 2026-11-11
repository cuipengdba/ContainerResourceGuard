#!/usr/bin/env python3
"""Reproduce the R235 IO/wait timeline entirely from published evidence.

This forensic tool reads no live node, starts no workload, and cannot certify
the product or infer physical completion bandwidth from io.stat counters.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
import os
from pathlib import Path

MAXIMUM=33554432
THREAD_SHA='c97d1fa67473d368178aca0a392739d67e05b7da8ee4c13c0d62adcab96fd866'
REQUEST_SHA='856ac0612a6408ffcce7d41fd7b2263551d48f9bc7365b5e93c719dfa25b7a78'
EXECUTOR_SHA='0ff4743e1ffb7b1006eddec87a471175eda259aed0e85f60e81fe7424641a62a'
METRICS={'rbytes':'rbps','wbytes':'wbps','rios':'riops','wios':'wiops'}


def digest(raw):return hashlib.sha256(raw).hexdigest()


def read(path,compressed=False):
    assert path.stat().st_size<=MAXIMUM,'input file too large'
    opener=gzip.open if compressed else open
    with opener(path,'rb') as stream:raw=stream.read(MAXIMUM+1)
    assert len(raw)<=MAXIMUM,'decompressed input too large'
    return json.loads(raw),digest(raw)


def pairs(text):
    fields=[line.split() for line in text.splitlines()]
    assert all(len(row)==2 and row[1].isdigit() for row in fields)
    assert len({row[0] for row in fields})==len(fields)
    return {key:int(value) for key,value in fields}


def io_stats(text,limits=False):
    out={}
    for line in text.splitlines():
        parts=line.split();assert len(parts)>=2 and parts[0] not in out
        values={}
        for field in parts[1:]:
            key,value=field.split('=');assert key not in values and (value.isdigit() or limits and value=='max')
            values[key]=None if value=='max' else int(value)
        out[parts[0]]=values
    return out


def available(sample,name):
    value=sample['cgroup'][name];assert value['available'],name
    return value['value']


def distribution(values):
    ordered=sorted(values)
    return {'count':len(values),'minimum':ordered[0],'median':ordered[(len(ordered)-1)//2],
            'p95_nearest_rank':ordered[math.ceil(len(ordered)*.95)-1],'maximum':ordered[-1]} if values else None


def summarize(rows):
    duration=sum(row['seconds'] for row in rows);devices=sorted({d for row in rows for d in row['io']})
    out={'intervals':len(rows),'seconds':duration,'devices':{}}
    for dev in devices:
        valid=[v for v in rows if dev in v['io'] and v['io'][dev]['available']]
        elapsed=sum(v['seconds'] for v in valid)
        out['devices'][dev]={'available_intervals':len(valid),'unknown_intervals':len(rows)-len(valid),'measured_seconds':elapsed,
            'metrics':{key:{'total_counter_delta':sum(v['io'][dev]['deltas'][key] for v in valid),
                'counter_delta_per_second':sum(v['io'][dev]['deltas'][key] for v in valid)/elapsed if elapsed else None,
                'one_interval_rates':distribution([v['io'][dev]['rates'][key] for v in valid]),
                'one_interval_ratios_to_constant_configured_cap':distribution([v['io'][dev]['ratios'][key] for v in valid if v['io'][dev]['ratios'][key] is not None])} for key in METRICS}}
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__);root=Path(__file__).resolve().parents[1]
    p.add_argument('--result',type=Path,default=root/'docs/test-results-business-pressure-final-wait-failure.json')
    p.add_argument('--threads',type=Path,default=root/'docs/test-evidence/native-pressure235-dbs-threads.json.gz')
    p.add_argument('--requests',type=Path,default=root/'docs/test-evidence/native-pressure235-dbs-request-pg.json.gz')
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    result,result_sha=read(args.result);threads,thread_sha=read(args.threads,True);requests,request_sha=read(args.requests,True)
    assert result['schema']=='crg-final-wait-full-pressure-failure-v1' and result['exit']['executor_sha256']==EXECUTOR_SHA
    assert thread_sha==THREAD_SHA==result['thread_reports']['dbs']['sha256']
    assert request_sha==REQUEST_SHA==result['roles']['dbs']['native_diagnostic_evidence']['uncompressed_sha256']
    assert threads['schema']=='crg-vendor-thread-wait-observer-report-v1' and requests['schema']=='crg-native-request-pg-diagnostics-v1'
    assert len(threads['samples'])==600 and len(requests['requests'])==419 and len(requests['pg_samples'])==601
    boot=result['main_report']['roles']['dbs']['boots'][-1];samples=threads['samples'];intervals=[]
    transitions=boot['reload_intervals'];expected_sets={key:set() for key in ['cpu.max','memory.max','io.max']}
    for values in [boot['active_controls'],*(v['actual_kernel_readbacks'] for v in transitions)]:
        for key in expected_sets:expected_sets[key].add(values[key])
    sample_controls={key:Counter(available(s,key) for s in samples) for key in expected_sets}
    assert all(set(sample_controls[key])<=expected_sets[key] for key in expected_sets),'unexpected controller value sampled'
    for before,after in zip(samples,samples[1:]):
        elapsed=after['monotonic']-before['monotonic'];assert .5<elapsed<2
        assert after['epoch']>before['epoch'] and abs(after['epoch']-before['epoch']-elapsed)<.05
        old,new=io_stats(available(before,'io.stat')),io_stats(available(after,'io.stat'))
        oldlimits,newlimits=io_stats(available(before,'io.max'),True),io_stats(available(after,'io.max'),True)
        memory=pairs(available(after,'memory.stat'))
        row={'first_epoch':before['epoch'],'last_epoch':after['epoch'],'seconds':elapsed,'io':{},
             'memory':{key:memory[key] for key in ['anon','file','file_dirty','file_writeback','shmem']},
             'D_tasks':[{'tid':v['stat']['pid'],'wait':v.get('wait_detail')} for v in after['tasks'] if v['stat']['state']=='D'],
             'controls':{key:available(after,key) for key in expected_sets},
             'overlaps_policy_transition':any(v['started_epoch']<=after['epoch'] and v['ended_epoch']>=before['epoch'] for v in transitions)}
        for dev in sorted(set(old)|set(new)):
            if dev not in old or dev not in new or any(new[dev][k]<old[dev][k] for k in METRICS):
                row['io'][dev]={'available':False,'reason':'device-set-change-or-counter-reset'};continue
            deltas={key:new[dev][key]-old[dev][key] for key in METRICS};rates={key:value/elapsed for key,value in deltas.items()}
            cap=oldlimits.get(dev) if oldlimits.get(dev)==newlimits.get(dev) and not row['overlaps_policy_transition'] else None
            row['io'][dev]={'available':True,'deltas':deltas,'rates':rates,
                'cap':cap,'ratios':{key:rates[key]/cap[limit] if cap and cap.get(limit) else None for key,limit in METRICS.items()}}
        intervals.append(row)
    errors=[v for v in requests['requests'] if not v['success'] or not v['within_original_5seconds']]
    windows=[]
    for event in errors:
        selected=[v for v in intervals if v['first_epoch']<=event['ended_epoch'] and v['last_epoch']>=event['started_epoch']]
        windows.append({'request_sequence':event['sequence'],'kind':event['kind'],'started_epoch':event['started_epoch'],'ended_epoch':event['ended_epoch'],
            'after_last_recorded_policy_transition_seconds':event['started_epoch']-max(v['ended_epoch'] for v in transitions),
            'all_window_samples_outside_policy_transitions':not any(v['overlaps_policy_transition'] for v in selected),
            'controls_observed':{key:sorted({v['controls'][key] for v in selected}) for key in expected_sets},'bracket_IO':summarize(selected),
            'file_writeback_bytes':distribution([v['memory']['file_writeback'] for v in selected]),
            'D_bracketing_sample_count':sum(len(v['D_tasks']) for v in selected),
            'D_samples_within_request_count':sum(v['stat']['state']=='D' for sample in samples
                if event['started_epoch']<=sample['epoch']<=event['ended_epoch'] for v in sample['tasks'])})
    policy_runs=[]
    for row in intervals:
        key=json.dumps(row['controls'],sort_keys=True)
        if not policy_runs or policy_runs[-1]['key']!=key:policy_runs.append({'key':key,'rows':[]})
        policy_runs[-1]['rows'].append(row)
    output={'schema':'crg-R235-published-IO-timeline-v1','source_sha256':{'result_json':result_sha,'threads_uncompressed':thread_sha,'requests_uncompressed':request_sha,'analysis_source':digest(Path(__file__).read_bytes())},
            'controller_readback_counts':{key:dict(value) for key,value in sample_controls.items()},
            'all_sampled_controllers_within_recorded_policy_values':True,
            'whole_sample_envelope':summarize(intervals),'failure_windows':windows,
            'policy_runs':[{'controls':json.loads(v['key']),'first_epoch':v['rows'][0]['first_epoch'],'last_epoch':v['rows'][-1]['last_epoch'],'IO':summarize(v['rows'])} for v in policy_runs],
            'intervals':intervals,'interpretation':{'counter_deltas_are_not_device_completion_or_latency':True,'parent_child_devices_must_not_be_added':True,
                'instantaneous_ratio_above_one_is_not_limit_violation':True,'separate_proc_reads_are_not_atomic':True,
                'bracketing_IO_intervals_can_include_samples_outside_request':True,'causal_chain_or_capacity_conclusion_proven':False},
            'new_live_actions':False,'stable_release_accepted':False}
    raw=(json.dumps(output,ensure_ascii=True,sort_keys=True,separators=(',',':'))+'\n').encode();assert len(raw)<MAXIMUM
    fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(raw)
    print(json.dumps({'phase':'analyzed-not-product-accepted','output':str(args.output),'output_sha256':digest(raw),'intervals':len(intervals),
                      'failure_windows':len(windows),'all_failure_windows_outside_policy_changes':all(v['all_window_samples_outside_policy_transitions'] for v in windows)}))


if __name__=='__main__':main()
