#!/usr/bin/env python3
"""Actual-controller checks in labelled scratch containers on ephemeral CI VMs.

Test fixture only. Never a product controller or a vendor business acceptance.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import stat
import struct
import subprocess
import tempfile
import time
import traceback
import uuid

parser = argparse.ArgumentParser(description=__doc__)
for name in ['binary', 'holder', 'load', 'output']:
    parser.add_argument('--' + name, type=Path, required=True)
parser.add_argument('--source-revision', required=True)
parser.add_argument('--expected-arch', choices=['amd64', 'arm64'], required=True)
args = parser.parse_args()
if platform.system() != 'Linux' or os.geteuid() != 0 or os.environ.get('CRG_NATIVE_CGROUP_TEST') != 'ephemeral-github-vm-only':
    parser.error('explicit ephemeral GitHub VM test marker and root are required')
if not re.fullmatch('[0-9a-f]{40}', args.source_revision):
    parser.error('exact source SHA required')
if platform.machine() not in {'amd64': ['x86_64'], 'arm64': ['aarch64', 'arm64']}[args.expected_arch]:
    parser.error('actual native architecture differs')
args.output = args.output.resolve()
args.output.mkdir(mode=0o755, parents=True, exist_ok=False)
nonce = uuid.uuid4().hex
tag = 'crg-native-controller:' + nonce
private = Path(tempfile.mkdtemp(prefix='crg-native-controller-')).resolve()
containers = []
storage = {'stage': 'not-created'}
fields = ['cpu.max', 'memory.max', 'io.max', 'pids.max', 'cpu.weight', 'io.weight', 'memory.high', 'memory.swap.max']
report = {'phase': 'preparing', 'source_revision': args.source_revision,
          'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'scope': 'native scratch placeholder PID1, actual own cgroup; not vendor business',
          'architecture': args.expected_arch, 'machine': platform.machine(), 'kernel': platform.release(),
          'tests': [], 'measurements': {}, 'cleanup': {}}


def save():
    candidate = args.output / 'report.candidate'
    candidate.write_text(json.dumps(report, indent=2) + '\n')
    candidate.chmod(0o644)
    candidate.replace(args.output / 'report.json')


def record(name, passed, **data):
    report['tests'].append(dict(name=name, passed=bool(passed), **data))
    save()
    if not passed:
        raise AssertionError(name)


def run(command, timeout=30, check=True):
    result = subprocess.run([str(x) for x in command], capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        report['last_failed_command'] = {'operation': str(command[0:2]), 'exit': result.returncode,
                                         'stderr_tail': result.stderr[-1000:]}
        save()
        raise RuntimeError('fixture command failed')
    return result


def read(path):
    if path.stat().st_size > 1024 * 1024:
        raise RuntimeError('fixture JSON exceeds1MiB')
    return json.loads(path.read_text())


def proc(pid):
    text = Path('/proc', str(pid), 'stat').read_text()
    values = text[text.rfind(')') + 2:].split()
    return {'pid': int(pid), 'start_ticks': int(values[19])}


def controls(item):
    return {name: (item['group'] / name).read_text().strip() for name in fields}


def actors(item):
    found = []
    for pid in (item['group'] / 'cgroup.procs').read_text().splitlines():
        try:
            p = Path('/proc', pid)
            argv = p.joinpath('cmdline').read_bytes().split(b'\0')
            if len(argv) > 1 and argv[0] == b'/crg' and argv[1] == b'run':
                if hashlib.sha256(p.joinpath('exe').read_bytes()).hexdigest() != report['programs']['crg']:
                    raise RuntimeError('running Agent source differs')
                found.append(proc(pid))
        except (FileNotFoundError, ProcessLookupError):
            pass
    return found


def alive(item):
    if proc(item['main']['pid']) != item['main']:
        raise RuntimeError('placeholder PID1 identity changed')
    if Path('/proc', str(item['main']['pid']), 'cgroup').read_text() != item['membership']:
        raise RuntimeError('placeholder cgroup identity changed')


def ex(item, *command, **kwargs):
    alive(item)
    return run(['docker', 'exec', item['id'], *command], **kwargs)


def status(item):
    return read(item['folder'] / 'state/status.json')


def start_agent(item, seconds=30):
    alive(item)
    path = item['folder'] / 'state/status.json'
    previous_stamp = path.stat().st_mtime_ns if path.exists() else None
    run(['docker', 'exec', '-d', item['id'], '/crg', 'run', '--config', '/etc/crg/config.json'])
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        alive(item)
        current = actors(item)
        if len(current) > 1:
            raise RuntimeError('more than one own Agent')
        if len(current) == 1 and path.exists() and path.stat().st_mtime_ns != previous_stamp:
            s = status(item)
            if s['state'] in ['managed', 'degraded']:
                return s, current[0]
        time.sleep(.2)
    raise RuntimeError('Agent readiness observation deadline')


def stop_agent(item):
    result = json.loads(ex(item, '/crg', 'disable', '--config', '/etc/crg/config.json', timeout=30).stdout)
    deadline = time.monotonic() + 10
    while actors(item) and time.monotonic() < deadline:
        time.sleep(.1)
    return result['state'] == 'restored' and not actors(item) and controls(item) == item['original']


def logs(item):
    paths = list((item['folder'] / 'state/logs').glob('crg-*.log'))
    if not paths or any(p.stat().st_mode & 0o777 != 0o600 for p in paths):
        raise RuntimeError('daily0600 logs absent')
    events = [json.loads(line) for p in paths for line in p.read_text().splitlines()]
    if not any(x['event'] == 'cgroup_detected' and x.get('fields', {}).get('check', {}).get('cgroup_version') == 'v2' for x in events):
        raise RuntimeError('v2 version log absent')
    return paths, events


def verify_storage():
    loop = storage['loop']
    if not re.fullmatch(r'/dev/loop[0-9]+', loop):
        raise RuntimeError('not an owned loop device')
    attached = run(['losetup', '--noheadings', '--raw', '--output', 'BACK-FILE', loop]).stdout.strip()
    if attached != str(private / 'block.img') or not stat.S_ISBLK(os.stat(loop).st_mode):
        raise RuntimeError('loop backing file differs')
    device = Path('/dev/mapper', storage['name'])
    value = device.stat()
    if not stat.S_ISBLK(value.st_mode):
        raise RuntimeError('not the owned mapper block device')
    root = Path('/sys/dev/block', str(os.major(value.st_rdev)) + ':' + str(os.minor(value.st_rdev)))
    if root.joinpath('dm/name').read_text().strip() != storage['name'] or root.joinpath('dm/uuid').read_text().strip() != storage['uuid']:
        raise RuntimeError('mapper ownership UUID/name differs')
    if sorted(x.name for x in root.joinpath('slaves').iterdir()) != [Path(loop).name]:
        raise RuntimeError('mapper has an unexpected backing device')
    loop_device = os.stat(loop).st_rdev
    expected = ['0', str(2 * 1024**3 // 512), 'linear', str(os.major(loop_device)) + ':' + str(os.minor(loop_device)), '0']
    if run(['dmsetup', 'table', storage['name']]).stdout.split() != expected:
        raise RuntimeError('mapper target geometry differs')
    return device, value.st_rdev


def prepare_storage():
    # A real, disposable dm UUID over an exclusive loop file. No existing disk
    # is formatted, no partition identity is fabricated, and no profile is given.
    storage.update(stage='creating', name='crg-native-' + nonce, uuid='CRG-NATIVE-' + nonce)
    image = private / 'block.img'
    descriptor = os.open(image, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        os.ftruncate(descriptor, 2 * 1024**3)
    finally:
        os.close(descriptor)
    storage['loop'] = run(['losetup', '--find', '--show', '--direct-io=on', '--nooverlap', image]).stdout.strip()
    if not re.fullmatch(r'/dev/loop[0-9]+', storage['loop']):
        raise RuntimeError('unexpected owned loop allocation')
    if run(['losetup', '--noheadings', '--raw', '--output', 'BACK-FILE', storage['loop']]).stdout.strip() != str(image):
        raise RuntimeError('new loop backing file differs')
    run(['dmsetup', 'create', storage['name'], '--uuid', storage['uuid'], '--table', '0 ' + str(2 * 1024**3 // 512) + ' linear ' + storage['loop'] + ' 0'])
    device, number = verify_storage()
    run(['mkfs.ext4', '-q', '-m', '0', '-E', 'lazy_itable_init=0,lazy_journal_init=0', device], timeout=90)
    mount = private / 'blockfs'
    mount.mkdir(mode=0o700)
    run(['mount', '-t', 'ext4', '-o', 'nodev,nosuid', device, mount])
    if not mount.is_mount() or mount.stat().st_dev != number:
        raise RuntimeError('owned filesystem mount differs')
    mount.chmod(0o700)
    storage.update(stage='mounted', directory=mount, number=number)
    report['storage_fixture'] = {'kind': 'ext4 on real dm-linear UUID over exclusive loop file', 'sparse_backing_bytes': 2 * 1024**3, 'physical_independent_device': False, 'device': str(os.major(number)) + ':' + str(os.minor(number))}


def cleanup_storage():
    if storage['stage'] == 'not-created':
        return
    # Partial setup is a retained failure; do not guess owners or detach globals.
    if storage['stage'] != 'mounted':
        raise RuntimeError('partial block fixture setup requires VM disposal; private file retained')
    device, number = verify_storage()
    mount = storage['directory']
    if not mount.is_mount() or mount.stat().st_dev != number:
        raise RuntimeError('cleanup mount ownership differs')
    run(['umount', mount], timeout=30)
    if mount.is_mount() or mount.stat().st_dev == number:
        raise RuntimeError('own mount remains active')
    verify_storage()
    run(['dmsetup', 'remove', storage['name']], timeout=30)
    deadline = time.monotonic() + 10
    root = Path('/sys/dev/block', str(os.major(number)) + ':' + str(os.minor(number)))
    while (root.exists() or device.exists()) and time.monotonic() < deadline:
        time.sleep(.1)
    if root.exists() or device.exists():
        raise RuntimeError('own mapper cleanup incomplete')
    attached = run(['losetup', '--noheadings', '--raw', '--output', 'BACK-FILE', storage['loop']]).stdout.strip()
    if attached != str(private / 'block.img'):
        raise RuntimeError('loop ownership changed before detach')
    run(['losetup', '--detach', storage['loop']])
    remaining = run(['losetup', '--associated', private / 'block.img', '--noheadings', '--raw', '--output', 'NAME']).stdout.strip()
    if remaining:
        raise RuntimeError('own loop backing file still associated')
    report['cleanup']['own_mount_mapper_and_loop_absent'] = True


def make_folder(name, config):
    folder = storage['directory'] / name
    folder.mkdir(mode=0o700)
    for sub in ['config', 'state', 'data']:
        (folder / sub).mkdir(mode=0o700)
    config = {**config, 'data_paths': ['/data'], 'state_dir': '/state', 'log_dir': '/state/logs', 'interval_seconds': 1}
    path = folder / 'config/config.json'
    path.write_text(json.dumps(config))
    path.chmod(0o600)
    (folder / 'data/sentinel').write_text('preserve\n')
    return folder


def launch(folder, name, readonly=False):
    name = 'crg-native-' + nonce + '-' + name
    command = ['docker', 'run', '-d', '--name', name, '--label', 'crg.native-ci=' + nonce,
               '--network', 'none', '--cgroupns', 'host', '--cpus', '2', '--memory', '4g', '--memory-swap', '4g']
    command += ['--cap-drop', 'ALL'] if readonly else ['--privileged']
    command += ['--mount', 'type=bind,src=/sys/fs/cgroup,dst=/sys/fs/cgroup' + (',readonly' if readonly else '')]
    for source, target in [('config', '/etc/crg'), ('state', '/state'), ('data', '/data')]:
        command += ['--mount', 'type=bind,src=' + str(folder / source) + ',dst=' + target]
    command.append(tag)
    cid = run(command).stdout.strip()
    if not re.fullmatch('[0-9a-f]{64}', cid):
        raise RuntimeError('unexpected Docker ID')
    item = {'id': cid, 'folder': folder}
    containers.append(item)  # Keep cleanup ownership even if a later guard fails.
    meta = json.loads(run(['docker', 'inspect', cid]).stdout)[0]
    host = meta['HostConfig']
    if meta['Id'] != cid or meta['Config']['Labels'].get('crg.native-ci') != nonce or host['NetworkMode'] != 'none' or host.get('PidMode') not in ['', 'private'] or host['CgroupnsMode'] != 'host':
        raise RuntimeError('own private Docker fixture metadata differs')
    pid = meta['State']['Pid']
    if pid <= 1 or any(Path('/proc', str(pid), 'ns', ns).stat().st_ino == Path('/proc/1/ns', ns).stat().st_ino for ns in ['pid', 'mnt', 'net']):
        raise RuntimeError('private process/mount/network namespace required')
    membership = Path('/proc', str(pid), 'cgroup').read_text()
    lines = membership.splitlines()
    if len(lines) != 1 or not lines[0].startswith('0::/'):
        raise RuntimeError('pure cgroupv2 membership required')
    group = Path('/sys/fs/cgroup') / lines[0].split('::', 1)[1].lstrip('/')
    if group.resolve() != group or group.name not in [cid, 'docker-' + cid + '.scope']:
        raise RuntimeError('not the own Docker cgroup leaf')
    item.update(group=group, main=proc(pid), membership=membership)
    item['original'] = controls(item)
    item['oom'] = int(dict(x.split() for x in (group / 'memory.events').read_text().splitlines())['oom_kill'])
    mounts = [line.split(' - ', 1)[0].split() for line in Path('/proc', str(pid), 'mountinfo').read_text().splitlines() if line.split(' - ', 1)[0].split()[4] == '/sys/fs/cgroup']
    if readonly and (not mounts or not all('ro' in x[5].split(',') for x in mounts) or host.get('CapDrop') != ['ALL']):
        raise RuntimeError('fixture is not actually read-only/capability-revoked')
    return item


def remove(item):
    existing = run(['docker', 'inspect', item['id']], check=False)
    if existing.returncode:
        raise RuntimeError('own container disappeared before controlled cleanup')
    meta = json.loads(existing.stdout)[0]
    if meta['Id'] != item['id'] or meta['Config']['Labels'].get('crg.native-ci') != nonce:
        raise RuntimeError('cleanup owner differs')
    run(['docker', 'stop', '--time', '10', item['id']], timeout=20)
    run(['docker', 'rm', item['id']])
    absent = run(['docker', 'container', 'ls', '-a', '--filter', 'id=' + item['id'], '--format', '{{.ID}}'])
    deadline = time.monotonic() + 10
    while item.get('group', Path('/nonexistent')).exists() and time.monotonic() < deadline:
        time.sleep(.1)
    if absent.stdout.strip() or item.get('group', Path('/nonexistent')).exists():
        raise RuntimeError('own Docker or cgroup cleanup incomplete')
    item['removed'] = True


def exact(item, s, expected):
    alive(item)
    return (s['state'] == 'managed' and len(s['items']) == 3 and
            {x['file'] for x in s['items']} == {'cpu.max', 'memory.max', 'io.max'} and
            all(x['state'] == 'applied' for x in s['items']) and controls(item) == expected)


try:
    save()
    report['programs'] = {}
    for path, name in [(args.binary, 'crg'), (args.holder, 'hold'), (args.load, 'load')]:
        blob = path.read_bytes()
        if len(blob) < 64 or blob[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', blob, 18)[0] != {'amd64': 62, 'arm64': 183}[args.expected_arch]:
            raise RuntimeError('test executable is not the native static ELF target')
        offset = struct.unpack_from('<Q', blob, 32)[0]
        size, count = struct.unpack_from('<HH', blob, 54)
        if size < 56 or offset + size * count > len(blob) or any(struct.unpack_from('<I', blob, offset + size * n)[0] == 3 for n in range(count)):
            raise RuntimeError('test executable requires an ELF interpreter or has invalid program headers')
        report['programs'][name] = hashlib.sha256(blob).hexdigest()
        shutil.copyfile(path, private / name)
        (private / name).chmod(0o755)
    info = json.loads(run([args.binary.resolve(), 'build-info']).stdout)
    record('exact-native-program-source', info['revision'] == args.source_revision and info['arch'] == args.expected_arch and info['os'] == 'linux')
    endpoint = json.loads(run(['docker', 'context', 'inspect', '--format', '{{json .Endpoints.docker.Host}}']).stdout)
    record('local-Docker-only', endpoint in ['unix:///var/run/docker.sock', 'unix:///run/docker.sock'])
    report['docker'] = json.loads(run(['docker', 'version', '--format', '{{json .Server}}']).stdout)
    (private / 'Dockerfile').write_text('FROM scratch\nCOPY crg /crg\nCOPY hold /hold\nCOPY load /load\nENTRYPOINT ["/hold"]\n')
    run(['docker', 'build', '--network', 'none', '--label', 'crg.native-ci=' + nonce, '-t', tag, str(private)], timeout=120)
    image = json.loads(run(['docker', 'image', 'inspect', tag]).stdout)[0]
    record('scratch-image-native-and-owned', image['Architecture'] == args.expected_arch and image['Config']['Labels']['crg.native-ci'] == nonce)
    prepare_storage()
    manual = make_folder('manual', {'resource_mode': 'manual', 'limits': {'cpu_cores': .5, 'memory_max': '128MiB', 'io_read_bps': '4MiB', 'io_write_bps': '4MiB', 'io_read_iops': 256, 'io_write_iops': 256}})
    item = launch(manual, 'manual')
    dev = manual.joinpath('data').stat().st_dev
    device = str(os.major(dev)) + ':' + str(os.minor(dev))
    report['data_device'] = device
    root = Path('/sys/dev/block', device)
    report['device_inventory'] = {'exposed': root.exists(), 'is_partition': root.joinpath('partition').exists(), 'direct_identity_files': {p: root.joinpath(p).is_file() for p in ['dm/uuid', 'device/wwid', 'wwid']}}
    expected = {**item['original'], 'cpu.max': '50000 100000', 'memory.max': str(128 * 1024**2), 'io.max': device + ' rbps=4194304 wbps=4194304 riops=256 wiops=256'}
    s, agent = start_agent(item)
    record('manual-exact-three-actual-controls', exact(item, s, expected), actual_controls=controls(item))
    logs(item)
    before = dict(x.split() for x in (item['group'] / 'cpu.stat').read_text().splitlines())
    started = time.monotonic()
    cpu = json.loads(ex(item, '/load', '--mode', 'cpu', '--seconds', '8', '--workers', '4', timeout=20).stdout)
    elapsed = time.monotonic() - started
    after = dict(x.split() for x in (item['group'] / 'cpu.stat').read_text().splitlines())
    used = (int(after['usage_usec']) - int(before['usage_usec'])) / 1e6
    report['measurements']['CPU'] = {'actual_wall_seconds': elapsed, 'used_CPU_seconds': used, 'average_cores': used / elapsed, 'nr_throttled_delta': int(after['nr_throttled']) - int(before['nr_throttled']), 'load': cpu}
    record('CPU-actual-throttling', .2 <= used / elapsed <= .65 and int(after['nr_throttled']) > int(before['nr_throttled']))
    for mode in ['read', 'write', 'randwrite']:
        value = json.loads(ex(item, '/load', '--mode', mode, '--seconds', '6', '--directory', '/data', timeout=45).stdout)
        report['measurements'][mode] = value
        record(mode + '-actual-direct-IO-cap', value['seconds'] >= 6 and value['count'] > 0 and 0 < value['rate'] <= 4 * 1024**2 * 1.35 and (mode != 'randwrite' or 0 < value['iops'] <= 256 * 1.35))
    value = json.loads(ex(item, '/load', '--mode', 'memory', '--bytes', str(32 * 1024**2), '--seconds', '4', timeout=15).stdout)
    record('memory-limit-and-safe-allocation', value['count'] == 32 * 1024**2 and controls(item) == expected)
    if actors(item) != [agent] or proc(agent['pid']) != agent:
        raise RuntimeError('Agent identity changed before targeted crash')
    with_handle = os.pidfd_open(agent['pid'])
    try:
        if proc(agent['pid']) != agent or Path('/proc', str(agent['pid']), 'cgroup').read_text() != item['membership']:
            raise RuntimeError('targeted Agent identity changed')
        signal.pidfd_send_signal(with_handle, signal.SIGKILL)
    finally:
        os.close(with_handle)
    deadline = time.monotonic() + 10
    while actors(item) and time.monotonic() < deadline:
        time.sleep(.1)
    alive(item)
    record('Agent-crash-retains-kernel-caps-and-PID1', not actors(item) and controls(item) == expected)
    s, restarted = start_agent(item)
    record('same-journal-Agent-restart', restarted != agent and exact(item, s, expected))
    record('manual-disable-restores-eight-originals', stop_agent(item))
    record('manual-logs-sentinel-and-no-OOM', bool(logs(item)) and (manual / 'data/sentinel').read_text() == 'preserve\n' and int(dict(x.split() for x in (item['group'] / 'memory.events').read_text().splitlines())['oom_kill']) == item['oom'])
    remove(item)
    percent = make_folder('percent', {'cpu_percent': 10, 'memory_percent': 1, 'io_percent': 20})
    item = launch(percent, 'percent')
    s, agent = start_agent(item, 210)  # Product180s calibration plus fixed30s observation.
    hostcpus = sum(int(b) - int(a) + 1 if '-' in part else 1 for part in Path('/sys/devices/system/cpu/online').read_text().strip().split(',') for a, b in [part.split('-') if '-' in part else (part, part)])
    hostmem = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:'))) * 1024
    profile = percent / 'config/io-profile.json'
    p = read(profile)
    if len(p['devices']) != 1:
        raise RuntimeError('expected exactly one automatically calibrated device')
    d = p['devices'][0]
    profile_bytes = profile.read_bytes()
    profile_stamp = profile.stat().st_mtime_ns
    page = os.sysconf('SC_PAGESIZE')
    rates = [math.floor(d[k] * 20 / 100) for k in ['read_bps', 'write_bps', 'read_iops', 'write_iops']]
    expected = {**item['original'], 'cpu.max': str(int(hostcpus * 10 / 100 * 100000)) + ' 100000', 'memory.max': str(int(hostmem * 1 / 100) // page * page), 'io.max': d['device'] + ' ' + ' '.join(k + '=' + str(v) for k, v in zip(['rbps', 'wbps', 'riops', 'wiops'], rates))}
    report['measurements']['percent'] = {'host_online_CPUs': hostcpus, 'host_memory_bytes': hostmem, 'requested_percentages': {'cpu': 10, 'memory': 1, 'IO': 20}, 'expected_controls': expected, 'automatic_IO_state': s.get('automatic_io', {}).get('state'), 'profile_sha256': hashlib.sha256(profile_bytes).hexdigest()}
    record('independent-percentages-and-real-automatic-profile', s.get('automatic_io', {}).get('state') == 'calibrated' and exact(item, s, expected) and all(v > 0 for v in rates))
    paths, events = logs(item)
    prefix = {p.name: p.read_bytes() for p in paths}
    old_id = item['id']
    journal = read(percent / 'state/journal.json')
    record('percent-disable-before-normal-rebuild', stop_agent(item))
    remove(item)
    item = launch(percent, 'rebuild')
    s, agent = start_agent(item)
    previous = read(percent / 'state/journal.previous.json')
    current = read(percent / 'state/journal.json')
    record('new-Docker-ID-discovers-new-journal-identity', item['id'] != old_id and previous['identity'] == journal['identity'] and current['identity'] != previous['identity'] and exact(item, s, expected))
    record('stable-profile-reused-without-second-calibration', s.get('automatic_io', {}).get('state') == 'reused' and profile.read_bytes() == profile_bytes and profile.stat().st_mtime_ns == profile_stamp)
    paths, events = logs(item)
    record('daily-log-prefix-retained-and-appended', all((percent / 'state/logs' / name).read_bytes().startswith(data) and (percent / 'state/logs' / name).stat().st_size > len(data) for name, data in prefix.items()))
    record('new-container-originals-restore-and-no-OOM', stop_agent(item) and (percent / 'data/sentinel').read_text() == 'preserve\n' and int(dict(x.split() for x in (item['group'] / 'memory.events').read_text().splitlines())['oom_kill']) == item['oom'])
    remove(item)
    readonly = make_folder('readonly', {'resource_mode': 'manual', 'limits': {'cpu_cores': .5, 'memory_max': '128MiB', 'io_read_bps': '4MiB', 'io_write_bps': '4MiB', 'io_read_iops': 256, 'io_write_iops': 256}})
    item = launch(readonly, 'readonly', readonly=True)
    s, agent = start_agent(item)
    record('actual-readonly-without-capabilities-is-degraded', s['state'] == 'degraded' and controls(item) == item['original'] and all(x['state'] != 'applied' for x in s['items']))
    _, events = logs(item)
    alive(item)
    record('readonly-failure-visible-and-PID1-preserved', any('read-only file system' in x.get('detail', '') for x in s['items']) and bool(events))
    record('readonly-disable-with-no-owned-mutations', stop_agent(item))
    remove(item)
    report['phase'] = 'passed'
except Exception as error:
    report.update(phase='failed', failure_class=type(error).__name__, failure=str(error), traceback=traceback.format_exc())
finally:
    for item in containers:
        if not item.get('removed'):
            try:
                if (item['folder'] / 'state/status.json').exists():
                    report.setdefault('failure_status', []).append(status(item))
                remove(item)
            except Exception as error:
                report.setdefault('cleanup_errors', []).append(type(error).__name__ + ': ' + str(error))
    try:
        image = run(['docker', 'image', 'inspect', tag], check=False)
        if image.returncode == 0:
            meta = json.loads(image.stdout)[0]
            if meta['Config']['Labels'].get('crg.native-ci') == nonce:
                result = run(['docker', 'image', 'rm', tag], check=False)
                if result.returncode:
                    report.setdefault('cleanup_errors', []).append('own image removal failed')
                else:
                    absent = run(['docker', 'image', 'ls', '--filter', 'reference=' + tag, '--format', '{{.ID}}'])
                    report['cleanup']['own_image_absent'] = not absent.stdout.strip()
                    if absent.stdout.strip():
                        report.setdefault('cleanup_errors', []).append('own image still present')
            else:
                report.setdefault('cleanup_errors', []).append('image cleanup owner differs')
    except Exception as error:
        report.setdefault('cleanup_errors', []).append(type(error).__name__ + ': ' + str(error))
    report['cleanup']['all_owned_containers_and_cgroups_absent'] = all(x.get('removed') for x in containers)
    if report['cleanup']['all_owned_containers_and_cgroups_absent']:
        try:
            cleanup_storage()
        except Exception as error:
            report.setdefault('cleanup_errors', []).append(type(error).__name__ + ': ' + str(error))
    if not report.get('cleanup_errors') and report['cleanup']['all_owned_containers_and_cgroups_absent']:
        if private.parent != Path(tempfile.gettempdir()).resolve() or not private.name.startswith('crg-native-controller-') or private.is_symlink():
            raise RuntimeError('private temporary cleanup path differs')
        shutil.rmtree(private)
        report['cleanup']['private_directory_removed'] = not private.exists()
    if report.get('cleanup_errors'):
        report['phase'] = 'failed'
    save()
print(json.dumps({'phase': report['phase'], 'checks': len(report['tests']), 'failure': report.get('failure')}))
raise SystemExit(0 if report['phase'] == 'passed' else 1)
