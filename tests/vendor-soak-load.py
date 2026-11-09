from __future__ import print_function, division

"""Bounded synthetic workload INSIDE a disposable vendor container, Python 2/3.

Creates one new 64MiB test schema. Never run against a business database.
No management of containers, resources, original tables, or database settings.
"""
import argparse
import ctypes
import datetime
import json
import os
import re
import select
import signal
import tempfile
import threading
import time
try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run-id', required=True)
parser.add_argument('--seconds', type=int, required=True)
parser.add_argument('--source-run-id', help='reuse only a prior passed equal-duration fixture; never reuse its output')
parser.add_argument('--test-phase', choices=['smoke', 'baseline', 'enforce', 'acceptance'], default='smoke')
args = parser.parse_args()
if not re.match(r'^[0-9]{8,14}\Z', args.run_id):
    parser.error('run-id must contain 8..14 digits')
if not 1 <= args.seconds <= 604800:
    parser.error('seconds must be 1..604800; short smoke is not long acceptance')
if args.test_phase in ['baseline', 'enforce'] and args.seconds < 86400:
    parser.error('baseline/enforce acceptance requires at least 86400 actual seconds')
if args.test_phase == 'acceptance' and args.seconds < 604800:
    parser.error('seven-day acceptance requires at least 604800 actual seconds')
if args.source_run_id and not re.match(r'^[0-9]{8,14}\Z', args.source_run_id):
    parser.error('source-run-id must contain 8..14 digits')
if os.environ.get('CRG_VENDOR_SOAK_TEST') != 'disposable-loopback-only':
    parser.error('explicit disposable test marker missing')
if open('/proc/self/cgroup').read() != open('/proc/1/cgroup').read():
    parser.error('test worker must share its own container PID1 cgroup')

import psycopg2
from psycopg2 import extensions

if hasattr(time, 'monotonic'):
    monotonic = time.monotonic
else:
    class Timespec(ctypes.Structure):
        _fields_ = [('seconds', ctypes.c_long), ('nanoseconds', ctypes.c_long)]
    libc = ctypes.CDLL(None, use_errno=True)
    def monotonic():
        result = Timespec()
        if libc.clock_gettime(1, ctypes.byref(result)) != 0:
            raise RuntimeError('monotonic clock unavailable')
        return result.seconds + result.nanoseconds / 1e9

stop = threading.Event()
interrupted = [False]
lock = threading.Lock()
bounds = [.001, .005, .01, .02, .05, .1, .25, .5, 1, 2, 5]
def stats():
    return {'attempts': 0, 'successes': 0, 'errors': 0, 'max_seconds': 0,
            'total_seconds': 0, 'histogram': [0] * (len(bounds) + 1)}
report = {'schema': 'crg-vendor-soak-v1', 'run_id': args.run_id,
          'test_phase': args.test_phase,
          'requested_duration_seconds': args.seconds, 'phase': 'preparing',
          'scope': 'synthetic loopback SQL and POST /test; no vendor-specific backup APIs',
          'criteria': {'sql_period_seconds': 2, 'api_period_seconds': 5,
                       'maximum_seconds': 5, 'p95_upper_bound_seconds': 1,
                       'maximum_errors': 0, 'minimum_scheduled_samples_fraction': .98},
          'latency_bucket_upper_seconds': bounds + ['over-5'],
          'sql': stats(), 'api': stats()}
schema = 'crg_soak_' + (args.source_run_id or args.run_id)
root = '/opt/postgresql/basebackup/crg-soak-' + args.run_id
os.mkdir(root, 0o700)  # Fresh directory; never replace another run.

def save():
    with lock:
        snapshot = json.dumps(report, sort_keys=True, indent=2)
    fd, path = tempfile.mkstemp(prefix='.sample-', dir=root)
    try:
        os.chmod(path, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(snapshot + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.rename(path, root + '/load.json')
    finally:
        if os.path.exists(path):
            os.unlink(path)

def wait_pg(connection, seconds):
    deadline = monotonic() + seconds
    while True:
        state = connection.poll()
        if state == extensions.POLL_OK:
            return
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise RuntimeError('bounded SQL client deadline')
        if state == extensions.POLL_READ:
            readable, _, _ = select.select([connection.fileno()], [], [], remaining)
            if not readable:
                raise RuntimeError('bounded SQL read deadline')
        elif state == extensions.POLL_WRITE:
            _, writable, _ = select.select([], [connection.fileno()], [], remaining)
            if not writable:
                raise RuntimeError('bounded SQL write deadline')
        else:
            raise RuntimeError('unsupported asynchronous client state')

def connect():
    connection = psycopg2.connect(host='127.0.0.1', port=5432, user='postgres',
                                  dbname='postgres', connect_timeout=3, **{'async': 1})
    try:
        wait_pg(connection, 5)
        return connection
    except Exception:
        connection.close()
        raise

def query(connection, statement, seconds=5):
    cursor = connection.cursor()
    try:
        cursor.execute(statement)
        wait_pg(connection, seconds)
        return cursor.fetchall() if cursor.description else []
    finally:
        cursor.close()

def checksum(connection):
    row = query(connection, 'SELECT count(*),sum(id),sum(octet_length(payload)),'
                 "md5(string_agg(md5(payload),'' ORDER BY id)),sum(counter) FROM " +
                 schema + '.fixture', 60)[0]
    return [int(row[0]), int(row[1]), int(row[2]), row[3], int(row[4])]

def sample(kind, started, success):
    elapsed = monotonic() - started
    with lock:
        item = report[kind]
        item['attempts'] += 1
        item['successes' if success and elapsed <= 5 else 'errors'] += 1
        item['max_seconds'] = max(item['max_seconds'], elapsed)
        item['total_seconds'] += elapsed
        bucket = next((i for i, bound in enumerate(bounds) if elapsed <= bound), len(bounds))
        item['histogram'][bucket] += 1

def sql_load():
    connection = None
    iteration = 0
    try:
        while not stop.is_set():
            started = monotonic()
            success = False
            try:
                if connection is None:
                    connection = connect()
                first = 1 + iteration % 1024 * 16
                rows = query(connection, 'UPDATE ' + schema + '.fixture SET counter=counter+1 '
                             'WHERE id BETWEEN %d AND %d RETURNING id' % (first, first + 15))
                success = len(rows) == 16
                iteration += 1
            except Exception:
                if connection is not None:
                    connection.close()
                    connection = None
            sample('sql', started, success)
            stop.wait(max(0, 2 - (monotonic() - started)))
    finally:
        if connection is not None:
            connection.close()

def api_load():
    while not stop.is_set():
        started = monotonic()
        success = False
        try:
            response = urlopen(Request('http://127.0.0.1:8090/test', data=b'{}',
                               headers={'Content-Type': 'application/json'}), timeout=4)
            try:
                success = response.getcode() == 200 and json.loads(response.read(1024))['Result'] == '000'
            finally:
                response.close()
        except Exception:
            pass
        sample('api', started, success)
        stop.wait(max(0, 5 - (monotonic() - started)))

def handle_stop(signum, frame):
    interrupted[0] = True
    stop.set()
signal.signal(signal.SIGTERM, handle_stop)
signal.signal(signal.SIGINT, handle_stop)
save()
try:
    connection = connect()
    try:
        if args.source_run_id:
            previous_path = '/opt/postgresql/basebackup/crg-soak-' + args.source_run_id + '/load.json'
            if os.path.islink(previous_path):
                raise RuntimeError('prior test output must not be a symlink')
            with open(previous_path) as stream:
                previous = json.load(stream)
            if previous.get('phase') != 'passed' or previous.get('requested_duration_seconds') != args.seconds or previous.get('elapsed_seconds', 0) < args.seconds:
                raise RuntimeError('prior equal-duration workload did not complete acceptance')
            report['source_run_id'] = args.source_run_id
        else:
            query(connection, 'CREATE SCHEMA ' + schema)
            query(connection, 'CREATE TABLE ' + schema + '.fixture(id bigint PRIMARY KEY,'
                  'payload text NOT NULL,counter bigint NOT NULL DEFAULT 0)')
            query(connection, 'ALTER TABLE ' + schema + '.fixture ALTER COLUMN payload SET STORAGE EXTERNAL')
            query(connection, 'INSERT INTO ' + schema +
                  ".fixture(id,payload) SELECT g,repeat(md5(g::text),128) FROM generate_series(1,16384) g", 300)
            query(connection, 'CHECKPOINT', 300)
        report['initial_checksum'] = checksum(connection)
        if args.source_run_id and report['initial_checksum'][:4] != previous['final_checksum'][:4]:
            raise RuntimeError('prior workload data integrity does not match')
    finally:
        connection.close()
    if report['initial_checksum'][0] != 16384 or report['initial_checksum'][2] != 67108864:
        raise RuntimeError('initial fixture integrity mismatch')
    started = monotonic()
    report['started_utc'] = datetime.datetime.utcnow().isoformat() + 'Z'
    report['phase'] = 'running'
    save()
    threads = [threading.Thread(target=sql_load), threading.Thread(target=api_load)]
    for thread in threads:
        thread.daemon = True
        thread.start()
    next_save = started + 300
    while not stop.wait(.5):
        elapsed = monotonic() - started
        if elapsed >= args.seconds:
            break
        if monotonic() >= next_save:
            report['elapsed_seconds'] = elapsed
            save()
            next_save = monotonic() + 300
    stop.set()
    for thread in threads:
        thread.join(7)
    report['threads_stopped'] = all(not thread.is_alive() for thread in threads)
    report['elapsed_seconds'] = monotonic() - started
    connection = connect()
    try:
        report['final_checksum'] = checksum(connection)
    finally:
        connection.close()
    report['payload_integrity'] = report['initial_checksum'][:4] == report['final_checksum'][:4]
    passed = report['threads_stopped'] and report['payload_integrity'] and not interrupted[0]
    for kind, period in [('sql', 2), ('api', 5)]:
        item = report[kind]
        cumulative = 0
        p95 = None
        for index, count in enumerate(item['histogram']):
            cumulative += count
            if cumulative >= item['attempts'] * .95:
                p95 = bounds[index] if index < len(bounds) else None
                break
        item['p95_bucket_upper_seconds'] = p95
        item['sample_coverage'] = item['attempts'] / max(1, args.seconds / period)
        passed = passed and item['errors'] == 0 and item['max_seconds'] <= 5 and p95 is not None and p95 <= 1 and item['sample_coverage'] >= .98
    report['phase'] = 'passed' if passed else 'failed'
except Exception as error:
    stop.set()
    report['phase'] = 'failed'
    # Never collect arbitrary exception messages, environment or connection data.
    report['failure_class'] = type(error).__name__ if type(error).__name__ in ['RuntimeError', 'OperationalError', 'ProgrammingError', 'OSError'] else 'other'
report['interrupted'] = interrupted[0]
report['ended_utc'] = datetime.datetime.utcnow().isoformat() + 'Z'
save()
print(json.dumps({'phase': report['phase'], 'requested_seconds': args.seconds,
                  'actual_seconds': report.get('elapsed_seconds'), 'interrupted': interrupted[0]}))
raise SystemExit(0 if report['phase'] == 'passed' else 1)
