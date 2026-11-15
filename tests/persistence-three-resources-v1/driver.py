#!/usr/bin/env python3
"""Exact final ELF persistence faults on actual own-container cgroups; CI only."""
import argparse,errno,hashlib,json,os,platform,re,selectors,shutil,signal,stat,subprocess,tempfile,time,traceback,uuid
from pathlib import Path
P=argparse.ArgumentParser(description=__doc__)
for name in ['binary','holder','worker','helper','output','plan']:P.add_argument('--'+name,type=Path,required=True)
P.add_argument('--arch',choices=['amd64','arm64'],required=True)
A=P.parse_args()
if (platform.system()!='Linux' or os.geteuid()!=0 or os.environ.get('CRG_PERSIST_TEST')!='ephemeral-github-hosted-vm-only'
 or os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('RUNNER_ENVIRONMENT')!='github-hosted'):
 P.error('explicit disposable GitHub-hosted root VM required')
A.output=A.output.resolve();A.output.mkdir(parents=True,exist_ok=False)
PLAN=json.loads(A.plan.read_bytes());NONCE=uuid.uuid4().hex;TAG='crg-persistence:'+NONCE;LABEL='crg.persistence-ci'
PRIVATE=Path(tempfile.mkdtemp(prefix='crg-three-resource-')).resolve();ITEMS=[];MOUNTS=[]
storage={'stage':'not-created'}
FIELDS=['cpu.max','memory.max','memory.high','io.max','pids.max','cpu.weight','io.weight','memory.swap.max']
sha=lambda raw:hashlib.sha256(raw).hexdigest()
R={'schema':'crg-native-three-resource-persistence-v1','phase':'preparing','scope':PLAN['scope'],'plan_sha256':sha(A.plan.read_bytes()),
   'driver_sha256':sha(Path(__file__).read_bytes()),'source_revision':PLAN['source_revision'],'arch':A.arch,
   'kernel':platform.release(),'tests':[],'cases':[],'cleanup':{}}


def save():
    temporary = A.output / 'report.tmp'
    temporary.write_text(json.dumps(R, indent=2) + '\n')
    temporary.replace(A.output / 'report.json')

def check(name, passed, **data):
    R['tests'].append(dict(name=name, passed=bool(passed), **data))
    save()
    if not passed:
        raise AssertionError(name)

def run(args, timeout=30, required=True):
    result = subprocess.run([str(x) for x in args], capture_output=True,
                            text=True, timeout=timeout)
    if required and result.returncode:
        R['last_command_error'] = {'operation': str(args[:2]), 'exit': result.returncode,
                                   'stderr': result.stderr[-2000:]}
        save()
        raise RuntimeError('fixture command failed')
    return result

def load(path):
    if path.stat().st_size > 1048576:
        raise RuntimeError('JSON exceeds1MiB')
    return json.loads(path.read_bytes())

def proc(pid):
    raw = Path('/proc', str(pid), 'stat').read_text()
    return {'pid': int(pid), 'start_ticks': int(raw[raw.rfind(')') + 2:].split()[19])}

def still(identity):
    try:
        return proc(identity['pid']) == identity
    except (FileNotFoundError, ProcessLookupError):
        return False

def owned(item):
    meta = json.loads(run(['docker', 'inspect', item['id']]).stdout)[0]
    if (meta['Id'] != item['id'] or meta['Config']['Labels'].get(LABEL) != NONCE or
            meta['State']['Pid'] != item['main']['pid'] or not still(item['main']) or
            Path('/proc', str(item['main']['pid']), 'cgroup').read_text() != item['membership'] or
            item['group'].resolve() != item['group'] or
            item['group'].stat().st_ino != item['group_inode']):
        raise RuntimeError('own container/PID1/cgroup identity changed')
    return meta

def controls(item):
    owned(item)
    return {name: (item['group'] / name).read_text().strip() for name in FIELDS}

def events(item):
    owned(item)
    return {k: int(v) for k, v in (line.split() for line in
            (item['group'] / 'memory.events').read_text().splitlines())}

def wait_for(operation, predicate, seconds=20):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = operation()
        if predicate(value):
            return value
        time.sleep(.1)
    raise TimeoutError('bounded fixture observation timed out')

class Worker:
    def __init__(self, item):
        self.item = item
        owned(item)
        self.p = subprocess.Popen(['docker', 'exec', '-i', item['id'], '/worker'],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, bufsize=1)
        self.select = selectors.DefaultSelector()
        self.select.register(self.p.stdout, selectors.EVENT_READ)
        self.first = self.command('status')
        # Worker PID is namespace-local; record host identity by exact argv.
        matches = []
        for pid in (item['group'] / 'cgroup.procs').read_text().split():
            try:
                if Path('/proc', pid, 'cmdline').read_bytes().split(b'\0')[0] == b'/worker':
                    matches.append(proc(pid))
            except (FileNotFoundError, ProcessLookupError):
                pass
        if len(matches) != 1:
            raise RuntimeError('one native worker required')
        self.identity = matches[0]
        item['observed'].append(self.identity)

    def command(self, text):
        owned(self.item)
        self.p.stdin.write(text + '\n')
        self.p.stdin.flush()
        if not self.select.select(15):
            raise TimeoutError('worker acknowledgement missing')
        raw = self.p.stdout.readline()
        value = json.loads(raw)
        if value['fsync_failed'] or value['command'] != text.split()[0]:
            raise RuntimeError('worker failed or acknowledgement differs')
        self.item['record']['worker_acks'].append(value)
        return value


    def close(self):
        if self.p.poll() is None:
            self.command('quit')
            self.p.wait(timeout=10)
        self.select.close()
        if self.p.returncode != 0:
            raise RuntimeError('worker did not exit normally')

def remove(item):
    if item.get('removed'):
        return
    meta = json.loads(run(['docker', 'inspect', item['id']]).stdout)[0]
    if meta['Id'] != item['id'] or meta['Config']['Labels'].get(LABEL) != NONCE:
        raise RuntimeError('cleanup ownership changed')
    if 'main' in item:
        owned(item)
    run(['docker', 'stop', '--time', '10', item['id']], timeout=20)
    run(['docker', 'rm', item['id']])
    wait_for(lambda: item.get('group', Path('/nonexistent')).exists(), lambda v: not v)
    absent = not run(['docker', 'ps', '-aq', '--filter', 'id=' + item['id']]).stdout.strip()
    dead = all(not still(p) for p in item['observed'])
    if not absent or not dead:
        raise RuntimeError('own Docker/cgroup/observed process cleanup incomplete')
    item['removed'] = True
    item.get('record', {})['cleanup'] = {'container_absent': absent, 'cgroup_absent': True,
                                        'observed_identities': item['observed'], 'all_observed_dead': dead}


def configuration(item, cores):
    value = {'resource_mode': 'manual', 'limits': {'cpu_cores': cores, 'memory_high': '128MiB' if cores == .5 else '192MiB',
                      'io_read_bps': '4MiB' if cores == .5 else '6MiB',
                      'io_write_bps': '4MiB' if cores == .5 else '6MiB'}, 'mode': 'enforce',
             'interval_seconds': 1, 'io_calibration': 'off', 'data_paths': ['/data'],
             'state_dir': '/state', 'log_dir': '/logs'}
    path = item['folder'] / 'config/config.json'
    temporary = path.with_suffix('.new')
    temporary.write_text(json.dumps(value))
    temporary.replace(path)


def ex(item, *command, required=True):
    owned(item)
    return run(['docker', 'exec', item['id'], *command], required=required)


def actors(item):
    owned(item)
    found = []
    for pid in (item['group'] / 'cgroup.procs').read_text().split():
        try:
            argv = Path('/proc', pid, 'cmdline').read_bytes().split(b'\0')
            if argv[:2] == [b'/crg', b'run']:
                value = proc(pid)
                if sha(Path('/proc', pid, 'exe').read_bytes()) != R['binary_sha256']:
                    raise RuntimeError('candidate executable identity differs')
                status = dict(line.split(':', 1) for line in Path('/proc', pid, 'status').read_text().splitlines())
                if int(status['CapEff'].strip(), 16) & 6 or int(status['CapBnd'].strip(), 16) & 6:
                    raise RuntimeError('DAC bypass capabilities must be absent after candidate exec')
                if value not in item['observed']:
                    item['observed'].append(value)
                    item['record'].setdefault('candidate_capabilities', []).append({
                        **value, 'effective': status['CapEff'].strip(), 'bounding': status['CapBnd'].strip(),
                        'executable_sha256': R['binary_sha256']})
                found.append(value)
        except (FileNotFoundError, ProcessLookupError):
            pass
    if len(found) > 1:
        raise RuntimeError('one Agent per own container required')
    return found


def mount_row(path):
    rows = [line.split() for line in Path('/proc/self/mountinfo').read_text().splitlines()
            if line.split()[4] == str(path)]
    if len(rows) != 1:
        raise RuntimeError('exact private state mount required')
    row = rows[0]
    separator = row.index('-')
    return {'mount_id': int(row[0]), 'device': row[2], 'target': row[4],
            'filesystem': row[separator + 1], 'source': row[separator + 2], 'options': row[5]}


def verify_storage():
    loop = storage['loop']
    if not re.fullmatch(r'/dev/loop[0-9]+', loop):
        raise RuntimeError('not an owned loop device')
    attached = run(['losetup', '--noheadings', '--raw', '--output', 'BACK-FILE', loop]).stdout.strip()
    if attached != str(PRIVATE / 'block.img') or not stat.S_ISBLK(os.stat(loop).st_mode):
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
    storage.update(stage='creating', name='crg-three-resource-' + NONCE, uuid='CRG-THREE-RESOURCE-' + NONCE)
    image = PRIVATE / 'block.img'
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
    mount = PRIVATE / 'blockfs'
    mount.mkdir(mode=0o700)
    run(['mount', '-t', 'ext4', '-o', 'nodev,nosuid', device, mount])
    if not mount.is_mount() or mount.stat().st_dev != number:
        raise RuntimeError('owned filesystem mount differs')
    mount.chmod(0o700)
    storage.update(stage='mounted', directory=mount, number=number)
    storage['device'] = str(os.major(number)) + ':' + str(os.minor(number))
    R['storage_fixture'] = {'kind': 'ext4 on real dm-linear UUID over exclusive loop file', 'sparse_backing_bytes': 2 * 1024**3, 'physical_independent_device': False, 'device': str(os.major(number)) + ':' + str(os.minor(number))}


def cleanup_storage():
    if storage['stage'] == 'not-created':
        return
    # Partial setup is a retained failure; do not guess owners or detach globals.
    if storage['stage'] != 'mounted':
        raise RuntimeError('partial block fixture setup requires VM disposal; PRIVATE file retained')
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
    if attached != str(PRIVATE / 'block.img'):
        raise RuntimeError('loop ownership changed before detach')
    run(['losetup', '--detach', storage['loop']])
    remaining = run(['losetup', '--associated', PRIVATE / 'block.img', '--noheadings', '--raw', '--output', 'NAME']).stdout.strip()
    if remaining:
        raise RuntimeError('own loop backing file still associated')
    R['cleanup']['own_mount_mapper_and_loop_absent'] = True


def launch(name):
    verify_storage()
    folder = storage['directory'] / name
    folder.mkdir(mode=0o700)
    for n in ['config', 'state', 'data', 'logs']:
        (folder / n).mkdir(parents=True, mode=0o700)
    state = folder / 'state'
    source = 'crg-persist-' + NONCE + '-' + name
    run(['mount', '-t', 'tmpfs', '-o', 'size=4m,nr_inodes=128,mode=0700,nosuid,nodev,noexec', source, state])
    mounted = mount_row(state)
    if mounted['source'] != source or mounted['filesystem'] != 'tmpfs':
        raise RuntimeError('state filesystem ownership differs')
    MOUNTS.append((state, mounted))
    command = ['docker', 'run', '-d', '--name', 'crg-persist-' + NONCE + '-' + name,
               '--label', LABEL + '=' + NONCE, '--network', 'none', '--cgroupns', 'host',
               '--cpus', '2', '--memory', '512m', '--memory-swap', '512m', '--privileged',
               '--env', 'CRG_PERSIST_FIXTURE=ephemeral-github-hosted-vm-only',
               '--mount', 'type=bind,src=/sys/fs/cgroup,dst=/sys/fs/cgroup']
    for n, target in [('config', '/etc/crg'), ('state', '/state'), ('data', '/data'), ('logs', '/logs')]:
        command += ['--mount', 'type=bind,src=' + str(folder / n) + ',dst=' + target]
    cid = run(command + [TAG]).stdout.strip()
    if not re.fullmatch('[0-9a-f]{64}', cid):
        raise RuntimeError('invalid Docker identity')
    item = {'id': cid, 'name': name, 'folder': folder, 'observed': []}
    ITEMS.append(item)
    meta = json.loads(run(['docker', 'inspect', cid]).stdout)[0]
    host, pid = meta['HostConfig'], meta['State']['Pid']
    if (meta['Config']['Labels'].get(LABEL) != NONCE or host['NetworkMode'] != 'none'
            or host['CgroupnsMode'] != 'host' or host.get('PidMode') not in ['', 'private'] or pid <= 1
            or any(Path('/proc', str(pid), 'ns', n).stat().st_ino == Path('/proc/1/ns', n).stat().st_ino
                   for n in ['pid', 'mnt', 'net'])):
        raise RuntimeError('private labelled namespace identity differs')
    membership = Path('/proc', str(pid), 'cgroup').read_text()
    if not re.fullmatch('0::/[^\n]*\n', membership):
        raise RuntimeError('pure v2 required')
    group = Path('/sys/fs/cgroup') / membership.strip().split('::')[1].lstrip('/')
    if group.resolve() != group or group.name not in [cid, 'docker-' + cid + '.scope']:
        raise RuntimeError('not an own Docker leaf')
    item.update(main=proc(pid), membership=membership, group=group, group_inode=group.stat().st_ino)
    item['observed'].append(item['main'])
    # Explicit harness-owned external caps, captured before the Agent exists.
    (group / 'memory.high').write_text(str(384 * 1024**2))
    (group / 'io.max').write_text(storage['device'] + ' rbps=max wbps=max riops=4096 wiops=4096')
    item['original'] = controls(item)
    record = {'name': name, 'container_id': cid, 'main': item['main'], 'cgroup': str(group),
              'original_controls': item['original'], 'state_mount': mounted, 'worker_acks': [],
              'commands': [], 'samples': []}
    item['record'] = record
    R['cases'].append(record)
    item['output'] = A.output / name
    item['output'].mkdir()
    configuration(item, .5)
    item['oom'] = events(item)
    save()
    return item


def journal(item):
    return load(item['folder'] / 'state/journal.json')


def targets(item, updated=False):
    return {'cpu.max': '75000 100000' if updated else '50000 100000',
            'memory.high': str((192 if updated else 128) * 1024**2),
            'io.max': storage['device'] + (' rbps=6291456 wbps=6291456' if updated else ' rbps=4194304 wbps=4194304') + ' riops=4096 wiops=4096'}


def journal_key(field):
    return field + ':' + (storage['device'] if field == 'io.max' else '')


def applied_value(field, value):
    return value.split(' ', 1)[1] if field == 'io.max' else value


def cpu(item, desired):
    # Historical function name; every call now validates all three resources
    # and all five unchanged external controls, never CPU alone.
    return controls(item) == {**item['original'], **targets(item, desired == '75000 100000')}



def start(item, label, once=False):
    owned(item)
    assert not actors(item)
    out = open(item['output'] / (label + '.stdout'), 'w')
    err = open(item['output'] / (label + '.stderr'), 'w')
    command = ['docker', 'exec', item['id'], '/fault-helper', '/crg', 'run', '--config', '/etc/crg/config.json']
    if once:
        command.append('--once')
    child = subprocess.Popen(command, stdout=out, stderr=err)
    item['record']['commands'].append({'label': label, 'once': once})
    return child, out, err


def finish(item, process, label, timeout=30):
    child, out, err = process
    try:
        code = child.wait(timeout=timeout)
    finally:
        out.close(); err.close()
    text = (item['output'] / (label + '.stdout')).read_text() + (item['output'] / (label + '.stderr')).read_text()
    row = next(v for v in item['record']['commands'] if v['label'] == label)
    row.update(exit=code, output_sha256=sha(text.encode()))
    save()
    return code, text


def baseline(item):
    process = start(item, 'baseline')
    actor = wait_for(lambda: actors(item), lambda value: len(value) == 1)[0]
    wait_for(lambda: cpu(item, '50000 100000') and (item['folder'] / 'state/status.json').exists(), bool)
    check(item['name'] + ': exact single capability-bounded candidate managed CPU',
          journal(item)['mutations']['cpu.max:']['applied'] == '50000 100000'
          and journal(item)['mutations']['cpu.max:']['original'] == item['original']['cpu.max'])
    item['record']['initial_journal'] = journal(item)
    entries = journal(item)['mutations']
    assert set(entries) == {journal_key(k) for k in targets(item)}
    assert all(entries[journal_key(k)]['applied'] == applied_value(k, v) and not entries[journal_key(k)].get('pending') for k, v in targets(item).items())
    item['record']['baseline_targets'] = targets(item)
    item['record']['updated_targets'] = targets(item, True)
    return process, actor


def signal_actor(item, actor, sig):
    owned(item)
    if actors(item) != [actor] or not still(actor):
        raise RuntimeError('exact registered candidate changed before signal')
    os.kill(actor['pid'], sig)


def restore(item):
    assert not actors(item)
    result = ex(item, '/fault-helper', '/crg', 'restore', '--config', '/etc/crg/config.json', required=False)
    value = json.loads(result.stdout)
    item['record']['restore'] = {'exit': result.returncode, 'result': value,
                                 'controls': controls(item), 'journal': journal(item)}
    check(item['name'] + ': original eight controls durably restored', result.returncode == 0
          and value['state'] == 'restored' and controls(item) == item['original'] and not journal(item)['mutations'])


def state_fault(item, worker, kind):
    process, actor = baseline(item)
    state = item['folder'] / 'state'
    old = (state / 'journal.json').read_bytes()
    started = time.monotonic()
    if kind == 'full':
        fd = os.open(state / 'fill', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        total = 0
        try:
            while total <= 4 * 1024**2:
                try:
                    total += os.write(fd, b'x' * 65536)
                except OSError as error:
                    if error.errno != errno.ENOSPC:
                        raise
                    item['record']['fill'] = {'bytes': total, 'errno': error.errno,
                                             'free_blocks': os.statvfs(state).f_bavail}
                    break
            else:
                raise RuntimeError('bounded state filesystem did not reach ENOSPC')
        finally:
            os.close(fd)
    elif kind == 'permission':
        state.chmod(0)
    elif kind == 'readonly':
        mountinfo = Path('/proc', str(item['main']['pid']), 'mountinfo')
        before = {line.split()[0] for line in mountinfo.read_text().splitlines()}
        ex(item, '/fault-helper', 'remount-ro')
        mounts = [line.split() for line in mountinfo.read_text().splitlines()
                  if line.split()[4] == '/state' and line.split()[0] not in before]
        item['record']['readonly_overlay'] = {'new_mount_rows': mounts,
            'statvfs_readonly': bool(os.statvfs('/proc/' + str(item['main']['pid']) + '/root/state').f_flag & os.ST_RDONLY)}
        check(item['name'] + ': actual private container state mount read-only', len(mounts) == 1
              and 'ro' in mounts[0][5].split(',') and item['record']['readonly_overlay']['statvfs_readonly'])
    configuration(item, .75)
    code, text = finish(item, process, 'baseline')
    reason = {'full': 'no space left on device', 'permission': 'permission denied', 'readonly': 'read-only file system'}[kind]
    check(item['name'] + ': live Agent fails closed without policy change', code != 0 and reason in text.lower()
          and not still(actor) and not actors(item) and cpu(item, '50000 100000') and (state / 'journal.json').read_bytes() == old)
    for number in range(3):
        deadline = started + (number + 1) * 10.5
        while time.monotonic() < deadline:
            snapshot = {'elapsed_seconds': time.monotonic() - started, 'controls': controls(item),
                        'journal_sha256': sha((state / 'journal.json').read_bytes()), 'main_alive': still(item['main'])}
            item['record']['samples'].append(snapshot)
            if not cpu(item, '50000 100000') or snapshot['journal_sha256'] != sha(old) or not snapshot['main_alive']:
                raise RuntimeError('fault-period original journal/retained controls/PID1 changed')
            time.sleep(.5)
        retry = start(item, 'retry-' + str(number), once=True)
        retry_code, retry_text = finish(item, retry, 'retry-' + str(number))
        check(item['name'] + ': sustained fault retry ' + str(number), retry_code != 0
              and reason in retry_text.lower() and not actors(item) and cpu(item, '50000 100000'))
        worker.command('status')
    item['record']['fault_seconds'] = time.monotonic() - started
    check(item['name'] + ': fault sustained for at least30seconds', item['record']['fault_seconds'] >= 30)
    if kind == 'full':
        (state / 'fill').unlink()
    elif kind == 'permission':
        state.chmod(0o700)
    else:
        ex(item, '/fault-helper', 'remount-rw')
    retry = start(item, 'recovered', once=True)
    code, text = finish(item, retry, 'recovered')
    check(item['name'] + ': removal of real fault permits new policy', code == 0 and cpu(item, '75000 100000')
          and journal(item)['mutations']['cpu.max:']['applied'] == '75000 100000')
    restore(item)


def traced_fault(item, worker, stage, field='io.max'):
    process, actor = baseline(item)
    trace = item['output'] / 'persistence.strace'
    diagnostic = open(item['output'] / 'strace.stderr', 'w')
    tracer = subprocess.Popen(['/usr/bin/strace', '-f', '-ttt', '-T', '-yy', '-e', 'trace=fsync,rename,renameat,write',
                               '-e', 'inject=fsync:delay_exit=3s', '-o', str(trace), '-p', str(actor['pid'])],
                              stdout=subprocess.DEVNULL, stderr=diagnostic)
    key = journal_key(field)
    requested = applied_value(field, targets(item, True)[field])
    desired = {**item['original'], **targets(item)}
    for resource in ['cpu.max', 'memory.high', 'io.max']:
        if resource == field:
            if stage != 'before-control':
                desired[resource] = targets(item, True)[resource]
            break
        desired[resource] = targets(item, True)[resource]
    try:
        def attached():
            if tracer.poll() is not None:
                raise RuntimeError('tracer exited before actual syscall attachment')
            tasks = list(Path('/proc', str(actor['pid']), 'task').iterdir())
            return tasks and all(re.search(r'^TracerPid:\s*' + str(tracer.pid) + r'\s*$',
                    (p / 'status').read_text(), re.M) for p in tasks)
        wait_for(attached, bool)
        configuration(item, .75)
        def barrier():
            return journal(item)['mutations'][key].get('pending') == requested and controls(item) == desired
        if stage == 'complete':
            wait_for(lambda: cpu(item, '75000 100000') and
                     all(not v.get('pending') for v in journal(item)['mutations'].values()), bool, 90)
            signal_actor(item, actor, signal.SIGTERM)
        else:
            wait_for(barrier, bool, 90)
            uncommitted = None
            if stage == 'after-control':
                def finalization_file():
                    for path in (item['folder'] / 'state').glob('.crg-*'):
                        try:
                            raw = path.read_bytes()
                            value = json.loads(raw)['mutations'][key]
                            if value['applied'] == requested and not value.get('pending'):
                                return {'name': path.name, 'bytes': len(raw), 'sha256': sha(raw)}
                        except (FileNotFoundError, ValueError, KeyError):
                            pass
                    return None
                uncommitted = wait_for(finalization_file, bool, 10)
            before = time.monotonic_ns()
            time.sleep(.25)
            check(item['name'] + ': durable pending journal and actual kernel boundary', barrier())
            snapshot = {'before_monotonic_ns': before, 'signal_monotonic_ns': time.monotonic_ns(),
                        'journal': journal(item), 'controls': controls(item), 'actor': actor,
                        'resource': field, 'mutation_key': key, 'requested_value': requested,
                        'uncommitted_finalization': uncommitted}
            item['record']['kill_boundary'] = snapshot
            signal_actor(item, actor, signal.SIGKILL)
        code, text = finish(item, process, 'baseline', timeout=30)
        wait_for(lambda: actors(item), lambda v: not v)
        tracer.wait(timeout=15)
    finally:
        if tracer.poll() is None:
            tracer.terminate(); tracer.wait(timeout=10)
        diagnostic.close()
    content = trace.read_text()
    item['record']['trace_sha256'] = sha(trace.read_bytes())
    delayed = [line for line in content.splitlines() if 'fsync(' in line and 'DELAYED' in line and '/state' in line]
    check(item['name'] + ': actual delayed state fsync trace retained', bool(delayed))
    if stage == 'complete':
        check(item['name'] + ': delayed persistence completes without lost ownership', code == 0
              and cpu(item, '75000 100000') and all(not v.get('pending') for v in journal(item)['mutations'].values()))
    else:
        check(item['name'] + ': exact Agent killed at required durable/kernel state', code != 0
              and not still(actor) and controls(item) == desired and 'killed by SIGKILL' in content
              and journal(item)['mutations'][key].get('pending') == requested)
    restore(item)


def case(name, operation):
    item = launch(name)
    worker = Worker(item)
    try:
        operation(item, worker)
        value = worker.command('status')
        after = events(item)
        check(name + ': placeholder and bounded fsync task survive', still(item['main'])
              and value['fsync_count'] > worker.first['fsync_count'] and not value['fsync_failed'])
        check(name + ': observed OOM counters unchanged', all(after[k] == item['oom'][k]
              for k in ['oom', 'oom_kill', 'oom_group_kill'] if k in after), before=item['oom'], after=after)
        worker.close()
    finally:
        state = item['folder'] / 'state'
        state.chmod(0o700)
        remove(item)
        item['record']['archived_state_files'] = []
        for p in state.iterdir():
            if p.is_file() and not p.is_symlink() and p.name != 'fill' and p.stat().st_size <= 1048576:
                raw = p.read_bytes()
                (item['output'] / p.name).write_bytes(raw)
                item['record']['archived_state_files'].append({'name': p.name, 'bytes': len(raw),
                                                                'sha256': sha(raw)})
        mounted = next(row for path, row in MOUNTS if path == state)
        assert mount_row(state) == mounted
        run(['umount', state])
        assert not os.path.ismount(state)
        MOUNTS.remove((state, mounted))
        check(name + ': exact private state mount removed', not os.path.ismount(state))
        save()


try:
    R['binary_sha256'] = sha(A.binary.read_bytes())
    check('exact final ELF', R['binary_sha256'] == PLAN['binary_sha256'][A.arch])
    check('native architecture', platform.machine() in {'amd64': ['x86_64'], 'arm64': ['aarch64', 'arm64']}[A.arch])
    check('local exclusive Docker VM', not run(['docker', 'ps', '-q']).stdout.strip()
          and json.loads(run(['docker', 'context', 'inspect']).stdout)[0]['Endpoints']['docker']['Host'] == 'unix:///var/run/docker.sock')
    image = PRIVATE / 'image'; image.mkdir()
    for source, name in [(A.binary, 'crg'), (A.holder, 'hold'), (A.worker, 'worker'), (A.helper, 'fault-helper')]:
        shutil.copyfile(source, image / name); (image / name).chmod(0o755)
    (image / 'Dockerfile').write_text('FROM scratch\nCOPY crg hold worker fault-helper /\nENTRYPOINT ["/hold"]\n')
    run(['docker', 'build', '--label', LABEL + '=' + NONCE, '-t', TAG, image], timeout=90)
    prepare_storage()
    for kind in ['full', 'permission', 'readonly']:
        case(kind + '-state', lambda item, worker, kind=kind: state_fault(item, worker, kind))
    for field in ['cpu.max', 'memory.high', 'io.max']:
        for stage in ['before-control', 'after-control']:
            case('delayed-' + field + '-' + stage, lambda item, worker, stage=stage, field=field: traced_fault(item, worker, stage, field))
    case('delayed-complete', lambda item, worker: traced_fault(item, worker, 'complete'))
    R['phase'] = 'passed'
except BaseException as error:
    R['phase'] = 'failed'; R['error'] = str(error); R['traceback'] = traceback.format_exc()
finally:
    errors = []
    for item in ITEMS:
        try:
            remove(item)
        except BaseException as error:
            errors.append(str(error))
    for path, mounted in list(MOUNTS):
        try:
            if mount_row(path) != mounted:
                raise RuntimeError('state mount identity changed; retained')
            run(['umount', path]); MOUNTS.remove((path, mounted))
        except BaseException as error:
            errors.append(str(error))
    image = run(['docker', 'image', 'inspect', TAG], required=False)
    if image.returncode == 0:
        value = json.loads(image.stdout)[0]
        if value['Config'].get('Labels', {}).get(LABEL) == NONCE:
            result = run(['docker', 'image', 'rm', TAG], required=False)
            if result.returncode:
                errors.append('owned image removal failed')
        else:
            errors.append('image ownership differs; retained')
    R['cleanup'] = {'errors': errors, 'owned_state_mounts_remaining': len(MOUNTS),
                    'private_fixture_files_retained_until_VM_disposal': True}
    try:
        cleanup_storage()
    except BaseException as error:
        errors.append(str(error))
    if errors:
        R['phase'] = 'failed'
    save()
print(json.dumps({'phase': R['phase'], 'checks': len(R['tests']), 'passed': sum(v['passed'] for v in R['tests']),
                  'cases': len(R['cases']), 'error': R.get('error')}))
raise SystemExit(0 if R['phase'] == 'passed' else 1)
