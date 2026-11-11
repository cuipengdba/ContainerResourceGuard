#!/usr/bin/env python3
"""Read-only-by-default lab gate and retained-data auxiliary fault execution.

This is a disposable-node test driver, never a product container manager. Long
mode requires the original seven-day run and its actual retained-data postflight;
short rehearsal is explicitly separate and cannot qualify either long stage.
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
import select
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import time

spec = importlib.util.spec_from_file_location('aged_postflight', Path(__file__).with_name('vendor-aged-postflight.py'))
aged = importlib.util.module_from_spec(spec);spec.loader.exec_module(aged)
gate, require, Rejected = aged.gate, aged.require, aged.Rejected
POSTFLIGHT_SHA = '0bd77b3d99ec599a1f546b3a786df2b9c6b34bdf5c3f2e98f42fa7a8f937463c'
KINDS = ['missing', 'invalid', 'crash', 'hang', 'ignoreterm', 'rollback',
         'cgroup-readonly', 'profile-readonly', 'state-readonly', 'cancel-calibration']
CRITERIA = {'PG_API_readiness_seconds': 90, 'cache_after_API_seconds': 45,
            'TERM_seconds': 12, 'degraded_observation_seconds': 180,
            'calibration_cancel_observation_seconds': 60, 'payload_bytes': 67108864,
            'clone_host_available_bytes': 28*1024**3,
            'steady_host_available_bytes': 8*1024**3, 'disk_free_bytes': 20*1024**3,
            'automatic_percentages': {'cpu_percent': 30, 'memory_percent': 30, 'io_percent': 30}}


def checked_plan(path, expected, rehearsal):
    plan, digest = gate.read_json(path)
    require(re.fullmatch(r'[0-9a-f]{64}', expected) and digest == expected, 'FAULT_PLAN_DIGEST')
    require(plan.get('schema') == 'crg-aged-fault-plan-v1'
            and plan.get('mode') == ('short-rehearsal' if rehearsal else 'seven-day-aged-faults')
            and plan.get('criteria') == CRITERIA and plan.get('cases') == KINDS
            and plan.get('pins') == aged.PINS, 'FAULT_PLAN_CONTRACT')
    require(gate.digest(Path(__file__))['sha256'] == plan.get('executor_sha256')
            and gate.digest(Path(__file__).with_name('vendor-aged-postflight.py'))['sha256'] == POSTFLIGHT_SHA,
            'FAULT_EXECUTOR_SOURCE')
    work = gate.lab_root(plan['work_root'])
    require(re.fullmatch(r'crg-vendor-lab-[a-z0-9-]+', plan['namespace']), 'FAULT_NAMESPACE')
    post = aged.checked_plan(Path(plan['postflight_plan']), plan['postflight_plan_sha256'], rehearsal)
    require(post['mode'] == ('short-rehearsal' if rehearsal else 'seven-day-postflight')
            and work != Path(post['work_root']) and plan['namespace'] != post['namespace'], 'FAULT_TARGET_OVERLAP')
    for row in post['roles'].values():
        folder = Path(row['folder'])
        require(not work.is_relative_to(folder) and not folder.is_relative_to(work), 'FAULT_DATA_OVERLAP')
    original = plan['original_supervisors']
    require(set(original) == {'dbs', 'hisdbs'}, 'ORIGINAL_SUPERVISOR_MANIFEST')
    for role, row in original.items():
        require(gate.digest(Path(row['path']))['sha256'] == row['sha256']
                and Path(row['path']).name == 'supervisor.original.sh'
                and str(Path(row['path'])).startswith('/var/tmp/crg-'), 'ORIGINAL_SUPERVISOR_SOURCE')
    return plan, post, original


def postflight_proof(report, post, digest):
    require(report.get('schema') == 'crg-aged-execution-report-v1' and report.get('phase') == 'passed'
            and report.get('mode') == post['mode'] and report.get('plan_sha256') == digest
            and report.get('executor_sha256') == POSTFLIGHT_SHA
            and report.get('source_revision') == aged.PINS['revision']
            and report.get('binary_sha256') == aged.PINS['binary']
            and report.get('criteria') == aged.CRITERIA
            and report.get('postflight_executed') is True and report.get('aged_fixture_retained') is True
            and report.get('namespace_absent') is True and not report.get('cleanup_error')
            and report.get('P10_complete') is False and report.get('release_accepted') is False,
            'POSTFLIGHT_NOT_ACCEPTED')
    tests = report.get('tests', [])
    require(len(tests) == 36 and len({x['name'] for x in tests}) == 36
            and all(x.get('passed') is True for x in tests)
            and set(report.get('roles', {})) == {'dbs', 'hisdbs'}, 'POSTFLIGHT_CHECKS')
    for role, row in report['roles'].items():
        require(row.get('phase') == 'postflight-component-passed'
                and len(row.get('boots', [])) == 2, 'POSTFLIGHT_ROLE')
        a, b = row['boots']
        require(a['container_id'] != b['container_id'] and a['identity'] != b['identity']
                and a['primary_start'] != b['primary_start'], 'POSTFLIGHT_REBUILD')
        aged.validate_native(row['native'], post['run_id']+('0' if role == 'dbs' else '1'))


def no_other_mounts(folders):
    """Reject data consumers/writable ancestors; permit constrained RO monitors."""
    value = json.loads(gate.command(['kubectl', 'get', 'pods', '-A', '-o', 'json']))
    roots = [str(p) for p in folders]
    for pod in value.get('items', []):
        for volume in pod.get('spec', {}).get('volumes', []):
            path = volume.get('hostPath', {}).get('path')
            if path:
                path = os.path.realpath(path)
                direct = any(path == root or path.startswith(root+'/') for root in roots)
                parent = any(root.startswith(path.rstrip('/')+'/') for root in roots)
                if not direct and not parent:continue
                # A node monitor's read-only root view is not another PG owner.
                # Never whitelist Pod names/namespaces or allow direct data mounts.
                consumers = [(c, m) for key in ['containers', 'initContainers', 'ephemeralContainers']
                             for c in pod.get('spec', {}).get(key, [])
                             for m in c.get('volumeMounts', []) if m['name'] == volume['name']]
                constrained = bool(consumers) and all(m.get('readOnly') is True
                    and m.get('mountPropagation') != 'Bidirectional'
                    and c.get('securityContext', {}).get('privileged') is not True
                    and c.get('securityContext', {}).get('allowPrivilegeEscalation') is False
                    and 'ALL' in c.get('securityContext', {}).get('capabilities', {}).get('drop', [])
                    and not set(c.get('securityContext', {}).get('capabilities', {}).get('add', [])) & {'SYS_ADMIN', 'ALL'}
                    for c, m in consumers)
                require(not direct and constrained, 'AGED_DATA_ALREADY_MOUNTED')


def readiness(plan, post):
    component = None
    seal = None
    if plan['mode'] == 'seven-day-aged-faults':
        lineage, actual = gate.load_plan(Path(post['lineage_plan']), post['lineage_plan_sha256'])
        require(actual == '58a8fe7c07c7655c13e1b54a83ad8afd63646947de9b8b8929f1d089dbe2a8cb', 'FROZEN_LONG_LINEAGE')
        require(post['work_root'] == lineage['postflight_root'] and post['namespace'] == lineage['postflight_namespace']
                and all(row['folder'] == str(Path(lineage['component_root'])/'fixture'/(role+'-business'))
                        and row['aged_run_id'] == lineage['run_id'] for role, row in post['roles'].items()), 'FROZEN_LONG_ROLE_BINDING')
        component, inputs = gate.component(lineage)
        seal, actual = gate.read_json(Path(post['lineage_seal']))
        require(actual == post['lineage_seal_sha256']
                == 'd45cd434b6b614141dab56742207fa245c04f59c80d4469c514e7d255fd108bd'
                and seal['launch'] == inputs[1], 'AGED_SEAL_BINDING')
        if component['phase'] == 'pending':
            return {'phase': 'pending', 'runner_identity_verified_live': True,
                    'fault_execution_allowed': False, 'P10_complete': False, 'release_accepted': False}
    oldroot = Path(post['work_root'])
    proof, proof_hash = gate.read_json(oldroot/'report.json')
    postflight_proof(proof, post, plan['postflight_plan_sha256'])
    require(gate.namespace(post['namespace']) is None, 'POSTFLIGHT_NAMESPACE_PRESENT')
    require(gate.namespace(plan['namespace']) is None and not Path(plan['work_root']).exists(), 'FAULT_TARGET_NOT_FRESH')
    for row in proof['roles'].values():
        for boot in row['boots']:
            group = gate.path_clean(boot['cgroup'])
            require(str(group).startswith('/sys/fs/cgroup/kubepods.slice/')
                    and group.name == 'cri-containerd-'+boot['container_id']+'.scope'
                    and not group.exists() and not list(group.parent.glob('cri-containerd-*.scope')),
                    'POSTFLIGHT_CGROUP_PRESENT')
    for proc in Path('/proc').glob('[0-9]*'):
        try:
            args = (proc/'cmdline').read_bytes().split(b'\0')
            require(not (str(Path(plan['postflight_plan'])).encode() in args
                         and any(a.endswith(b'vendor-aged-postflight.py') for a in args)), 'POSTFLIGHT_EXECUTOR_LIVE')
        except (FileNotFoundError, ProcessLookupError):pass
    snapshots = {}
    for role, binding in post['roles'].items():
        folder = gate.path_clean(binding['folder']);native, native_hash = gate.read_json(folder/('postgresql/basebackup/crg-soak-'+binding['aged_run_id']+'/load.json'))
        require(native['phase'] == 'passed' and native['payload_integrity'] is True
                and len(native['final_checksum']) == 5 and native['final_checksum'][0] == 16384
                and native['final_checksum'][2] == CRITERIA['payload_bytes'], 'AGED_DATA_PROOF')
        if component:
            require(native == inputs[3]['roles'][role]['workload'], 'AGED_NATIVE_NOT_ORIGINAL_LONG_RESULT')
        else:
            aged.validate_native(native, binding['aged_run_id'])
        files = {n: gate.digest(folder/n) for n in gate.immutable_files(role)}
        require(files['crg/crg']['sha256'] == aged.PINS['binary']
                and files['ccg/bin/containercacheguard']['sha256'] == aged.PINS['cache'], 'AGED_PROGRAM_SOURCE')
        if seal:
            require(all(gate.directory(folder/n) == v for n, v in seal['roles'][role]['directories'].items()), 'AGED_DIRECTORY_LINEAGE')
            require(all(files[n] == v for n, v in seal['roles'][role]['files'].items() if n != 'crg/crg'), 'AGED_PRIVATE_INPUT_LINEAGE')
        else:
            require(files['pod.json']['sha256'] == binding['pod_sha256'], 'SHORT_POD_SOURCE')
        journal, journal_hash = gate.read_json(folder/'resource-state/journal.json')
        require(journal['identity'] == proof['roles'][role]['boots'][1]['identity'], 'POSTFLIGHT_JOURNAL_IDENTITY')
        logs = {p.name: gate.digest(p) for p in sorted((folder/'log/crg').glob('crg-*.log'))}
        require(logs and all(v['mode'] == 0o600 for v in logs.values())
                and sum(v['size'] for v in logs.values()) <= 1_000_000_000, 'AGED_DAILY_LOGS')
        if seal:
            require(len(logs) >= 7 and all(gate.digest(folder/'log/crg'/n, v['size']) == v
                                           for n, v in seal['roles'][role]['log_prefixes'].items()), 'AGED_LOG_LINEAGE')
        snapshots[role] = {'folder': str(folder), 'native_sha256': native_hash,
                           'checksum': native['final_checksum'],
                           'directories': {n: gate.directory(folder/n) for n in gate.DIRECTORIES},
                           'files': files, 'journal_sha256': journal_hash, 'log_prefixes': logs}
    no_other_mounts([Path(r['folder']) for r in snapshots.values()])
    return {'phase': 'ready-for-aged-faults' if component else 'ready-for-short-rehearsal',
            'fault_execution_allowed': True, 'seven_day_accepted': bool(component),
            'postflight_report_sha256': proof_hash, 'retained_sources': snapshots,
            'P10_complete': False, 'release_accepted': False}


def tree_snapshot(root):
    """Bounded regular files only; never follow a source symlink or device."""
    root = gate.path_clean(root);gate.directory(root)
    result = {};total = 0
    for p in sorted(root.rglob('*')):
        require(not p.is_symlink(), 'STATE_TREE_SYMLINK')
        if p.is_dir():continue
        value = gate.digest(p);total += value['size']
        require(len(result) < 256 and total <= 64*1024**2, 'STATE_TREE_BOUNDS')
        result[str(p.relative_to(root))] = value
    return result


def copy_tree(source, target):
    before = tree_snapshot(source);target.mkdir(mode=0o700)
    for name, value in before.items():
        dest = target/name;dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copyfile(source/name, dest);dest.chmod(value['mode'])
        require(gate.digest(dest)['sha256'] == value['sha256'], 'PRIVATE_COPY_DIGEST')
    require(tree_snapshot(source) == before, 'SOURCE_CHANGED_DURING_COPY')


def fault_pod(original, role, folder, namespace, work, case, kind):
    """Only helper inputs are private; PG, credentials, cache and data stay aged."""
    require(kind in KINDS, 'FAULT_KIND')
    pod = aged.adapt_pod(original, role, folder, namespace, work)
    spec = pod['spec'];main = next(c for c in spec['containers'] if c['name'] == role)
    spec['volumes'] = [v for v in spec['volumes'] if v['name'] not in ['staging', 'recovery']]
    main['volumeMounts'] = [v for v in main['volumeMounts'] if v['name'] not in ['staging', 'recovery']]
    overrides = {'crg': case/'crg', 'crg-config': case/'crg-config', 'resource-state': case/'resource-state'}
    if kind == 'rollback':overrides['ccg'] = case/'ccg'
    for volume in spec['volumes']:
        if volume['name'] in overrides:volume['hostPath']['path'] = str(overrides[volume['name']])
    for mount in main['volumeMounts']:
        if mount['name'] in ['ccg', 'crg']:mount['readOnly'] = True
        if mount['name'] == 'crg-config':mount['readOnly'] = kind == 'profile-readonly'
        if mount['name'] == 'resource-state':mount['readOnly'] = kind == 'state-readonly'
    env = {e['name']: e for e in main['env']}
    for name, value in {'CRG_BIN': '/opt/crg/missing' if kind == 'missing' else '/opt/crg/fault.sh' if kind in ['crash', 'hang', 'ignoreterm'] else '/opt/crg/crg',
                        'CRG_CONFIG': '/etc/crg/config.json', 'CRG_HELPER_SCRIPT': '/opt/crg/optional-agent.sh'}.items():
        require(name in env, 'ORIGINAL_HELPER_ENV');env[name].clear();env[name].update(name=name, value=value)
    if kind == 'cgroup-readonly':
        require(not any(m['mountPath'] == '/sys/fs/cgroup' for m in main['volumeMounts']), 'CGROUP_MOUNT_COLLISION')
        spec['volumes'].append({'name': 'restricted-cgroup', 'hostPath': {'path': '/sys/fs/cgroup', 'type': 'Directory'}})
        main['volumeMounts'].append({'name': 'restricted-cgroup', 'mountPath': '/sys/fs/cgroup', 'readOnly': True})
    return pod


class Execution(aged.Execution):
    def __init__(self, plan, digest, post, original):
        super().__init__(plan, digest)
        self.post, self.original = post, original
        self.report = {'schema': 'crg-aged-fault-report-v1', 'phase': 'preparing', 'mode': plan['mode'],
                       'plan_sha256': digest, 'executor_sha256': gate.digest(Path(__file__))['sha256'],
                       'postflight_executor_sha256': POSTFLIGHT_SHA, 'pins': aged.PINS,
                       'criteria': CRITERIA, 'cases': {}, 'tests': [], 'faults_executed': True,
                       'scope': 'same retained PG data and original private start/config/cache; private fault helper inputs only',
                       'P10_complete': False, 'release_accepted': False}

    def reserve(self, clone=False):
        available = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
        require(available >= CRITERIA['clone_host_available_bytes' if clone else 'steady_host_available_bytes']
                and shutil.disk_usage(self.root).free >= CRITERIA['disk_free_bytes'], 'NODE_RESERVE')

    def prepare(self, role, kind, folder, case):
        case.mkdir(mode=0o700)
        for name in ['crg', 'resource-state']:copy_tree(folder/name, case/name)
        (case/'crg-config').mkdir(mode=0o700)
        config = dict(CRITERIA['automatic_percentages'])
        if kind == 'invalid':config['cpu_percent'] = 0
        p = case/'crg-config/config.json';p.write_text(json.dumps(config));p.chmod(0o600)
        if kind in ['crash', 'hang', 'ignoreterm']:
            bodies = {'crash': 'exit 42', 'hang': "trap 'exit 0' TERM INT; while :; do sleep 1 & wait $!; done",
                      'ignoreterm': "trap '' TERM INT; while :; do sleep 1 & wait $!; done"}
            p = case/'crg/fault.sh';p.write_text('#!/bin/bash\n'+bodies[kind]+'\n');p.chmod(0o755)
        if kind == 'rollback':
            copy_tree(folder/'ccg', case/'ccg')
            p = case/'ccg/scripts/business-supervisor.sh';shutil.copyfile(self.original[role]['path'], p)
            require(gate.digest(p)['sha256'] == self.original[role]['sha256'], 'ROLLBACK_SUPERVISOR_COPY')
        pod = fault_pod(gate.read_json(folder/'pod.json')[0], role, folder, self.ns, self.root, case, kind)
        p = case/'pod.json';p.write_text(json.dumps(pod));p.chmod(0o600)
        return pod

    def cancel(self, key, group, case):
        deadline = time.monotonic()+60;found = None
        while time.monotonic() < deadline and found is None:
            self.reserve()
            for process in (group/'cgroup.procs').read_text().splitlines():
                try:
                    proc = Path('/proc', process);argv = (proc/'cmdline').read_bytes().split(b'\0')
                    if len(argv) < 2 or Path(os.fsdecode(argv[0])).name != 'crg' or argv[1] != b'run':continue
                    require(hashlib.sha256((proc/'exe').read_bytes()).hexdigest() == aged.PINS['binary'], 'CANCEL_EXE_IDENTITY')
                    if any(Path(os.readlink(fd)).name.startswith('.crg-calibration-') for fd in (proc/'fd').iterdir()):found = int(process);break
                except (FileNotFoundError, ProcessLookupError):pass
            if found is None:time.sleep(.2)
        require(found is not None, 'ACTUAL_CALIBRATION_FD_NOT_OBSERVED')
        invalid = case/'crg-config/invalid-next.json';invalid.write_text('{"cpu_percent":0}');invalid.chmod(0o600)
        invalid.replace(case/'crg-config/config.json');handle = os.pidfd_open(found)
        try:
            proc = Path('/proc', str(found))
            require(group.name in (proc/'cgroup').read_text()
                    and hashlib.sha256((proc/'exe').read_bytes()).hexdigest() == aged.PINS['binary'], 'CANCEL_PID_REUSED')
            signal.pidfd_send_signal(handle, signal.SIGTERM);exited = bool(select.select([handle], [], [], 30)[0])
        finally:os.close(handle)
        self.check(key+'-actual-calibration-TERM-before-first-controls', exited
                   and aged.controls(group) == self.report['cases'][key]['runtime_original_controls']
                   and not (case/'crg-config/io-profile.json').exists())

    def case(self, role, kind, snapshot):
        key = role+'-'+kind;folder = Path(snapshot['folder']);case = self.root/key
        no_other_mounts([Path(r['folder']) for r in self.report['readiness']['retained_sources'].values()])
        self.reserve(True);pod = self.prepare(role, kind, folder, case)
        row = {'role': role, 'kind': kind, 'phase': 'preparing', 'aged_native_sha256': snapshot['native_sha256']}
        self.report['cases'][key] = row;self.report['phase'] = 'testing-'+key;self.save()
        group = None
        try:
            state_before = tree_snapshot(case/'resource-state')
            self.create(pod);meta = json.loads(self.run(['kubectl', 'get', 'pod', '-n', self.ns, role+'-business', '-o', 'json']).stdout)
            self.pods[role] = meta['metadata']['uid']
            self.run(['kubectl', 'wait', '-n', self.ns, '--for=condition=Ready', 'pod/'+role+'-business', '--timeout=90s'], timeout=100)
            meta, cid, pid, group = self.identity(role)
            original = aged.controls(group)
            require(original['cpu.max'] == '800000 100000' and original['memory.max'] == '21474836480'
                    and original['io.max'] == '', 'RUNTIME_ORIGINALS')
            self.run(['nsenter', '-t', str(pid), '-n', '--', 'ip', 'link', 'set', 'dev', 'eth0', 'down'])
            require('state DOWN' in self.run(['nsenter', '-t', str(pid), '-n', '--', 'ip', '-o', 'link', 'show', 'dev', 'eth0']).stdout, 'NETWORK_GATE')
            pid1 = self.ex(role, 'cat', '/proc/1/stat').stdout.rsplit(')', 1)[1].split()[19]
            oom = lambda: int(dict(x.split() for x in (group/'memory.events').read_text().splitlines())['oom_kill'])
            original_oom = oom();cachefile = folder/'cache-state/status.json'
            stamp = lambda: (cachefile.stat().st_ino, cachefile.stat().st_mtime_ns, cachefile.stat().st_size) if cachefile.exists() else None
            old_cache = stamp();status = case/'resource-state/status.json'
            old_status = gate.digest(status) if status.exists() else None
            row.update(pod_uid=meta['metadata']['uid'], container_id=cid, cgroup=str(group), runtime_original_controls=original,
                       network_isolated_before_start=True, copied_aged_state=state_before)
            started = time.monotonic();(self.root/'gates'/meta['metadata']['uid']).write_text('isolated\n');row['phase'] = 'booting';self.save()
            if kind == 'cancel-calibration':self.cancel(key, group, case)
            deadline = started+90
            while time.monotonic() < deadline:
                self.reserve()
                try:
                    q = self.ex(role, 'su', '-', 'postgres', '-c', '/opt/postgresql/pgsql/bin/pg_isready -h127.0.0.1 -p5432 -t2', check=False, timeout=max(.01, min(15, deadline-time.monotonic())))
                    if q.returncode == 0 and time.monotonic() < deadline:
                        row.setdefault('PG_ready_seconds', time.monotonic()-started)
                        api = "import urllib2,json; r=urllib2.urlopen(urllib2.Request('http://127.0.0.1:8090/test',data='{}',headers={'Content-Type':'application/json'}),timeout=3); assert r.getcode()==200; assert json.loads(r.read(1024))['Result']=='000'"
                        if self.ex(role, 'python', '-c', api, check=False, timeout=max(.01, min(10, deadline-time.monotonic()))).returncode == 0 and time.monotonic() < deadline:break
                except subprocess.TimeoutExpired:row['observation_timeouts'] = row.get('observation_timeouts', 0)+1;self.save()
                time.sleep(max(0, min(1, deadline-time.monotonic())))
            else:raise Rejected('ORIGINAL_PG_API_90S')
            row['PG_API_ready_seconds'] = time.monotonic()-started
            self.check(key+'-original-PG-and-API-ready-within90s', True)
            deadline = time.monotonic()+45
            while time.monotonic() < deadline:
                self.reserve();caches = self.processes(group, '/opt/ccg/bin/containercacheguard')
                if len(caches) == 1 and caches[0][2] == aged.PINS['cache'] and stamp() != old_cache and cachefile.exists() and gate.read_json(cachefile)[0].get('action') == 'enforce':break
                time.sleep(1)
            else:raise Rejected('FRESH_CACHE_45S')
            self.check(key+'-original-fresh-cache-enforce-and-CCG-readonly', 'ro' in self.ex(role, 'findmnt', '-n', '-o', 'OPTIONS', '/opt/ccg').stdout.strip().split(','))
            self.check(key+'-SQL-after-cache-and-original-ls-probe', self.sql(role, 'SELECT 1;') == '1' and self.ex(role, 'ls', check=False, timeout=10).returncode == 0)
            schema = 'crg_soak_'+self.post['roles'][role]['aged_run_id']
            query = "SELECT count(*),sum(id),sum(octet_length(payload)),md5(string_agg(md5(payload),'' ORDER BY id)),sum(counter) FROM "+schema+'.fixture;'
            expected = [str(x) for x in snapshot['checksum']]
            primary = self.sql(role, 'SELECT pg_postmaster_start_time();')
            self.check(key+'-actual-aged64MiB-and-final-counter-reopened', self.sql(role, query).split('|') == expected)
            if kind in ['cgroup-readonly', 'profile-readonly']:
                deadline = time.monotonic()+180;value = None
                while time.monotonic() < deadline:
                    if status.exists() and gate.digest(status) != old_status:
                        value = gate.read_json(status)[0]
                        if value.get('state') == 'degraded':break
                    self.reserve();time.sleep(1)
                else:raise Rejected('FRESH_DEGRADED_RESULT_180S')
                row['resource_state'] = value['state'];row['automatic_io'] = value.get('automatic_io');self.save()
                if kind == 'profile-readonly':self.check(key+'-output-permission-skips-measurement', value.get('automatic_io', {}).get('reason_code') == 'calibration_output_unwritable' and not (case/'crg-config/io-profile.json').exists())
                else:self.check(key+'-read-only-controls-remain-original', aged.controls(group) == original and 'ro' in self.ex(role, 'findmnt', '-n', '-o', 'OPTIONS', '/sys/fs/cgroup').stdout.strip().split(','))
            if kind == 'state-readonly':
                r = self.ex(role, '/opt/crg/crg', 'run', '--config', '/etc/crg/config.json', '--once', check=False, timeout=20)
                self.check(key+'-state-readonly-refuses-before-benchmark-or-controls', r.returncode != 0 and tree_snapshot(case/'resource-state') == state_before and not (case/'crg-config/io-profile.json').exists() and aged.controls(group) == original)
            self.check(key+'-aged-payload-counter-and-PG-preserved-after-fault', self.sql(role, query).split('|') == expected and self.sql(role, 'SELECT pg_postmaster_start_time();') == primary)
            self.check(key+'-PID1-and-OOM-preserved', self.ex(role, 'cat', '/proc/1/stat').stdout.rsplit(')', 1)[1].split()[19] == pid1 and oom() == original_oom)
            stopped = time.monotonic();deadline = stopped+12;self.ex(role, 'kill', '-TERM', '1', check=False, timeout=10)
            while time.monotonic() < deadline:
                meta = json.loads(self.run(['kubectl', 'get', 'pod', '-n', self.ns, role+'-business', '-o', 'json'], timeout=max(.01, min(5, deadline-time.monotonic()))).stdout)
                require(meta['metadata']['uid'] == self.pods[role], 'TERM_POD_IDENTITY')
                state = next(x['state'] for x in meta['status']['containerStatuses'] if x['name'] == role)
                if 'terminated' in state:break
                time.sleep(.2)
            else:raise Rejected('ORIGINAL_TERM_12S')
            row['TERM_seconds'] = time.monotonic()-stopped;row['main_exit_code'] = state['terminated']['exitCode']
            self.check(key+'-original-TERM-within12s', row['TERM_seconds'] <= 12)
            row['phase'] = 'checked'
        except BaseException as error:
            row.update(phase='failed', reason=str(error) if isinstance(error, Rejected) else type(error).__name__);raise
        finally:
            self.delete_pod(role, group);row['own_pod_removed'] = role not in self.pods;self.save()

    def retained(self, role, snapshot):
        folder = Path(snapshot['folder'])
        self.check(role+'-aged-directories-inputs-program-and-source-journal-unchanged',
                   all(gate.directory(folder/n) == v for n, v in snapshot['directories'].items())
                   and all(gate.digest(folder/n) == v for n, v in snapshot['files'].items())
                   and gate.digest(folder/'resource-state/journal.json')['sha256'] == snapshot['journal_sha256'])
        old = snapshot['log_prefixes'];logs = {p.name: gate.digest(p) for p in (folder/'log/crg').glob('crg-*.log')}
        self.check(role+'-daily0600-aged-log-prefixes-retained-and-new-output',
                   all(gate.digest(folder/'log/crg'/n, v['size']) == v for n, v in old.items())
                   and all(v['mode'] == 0o600 for v in logs.values()) and sum(v['size'] for v in logs.values()) <= 1_000_000_000
                   and any(n not in old or v['size'] > old[n]['size'] for n, v in logs.items()))

    def execute(self, ready):
        self.root.mkdir(mode=0o700, exist_ok=False);self.report['readiness'] = ready;self.save()
        try:
            (self.root/'gates').mkdir(mode=0o700)
            self.create({'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': self.ns, 'labels': {'managed-by': 'crg-vendor-test'}}})
            self.namespace_uid = gate.namespace(self.ns)['metadata']['uid'];self.report['namespace_uid'] = self.namespace_uid;self.save()
            self.create({'apiVersion': 'networking.k8s.io/v1', 'kind': 'NetworkPolicy', 'metadata': {'name': 'deny-all', 'namespace': self.ns}, 'spec': {'podSelector': {}, 'policyTypes': ['Ingress', 'Egress']}})
            for role, snapshot in ready['retained_sources'].items():
                for kind in KINDS:self.case(role, kind, snapshot)
                self.retained(role, snapshot)
            require(len(self.report['cases']) == 20 and len(self.report['tests']) == 152, 'COMPLETE_CASE_SET')
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
                    require(gate.namespace(self.ns) is None, 'CLEANUP_NAMESPACE_NOT_ABSENT');self.report['namespace_absent'] = True
            except BaseException as error:self.report.update(phase='failed', cleanup_error=str(error) if isinstance(error, Rejected) else type(error).__name__)
            self.report.update(aged_fixture_retained=True, ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());self.save()
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
        plan, post, original = checked_plan(args.plan, args.plan_sha256, args.rehearsal)
        result = readiness(plan, post)
        if args.execute and result.get('fault_execution_allowed'):
            require(os.environ.get('CRG_AGED_FAULTS') == 'authorized-disposable-test-node-only', 'EXPLICIT_LAB_MARKER')
            result = readiness(plan, post);require(result.get('fault_execution_allowed') is True, 'READINESS_CHANGED')
            def interrupted(signum, frame):raise KeyboardInterrupt()
            signal.signal(signal.SIGTERM, interrupted)
            result = Execution(plan, args.plan_sha256, post, original).execute(result)
    except Rejected as error:
        result = {'phase': 'rejected', 'reason': str(error), 'P10_complete': False, 'release_accepted': False}
    except (OSError, TypeError, KeyError, AttributeError, ValueError, RecursionError, subprocess.SubprocessError):
        result = {'phase': 'rejected', 'reason': 'INPUT_SHAPE_READ_OR_INVENTORY', 'P10_complete': False, 'release_accepted': False}
    print(json.dumps({k: result[k] for k in ['phase', 'reason', 'fault_execution_allowed', 'seven_day_accepted', 'runner_identity_verified_live', 'P10_complete', 'release_accepted'] if k in result}, indent=2))
    return 2 if result['phase'] == 'pending' else 1 if result['phase'] in ['rejected', 'failed'] else 0


if __name__ == '__main__':
    sys.exit(main())
