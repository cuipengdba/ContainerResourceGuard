from __future__ import division, print_function
"""Python 2/3 checks using mock read-only PG callbacks; no service mutations."""
import argparse
import hashlib
import json
import os
import stat
import sys
import threading
import time
import types

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--work-dir', required=True)
args = parser.parse_args()
assert sys.platform.startswith('linux') and os.environ.get('CRG_NATIVE_DIAGNOSTICS_SELFTEST') == 'authorized-disposable-test-node-only'
assert args.work_dir.startswith('/var/tmp/crg-') or args.work_dir.startswith('/tmp/crg-')
assert '..' not in args.work_dir.split('/') and not os.path.lexists(args.work_dir)
os.mkdir(args.work_dir, 0o700)
source = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor-native-diagnostics.py')
module = types.ModuleType('native_diagnostics')
module.__file__ = source
with open(source, 'rb') as stream:
    raw_source = stream.read()
exec(compile(raw_source, source, 'exec'), module.__dict__)
checks = []


def check(name, value):
    checks.append({'name': name, 'passed': bool(value)})
    assert value, name


class Connection(object):
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def fixture(query=None, clock=None):
    return module.Diagnostics('202611111840', threading.Lock(), threading.Event(),
                              clock or time.time, Connection, query or (lambda c, s, t: []), '0'*64)


try:
    secret = 'private-exception-string-must-not-be-retained'
    value = module.error_code(RuntimeError(secret))
    check('arbitrary-error-message-not-retained', secret not in json.dumps(value) and value['code'] == 'unclassified-runtime')
    check('known-readiness-deadline-distinct', module.error_code(RuntimeError('bounded SQL readiness deadline'))['code'] == 'sql-readiness-deadline')
    check('unknown-exception-class-explicit', module.error_code(Exception(secret))['class'] == 'other')
    row = ['123', '1794390000.25', 'active', 'Lock', 'transactionid', '1794390001', '1794390000.5', '{0,124}', 'fixture-update']
    values, truncated = module.pg_rows([row])
    check('PG-session-identity-and-lock-blockers', not truncated and values[0]['pid'] == 123 and values[0]['backend_start_epoch'] == 1794390000.25 and values[0]['blocking_pids'] == [0,124])
    absent = list(row)
    absent[1:8] = [None]*7
    values, _ = module.pg_rows([absent])
    check('PG-missing-identity-and-blockers-unknown', not values[0]['identity_available'] and not values[0]['activity_fields_available'] and values[0]['blocking_pids'] is None)
    empty = list(row)
    empty[7] = '{}'
    check('measured-empty-blockers-distinct-from-unknown', module.pg_rows([empty])[0][0]['blocking_pids'] == [])
    check('PG-row-truncation-explicit', module.pg_rows([row]*17)[1] is True and len(module.pg_rows([row]*17)[0]) == 16)
    for name, bad in [('row-count', [row]*18), ('column-count', [row[:-1]]), ('backend-pid', [['0']+row[1:]]),
                      ('arbitrary-event', [row[:4]+[secret]+row[5:]]), ('nonfinite-identity', [[row[0], 'nan']+row[2:]])]:
        try:
            module.pg_rows(bad)
        except ValueError:
            check('reject-PG-'+name, True)
        else:
            check('reject-PG-'+name, False)
    clock = [10.0]
    d = fixture(clock=lambda: clock[0])
    event = d.safe(d.begin, 'sql', 48, 10.0)
    d.safe(d.stage, event, 'query', 123)
    d.safe(d.failure, event, RuntimeError('bounded SQL result deadline'))
    clock[0] = 15.013
    d.safe(d.finish, event, False)
    check('request-error-time-stage-PID-and-original-key', event['synthetic_first_key'] == 769 and event['backend_pid'] == 123 and event['elapsed_seconds'] > 5 and event['stage'] == 'query' and event['error']['code'] == 'sql-result-deadline' and d.summary['request_errors'] == 1)
    before = d.summary['recorder_internal_errors']
    d.safe(d.stage, event, secret)
    check('recorder-failure-isolated-and-sanitized', d.summary['recorder_internal_errors'] == before+1 and secret not in json.dumps(d.data))
    d.data['requests'] = [{}]*module.MAX_REQUESTS
    check('request-cap-does-not-stop-business', d.safe(d.begin, 'api', 0, clock[0]) is None and d.summary['dropped_requests'] == 1 and not d.stop.is_set())
    d = fixture()
    d.pg_bytes = module.PG_BUDGET
    d.observe()
    check('PG-budget-stops-probe-only', d.summary['phase'] == 'capacity-exceeded' and d.summary['dropped_pg_samples'] == 1 and not d.stop.is_set())
    calls = []
    def query(connection, sql, seconds):
        calls.append((sql, seconds))
        return [row]
    d = fixture(query)
    d.start()
    time.sleep(.15)
    check('probe-never-stops-original-workload', not d.stop.is_set())
    d.stop.set()
    d.join()
    check('actual-thread-bounded-read-only-query-and-stop', d.summary['probe_thread_stopped'] and d.summary['pg_samples'] == 1 and calls[0][1] == 1 and calls[0][0].startswith('SELECT ') and 'LIMIT 17' in calls[0][0] and 'pg_cancel' not in calls[0][0])
    folder = os.path.join(args.work_dir, 'normal')
    os.mkdir(folder, 0o700)
    d.finalize(folder)
    path = os.path.join(folder, 'native-diagnostics.json')
    with open(path, 'rb') as stream:
        raw = stream.read()
    saved = json.loads(raw.decode('utf-8'))
    check('private-bounded-final-artifact-and-digest', stat.S_IMODE(os.stat(path).st_mode) == 0o600 and hashlib.sha256(raw).hexdigest() == d.summary['report_sha256'] and saved['summary']['diagnostic_complete'] and len(raw) <= module.MAX_REPORT)
    d.finalize(folder)
    with open(path, 'rb') as stream:
        check('existing-output-not-replaced', stream.read() == raw and d.summary['phase'] == 'report-write-failed')
    other = os.path.join(args.work_dir, 'symlink')
    os.mkdir(other, 0o700)
    os.symlink(path, os.path.join(other, 'native-diagnostics.json'))
    fixture().finalize(other)
    with open(path, 'rb') as stream:
        check('symlink-target-not-replaced', stream.read() == raw)
    def failure(connection, sql, seconds):
        raise RuntimeError(secret)
    d = fixture(failure)
    d.start()
    time.sleep(.15)
    d.stop.set()
    d.join()
    check('PG-query-error-explicit-unknown-no-raw-message', d.summary['pg_errors'] == 1 and not d.data['pg_samples'][0]['available'] and secret not in json.dumps(d.data) and d.summary['probe_thread_stopped'])
    original = module.thread_cpu
    module.thread_cpu = lambda: None
    d = fixture()
    d.safe(d.begin, 'api', 0, 1.0)
    module.thread_cpu = original
    check('missing-CPU-clock-not-zero', d.summary['recorder_cpu_seconds'] is None and not d.summary['recorder_cpu_available'])
finally:
    result = {'schema': 'crg-native-diagnostics-selftest-v1', 'phase': 'passed' if len(checks) == 23 and all(i['passed'] for i in checks) else 'failed',
              'checks': checks, 'python_version': sys.version.split()[0], 'platform': sys.platform,
              'diagnostic_source_sha256': hashlib.sha256(raw_source).hexdigest(),
              'business_or_database_processes_used': False, 'original_worker_or_product_modified': False}
    with open(os.path.join(args.work_dir, 'checks-result.json'), 'w') as stream:
        stream.write(json.dumps(result, indent=2)+'\n')
    os.chmod(os.path.join(args.work_dir, 'checks-result.json'), 0o600)
print(json.dumps({'phase': result['phase'], 'checks': len(checks), 'python_version': result['python_version']}))
raise SystemExit(0 if result['phase'] == 'passed' else 1)
