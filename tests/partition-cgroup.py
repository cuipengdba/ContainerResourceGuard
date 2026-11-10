#!/usr/bin/env python3
"""Real GPT sibling-partition checks in owned scratch containers on ephemeral CI VMs.

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
for name in ['binary', 'old-binary', 'holder', 'load', 'shared-load', 'output']:
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
          'scope': 'real GPT sibling partitions, native scratch PID1 and own cgroup; not vendor business or independent physical disks',
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


def run(command, timeout=30, check=True, input=None):
    result = subprocess.run([str(x) for x in command], capture_output=True, text=True, timeout=timeout, input=input)
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


def stop_agent(item, binary='/crg'):
    result = json.loads(ex(item, binary, 'disable', '--config', '/etc/crg/config.json', timeout=30).stdout)
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


def debug_hosts():
    if not Path('/sys/class/scsi_host').exists():
        return set()
    return {x.joinpath('device').resolve(strict=True) for x in Path('/sys/class/scsi_host').iterdir()
            if x.joinpath('proc_name').read_text().strip() == 'scsi_debug'}


def verify_storage():
    if not storage.get('module_owned') or debug_hosts() != {storage['host']}:
        raise RuntimeError('exclusive owned scsi_debug host differs')
    params = Path('/sys/module/scsi_debug/parameters')
    for name, expected in [('dev_size_mb', '2560'), ('num_tgts', '1'), ('max_luns', '1'), ('vpd_use_hostno', '1')]:
        if params.joinpath(name).read_text().strip() != expected:
            raise RuntimeError('owned SCSI test parameters changed')
    device = storage['node']
    value = device.lstat()
    root = Path('/sys/dev/block', devstr(value.st_rdev)).resolve(strict=True)
    real = root.joinpath('device').resolve(strict=True)
    if (not stat.S_ISBLK(value.st_mode) or value.st_rdev != storage['number'] or root != storage['root'] or
            storage['host'] not in real.parents or root.joinpath('partition').exists() or
            root.joinpath('dev').read_text().strip() != devstr(value.st_rdev) or
            int(root.joinpath('size').read_text()) != 2560 * 1024**2 // 512 or
            root.joinpath(storage['identity_file']).read_text().strip() != storage['wwid']):
        raise RuntimeError('owned SCSI disk tree, geometry or stable WWID changed')
    disks = {x.resolve() for x in Path('/sys/class/block').iterdir()
             if x.joinpath('device').exists() and storage['host'] in x.joinpath('device').resolve().parents}
    if disks != {root}:
        raise RuntimeError('exclusive SCSI test host has unexpected disks')
    return device, value.st_rdev


def devstr(number):
    return str(os.major(number)) + ':' + str(os.minor(number))


def partition_roots():
    _, number = verify_storage()
    parent = Path('/sys/dev/block', devstr(number)).resolve(strict=True)
    return sorted(x for x in parent.iterdir() if x.joinpath('partition').is_file())


def verify_partition(part):
    _, parent_number = verify_storage()
    parent = Path('/sys/dev/block', devstr(parent_number)).resolve(strict=True)
    root = Path('/sys/dev/block', devstr(part['number'])).resolve(strict=True)
    value = part['node'].lstat()
    if (root.parent != parent or root != part['root'] or
            int(root.joinpath('partition').read_text()) != part['index'] or
            root.joinpath('dev').read_text().strip() != devstr(part['number']) or
            int(root.joinpath('start').read_text()) != part['start'] or
            int(root.joinpath('size').read_text()) != part['sectors'] or
            not stat.S_ISBLK(value.st_mode) or value.st_rdev != part['number']):
        raise RuntimeError('owned actual GPT partition identity/geometry differs')


def write_gpt(first_sectors):
    device, _ = verify_storage()
    if partition_roots() or any(x.is_mount() for x in private.glob('blockfs*')):
        raise RuntimeError('all own partitions must be offline before GPT write')
    table = ('label: gpt\nlabel-id: ' + str(uuid.UUID(nonce)) + '\nunit: sectors\n\n' +
             'start=2048, size=' + str(first_sectors) + ', type=linux\n' +
             'start=2623488, size=1572864, type=linux\n')
    run(['sfdisk', '--lock=yes', '--wipe', 'never', '--wipe-partitions', 'never',
         '--no-reread', '--no-tell-kernel', device], input=table)
    actual = json.loads(run(['sfdisk', '--json', device]).stdout)['partitiontable']
    if (actual['label'] != 'gpt' or actual['id'].lower() != str(uuid.UUID(nonce)) or
            actual['unit'] != 'sectors' or actual.get('sectorsize', 512) != 512 or
            [(x['start'], x['size']) for x in actual['partitions']] != [(2048, first_sectors), (2623488, 1572864)]):
        raise RuntimeError('new owned GPT table differs')
    run(['partx', '--add', device])
    deadline = time.monotonic() + 10
    while len(partition_roots()) != 2 and time.monotonic() < deadline:
        time.sleep(.1)
    roots = partition_roots()
    if len(roots) != 2:
        raise RuntimeError('kernel did not expose exactly two real partitions')
    parts = []
    for root in roots:
        index = int(root.joinpath('partition').read_text())
        if index not in [1, 2]:
            raise RuntimeError('unexpected own partition index')
        major, minor = map(int, root.joinpath('dev').read_text().split(':'))
        number = os.makedev(major, minor)
        node = private / ('partition-' + str(index))
        if node.exists():
            raise RuntimeError('private partition node already exists')
        os.mknod(node, stat.S_IFBLK | 0o600, number)
        part = dict(index=index, number=number, root=root, node=node,
                    mount=private / ('blockfs' + str(index)), start=2048 if index == 1 else 2623488,
                    sectors=first_sectors if index == 1 else 1572864)
        verify_partition(part)
        parts.append(part)
    storage['partitions'] = sorted(parts, key=lambda x: x['index'])


def mount_partitions(format_new=False):
    for part in storage['partitions']:
        verify_partition(part)
        if format_new:
            run(['mkfs.ext4', '-q', '-m', '0', '-E', 'lazy_itable_init=0,lazy_journal_init=0', part['node']], timeout=90)
        part['mount'].mkdir(mode=0o700, exist_ok=not format_new)
        run(['mount', '-t', 'ext4', '-o', 'nodev,nosuid', part['node'], part['mount']])
        if not part['mount'].is_mount() or part['mount'].stat().st_dev != part['number']:
            raise RuntimeError('own partition filesystem mount differs')
        part['mount'].chmod(0o700)
    storage.update(stage='mounted', directory=storage['partitions'][0]['mount'], sibling_directory=storage['partitions'][1]['mount'])


def unmount_partitions():
    if storage['stage'] != 'mounted' or any(not x.get('removed') for x in containers):
        raise RuntimeError('partition unmount requires all owned containers absent')
    for part in storage['partitions']:
        verify_partition(part)
        if not part['mount'].is_mount() or part['mount'].stat().st_dev != part['number']:
            raise RuntimeError('cleanup partition mount owner differs')
    for part in storage['partitions']:
        run(['umount', part['mount']])
        if part['mount'].is_mount() or part['mount'].stat().st_dev == part['number']:
            raise RuntimeError('own partition mount remains active')
    device, _ = verify_storage()
    for part in storage['partitions']:
        verify_partition(part)
    run(['partx', '--delete', '--nr', '1:2', device])
    deadline = time.monotonic() + 10
    while partition_roots() and time.monotonic() < deadline:
        time.sleep(.1)
    if partition_roots():
        raise RuntimeError('own kernel partitions remain active')
    for part in storage['partitions']:
        value = part['node'].lstat()
        if not stat.S_ISBLK(value.st_mode) or value.st_rdev != part['number']:
            raise RuntimeError('private stale partition node changed')
        part['node'].unlink()
    storage['stage'] = 'offline'


def prepare_storage():
    for command in ['sfdisk', 'partx', 'modinfo', 'modprobe', 'mkfs.ext4', 'mount', 'umount', 'blockdev']:
        if not shutil.which(command):
            raise RuntimeError('required fixture utility absent: ' + command)
    # Refuse to reuse/unload a module or SCSI debug host owned by anyone else.
    if Path('/sys/module/scsi_debug').exists() or debug_hosts():
        raise RuntimeError('scsi_debug already in use; no fixture writes permitted')
    module = run(['modinfo', '-F', 'filename', 'scsi_debug']).stdout.strip()
    vermagic = run(['modinfo', '-F', 'vermagic', 'scsi_debug']).stdout.strip()
    if not Path(module).is_file() or not vermagic.startswith(platform.release() + ' '):
        raise RuntimeError('actual-kernel scsi_debug module unavailable')
    before_blocks = {x.resolve() for x in Path('/sys/class/block').iterdir()}
    if Path('/sys/module/scsi_debug').exists() or debug_hosts():
        raise RuntimeError('SCSI test ownership changed before module load')
    storage.update(stage='creating', module_file=module, module_vermagic=vermagic)
    run(['modprobe', 'scsi_debug', 'dev_size_mb=2560', 'num_tgts=1', 'max_luns=1',
         'add_host=1', 'vpd_use_hostno=1', 'sector_size=512'], timeout=60)
    storage['module_owned'] = True
    deadline = time.monotonic() + 10
    while len(debug_hosts()) != 1 and time.monotonic() < deadline:
        time.sleep(.1)
    hosts = debug_hosts()
    if len(hosts) != 1:
        raise RuntimeError('exactly one new SCSI debug host required')
    host = next(iter(hosts))
    disks = [x.resolve() for x in Path('/sys/class/block').iterdir()
             if x.joinpath('device').exists() and host in x.joinpath('device').resolve().parents]
    if len(disks) != 1 or disks[0] in before_blocks:
        raise RuntimeError('exactly one new owned SCSI test disk required')
    root = disks[0]
    major, minor = map(int, root.joinpath('dev').read_text().split(':'))
    number = os.makedev(major, minor)
    identity_file = next((x for x in ['device/wwid', 'wwid'] if root.joinpath(x).is_file() and root.joinpath(x).read_text().strip()), None)
    if identity_file is None:
        raise RuntimeError('new SCSI test disk lacks actual stable WWID')
    node = private / 'disk'
    os.mknod(node, stat.S_IFBLK | 0o600, number)
    storage.update(host=host, root=root, number=number, node=node, identity_file=identity_file, wwid=root.joinpath(identity_file).read_text().strip())
    device, number = verify_storage()
    if run(['blockdev', '--getss', device]).stdout.strip() != '512':
        raise RuntimeError('fixture requires actual512-byte logical sectors')
    write_gpt(2097152)
    mount_partitions(format_new=True)
    report['storage_fixture'] = {'kind': 'two real GPT ext4 partitions on exclusive kernel scsi_debug RAM-backed SCSI disk with actual WWID',
                                'logical_and_backing_bytes': 2560 * 1024**2, 'physical_independent_device': False,
                                'module_vermagic': vermagic, 'control_device': devstr(number),
                                'partitions': [{'filesystem_device': devstr(x['number']), 'partition': x['index'], 'start': x['start'], 'sectors': x['sectors']} for x in storage['partitions']]}


def cleanup_storage():
    if storage['stage'] == 'not-created':
        return
    if storage['stage'] != 'mounted':
        raise RuntimeError('partial block fixture retained for VM disposal; no guessed cleanup')
    unmount_partitions()
    verify_storage()
    root, host = storage['root'], storage['host']
    run(['modprobe', '--remove', 'scsi_debug'], timeout=30)
    deadline = time.monotonic() + 10
    while (root.exists() or host.exists() or Path('/sys/module/scsi_debug').exists()) and time.monotonic() < deadline:
        time.sleep(.1)
    if root.exists() or host.exists() or Path('/sys/module/scsi_debug').exists() or debug_hosts():
        raise RuntimeError('owned SCSI disk, host or module cleanup incomplete')
    value = storage['node'].lstat()
    if not stat.S_ISBLK(value.st_mode) or value.st_rdev != storage['number']:
        raise RuntimeError('private stale SCSI device node changed')
    storage['node'].unlink()
    report['cleanup']['own_partitions_mounts_SCSI_disk_host_and_module_absent'] = True


def make_folder(name, config):
    folder = storage['directory'] / name
    folder.mkdir(mode=0o700)
    (storage['sibling_directory'] / name).mkdir(mode=0o700)
    for sub in ['config', 'state', 'data']:
        (folder / sub).mkdir(mode=0o700)
    config = {**config, 'data_paths': ['/data', '/sibling'], 'state_dir': '/state', 'log_dir': '/state/logs', 'interval_seconds': 1}
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
    command += ['--mount', 'type=bind,src=' + str(storage['sibling_directory'] / folder.name) + ',dst=/sibling']
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
    for path, name in [(args.binary, 'crg'), (args.old_binary, 'oldcrg'), (args.holder, 'hold'), (args.load, 'load'), (args.shared_load, 'shared-load')]:
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
    old_info = json.loads(run([args.old_binary.resolve(), 'build-info']).stdout)
    record('original-released-preview-for-independent-restore', old_info['revision'] == '7638ee9f871287d1056e267034e0c4e46903b66e' and old_info['version'] == 'v0.1.0-rc.3-preview.1' and report['programs']['oldcrg'] == {'amd64': 'f07973272313db26d359797dda4665145f7dd6490bac2a55f9084bd367faf361', 'arm64': 'c20a9ea5b070ea1039f1dcdc8cbba867eda58eb016c1c4cd8aceec28a8151463'}[args.expected_arch])
    endpoint = json.loads(run(['docker', 'context', 'inspect', '--format', '{{json .Endpoints.docker.Host}}']).stdout)
    record('local-Docker-only', endpoint in ['unix:///var/run/docker.sock', 'unix:///run/docker.sock'])
    report['docker'] = json.loads(run(['docker', 'version', '--format', '{{json .Server}}']).stdout)
    (private / 'Dockerfile').write_text('FROM scratch\nCOPY crg /crg\nCOPY hold /hold\nCOPY load /load\nCOPY oldcrg /oldcrg\nCOPY shared-load /shared-load\nENTRYPOINT ["/hold"]\n')
    run(['docker', 'build', '--network', 'none', '--label', 'crg.native-ci=' + nonce, '-t', tag, str(private)], timeout=120)
    image = json.loads(run(['docker', 'image', 'inspect', tag]).stdout)[0]
    record('scratch-image-native-and-owned', image['Architecture'] == args.expected_arch and image['Config']['Labels']['crg.native-ci'] == nonce)
    prepare_storage()
    manual = make_folder('manual', {'resource_mode': 'manual', 'limits': {'cpu_cores': .5, 'memory_max': '128MiB', 'io_read_bps': '4MiB', 'io_write_bps': '4MiB', 'io_read_iops': 256, 'io_write_iops': 256}})
    item = launch(manual, 'manual')
    dev = manual.joinpath('data').stat().st_dev
    device = str(os.major(dev)) + ':' + str(os.minor(dev))
    filesystem_device = device
    device = devstr(storage['number'])
    report['data_device'] = filesystem_device
    record('actual-two-partition-filesystems-share-one-parent', filesystem_device != device and len(storage['partitions']) == 2 and len({x['number'] for x in storage['partitions']}) == 2)
    item['docker_original'] = controls(item)
    alive(item)
    (item['group'] / 'io.max').write_text(device + ' rbps=33554432 wbps=33554432 riops=2048 wiops=2048')
    item['original'] = controls(item)
    record('finite-external-own-leaf-baseline-established', item['original']['io.max'] == device + ' rbps=33554432 wbps=33554432 riops=2048 wiops=2048')
    root = Path('/sys/dev/block', filesystem_device)
    report['device_inventory'] = {'exposed': root.exists(), 'is_partition': root.joinpath('partition').exists(), 'direct_identity_files': {p: root.joinpath(p).is_file() for p in ['dm/uuid', 'device/wwid', 'wwid']}}
    expected = {**item['original'], 'cpu.max': '50000 100000', 'memory.max': str(128 * 1024**2), 'io.max': device + ' rbps=4194304 wbps=4194304 riops=256 wiops=256'}
    s, agent = start_agent(item)
    record('manual-exact-three-actual-controls', exact(item, s, expected), actual_controls=controls(item))
    plan = json.loads(ex(item, '/crg', 'doctor', '--config', '/etc/crg/config.json').stdout)
    report['manual_doctor'] = plan
    journal = read(manual / 'state/journal.json')
    io_entries = [x for x in journal['mutations'].values() if x['file'] == 'io.max']
    record('manual-journal-uses-one-whole-device-key', len(io_entries) == 1 and io_entries[0]['device'] == device and len(io_entries[0]['device_identity']) == 64)
    coverage = s['plan']['data_paths']
    record('two-real-filesystem-paths-covered-by-one-control-target', len(coverage) == 2 and {x['path'] for x in coverage} == {'/data', '/sibling'} and len({x['device'] for x in coverage}) == 2 and all(x['state'] == 'planned' and x['control_device'] == device and x['device'] != device for x in coverage), coverage=coverage)
    logs(item)
    before = dict(x.split() for x in (item['group'] / 'cpu.stat').read_text().splitlines())
    started = time.monotonic()
    cpu = json.loads(ex(item, '/load', '--mode', 'cpu', '--seconds', '8', '--workers', '4', timeout=20).stdout)
    elapsed = time.monotonic() - started
    after = dict(x.split() for x in (item['group'] / 'cpu.stat').read_text().splitlines())
    used = (int(after['usage_usec']) - int(before['usage_usec'])) / 1e6
    report['measurements']['CPU'] = {'actual_wall_seconds': elapsed, 'used_CPU_seconds': used, 'average_cores': used / elapsed, 'nr_throttled_delta': int(after['nr_throttled']) - int(before['nr_throttled']), 'load': cpu}
    record('CPU-actual-throttling', .2 <= used / elapsed <= .65 and int(after['nr_throttled']) > int(before['nr_throttled']))
    for directory in ['/data', '/sibling']:
        for mode in ['read', 'write', 'randwrite']:
            value = json.loads(ex(item, '/load', '--mode', mode, '--seconds', '6', '--directory', directory, timeout=45).stdout)
            report['measurements'][directory + '/' + mode] = value
            record(directory + '-' + mode + '-actual-direct-IO-cap', value['seconds'] >= 6 and value['count'] > 0 and 0 < value['rate'] <= 4 * 1024**2 * 1.35 and (mode != 'randwrite' or 0 < value['iops'] <= 256 * 1.35))
    for mode in ['write', 'randwrite']:
        value = json.loads(ex(item, '/shared-load', '--mode', mode, '--seconds', '6', '--first', '/data', '--second', '/sibling', timeout=90).stdout)
        report['measurements']['simultaneous-' + mode] = value
        record('sibling-partitions-share-one-' + mode + '-budget', value['seconds'] >= 6 and all(x > 0 for x in value['counts']) and len(set(value['filesystem_devices'])) == 2 and value['population_seconds_excluded'] > 0 and 0 < value['rate'] <= 4 * 1024**2 * 1.35 and (mode != 'randwrite' or 0 < value['iops'] <= 256 * 1.35))
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
    record('old-released-disable-restores-eight-finite-originals', stop_agent(item, '/oldcrg'))
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
    expected = {**item['original'], 'cpu.max': str(int(hostcpus * 10 / 100 * 100000)) + ' 100000', 'memory.max': str(int(hostmem * 1 / 100) // page * page), 'io.max': device + ' ' + ' '.join(k + '=' + str(v) for k, v in zip(['rbps', 'wbps', 'riops', 'wiops'], rates))}
    report['measurements']['percent'] = {'host_online_CPUs': hostcpus, 'host_memory_bytes': hostmem, 'requested_percentages': {'cpu': 10, 'memory': 1, 'IO': 20}, 'expected_controls': expected, 'automatic_IO_state': s.get('automatic_io', {}).get('state'), 'profile_sha256': hashlib.sha256(profile_bytes).hexdigest()}
    record('independent-percentages-and-real-automatic-profile', s.get('automatic_io', {}).get('state') == 'calibrated' and exact(item, s, expected) and all(v > 0 for v in rates))
    record('automatic-profile-binds-filesystem-to-whole-parent', d['device'] == filesystem_device and s['automatic_io']['selection']['control_device'] == device and s['automatic_io']['selection']['device'] == filesystem_device)
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
    # Independently calibrate the second actual filesystem only after restore.
    ex(item, '/crg', 'calibrate', '--directory', '/sibling', '--seconds', '1', '--samples', '1', '--output', '/etc/crg/sibling-profile.json', timeout=60)
    ex(item, '/crg', 'profile-merge', '--io-profile', '/etc/crg/io-profile.json', '--merge-profile', '/etc/crg/sibling-profile.json', '--output', '/etc/crg/both-profile.json')
    both = read(percent / 'config/both-profile.json')
    if len(both['devices']) != 2 or len({x['identity'] for x in both['devices']}) != 2:
        raise RuntimeError('two independently measured filesystem profiles required')
    cfg = read(percent / 'config/config.json')
    cfg['io_profile'] = '/etc/crg/both-profile.json'
    (percent / 'config/config.json').write_text(json.dumps(cfg))
    rates = [math.floor(min(x[k] for x in both['devices']) * 20 / 100) for k in ['read_bps', 'write_bps', 'read_iops', 'write_iops']]
    expected['io.max'] = device + ' ' + ' '.join(k + '=' + str(v) for k, v in zip(['rbps', 'wbps', 'riops', 'wiops'], rates))
    ex(item, '/crg', 'enable', '--config', '/etc/crg/config.json')
    s, agent = start_agent(item)
    journal = read(percent / 'state/journal.json')
    ios = [x for x in journal['mutations'].values() if x['file'] == 'io.max']
    record('two-real-profiles-form-one-minimum-percentage-cap', exact(item, s, expected) and len(ios) == 1 and s['automatic_io']['state'] == 'reused', rates=rates, profiles=both)
    parent_identity = ios[0]['device_identity']
    record('merged-profile-originals-restored', stop_agent(item))
    # Deliberately untrusted overlapping profile, not a claimed disk calibration.
    bad = json.loads(json.dumps(both))
    whole = {k: v for k, v in both['devices'][0].items() if k != 'measurements'}
    whole.update(device=device, identity=parent_identity)
    bad['devices'].append(whole)
    (percent / 'config/overlap-profile.json').write_text(json.dumps(bad))
    cfg['io_profile'] = '/etc/crg/overlap-profile.json'
    (percent / 'config/config.json').write_text(json.dumps(cfg))
    ex(item, '/crg', 'enable', '--config', '/etc/crg/config.json')
    s, agent = start_agent(item)
    actual = controls(item)
    record('mixed-whole-and-partition-baselines-refuse-IO-writes', s['state'] == 'degraded' and {x['file'] for x in s['items']} == {'cpu.max', 'memory.max'} and all(x['state'] == 'applied' for x in s['items']) and actual['io.max'] == item['original']['io.max'] and actual['cpu.max'] == expected['cpu.max'] and actual['memory.max'] == expected['memory.max'], status=s)
    record('overlap-profile-safe-restore', stop_agent(item))
    cfg['io_profile'] = '/etc/crg/both-profile.json'
    (percent / 'config/config.json').write_text(json.dumps(cfg))
    before_geometry_bytes = (percent / 'config/both-profile.json').read_bytes()
    before_geometry_stamp = (percent / 'config/both-profile.json').stat().st_mtime_ns
    remove(item)
    unmount_partitions()
    write_gpt(2099200)  # Exactly+1MiB; existing filesystem/data untouched.
    mount_partitions()
    record('offline-owned-partition-growth-preserves-cache-and-data', (percent / 'config/both-profile.json').read_bytes() == before_geometry_bytes and (percent / 'config/both-profile.json').stat().st_mtime_ns == before_geometry_stamp and (percent / 'data/sentinel').read_text() == 'preserve\n')
    item = launch(percent, 'geometry')
    s, agent = start_agent(item, 210)
    changed = read(percent / 'config/both-profile.json')
    old_ids = {x['identity'] for x in both['devices']}
    new = [x for x in changed['devices'] if x['identity'] not in old_ids]
    if len(new) != 1:
        raise RuntimeError('one new actual geometry identity required')
    unchanged = read(percent / 'config/sibling-profile.json')['devices'][0]
    rates = [math.floor(min(new[0][k], unchanged[k]) * 20 / 100) for k in ['read_bps', 'write_bps', 'read_iops', 'write_iops']]
    expected = {**item['original'], 'cpu.max': expected['cpu.max'], 'memory.max': expected['memory.max'], 'io.max': device + ' ' + ' '.join(k + '=' + str(v) for k, v in zip(['rbps', 'wbps', 'riops', 'wiops'], rates))}
    journal = read(percent / 'state/journal.json')
    ios = [x for x in journal['mutations'].values() if x['file'] == 'io.max']
    record('changed-geometry-recalibrates-with-stale-profile-visible', s['automatic_io']['state'] == 'calibrated' and len(changed['devices']) == 3 and s['state'] == 'degraded' and len(s['items']) == 3 and all(x['state'] == 'applied' for x in s['items']) and controls(item) == expected and len(ios) == 1 and ios[0]['device_identity'] == parent_identity, status=s, profiles=changed)
    check = json.loads(ex(item, '/crg', 'profile-check', '--io-profile', '/etc/crg/both-profile.json').stdout)
    record('old-partition-profile-reported-unavailable', sum(x['state'] == 'unavailable' for x in check['devices']) == 1 and sum(x['state'] == 'resolved' for x in check['devices']) == 2, inspection=check)
    record('geometry-originals-data-logs-and-no-OOM', stop_agent(item) and bool(logs(item)) and (percent / 'data/sentinel').read_text() == 'preserve\n' and int(dict(x.split() for x in (item['group'] / 'memory.events').read_text().splitlines())['oom_kill']) == item['oom'])
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
print(json.dumps({'phase': report['phase'], 'checks': len(report['tests']), 'failure': report.get('failure'), 'last_failed_command': report.get('last_failed_command'), 'cleanup_errors': report.get('cleanup_errors')}))
raise SystemExit(0 if report['phase'] == 'passed' else 1)
