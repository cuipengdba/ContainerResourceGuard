#!/usr/bin/env python3
"""Disposable business probe segmentation; never rewrites historical results."""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import sys
import types

sys.dont_write_bytecode = True
HERE = Path(__file__).parent
RELOAD_SHA = 'aaef6058f12693a62a1885d0e988c2295a7d748ba2e31896d8af807153e3e3b7'
TIMED_ENGINE_SHA = '5abbc7110ece3383c63e84737c70f8265d7f674ffdca09cff23fdade05fbe42d'
API_SHA = '907a705ddfa55a3635a757c38ee5fcb46e1b0a5c93a2056b15e06488e2b8f2d8'
if hashlib.sha256((HERE/'vendor-versioned-business-reload.py').read_bytes()).hexdigest() != RELOAD_SHA:
    raise ValueError('FROZEN_RELOAD_EXECUTOR')
spec = importlib.util.spec_from_file_location('timing_reload_base', HERE/'vendor-versioned-business-reload.py')
reload = importlib.util.module_from_spec(spec);spec.loader.exec_module(reload)
gate, require, Rejected = reload.gate, reload.require, reload.Rejected
ROOT = '/var/tmp/crg-business-timing100-20261111'
NS = 'crg-vendor-lab-timing100-20261111'
TOOLS = '/var/tmp/crg-timing100-tools-20261111'
ENGINE = TOOLS+'/vendor-engine-timed.py'
API = TOOLS+'/vendor-api-timed.py'
RUN = '20261111100'


def rebind(function, **bindings):
    """Keep the frozen function's code object; only explicit data bindings vary."""
    require(not function.__code__.co_freevars, 'UNEXPECTED_BASE_CLOSURE')
    return types.FunctionType(function.__code__, dict(function.__globals__, **bindings), function.__name__, function.__defaults__)


def engine_shape(original, timed):
    def shape(source):
        tree=ast.parse(source)
        probes=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='probe']
        require(len(probes)==1,'ONE_PROBE_FUNCTION');probes[0].body=[ast.Pass()]
        return ast.dump(tree,include_attributes=False)
    require(shape(original)==shape(timed),'ONLY_ENGINE_PROBE_MAY_CHANGE')


def checked_plan(path, expected):
    p, actual = gate.read_json(path)
    require(actual==expected and re.fullmatch(r'[0-9a-f]{64}',expected),'PLAN_DIGEST')
    require(p.get('schema')=='crg-business-exec-timing-plan-v1' and p.get('work_root')==ROOT
            and p.get('namespace')==NS and p.get('run_id')==RUN and p.get('mode')=='exec-timing'
            and p.get('pins')==reload.PINS and p.get('criteria')==reload.base.CRITERIA
            and p.get('policies')==reload.POLICIES and p.get('numeric_readbacks')==reload.EXPECTED
            and p.get('executor_sha256')==gate.digest(Path(__file__))['sha256']
            and p.get('reload_executor_sha256')==RELOAD_SHA and p.get('timed_engine_sha256')==TIMED_ENGINE_SHA
            and p.get('timed_api_sha256')==API_SHA, 'PLAN_CONTRACT')
    require(p.get('worker')==reload.WORKER and p.get('engine')==ENGINE and p.get('timed_api')==API
            and p.get('profile')==reload.PROFILE and p.get('previous_binary')=='/var/tmp/crg-r71-20261111/binaries/previous','TOOL_BINDINGS')
    old_plan,_=gate.read_json(Path('/var/tmp/crg-reload95-tools-20261111/reload-plan.json'))
    require(p.get('roles')==old_plan['roles'],'ORIGINAL_SOURCE_FOLDERS')
    for path,pin in [(API,API_SHA),(ENGINE,TIMED_ENGINE_SHA),(reload.ENGINE,reload.PINS['engine']),
                     (reload.WORKER,reload.PINS['worker']),(reload.PROFILE,reload.PINS['profile']),
                     (p['previous_binary'],reload.PINS['previous'])]:
        require(gate.digest(Path(path))['sha256']==pin,'QUALIFIED_TOOL_SOURCE')
    engine_shape(Path(reload.ENGINE).read_text(),Path(ENGINE).read_text())
    # Use the exact independent numeric expectations and capacity/profile pins
    # from R95; the live policy waiter also reads every actual kernel value.
    mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:')))*1024
    require(mem==66673278976 and Path('/sys/devices/system/cpu/online').read_text().strip()=='0-23'
            and os.sysconf('SC_PAGE_SIZE')==4096,'ORIGINAL_CAPACITY')
    return p


def readiness(plan):
    previous,_=gate.read_json(Path('/var/tmp/crg-business-reload95-20261111/report.json'))
    require(gate.digest(Path('/var/tmp/crg-business-reload95-20261111/report.json'))['sha256']=='14c7bae7e959d7b6af965837144dcf19f1c683a2dfd8310bc2c3ea37b6af51e6'
            and previous['phase']=='passed' and len(previous['tests'])==24 and all(x['passed'] for x in previous['tests'])
            and previous['namespace_absent'] and previous['original_config_bytes_and_profile_absence_restored'],'PRIOR_RELOAD_TERMINAL')
    launch,_=gate.read_json(Path('/var/tmp/crg-reload95-tools-20261111/reload-launch.json'))
    worker,_=gate.read_json(Path('/var/tmp/crg-reload95-tools-20261111/reload-worker.json'))
    receipt,_=gate.read_json(Path('/var/tmp/crg-reload95-tools-20261111/reload.exit.json'))
    require(receipt['exit']==0 and receipt['executor_sha256']==RELOAD_SHA
            and not gate.proc(launch['pid'],launch['entry'],launch['start_ticks'])['live']
            and not gate.proc(worker['pid'],worker['entry'],worker['start_ticks'])['live']
            and gate.namespace('crg-vendor-lab-reload95-20261111') is None,'PRIOR_EXECUTION_NOT_GONE')
    # The old read-only predicate is unchanged, with only our two new targets.
    result=rebind(reload.readiness,ROOT=ROOT,NS=NS)(plan)
    result['scope']='read-only segmentation prerequisites; not historical failure resolution'
    return result


class Execution(reload.Execution):
    def __init__(self,plan,digest):
        super().__init__(plan,digest)
        self.report.update(schema='crg-business-exec-timing-report-v1',mode='exec-timing',
            executor_sha256=gate.digest(Path(__file__))['sha256'],base_reload_executor_sha256=RELOAD_SHA,
            timed_engine_sha256=TIMED_ENGINE_SHA,timed_api_sha256=API_SHA,
            scope='new instrumented 600s business reload; only engine probe function differs; historical 7.017s cause not proven',
            historical_failure_resolved=False)

    def business_native(self,role,folder,group,row):
        _,cid,_,actual_group=self.identity(role);require(actual_group==group,'TIMING_OWN_GROUP')
        entry='/tmp/crg-timed-api-'+RUN+('0' if role=='dbs' else '1')+'00.py'
        self.ex(role,'/bin/bash','-c','set -Ce; umask 077; cat > '+entry+'; chmod 0444 '+entry,data=Path(API).read_text())
        require(self.ex(role,'sha256sum',entry).stdout.split()[0]==API_SHA,'INNER_PROBE_COPY')
        context=self.root/(role+'-timing-context.json')
        with context.open('x') as out:
            os.chmod(context,0o600);json.dump({'cgroup':str(group),'container_id':cid},out)
        # All seven resource transitions, numeric checks, native thresholds,
        # original engine scheduling and cleanup use the frozen code object.
        rebind(reload.Execution.business_native,ENGINE=ENGINE)(self,role,folder,group,row)
        probes=row['engine']['roles'][role]['probes'];valid=[];unclassified=[]
        for i,sample in enumerate(probes):
            inner=sample.get('api_inner',{})
            if inner.get('schema')=='crg-inner-api-timing-v1':
                seconds=inner['request_seconds']
                require(type(seconds) in [int,float] and 0<=seconds<=sample['api_seconds']+.001
                        and inner['request_finished_monotonic']>=inner['request_started_monotonic']
                        and abs(seconds-(inner['request_finished_monotonic']-inner['request_started_monotonic']))<.000001,
                        'INNER_TIMING_BOUNDS')
                valid.append({'index':i,'outer_seconds':sample['api_seconds'],'inner_seconds':seconds,
                    'outside_inner_request_seconds':sample['api_outside_inner_request_seconds'],
                    'outer_above_original5s':sample['api_seconds']>5,'request_ok':inner['request_ok']})
            else:unclassified.append(i)
        row['timing']={'valid_probes':valid,'unclassified_probes':unclassified,
            'outer_above5s_count':sum(x['outer_seconds']>5 for x in valid),
            'inner_above5s_count':sum(x['inner_seconds']>5 for x in valid),
            'historical_7_017s_attributed':False}
        self.check(role+'-completed-API-probes-have-bounded-inner-timings',bool(valid) and not unclassified)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--plan-sha256',required=True);parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    try:
        require(sys.platform=='linux' and os.geteuid()==0,'LINUX_ROOT')
        plan=checked_plan(args.plan,args.plan_sha256);ready=readiness(plan)
        if not args.execute:print(json.dumps(ready));return 0
        require(os.environ.get('CRG_EXEC_TIMING')=='authorized-disposable-test-node-only','EXPLICIT_LAB_MARKER')
        def interrupted(signum,frame):raise KeyboardInterrupt()
        signal.signal(signal.SIGTERM,interrupted);ready=readiness(plan)
        result=Execution(plan,args.plan_sha256).execute(ready)
        print(json.dumps({'phase':result['phase'],'checks':len(result['tests']),'reason':result.get('reason'),'historical_failure_resolved':False}))
        return 0 if result['phase']=='passed' and result.get('namespace_absent') and result.get('original_config_bytes_and_profile_absence_restored') else 1
    except BaseException as error:
        print(json.dumps({'phase':'rejected','reason':str(error) if isinstance(error,Rejected) else type(error).__name__,'executed':False}));return 1


if __name__=='__main__':raise SystemExit(main())
