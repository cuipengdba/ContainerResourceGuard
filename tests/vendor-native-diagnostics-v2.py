from __future__ import division, print_function
"""Versioned test diagnostics: original requests/locks plus qualified PG waits.

Only disposable native tests use this module. Optional PG/proc failure never
sets the workload stop event, retries its requests or changes its deadlines.
"""
import hashlib
import json
import os
import sys
import time
import types

BASE_SHA = '83b3f8894eea96af9dfc2c789ee54b63cd5803e9dd2218a74f6bc100934c31ab'
WAIT_SHA = '09c330fb06f5ebedddbf4fca108c3b7d4e0f74ca97d3e565292b41ad5391ed69'


def frozen(name, digest):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    with open(path, 'rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('NATIVE_V2_FROZEN_SOURCE')
    module = types.ModuleType(name.replace('-', '_').replace('.', '_'))
    module.__file__ = path
    exec(compile(raw, path, 'exec'), module.__dict__)
    return module


base = frozen('vendor-native-diagnostics.py', BASE_SHA)


def pg_rows(values):
    rows, truncated = base.pg_rows(values)
    for row, original in zip(rows, values):
        # Preserve PG decimal identity text; it is not an OS process start tick.
        row['backend_start_epoch_text'] = original[1]
    return rows, truncated


def create_wait_sampler(run):
    # Python 2 clears a ModuleType dictionary when the module object dies.
    # Keep it alive during construction and for the sampler's whole lifetime.
    module = frozen('vendor-pg-wait.py', WAIT_SHA)
    sampler = module.Sampler(run)
    sampler._source_module = module
    return sampler


def wait_error(error, traceback):
    names = ['Rejected', 'OSError', 'IOError', 'ValueError', 'TypeError', 'NameError',
             'KeyError', 'ImportError', 'SyntaxError', 'AttributeError', 'RuntimeError']
    result = {'class': type(error).__name__ if type(error).__name__ in names else 'other'}
    if isinstance(error, (OSError, IOError)) and type(getattr(error, 'errno', None)) is int:
        result['errno'] = error.errno
    frames, count = [], 0
    while traceback is not None and count < 32:
        frame = traceback.tb_frame
        name = os.path.basename(frame.f_code.co_filename)
        if name in ['vendor-native-diagnostics-v2.py', 'vendor-pg-wait.py', 'vendor-device-state-observer.py']:
            frames.append({'source': name, 'line': traceback.tb_lineno})
        traceback, count = traceback.tb_next, count+1
    result['source_frames'] = frames[-6:]
    return result


class Diagnostics(base.Diagnostics):
    def __init__(self, *args):
        base.Diagnostics.__init__(self, *args)
        before = "application_name='crg-disposable-soak'"
        base.require(self.activity_sql.count(before) == 1, 'NATIVE_V2_BASE_SQL')
        self.activity_sql = self.activity_sql.replace(before, "application_name='crg-disposable-soak-"+self.run_id+"'")
        self.wait_sampler, self.wait_initialization_attempted = None, False
        self.wait_initialization_error = None
        self.summary.update(pg_wait_samples=0, pg_wait_errors=0, pg_wait_unknown_targets=0)
        self.data.update(schema='crg-native-request-pg-diagnostics-v2',
                         frozen_base_sha256=BASE_SHA, frozen_pg_wait_sha256=WAIT_SHA,
                         unique_application_name='crg-disposable-soak-'+self.run_id)
        self.data['limits'].append('PG wait snapshots have separate monotonic intervals; no atomic join or IO causality is claimed.')

    def wait_sample(self, connection):
        if not self.wait_initialization_attempted:
            self.wait_initialization_attempted = True
            try:
                self.wait_sampler = create_wait_sampler(self.run_id)
            except Exception as error:
                self.wait_initialization_error = wait_error(error, sys.exc_info()[2])
        if self.wait_sampler is None:
            return {'available': False, 'reason': 'PG_WAIT_INITIALIZATION_UNAVAILABLE', 'error': self.wait_initialization_error,
                    'targets': [], 'signals_or_control_writes': 0}
        try:
            return self.wait_sampler.sample(lambda sql, seconds: self.query(connection, sql, seconds))
        except Exception as error:
            return {'available': False, 'reason': 'PG_WAIT_COLLECTION_UNAVAILABLE',
                    'error': wait_error(error, sys.exc_info()[2]),
                    'targets': [], 'signals_or_control_writes': 0}

    def observe(self):
        connection = None
        cpu = base.thread_cpu()
        try:
            while not self.stop.is_set():
                began = self.clock()
                sample = {'started_epoch': time.time(), 'started_monotonic': began,
                          'pg_wait': {'available': False, 'reason': 'NATIVE_ACTIVITY_UNAVAILABLE', 'targets': []}}
                try:
                    if connection is None:
                        connection = self.connect()
                    values = self.query(connection, self.activity_sql, 1)
                    rows, truncated = pg_rows(values)
                    sample.update(available=True, rows=rows, truncated=truncated)
                    sample['pg_wait'] = self.wait_sample(connection)
                    if not sample['pg_wait']['available']:
                        # A failed bounded libpq query may leave results pending.
                        # Close only this diagnostic connection, never a client.
                        self.close(connection)
                        connection = None
                except Exception as error:
                    sample.update(available=False, error=base.error_code(error))
                    if connection is not None:
                        self.close(connection)
                        connection = None
                sample.update(ended_epoch=time.time(), elapsed_seconds=self.clock()-began)
                size = len(json.dumps(sample).encode('utf-8'))
                with self.lock:
                    if len(self.data['pg_samples']) >= base.MAX_SAMPLES or size > base.MAX_SAMPLE or self.pg_bytes+size > base.PG_BUDGET:
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
                    wait = sample['pg_wait']
                    if wait['available']:
                        self.summary['pg_wait_samples'] += 1
                        self.summary['pg_wait_unknown_targets'] += sum(not r['kernel_wait']['available'] for r in wait['targets'])
                    else:
                        self.summary['pg_wait_errors'] += 1
                self.stop.wait(max(0, 1-(self.clock()-began)))
        except Exception:
            with self.lock:
                self.summary['phase'] = 'probe-failed'
                self.summary['pg_errors'] += 1
        finally:
            if connection is not None:
                self.close(connection)
            ended = base.thread_cpu()
            with self.lock:
                self.summary['probe_thread_cpu_seconds'] = None if cpu is None or ended is None else max(0, ended-cpu)

    def finalize(self, root):
        began = base.thread_cpu()
        try:
            with self.lock:
                if self.summary['phase'] == 'observing':
                    self.summary['phase'] = 'collected' if self.summary['probe_thread_stopped'] else 'probe-still-live'
                errors = ['pg_errors', 'pg_truncated_samples', 'dropped_pg_samples', 'dropped_requests',
                          'recorder_internal_errors', 'pg_wait_errors']
                self.summary['diagnostic_complete'] = (self.summary['phase'] == 'collected'
                    and self.summary['pg_wait_samples'] > 0 and not any(self.summary[k] for k in errors))
                raw = (json.dumps(self.data, sort_keys=True, separators=(',', ':'))+'\n').encode('utf-8')
            base.require(len(raw) <= base.MAX_REPORT, 'DIAGNOSTIC_REPORT_BOUND')
            path = os.path.join(root, 'native-diagnostics.json')
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            self.summary.update(report_filename='native-diagnostics.json', report_sha256=hashlib.sha256(raw).hexdigest(), report_bytes=len(raw))
        except Exception as error:
            self.summary.update(phase='report-write-failed', report_write_error=base.error_code(error), diagnostic_complete=False)
        finally:
            ended = base.thread_cpu()
            self.summary['final_report_thread_cpu_seconds'] = None if began is None or ended is None else max(0, ended-began)
