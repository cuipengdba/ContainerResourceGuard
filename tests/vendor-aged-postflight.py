#!/usr/bin/env python3
"""Explicit lab-only execution after the immutable aged-lineage readiness gate.

Default invocation is read-only. --execute requires Linux root and the explicit
disposable-node marker. A short rehearsal has a separate plan and never qualifies
the seven-day run. This is a test fixture, not a product container manager.
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
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import time

spec = importlib.util.spec_from_file_location('aged_gate', Path(__file__).with_name('vendor-aged-preflight.py'))
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
require, Rejected = gate.require, gate.Rejected
CONTROLS = gate.CONTROLS
CRITERIA = {'startup_seconds': 300, 'cache_after_ready_seconds': 45,
            'native_seconds_each_role': 600, 'clone_host_available_bytes': 28 * 1024**3,
            'steady_host_available_bytes': 8 * 1024**3, 'disk_free_bytes': 20 * 1024**3,
            'maximum_errors': 0, 'maximum_request_seconds': 5, 'p95_bucket_seconds': 1,
            'minimum_coverage': .98, 'payload_bytes': 67108864, 'oom_kill_delta': 0}
PINS = {'revision': 'd3706f3ea7ad279fea818e5ad1aa62ac5d3f8710',
        'binary': '3a1ce7dbf5630f8f1c823005ceb4958653c6c235b2ba5026956ca6597f1926f9',
        'cache': '757ba385a0ee4bdadc968b96b5c3e69fd44353060e5ab28520fd6f73a59902de',
        'worker': 'ba87ef2d646b723eb8419de25ffcd736f7a5b0925716f4b638761dff70bb2461',
        'previous': '3f69370b2b0f04f447801212599d6f4596b280331ff83866a11260dc7fc8f8a9'}


def controls(group):
    return {name: (group/name).read_text().strip() for name in CONTROLS}


def checked_plan(path, expected, rehearsal):
    value, actual = gate.read_json(path)
    require(actual == expected and re.fullmatch(r'[0-9a-f]{64}', expected), 'EXECUTION_PLAN_DIGEST')
    require(value.get('schema') == 'crg-aged-execution-v1' and value.get('criteria') == CRITERIA
            and value.get('pins') == PINS, 'EXECUTION_PLAN_CONTRACT')
    require(value.get('mode') == ('short-rehearsal' if rehearsal else 'seven-day-postflight'), 'MODE_MISMATCH')
    require(gate.digest(Path(__file__))['sha256'] == value['executor_sha256'], 'EXECUTOR_SOURCE')
    require(gate.digest(Path(__file__).with_name('vendor-aged-preflight.py'))['sha256']
            == 'b82c3a4e50969ac73c49322a7755eb4e40d277741e67270d7845b7e32b016439', 'GATE_SOURCE')
    require(gate.digest(Path(__file__).with_name('soak-report-audit.py'))['sha256']
            == '4feb3e7fad630e37245c837fc85e90dec4e10a086e5fe96a4bc299f4ad481eb8', 'AUDITOR_SOURCE')
    gate.lab_root(value['work_root'])
    require(re.fullmatch(r'crg-vendor-lab-[a-z0-9-]+', value['namespace']), 'NAMESPACE')
    require(re.fullmatch(r'[0-9]{8,11}', value['run_id']), 'RUN_ID')
    for name, pin in [('worker', 'worker'), ('previous_binary', 'previous')]:
        require(gate.digest(Path(value[name]))['sha256'] == PINS[pin], 'QUALIFIED_TOOL_SOURCE')
    require(set(value['roles']) == {'dbs', 'hisdbs'}, 'ROLE_SET')
    for role, row in value['roles'].items():
        folder = gate.path_clean(row['folder'])
        require(str(folder).startswith('/var/tmp/crg-') and folder.name == role+'-business', 'AGED_FOLDER')
        require(re.fullmatch(r'[0-9]{8,14}', row['aged_run_id']), 'AGED_RUN_ID')
        require(not folder.is_relative_to(value['work_root']) and not Path(value['work_root']).is_relative_to(folder), 'WORK_OVERLAP')
    require(value['roles']['dbs']['folder'] != value['roles']['hisdbs']['folder'], 'ROLE_DATA_SHARED')
    return value


def readiness(plan):
    """This path never creates even a report/lock or an output directory."""
    if plan['mode'] == 'seven-day-postflight':
        frozen, frozen_digest = gate.load_plan(Path(plan['lineage_plan']), plan['lineage_plan_sha256'])
        require(frozen_digest == '58a8fe7c07c7655c13e1b54a83ad8afd63646947de9b8b8929f1d089dbe2a8cb'
                and plan['lineage_seal_sha256'] == 'd45cd434b6b614141dab56742207fa245c04f59c80d4469c514e7d255fd108bd', 'FROZEN_LINEAGE_BINDING')
        require(plan['work_root'] == frozen['postflight_root'] and plan['namespace'] == frozen['postflight_namespace'], 'POSTFLIGHT_TARGET')
        for role, row in plan['roles'].items():
            require(row['folder'] == str(Path(frozen['component_root'])/'fixture'/(role+'-business'))
                    and row['aged_run_id'] == frozen['run_id'], 'AGED_ROLE_BINDING')
        seal, actual = gate.read_json(Path(plan['lineage_seal']))
        require(actual == plan['lineage_seal_sha256'], 'LINEAGE_SEAL_DIGEST')
        state, inputs = gate.component(frozen)
        if state['phase'] == 'pending':
            require(seal['plan_sha256'] == frozen_digest and seal['launch'] == inputs[1], 'LINEAGE_SEAL_BINDING')
            return state
        result = gate.verify_lineage(frozen, frozen_digest, seal, inputs)
        result['component'] = state
        return result
    proof, actual = gate.read_json(Path(plan['rehearsal_proof']))
    require(actual == plan['rehearsal_proof_sha256'] and proof['phase'] == 'passed'
            and proof['namespace_absent'] is True and len(proof['tests']) == 12
            and all(t['passed'] is True for t in proof['tests'])
            and proof['sources']['v10']['revision'] == PINS['revision']
            and proof['sources']['v10']['binary_sha256'] == PINS['binary'], 'SHORT_PROOF')
    require(gate.namespace(plan['old_namespace']) is None, 'SHORT_OLD_NAMESPACE_PRESENT')
    require(gate.namespace(plan['namespace']) is None and not Path(plan['work_root']).exists(), 'POSTFLIGHT_TARGET_NOT_FRESH')
    for role, row in plan['roles'].items():
        folder = Path(row['folder'])
        require(folder == Path(plan['rehearsal_proof']).parent/('v10-'+role+'-bw64')/(role+'-business'), 'SHORT_SOURCE_FOLDER')
        native, _ = gate.read_json(folder/('postgresql/basebackup/crg-soak-'+row['aged_run_id']+'/load.json'))
        validate_native(native, row['aged_run_id'])
        require(gate.digest(folder/'pod.json')['sha256'] == row['pod_sha256']
                and gate.digest(folder/'crg/crg')['sha256'] == PINS['binary']
                and gate.digest(folder/'ccg/bin/containercacheguard')['sha256'] == PINS['cache'], 'SHORT_SOURCE_INPUT')
    return {'phase': 'ready-for-short-rehearsal', 'postflight_allowed': True,
            'seven_day_accepted': False, 'P10_complete': False, 'release_accepted': False}


def adapt_pod(original, role, folder, namespace, work):
    """Retain original private settings; change only recorded lab plumbing."""
    require(original['kind'] == 'Pod' and original['metadata']['name'] == role+'-business'
            and original['metadata']['labels'].get('managed-by') == 'crg-vendor-test', 'POD_OWNERSHIP')
    pod = copy.deepcopy(original);spec = pod['spec']
    require(not any(spec.get(key) for key in ['hostPID', 'hostNetwork', 'hostIPC'])
            and spec['restartPolicy'] == 'Never' and spec['automountServiceAccountToken'] is False
            and {c['name'] for c in spec['containers']} == {role, 'isolated-dcs'}, 'POD_ISOLATION')
    pod['metadata']['namespace'] = namespace
    main = next(c for c in spec['containers'] if c['name'] == role)
    dcs = next(c for c in spec['containers'] if c['name'] == 'isolated-dcs')
    require(main['imagePullPolicy'] == dcs['imagePullPolicy'] == 'Never'
            and main['resources']['limits'] == {'cpu': '8', 'memory': '20Gi'}
            and main['command'][-1].endswith('exec /bin/bash /opt/ccg/scripts/business-supervisor.sh')
            and dcs['command'][0] == '/aux/etcd'
            and '--listen-client-urls' in dcs['command']
            and dcs['command'][dcs['command'].index('--listen-client-urls')+1] == 'http://127.0.0.1:2379', 'ORIGINAL_START_OR_BUDGET')
    names = [v['name'] for v in spec['volumes']]
    require(len(names) == len(set(names)) and 'staging' not in names and 'recovery' not in names, 'VOLUME_SET')
    for volume in spec['volumes']:
        if 'hostPath' not in volume:
            require('emptyDir' in volume, 'VOLUME_TYPE');continue
        name = volume['name'];path = gate.path_clean(volume['hostPath']['path'])
        if name == 'gate':
            require(path.name == 'gates' and str(path).startswith('/var/tmp/crg-'), 'OLD_GATE_PATH')
            volume['hostPath']['path'] = str(work/'gates')
        elif name == 'aux':
            require(path.name == 'aux' and str(path).startswith('/var/tmp/crg-'), 'OLD_AUX_PATH')
            require(gate.digest(path/'etcd')['sha256'] == gate.digest(Path('/usr/bin/etcd'))['sha256'], 'DCS_SOURCE')
        else:
            require(path.is_relative_to(folder), 'FOREIGN_HOST_MOUNT')
    mounts = {m['name']: m for m in main['volumeMounts']}
    require(mounts['ccg']['readOnly'] is True and mounts['ccg']['mountPath'] == '/opt/ccg'
            and mounts['crg']['mountPath'] == '/opt/crg', 'ORIGINAL_CCG_MOUNT')
    # Only program replacement during maintenance requires this lab mount writable.
    mounts['crg']['readOnly'] = False
    for env in main['env']:
        if env['name'] == 'MY_POD_NAMESPACE':env['value'] = namespace
    for name, target, ro in [('staging', '/staging', True), ('recovery', '/recovery', False)]:
        spec['volumes'].append({'name': name, 'hostPath': {'path': str(work/role/name), 'type': 'Directory'}})
        main['volumeMounts'].append({'name': name, 'mountPath': target, 'readOnly': ro})
    return pod


def validate_native(value, run_id):
    require(value['schema'] == 'crg-vendor-soak-v1' and value['phase'] == 'passed'
            and value['run_id'] == run_id and value['test_phase'] == 'smoke'
            and value['requested_duration_seconds'] == 600
            and gate.audit.number(value['elapsed_seconds']) and value['elapsed_seconds'] >= 600
            and not value['interrupted'] and value['threads_stopped'] is True
            and value['payload_integrity'] is True and value['primary_not_restarted'] is True
            and value['primary_start_time_initial'] == value['primary_start_time_final']
            and len(value['initial_checksum']) == len(value['final_checksum']) == 5
            and value['initial_checksum'][:4] == value['final_checksum'][:4]
            and value['initial_checksum'][0] == 16384 and value['initial_checksum'][2] == 67108864, 'NATIVE_COMPLETION')
    require(value['criteria'] == {'sql_period_seconds': 2, 'api_period_seconds': 5,
            'maximum_seconds': 5, 'p95_upper_bound_seconds': 1, 'maximum_errors': 0,
            'minimum_scheduled_samples_fraction': .98}, 'NATIVE_CRITERIA')
    for kind, period in [('sql', 2), ('api', 5)]:
        item = value[kind]
        require(type(item['attempts']) is int and item['errors'] == 0 and item['attempts'] == item['successes']
                and item['attempts'] >= 600/period*.98
                and gate.audit.number(item['max_seconds']) and 0 <= item['max_seconds'] <= 5
                and value['latency_bucket_upper_seconds'] == [.001, .005, .01, .02, .05, .1, .25, .5, 1, 2, 5, 'over-5']
                and len(item['histogram']) == 12
                and sum(item['histogram']) == item['attempts'], 'NATIVE_SAMPLES')
        bounds = value['latency_bucket_upper_seconds'];total = 0;p95 = None
        for upper, count in zip(bounds, item['histogram']):
            require(type(count) is int and count >= 0, 'NATIVE_HISTOGRAM')
            total += count
            if p95 is None and total >= item['attempts']*.95:p95 = upper
        require(type(p95) in (int, float) and p95 <= 1 and p95 == item['p95_bucket_upper_seconds'], 'NATIVE_P95')


class Execution:
    def __init__(self, plan, plan_digest):
        self.plan, self.root, self.ns = plan, Path(plan['work_root']), plan['namespace']
        self.namespace_uid = None;self.pods = {};self.worker = None;self.worker_log = None
        self.report = {'schema': 'crg-aged-execution-report-v1', 'phase': 'preparing',
                       'mode': plan['mode'], 'plan_sha256': plan_digest,
                       'source_revision': PINS['revision'], 'binary_sha256': PINS['binary'],
                       'executor_sha256': gate.digest(Path(__file__))['sha256'],
                       'criteria': CRITERIA, 'roles': {}, 'tests': [],
                       'P10_complete': False, 'release_accepted': False, 'postflight_executed': True,
                       'scope': 'actual retained lab data; private original images/settings and paths; independent logical restore database on same test host',
                       'maintenance_scope': 'current to previous development binary and back; not two released minors'}

    def save(self):
        path = self.root/'report.candidate'
        with path.open('w', encoding='utf-8') as out:
            os.chmod(path, 0o600);json.dump(self.report, out, indent=2);out.flush();os.fsync(out.fileno())
        path.replace(self.root/'report.json')

    def check(self, name, passed, **extra):
        self.report['tests'].append(dict(name=name, passed=bool(passed), **extra));self.save()
        require(passed, name)

    def run(self, args, check=True, timeout=30, data=None):
        result = subprocess.run(args, input=data, capture_output=True, text=True, timeout=timeout)
        require(not check or result.returncode == 0, 'LAB_COMMAND_EXIT_'+str(result.returncode))
        return result

    def ex(self, role, *args, **kwargs):
        prefix = ['kubectl', 'exec', '-n', self.ns, role+'-business', '-c', role]
        if kwargs.get('data') is not None:prefix.append('-i')
        return self.run([*prefix, '--', *args], **kwargs)

    def sql(self, role, statement, db='postgres', timeout=60):
        require(re.fullmatch(r'[a-z0-9_]+', db), 'DATABASE_NAME')
        cmd = '/opt/postgresql/pgsql/bin/psql -X -qAt -v ON_ERROR_STOP=1 -w -h127.0.0.1 -p5432 -U postgres -d '+db+' -c '+shlex.quote(statement)
        return self.ex(role, 'su', '-', 'postgres', '-c', cmd, timeout=timeout).stdout.strip()

    def reserve(self, clone=False):
        available = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
        require(available >= CRITERIA['clone_host_available_bytes' if clone else 'steady_host_available_bytes']
                and shutil.disk_usage(self.root).free >= CRITERIA['disk_free_bytes'], 'NODE_RESERVE')

    def create(self, obj):
        self.run(['kubectl', 'create', '-f', '-'], data=json.dumps(obj))

    def identity(self, role):
        meta = json.loads(self.run(['kubectl', 'get', 'pod', '-n', self.ns, role+'-business', '-o', 'json']).stdout)
        require(meta['metadata']['uid'] == self.pods[role] and meta['metadata']['labels'].get('managed-by') == 'crg-vendor-test', 'OWN_POD_UID')
        require(all(x['restartCount'] == 0 for x in meta['status']['containerStatuses']), 'NO_CONTAINER_RESTART')
        item = next(x for x in meta['status']['containerStatuses'] if x['name'] == role)
        cid = item['containerID'].split('://', 1)[1]
        pid = json.loads(self.run(['crictl', 'inspect', cid]).stdout)['info']['pid']
        require(type(pid) is int and pid > 1, 'MAIN_PID')
        for namespace in ['net', 'pid', 'mnt']:
            require(os.stat('/proc/'+str(pid)+'/ns/'+namespace).st_ino != os.stat('/proc/self/ns/'+namespace).st_ino, 'HOST_NAMESPACE')
        return meta, cid, pid, gate.group(pid, cid)

    def processes(self, group, entry):
        values = []
        for pid in (group/'cgroup.procs').read_text().splitlines():
            try:
                p = Path('/proc', pid);argv = (p/'cmdline').read_bytes().split(b'\0')
                if len(argv) > 1 and argv[0] == entry.encode() and argv[1] == b'run':
                    fields = (p/'stat').read_text().rsplit(')', 1)[1].split()
                    if fields[0] != 'Z':values.append((int(pid), int(fields[19]), hashlib.sha256((p/'exe').read_bytes()).hexdigest()))
            except (FileNotFoundError, ProcessLookupError):pass
        return values

    def boot(self, role, folder, pod, phase):
        self.reserve(True);self.create(pod)
        meta = json.loads(self.run(['kubectl', 'get', 'pod', '-n', self.ns, role+'-business', '-o', 'json']).stdout)
        self.pods[role] = meta['metadata']['uid']
        self.run(['kubectl', 'wait', '-n', self.ns, '--for=condition=Ready', 'pod/'+role+'-business', '--timeout=90s'], timeout=100)
        meta, cid, pid, group = self.identity(role)
        original = controls(group)
        require(original['cpu.max'] == '800000 100000' and original['memory.max'] == '21474836480'
                and original['io.max'] == '', 'NEW_RUNTIME_ORIGINALS')
        self.run(['nsenter', '-t', str(pid), '-n', '--', 'ip', 'link', 'set', 'dev', 'eth0', 'down'])
        require('state DOWN' in self.run(['nsenter', '-t', str(pid), '-n', '--', 'ip', '-o', 'link', 'show', 'dev', 'eth0']).stdout, 'NETWORK_GATE')
        cachefile = folder/'cache-state/status.json'
        stamp = lambda: (cachefile.stat().st_ino, cachefile.stat().st_mtime_ns, cachefile.stat().st_size) if cachefile.exists() else None
        old_stamp = stamp();began = time.monotonic();deadline = began+300
        (self.root/'gates'/meta['metadata']['uid']).write_text('isolated\n')
        row = {'phase': phase, 'pod_uid': meta['metadata']['uid'], 'container_id': cid, 'cgroup': str(group),
               'runtime_original_controls': original, 'network_isolated_before_start': True}
        self.report['roles'][role]['boots'].append(row);self.save()
        status = folder/'resource-state/status.json'
        while time.monotonic() < deadline:
            self.reserve()
            try:
                q = self.ex(role, 'su', '-', 'postgres', '-c', '/opt/postgresql/pgsql/bin/pg_isready -h127.0.0.1 -p5432 -t2', check=False, timeout=max(.01, min(15, deadline-time.monotonic())))
                if q.returncode == 0 and time.monotonic() < deadline:
                    api = "import urllib2,json; r=urllib2.urlopen(urllib2.Request('http://127.0.0.1:8090/test',data='{}',headers={'Content-Type':'application/json'}),timeout=3); assert r.getcode()==200; assert json.loads(r.read(1024))['Result']=='000'"
                    a = self.ex(role, 'python', '-c', api, check=False, timeout=max(.01, min(10, deadline-time.monotonic())))
                    state = gate.read_json(status)[0] if status.exists() else {}
                    if a.returncode == 0 and state.get('state') == 'managed' and time.monotonic() < deadline:break
            except subprocess.TimeoutExpired:row['observation_timeouts'] = row.get('observation_timeouts', 0)+1
            time.sleep(max(0, min(2, deadline-time.monotonic())))
        else:raise Rejected('ORIGINAL_STARTUP_300S')
        row['ready_seconds'] = time.monotonic()-began
        active = controls(group);state = gate.read_json(status)[0]
        require(active['cpu.max'] == '720000 100000' and active['memory.max'] == '20001980416'
                and re.fullmatch(r'[0-9]+:[0-9]+ rbps=67108864 wbps=67108864 riops=4096 wiops=4096', active['io.max'])
                and all(active[n] == original[n] for n in CONTROLS[3:])
                and {x['file'] for x in state['items']} == {'cpu.max', 'memory.max', 'io.max'}
                and all(x['state'] == 'applied' for x in state['items']), 'EXACT_THREE_CONTROLS')
        row['identity'] = state['plan']['environment']['identity'];row['active_controls'] = active
        self.check(role+'-'+phase+'-original-start-and-three-controls', True)
        cache_deadline = min(deadline, time.monotonic()+45)
        while time.monotonic() < cache_deadline:
            caches = self.processes(group, '/opt/ccg/bin/containercacheguard')
            if len(caches) == 1 and caches[0][2] == PINS['cache'] and stamp() != old_stamp and cachefile.exists() and gate.read_json(cachefile)[0].get('action') == 'enforce':break
            time.sleep(min(1, max(0, cache_deadline-time.monotonic())))
        else:raise Rejected('FRESH_CACHE_WITHIN_ORIGINAL_BUDGET')
        agents = self.processes(group, '/opt/crg/crg')
        self.check(role+'-'+phase+'-one-current-Agent-fresh-cache-readonly-CCG', len(agents) == 1 and agents[0][2] == PINS['binary'] and 'ro' in self.ex(role, 'findmnt', '-n', '-o', 'OPTIONS', '/opt/ccg').stdout.strip().split(','))
        row['primary_start'] = self.sql(role, 'SELECT pg_postmaster_start_time();')
        return row, group

    def delete_pod(self, role, group=None):
        if role not in self.pods:return
        meta = json.loads(self.run(['kubectl', 'get', 'pod', '-n', self.ns, role+'-business', '-o', 'json']).stdout)
        require(meta['metadata']['uid'] == self.pods[role]
                and meta['metadata']['labels'].get('managed-by') == 'crg-vendor-test', 'CLEANUP_POD_UID')
        self.run(['kubectl', 'delete', 'pod', '-n', self.ns, role+'-business', '--wait=true', '--timeout=120s'], timeout=130)
        result = self.run(['kubectl', 'get', 'pod', '-n', self.ns, role+'-business', '--ignore-not-found', '-o', 'json'])
        require(not result.stdout.strip(), 'OWN_POD_NOT_ABSENT');del self.pods[role]
        if group:
            deadline = time.monotonic()+30
            while group.exists() and time.monotonic() < deadline:time.sleep(.5)
            require(not group.exists(), 'OLD_CGROUP_NOT_GONE')

    def maintained_native(self, role, folder, group, row, aged_checksum, checksum_sql):
        run_id = self.plan['run_id']+('0' if role == 'dbs' else '1')
        entry = '/tmp/crg-aged-load-'+run_id+'.py';worker = Path(self.plan['worker']).read_text()
        self.ex(role, '/bin/bash', '-c', 'set -Ce; umask 077; cat > '+entry+'; chmod 0444 '+entry, data=worker)
        require(self.ex(role, 'sha256sum', entry).stdout.split()[0] == PINS['worker'], 'NATIVE_WORKER_COPY')
        self.worker_log = (self.root/(role+'-native.log')).open('x')
        self.worker = subprocess.Popen(['kubectl', 'exec', '-n', self.ns, role+'-business', '-c', role, '--', 'su', '-', 'postgres', '-c',
            'CRG_VENDOR_SOAK_TEST=disposable-loopback-only python '+entry+' --run-id '+run_id+' --seconds 600 --test-phase smoke'],
            stdin=subprocess.DEVNULL, stdout=self.worker_log, stderr=self.worker_log)
        load = folder/('postgresql/basebackup/crg-soak-'+run_id+'/load.json');deadline = time.monotonic()+360
        while time.monotonic() < deadline:
            require(self.worker.poll() is None, 'NATIVE_EARLY_EXIT')
            if load.exists() and gate.read_json(load)[0].get('phase') == 'running':break
            self.reserve();time.sleep(2)
        else:raise Rejected('NATIVE_PREPARATION_DEADLINE')
        started = gate.audit.timestamp(gate.read_json(load)[0]['started_utc'])
        fixed = controls(group);journal = (folder/'resource-state/journal.json').read_bytes()
        caches = self.processes(group, '/opt/ccg/bin/containercacheguard')
        require(len(caches) == 1, 'CACHE_SINGLE_INSTANCE')
        pid1 = self.ex(role, 'cat', '/proc/1/stat').stdout.rsplit(')', 1)[1].split()[19]
        intervals = self.report['roles'][role]['maintenance_intervals']
        def active():
            require(self.worker.poll() is None and time.time() < started+600 and gate.read_json(load)[0]['phase'] == 'running', 'MAINTENANCE_NATIVE_ENVELOPE')
        def same():
            return controls(group) == fixed and (folder/'resource-state/journal.json').read_bytes() == journal and self.processes(group, '/opt/ccg/bin/containercacheguard') == caches and self.ex(role, 'cat', '/proc/1/stat').stdout.rsplit(')', 1)[1].split()[19] == pid1
        def cli(command, *args):
            active();began = time.time()
            value = json.loads(self.ex(role, '/staging/crg', command, '--config', '/etc/crg/config.json', *args, timeout=90).stdout)
            active();intervals.append({'command': command, 'started_epoch': began, 'ended_epoch': time.time()});self.save()
            require(same(), 'MAINTENANCE_CHANGED_BUSINESS_OR_ORIGINALS')
            return value
        def wait_guard(expected):
            deadline = min(time.monotonic()+120, time.monotonic()+max(0, started+600-time.time()))
            while time.monotonic() < deadline:
                active();agents = self.processes(group, '/opt/crg/crg')
                if len(agents) == 1 and agents[0][2] == expected:return
                time.sleep(1)
            raise Rejected('SOURCE_QUALIFIED_AGENT_NOT_RESUMED')
        cli('quiesce')
        install_args = ['--install-dir', '/opt/crg', '--previous-sha256', PINS['binary'], '--candidate-sha256', PINS['previous']]
        first = cli('binary-install', *install_args, '--backup-dir', '/recovery/first')
        self.check(role+'-aged-state-online-install-previous-development-binary', first['state'] == 'installed' and gate.digest(folder/'crg/crg')['sha256'] == PINS['previous'])
        first_back = cli('binary-rollback', '--install-dir', '/opt/crg', '--backup-dir', '/recovery/first')
        self.check(role+'-aged-state-immediate-rollback', first_back['state'] == 'rolled_back' and gate.digest(folder/'crg/crg')['sha256'] == PINS['binary'])
        cli('binary-install', *install_args, '--backup-dir', '/recovery/second');cli('enable');wait_guard(PINS['previous'])
        self.check(role+'-aged-state-previous-Agent-managed-with-same-PID1-PG-cache', same() and self.sql(role, 'SELECT pg_postmaster_start_time();') == row['primary_start'])
        cli('quiesce');cli('binary-rollback', '--install-dir', '/opt/crg', '--backup-dir', '/recovery/second');cli('enable');wait_guard(PINS['binary'])
        self.check(role+'-aged-state-current-Agent-resumed-after-rollback', same() and self.sql(role, checksum_sql) == aged_checksum)
        end_deadline = time.monotonic()+720
        while self.worker.poll() is None and time.monotonic() < end_deadline:
            self.reserve();require(same(), 'STEADY_BUSINESS_CHANGED');time.sleep(3)
        require(self.worker.poll() == 0, 'NATIVE_COMPLETION_EXIT');self.worker_log.close();self.worker_log = None;self.worker = None
        native = gate.read_json(load)[0];validate_native(native, run_id)
        start = gate.audit.timestamp(native['started_utc']);end = gate.audit.timestamp(native['measurement_finished_utc'])
        self.check(role+'-600s-native-and-all-eight-maintenance-intervals-covered', len(intervals) == 8 and all(start <= i['started_epoch'] <= i['ended_epoch'] <= end for i in intervals) and same())
        self.report['roles'][role]['native'] = native;self.save()

    def role(self, role):
        config = self.plan['roles'][role];folder = Path(config['folder'])
        item = {'phase': 'booting-retained-data', 'boots': [], 'maintenance_intervals': []};self.report['roles'][role] = item;self.save()
        old_native, _ = gate.read_json(folder/('postgresql/basebackup/crg-soak-'+config['aged_run_id']+'/load.json'))
        require(old_native['phase'] == 'passed' and old_native['payload_integrity'] is True, 'AGED_NATIVE_NOT_PASSED')
        directories = {name: gate.directory(folder/name) for name in gate.DIRECTORIES}
        immutable = {name: gate.digest(folder/name) for name in gate.immutable_files(role) if name != 'crg/crg'}
        logs = {p.name: gate.digest(p) for p in (folder/'log/crg').glob('crg-*.log')}
        old_journal = gate.read_json(folder/'resource-state/journal.json')[0]
        pod, _ = gate.read_json(folder/'pod.json');pod = adapt_pod(pod, role, folder, self.ns, self.root)
        private = self.root/role/'pod.json';private.write_text(json.dumps(pod));private.chmod(0o600)
        first, first_group = self.boot(role, folder, pod, 'aged-reopen')
        previous = gate.read_json(folder/'resource-state/journal.previous.json')[0]
        self.check(role+'-aged-journal-rollover-before-data-check', previous['identity'] == old_journal['identity'] and first['identity'] != old_journal['identity'])
        schema = 'crg_soak_'+config['aged_run_id']
        checksum_sql = "SELECT count(*),sum(id),sum(octet_length(payload)),md5(string_agg(md5(payload),'' ORDER BY id)),sum(counter) FROM "+schema+'.fixture;'
        before = self.sql(role, checksum_sql)
        self.check(role+'-actual-aged64MiB-and-final-counter-reopened', before.split('|') == [str(x) for x in old_native['final_checksum']])
        dump = '/opt/postgresql/basebackup/crg-aged-'+self.plan['run_id']+'.dump'
        archive = folder/'postgresql/basebackup'/Path(dump).name
        require(not archive.exists(), 'BACKUP_TARGET_NOT_FRESH')
        self.ex(role, 'su', '-', 'postgres', '-c', '/opt/postgresql/pgsql/bin/pg_dump -w -h127.0.0.1 -p5432 -U postgres -Fc -n '+schema+' -f '+dump+' postgres', timeout=300)
        backup = gate.digest(archive);listing = self.ex(role, 'su', '-', 'postgres', '-c', '/opt/postgresql/pgsql/bin/pg_restore -l '+dump).stdout
        self.check(role+'-aged-schema-logical-backup-readable', backup['size'] > 0 and 'TABLE DATA '+schema+' fixture' in listing)
        db = 'crg_aged_restore_'+self.plan['run_id']
        require(self.sql(role, "SELECT count(*) FROM pg_database WHERE datname='"+db+"';") == '0', 'RESTORE_DATABASE_NOT_FRESH')
        self.sql(role, 'CREATE DATABASE '+db+';')
        self.ex(role, 'su', '-', 'postgres', '-c', '/opt/postgresql/pgsql/bin/pg_restore --exit-on-error -w -h127.0.0.1 -p5432 -U postgres -d '+db+' '+dump, timeout=300)
        self.check(role+'-independent-database-restores-aged-payload-and-counter', self.sql(role, checksum_sql, db) == before and self.sql(role, checksum_sql) == before)
        self.sql(role, 'DROP DATABASE '+db+';')
        self.delete_pod(role, first_group)
        second, second_group = self.boot(role, folder, pod, 'same-data-new-Pod')
        previous = gate.read_json(folder/'resource-state/journal.previous.json')[0]
        self.check(role+'-new-ID-journal-PG-restart-and-same-aged-data', second['container_id'] != first['container_id'] and second['identity'] != first['identity'] and previous['identity'] == first['identity'] and first['primary_start'] != second['primary_start'] and self.sql(role, checksum_sql) == before and gate.digest(archive) == backup)
        self.maintained_native(role, folder, second_group, second, before, checksum_sql)
        self.check(role+'-aged-payload-counter-after-native-maintenance', self.sql(role, checksum_sql) == before)
        disabled = json.loads(self.ex(role, '/opt/crg/crg', 'disable', '--config', '/etc/crg/config.json', timeout=30).stdout)
        self.check(role+'-disable-restores-new-runtime-originals-and-no-OOM', disabled['state'] == 'restored' and controls(second_group) == second['runtime_original_controls'] and int(dict(x.split() for x in (second_group/'memory.events').read_text().splitlines())['oom_kill']) == 0)
        self.check(role+'-same-aged-directories-config-private-inputs-and-program-restored', all(gate.directory(folder/name) == value for name, value in directories.items()) and all(gate.digest(folder/name) == value for name, value in immutable.items()) and gate.digest(folder/'crg/crg')['sha256'] == PINS['binary'])
        self.check(role+'-daily0600-logs-retain-original-prefixes-and-append', bool(logs) and all(gate.digest(folder/'log/crg'/name, value['size']) == value for name, value in logs.items()) and any((folder/'log/crg'/name).stat().st_size > value['size'] for name, value in logs.items()) and all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in (folder/'log/crg').glob('crg-*.log')))
        self.delete_pod(role, second_group);item['phase'] = 'postflight-component-passed';self.save()

    def execute(self, readiness_result):
        self.root.mkdir(mode=0o700, exist_ok=False)
        self.report['readiness'] = readiness_result;self.save()
        try:
            (self.root/'gates').mkdir(mode=0o700)
            for role in ['dbs', 'hisdbs']:
                for name in ['', 'staging', 'recovery']:(self.root/role/name).mkdir(mode=0o700)
                shutil.copyfile(self.plan['previous_binary'], self.root/role/'staging/crg');(self.root/role/'staging/crg').chmod(0o755)
            self.create({'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': self.ns, 'labels': {'managed-by': 'crg-vendor-test'}}})
            self.namespace_uid = gate.namespace(self.ns)['metadata']['uid']
            self.report['namespace_uid'] = self.namespace_uid;self.save()
            self.create({'apiVersion': 'networking.k8s.io/v1', 'kind': 'NetworkPolicy', 'metadata': {'name': 'deny-all', 'namespace': self.ns}, 'spec': {'podSelector': {}, 'policyTypes': ['Ingress', 'Egress']}})
            for role in ['dbs', 'hisdbs']:
                self.report['phase'] = 'testing-'+role;self.save();self.role(role)
            self.report['phase'] = 'passed'
        except BaseException as error:
            self.report.update(phase='failed', reason=str(error) if isinstance(error, Rejected) else type(error).__name__)
        finally:
            try:
                for role in list(self.pods):self.delete_pod(role)
                if self.namespace_uid:
                    meta = gate.namespace(self.ns)
                    require(meta and meta['metadata']['uid'] == self.namespace_uid and meta['metadata']['labels'].get('managed-by') == 'crg-vendor-test', 'CLEANUP_NAMESPACE_UID')
                    self.run(['kubectl', 'delete', 'namespace', self.ns, '--wait=true', '--timeout=150s'], timeout=160)
                    require(gate.namespace(self.ns) is None, 'CLEANUP_NAMESPACE_NOT_ABSENT')
                    self.report['namespace_absent'] = True
            except BaseException as error:
                self.report.update(phase='failed', cleanup_error=type(error).__name__)
            if self.worker:
                try:self.worker.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    self.worker.terminate()
                    try:self.worker.wait(timeout=15)
                    except subprocess.TimeoutExpired:self.worker.kill();self.worker.wait(timeout=15)
                    self.report.update(phase='failed', local_exec_cleanup_forced=True)
            if self.worker_log:self.worker_log.close()
            self.report['aged_fixture_retained'] = True;self.report['ended_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat();self.save()
        return self.report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--rehearsal', action='store_true')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    try:
        require(sys.platform == 'linux' and os.geteuid() == 0, 'LINUX_TEST_NODE_ROOT_REQUIRED')
        plan = checked_plan(args.plan, args.plan_sha256, args.rehearsal)
        result = readiness(plan)
        if args.execute and result.get('postflight_allowed'):
            require(os.environ.get('CRG_AGED_POSTFLIGHT') == 'authorized-disposable-test-node-only', 'EXPLICIT_LAB_MARKER')
            # Re-read the readiness gate immediately before exclusive work-root creation.
            result = readiness(plan)
            require(result.get('postflight_allowed') is True, 'READINESS_CHANGED')
            def interrupted(signum, frame):
                raise KeyboardInterrupt()
            signal.signal(signal.SIGTERM, interrupted)
            result = Execution(plan, args.plan_sha256).execute(result)
        result.update(P10_complete=False, release_accepted=False)
    except Rejected as error:
        result = {'phase': 'rejected', 'reason': str(error), 'P10_complete': False, 'release_accepted': False}
    except (OSError, TypeError, KeyError, AttributeError, ValueError, RecursionError, subprocess.SubprocessError):
        result = {'phase': 'rejected', 'reason': 'INPUT_SHAPE_READ_OR_INVENTORY', 'P10_complete': False, 'release_accepted': False}
    # Full reports/private Pod specs remain in the private test folder.
    print(json.dumps({k: result[k] for k in ['phase', 'reason', 'postflight_allowed', 'P10_complete', 'release_accepted', 'namespace_absent'] if k in result}, indent=2))
    return 2 if result['phase'] == 'pending' else 1 if result['phase'] in ['rejected', 'failed'] else 0


if __name__ == '__main__':
    sys.exit(main())
