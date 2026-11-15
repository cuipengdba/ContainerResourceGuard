"""Bounded, read-only wait/pressure observer for one disposable vendor Pod.

Python 2/3; never a CRG product agent. The only PostgreSQL query reads numeric
backend identities and fixed wait labels for the two synthetic applications.
Never exports query text, connection strings, environment or arbitrary errors.
"""
from __future__ import print_function, division
import argparse
import ast
import ctypes
import datetime
import hashlib
import json
import math
import os
import re
import signal
import stat
import sys
import threading
import time
import select

MAX_READ = 32768
MAX_SAMPLES = 900
MAX_LINE = 16384
MAX_BYTES = 4 * 1024 * 1024
PERIOD = 2
WAIT_EVENTS = set('relation tuple transactionid virtualxid advisory extend object '
                  'frozenid spectoken page ClientRead ClientWrite DataFileRead '
                  'DataFileWrite DataFileExtend DataFileSync WALWrite WALSync '
                  'WALInsert WALInitWrite WALInitSync BufferIO BufferContent '
                  'BufferMapping LockManager XactSync SyncRep CheckpointDone '
                  'CheckpointStart CheckpointWriteDelay PgSleep'.split())
WAIT_TYPES = set('Activity BufferPin Client Extension IO IPC Lock LWLock Timeout'.split())
STATES = set(['active', 'idle', 'idle in transaction',
              'idle in transaction (aborted)', 'fastpath function call', 'disabled'])
CPU_KEYS = set('usage_usec user_usec system_usec nr_periods nr_throttled throttled_usec'.split())
MEM_KEYS = set('anon file kernel_stack pagetables percpu sock shmem file_mapped '
               'file_dirty file_writeback inactive_anon active_anon inactive_file '
               'active_file slab_reclaimable slab_unreclaimable pgfault pgmajfault '
               'pgscan pgsteal workingset_refault_anon workingset_refault_file'.split())
EVENT_KEYS = set('low high max oom oom_kill oom_group_kill'.split())
VM_KEYS = set('nr_dirty nr_writeback nr_writeback_temp nr_free_pages pgpgin pgpgout '
              'pswpin pswpout pgscan_kswapd pgscan_direct pgsteal_kswapd pgsteal_direct'.split())
IO_KEYS = set('rbytes wbytes rios wios dbytes dios'.split())
ACTIVITY_SQL = (
    "SELECT pid,state,coalesce(wait_event_type,''),coalesce(wait_event,''),"
    "coalesce(extract(epoch FROM clock_timestamp()-query_start),0)::float8,"
    "pg_blocking_pids(pid)::text FROM pg_stat_activity "
    "WHERE datname='postgres' AND usename='postgres' "
    "AND application_name IN ('crg-disposable-soak','crg-disposable-lock') "
    "AND pid<>pg_backend_pid() ORDER BY pid LIMIT 32")


if hasattr(time, 'monotonic'):
    monotonic = time.monotonic
else:
    class Timespec(ctypes.Structure):
        _fields_ = [('seconds', ctypes.c_long), ('nanoseconds', ctypes.c_long)]
    _libc = ctypes.CDLL(None, use_errno=True)
    def monotonic():
        value = Timespec()
        if _libc.clock_gettime(1, ctypes.byref(value)) != 0:
            raise RuntimeError('monotonic unavailable')
        return value.seconds + value.nanoseconds / 1e9


def read_text(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_CLOEXEC', 0))
    with os.fdopen(fd, 'rb') as stream:
        raw = stream.read(MAX_READ + 1)
    if len(raw) > MAX_READ:
        raise RuntimeError('bounded read exceeded')
    return raw.decode('ascii')


def integer(value):
    if not re.match(r'^[0-9]{1,22}\Z', value):
        raise ValueError('invalid unsigned counter')
    return int(value)


def counters(text, allowed):
    result = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) != 2:
            raise ValueError('invalid counter line')
        if fields[0] in allowed:
            if fields[0] in result:
                raise ValueError('duplicate counter')
            result[fields[0]] = integer(fields[1])
    return result


def pressure(text):
    result = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) != 5 or fields[0] not in ['some', 'full'] or fields[0] in result:
            raise ValueError('invalid pressure line')
        item = {}
        for field in fields[1:]:
            key, value = field.split('=', 1)
            if key in item:
                raise ValueError('duplicate pressure counter')
            if key == 'total':
                item[key] = integer(value)
            elif key in ['avg10', 'avg60', 'avg300'] and re.match(r'^[0-9]{1,3}\.[0-9]{1,4}\Z', value):
                item[key] = float(value)
                if not 0 <= item[key] <= 100:
                    raise ValueError('invalid pressure percentage')
            else:
                raise ValueError('invalid pressure counter')
        if set(item) != set(['total', 'avg10', 'avg60', 'avg300']):
            raise ValueError('incomplete pressure counters')
        result[fields[0]] = item
    if not result:
        raise ValueError('empty pressure file')
    return result


def io_counters(text):
    result = {}
    for line in text.splitlines():
        fields = line.split()
        if not fields or not re.match(r'^[0-9]{1,10}:[0-9]{1,10}\Z', fields[0]) or fields[0] in result:
            raise ValueError('invalid IO device')
        if len(result) >= 32:
            raise ValueError('IO devices exceed bound')
        item = {}
        for field in fields[1:]:
            key, value = field.split('=', 1)
            if key in IO_KEYS:
                if key in item:
                    raise ValueError('duplicate IO counter')
                item[key] = integer(value)
        result[fields[0]] = item
    return result


def backends(rows):
    if len(rows) > 32:
        raise ValueError('backend rows exceed bound')
    result = []
    seen = set()
    for row in rows:
        if len(row) != 6:
            raise ValueError('invalid backend columns')
        pid = integer(row[0])
        if pid < 1 or pid in seen:
            raise ValueError('invalid backend identity')
        seen.add(pid)
        age = float(row[4])
        if not 0 <= age <= 604800 or math.isnan(age) or math.isinf(age):
            raise ValueError('invalid query age')
        if not re.match(r'^\{([0-9]+(,[0-9]+)*)?\}\Z', row[5]):
            raise ValueError('invalid blocking identities')
        blockers = [integer(value) for value in row[5][1:-1].split(',')] if row[5] != '{}' else []
        if len(blockers) > 32:
            raise ValueError('blocking identities exceed bound')
        result.append({'pid': pid,
                       'state': row[1] if row[1] in STATES else 'other',
                       'wait_type': row[2] if row[2] in WAIT_TYPES else ('none' if row[2] == '' else 'other'),
                       'wait_event': row[3] if row[3] in WAIT_EVENTS else ('none' if row[3] == '' else 'other'),
                       'query_age_seconds': age, 'blocking_pids': blockers})
    return result


def encode_frame(value, written, terminal=False):
    data = (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode('ascii')
    reserve = 2048 if not terminal else 0
    if len(data) > MAX_LINE or written + len(data) + reserve > MAX_BYTES:
        raise RuntimeError('timeline output bound')
    return data


def stop_requested(root, run_id, expected_start, expected_membership, began):
    path = root + '/stop.json'
    if not os.path.lexists(path):
        return False
    value = json.loads(read_text(path))
    if (value.get('schema') != 'crg-owned-wait-stop-v1' or
            value.get('run_id') != run_id or
            value.get('pid1_start_ticks') != expected_start or
            value.get('membership_sha256') != expected_membership):
        raise RuntimeError('stop request identity mismatch')
    requested = float(value['requested_monotonic'])
    if math.isnan(requested) or math.isinf(requested) or not began <= requested <= monotonic() + 1:
        raise RuntimeError('stop request time mismatch')
    return True


def start_ticks(pid):
    text = read_text('/proc/' + str(pid) + '/stat')
    return integer(text[text.rfind(')') + 2:].split()[19])


class PinnedGroup(object):
    def __init__(self, container_id, expected_start, expected_membership_sha):
        self.container_id = container_id
        self.expected_start = expected_start
        self.membership = read_text('/proc/self/cgroup')
        if self.membership != read_text('/proc/1/cgroup') or hashlib.sha256(self.membership.encode('ascii')).hexdigest() != expected_membership_sha:
            raise RuntimeError('own cgroup identity mismatch')
        lines = self.membership.splitlines()
        if len(lines) != 1 or not lines[0].startswith('0::/'):
            raise RuntimeError('pure v2 required')
        relative = lines[0][3:]
        if '..' in relative.split('/') or not relative.endswith('/cri-containerd-' + container_id + '.scope'):
            raise RuntimeError('own container leaf required')
        self.path = '/sys/fs/cgroup' + relative
        if os.path.realpath(self.path) != self.path:
            raise RuntimeError('noncanonical own group')
        info = os.stat(self.path)
        self.identity = (info.st_dev, info.st_ino)
        self.verify()

    def verify(self):
        if start_ticks(1) != self.expected_start or read_text('/proc/self/cgroup') != self.membership or read_text('/proc/1/cgroup') != self.membership:
            raise RuntimeError('PID1 or membership changed')
        info = os.stat(self.path)
        if (info.st_dev, info.st_ino) != self.identity:
            raise RuntimeError('cgroup inode changed')

    def sample(self):
        self.verify()
        result = {'cpu_stat': counters(read_text(self.path + '/cpu.stat'), CPU_KEYS),
                  'memory_current': integer(read_text(self.path + '/memory.current').strip()),
                  'memory_events': counters(read_text(self.path + '/memory.events'), EVENT_KEYS),
                  'memory_stat': counters(read_text(self.path + '/memory.stat'), MEM_KEYS),
                  'io_stat': io_counters(read_text(self.path + '/io.stat'))}
        for resource in ['cpu', 'memory', 'io']:
            result[resource + '_pressure'] = pressure(read_text(self.path + '/' + resource + '.pressure'))
        self.verify()
        return result


def load_client(path, expected):
    # Execute only exact hash-bound client functions. No worker main/guards,
    # synthetic schema creation or workload SQL is executed by this observer.
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
            raise RuntimeError('invalid worker input')
        raw = stream.read(65537)
    if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != expected:
        raise RuntimeError('worker input changed')
    names = set(['Connection', 'ready', 'connect', 'query'])
    tree = ast.parse(raw)
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    if len(nodes) != 4:
        raise RuntimeError('missing client functions')
    module = ast.Module(body=nodes)
    if sys.version_info[0] >= 3:
        module.type_ignores = []
    pq = ctypes.CDLL('/opt/postgresql/pgsql/lib/libpq.so.5')
    pointer, number, string = ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p
    for name, returns, parameters in [
            ('PQconnectStartParams', pointer, [ctypes.POINTER(string), ctypes.POINTER(string), number]),
            ('PQconnectPoll', number, [pointer]), ('PQsocket', number, [pointer]),
            ('PQsetnonblocking', number, [pointer, number]), ('PQfinish', None, [pointer]),
            ('PQsendQuery', number, [pointer, string]), ('PQflush', number, [pointer]),
            ('PQconsumeInput', number, [pointer]), ('PQisBusy', number, [pointer]),
            ('PQgetResult', pointer, [pointer]), ('PQresultStatus', number, [pointer]),
            ('PQntuples', number, [pointer]), ('PQnfields', number, [pointer]),
            ('PQgetisnull', number, [pointer, number, number]),
            ('PQgetlength', number, [pointer, number, number]),
            ('PQgetvalue', pointer, [pointer, number, number]), ('PQclear', None, [pointer])]:
        function = getattr(pq, name)
        function.restype, function.argtypes = returns, parameters
    namespace = dict(pq=pq, ctypes=ctypes, string=string, monotonic=monotonic, select=select)
    exec(compile(module, '<exact-worker-client>', 'exec'), namespace)
    return namespace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--container-id', required=True)
    parser.add_argument('--pid1-start-ticks', required=True, type=int)
    parser.add_argument('--membership-sha256', required=True)
    parser.add_argument('--worker', required=True)
    parser.add_argument('--worker-sha256', required=True)
    parser.add_argument('--seconds', type=int, required=True)
    args = parser.parse_args()
    if os.environ.get('CRG_VENDOR_WAIT_TEST') != 'disposable-loopback-only' or os.geteuid() == 0:
        parser.error('isolated unprivileged test marker required')
    if not re.match(r'^[0-9]{8,14}\Z', args.run_id) or not re.match(r'^[0-9a-f]{64}\Z', args.container_id):
        parser.error('invalid own run/container identity')
    if any(not re.match(r'^[0-9a-f]{64}\Z', h) for h in [args.membership_sha256, args.worker_sha256]) or args.pid1_start_ticks <= 0:
        parser.error('invalid expected hashes/start')
    if not 30 <= args.seconds <= 1800 or args.worker != '/tmp/crg-soak-load-' + args.run_id + '.py':
        parser.error('bounded duration and exact own worker required')
    pin = PinnedGroup(args.container_id, args.pid1_start_ticks, args.membership_sha256)
    client = load_client(args.worker, args.worker_sha256)
    root = '/opt/postgresql/basebackup/crg-wait-' + args.run_id
    os.mkdir(root, 0o700)
    fd = os.open(root + '/timeline.jsonl', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    output = os.fdopen(fd, 'wb')
    stopped = threading.Event()
    reason = ['duration']
    def finish(signum, frame):
        reason[0] = 'explicit_own_signal'
        stopped.set()
    signal.signal(signal.SIGTERM, finish)
    signal.signal(signal.SIGINT, finish)
    written = [0]
    def emit(value, terminal=False):
        data = encode_frame(value, written[0], terminal)
        output.write(data)
        output.flush()
        written[0] += len(data)
    connection = None
    count = errors = 0
    began = monotonic()
    phase = 'complete'
    try:
        emit({'kind': 'header', 'schema': 'crg-own-wait-pressure-timeline-v1', 'run_id': args.run_id,
              'pid': os.getpid(), 'start_ticks': start_ticks(os.getpid()),
              'pid1_start_ticks': args.pid1_start_ticks, 'membership_sha256': args.membership_sha256,
              'group_device': pin.identity[0], 'group_inode': pin.identity[1],
              'source_sha256': hashlib.sha256(open(__file__, 'rb').read()).hexdigest(),
              'worker_sha256': args.worker_sha256, 'period_seconds': PERIOD,
              'maximum_samples': MAX_SAMPLES, 'maximum_bytes': MAX_BYTES,
              'maximum_line_bytes': MAX_LINE, 'query_timeout_seconds': 1,
              'scope': 'one disposable container; host PSI/vmstat global; sampled non-atomic; observer adds one read query/2s; no performance causality claim'})
        while not stopped.is_set() and monotonic() - began < args.seconds:
            if stop_requested(root, args.run_id, args.pid1_start_ticks, args.membership_sha256, began):
                reason[0] = 'explicit_own_stop_file'
                break
            if count >= MAX_SAMPLES:
                reason[0] = 'sample_limit'
                phase = 'partial'
                break
            started = monotonic()
            row = {'kind': 'sample', 'sequence': count + 1, 'observed_utc': datetime.datetime.utcnow().isoformat() + 'Z',
                   'sample_started_monotonic': started, 'group': pin.sample(), 'host': {}}
            # Only fixed, public numeric kernel counters; no process cmdlines.
            for resource in ['cpu', 'memory', 'io']:
                row['host'][resource + '_pressure'] = pressure(read_text('/proc/pressure/' + resource))
            row['host']['vmstat'] = counters(read_text('/proc/vmstat'), VM_KEYS)
            try:
                if connection is None:
                    connection = client['connect']()  # Original bounded5s connection.
                row['backends'] = backends(client['query'](connection, ACTIVITY_SQL, seconds=1))
                row['backend_query_phase'] = 'complete'
            except Exception:
                errors += 1
                row.update(backends=[], backend_query_phase='unavailable')
                if connection is not None:
                    connection.close()
                    connection = None
            pin.verify()
            row['sample_finished_monotonic'] = monotonic()
            emit(row)
            count += 1
            stopped.wait(max(0, PERIOD - (monotonic() - started)))
    except Exception:
        phase = 'failed'
        reason[0] = 'bounded_observer_failure'
    finally:
        if connection is not None:
            connection.close()
        summary = {'kind': 'terminal', 'phase': phase, 'reason': reason[0],
                   'samples': count, 'backend_query_errors': errors,
                   'elapsed_seconds': monotonic() - began, 'bytes_before_terminal': written[0]}
        try:
            emit(summary, terminal=True)
            output.flush()
            os.fsync(output.fileno())
        finally:
            output.close()
    print(json.dumps(summary, sort_keys=True))
    return 0 if phase == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
