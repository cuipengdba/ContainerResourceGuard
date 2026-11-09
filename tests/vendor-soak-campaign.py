#!/usr/bin/env python3
"""Host-side acceptance fixture for disposable original-image Pods on one test node.

Never a product daemon. Does not apply resources or manage business lifecycles.
Starts only synthetic workers and temporary engine tests in verified lab Pods.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--namespace', required=True)
parser.add_argument('--fixture-root', type=Path, required=True)
parser.add_argument('--work-dir', type=Path, required=True)
parser.add_argument('--run-id', required=True)
parser.add_argument('--source-run-id', help='reuse only the same container workload data from a prior passed equal-duration native run')
parser.add_argument('--test-phase', choices=['smoke', 'baseline', 'enforce', 'acceptance'], required=True)
parser.add_argument('--seconds', type=int, required=True)
parser.add_argument('--agent-sha256', required=True)
parser.add_argument('--cache-sha256', required=True)
args = parser.parse_args()
if not re.fullmatch(r'crg-vendor-lab-[a-z0-9-]+', args.namespace):
    parser.error('only disposable crg-vendor-lab-* namespaces are accepted')
if not re.fullmatch(r'[0-9]{8,12}', args.run_id):
    parser.error('run-id must contain 8..12 digits; two extra digits reserved for backup cycles')
if args.source_run_id and not re.fullmatch(r'[0-9]{8,12}', args.source_run_id):
    parser.error('source-run-id must contain 8..12 digits')
if not 120 <= args.seconds <= 604800 or args.test_phase in ['baseline', 'enforce'] and args.seconds != 86400 or args.test_phase == 'acceptance' and args.seconds != 604800:
    parser.error('smoke requires 120..604800 seconds; baseline/enforce require 86400; acceptance requires 604800')
if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
    parser.error('Linux pidfd support in Python 3.9+ is required for test-worker cleanup')
for path in [args.fixture_root, args.work_dir]:
    if not str(path).startswith('/var/tmp/crg-') or '..' in path.parts or not path.is_absolute():
        parser.error('explicit /var/tmp/crg-* test paths required')
for value in [args.agent_sha256, args.cache_sha256]:
    if not re.fullmatch(r'[0-9a-f]{64}', value):
        parser.error('expected SHA256 digests required')

root = Path(__file__).resolve().parent
worker_source = (root / 'vendor-soak-load.py').read_bytes()
engine_script = root / 'vendor-engine-smoke.py'
roles = {}
jobs = []
created_output = False
report = {'schema': 'crg-vendor-campaign-v1', 'phase': 'preparing',
          'test_phase': args.test_phase, 'requested_seconds': args.seconds,
          'source_run_id': args.source_run_id,
          'worker_sha256': hashlib.sha256(worker_source).hexdigest(),
          'engine_script_sha256': hashlib.sha256(engine_script.read_bytes()).hexdigest(),
          'agent_sha256': args.agent_sha256, 'cache_sha256': args.cache_sha256,
          'scope': 'synthetic SQL/API and engine cycle in original-image clones; vendor-specific APIs not verified',
          'criteria': {'host_available_min_bytes': 8 * 1024**3,
                       'disk_free_min_bytes': 20 * 1024**3,
                       'host_sample_seconds': 60, 'OOM_kill_delta_max': 0,
                       'backup_offsets_seconds': [30] if args.test_phase == 'smoke' else [300] + list(range(21600, args.seconds, 21600))},
          'roles': {}, 'backups': [], 'started_epoch': time.time()}


def run(command, timeout=30, check=True, data=None):
    result = subprocess.run(command, input=data, capture_output=True, timeout=timeout)
    if check and result.returncode:
        # Raw logs can contain private data: never propagate arbitrary stderr.
        raise RuntimeError('test command failed; exit=' + str(result.returncode))
    return result


def ex(role, *command, **kwargs):
    return run(['kubectl', 'exec', '-n', args.namespace, role + '-business', '-c', role, '--', *command], **kwargs)


def save():
    temporary = args.work_dir / 'report.candidate'
    temporary.write_text(json.dumps(report, indent=2))
    temporary.chmod(0o600)
    temporary.replace(args.work_dir / 'report.json')


def guards():
    available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                         if line.startswith('MemAvailable:'))) * 1024
    free = shutil.disk_usage(args.fixture_root).free
    if available < report['criteria']['host_available_min_bytes'] or free < report['criteria']['disk_free_min_bytes']:
        raise RuntimeError('node reserve threshold reached')
    return {'host_available_bytes': available, 'disk_free_bytes': free}


def ticks(pid):
    text = Path('/proc', str(pid), 'stat').read_text()
    return int(text[text.rfind(')') + 2:].split()[19])


def find_guard(group, basename, expected):
    found = []
    for pid in group.joinpath('cgroup.procs').read_text().splitlines():
        try:
            process = Path('/proc', pid)
            argv = process.joinpath('cmdline').read_bytes().split(b'\0')
            if len(argv) > 1 and Path(os.fsdecode(argv[0])).name == basename and argv[1] == b'run':
                if hashlib.sha256(process.joinpath('exe').read_bytes()).hexdigest() != expected:
                    raise RuntimeError('guard binary digest mismatch')
                found.append((int(pid), ticks(pid)))
        except (FileNotFoundError, ProcessLookupError):
            continue
    if len(found) != 1:
        raise RuntimeError('expected exactly one own guard process')
    return found[0]


def verify_process(role, identity):
    pid, start = identity
    membership = Path('/proc', str(pid), 'cgroup').read_text()
    if ticks(pid) != start or membership != roles[role]['membership']:
        raise RuntimeError('own process identity changed')


def controls(group):
    return {name: group.joinpath(name).read_text().strip()
            for name in ['cpu.max', 'memory.max', 'io.max', 'cpu.weight', 'pids.max', 'memory.high', 'memory.swap.max', 'io.weight']
            if group.joinpath(name).exists()}


def process_metrics(identity):
    pid, start = identity
    process = Path('/proc', str(pid))
    text = process.joinpath('stat').read_text()
    fields = text[text.rfind(')') + 2:].split()
    if int(fields[19]) != start:
        raise RuntimeError('process changed during numeric sampling')
    status = dict(line.split(':', 1) for line in process.joinpath('status').read_text().splitlines() if ':' in line)
    io = dict(line.split(':', 1) for line in process.joinpath('io').read_text().splitlines())
    return {'CPU_seconds': (int(fields[11]) + int(fields[12])) / os.sysconf('SC_CLK_TCK'),
            'RSS_bytes': int(status['VmRSS'].split()[0]) * 1024,
            'write_bytes': int(io['write_bytes']), 'wchar': int(io['wchar'])}


def take_sample(role):
    own = roles[role]
    for process in [own['main'], own['agent'], own['cache']]:
        verify_process(role, process)
    if controls(own['group']) != own['controls']:
        raise RuntimeError('resource controls changed during fixed-budget phase')
    state = json.loads(own['state'].read_text())
    expected = 'observe' if args.test_phase in ['baseline', 'smoke'] else 'managed'
    if state['state'] != expected or (expected == 'managed' and not all(item['state'] == 'applied' for item in state['items'])):
        raise RuntimeError('resource state no longer matches phase')
    cache = json.loads(own['cache_state'].read_text())
    if cache.get('action') != 'enforce':
        raise RuntimeError('original cache helper is not in enforce mode')
    events = dict(line.split() for line in own['group'].joinpath('memory.events').read_text().splitlines())
    if int(events['oom_kill']) != own['oom_kills']:
        raise RuntimeError('container OOM kill observed')
    return {'elapsed_seconds': time.monotonic() - started,
            'cpu_stat': own['group'].joinpath('cpu.stat').read_text(),
            'memory_current': int(own['group'].joinpath('memory.current').read_text()),
            'memory_events': {key: int(value) for key, value in events.items()},
            'io_stat': own['group'].joinpath('io.stat').read_text(),
            'agent': process_metrics(own['agent']), 'cache': process_metrics(own['cache']),
            'agent_same_process': True, 'cache_same_process': True, 'PID1_same_process': True}


def stop_worker(role):
    # Identify only our Python entry inside this exact cgroup; never signal a
    # guard, business process, another worker or a reused PID.
    own = roles[role]
    if not own.get('entry'):
        return
    for pid in own['group'].joinpath('cgroup.procs').read_text().splitlines():
        try:
            process = Path('/proc', pid)
            argv = process.joinpath('cmdline').read_bytes().split(b'\0')
            if own.get('entry', '').encode() not in argv:
                continue
            before = ticks(pid)
            handle = os.pidfd_open(int(pid))
            try:
                if ticks(pid) != before or process.joinpath('cgroup').read_text() != own['membership']:
                    raise RuntimeError('worker identity changed')
                signal.pidfd_send_signal(handle, signal.SIGTERM)
            finally:
                os.close(handle)
        except (FileNotFoundError, ProcessLookupError):
            continue


try:
    args.work_dir.mkdir(mode=0o700, exist_ok=False)
    created_output = True
    save()
    guards()
    for role in ['dbs', 'hisdbs']:
        meta = json.loads(run(['kubectl', 'get', 'pod', '-n', args.namespace, role + '-business', '-o', 'json']).stdout)
        if meta['metadata'].get('labels', {}).get('managed-by') != 'crg-vendor-test' or any(meta['spec'].get(flag) for flag in ['hostPID', 'hostNetwork', 'hostIPC']):
            raise RuntimeError('not an isolated original-image lab Pod')
        container = next(item for item in meta['status']['containerStatuses'] if item['name'] == role)
        cid = container['containerID'].split('://')[1]
        runtime = json.loads(run(['crictl', 'inspect', cid]).stdout)
        pid = runtime['info']['pid']
        membership = Path('/proc', str(pid), 'cgroup').read_text()
        relative = next(line.split('::', 1)[1] for line in membership.splitlines() if line.startswith('0::'))
        group = Path('/sys/fs/cgroup') / relative.lstrip('/')
        if group.name != 'cri-containerd-' + cid + '.scope' or '/kubepods.slice/' not in str(group):
            raise RuntimeError('not the own supported cgroup leaf')
        if b'state DOWN' not in run(['nsenter', '-t', str(pid), '-n', '--', 'ip', '-o', 'link', 'show', 'dev', 'eth0']).stdout:
            raise RuntimeError('non-loopback network is not down')
        folder = args.fixture_root / (role + '-business')
        # Verify the host fixture path belongs to this Pod's actual PG mount.
        spec = next(item for item in meta['spec']['containers'] if item['name'] == role)
        volume = next(item['name'] for item in spec['volumeMounts'] if item['mountPath'] == '/opt/postgresql')
        data_path = next(item['hostPath']['path'] for item in meta['spec']['volumes'] if item['name'] == volume)
        if Path(data_path).resolve() != (folder / 'postgresql').resolve():
            raise RuntimeError('fixture data is not this Pod data directory')
        own = {'group': group, 'membership': membership, 'main': (pid, ticks(pid)),
               'agent': find_guard(group, 'crg', args.agent_sha256),
               'cache': find_guard(group, 'containercacheguard', args.cache_sha256),
               'state': folder / 'resource-state/status.json',
               'cache_state': folder / 'cache-state/status.json', 'controls': controls(group)}
        own['oom_kills'] = int(dict(line.split() for line in group.joinpath('memory.events').read_text().splitlines())['oom_kill'])
        own['load_file'] = folder / ('postgresql/basebackup/crg-soak-' + args.run_id + '/load.json')
        roles[role] = own
        report['roles'][role] = {'fixed_controls': own['controls'], 'samples': []}
    started = time.monotonic()
    for role in roles:
        take_sample(role)  # All preconditions checked before creating test data.
    for role, own in roles.items():
        entry = '/tmp/crg-soak-load-' + args.run_id + '.py'
        own['entry'] = entry
        ex(role, '/bin/bash', '-c', 'set -Ce; umask 077; cat > ' + entry + '; chmod 0444 ' + entry, data=worker_source)
        command = 'CRG_VENDOR_SOAK_TEST=disposable-loopback-only python ' + entry + ' --run-id ' + args.run_id + ' --seconds ' + str(args.seconds) + ' --test-phase ' + args.test_phase
        if args.source_run_id:
            command += ' --source-run-id ' + args.source_run_id
        log = (args.work_dir / (role + '-load.log')).open('w')
        job = subprocess.Popen(['kubectl', 'exec', '-n', args.namespace, role + '-business', '-c', role, '--', 'su', '-', 'postgres', '-c', command], stdin=subprocess.DEVNULL, stdout=log, stderr=log)
        jobs.append((role, job, log))
    deadline = time.monotonic() + 360
    while True:
        if any(job.poll() is not None for _, job, _ in jobs):
            raise RuntimeError('worker exited before both workload timers started')
        if all(own['load_file'].exists() and json.loads(own['load_file'].read_text()).get('phase') == 'running' for own in roles.values()):
            break
        if time.monotonic() >= deadline:
            raise RuntimeError('workload initialization deadline')
        guards()
        time.sleep(.5)
    started = time.monotonic()
    report['phase'] = 'measuring'
    report['both_workers_started_epoch'] = time.time()
    backup_index = 0
    next_sample = started
    backup = None
    backup_started = 0
    while True:
        elapsed = time.monotonic() - started
        guards()
        if elapsed >= next_sample - started:
            for role in roles:
                report['roles'][role]['samples'].append(take_sample(role))
            next_sample += 60
            save()
        if backup is not None and backup.poll() is not None:
            log.close()
            current = report['backups'][-1]
            result = json.loads((Path(current_dir) / 'business-backup.json').read_text())
            current['exit'], current['phase'] = backup.returncode, result['phase']
            current['roles'] = {role: {'checks': len(value['checks']), 'cleanup': value.get('own_fixture_schema_restore_database_snapshot_removed', False)} for role, value in result['roles'].items()}
            if backup.returncode or result['phase'] != 'passed' or not all(item['cleanup'] for item in current['roles'].values()):
                raise RuntimeError('periodic engine regression or cleanup failed')
            backup = None
            save()
        if backup is not None and time.monotonic() - backup_started > 1800:
            raise RuntimeError('periodic engine cycle exceeded 1800 seconds')
        offsets = report['criteria']['backup_offsets_seconds']
        if backup is None and backup_index < len(offsets) and elapsed >= offsets[backup_index]:
            cycle_id = args.run_id + ('%02d' % backup_index)
            current_dir = str(args.work_dir / ('backup-' + cycle_id))
            log = (args.work_dir / ('backup-' + cycle_id + '.log')).open('w')
            backup = subprocess.Popen(['python3', str(engine_script), '--namespace', args.namespace, '--work-dir', current_dir, '--run-id', cycle_id, '--cleanup-fixture'], stdin=subprocess.DEVNULL, stdout=log, stderr=log)
            backup_started = time.monotonic()
            report['backups'].append({'offset_seconds': elapsed, 'run_id': cycle_id})
            backup_index += 1
            save()
        if all(job.poll() is not None for _, job, _ in jobs):
            if backup is not None or backup_index != len(offsets):
                raise RuntimeError('workers ended before all scheduled engine cycles finished')
            break
        if elapsed > args.seconds + 120:
            raise RuntimeError('workload completion deadline')
        time.sleep(.5)
    for role, job, log in jobs:
        log.close()
        result = json.loads(roles[role]['load_file'].read_text())
        report['roles'][role]['workload'] = result
        if job.returncode or result.get('phase') != 'passed' or not result.get('primary_not_restarted'):
            raise RuntimeError('native workload failed')
        samples = report['roles'][role]['samples']
        if len(samples) < args.seconds / 60 * .98 or any(b['elapsed_seconds'] - a['elapsed_seconds'] > 120 for a, b in zip(samples, samples[1:])):
            raise RuntimeError('host sampling coverage insufficient')
    report['elapsed_seconds_since_both_started'] = time.monotonic() - started
    report['phase'] = 'passed'
except BaseException as error:
    report['phase'] = 'failed'
    report['failure_class'] = type(error).__name__
    # Fixed strings written by this tool are not arbitrary command output.
    report['failure'] = str(error) if type(error) is RuntimeError else 'fixture exception; inspect private local logs'
finally:
    for role in roles:
        try:
            stop_worker(role)
        except Exception:
            report.setdefault('cleanup_errors', []).append('worker termination verification failed: ' + role)
    if 'backup' in globals() and backup is not None and backup.poll() is None:
        # The engine entry converts TERM into an exception so its per-instance
        # cleanup still runs. Do not terminate business or auxiliary guards.
        backup.terminate()
        try:
            backup.wait(timeout=120)
        except subprocess.TimeoutExpired:
            report.setdefault('cleanup_errors', []).append('temporary engine cleanup still pending; inspect private logs')
    # No business Pod deletion, guard signal or resource relaxation in this tool.
    for role, job, log in jobs:
        try:
            job.wait(timeout=15)
        except subprocess.TimeoutExpired:
            report.setdefault('cleanup_errors', []).append('worker exec client still running: ' + role)
        log.close()
    report['ended_epoch'] = time.time()
    if created_output:
        save()
print(json.dumps({'phase': report['phase'], 'test_phase': args.test_phase, 'failure': report.get('failure')}))
raise SystemExit(0 if report['phase'] == 'passed' else 1)
