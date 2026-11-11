#!/usr/bin/env python3
"""Disposable DBS/HISDBS reload edge cases under the frozen 600s business gates.

Default is read-only; no product process manages another container. Kernel
memory is never directly lowered by this fixture. Production code is unchanged.
"""
import argparse,ast,datetime,hashlib,importlib.util,json,os,re,signal,stat,subprocess,sys,time,types
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
ROOT='/var/tmp/crg-business-edges113-20261111'
NS='crg-vendor-lab-edges113-20261111'
RUN='20261111113'
TOOLS='/var/tmp/crg-edges113-tools-20261111'
API=TOOLS+'/vendor-api-timed.py'
ENGINE=TOOLS+'/vendor-engine-timed.py'
EDGE_CONTRACT={'unsafe_memory_percent':1,'unsafe_memory_bytes':666730496,'unsafe_hold_seconds':6,
    'stable_window_seconds':6,'source_failure_hold_seconds':3,'source_failure_wait_seconds':60,
    'source_cases':['missing','directory','FIFO','oversized','dangling-symlink'],
    'source_recovery_keeps_generation':9,'total_intervals_each_role':22,'total_main_checks':54}

def rebind(function,**bindings):
    require(not function.__code__.co_freevars,'FROZEN_FUNCTION_CLOSURE')
    return types.FunctionType(function.__code__,dict(function.__globals__,**bindings),function.__name__,function.__defaults__)

def checked_plan(path,expected):
    p,actual=gate.read_json(path)
    require(actual==expected and re.fullmatch(r'[0-9a-f]{64}',expected),'PLAN_DIGEST')
    require(p.get('schema')=='crg-business-reload-edges-plan-v1' and p.get('mode')=='reload-edges'
        and p.get('work_root')==ROOT and p.get('namespace')==NS and p.get('run_id')==RUN
        and p.get('pins')==PINS and p.get('criteria')==base.CRITERIA and p.get('policies')==POLICIES
        and p.get('numeric_readbacks')==EXPECTED and p.get('edge_contract')==EDGE_CONTRACT
        and p.get('executor_sha256')==gate.digest(Path(__file__))['sha256']
        and p.get('reload_executor_sha256')==RELOAD_SHA and p.get('timed_api_sha256')==API_SHA
        and p.get('timed_engine_sha256')==TIMED_ENGINE_SHA,'PLAN_CONTRACT')
    require(p.get('worker')==WORKER and p.get('engine')==ENGINE and p.get('timed_api')==API
        and p.get('profile')==PROFILE and p.get('previous_binary')=='/var/tmp/crg-r71-20261111/binaries/previous','TOOL_BINDINGS')
    old=gate.read_json(Path('/var/tmp/crg-reload95-tools-20261111/reload-plan.json'))[0]
    require(p.get('roles')==old['roles'],'SOURCE_ROLE_BINDINGS')
    for path,want in [(API,API_SHA),(ENGINE,TIMED_ENGINE_SHA),(reload.ENGINE,PINS['engine']),
        (WORKER,PINS['worker']),(PROFILE,PINS['profile']),(p['previous_binary'],PINS['previous'])]:
        require(gate.digest(Path(path))['sha256']==want,'FROZEN_SOURCE')
    mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:')))*1024
    require(mem==66673278976 and Path('/sys/devices/system/cpu/online').read_text().strip()=='0-23'
        and os.sysconf('SC_PAGE_SIZE')==4096 and int(mem*.01)//4096*4096==EDGE_CONTRACT['unsafe_memory_bytes'],'NODE_CAPACITY')
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
    result=rebind(reload.readiness,ROOT=ROOT,NS=NS)(plan)
    result['scope']='read-only edge prerequisites; not long or historical exec acceptance'
    return result

class Execution(reload.Execution):
    def __init__(self,plan,digest):
        super().__init__(plan,digest)
        self.report.update(schema='crg-business-reload-edges-report-v1',mode='reload-edges',
            executor_sha256=gate.digest(Path(__file__))['sha256'],base_reload_executor_sha256=RELOAD_SHA,
            timed_engine_sha256=TIMED_ENGINE_SHA,timed_api_sha256=API_SHA,edge_contract=EDGE_CONTRACT,
            scope='original business600s plus original7 transitions, unsafe memory and stable-window/source-failure cases; no long acceptance',
            historical_failure_resolved=False)

    def business_native(self, role, folder, group, row):
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

        def deferred_memory():
            nonlocal expected
            active();began=time.time();target=666730496;used=int((group/'memory.current').read_text())
            require(used>target,'REAL_USAGE_MUST_EXCEED_UNSAFE_TARGET')
            policy=dict(POLICIES[0],memory_percent=1);mark=self.write_config(folder,policy)
            deadline=time.monotonic()+60;expected=dict(expected,**EXPECTED[0])
            while time.monotonic()<deadline:
                active();self.reserve();d=gate.read_json(status)[0];cfg=d.get('configuration',{})
                memory=next((i for i in d.get('items',[]) if i['file']=='memory.max'),{})
                require((group/'memory.max').read_text().strip()==expected['memory.max'],'UNSAFE_MEMORY_WAS_APPLIED')
                if status.stat().st_mtime_ns>mark and cfg.get('state')=='accepted' and cfg.get('generation')==6 and d.get('state')=='degraded' and memory.get('state')=='skipped' and memory.get('reason_code')=='memory_safety' and memory.get('value')==str(target):break
                time.sleep(.25)
            else:raise Rejected('DANGEROUS_MEMORY_DEFER_60S')
            require(d['plan']['percentages']==policy,'DEFERRED_REQUEST_VISIBLE')
            observed=[];hold=time.monotonic()+6
            while time.monotonic()<hold:
                active();same();current=int((group/'memory.current').read_text())
                require(current>target,'UNSAFE_TARGET_NO_LONGER_EXCEEDS_REAL_USAGE')
                observed.append({'epoch':time.time(),'memory_current':current,'memory_max':(group/'memory.max').read_text().strip()})
                time.sleep(.25)
            journal=gate.read_json(folder/'resource-state/journal.json')[0];mutation=journal['mutations']['memory.max:']
            require(mutation['applied']==expected['memory.max'] and not mutation.get('pending') and not mutation.get('conflict'),'UNSAFE_WRITE_INTENT_OR_CONFLICT')
            edge_interval('unsafe-memory1-accepted-but-kernel-limit-deferred',began,d,
                {'requested_policy':policy,'requested_memory_bytes':target,'memory_reason_code':memory['reason_code'],
                 'hold_observations':observed,'hold_seconds':6,'journal_applied_memory':mutation['applied'],'journal_pending':mutation.get('pending','')})

        def stable_memory():
            nonlocal expected
            active();began=time.time();began_monotonic=time.monotonic();policy=dict(POLICIES[1],memory_stable_seconds=6)
            old_memory=expected['memory.max'];mark=self.write_config(folder,policy);deadline=time.monotonic()+60
            expected=dict(expected,**EXPECTED[1]);expected['memory.max']=old_memory
            while time.monotonic()<deadline:
                active();self.reserve();d=gate.read_json(status)[0];cfg=d.get('configuration',{})
                memory=next((i for i in d.get('items',[]) if i['file']=='memory.max'),{})
                require((group/'memory.max').read_text().strip()==old_memory,'SAFE_WINDOW_NOT_OBSERVED_BEFORE_WRITE')
                if status.stat().st_mtime_ns>mark and cfg.get('state')=='accepted' and cfg.get('generation')==8 and memory.get('state')=='skipped' and memory.get('reason_code')=='memory_window':break
                time.sleep(.25)
            else:raise Rejected('STABLE_WINDOW_PENDING_60S')
            same();edge_interval('safe-memory29-waits-for6s-stable-window',began,d,{'memory_reason_code':memory['reason_code'],'requested_policy':policy})
            observed=[];applied=None;deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                active();self.reserve();d=gate.read_json(status)[0];actual=base.controls(group);now=time.time()
                require(all(actual[k]==expected[k] for k in base.CONTROLS if k!='memory.max'),'WINDOW_OTHER_LIMIT_CHANGED')
                observed.append({'epoch':now,'memory_current':int((group/'memory.current').read_text()),'memory_max':actual['memory.max']})
                if actual['memory.max']==EXPECTED[1]['memory.max']:
                    applied=now;require(time.monotonic()-began_monotonic>=6,'MEMORY_LIMIT_APPLIED_BEFORE_FROZEN_WINDOW')
                    if d.get('state')=='managed' and d['configuration']['generation']==8:break
                else:require(actual['memory.max']==old_memory,'UNEXPECTED_WINDOW_MEMORY_VALUE')
                time.sleep(.25)
            else:raise Rejected('STABLE_WINDOW_APPLY_60S')
            expected=dict(expected,**EXPECTED[1]);same()
            edge_interval('safe-memory29-applies-after-stable-window',began,d,
                {'requested_policy':policy,'observed_applied_epoch':applied,'observed_elapsed_monotonic':time.monotonic()-began_monotonic,'minimum_stable_seconds':6,'observations':observed})

        def failed_source(kind,phrase):
            config=folder/'crg-config/config.json';saved=config.with_name('edges113.saved')
            require(not saved.exists() and not saved.is_symlink() and config.is_file() and not config.is_symlink(),'SOURCE_EDGE_OWNERSHIP')
            active();before=gate.read_json(status)[0];raw=config.read_bytes();began=time.time();config.rename(saved);made=None
            try:
                if kind=='directory':config.mkdir(mode=0o700)
                elif kind=='FIFO':os.mkfifo(config,0o600)
                elif kind=='oversized':
                    with config.open('xb') as stream:os.chmod(config,0o600);stream.write(b' '*(1048576+1));stream.flush();os.fsync(stream.fileno())
                elif kind=='dangling-symlink':config.symlink_to('edges113-never-created.json')
                else:require(kind=='missing','UNKNOWN_EDGE_KIND')
                if kind!='missing':
                    item=config.lstat();made=(item.st_dev,item.st_ino,item.st_mode)
                mark=time.time_ns();deadline=time.monotonic()+60
                while time.monotonic()<deadline:
                    active();same();d=gate.read_json(status)[0];cfg=d.get('configuration',{})
                    if status.stat().st_mtime_ns>mark and d.get('state')=='degraded' and cfg.get('state')=='rejected' and cfg.get('generation')==9 and phrase in cfg.get('error',''):break
                    time.sleep(.25)
                else:raise Rejected('SOURCE_'+kind+'_REJECT_60S')
                require(cfg['accepted_hash']==before['configuration']['accepted_hash'] and d['plan']['percentages']==POLICIES[1],'SOURCE_FAILURE_DISCARDS_LAST_GOOD_POLICY')
                hold=time.monotonic()+3
                while time.monotonic()<hold:active();same();time.sleep(.25)
                edge_interval(kind+'-config-retains-last-good-and-responsive-Agent',began,d,
                    {'source_kind':kind,'rejection_error':cfg['error'],'hold_seconds':3,'last_good_policy':POLICIES[1]})
            finally:
                if made is not None:
                    item=config.lstat();require((item.st_dev,item.st_ino,item.st_mode)==made,'FAULT_SOURCE_REPLACED_EXTERNALLY')
                    if kind=='directory':config.rmdir()
                    else:config.unlink()
                else:require(not config.exists() and not config.is_symlink(),'MISSING_SOURCE_CREATED_EXTERNALLY')
                require(saved.is_file() and not saved.is_symlink() and saved.read_bytes()==raw,'SAVED_SOURCE_CHANGED')
                saved.replace(config)
            wait_policy(kind+'-source-recovery-keeps-generation9',POLICIES[1],EXPECTED[1],9)


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
        deferred_memory()
        wait_policy('unsafe-memory-request-recovery-to-percent30',POLICIES[0],EXPECTED[0],7)
        stable_memory()
        wait_policy('stable-window-config-removal-retains-valid-percent29',POLICIES[1],EXPECTED[1],9)
        for kind,phrase in [('missing','no such file'),('directory','regular file'),('FIFO','regular file'),('oversized','exceeds 1MiB'),('dangling-symlink','no such file')]:failed_source(kind,phrase)


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
            len(intervals)==22 and all(started <= x['started_epoch'] <= x['ended_epoch'] <= finish for x in covered)
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
        require(os.environ.get('CRG_RELOAD_EDGES')=='authorized-disposable-test-node-only','EXPLICIT_LAB_MARKER')
        def interrupted(signum,frame):raise KeyboardInterrupt()
        signal.signal(signal.SIGTERM,interrupted);ready=readiness(plan)
        result=Execution(plan,args.plan_sha256).execute(ready)
        require(result['phase']!='passed' or len(result['tests'])==54,'EXPECTED_54_CHECKS')
        print(json.dumps({'phase':result['phase'],'checks':len(result['tests']),'reason':result.get('reason'),'stable_release_accepted':False}))
        return 0 if result['phase']=='passed' and result.get('namespace_absent') and result.get('original_config_bytes_and_profile_absence_restored') else 1
    except BaseException as error:
        print(json.dumps({'phase':'rejected','reason':str(error) if isinstance(error,Rejected) else type(error).__name__,'executed':False}));return 1

if __name__=='__main__':raise SystemExit(main())
