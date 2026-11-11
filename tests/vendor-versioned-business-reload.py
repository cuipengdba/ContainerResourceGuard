#!/usr/bin/env python3
"""Pinned, disposable DBS/HISDBS business reload qualification, never a manager.

Default is read-only. Original workload, engine deadlines and latency criteria
are unchanged. Each role has one Agent. This is not seven-day acceptance.
"""
import argparse
import copy
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time

sys.dont_write_bytecode = True
BASE_SHA = '9e0c5d5a7cf70949cea08a019e8e89cbdf15d6a99ca6c726b1202693117e1cad'
here = Path(__file__).parent
if hashlib.sha256((here/'vendor-versioned-aged-postflight.py').read_bytes()).hexdigest() != BASE_SHA:
    raise ValueError('FROZEN_BUSINESS_HELPER')
spec = importlib.util.spec_from_file_location('reload_business_base', here/'vendor-versioned-aged-postflight.py')
base = importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
gate, require, Rejected = base.gate, base.require, base.Rejected
PINS = dict(base.PINS, engine='b0d4fe313156743ff1424b46eb58c5ab5b8e1f2c91851420023f5f018dd08e5c',
            profile='00e35e91594ed0ad1075a196c20bd8f4c6628c346c4bd6e901ac05d4cc90ef6b')
ROOT = '/var/tmp/crg-business-reload95-20261111'
NS = 'crg-vendor-lab-reload95-20261111'
PROFILE = '/var/tmp/crg-r30-20261110/actual/v10/config/io-profile.json'
WORKER = '/var/tmp/crg-r78-20261111/tests/vendor-soak-load.py'
ENGINE = '/var/tmp/crg-r78-20261111/tests/vendor-engine-smoke.py'
MANUAL = {'resource_mode': 'manual', 'limits': {'cpu_cores': 7.2, 'memory_max': '20001980416B',
          'io_read_bps': '64MiB', 'io_write_bps': '64MiB', 'io_read_iops': 4096, 'io_write_iops': 4096},
          'data_paths': ['/opt/postgresql']}
POLICIES = [{'cpu_percent': 30, 'memory_percent': 30, 'io_percent': 100},
            {'cpu_percent': 25, 'memory_percent': 29, 'io_percent': 80}]
EXPECTED = [dict(zip(base.CONTROLS[:3], values)) for values in [
    ['720000 100000', '20001980416', '253:0 rbps=64700080 wbps=37470104 riops=83 wiops=135'],
    ['600000 100000', '19335249920', '253:0 rbps=51760064 wbps=29976083 riops=66 wiops=108']]]


def checked_plan(path, expected):
    p, actual = gate.read_json(path)
    require(actual == expected and re.fullmatch(r'[0-9a-f]{64}', expected), 'PLAN_DIGEST')
    require(p.get('schema') == 'crg-versioned-business-reload-plan-v1'
            and p.get('work_root') == ROOT and p.get('namespace') == NS and p.get('run_id') == '20261111095'
            and p.get('pins') == PINS and p.get('criteria') == base.CRITERIA
            and p.get('policies') == POLICIES and p.get('numeric_readbacks') == EXPECTED
            and p.get('executor_sha256') == gate.digest(Path(__file__))['sha256'], 'PLAN_CONTRACT')
    require(p.get('worker') == WORKER and p.get('engine') == ENGINE and p.get('profile') == PROFILE
            and p.get('previous_binary') == '/var/tmp/crg-r71-20261111/binaries/previous', 'TOOL_PATHS')
    require(set(p.get('roles', {})) == {'dbs', 'hisdbs'}, 'ROLE_SET')
    for role, row in p['roles'].items():
        require(row['folder'] == '/var/tmp/crg-realpaths64-20261111/v10-'+role+'-bw64/'+role+'-business'
                and row['aged_run_id'] == '20261111064'+('0' if role == 'dbs' else '1'), 'SOURCE_ROLE')
        gate.path_clean(row['folder'])
    # Independently recompute page rounding and measured rates, never trust the
    # Agent plan itself as the expected numeric kernel value.
    profile, _ = gate.read_json(Path(PROFILE));device = profile['devices'][0]
    require(gate.digest(Path(PROFILE))['sha256'] == PINS['profile'] and len(profile['devices']) == 1
            and profile['version'] == 2 and len(device['measurements']) == 3, 'MEASURED_PROFILE')
    mem = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:')))*1024
    online = Path('/sys/devices/system/cpu/online').read_text().strip()
    cpus = sum(int(x.split('-')[1])-int(x.split('-')[0])+1 if '-' in x else 1 for x in online.split(','))
    page = os.sysconf('SC_PAGE_SIZE')
    for policy, numeric in zip(POLICIES, EXPECTED):
        require(numeric['cpu.max'] == str(int(cpus*policy['cpu_percent']/100*100000))+' 100000'
                and numeric['memory.max'] == str(int(mem*policy['memory_percent']/100)//page*page), 'NODE_CAPACITY_CHANGED')
        rates = ' '.join(k+'='+str(int(device[f]*policy['io_percent']/100)) for k, f in
                         [('rbps','read_bps'), ('wbps','write_bps'), ('riops','read_iops'), ('wiops','write_iops')])
        require(numeric['io.max'] == device['device']+' '+rates, 'INDEPENDENT_IO_NUMBERS')
    for name in ['worker', 'engine']:
        require(gate.digest(Path(p[name]))['sha256'] == PINS[name], 'FROZEN_'+name.upper())
    require(gate.digest(Path(p['previous_binary']))['sha256']==PINS['previous'],'PREVIOUS_BINARY_PIN')
    return p


def readiness(plan):
    require(not Path(ROOT).exists() and gate.namespace(NS) is None, 'FRESH_TARGET')
    proof, digest = gate.read_json(Path(base.SHORT_BINDINGS['rehearsal_proof']))
    require(digest == '66c381e4ecb03513501ba9d92c874d90605fa685921a98a597a5072c1f8002ce'
            and proof['phase'] == 'passed' and proof['namespace_absent'] is True
            and len(proof['tests']) == 12 and all(x['passed'] for x in proof['tests'])
            and proof['sources']['v10']['binary_sha256'] == PINS['binary'], 'SOURCE_BUSINESS_PROOF')
    require(gate.namespace(base.SHORT_BINDINGS['old_namespace']) is None, 'SOURCE_NAMESPACE_PRESENT')
    folders = [Path(row['folder']) for row in plan['roles'].values()]
    base.no_other_mounts(folders)
    for role, row in plan['roles'].items():
        folder = Path(row['folder'])
        require(gate.digest(folder/'pod.json')['sha256'] == row['pod_sha256']
                and gate.digest(folder/'crg/crg')['sha256'] == PINS['binary']
                and gate.digest(folder/'ccg/bin/containercacheguard')['sha256'] == PINS['cache'], 'SOURCE_INPUT')
        config, _ = gate.read_json(folder/'crg-config/config.json')
        require(config == MANUAL and not (folder/'crg-config/io-profile.json').exists(), 'ORIGINAL_CONFIG_AND_PROFILE_ABSENCE')
        native, _ = gate.read_json(folder/('postgresql/basebackup/crg-soak-'+row['aged_run_id']+'/load.json'))
        base.validate_native(native, row['aged_run_id'])
    return {'phase': 'ready', 'executed': False, 'stable_release_accepted': False}


class Execution(base.Execution):
    def __init__(self, plan, digest):
        super().__init__(plan, digest)
        self.report.update(schema='crg-versioned-business-reload-report-v1', mode='business-reload',
                           executor_sha256=gate.digest(Path(__file__))['sha256'], postflight_executed=False,
                           scope='original vendor startup; 600s native SQL/API with reload and original engine backup/stream/restore',
                           base_helper_sha256=BASE_SHA, measured_profile_sha256=PINS['profile'])
        self.report.pop('maintenance_scope', None)
        self.inputs = {};self.engine_job = None;self.engine_log = None

    def write_config(self, folder, value, symlink=False):
        config = folder/'crg-config/config.json';temp = config.with_name('reload95.next')
        require(not temp.exists() and not temp.is_symlink(), 'CONFIG_TEMP_FRESH')
        data = value if isinstance(value, bytes) else json.dumps(dict(value, interval_seconds=1, data_paths=['/opt/postgresql'])).encode()
        target = config.with_name('reload95.target.json') if symlink else temp
        require(not target.is_symlink(), 'CONFIG_TARGET_NOT_LINK')
        with target.open('wb') as stream:
            os.chmod(target, 0o600);stream.write(data);stream.flush();os.fsync(stream.fileno())
        if symlink:temp.symlink_to(target.name)
        temp.replace(config)
        return time.time_ns()

    def business_native(self, role, folder, group, row):
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
            len(intervals)==7 and all(started <= x['started_epoch'] <= x['ended_epoch'] <= finish for x in covered)
            and len(samples)>=600/60*.98 and all(b['epoch']-a['epoch']<=120 for a,b in zip(samples,samples[1:]))
            and samples[0]['epoch']-started<=120 and finish-samples[-1]['epoch']<=120)
        row['engine_native_validation']='passed-with-entire-600s-native';self.engine_job=None
        self.check(role+'-same-Agent-PID1-PG-cache-profile-and-zero-OOM',
            self.sql(role,'SELECT pg_postmaster_start_time();')==row['primary_start']
            and gate.digest(profile)['sha256']==PINS['profile'] and profile.stat().st_mtime_ns==profile_mtime)
        same()

    def role(self, role):
        folder=Path(self.plan['roles'][role]['folder']);self.reserve(True)
        item={'phase':'booting-original-business','boots':[]};self.report['roles'][role]=item;self.save()
        config=folder/'crg-config/config.json';profile=folder/'crg-config/io-profile.json'
        original=config.read_bytes();require(json.loads(original)==MANUAL and not profile.exists(), 'EXCLUSIVE_INPUTS')
        self.inputs[role]=(original,config,profile)
        profile.write_bytes(Path(PROFILE).read_bytes());profile.chmod(0o600);self.write_config(folder,MANUAL)
        pod,_=gate.read_json(folder/'pod.json');pod=base.adapt_pod(pod,role,folder,self.ns,self.root)
        # Read-only program mount: this qualification never replaces a program.
        next(m for c in pod['spec']['containers'] if c['name']==role for m in c['volumeMounts'] if m['name']=='crg')['readOnly']=True
        row,group=self.boot(role,folder,pod,'business-reload');row.update(reload_intervals=[],samples=[])
        self.business_native(role,folder,group,row)
        disabled=json.loads(self.ex(role,'/opt/crg/crg','disable','--config','/etc/crg/config.json',timeout=30).stdout)
        self.check(role+'-explicit-disable-restores-true-runtime-originals',disabled['state']=='restored' and base.controls(group)==row['runtime_original_controls'])
        self.delete_pod(role,group);item['phase']='business-reload-passed';self.save()

    def execute(self, readiness_result):
        try:return super().execute(readiness_result)
        finally:
            if self.engine_job is not None and self.engine_job.poll() is None:
                self.engine_job.terminate()
                try:self.engine_job.wait(timeout=120)
                except subprocess.TimeoutExpired:self.report.update(phase='failed',engine_cleanup_pending=True)
            if self.engine_log:self.engine_log.close()
            # Only the proven-unmounted disposable inputs are restored. Never
            # overwrite an input if another Pod acquired it after our cleanup.
            if self.root.exists():
                try:
                    require(not self.pods,'PODS_NOT_GONE_BEFORE_INPUT_RESTORE')
                    base.no_other_mounts([Path(self.plan['roles'][r]['folder']) for r in self.inputs])
                    for role,(original,config,profile) in self.inputs.items():
                        require(not profile.is_symlink() and gate.digest(profile)['sha256']==PINS['profile'],'PROFILE_CHANGED')
                        temp=config.with_name('reload95.restore');require(not temp.exists(),'RESTORE_TEMP_FRESH')
                        with temp.open('xb') as out:out.write(original);os.chmod(temp,0o600);out.flush();os.fsync(out.fileno())
                        temp.replace(config);profile.unlink()
                        target=config.with_name('reload95.target.json')
                        if target.exists():
                            require(not target.is_symlink() and stat.S_ISREG(target.stat().st_mode),'OWN_CONFIG_TARGET');target.unlink()
                        require(config.read_bytes()==original,'CONFIG_RESTORE_VERIFY')
                    self.report['original_config_bytes_and_profile_absence_restored']=True
                except BaseException as error:self.report.update(phase='failed',input_restore_error=str(error) if isinstance(error,Rejected) else type(error).__name__)
                self.save()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--plan-sha256',required=True);parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    try:
        require(sys.platform=='linux' and os.geteuid()==0,'LINUX_ROOT')
        plan=checked_plan(args.plan,args.plan_sha256);ready=readiness(plan)
        if not args.execute:print(json.dumps(ready));return 0
        require(os.environ.get('CRG_BUSINESS_RELOAD')=='authorized-disposable-test-node-only','EXPLICIT_LAB_MARKER')
        def interrupted(signum, frame):raise KeyboardInterrupt()
        signal.signal(signal.SIGTERM,interrupted)
        ready=readiness(plan)
        result=Execution(plan,args.plan_sha256).execute(ready)
        print(json.dumps({'phase':result['phase'],'checks':len(result['tests']),'reason':result.get('reason'),'stable_release_accepted':False}))
        return 0 if result['phase']=='passed' and result.get('namespace_absent') and result.get('original_config_bytes_and_profile_absence_restored') else 1
    except BaseException as error:
        print(json.dumps({'phase':'rejected','reason':str(error) if isinstance(error,Rejected) else type(error).__name__,'executed':False}));return 1


if __name__=='__main__':raise SystemExit(main())
