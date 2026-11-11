#!/usr/bin/env python3
"""Independently review frozen Agent activity lifecycle evidence, never signal."""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path

ELF = 'dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8'
ACTIVITY = 'bd11d8617637336f6ed30c291764550657158d94db0d1cbff43bb86a982b569f'
HOST_SOURCE = '75b6b9dff26a4de42699692ca75a5f8dddc71222e332f9df90662935f625c2ac'
FIRST = '551a349a475870a7063fce7afb1e44c30aaa0a0a8155eb9bb106c2ee146e90e1'
V2 = 'db3b70a2b58f6817877f51af131cc7a328b2f8852ce515419f2b5af917d7ab7c'
CONTROLS = {'cpu.max','memory.max','io.max','cpu.weight','pids.max','io.weight','memory.high','memory.swap.max'}
REFUSALS = ['pid1','self','stale-ticks','wrong-exe','wrong-cgroup','wrong-argv','wrong-nonce']
SUFFIXES = ['real-path-original-startup-manual-accepted-budget','original-CCG-mount-stays-readonly',
 'original-cache-independent-enforce','owned-exact-Agent-and-original-business-identities',
 *['reject-'+v for v in REFUSALS], 'active-session-no-signals-business-preserved',
 'only-Agent-paused-kernel-and-business-preserved','normal-resume-same-instance-watchdog-reaped',
 'exception-resumes-original-Agent-and-preserves-body-error',
 'final-disable-restores-runtime-and-retains-original-business']


def need(value, reason):
    if not value:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def bounded(path, maximum=32*1024*1024):
    with path.open('rb') as stream:
        raw=stream.read(maximum+1)
    need(len(raw)<=maximum, 'READ_BOUND')
    return raw


def artifact(repo, item):
    path=(repo/item['path']).resolve()
    need(path.is_relative_to(repo) and not path.is_symlink(), 'ARTIFACT_PATH')
    raw=bounded(path)
    need(sha(raw)==item['sha256'], 'ARTIFACT_DIGEST')
    with gzip.open(path,'rb') as stream:
        data=stream.read(32*1024*1024+1)
    need(len(data)<=32*1024*1024 and sha(data)==item['uncompressed_sha256'], 'ARTIFACT_CONTENT')
    return json.loads(data)


def frozen(repo, source, planfile, digest):
    raw=bounded(repo/source)
    need(sha(raw)==digest, 'EXECUTOR_DIGEST')
    tree=ast.parse(raw)
    nodes=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='FROZEN_PLAN' for v in n.targets)]
    need(len(nodes)==1, 'FROZEN_PLAN_DECLARATION')
    expected=dict(ast.literal_eval(nodes[0].value),executor_sha256=digest)
    plan=json.loads(bounded(repo/planfile))
    need(plan==expected and plan['activity_source_sha256']==ACTIVITY and plan['expected_checks']==32, 'FROZEN_PLAN_BINDING')
    need(plan['budget']=={'cpu_cores':7.2,'memory_max_bytes':20001980416,'read_write_bps':67108864,'read_write_iops':4096}, 'QUALIFICATION_BUDGET')
    return plan


def terminal(obs, expected, phase):
    report=obs['report']
    need(report['phase']==phase and report['job_sha256']==expected, 'TERMINAL_SOURCE_PHASE')
    need(obs['exit']['executor_sha256']==expected and obs['exit']['exit']==(0 if phase=='passed' else 1)
         and obs['exit']['timed_out'] is False, 'TERMINAL_EXIT')
    need(report['namespace_absent'] is True and obs['namespace_absent'] is True, 'NAMESPACE_CLEANUP')
    need(set(obs['processes'])=={'runner','worker'} and all(v['same_instance_present'] is False for v in obs['processes'].values()), 'RUNNER_WORKER_CLEANUP')
    need(len(obs['cgroups'])==2 and {v['role'] for v in obs['cgroups']}=={'dbs','hisdbs'} and
         all(v['exists'] is False and v['parent_exists'] is False for v in obs['cgroups']), 'CGROUP_CLEANUP')
    need(all(v['same_instance_present'] is False for v in obs['watchdogs']), 'WATCHDOG_CLEANUP')
    need(set(report['roles'])=={'dbs','hisdbs'} and all(v['own_pod_removed'] is True for v in report['roles'].values()), 'BOTH_POD_CLEANUP')
    file=obs['files']['report.json']
    need(file['value']==report and sha(json.dumps(report,indent=2).encode())==file['sha256'], 'RAW_REPORT_BINDING')
    return report


def review(repo, index):
    need(index['schema']=='crg-agent-activity-qualification-evidence-v1', 'INDEX_SCHEMA')
    need(sha(bounded(repo/'tests/vendor-agent-activity-session.py'))==ACTIVITY, 'ACTIVITY_SOURCE')
    first_plan=frozen(repo,'tests/vendor-agent-activity-qualification.py','docs/test-plan-agent-activity-qualification.json',FIRST)
    plan=frozen(repo,'tests/vendor-agent-activity-qualification-v2.py','docs/test-plan-agent-activity-qualification-v2.json',V2)
    host=artifact(repo,index['artifacts']['host'])
    host_source=artifact(repo,index['artifacts']['host_source'])
    need(sha(host_source['source'].encode())==HOST_SOURCE, 'HOST_EXECUTED_SOURCE')
    h=host['report'];need(h['phase']=='passed' and h['source_sha256']==ACTIVITY and len(h['tests'])==27 and
        len({v['name'] for v in h['tests']})==27 and all(v['passed'] is True for v in h['tests']) and not h.get('cleanup_errors'), 'HOST_27_CHECKS')
    need(sha(json.dumps(h,indent=2).encode())==host['report_sha256'] and
        len(host['independent_instances'])>=10 and all(v['same_instance_present'] is False for v in host['independent_instances']), 'HOST_TERMINAL')
    death=h['records']['owner-death'];lease=h['records']['lease-expiry']
    need(death['owner_was_SIGKILLed'] is True and death['same_start_ticks'] is True and
         death['watchdog']['reason']=='owner-pipe-eof' and death['watchdog']['CONT_count']==1 and
         lease['watchdog']['reason']=='lease-expired' and lease['watchdog']['CONT_count']==1, 'HOST_WATCHDOG_RECOVERY')
    first_obs=artifact(repo,index['artifacts']['first_failure'])
    first=terminal(first_obs,FIRST,'failed')
    need(len(first['tests'])==6 and all(v['passed'] is True for v in first['tests']) and all(
        v['phase']=='failed' and v['error']=='test command failed, exit=127' and not v.get('activity_records') for v in first['roles'].values()), 'FIRST_FAILURE_PRESERVED')
    need(plan['previous_failed_source_sha256']==FIRST and plan['previous_failed_report_sha256']==first_obs['files']['report.json']['sha256'], 'FAILURE_PLAN_BINDING')
    obs=artifact(repo,index['artifacts']['vendor_v2']);report=terminal(obs,V2,'passed')
    need(report['plan_sha256']==sha(bounded(repo/'docs/test-plan-agent-activity-qualification-v2.json')), 'REPORT_PLAN_BINDING')
    expected={role+'-'+name for role in ['dbs','hisdbs'] for name in SUFFIXES}
    need(len(report['tests'])==32 and len(expected)==32 and {v['name'] for v in report['tests']}==expected and
        all(v['passed'] is True for v in report['tests']), 'VENDOR_EXACT_32_CHECKS')
    need(report['qualified_program']['binary_sha256']==ELF and len(obs['watchdogs'])==6, 'VENDOR_PROGRAM_AND_WATCHDOGS')
    roles={}
    for role,row in report['roles'].items():
        need(row['phase']=='short-qualification-passed' and row['ready_and_managed_seconds']<=300 and
             row['cache_enforce_observation_seconds']<=45 and row['PG_start_time'], 'VENDOR_STARTUP')
        p=row['activity_plan'];controls=row['actual_controls'];records=row['activity_records']
        need(p['kind']=='vendor-container' and p['binary_sha256']==ELF and p['argv']==['/opt/crg/crg','run','--config','/etc/crg/config.json'] and
             p['pid']>1 and p['pid']!=p['container_pid'] and p['start_ticks']>0 and
             Path(p['cgroup']).name=='cri-containerd-'+p['container_id']+'.scope' and
             ('pod'+p['pod_uid'].replace('-','_')) in Path(p['cgroup']).parent.name, 'OWN_VENDOR_AGENT')
        need(set(controls)==CONTROLS and controls['cpu.max']=='720000 100000\n' and controls['memory.max']=='20001980416\n', 'ACTUAL_CPU_MEMORY')
        io=controls['io.max'].split();need(io[0]=='253:0' and dict(v.split('=') for v in io[1:])==
             {'rbps':'67108864','wbps':'67108864','riops':'4096','wiops':'4096'}, 'ACTUAL_IO')
        need(set(records)==set(REFUSALS+['active','paused','exception']), 'SESSION_SET')
        for label in REFUSALS:
            v=records[label];need(v['STOP_count']==v['CONT_count']==0 and v['phase']=='closed', 'REFUSED_WITHOUT_SIGNAL')
        for label in ['active','paused','exception']:
            v=records[label];count=0 if label=='active' else 1
            need(v['phase']=='closed' and v['STOP_count']==v['CONT_count']==count and v['watchdog_exit']==0 and
                 v['watchdog']['CONT_count']==0 and v['watchdog']['reason']=='owner-completed' and
                 v['initial']['pid']==p['pid'] and v['initial']['start_ticks']==p['start_ticks'] and
                 v['initial']['controls']==controls and v['initial']['control_values_preserved'] is True and
                 v['initial']['all_threads_stopped']==(label!='active'), 'SESSION_LIFECYCLE')
            if count:need(v['resumed_same_instance'] is True, 'SAME_AGENT_RESUMED')
        a,z=row['paused_samples'];need(all(v['all_threads_stopped'] and v['controls']==controls and v['control_values_preserved'] for v in [a,z]) and
            a['user_ticks']==z['user_ticks'] and a['system_ticks']==z['system_ticks'], 'PAUSED_ACTUAL_PROCESS')
        need(row['final_actual_controls']==dict(controls,**{'cpu.max':'800000 100000\n','memory.max':'21474836480\n','io.max':''}), 'RESTORE_EXACT_RUNTIME')
        roles[role]={'checks':16,'normal_and_exception_same_Agent_resume':True,'actual_eight_controls_preserved_during_pause':True,
            'original_business_probes_and_PG_cache_identity_preserved':True,'runtime_originals_restored':True,
            'root_psql_diagnostic':row.get('root_psql_diagnostic')}
    return {'schema':'crg-agent-activity-qualification-analysis-v1','phase':'qualified','host_checks':27,'vendor_checks':32,
        'roles':roles,'independent_terminal_cleanup':True,'first_failure_preserved':True,
        'scope':'short lifecycle qualification only; host shadow files and actual vendor kernel evidence distinguished',
        'fixed_IO_ABBA_executed':False,'native600_business_accepted':False,'original32_accepted':False,'stable_release_accepted':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--index',default='docs/test-results-agent-activity-qualification.json')
    args=p.parse_args()
    try:
        repo=args.repo.resolve();index=json.loads(bounded(repo/args.index))
        print(json.dumps(review(repo,index),ensure_ascii=False,indent=2));return 0
    except (ValueError,KeyError,IndexError,TypeError,OSError,AssertionError) as error:
        print(json.dumps({'phase':'rejected','reason':str(error),'stable_release_accepted':False}));return 1


if __name__=='__main__':
    raise SystemExit(main())
