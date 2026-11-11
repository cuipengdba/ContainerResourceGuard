from __future__ import division, print_function
"""Portable parser/identity boundary checks; no PostgreSQL instance needed."""
import argparse
import hashlib
import json
import os
import sys
import types

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--work-dir', required=True)
args = parser.parse_args()
assert sys.platform.startswith('linux') and os.environ.get('CRG_PG_WAIT_CHECKS') == 'authorized-disposable-readonly-only'
assert args.work_dir.startswith(('/var/tmp/crg-', '/tmp/crg-')) and '..' not in args.work_dir.split('/') and not os.path.lexists(args.work_dir)
os.umask(0o077)
os.mkdir(args.work_dir, 0o700)
source = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor-pg-wait.py')
m = types.ModuleType('pg_wait_checks_target')
m.__file__ = source
with open(source, 'rb') as stream:
    raw_source = stream.read()
exec(compile(raw_source, source, 'exec'), m.__dict__)
run = '20261111313'
row = ['postgres', m.app_name(run), '123', '1794410000.123456', 'active', 'LWLock', 'WALWrite']
checks = []
def check(name, value):
    checks.append({'name': name, 'passed': bool(value)})
    assert value, name
def reject(name, work, code):
    try:
        work()
    except m.Rejected as error:
        check(name, str(error) == code)
    else:
        check(name, False)
result = {'schema': 'crg-pg-wait-parser-checks-v1', 'phase': 'running', 'checks': checks,
          'python': sys.version.split()[0], 'helper_sha256': hashlib.sha256(raw_source).hexdigest(),
          'signals_or_control_writes': 0, 'real_PG_qualification': False}
try:
    sql = m.selection_sql(run)
    check('exact-run-app-database-and-row-bound-without-query-body-column', m.app_name(run) in sql and "datname='postgres'" in sql and 'LIMIT 5' in sql and 'query,' not in sql)
    check('backend-start-kept-as-exact-text-not-proc-ticks', m.selected([row], run)[0]['backend_start_epoch_text'] == row[3])
    for name, rows, code in [
        ('five-rows-refuse-truncation', [row]*5, 'PG_WAIT_ROW_BOUND_OR_TRUNCATED'),
        ('wrong-database', [['other']+row[1:]], 'PG_WAIT_RUN_CONTEXT'),
        ('wrong-run', [[row[0], 'crg-disposable-soak-20261111000']+row[2:]], 'PG_WAIT_RUN_CONTEXT'),
        ('invalid-PID', [row[:2]+['0']+row[3:]], 'PG_WAIT_PID'),
        ('nonfinite-backend-start', [row[:3]+['nan']+row[4:]], 'PG_WAIT_BACKEND_START'),
        ('duplicate-PID', [row, row], 'PG_WAIT_DUPLICATE_PID'),
        ('missing-column', [row[:-1]], 'PG_WAIT_COLUMNS'),
        ('unapproved-event', [row[:-1]+['private/event']], 'PG_WAIT_LABEL'),
        ('unavailable-backend-start', [row[:3]+[None]+row[4:]], 'PG_WAIT_BACKEND_START')]:
        reject(name, lambda rows=rows: m.selected(rows, run), code)
    reject('run-cannot-inject-SQL', lambda: m.selection_sql("20261111' OR true"), 'PG_WAIT_RUN')
    text = '74 0x3 0x111 0x222 0x333 0x444 0x555 0x666 0x777'
    call = m.syscall(text, 'linux-x86_64')
    check('native-x86-fsync-FD-only-no-registers', call['operation'] == 'fsync' and call['fd'] == 3 and '0x' not in json.dumps(call))
    check('unknown-ABI-never-decodes-FD', m.syscall(text, 'unknown')['operation'] == 'unknown' and 'fd' not in m.syscall(text, 'unknown'))
    check('running-is-unknown', m.syscall('running', 'linux-x86_64')['reason'] == 'task-running')
    check('outside-syscall-is-unknown', m.syscall('-1 0x123 0x456', 'linux-x86_64')['reason'] == 'outside-system-call')
    reject('malformed-syscall-refused', lambda: m.syscall('1 0x3', 'linux-x86_64'), 'PG_WAIT_SYSCALL')
    check('actual-PGDATA-WAL-path-allowlisted', m.fd_metadata('/opt/postgresql/pgdata/pg_wal/000000010000000000000001', run)['kind'] == 'allowlisted-path')
    check('old-assumed-data-path-redacted', m.fd_metadata('/opt/postgresql/data/pg_wal/private', run)['kind'] == 'redacted-other-path')
    check('path-traversal-redacted', m.fd_metadata('/opt/postgresql/pgdata/../private', run)['kind'] == 'redacted-other-path')
    check('unapproved-path-text-not-retained', 'secret-file' not in json.dumps(m.fd_metadata('/home/secret-file', run)))
    check('only-current-run-backup-path-allowed', m.fd_metadata('/opt/postgresql/basebackup/crg-soak-'+run+'/backup_manifest', run)['kind'] == 'allowlisted-path')
    check('other-run-backup-redacted', m.fd_metadata('/opt/postgresql/basebackup/crg-soak-20261111000/backup_manifest', run)['kind'] == 'redacted-other-path')
    check('socket-number-not-retained', m.fd_metadata('socket:[12345]', run) == {'kind': 'socket'})
    stack = m.kernel_stack('[<ffffffff12345678>] io_schedule+0x1/0x20\n')
    check('kernel-addresses-offsets-not-retained', stack['frames'] == ['io_schedule'] and 'ffff' not in json.dumps(stack) and '0x' not in json.dumps(stack))
    check('kernel-stack-eight-frame-bound', len(m.kernel_stack('io_schedule\n'*40)['frames']) == 8 and m.kernel_stack('io_schedule\n'*40)['truncated'])
    check('unknown-stack-format-counted', m.kernel_stack('??? private\n')['unknown_lines'] == 1 and 'private' not in json.dumps(m.kernel_stack('??? private\n')))
    previous = os.environ.pop('CRG_PG_WAIT', None)
    try:
        reject('missing-lab-marker-before-PG-proc-reads', lambda: m.Sampler(run), 'PG_WAIT_LAB_MARKER')
    finally:
        if previous is not None:
            os.environ['CRG_PG_WAIT'] = previous
    check('arbitrary-exception-text-not-retained', m.reason(RuntimeError('private-exception')) == 'unavailable')
    directory = os.open('/proc/'+str(os.getpid()), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        check('actual-portable-readlinkat-exe', m.readlink(directory, 'exe') == os.readlink('/proc/'+str(os.getpid())+'/exe'))
    finally:
        os.close(directory)
    check('actual-thread-CPU-clock-and-monotonic-clock', m.reader.clock(3) >= 0 and m.reader.clock(1) > 0)
    check('deleted-allowlisted-path-explicit', m.fd_metadata('/opt/postgresql/pgdata/base/1/2 (deleted)', run)['deleted'])
    result['phase'] = 'passed' if len(checks) == 32 else 'failed'
except BaseException as error:
    result.update(phase='failed', reason_class=type(error).__name__, reason=str(error)[:150])
finally:
    fd = os.open(args.work_dir+'/qualification.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(json.dumps(result, indent=2)+'\n')
print(json.dumps({'phase': result['phase'], 'checks': len(checks), 'reason': result.get('reason')}))
sys.exit(0 if result['phase'] == 'passed' else 1)
