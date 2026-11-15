#!/usr/bin/env python3
"""Exact candidate archives: staging/refusal/races and a scratch-container update.

Disposable GitHub-hosted VM only. Never searches for vendor containers.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import selectors
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import traceback
import uuid

P = argparse.ArgumentParser(description=__doc__)
for name in ['plan', 'candidate', 'previous', 'stager', 'holder', 'worker', 'output']:
    P.add_argument('--' + name, type=Path, required=True)
P.add_argument('--arch', choices=['amd64', 'arm64'], required=True)
A = P.parse_args()
if (sys.platform != 'linux' or os.geteuid() != 0 or os.environ.get('CRG_STAGING_TEST') != 'ephemeral-github-hosted-vm-only'
        or os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted'):
    P.error('explicit disposable GitHub-hosted root VM required')
A.output = A.output.resolve()
A.output.mkdir(parents=True, exist_ok=False)
PLAN = json.loads(A.plan.read_bytes())
ROW = PLAN['artifacts'][A.arch]
ROOT = Path(tempfile.mkdtemp(prefix='crg-stage-CI-')).resolve()
NONCE = uuid.uuid4().hex
TAG, LABEL = 'crg-staging:' + NONCE, 'crg.staging-ci'
ITEM = None
R = {'schema': 'crg-verified-staging-native-v1', 'phase': 'preparing', 'arch': A.arch,
     'machine': platform.machine(), 'kernel': platform.release(), 'python': platform.python_version(),
     'scope': PLAN['scope'], 'plan_sha256': hashlib.sha256(A.plan.read_bytes()).hexdigest(),
     'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
     'tests': [], 'staging': [], 'maintenance': [], 'cleanup': {}}
FIELDS = ['cpu.max', 'memory.max', 'memory.high', 'io.max', 'pids.max', 'cpu.weight', 'io.weight', 'memory.swap.max']
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def save():
    p = A.output / 'report.tmp'
    p.write_text(json.dumps(R, indent=2) + '\n')
    p.replace(A.output / 'report.json')


def check(name, passed, **data):
    R['tests'].append({'name': name, 'passed': bool(passed), **data})
    save()
    if not passed:
        raise AssertionError(name)


def run(command, timeout=45, required=True):
    r = subprocess.run([str(x) for x in command], capture_output=True, text=True, timeout=timeout)
    if required and r.returncode:
        R['command_error'] = {'operation': str(command[:2]), 'exit': r.returncode, 'stderr': r.stderr[-2000:]}
        save()
        raise RuntimeError('fixture command failed')
    return r


def load(path):
    if path.stat().st_size > 1048576:
        raise RuntimeError('JSON exceeds1MiB')
    return json.loads(path.read_bytes())


def tree(path):
    if path.is_symlink():
        return {'symlink': os.readlink(path)}
    if not path.exists():
        return None
    if path.is_file():
        return {'file_sha256': sha(path.read_bytes())}
    entries = {str(p.relative_to(path)): {'mode': stat.S_IMODE(p.lstat().st_mode),
            'sha256': sha(p.read_bytes()) if p.is_file() else None}
            for p in sorted(path.rglob('*'))}
    return {'entry_count': len(entries), 'manifest_sha256': sha(json.dumps(entries, sort_keys=True).encode()),
            'crg_sha256': sha((path / 'crg').read_bytes()) if (path / 'crg').is_file() else None}


def arguments(archive, destination, **overrides):
    v = {'sha256': sha(archive.read_bytes()) if archive.is_file() else ROW['candidate_sha256'],
         'source-revision': PLAN['source_revision'], 'package-revision': PLAN['candidate_package_revision'],
         'arch': A.arch, **overrides}
    return [sys.executable, '-I', str(A.stager), str(archive), '--destination', str(destination),
            *[x for k, value in v.items() for x in ['--' + k, value]]]


def staged(name, archive=None, destination=None, success=False, overrides=None):
    archive = archive or A.candidate
    destination = destination or ROOT / name
    before = tree(destination)
    r = run(arguments(archive, destination, **(overrides or {})), required=False, timeout=180)
    value = json.loads(r.stdout)
    data = {'name': name, 'exit': r.returncode, 'result': value, 'before': before, 'after': tree(destination)}
    R['staging'].append(data)
    if success:
        check(name, r.returncode == 0 and value['state'] == 'staged' and value['published']
              and not value['package_code_executed'] and sha((destination / 'crg').read_bytes()) == value['binary_sha256'])
    else:
        check(name, r.returncode != 0 and value['state'] == 'rejected' and not value['published']
              and not value['package_code_executed'] and not value.get('cleanup_error') and before == data['after'])
    check(name + ': no private staging residue', not list(destination.parent.glob('.crg-stage-*')))
    return destination


def malicious(name, kind):
    path = ROOT / (name + '.tar.gz')
    with tarfile.open(A.candidate, 'r:gz') as original, tarfile.open(path, 'w:gz') as out:
        for target in ['BUILD.json', 'SBOM.cdx.json', 'crg']:
            member = original.getmember(target)
            raw = original.extractfile(member).read()
            if kind == 'changed-binary' and target == 'crg':
                raw = raw[:-1] + bytes([raw[-1] ^ 1])
            out.addfile(member, io.BytesIO(raw))
        info = tarfile.TarInfo({'traversal': '../escaped', 'absolute': '/escaped',
                               'duplicate': 'BUILD.json'}.get(kind, 'unsafe'))
        if kind in ['symlink', 'hardlink']:
            info.type = tarfile.SYMTYPE if kind == 'symlink' else tarfile.LNKTYPE
            info.linkname = '/escaped'
        elif kind == 'fifo':
            info.type = tarfile.FIFOTYPE
        elif kind == 'reserved':
            info.name = 'STAGING-VERIFICATION.json'
        out.addfile(info)
    return path


def race(name, action, success):
    archive = ROOT / (name + '-input.tar.gz')
    shutil.copyfile(A.candidate, archive)
    destination = ROOT / name
    trace = A.output / (name + '.strace')
    stdout, stderr = open(A.output / (name + '.stdout'), 'w'), open(A.output / (name + '.stderr'), 'w')
    command = ['/usr/bin/strace', '-f', '-ttt', '-T', '-yy', '-e', 'trace=fsync',
               '-e', 'inject=fsync:delay_enter=2s:when=1', '-o', str(trace),
               *arguments(archive, destination)]
    child = subprocess.Popen(command, stdout=stdout, stderr=stderr)
    try:
        deadline = time.monotonic() + 120
        stage = first = None
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError('stager exited before delayed-fsync barrier')
            for path in ROOT.glob('.crg-stage-*'):
                if (path / 'BUILD.json').is_file():
                    stage, first = path, path / 'BUILD.json'
                    break
            if stage:
                break
            time.sleep(.01)
        if not stage:
            raise TimeoutError('staging barrier not observed')
        before = time.monotonic_ns()
        action(archive, destination)
        barrier = {'temporary_name': stage.name, 'first_file': first.name,
                   'before_monotonic_ns': before, 'after_monotonic_ns': time.monotonic_ns(),
                   'temporary_still_present': stage.exists(), 'destination_before_stager_publish': tree(destination)}
        code = child.wait(timeout=120)
    finally:
        stdout.close()
        stderr.close()
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=10)
    value = load(A.output / (name + '.stdout'))
    barrier['named_delayed_fsync_trace'] = any(stage.name in line and 'BUILD.json' in line
                                             and 'fsync(' in line and 'DELAYED' in line for line in trace.read_text().splitlines())
    R['staging'].append({'name': name, 'exit': code, 'result': value, 'barrier': barrier,
                          'input_sha256_after': sha(archive.read_bytes()), 'destination_after': tree(destination)})
    check(name + ': actual publication barrier', barrier['temporary_still_present'] and barrier['named_delayed_fsync_trace'])
    if success:
        check(name + ': immutable verified snapshot used', code == 0 and value['state'] == 'staged'
              and sha((destination / 'crg').read_bytes()) == ROW['candidate_binary_sha256']
              and sha(archive.read_bytes()) != ROW['candidate_sha256'])
    else:
        check(name + ': external winner never replaced', code != 0 and value['state'] == 'rejected'
              and (destination / 'sentinel').read_text() == 'external-winner'
              and list(destination.iterdir()) == [destination / 'sentinel'] and not value.get('cleanup_error'))
    check(name + ': temporary cleanup complete', not list(ROOT.glob('.crg-stage-*')))


def proc(pid):
    raw = Path('/proc', str(pid), 'stat').read_text()
    return {'pid': int(pid), 'start_ticks': int(raw[raw.rfind(')') + 2:].split()[19])}


def live(identity):
    try:
        value = proc(identity['pid'])
        return all(value[k] == identity[k] for k in ['pid', 'start_ticks'])
    except (FileNotFoundError, ProcessLookupError):
        return False


def owned():
    i = ITEM
    m = json.loads(run(['docker', 'inspect', i['id']]).stdout)[0]
    if (m['Id'] != i['id'] or m['Config']['Labels'].get(LABEL) != NONCE or
            m['State']['Pid'] != i['main']['pid'] or not live(i['main']) or
            Path('/proc', str(i['main']['pid']), 'cgroup').read_text() != i['membership'] or
            i['group'].resolve() != i['group'] or i['group'].stat().st_ino != i['inode']):
        raise RuntimeError('exact owned container/PID1/cgroup identity changed')


def controls():
    owned()
    return {n: (ITEM['group'] / n).read_text().strip() for n in FIELDS}


def events():
    owned()
    return {k: int(v) for k, v in (line.split() for line in (ITEM['group'] / 'memory.events').read_text().splitlines())}


def ex(*command, required=True):
    owned()
    r = run(['docker', 'exec', ITEM['id'], *command], required=required)
    value = json.loads(r.stdout) if r.stdout.strip() else {}
    R['maintenance'].append({'operation': list(command), 'exit': r.returncode, 'result': value,
                              'controls': controls(), 'journal': load(ITEM['folder'] / 'state/journal.json')
                              if (ITEM['folder'] / 'state/journal.json').exists() else None})
    save()
    return r.returncode, value


def actors():
    owned()
    found = []
    for pid in (ITEM['group'] / 'cgroup.procs').read_text().split():
        try:
            argv = Path('/proc', pid, 'cmdline').read_bytes().split(b'\0')
            if argv[:2] == [b'/opt/crg/crg', b'run']:
                identity = {**proc(pid), 'sha256': sha(Path('/proc', pid, 'exe').read_bytes())}
                if identity not in ITEM['observed']:
                    ITEM['observed'].append(identity)
                found.append(identity)
        except (FileNotFoundError, ProcessLookupError):
            pass
    if len(found) > 1:
        raise RuntimeError('more than one Agent in fixture')
    return found


def wait(operation, predicate, seconds=20):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = operation()
        if predicate(value):
            return value
        time.sleep(.1)
    raise TimeoutError('bounded observation timed out')


def agent(expected):
    owned()
    run(['docker', 'exec', '-d', ITEM['id'], '/opt/crg/crg', 'run', '--config', '/etc/crg/config.json'])
    value = wait(actors, lambda a: len(a) == 1)
    wait(controls, lambda c: c == {**ITEM['original'], 'cpu.max': '50000 100000'})
    check('native: single Agent ' + expected[:8], value[0]['sha256'] == expected)
    return value[0]


def native(candidate, previous):
    global ITEM
    check('native: local exclusive Docker VM', not run(['docker', 'ps', '-q']).stdout.strip()
          and json.loads(run(['docker', 'context', 'inspect']).stdout)[0]['Endpoints']['docker']['Host'] == 'unix:///var/run/docker.sock')
    image = ROOT / 'image'
    image.mkdir()
    for source, name in [(A.holder, 'hold'), (A.worker, 'worker')]:
        shutil.copyfile(source, image / name)
        (image / name).chmod(0o755)
    (image / 'Dockerfile').write_text('FROM scratch\nCOPY hold worker /\nENTRYPOINT ["/hold"]\n')
    run(['docker', 'build', '--label', LABEL + '=' + NONCE, '-t', TAG, image], timeout=90)
    folder = ROOT / 'native'
    for n in ['config', 'state', 'data', 'install', 'recovery']:
        (folder / n).mkdir(parents=True, mode=0o700)
    shutil.copyfile(previous / 'crg', folder / 'install/crg')
    (folder / 'install/crg').chmod(0o755)
    config = {'resource_mode': 'manual', 'limits': {'cpu_cores': .5}, 'io_calibration': 'off',
              'mode': 'enforce', 'interval_seconds': 1, 'state_dir': '/state', 'log_dir': '/state/logs', 'data_paths': ['/data']}
    (folder / 'config/config.json').write_text(json.dumps(config))
    command = ['docker', 'run', '-d', '--name', 'crg-staging-' + NONCE, '--label', LABEL + '=' + NONCE,
               '--network', 'none', '--cgroupns', 'host', '--cpus', '2', '--memory', '512m', '--memory-swap', '512m',
               '--privileged', '--mount', 'type=bind,src=/sys/fs/cgroup,dst=/sys/fs/cgroup']
    for source, target in [('config', '/etc/crg'), ('state', '/state'), ('data', '/data'), ('install', '/opt/crg'), ('recovery', '/recovery')]:
        command += ['--mount', 'type=bind,src=' + str(folder / source) + ',dst=' + target]
    command += ['--mount', 'type=bind,src=' + str(candidate) + ',dst=/incoming,readonly', TAG]
    cid = run(command).stdout.strip()
    if not re.fullmatch('[0-9a-f]{64}', cid):
        raise RuntimeError('invalid Docker identity')
    ITEM = {'id': cid, 'folder': folder, 'observed': []}
    meta = json.loads(run(['docker', 'inspect', cid]).stdout)[0]
    pid, host = meta['State']['Pid'], meta['HostConfig']
    if (meta['Config']['Labels'].get(LABEL) != NONCE or host['NetworkMode'] != 'none' or host['CgroupnsMode'] != 'host'
            or host.get('PidMode') not in ['', 'private'] or pid <= 1
            or any(Path('/proc', str(pid), 'ns', ns).stat().st_ino == Path('/proc/1/ns', ns).stat().st_ino for ns in ['pid', 'mnt', 'net'])):
        raise RuntimeError('private labelled namespaces required')
    membership = Path('/proc', str(pid), 'cgroup').read_text()
    if not re.fullmatch('0::/[^\n]*\n', membership):
        raise RuntimeError('pure v2 leaf required')
    group = Path('/sys/fs/cgroup') / membership.strip().split('::')[1].lstrip('/')
    if group.resolve() != group or group.name not in [cid, 'docker-' + cid + '.scope']:
        raise RuntimeError('not an own Docker leaf')
    ITEM.update(main=proc(pid), membership=membership, group=group, inode=group.stat().st_ino)
    ITEM['observed'].append(ITEM['main'])
    ITEM['original'] = controls()
    before_events = events()
    R['native'] = {'container_id': cid, 'main': ITEM['main'], 'cgroup': str(group),
                   'original_controls': ITEM['original'], 'worker_acks': []}
    worker = subprocess.Popen(['docker', 'exec', '-i', cid, '/worker'], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    selector = selectors.DefaultSelector()
    selector.register(worker.stdout, selectors.EVENT_READ)
    def ack(command):
        owned()
        worker.stdin.write(command + '\n'); worker.stdin.flush()
        if not selector.select(10):
            raise TimeoutError('worker acknowledgement missing')
        value = json.loads(worker.stdout.readline())
        if value['fsync_failed']:
            raise RuntimeError('bounded fsync worker failed')
        R['native']['worker_acks'].append(value)
        return value
    first = ack('status')
    for pid in (group / 'cgroup.procs').read_text().split():
        if Path('/proc', pid, 'cmdline').read_bytes().split(b'\0')[0] == b'/worker':
            ITEM['observed'].append(proc(pid))
    old = agent(ROW['previous_binary_sha256'])
    code, value = ex('/opt/crg/crg', 'quiesce', '--config', '/etc/crg/config.json')
    wait(actors, lambda a: not a)
    limited = {**ITEM['original'], 'cpu.max': '50000 100000'}
    check('native: quiesce keeps owned policy and business', code == 0 and controls() == limited and not live(old))
    code, value = ex('/incoming/crg', 'upgrade-check', '--config', '/etc/crg/config.json')
    check('native: verified candidate accepts current quiescent state', code == 0 and value['compatible']
          and value['quiescent_snapshot'] and value['disabled_for_current_container'])
    before = sha((folder / 'install/crg').read_bytes())
    code, value = ex('/incoming/crg', 'binary-install', '--config', '/etc/crg/config.json', '--install-dir', '/opt/crg',
                     '--backup-dir', '/recovery/rejected', '--previous-sha256', ROW['previous_binary_sha256'],
                     '--candidate-sha256', '0' * 64, required=False)
    check('native: wrong candidate digest refuses installed replacement', code != 0 and sha((folder / 'install/crg').read_bytes()) == before
          and controls() == limited and not (folder / 'recovery/rejected').exists())
    code, value = ex('/incoming/crg', 'binary-install', '--config', '/etc/crg/config.json', '--install-dir', '/opt/crg',
                     '--backup-dir', '/recovery/forward', '--previous-sha256', ROW['previous_binary_sha256'],
                     '--candidate-sha256', ROW['candidate_binary_sha256'])
    check('native: actual verified package binary installed with private backup', code == 0 and value['state'] == 'installed'
          and sha((folder / 'install/crg').read_bytes()) == ROW['candidate_binary_sha256']
          and sha((folder / 'recovery/forward/previous-crg').read_bytes()) == ROW['previous_binary_sha256'] and controls() == limited)
    code, value = ex('/opt/crg/crg', 'build-info')
    check('native: installed final build identity', code == 0 and value['version'] == 'v1.0.0' and value['revision'] == PLAN['source_revision'])
    ex('/opt/crg/crg', 'enable', '--config', '/etc/crg/config.json')
    current_agent = agent(ROW['candidate_binary_sha256'])
    check('native: old writer gone after forward installation', not live(old) and actors() == [current_agent])
    ex('/opt/crg/crg', 'quiesce', '--config', '/etc/crg/config.json')
    wait(actors, lambda a: not a)
    code, value = ex('/incoming/crg', 'binary-rollback', '--config', '/etc/crg/config.json', '--install-dir', '/opt/crg', '--backup-dir', '/recovery/forward')
    check('native: unchanged snapshot rollback restores exact previous binary', code == 0 and value['state'] == 'rolled_back'
          and sha((folder / 'install/crg').read_bytes()) == ROW['previous_binary_sha256'] and controls() == limited and not live(current_agent))
    ex('/opt/crg/crg', 'enable', '--config', '/etc/crg/config.json')
    old_again = agent(ROW['previous_binary_sha256'])
    ex('/opt/crg/crg', 'disable', '--config', '/etc/crg/config.json')
    wait(actors, lambda a: not a)
    last = ack('status')
    after_events = events()
    check('native: disable restores all eight original controls', controls() == ITEM['original'] and not live(old_again))
    check('native: placeholder and bounded fsync worker survive entire maintenance', last['fsync_count'] > first['fsync_count']
          and live(ITEM['main']) and not last['fsync_failed'])
    check('native: observed cgroup OOM counters unchanged', all(after_events[k] == before_events[k]
          for k in ['oom', 'oom_kill', 'oom_group_kill'] if k in after_events), before=before_events, after=after_events)
    ack('quit'); worker.wait(timeout=10); selector.close()
    check('native: worker exits normally', worker.returncode == 0)


def cleanup():
    failures = []
    if ITEM is not None:
        try:
            meta = json.loads(run(['docker', 'inspect', ITEM['id']]).stdout)[0]
            if meta['Id'] != ITEM['id'] or meta['Config']['Labels'].get(LABEL) != NONCE:
                raise RuntimeError('cleanup owner changed')
            if 'main' in ITEM:
                owned()
            run(['docker', 'stop', '--time', '10', ITEM['id']], timeout=20)
            run(['docker', 'rm', ITEM['id']])
            wait(lambda: ITEM.get('group', Path('/nonexistent')).exists(), lambda v: not v)
            gone = not run(['docker', 'ps', '-aq', '--filter', 'id=' + ITEM['id']]).stdout.strip()
            dead = all(not live(p) for p in ITEM['observed'])
            check('cleanup: exact container cgroup and observed processes gone', gone and dead,
                  observed=ITEM['observed'], container_absent=gone, cgroup_absent=True, all_observed_dead=dead)
        except BaseException as error:
            failures.append(str(error))
    image = run(['docker', 'image', 'inspect', TAG], required=False)
    if image.returncode == 0:
        value = json.loads(image.stdout)[0]
        if value['Config'].get('Labels', {}).get(LABEL) == NONCE:
            try:
                run(['docker', 'image', 'rm', TAG])
            except BaseException as error:
                failures.append(str(error))
        else:
            failures.append('image ownership differs; retained')
    R['cleanup'] = {'errors': failures, 'private_fixture_files_retained_until_VM_disposal': True}
    if failures:
        R['phase'] = 'failed'
    if ITEM is not None:
        target = A.output / 'native-state'
        for base in ['state', 'recovery']:
            for p in (ITEM['folder'] / base).rglob('*'):
                if p.is_file() and not p.is_symlink() and p.stat().st_size <= 2 << 20:
                    dest = target / p.relative_to(ITEM['folder'])
                    dest.parent.mkdir(parents=True, exist_ok=True);shutil.copyfile(p, dest)


try:
    check('fixed artifact digests', sha(A.candidate.read_bytes()) == ROW['candidate_sha256']
          and sha(A.previous.read_bytes()) == ROW['previous_sha256'])
    check('frozen stager and verifier', sha(A.stager.read_bytes()) == PLAN['inputs']['scripts/stage-release.py']
          and sha(A.stager.with_name('verify-release.py').read_bytes()) == PLAN['inputs']['scripts/verify-release.py'])
    check('native architecture', platform.machine() in {'amd64': ['x86_64'], 'arm64': ['aarch64', 'arm64']}[A.arch])
    candidate = staged('valid-candidate', success=True, overrides={'sha256': ROW['candidate_sha256']})
    previous = staged('valid-previous', archive=A.previous, success=True, overrides={
        'sha256': ROW['previous_sha256'], 'package-revision': PLAN['previous_package_revision']})
    check('private file permissions only', all(stat.S_IMODE(p.lstat().st_mode) & 0o077 == 0
          for root in [candidate, previous] for p in [root, *root.rglob('*')]))
    for name, overrides in [('wrong-sha', {'sha256': '0' * 64}), ('wrong-source', {'source-revision': '0' * 40}),
                             ('wrong-package', {'package-revision': '0' * 40}),
                             ('wrong-arch', {'arch': 'arm64' if A.arch == 'amd64' else 'amd64'})]:
        staged(name, overrides=overrides)
    staged('existing-directory', destination=candidate)
    existing = ROOT / 'existing-file';existing.write_text('keep')
    staged('existing-file', destination=existing)
    link = ROOT / 'existing-link';link.symlink_to(candidate, target_is_directory=True)
    staged('existing-link', destination=link)
    archive_link = ROOT / 'archive-link';archive_link.symlink_to(A.candidate)
    staged('archive-link', archive=archive_link)
    fifo = ROOT / 'archive-fifo';os.mkfifo(fifo, 0o600)
    staged('archive-fifo', archive=fifo)
    for name, mode in [('open-parent', 0o777), ('readonly-parent', 0o500)]:
        parent = ROOT / name;parent.mkdir(mode=mode);parent.chmod(mode)
        staged(name, destination=parent / 'new')
    foreign = ROOT / 'foreign-parent';foreign.mkdir(mode=0o700);os.chown(foreign, 65534, 65534)
    staged('foreign-parent', destination=foreign / 'new')
    parent_link = ROOT / 'parent-link';parent_link.symlink_to(ROOT, target_is_directory=True)
    staged('parent-symlink', destination=parent_link / 'new')
    for kind in ['traversal', 'absolute', 'duplicate', 'symlink', 'hardlink', 'fifo', 'reserved', 'changed-binary']:
        staged('malicious-' + kind, archive=malicious('malicious-' + kind, kind))
    def replace_input(archive, destination):
        replacement = archive.with_suffix('.replacement')
        replacement.write_bytes(b'untrusted changed download')
        replacement.replace(archive)
    race('source-path-replaced', replace_input, True)
    def create_winner(archive, destination):
        destination.mkdir(mode=0o700)
        (destination / 'sentinel').write_text('external-winner')
    race('destination-created', create_winner, False)
    R['phase'] = 'native-maintenance';save()
    native(candidate, previous)
    R['phase'] = 'passed'
except BaseException as error:
    R.update(phase='failed', error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
finally:
    cleanup();save()
print(json.dumps({'phase': R['phase'], 'checks': len(R['tests']), 'error': R.get('error')}))
raise SystemExit(0 if R['phase'] == 'passed' else 1)
