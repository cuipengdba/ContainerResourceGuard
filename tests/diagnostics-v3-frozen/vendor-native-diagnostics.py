from __future__ import division, print_function
"""Bounded Python 2/3 diagnostics for disposable native workload tests only.

Records synthetic request metadata and reads PG activity using an independent
read-only connection. No business cancellation, retry, signaling or policy edits.
"""
import ctypes
import hashlib
import json
import math
import os
import re
import threading
import time

MAX_REQUESTS, MAX_SAMPLES, MAX_ROWS = 1024, 901, 16
MAX_EVENT, MAX_SAMPLE, MAX_REPORT = 2048, 16384, 8 * 1024 * 1024
PG_BUDGET = MAX_REPORT - MAX_REQUESTS * MAX_EVENT - 65536
KNOWN_ERRORS = {
    'bounded SQL socket deadline': 'sql-socket-deadline',
    'bounded SQL readiness deadline': 'sql-readiness-deadline',
    'bounded SQL result deadline': 'sql-result-deadline',
    'SQL send failed': 'sql-send-failed', 'SQL flush failed': 'sql-flush-failed',
    'SQL input failed': 'sql-input-failed', 'SQL server returned an error': 'sql-server-error',
    'SQL connection allocation failed': 'sql-connect-allocation',
    'SQL connection polling failed': 'sql-connect-poll',
    'SQL nonblocking mode unavailable': 'sql-nonblocking',
}
STAGES = {'connect', 'query', 'http-request', 'http-response', 'http-parse', 'complete'}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def error_code(error):
    name = type(error).__name__
    allowed = ['RuntimeError', 'OSError', 'IOError', 'ValueError', 'KeyError',
               'JSONDecodeError', 'URLError', 'HTTPError', 'timeout']
    result = {'class': name if name in allowed else 'other', 'code': 'unclassified'}
    # Compare against a fixed vocabulary; never retain arbitrary exception text.
    if type(error) is RuntimeError:
        result['code'] = KNOWN_ERRORS.get(str(error), 'unclassified-runtime')
    elif name == 'timeout':
        result['code'] = 'socket-timeout'
    elif name == 'HTTPError':
        value = getattr(error, 'code', None)
        if type(value) is int and 100 <= value <= 599:
            result['http_status'] = value
    return result


class Timespec(ctypes.Structure):
    _fields_ = [('seconds', ctypes.c_long), ('nanoseconds', ctypes.c_long)]


try:
    _clock_gettime = ctypes.CDLL(None).clock_gettime
    _clock_gettime.restype = ctypes.c_int
    _clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(Timespec)]
except (AttributeError, OSError):
    _clock_gettime = None


def thread_cpu():
    try:
        stamp = Timespec()
        if _clock_gettime is None or _clock_gettime(3, ctypes.byref(stamp)) != 0:
            return None
        return stamp.seconds + stamp.nanoseconds / 1e9
    except (AttributeError, OSError):
        return None


def finite_epoch(value):
    if value is None:
        return None
    number = float(value)
    require(not math.isnan(number) and not math.isinf(number) and number > 0, 'PG_EPOCH')
    return number


def pg_rows(rows):
    require(type(rows) is list and len(rows) <= MAX_ROWS + 1, 'PG_ROWS_BOUND')
    output = []
    for row in rows[:MAX_ROWS]:
        require(type(row) is list and len(row) == 9, 'PG_COLUMNS')
        pid = int(row[0])
        require(pid > 1, 'PG_BACKEND_PID')
        state, event_type, event = row[2:5]
        require(state is None or re.match(r'^[A-Za-z ()]{0,80}\Z', state), 'PG_STATE')
        for text in [event_type, event]:
            require(text is None or re.match(r'^[A-Za-z0-9_]{0,80}\Z', text), 'PG_LABEL')
        blockers = None
        if row[7] is not None:
            require(re.match(r'^\{(?:[0-9]+(?:,[0-9]+){0,15})?\}\Z', row[7]), 'PG_BLOCKERS_BOUND')
            blockers = [int(v) for v in row[7][1:-1].split(',')] if row[7] != '{}' else []
        require(row[8] in ['fixture-update', 'own-session-other'], 'PG_QUERY_CLASS')
        backend_start = finite_epoch(row[1])
        output.append({'pid': pid, 'backend_start_epoch': backend_start,
                       'identity_available': backend_start is not None,
                       'activity_fields_available': backend_start is not None and state is not None,
                       'state': state, 'wait_event_type': event_type, 'wait_event': event,
                       'query_start_epoch': finite_epoch(row[5]), 'transaction_start_epoch': finite_epoch(row[6]),
                       'blocking_pids': blockers, 'blocking_pids_measured': row[7] is not None,
                       'query_class': row[8]})
    return output, len(rows) > MAX_ROWS


class Diagnostics(object):
    def __init__(self, run_id, lock, stop, clock, connect, query, worker_sha256):
        require(re.match(r'^[0-9]{8,14}\Z', run_id), 'RUN_ID')
        self.run_id, self.lock, self.stop, self.clock = run_id, lock, stop, clock
        self.connect, self.query = connect, query
        self.thread, self.pg_bytes = None, 0
        self.summary = {'phase': 'not-started', 'request_count': 0, 'request_errors': 0,
                        'dropped_requests': 0, 'pg_samples': 0, 'pg_errors': 0, 'pg_truncated_samples': 0,
                        'dropped_pg_samples': 0, 'recorder_internal_errors': 0,
                        'recorder_cpu_seconds': 0.0, 'recorder_cpu_available': True,
                        'probe_thread_cpu_seconds': None, 'probe_thread_stopped': False,
                        'business_signals_cancellations_or_control_writes': 0}
        self.data = {'schema': 'crg-native-request-pg-diagnostics-v1', 'run_id': run_id,
                     'worker_sha256': worker_sha256, 'summary': self.summary,
                     'maximum_report_bytes': MAX_REPORT, 'requests': [], 'pg_samples': [],
                     'limits': ['No arbitrary SQL, error messages, connection parameters or response bodies.',
                                'PG state sampled separately; no sample does not prove no wait.',
                                'Blocking PID zero can denote a prepared transaction; it is not a process target.',
                                'No original request is retried, canceled or extended by diagnostics.']}
        pattern = 'UPDATE crg_soak_' + run_id + '.fixture SET counter=counter+1 WHERE id BETWEEN %'
        # Inspect lock blockers only when a backend actually reports Lock. Calls
        # can contend on PG lock-manager state; their overhead remains measured.
        self.activity_sql = ("SELECT pid::text,extract(epoch FROM backend_start)::text,state,wait_event_type,wait_event,"
                             "extract(epoch FROM query_start)::text,extract(epoch FROM xact_start)::text,"
                             "CASE WHEN wait_event_type='Lock' THEN pg_blocking_pids(pid)::text ELSE NULL END,"
                             "CASE WHEN query LIKE '" + pattern + "' THEN 'fixture-update' ELSE 'own-session-other' END "
                             "FROM (SELECT pid,backend_start,state,wait_event_type,wait_event,query_start,xact_start,query "
                             "FROM pg_stat_activity WHERE datname=current_database() AND application_name='crg-disposable-soak' "
                             "AND pid<>pg_backend_pid() ORDER BY pid LIMIT 17) AS bounded_own_sessions")

    def safe(self, operation, *args):
        began = thread_cpu()
        try:
            return operation(*args)
        except Exception:
            with self.lock:
                self.summary['recorder_internal_errors'] += 1
            return None
        finally:
            ended = thread_cpu()
            with self.lock:
                if began is None or ended is None:
                    self.summary['recorder_cpu_available'] = False
                    self.summary['recorder_cpu_seconds'] = None
                elif self.summary['recorder_cpu_seconds'] is not None:
                    self.summary['recorder_cpu_seconds'] += max(0, ended-began)

    def begin(self, kind, iteration, started):
        require(kind in ['sql', 'api'] and type(iteration) is int and iteration >= 0, 'REQUEST_CONTEXT')
        with self.lock:
            self.summary['request_count'] += 1
            if len(self.data['requests']) >= MAX_REQUESTS:
                self.summary['dropped_requests'] += 1
                return None
            event = {'sequence': self.summary['request_count'], 'kind': kind, 'iteration': iteration,
                     'started_monotonic': started, 'started_epoch': time.time(), 'stage': 'connect' if kind == 'sql' else 'http-request',
                     'backend_pid': None, 'connection_observed_epoch': None, 'error': None}
            if kind == 'sql':
                event['synthetic_first_key'] = 1 + iteration % 1024 * 16
            self.data['requests'].append(event)
            return event

    def stage(self, event, name, backend_pid=None):
        if event is None:
            return
        require(name in STAGES, 'REQUEST_STAGE')
        with self.lock:
            event['stage'] = name
            if backend_pid is not None:
                require(type(backend_pid) is int and backend_pid > 1, 'CLIENT_BACKEND_PID')
                event['backend_pid'] = backend_pid
                event['connection_observed_epoch'] = time.time()

    def failure(self, event, error):
        if event is not None:
            with self.lock:
                event['error'] = error_code(error)

    def finish(self, event, success):
        if event is None:
            return
        ended = self.clock()
        with self.lock:
            event.update(ended_monotonic=ended, ended_epoch=time.time(), elapsed_seconds=ended-event['started_monotonic'], success=bool(success))
            event['within_original_5seconds'] = event['elapsed_seconds'] <= 5
            if not success or not event['within_original_5seconds']:
                self.summary['request_errors'] += 1
            require(len(json.dumps(event).encode('utf-8')) <= MAX_EVENT, 'REQUEST_RECORD_BOUND')

    def start(self):
        require(self.thread is None, 'ONE_PROBE_THREAD')
        self.thread = threading.Thread(target=self.observe)
        self.thread.daemon = True
        with self.lock:
            self.summary['phase'] = 'observing'
        self.thread.start()

    def observe(self):
        connection = None
        cpu = thread_cpu()
        try:
            while not self.stop.is_set():
                began = self.clock()
                sample = {'started_epoch': time.time(), 'started_monotonic': began}
                try:
                    if connection is None:
                        connection = self.connect()
                    values = self.query(connection, self.activity_sql, 1)
                    rows, truncated = pg_rows(values)
                    sample.update(available=True, rows=rows, truncated=truncated)
                except Exception as error:
                    sample.update(available=False, error=error_code(error))
                    if connection is not None:
                        self.close(connection)
                        connection = None
                sample.update(ended_epoch=time.time(), elapsed_seconds=self.clock()-began)
                size = len(json.dumps(sample).encode('utf-8'))
                with self.lock:
                    if len(self.data['pg_samples']) >= MAX_SAMPLES or size > MAX_SAMPLE or self.pg_bytes+size > PG_BUDGET:
                        self.summary['dropped_pg_samples'] += 1
                        self.summary['phase'] = 'capacity-exceeded'
                        break
                    self.data['pg_samples'].append(sample)
                    self.pg_bytes += size
                    self.summary['pg_samples'] += 1
                    if not sample['available']:
                        self.summary['pg_errors'] += 1
                    elif sample['truncated']:
                        self.summary['pg_truncated_samples'] += 1
                self.stop.wait(max(0, 1-(self.clock()-began)))
        except Exception:
            with self.lock:
                self.summary['phase'] = 'probe-failed'
                self.summary['pg_errors'] += 1
        finally:
            if connection is not None:
                self.close(connection)
            ended = thread_cpu()
            with self.lock:
                self.summary['probe_thread_cpu_seconds'] = None if cpu is None or ended is None else max(0, ended-cpu)

    def close(self, connection):
        try:
            connection.close()
        except Exception:
            with self.lock:
                self.summary['pg_errors'] += 1
                self.summary['phase'] = 'probe-close-failed'

    def join(self):
        if self.thread is not None:
            self.thread.join(7)
            with self.lock:
                self.summary['probe_thread_stopped'] = not self.thread.is_alive()

    def finalize(self, root):
        began = thread_cpu()
        try:
            with self.lock:
                if self.summary['phase'] == 'observing':
                    self.summary['phase'] = 'collected' if self.summary['probe_thread_stopped'] else 'probe-still-live'
                if any(self.summary[k] for k in ['pg_errors', 'pg_truncated_samples', 'dropped_pg_samples', 'dropped_requests', 'recorder_internal_errors']):
                    self.summary['diagnostic_complete'] = False
                else:
                    self.summary['diagnostic_complete'] = self.summary['phase'] == 'collected'
                raw = (json.dumps(self.data, sort_keys=True, separators=(',', ':'))+'\n').encode('utf-8')
            require(len(raw) <= MAX_REPORT, 'DIAGNOSTIC_REPORT_BOUND')
            path = os.path.join(root, 'native-diagnostics.json')
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            self.summary.update(report_filename='native-diagnostics.json', report_sha256=hashlib.sha256(raw).hexdigest(), report_bytes=len(raw))
        except Exception as error:
            self.summary.update(phase='report-write-failed', report_write_error=error_code(error), diagnostic_complete=False)
        finally:
            ended = thread_cpu()
            self.summary['final_report_thread_cpu_seconds'] = None if began is None or ended is None else max(0, ended-began)
