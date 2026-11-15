#!/usr/bin/env python3
"""Synthetic legacy journal, exact final ELF, actual own-container kernel controls.

Only disposable GitHub-hosted Linux VMs. Never run against vendor containers.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import selectors
import shutil
import subprocess
import tempfile
import time
import traceback
import uuid

P = argparse.ArgumentParser(description=__doc__)
for name in ['binary', 'holder', 'worker', 'output', 'plan']:
    P.add_argument('--' + name, type=Path, required=True)
P.add_argument('--arch', choices=['amd64', 'arm64'], required=True)
A = P.parse_args()
if (platform.system() != 'Linux' or os.geteuid() != 0 or
        os.environ.get('CRG_RESTORE_TEST') != 'ephemeral-github-hosted-vm-only' or
        os.environ.get('GITHUB_ACTIONS') != 'true' or
        os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted'):
    P.error('explicit disposable GitHub-hosted root VM required')
if platform.machine() not in {'amd64': ['x86_64'], 'arm64': ['aarch64', 'arm64']}[A.arch]:
    P.error('native architecture mismatch')
A.output = A.output.resolve()
A.output.mkdir(parents=True, exist_ok=False)
PLAN = json.loads(A.plan.read_bytes())
LOW, HIGH, EXTERNAL = 128 << 20, 512 << 20, 384 << 20
FIELDS = ['cpu.max', 'memory.max', 'memory.high', 'io.max', 'pids.max',
          'cpu.weight', 'io.weight', 'memory.swap.max']
NONCE = uuid.uuid4().hex
TAG = 'crg-restore:' + NONCE
LABEL = 'crg.restore-ci'
PRIVATE = Path(tempfile.mkdtemp(prefix='crg-restore-')).resolve()
ITEMS = []
R = {'schema': 'crg-synthetic-legacy-restore-pressure-v1', 'phase': 'preparing',
     'scope': PLAN['scope'], 'plan_sha256': hashlib.sha256(A.plan.read_bytes()).hexdigest(),
     'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
     'source_revision': PLAN['source_revision'], 'arch': A.arch,
     'kernel': platform.release(), 'tests': [], 'cases': [], 'cleanup': {}}


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


def current(item):
    owned(item)
    return int((item['group'] / 'memory.current').read_text())


def write_max(item, value):
    # Harness emulates the legacy owner or an explicit concurrent external writer.
    # Candidate enforcement never uses memory.max for the new policy.
    owned(item)
    used = current(item)
    if value < used + (32 << 20):
        raise RuntimeError('harness refuses unsafe hard-limit write')
    (item['group'] / 'memory.max').write_text(str(value))
    if controls(item)['memory.max'] != str(value):
        raise RuntimeError('harness memory.max readback differs')
    item['record']['harness_writes'].append({'value': value, 'usage_before': used,
                                            'monotonic_ns': time.monotonic_ns()})


def ex(item, *command, **kw):
    owned(item)
    return run(['docker', 'exec', item['id'], *command], **kw)


def agents(item):
    owned(item)
    result = []
    for pid in (item['group'] / 'cgroup.procs').read_text().split():
        try:
            argv = Path('/proc', pid, 'cmdline').read_bytes().split(b'\0')
            if len(argv) > 1 and argv[:2] == [b'/crg', b'run']:
                if hashlib.sha256(Path('/proc', pid, 'exe').read_bytes()).hexdigest() != R['binary_sha256']:
                    raise RuntimeError('Agent executable differs')
                identity = proc(pid)
                if identity not in item['observed']:
                    item['observed'].append(identity)
                result.append(identity)
        except (FileNotFoundError, ProcessLookupError):
            pass
    if len(result) > 1:
        raise RuntimeError('more than one Agent in one fixture')
    return result


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

    def release(self):
        sent = time.monotonic_ns()
        self.command('free')
        wait_for(lambda: current(self.item), lambda n: n < 80 << 20)
        return sent

    def close(self):
        if self.p.poll() is None:
            self.command('quit')
            self.p.wait(timeout=10)
        self.select.close()
        if self.p.returncode != 0:
            raise RuntimeError('worker did not exit normally')


def journal(item):
    return load(item['folder'] / 'state/journal.json')


def memory_item(value):
    return next((v for v in value.get('items', []) if v['file'] == 'memory.max'), {})


def unchanged(item, memory, cpu=None):
    actual = controls(item)
    expected = {**item['original'], 'memory.max': str(memory)}
    if cpu is not None:
        expected['cpu.max'] = cpu
    return actual == expected


def restore(item, label):
    result = ex(item, '/crg', 'restore', '--config', '/etc/crg/config.json', required=False)
    value = json.loads(result.stdout)
    item['record'][label] = {'exit': result.returncode, 'status': value,
                             'controls': controls(item), 'journal': journal(item)}
    save()
    return result.returncode, value


def finish_restore(item, worker):
    worker.release()
    code, value = restore(item, 'final_restore')
    check(item['name'] + ': safe restore completes', code == 0 and value['state'] == 'restored'
          and not journal(item)['mutations'] and unchanged(item, LOW))


def delayed(item, action):
    state = item['folder'] / 'state'
    before = {p.name for p in state.glob('.crg-*')}
    old = (state / 'journal.json').read_bytes()
    out, err = open(state / 'restore.stdout', 'w'), open(state / 'restore.stderr', 'w')
    owned(item)
    command = ['docker', 'exec', item['id'], '/usr/bin/strace', '-f', '-ttt', '-T', '-yy',
               '-e', 'trace=fsync,fdatasync', '-e', 'inject=fsync:delay_enter=5s',
               '-o', '/state/restore.strace', '/crg', 'restore', '--config', '/etc/crg/config.json']
    child = subprocess.Popen(command, stdout=out, stderr=err)
    try:
        def pending():
            owned(item)
            if child.poll() is not None:
                raise RuntimeError('traced restore exited before pending-journal barrier')
            for path in state.glob('.crg-*'):
                if path.name in before:
                    continue
                try:
                    value = load(path)
                    if value.get('mutations', {}).get('memory.max:', {}).get('pending') == str(LOW):
                        return path
                except (ValueError, FileNotFoundError):
                    pass
            return None
        path = wait_for(pending, bool, seconds=15)
        barrier = {'temporary_name': path.name, 'start_monotonic_ns': time.monotonic_ns(),
                   'published_journal_unchanged_before': (state / 'journal.json').read_bytes() == old}
        action()
        barrier.update(end_monotonic_ns=time.monotonic_ns(), temporary_still_present=path.exists(),
                       published_journal_unchanged_after=(state / 'journal.json').read_bytes() == old,
                       current_after=current(item))
        code = child.wait(timeout=45)
    finally:
        out.close()
        err.close()
        if child.poll() is None:
            # Stop only the local Docker transport; owned fixture cleanup handles remote children.
            child.terminate()
            child.wait(timeout=10)
    trace = (state / 'restore.strace').read_text()
    value = load(state / 'restore.stdout')
    barrier['trace_proves_delayed_named_temp'] = any(
        path.name in line and 'fsync(' in line and 'DELAYED' in line for line in trace.splitlines())
    item['record']['delay_barrier'] = barrier
    item['record']['delayed_restore'] = {'exit': code, 'status': value,
                                         'journal': journal(item), 'controls': controls(item)}
    check(item['name'] + ': bounded persistence barrier proven',
          barrier['published_journal_unchanged_before'] and barrier['published_journal_unchanged_after']
          and barrier['temporary_still_present'] and barrier['trace_proves_delayed_named_temp'])
    return code, value


def launch(name, stable=0):
    folder = PRIVATE / name
    for sub in ['config', 'state', 'data']:
        (folder / sub).mkdir(parents=True, mode=0o700)
    config = {'resource_mode': 'manual', 'limits': {'cpu_cores': .5}, 'mode': 'enforce',
              'io_calibration': 'off', 'memory_stable_seconds': stable, 'interval_seconds': 1,
              'state_dir': '/state', 'log_dir': '/state/logs', 'data_paths': ['/data']}
    (folder / 'config/config.json').write_text(json.dumps(config))
    (folder / 'config/config.json').chmod(0o600)
    command = ['docker', 'run', '-d', '--name', 'crg-restore-' + NONCE + '-' + name,
               '--label', LABEL + '=' + NONCE, '--network', 'none', '--cgroupns', 'host',
               '--cpus', '2', '--memory', str(HIGH), '--memory-swap', str(HIGH), '--privileged',
               '--mount', 'type=bind,src=/sys/fs/cgroup,dst=/sys/fs/cgroup']
    for source, target in [('config', '/etc/crg'), ('state', '/state'), ('data', '/data')]:
        command += ['--mount', 'type=bind,src=' + str(folder / source) + ',dst=' + target]
    cid = run(command + [TAG]).stdout.strip()
    if not re.fullmatch('[0-9a-f]{64}', cid):
        raise RuntimeError('Docker CID invalid')
    item = {'id': cid, 'name': name, 'folder': folder, 'observed': []}
    ITEMS.append(item)
    meta = json.loads(run(['docker', 'inspect', cid]).stdout)[0]
    host, pid = meta['HostConfig'], meta['State']['Pid']
    if (meta['Config']['Labels'].get(LABEL) != NONCE or host['NetworkMode'] != 'none' or
            host['CgroupnsMode'] != 'host' or host.get('PidMode') not in ['', 'private'] or pid <= 1 or
            any(Path('/proc', str(pid), 'ns', ns).stat().st_ino == Path('/proc/1/ns', ns).stat().st_ino
                for ns in ['pid', 'mnt', 'net'])):
        raise RuntimeError('private labelled fixture identity invalid')
    membership = Path('/proc', str(pid), 'cgroup').read_text()
    if not re.fullmatch('0::/[^\n]*\n', membership):
        raise RuntimeError('pure v2 membership required')
    group = Path('/sys/fs/cgroup') / membership.strip().split('::')[1].lstrip('/')
    if group.resolve() != group or group.name not in [cid, 'docker-' + cid + '.scope']:
        raise RuntimeError('not an own Docker leaf')
    item.update(group=group, main=proc(pid), membership=membership, group_inode=group.stat().st_ino)
    item['observed'].append(item['main'])
    record = {'name': name, 'container_id': cid, 'main': item['main'], 'cgroup': str(group),
              'synthetic_legacy_journal': True, 'harness_writes': [], 'worker_acks': []}
    item['record'] = record
    R['cases'].append(record)
    item['oom'] = events(item)
    write_max(item, LOW)
    item['original'] = controls(item)
    record['original_controls'] = item['original']
    write_max(item, HIGH)
    doctor = json.loads(ex(item, '/crg', 'doctor', '--config', '/etc/crg/config.json').stdout)
    environment = doctor['environment']
    if environment['cgroup'] != str(group) or not environment['identity']:
        raise RuntimeError('candidate discovered target differs from owned leaf')
    payload = {'version': 1, 'identity': environment['identity'], 'target': str(group),
               'mutations': {'memory.max:': {'file': 'memory.max', 'value': str(HIGH),
                                            'original': str(LOW), 'applied': str(HIGH)}}}
    path = folder / 'state/journal.json'
    path.write_text(json.dumps(payload))
    path.chmod(0o600)
    record['seeded_journal'] = payload
    save()
    return item


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


def case(name, operation, stable=0):
    item = launch(name, stable)
    worker = Worker(item)
    try:
        operation(item, worker)
        time.sleep(.5)
        ack = worker.command('status')
        check(name + ': workload and controls survive', ack['fsync_count'] > worker.first['fsync_count']
              and not ack['fsync_failed'] and unchanged(item, LOW) and not agents(item))
        after = events(item)
        check(name + ': no observed cgroup OOM events',
              all(after[k] == item['oom'][k] for k in ['oom', 'oom_kill', 'oom_group_kill'] if k in after),
              before=item['oom'], after=after)
        worker.close()
    finally:
        # Cleanup always owns only the exact labelled fixture. A failed case remains failed.
        remove(item)
        target = A.output / name
        target.mkdir()
        for p in (item['folder'] / 'state').rglob('*'):
            if p.is_file() and not p.is_symlink() and p.stat().st_size <= 2 << 20:
                dest = target / p.relative_to(item['folder'] / 'state')
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, dest)
        save()


def unsafe(item, worker):
    worker.command('alloc ' + str(192 << 20))
    check('unsafe-before: actual allocation exceeds original limit', current(item) > LOW)
    code, value = restore(item, 'unsafe_restore')
    entry = memory_item(value)
    check('unsafe-before: deferred ownership retained', code != 0 and entry.get('state') == 'skipped'
          and entry.get('reason_code') == 'memory_safety' and unchanged(item, HIGH)
          and 'memory.max:' in journal(item)['mutations'])
    finish_restore(item, worker)


def allocate_during(item, worker):
    worker.command('alloc ' + str(16 << 20))
    code, value = delayed(item, lambda: worker.command('alloc ' + str(192 << 20)))
    entry = memory_item(value)
    check('allocate-during: post-persistence safety recheck prevents hard decrease', code != 0
          and entry.get('state') == 'skipped' and entry.get('reason_code') == 'memory_safety'
          and current(item) > LOW and unchanged(item, HIGH)
          and journal(item)['mutations']['memory.max:']['pending'] == str(LOW))
    finish_restore(item, worker)


def external_during(item, worker):
    worker.command('alloc ' + str(16 << 20))
    code, value = delayed(item, lambda: write_max(item, EXTERNAL))
    check('external-during: concurrent writer preserved and conflict persisted', code != 0
          and unchanged(item, EXTERNAL) and journal(item)['mutations']['memory.max:'].get('conflict'))
    code, value = restore(item, 'conflict_retry')
    check('external-during: conflict remains visible on retry', code != 0
          and memory_item(value).get('reason_code') == 'external_conflict' and unchanged(item, EXTERNAL))
    worker.release()
    write_max(item, LOW)  # Explicit external owner returns the original value; CRG must only forget it.
    code, value = restore(item, 'external_returned_original')
    check('external-during: externally restored entry forgotten safely', code == 0
          and value['state'] == 'restored' and not journal(item)['mutations'] and unchanged(item, LOW))


def stable_agent(item, worker):
    worker.command('alloc ' + str(192 << 20))
    owned(item)
    run(['docker', 'exec', '-d', item['id'], '/crg', 'run', '--config', '/etc/crg/config.json'])
    agent = wait_for(lambda: agents(item), lambda v: len(v) == 1)[0]
    samples = []
    for _ in range(3):
        value = wait_for(lambda: load(item['folder'] / 'state/status.json')
                         if (item['folder'] / 'state/status.json').exists() else {},
                         lambda v: memory_item(v).get('reason_code') == 'memory_safety')
        samples.append(value)
        check('live-agent: unsafe partial cycle ' + str(len(samples)), agents(item) == [agent]
              and unchanged(item, HIGH, '50000 100000'))
        time.sleep(1.1)
    sent = worker.release()
    seen = []
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        if agents(item) != [agent]:
            raise RuntimeError('Agent identity changed during stable window')
        value = load(item['folder'] / 'state/status.json')
        seen.append({'monotonic_ns': time.monotonic_ns(), 'memory_item': memory_item(value),
                     'actual_memory_max': controls(item)['memory.max']})
        if unchanged(item, LOW, '50000 100000') and 'memory.max:' not in journal(item)['mutations']:
            break
        time.sleep(.25)
    item['record']['stable_samples'] = seen
    elapsed = (time.monotonic_ns() - sent) / 1e9
    check('live-agent: same process waits for stable window then restores',
          elapsed >= 5 and any(v['memory_item'].get('reason_code') == 'memory_window' for v in seen)
          and unchanged(item, LOW, '50000 100000') and agents(item) == [agent], elapsed_seconds=elapsed)
    result = ex(item, '/crg', 'disable', '--config', '/etc/crg/config.json')
    item['record']['disable'] = json.loads(result.stdout)
    wait_for(lambda: agents(item), lambda v: not v)
    check('live-agent: disable restores CPU and leaves memory original', unchanged(item, LOW)
          and item['record']['disable']['state'] == 'restored')


try:
    endpoint = run(['docker', 'context', 'inspect']).stdout
    context = json.loads(endpoint)[0]
    check('local Docker endpoint only', context['Endpoints']['docker']['Host'] == 'unix:///var/run/docker.sock')
    check('exclusive VM has no other running Docker fixtures', not run(['docker', 'ps', '-q']).stdout.strip())
    check('unified cgroup2 filesystem', run(['stat', '-fc', '%T', '/sys/fs/cgroup']).stdout.strip() == 'cgroup2fs')
    mem = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    check('bounded fixture has host headroom', int(mem['MemAvailable'].split()[0]) >= 2 * 1024**2)
    R['binary_sha256'] = hashlib.sha256(A.binary.read_bytes()).hexdigest()
    check('exact final ELF', R['binary_sha256'] == PLAN['binary_sha256'][A.arch])
    info = json.loads(run([A.binary, 'build-info']).stdout)
    check('embedded final identity', info['version'] == 'v1.0.0' and info['revision'] == PLAN['source_revision']
          and info['arch'] == A.arch and info['go_version'] == 'go1.27.3', build_info=info)
    image = PRIVATE / 'image'
    image.mkdir()
    dependencies = ['/usr/bin/strace']
    ldd = run(['ldd', '/usr/bin/strace']).stdout
    if 'not found' in ldd:
        raise RuntimeError('strace dependency unresolved')
    dependencies += re.findall(r'(/[A-Za-z0-9_./+\-]+)', ldd)
    R['strace'] = {'version': run(['/usr/bin/strace', '--version']).stdout.splitlines()[0],
                   'dependencies': {}}
    for name in sorted(set(dependencies)):
        source = Path(name)
        if not source.is_file() or not str(source.resolve()).startswith(('/usr/lib/', '/lib/', '/usr/bin/')):
            raise RuntimeError('unexpected system tracer dependency')
        dest = image / 'rootfs' / name.lstrip('/')
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        dest.chmod(0o755)
        R['strace']['dependencies'][name] = hashlib.sha256(dest.read_bytes()).hexdigest()
    for source, name in [(A.binary, 'crg'), (A.holder, 'hold'), (A.worker, 'worker')]:
        shutil.copyfile(source, image / name)
        (image / name).chmod(0o755)
    (image / 'Dockerfile').write_text('FROM scratch\nCOPY rootfs /\nCOPY crg hold worker /\nENTRYPOINT ["/hold"]\n')
    run(['docker', 'build', '--label', LABEL + '=' + NONCE, '-t', TAG, image], timeout=90)
    R['phase'] = 'testing'
    save()
    for name, operation, stable in [('unsafe-before', unsafe, 0), ('allocate-during', allocate_during, 0),
                                     ('external-during', external_during, 0), ('stable-agent', stable_agent, 5)]:
        case(name, operation, stable)
    R['phase'] = 'passed'
except BaseException as error:
    R['phase'] = 'failed'
    R['error'] = type(error).__name__ + ': ' + str(error)
    R['traceback'] = traceback.format_exc()
finally:
    failures = []
    for item in reversed(ITEMS):
        try:
            remove(item)
        except BaseException as error:
            failures.append(type(error).__name__ + ': ' + str(error))
    meta = run(['docker', 'image', 'inspect', TAG], required=False)
    if meta.returncode == 0:
        value = json.loads(meta.stdout)[0]
        if value['Config'].get('Labels', {}).get(LABEL) == NONCE:
            try:
                run(['docker', 'image', 'rm', TAG])
            except BaseException as error:
                failures.append(str(error))
        else:
            failures.append('image owner changed; retained')
    R['cleanup'] = {'errors': failures, 'all_owned_containers_removed': all(i.get('removed') for i in ITEMS),
                     'private_bounded_fixture_files_retained_until_VM_disposal': True}
    if failures:
        R['phase'] = 'failed'
    save()
print(json.dumps({'phase': R['phase'], 'checks': len(R['tests']), 'error': R.get('error')}))
raise SystemExit(0 if R['phase'] == 'passed' else 1)
