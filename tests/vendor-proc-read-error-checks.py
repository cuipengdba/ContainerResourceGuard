from __future__ import print_function
"""Linux Python2/3 error privacy checks and own-process stack-read probe only."""
import argparse
import errno
import hashlib
import json
import os
import sys
import types

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--work-dir', required=True)
parser.add_argument('--helper-sha256', required=True)
args = parser.parse_args()
assert sys.platform.startswith('linux')
assert os.environ.get('CRG_PROC_ERROR_CHECKS') == 'authorized-disposable-readonly-only'
assert args.work_dir.startswith(('/var/tmp/crg-', '/tmp/crg-')) and '..' not in args.work_dir.split('/')
assert not os.path.lexists(args.work_dir)
os.umask(0o077)
os.mkdir(args.work_dir, 0o700)
source = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor-proc-read-error.py')
with open(source, 'rb') as stream:
    raw = stream.read(16385)
assert len(raw) <= 16384 and hashlib.sha256(raw).hexdigest() == args.helper_sha256
m = types.ModuleType('proc_error_target');m.__file__ = source
exec(compile(raw, source, 'exec'), m.__dict__)
checks = []
report = {'schema': 'crg-proc-read-error-checks-v1', 'phase': 'running',
          'helper_sha256': hashlib.sha256(raw).hexdigest(), 'python': sys.version.split()[0],
          'checks': checks, 'signals_cgroup_writes_or_DB_commands': 0,
          'scope': 'synthetic privacy/boundary cases plus own files and own process; not business or historic errno proof'}


def check(name, condition):
    checks.append({'name': name, 'passed': bool(condition)})
    if not condition:
        raise AssertionError(name)


try:
    for name in ['EPERM', 'EACCES', 'ENOENT', 'ESRCH', 'EINVAL', 'EOPNOTSUPP', 'EIO', 'EAGAIN']:
        number = getattr(errno, name)
        value = m.metadata(OSError(number, 'sensitive-message', '/private/example'), 'read')
        check('preserve-number-'+name, value['errno'] == number and value['errno_name'] == errno.errorcode[number] and not value['available'])
    check('unknown-positive-errno-explicit', m.metadata(OSError(4095, 'sensitive-message'), 'read')['errno_name'] == 'UNKNOWN_ERRNO')
    class SuppliedError(Exception):
        pass
    for label, number in [('negative', -1), ('zero', 0), ('too-large', 4096), ('boolean', True), ('text', 'sensitive-code')]:
        error = SuppliedError();error.errno = number
        value = m.metadata(error, 'open')
        check('invalid-errno-'+label, value['errno'] is None and value['errno_name'] is None)
    value = m.metadata(RuntimeError('sensitive-message'), 'read')
    check('non-OS-error-remains-unknown', value['reason'] == 'unavailable' and value['errno'] is None)
    class SensitiveClassName(OSError):
        pass
    check('arbitrary-class-name-not-returned', m.metadata(SensitiveClassName(errno.EIO, 'sensitive-message'), 'read')['reason'] == 'unavailable')
    text = json.dumps(m.metadata(OSError(errno.EACCES, 'sensitive-message', '/private/example'), 'read'))
    check('messages-filenames-not-returned-and-bounded', 'sensitive' not in text and '/private' not in text and len(text) <= 256)
    try:
        m.metadata(OSError(errno.EIO, 'sensitive-message'), 'sensitive-stage')
    except ValueError as error:
        check('stage-not-arbitrary-output', str(error) == 'PROC_ERROR_STAGE')
    else:
        check('stage-not-arbitrary-output', False)
    try:
        os.open(args.work_dir+'/absent', os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as error:
        check('actual-missing-file-errno', m.metadata(error, 'open')['errno'] == errno.ENOENT)
    else:
        check('actual-missing-file-errno', False)
    fd = os.open(args.work_dir+'/target', os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600);os.close(fd)
    os.symlink('target', args.work_dir+'/link')
    try:
        fd = os.open(args.work_dir+'/link', os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as error:
        check('actual-symlink-refusal-errno', m.metadata(error, 'open')['errno'] == errno.ELOOP)
    else:
        os.close(fd);check('actual-symlink-refusal-errno', False)
    try:
        os.read(-1, 1)
    except OSError as error:
        check('actual-read-failure-stage-and-errno', m.metadata(error, 'read')['stage'] == 'read' and m.metadata(error, 'read')['errno'] == errno.EBADF)
    probe = m.self_stack();report['self_stack_probe'] = probe
    check('actual-own-stack-structured-without-content', isinstance(probe.get('available'), bool) and 'raw' not in probe and 'frames' not in probe and (probe['available'] and 0 <= probe['bytes'] <= 4096 or not probe['available'] and probe.get('stage') in ['open', 'read'] and (probe.get('errno') is not None or probe['reason'] == 'READ_BOUND')))
    with open('/proc/self/status') as stream:
        status = stream.read(65537)
    caps = [line.split()[1] for line in status.splitlines() if line.startswith('CapEff:')]
    assert len(caps) == 1 and len(status) <= 65536
    report['own_identity'] = {'euid': os.geteuid(), 'egid': os.getegid(), 'CAP_SYS_ADMIN_effective': bool(int(caps[0], 16) & (1 << 21))}
    check('actual-identity-context-bounded', all(isinstance(report['own_identity'][k], int) for k in ['euid', 'egid']))
    previous = os.environ.pop('CRG_PROC_ERROR_CHECKS')
    try:
        try:
            m.self_stack()
        except ValueError as error:
            check('marker-required-before-own-proc-read', str(error) == 'PROC_ERROR_LAB_MARKER')
        else:
            check('marker-required-before-own-proc-read', False)
    finally:
        os.environ['CRG_PROC_ERROR_CHECKS'] = previous
    assert len(checks) == 24 and all(c['passed'] for c in checks)
    report['phase'] = 'passed'
except BaseException as error:
    report.update(phase='failed', failure_class=type(error).__name__, failure_check=checks[-1]['name'] if checks else None)
fd = os.open(args.work_dir+'/result.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
with os.fdopen(fd, 'w') as stream:
    stream.write(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
sys.exit(0 if report['phase'] == 'passed' else 1)
