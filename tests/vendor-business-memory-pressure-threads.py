#!/usr/bin/env python3
"""Exact memory30-to20 pressure and retry during frozen 600s vendor business.

Default is read-only; no product process manages another container. Kernel
memory is never directly lowered by this fixture. Production code is unchanged.
"""
import argparse,ast,select,datetime,hashlib,importlib.util,json,os,re,signal,stat,subprocess,sys,time,types
from pathlib import Path
sys.dont_write_bytecode=True
RELOAD_SHA='aaef6058f12693a62a1885d0e988c2295a7d748ba2e31896d8af807153e3e3b7'
API_SHA='907a705ddfa55a3635a757c38ee5fcb46e1b0a5c93a2056b15e06488e2b8f2d8'
TIMED_ENGINE_SHA='5abbc7110ece3383c63e84737c70f8265d7f674ffdca09cff23fdade05fbe42d'
here=Path(__file__).parent
if hashlib.sha256((here/'vendor-versioned-business-reload.py').read_bytes()).hexdigest()!=RELOAD_SHA:raise ValueError('FROZEN_RELOAD_HELPER')
spec=importlib.util.spec_from_file_location('reload_edges_frozen',here/'vendor-versioned-business-reload.py')
reload=importlib.util.module_from_spec(spec);spec.loader.exec_module(reload)
base,gate,require,Rejected=reload.base,reload.gate,reload.require,reload.Rejected
PINS,MANUAL,POLICIES,EXPECTED=reload.PINS,reload.MANUAL,reload.POLICIES,reload.EXPECTED
PROFILE,WORKER=reload.PROFILE,reload.WORKER
ROOT='/var/tmp/crg-business-pressure167-20261111'
NS='crg-vendor-lab-pressure167-20261111'
RUN='20261111167'
TOOLS='/var/tmp/crg-memory167-tools-20261111'
API=TOOLS+'/vendor-api-timed.py'
ENGINE=TOOLS+'/vendor-engine-timed.py'
PRESSURE_WORKER=TOOLS+'/vendor-memory-pressure-worker-v2.py'
PRESSURE_SHA='741a1aaaecef91bb54a06bdd6af3bf76f5f8e1ad17c25bbdee4c868fddd3daff'
PRESSURE_CONTRACT={'old_memory_percent': 30, 'requested_memory_percent': 20, 'old_memory_bytes': 20001980416, 'requested_memory_bytes': 13334654976, 'chunk_bytes': 67108864, 'maximum_helper_bytes': 12884901888, 'group_reserve_below_old_limit_bytes': 2147483648, 'pressure_above_target_bytes': 268435456, 'helper_lease_seconds': 10, 'helper_lifetime_seconds': 240, 'prepare_seconds': 60, 'defer_wait_seconds': 60, 'hold_seconds': 6, 'retry_wait_seconds': 60, 'total_intervals_each_role': 11, 'total_main_checks': 32, 'configuration_write_reference': 'before-mutation'}

THREAD_CONTRACT={'schema': 'crg-pressure-thread-session-contract-v1', 'observer_sha256': 'ac5dd6b7293949a6ea25da99fbcc8048b4ef628ddaba2c7be61a8c7536d579f1', 'session_sha256': '35f65518ce56f5b889c82041a1c45c87d9f3284ab6bd59cc39752bf78fdc8bce', 'session_selftest_sha256': '520d790872a095f9762e70775a130bc0cf4a544b1db38d176b796090aa085424', 'session_qualification': '/var/tmp/crg-thread165-tools-20261111/qualification.json', 'session_qualification_sha256': '6e43bfbb71141f3ce264ea36c239c28e670e28620d18d4d8f7d13cd816c10929', 'observer_qualification': '/var/tmp/crg-thread155-tools-20261111/qualification.json', 'observer_qualification_sha256': 'b305850e2a463e206ba0b13ae1ed7273c15c7a7131b95e9dc1361dda1aa14b83', 'prior_failed_report': '/var/tmp/crg-business-pressure142-20261111/report.json', 'prior_failed_report_sha256': '55fe93aef6b6469f6ad107680020cd47af626c844f4f09b9c3dcc51a1ad8fede', 'prior_DBS_short_observation': '/var/tmp/crg-thread157-live-20261111/dbs-threads.json', 'prior_DBS_short_observation_sha256': '2b13ca6b27ebcba7972fc805d0cc033f3ebcf4c223cef74cb682ef441e78cfe7', 'prior_HIS_short_observation': '/var/tmp/crg-thread158-live-20261111/hisdbs-threads.json', 'prior_HIS_short_observation_sha256': '3b3317ed2889985682e8abd0c6092a8cee8cd4756c65c54791d260475711ba0c', 'duration_seconds': 900, 'maximum_report_bytes': 33554432, 'maximum_threads': 64, 'sample_period_seconds': 1, 'listener_port': 8090, 'start_before_engine_and_pressure': True, 'start_handshake_seconds': 15, 'term_wait_seconds': 15, 'kill_wait_seconds': 5, 'whole_child_CPU_source': 'wait4-specific-child', 'business_error_precedence': True, 'business_quotas_and_SLA_unchanged': True}
THREAD_OBSERVER=TOOLS+'/vendor-thread-observer.py'
THREAD_SESSION=here/'vendor-thread-session.py'
require(gate.digest(THREAD_SESSION)['sha256']==THREAD_CONTRACT['session_sha256'],'FROZEN_THREAD_SESSION')
spec=importlib.util.spec_from_file_location('thread_session_frozen',THREAD_SESSION)
session=importlib.util.module_from_spec(spec);spec.loader.exec_module(session)

def rebind(function,**bindings):
    require(not function.__code__.co_freevars,'FROZEN_FUNCTION_CLOSURE')
    return types.FunctionType(function.__code__,dict(function.__globals__,**bindings),function.__name__,function.__defaults__)

def checked_plan(path,expected):
    p,actual=gate.read_json(path)
    require(actual==expected and re.fullmatch(r'[0-9a-f]{64}',expected),'PLAN_DIGEST')
    require(p.get('schema')=='crg-business-memory-pressure-threads-plan-v1' and p.get('mode')=='memory-pressure-threads'
        and p.get('work_root')==ROOT and p.get('namespace')==NS and p.get('run_id')==RUN
        and p.get('pins')==PINS and p.get('criteria')==base.CRITERIA and p.get('policies')==POLICIES
        and p.get('numeric_readbacks')==EXPECTED and p.get('pressure_contract')==PRESSURE_CONTRACT and p.get('pressure_worker')==PRESSURE_WORKER and p.get('pressure_worker_sha256')==PRESSURE_SHA
        and p.get('thread_contract')==THREAD_CONTRACT and p.get('thread_observer')==THREAD_OBSERVER
        and p.get('executor_sha256')==gate.digest(Path(__file__))['sha256']
        and p.get('reload_executor_sha256')==RELOAD_SHA and p.get('timed_api_sha256')==API_SHA
        and p.get('timed_engine_sha256')==TIMED_ENGINE_SHA,'PLAN_CONTRACT')
    require(p.get('worker')==WORKER and p.get('engine')==ENGINE and p.get('timed_api')==API
        and p.get('profile')==PROFILE and p.get('previous_binary')=='/var/tmp/crg-r71-20261111/binaries/previous','TOOL_BINDINGS')
    old=gate.read_json(Path('/var/tmp/crg-reload95-tools-20261111/reload-plan.json'))[0]
    require(p.get('roles')==old['roles'],'SOURCE_ROLE_BINDINGS')
    for path,want in [(THREAD_OBSERVER,THREAD_CONTRACT['observer_sha256']),
        (here/'vendor-thread-session-checks.py',THREAD_CONTRACT['session_selftest_sha256']),(PRESSURE_WORKER,PRESSURE_SHA),(API,API_SHA),(ENGINE,TIMED_ENGINE_SHA),(reload.ENGINE,PINS['engine']),
        (WORKER,PINS['worker']),(PROFILE,PINS['profile']),(p['previous_binary'],PINS['previous'])]:
        require(gate.digest(Path(path))['sha256']==want,'FROZEN_SOURCE')
    mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:')))*1024
    require(mem==66673278976 and Path('/sys/devices/system/cpu/online').read_text().strip()=='0-23'
        and os.sysconf('SC_PAGE_SIZE')==4096 and int(mem*.20)//4096*4096==PRESSURE_CONTRACT['requested_memory_bytes'],'NODE_CAPACITY')
    return p

def readiness(plan):
    previous=Path('/var/tmp/crg-business-timing100-20261111/report.json')
    data,digest=gate.read_json(previous)
    require(digest=='30fee708a27bde928218b091d5fed694511bec1e1c0294373afcd3bb9f411fe0'
        and data['phase']=='passed' and len(data['tests'])==26 and all(x['passed'] for x in data['tests'])
        and data['namespace_absent'] and data['original_config_bytes_and_profile_absence_restored'],'PREVIOUS_TIMING_TERMINAL')
    tools=Path('/var/tmp/crg-timing100-tools-20261111')
    launch=gate.read_json(tools/'timing-launch.json')[0];worker=gate.read_json(tools/'timing-worker.json')[0];receipt=gate.read_json(tools/'timing.exit.json')[0]
    require(receipt['exit']==0 and not gate.proc(launch['pid'],launch['entry'],launch['start_ticks'])['live']
        and not gate.proc(worker['pid'],worker['entry'],worker['start_ticks'])['live']
        and gate.namespace('crg-vendor-lab-timing100-20261111') is None,'PREVIOUS_TIMING_NOT_GONE')
    failed_path=Path('/var/tmp/crg-business-edges113-20261111/report.json')
    failed,failed_sha=gate.read_json(failed_path)
    require(failed_sha=='64dcccdedd1cba727a46cf29555a388fd08650493934fbcf98cf869301a419ac'
        and failed['phase']=='failed' and failed['reason']=='RELOAD_DEADLINE_directory-source-recovery-keeps-generation9'
        and len(failed['tests'])==17 and failed['namespace_absent'] and failed['original_config_bytes_and_profile_absence_restored'],
        'PRIOR_EDGE_FAILURE_NOT_RETAINED')
    failed_tools=Path('/var/tmp/crg-edges113-tools-20261111')
    old_launch=gate.read_json(failed_tools/'edges-launch.json')[0];old_worker=gate.read_json(failed_tools/'edges-worker.json')[0]
    receipt=gate.read_json(failed_tools/'edges.exit.json')[0]
    require(receipt['exit']==1 and not gate.proc(old_launch['pid'],old_launch['entry'],old_launch['start_ticks'])['live']
        and not gate.proc(old_worker['pid'],old_worker['entry'],old_worker['start_ticks'])['live']
        and gate.namespace('crg-vendor-lab-edges113-20261111') is None
        and all(not Path(boot['cgroup']).exists() for item in failed['roles'].values() for boot in item['boots']),
        'PRIOR_FAILED_EDGE_PROCESSES_OR_GROUPS_PRESENT')
    pressure_prior=Path('/var/tmp/crg-business-edges120-20261111/report.json')
    old,old_sha=gate.read_json(pressure_prior)
    require(old_sha=='46adac562c07546007013c301a610e15029544d39f50a23546fd199c853370c3'
        and old['phase']=='failed' and old['reason']=='ENGINE_CONTENT' and len(old['tests'])==24
        and old['namespace_absent'] and old['original_config_bytes_and_profile_absence_restored'],'R120_FAILURE_NOT_RETAINED')
    old_tools=Path('/var/tmp/crg-edges120-tools-20261111')
    launch=gate.read_json(old_tools/'edges-launch.json')[0];worker=gate.read_json(old_tools/'edges-worker.json')[0]
    receipt=gate.read_json(old_tools/'edges.exit.json')[0]
    require(receipt['exit']==1 and receipt['executor_sha256']=='69ba8d1024973f29a21accfaa14492bb8d16358f2e3210f8f57c1a2b2423915e'
        and not gate.proc(launch['pid'],launch['entry'],launch['start_ticks'])['live']
        and not gate.proc(worker['pid'],worker['entry'],worker['start_ticks'])['live']
        and gate.namespace('crg-vendor-lab-edges120-20261111') is None
        and all(not Path(boot['cgroup']).exists() for role in old['roles'].values() for boot in role['boots']),'R120_NOT_CLEAN')
    prior,prior_sha=gate.read_json(Path('/var/tmp/crg-business-pressure130-20261111/report.json'))
    require(prior_sha=='d023490de3075ad6efadcec9c339012d7a6b99d197b8425e2a55dd30793fe795'
        and prior['phase']=='failed' and prior['reason']=='PRESSURE_HELPER_CONTRACT' and len(prior['tests'])==10
        and prior['namespace_absent'] and prior['original_config_bytes_and_profile_absence_restored'],'R130_FAILURE_NOT_RETAINED')
    prior_tools=Path('/var/tmp/crg-memory130-tools-20261111')
    launch=gate.read_json(prior_tools/'pressure-launch.json')[0];worker=gate.read_json(prior_tools/'pressure-worker.json')[0]
    receipt=gate.read_json(prior_tools/'pressure.exit.json')[0]
    require(receipt['exit']==1 and not gate.proc(launch['pid'],launch['entry'],launch['start_ticks'])['live']
        and not gate.proc(worker['pid'],worker['entry'],worker['start_ticks'])['live']
        and gate.namespace('crg-vendor-lab-pressure130-20261111') is None
        and all(not Path(boot['cgroup']).exists() for item in prior['roles'].values() for boot in item['boots']),'R130_NOT_CLEAN')
    runtime,runtime_sha=gate.read_json(Path('/var/tmp/crg-python137-20261111/report.json'))
    runtime_launch=gate.read_json(prior_tools/'python137-launch.json')[0]
    require(runtime_sha=='b428c37efa823fbd983190850fa26d5af2b3226ddbcf0047c5506b72d5b38c04' and runtime['phase']=='passed' and runtime['namespace_absent']
        and runtime['source_sha256']==PRESSURE_SHA and len(runtime['roles'])==2
        and all(len(item['checks'])==8 and all(check['passed'] for check in item['checks']) for item in runtime['roles'].values())
        and runtime['Linux_host_selftest']['exit']==0 and not gate.proc(runtime_launch['pid'],runtime_launch['entry'],runtime_launch['start_ticks'])['live']
        and gate.namespace('crg-vendor-lab-python137-20261111') is None,'LEGACY_RUNTIME_QUALIFICATION')
    prior,prior_sha=gate.read_json(Path(THREAD_CONTRACT['prior_failed_report']))
    require(prior_sha==THREAD_CONTRACT['prior_failed_report_sha256'] and prior['phase']=='failed'
        and prior['reason']=='NATIVE_COMPLETION_EXIT' and len(prior['tests'])==13
        and prior['namespace_absent'] and prior['original_config_bytes_and_profile_absence_restored'],'R142_FAILURE_NOT_RETAINED')
    prior_tools=Path('/var/tmp/crg-memory142-tools-20261111')
    launch=gate.read_json(prior_tools/'pressure-launch.json')[0];worker=gate.read_json(prior_tools/'pressure-worker.json')[0]
    receipt=gate.read_json(prior_tools/'pressure.exit.json')[0]
    require(receipt['exit']==1 and not gate.proc(launch['pid'],launch['entry'],launch['start_ticks'])['live']
        and not gate.proc(worker['pid'],worker['entry'],worker['start_ticks'])['live']
        and gate.namespace('crg-vendor-lab-pressure142-20261111') is None
        and all(not Path(boot['cgroup']).exists() for item in prior['roles'].values() for boot in item['boots']),'R142_NOT_CLEAN')
    for key in ['session_qualification','observer_qualification']:
        value,digest=gate.read_json(Path(THREAD_CONTRACT[key]))
        require(digest==THREAD_CONTRACT[key+'_sha256'] and value['exit']==0 and not value['stderr'],'THREAD_QUALIFICATION_DIGEST')
        result=value['result'] if key=='session_qualification' else value['checks_result']
        require(result['phase']=='passed' and len(result['checks'])==(14 if key=='session_qualification' else 19)
            and all(i['passed'] for i in result['checks']),'THREAD_QUALIFICATION_CHECKS')
        if key=='session_qualification':
            require(result['selftest_target_gone'] and value['source_sha256']['vendor-thread-session.py']==THREAD_CONTRACT['session_sha256']
                and all(i['observer_original_instance_gone'] for i in result['records'].values()),'THREAD_SESSION_QUALIFIED_SOURCE')
    for key in ['prior_DBS_short_observation','prior_HIS_short_observation']:
        raw=Path(THREAD_CONTRACT[key]).read_bytes();require(len(raw)<33554432 and hashlib.sha256(raw).hexdigest()==THREAD_CONTRACT[key+'_sha256'],'THREAD_SHORT_OBSERVATION')
        value=json.loads(raw);require(value['phase']=='observed' and value['sample_count']==16 and value['target_signals_or_control_writes']==0,'THREAD_SHORT_OBSERVATION_CHECKS')
    result=rebind(reload.readiness,ROOT=ROOT,NS=NS)(plan)
    result['scope']='read-only exact30-to20 pressure prerequisites; prior failures retained'
    return result

class Execution(reload.Execution):
    def __init__(self,plan,digest):
        super().__init__(plan,digest)
        self.report.update(schema='crg-business-memory-pressure-threads-report-v1',mode='memory-pressure-threads',
            executor_sha256=gate.digest(Path(__file__))['sha256'],base_reload_executor_sha256=RELOAD_SHA,
            timed_engine_sha256=TIMED_ENGINE_SHA,timed_api_sha256=API_SHA,pressure_contract=PRESSURE_CONTRACT,pressure_worker_sha256=PRESSURE_SHA,thread_contract=THREAD_CONTRACT,
            scope='original business600s plus original7 transitions and exact memory30-to20 above-target pressure/release/retry; R120/R130 failures and other cases remain separate; qualified legacy-compatible helper',
            historical_failure_resolved=False)

    def write_config(self,folder,value,symlink=False):
        # Timestamp the causal mutation, before fsync/rename can already trigger
        # an accepted status. Do not require a redundant identical-policy write.
        began=time.time_ns()
        super().write_config(folder,value,symlink)
        return began

    def business_native(self, role, folder, group, row):
        record={};row['thread_observer']=record
        self.thread_session=session.Session(THREAD_OBSERVER,THREAD_CONTRACT['observer_sha256'],self.root,role,record)
        def finish():
            try:
                self.thread_session.stop()
                if record['phase']=='collected':
                    covered=[*row.get('reload_intervals',[])]
                    if 'engine_interval' in row:covered.append(row['engine_interval'])
                    record['engine_and_reload_interval_envelopes_covered']=bool(covered) and all(
                        record['first_sample_epoch']<=i['started_epoch']<=i['ended_epoch']<=record['last_sample_epoch'] for i in covered)
                    require(record['engine_and_reload_interval_envelopes_covered'],'THREAD_INTERVAL_ENVELOPE')
                    record['sampling_gaps_and_missing_fields_require_separate_review']=True
            finally:self.save()
        def diagnostic_error(error):
            record['cleanup_or_coverage_error']=str(error) if isinstance(error,(Rejected,session.Rejected)) else type(error).__name__
            self.save()
        try:
            return session.preserve_business_error(lambda:self._business_native_original(role,folder,group,row),finish,diagnostic_error)
        except session.Rejected as error:raise Rejected('THREAD_SESSION_'+str(error)) from error

    def _business_native_original(self, role, folder, group, row):
        _,cid,_,actual_group=self.identity(role);require(actual_group==group,'EDGE_TIMING_OWN_GROUP')
        api_entry='/tmp/crg-timed-api-'+self.plan['run_id']+('0' if role=='dbs' else '1')+'00.py'
        self.ex(role,'/bin/bash','-c','set -Ce; umask 077; cat > '+api_entry+'; chmod 0444 '+api_entry,data=Path(API).read_text())
        require(self.ex(role,'sha256sum',api_entry).stdout.split()[0]==API_SHA,'EDGE_TIMED_API_COPY')
        context=self.root/(role+'-timing-context.json')
        with context.open('x') as stream:
            os.chmod(context,0o600);json.dump({'cgroup':str(group),'container_id':cid},stream)
        run_id = self.plan['run_id']+('0' if role == 'dbs' else '1')
        entry = '/tmp/crg-business-reload-'+run_id+'.py'
        self.ex(role, '/bin/bash', '-c', 'set -Ce; umask 077; cat > '+entry+'; chmod 0444 '+entry,
                data=Path(WORKER).read_text())
        require(self.ex(role, 'sha256sum', entry).stdout.split()[0] == PINS['worker'], 'WORKER_COPY')
        self.worker_log = (self.root/(role+'-native.log')).open('x')
        self.worker = subprocess.Popen(['kubectl', 'exec', '-n', self.ns, role+'-business', '-c', role, '--',
            'su', '-', 'postgres', '-c', 'CRG_VENDOR_SOAK_TEST=disposable-loopback-only python '+entry+
            ' --run-id '+run_id+' --seconds 600 --test-phase smoke'], stdin=subprocess.DEVNULL,
            stdout=self.worker_log, stderr=self.worker_log)
        load = folder/('postgresql/basebackup/crg-soak-'+run_id+'/load.json');deadline = time.monotonic()+360
        while time.monotonic() < deadline:
            require(self.worker.poll() is None, 'NATIVE_PREPARATION_EXIT')
            if load.exists() and gate.read_json(load)[0].get('phase') == 'running':break
            self.reserve();time.sleep(1)
        else:raise Rejected('NATIVE_PREPARATION_360S')
        started = gate.audit.timestamp(gate.read_json(load)[0]['started_utc'])
        _, _, host_pid, actual_group = self.identity(role);require(actual_group == group, 'OWN_GROUP')
        pid1_ticks = Path('/proc', str(host_pid), 'stat').read_text().rsplit(')',1)[1].split()[19]
        agents = self.processes(group, '/opt/crg/crg');caches = self.processes(group, '/opt/ccg/bin/containercacheguard')
        require(len(agents) == len(caches) == 1 and agents[0][2] == PINS['binary'], 'ONE_AGENT_CACHE')
        profile = folder/'crg-config/io-profile.json';profile_mtime = profile.stat().st_mtime_ns
        fixed = base.controls(group);expected = dict(fixed);intervals = row['reload_intervals']
        status = folder/'resource-state/status.json';samples = row['samples'];next_sample = [0]
        self.thread_session.start(session.listener_owner(group),group,THREAD_CONTRACT['duration_seconds']);self.save()
        def same():
            self.reserve()
            require(self.processes(group, '/opt/crg/crg') == agents and self.processes(group, '/opt/ccg/bin/containercacheguard') == caches
                    and Path('/proc', str(host_pid), 'stat').read_text().rsplit(')',1)[1].split()[19] == pid1_ticks
                    and int(dict(x.split() for x in (group/'memory.events').read_text().splitlines())['oom_kill']) == 0
                    and base.controls(group) == expected, 'PROCESS_OR_KERNEL_CHANGE')
            if time.monotonic() >= next_sample[0]:
                samples.append({'epoch':time.time(), 'actual_kernel_readbacks':base.controls(group), 'same_processes':True})
                next_sample[0]=time.monotonic()+60;self.save()
        def active():
            require(self.worker.poll() is None and time.time() < started+600, 'RELOAD_NATIVE_ENVELOPE')
        def wait_policy(name, policy, numeric, generation, symlink=False, rejected=None):
            nonlocal expected
            active();began = time.time();before = gate.read_json(status)[0];mark = self.write_config(folder, policy, symlink)
            deadline = time.monotonic()+60
            while time.monotonic() < deadline:
                active();self.reserve();d = gate.read_json(status)[0]
                cfg = d.get('configuration', {})
                fresh = status.stat().st_mtime_ns > mark
                if rejected:
                    ok = cfg.get('state') == 'rejected' and rejected in cfg.get('error','') and cfg.get('generation') == generation
                else:
                    ok = d.get('state') == 'managed' and cfg.get('state') == 'accepted' and cfg.get('generation') == generation
                    if 'cpu_percent' in policy:ok = ok and d.get('plan',{}).get('percentages') == policy
                    else:ok = ok and d.get('plan',{}).get('resource_mode') == 'manual'
                if fresh and ok:break
                time.sleep(.25)
            else:raise Rejected('RELOAD_DEADLINE_'+name)
            expected = dict(expected, **numeric);same()
            actual = base.controls(group)
            require(d['plan']['environment']['identity'] == row['identity'], 'STATUS_IDENTITY')
            if rejected:
                require(d['state']=='degraded' and cfg['accepted_hash']==before['configuration']['accepted_hash']
                        and d['plan']['percentages']==POLICIES[1], 'REJECTED_FULL_POLICY_RETENTION')
            interval = {'case':name, 'started_epoch':began, 'ended_epoch':time.time(), 'generation':generation,
                        'configuration_state':cfg['state'], 'requested_policy': policy if isinstance(policy,dict) else 'malformed JSON',
                        'expected_numeric':dict(expected), 'actual_kernel_readbacks':actual,
                        'same_Agent_PID1_cache':True, 'PG_not_restarted':self.sql(role,'SELECT pg_postmaster_start_time();') == row['primary_start']}
            intervals.append(interval)
            self.check(role+'-'+name, interval['PG_not_restarted'] and actual == expected)
        def edge_interval(name, began, d, extra=None):
            actual=base.controls(group)
            require(actual==expected and d['plan']['environment']['identity']==row['identity'],'EDGE_KERNEL_OR_IDENTITY')
            interval={'case':name,'started_epoch':began,'ended_epoch':time.time(),
                'generation':d['configuration']['generation'],'configuration_state':d['configuration']['state'],
                'accepted_hash':d['configuration']['accepted_hash'],'expected_numeric':dict(expected),
                'actual_kernel_readbacks':actual,'same_Agent_PID1_cache':True,
                'PG_not_restarted':self.sql(role,'SELECT pg_postmaster_start_time();')==row['primary_start']}
            if extra:interval.update(extra)
            intervals.append(interval);self.check(role+'-'+name,interval['PG_not_restarted'])

        def pressure30to20():
            nonlocal expected
            active();began=time.time();target=13334654976;policy=dict(POLICIES[0],memory_percent=20)
            high=int(EXPECTED[0]['memory.max']);chunk=64<<20;maximum=12<<30;ceiling=high-(2<<30)
            entry='/tmp/crg-memory-pressure-'+self.plan['run_id']+('0' if role=='dbs' else '1')+'.py'
            self.ex(role,'/bin/bash','-c','set -Ce; umask 077; cat > '+entry+'; chmod 0444 '+entry,data=Path(PRESSURE_WORKER).read_text())
            require(self.ex(role,'sha256sum',entry).stdout.split()[0]==PRESSURE_SHA,'PRESSURE_HELPER_COPY')
            log=(self.root/(role+'-pressure-helper.log')).open('x');holder=None;owned=None;allocated=0
            record={'started_epoch':began,'target_memory_bytes':target,'old_memory_limit':high,'events':[],'host_samples':[],
                    'worker_sha256':PRESSURE_SHA,'maximum_helper_bytes':maximum,'maximum_group_bytes':ceiling,
                    'host_reserve_bytes':base.CRITERIA['steady_host_available_bytes'],'direct_control_file_writes':False}
            row['pressure30to20']=record;self.save()
            def recv(timeout=5):
                ready,_,_=select.select([holder.stdout],[],[],timeout)
                require(bool(ready),'PRESSURE_HELPER_RESPONSE_5S')
                line=holder.stdout.readline(4097)
                require(line.endswith('\n') and len(line)<=4096,'PRESSURE_HELPER_BOUNDED_RESPONSE')
                return json.loads(line)
            def send(op):
                holder.stdin.write(json.dumps({'op':op})+'\n');holder.stdin.flush();reply=recv()
                require(reply.get('phase')=='ack' and reply.get('op')==op,'PRESSURE_HELPER_ACK')
                record['events'].append(dict(reply,observed_epoch=time.time()));return reply
            def holder_live():
                require(holder.poll() is None and owned is not None and gate.proc(owned['pid'],entry,owned['start_ticks'])['live'],'PRESSURE_HELPER_IDENTITY')
            def safe_snapshot(require_high=False):
                active();self.reserve();holder_live();send('ping')
                current=int((group/'memory.current').read_text());available=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024
                require(current<ceiling and available>=base.CRITERIA['steady_host_available_bytes'],'PRESSURE_BUDGET_OR_RESERVE')
                if require_high:require(current>target,'PRESSURE_NOT_ABOVE_REAL_20_PERCENT')
                same();sample={'epoch':time.time(),'memory_current':current,'host_available':available,'allocated_bytes':allocated}
                record['host_samples'].append(sample);return current,available
            try:
                holder=subprocess.Popen(['kubectl','exec','-i','-n',self.ns,role+'-business','-c',role,'--','env',
                    'CRG_MEMORY_PRESSURE_TEST=authorized-disposable-loopback-only','python','-u',entry],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,bufsize=1)
                hello=recv();record['hello']=hello;self.save();require(hello.get('phase')=='ready' and hello.get('maximum_bytes')==maximum and hello.get('chunk_bytes')==chunk
                    and hello.get('lease_seconds')==10 and hello.get('lifetime_seconds')==240,'PRESSURE_HELPER_CONTRACT')
                found=[]
                for pid in (group/'cgroup.procs').read_text().splitlines():
                    try:
                        proc=Path('/proc',pid);args=(proc/'cmdline').read_bytes().split(b'\0');fields=(proc/'stat').read_text().rsplit(')',1)[1].split()
                        if entry.encode() in args and fields[0]!='Z':found.append({'pid':int(pid),'start_ticks':int(fields[19]),'entry':entry})
                    except (FileNotFoundError,ProcessLookupError):pass
                require(len(found)==1,'ONE_OWN_PRESSURE_HELPER');owned=found[0];record['process']=owned;record['hello']=hello
                deadline=time.monotonic()+60
                while time.monotonic()<deadline:
                    current,available=safe_snapshot()
                    if current>target+(256<<20):break
                    require(current+chunk<ceiling and available>=base.CRITERIA['steady_host_available_bytes']+chunk+(256<<20)
                        and allocated+chunk<=maximum,'PRESSURE_NEXT_CHUNK_UNSAFE')
                    ack=send('allocate');allocated+=chunk;require(ack['allocated_bytes']==allocated,'PRESSURE_ALLOCATION_ACK')
                else:raise Rejected('REAL_20_PERCENT_PRESSURE_PREPARATION_60S')
                safe_snapshot(True);mark=self.write_config(folder,policy);deadline=time.monotonic()+60
                while time.monotonic()<deadline:
                    safe_snapshot(True);d=gate.read_json(status)[0];cfg=d.get('configuration',{})
                    memory=next((i for i in d.get('items',[]) if i['file']=='memory.max'),{})
                    if status.stat().st_mtime_ns>mark and cfg.get('state')=='accepted' and cfg.get('generation')==7 and d.get('state')=='degraded' and memory.get('state')=='skipped' and memory.get('reason_code')=='memory_safety' and memory.get('value')==str(target):break
                    time.sleep(.25)
                else:raise Rejected('REAL_MEMORY30_TO20_DEFER_60S')
                require(d['plan']['percentages']==policy,'REAL_20_PERCENT_REQUEST_VISIBLE')
                hold=time.monotonic()+6
                while time.monotonic()<hold:safe_snapshot(True);time.sleep(.25)
                journal=gate.read_json(folder/'resource-state/journal.json')[0]['mutations']['memory.max:']
                require(journal['applied']==str(high) and not journal.get('pending') and not journal.get('conflict'),'REAL_20_PERCENT_UNSAFE_WRITE_INTENT')
                accepted_hash=cfg['accepted_hash'];record.update(requested_policy=policy,accepted_hash=accepted_hash,mutation_mark_ns=mark,
                    status_mtime_ns=status.stat().st_mtime_ns,hold_seconds=6,journal_during_pressure=journal)
                edge_interval('memory30-to20-deferred-above-real-target',began,d,{'requested_policy':policy,'target_memory_bytes':target,'memory_reason_code':'memory_safety','hold_seconds':6})
                release_started=time.time();ack=send('release');require(ack['allocated_bytes']==0,'PRESSURE_RELEASE_ACK')
                require(send('exit')['allocated_bytes']==0,'PRESSURE_EXIT_ACK');released=recv()
                require(released['phase']=='released' and released['allocated_bytes']==0 and holder.wait(timeout=5)==0,'PRESSURE_RELEASE_EXIT')
                require(not gate.proc(owned['pid'],entry,owned['start_ticks'])['live'],'PRESSURE_WORKER_NOT_GONE')
                record.update(released=released,release_started_epoch=release_started,worker_gone_after_release=True)
                deadline=time.monotonic()+60;transition=[]
                while time.monotonic()<deadline:
                    active();self.reserve();d=gate.read_json(status)[0];actual=base.controls(group);cfg=d.get('configuration',{})
                    require(self.processes(group,'/opt/crg/crg')==agents and self.processes(group,'/opt/ccg/bin/containercacheguard')==caches
                        and Path('/proc',str(host_pid),'stat').read_text().rsplit(')',1)[1].split()[19]==pid1_ticks
                        and int(dict(s.split() for s in (group/'memory.events').read_text().splitlines())['oom_kill'])==0,'PRESSURE_RELEASE_PROCESS_OR_OOM')
                    require(all(actual[k]==expected[k] for k in base.CONTROLS if k!='memory.max')
                        and actual['memory.max'] in [str(high),str(target)],'PRESSURE_RELEASE_OTHER_CONTROL_CHANGE')
                    current=int((group/'memory.current').read_text());transition.append({'epoch':time.time(),'memory_current':current,'memory_max':actual['memory.max']})
                    if actual['memory.max']==str(target) and d.get('state')=='managed' and cfg.get('state')=='accepted' and cfg.get('generation')==7:
                        require(cfg['accepted_hash']==accepted_hash and d['plan']['percentages']==policy,'PRESSURE_RETRY_POLICY_OR_GENERATION')
                        require(current+current//20+(16<<20)<=target,'PRESSURE_RETRY_WITHOUT_MEMORY_HEADROOM');break
                    time.sleep(.25)
                else:raise Rejected('REAL_MEMORY20_RETRY_AFTER_RELEASE_60S')
                expected=dict(expected,**{'memory.max':str(target)});same();record['release_observations']=transition
                edge_interval('memory20-retry-applies-same-generation7-after-release',release_started,d,
                    {'requested_policy':policy,'target_memory_bytes':target,'accepted_hash_before_release':accepted_hash,'no_configuration_rewrite':True,'pressure_worker_gone':True})
            finally:
                if holder is not None:
                    if holder.poll() is None:
                        if holder.stdin and not holder.stdin.closed:holder.stdin.close()
                        try:holder.wait(timeout=15)
                        except subprocess.TimeoutExpired:
                            holder.terminate()
                            try:holder.wait(timeout=5)
                            except subprocess.TimeoutExpired:holder.kill();holder.wait(timeout=5)
                            record['kubectl_cleanup_forced']=True
                    if owned is not None:record['worker_gone_on_final_check']=not gate.proc(owned['pid'],entry,owned['start_ticks'])['live']
                log.close();record['ended_epoch']=time.time();self.save()
                if owned is not None:require(record['worker_gone_on_final_check'],'PRESSURE_MEMORY_RELEASE_NOT_PROVEN')


        # Preserve the smoke campaign's original 30-second engine scheduling.
        while time.time() < started+30:active();same();time.sleep(max(0,min(1, started+30-time.time())))
        engine_dir = self.root/(role+'-engine');self.engine_log = (self.root/(role+'-engine.log')).open('x')
        engine_began = time.time()
        self.engine_job = subprocess.Popen(['python3', ENGINE, '--namespace', self.ns, '--work-dir', str(engine_dir),
            '--run-id', run_id+'00', '--cleanup-fixture', '--native-campaign-probes', '--role', role],
            stdin=subprocess.DEVNULL, stdout=self.engine_log, stderr=self.engine_log)
        wait_policy('manual-to-percent-during-engine', POLICIES[0], EXPECTED[0], 2)
        require(self.engine_job.poll() is None, 'NO_ENGINE_RELOAD_OVERLAP')
        wait_policy('three-independent-percentages-during-native', POLICIES[1], EXPECTED[1], 3)
        wait_policy('invalid-IO-retains-entire-policy', dict(POLICIES[1],io_percent=101), {}, 3, rejected='io_percent')
        wait_policy('partial-JSON-retains-entire-policy', b'{"cpu_percent":', {}, 3, rejected='EOF')
        wait_policy('duplicate-key-retains-entire-policy', b'{"cpu_percent":25,"cpu_percent":30}', {}, 3, rejected='duplicate')
        wait_policy('ConfigMap-style-symlink-accepts-valid-policy', POLICIES[0], EXPECTED[0], 4, symlink=True)
        wait_policy('percent-to-manual-three-resources', MANUAL, {k:fixed[k] for k in base.CONTROLS[:3]}, 5)
        wait_policy('pressure-test-return-to-percent30',POLICIES[0],EXPECTED[0],6)
        pressure30to20()
        wait_policy('released-memory20-returns-to-percent30',POLICIES[0],EXPECTED[0],8)

        end_deadline = time.monotonic()+720
        while self.worker.poll() is None and time.monotonic() < end_deadline:
            same()
            if self.engine_job.poll() is not None and 'engine' not in row:
                self.engine_log.close();self.engine_log=None
                engine, _ = gate.read_json(engine_dir/'business-backup.json');item=engine['roles'][role]
                require(self.engine_job.returncode == 0 and engine['phase'] == 'content-passed-native-pending'
                        and len(item['checks']) == 10 and all(x['passed'] for x in item['checks'])
                        and item.get('own_fixture_schema_restore_database_snapshot_removed') is True, 'ENGINE_CONTENT')
                row['engine']=engine;row['engine_interval']={'started_epoch':engine_began,'ended_epoch':time.time()};self.save()
            require(time.time()-engine_began <= 1800 or self.engine_job.poll() is not None, 'ENGINE_1800S')
            time.sleep(1)
        require(self.worker.poll() == 0, 'NATIVE_COMPLETION_EXIT')
        self.worker_log.close();self.worker_log=None;self.worker=None
        native, _ = gate.read_json(load);row['native']=native;self.save();base.validate_native(native,run_id)
        finish=gate.audit.timestamp(native['measurement_finished_utc'])
        require('engine' in row and self.engine_job.poll() == 0, 'ENGINE_INSIDE_NATIVE_MISSING')
        covered = [*intervals,row['engine_interval']]
        self.check(role+'-600s-native-surrounds-reload-backup-stream-restore',
            len(intervals)==11 and all(started <= x['started_epoch'] <= x['ended_epoch'] <= finish for x in covered)
            and len(samples)>=600/60*.98 and all(b['epoch']-a['epoch']<=120 for a,b in zip(samples,samples[1:]))
            and samples[0]['epoch']-started<=120 and finish-samples[-1]['epoch']<=120)
        row['engine_native_validation']='passed-with-entire-600s-native';self.engine_job=None
        self.check(role+'-same-Agent-PID1-PG-cache-profile-and-zero-OOM',
            self.sql(role,'SELECT pg_postmaster_start_time();')==row['primary_start']
            and gate.digest(profile)['sha256']==PINS['profile'] and profile.stat().st_mtime_ns==profile_mtime)
        same()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--plan-sha256',required=True);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    try:
        require(sys.platform=='linux' and os.geteuid()==0,'LINUX_ROOT')
        plan=checked_plan(args.plan,args.plan_sha256);ready=readiness(plan)
        if not args.execute:print(json.dumps(ready));return 0
        require(os.environ.get('CRG_MEMORY_PRESSURE_THREADS')=='authorized-disposable-test-node-only','EXPLICIT_LAB_MARKER')
        def interrupted(signum,frame):raise KeyboardInterrupt()
        signal.signal(signal.SIGTERM,interrupted);ready=readiness(plan)
        result=Execution(plan,args.plan_sha256).execute(ready)
        require(result['phase']!='passed' or len(result['tests'])==32,'EXPECTED_32_CHECKS')
        print(json.dumps({'phase':result['phase'],'checks':len(result['tests']),'reason':result.get('reason'),'stable_release_accepted':False}))
        return 0 if result['phase']=='passed' and result.get('namespace_absent') and result.get('original_config_bytes_and_profile_absence_restored') else 1
    except BaseException as error:
        print(json.dumps({'phase':'rejected','reason':str(error) if isinstance(error,Rejected) else type(error).__name__,'executed':False}));return 1

if __name__=='__main__':raise SystemExit(main())
