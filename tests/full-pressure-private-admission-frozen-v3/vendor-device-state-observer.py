#!/usr/bin/env python
"""Bounded, read-only device/cgroup metadata for disposable test diagnostics.

Python 2.7/3 on Linux. A frozen plan pins one process, its cgroup, the boot and
at most four already confirmed sysfs device directories. Default is preflight;
execution writes only one new private report, never a block device or control.
"""
from __future__ import division, print_function
import argparse
import ctypes
import errno
import hashlib
import json
import os
import re
import signal
import stat
import sys
import time

MAX_SECONDS, MAX_DEVICES, MAX_FILE = 900, 4, 65536
MAX_ROW, MAX_REPORT = 8192, 8 * 1024 * 1024
PLAN_SCHEMA = 'crg-device-state-observer-plan-v1'
STAT_FIELDS = ('reads_completed', 'reads_merged', 'read_sectors_512bytes', 'read_ms',
               'writes_completed', 'writes_merged', 'write_sectors_512bytes', 'write_ms',
               'in_flight', 'io_ms', 'weighted_io_ms', 'discards_completed',
               'discards_merged', 'discard_sectors_512bytes', 'discard_ms', 'flushes_completed', 'flush_ms')
MEM_KEYS = ('MemAvailable', 'Dirty', 'Writeback')
VM_KEYS = ('nr_dirty', 'nr_writeback', 'nr_dirtied', 'nr_written', 'nr_dirty_threshold',
           'nr_dirty_background_threshold', 'pgpgin', 'pgpgout', 'pswpin', 'pswpout', 'pgmajfault')
GROUP_KEYS = {'memory.stat': ('anon', 'file', 'shmem', 'file_dirty', 'file_writeback'),
              'memory.events': ('low', 'high', 'max', 'oom', 'oom_kill', 'oom_group_kill'),
              'cpu.stat': ('usage_usec', 'user_usec', 'system_usec', 'nr_periods', 'nr_throttled', 'throttled_usec')}
GROUP_FILES = tuple(GROUP_KEYS) + ('io.stat', 'memory.current', 'cpu.max', 'memory.max', 'io.max')
try:
    TEXT = (basestring,)
    INTS = (int, long)
except NameError:
    TEXT, INTS = (str,), (int,)


class Rejected(Exception):
    pass


def require(value, reason):
    if not value:
        raise Rejected(reason)


def integer(value, minimum=0):
    return type(value) in INTS and minimum <= value < 2**64


def match(pattern, value):
    return isinstance(value, TEXT) and re.match(pattern + r'\Z', value) is not None


def numeric(value):
    require(match(r'[0-9]{1,20}', value) and int(value) < 2**64, 'NUMERIC_FIELD')
    return int(value)


class Timespec(ctypes.Structure):
    _fields_ = [('seconds', ctypes.c_long), ('nanoseconds', ctypes.c_long)]


def libc_function(name, argtypes):
    f = getattr(ctypes.CDLL(None, use_errno=True), name)
    f.restype, f.argtypes = ctypes.c_int, argtypes
    return f


_clock, _openat = None, None
if sys.platform.startswith('linux'):
    _clock = libc_function('clock_gettime', [ctypes.c_int, ctypes.POINTER(Timespec)])
    _openat = libc_function('openat', [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_uint])


def clock(number):
    value = Timespec()
    require(_clock is not None and _clock(number, ctypes.byref(value)) == 0, 'CLOCK_UNAVAILABLE')
    return value.seconds + value.nanoseconds / 1e9


def identity(value):
    return [value.st_dev, value.st_ino]


def open_at(directory, name, flags, mode=0):
    require(match(r'[A-Za-z0-9_.-]{1,100}', name) and name not in ['.', '..'], 'RELATIVE_FILE_NAME')
    flags |= os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, 'O_CLOEXEC', 0)
    fd = _openat(directory, name.encode('ascii'), flags, mode)
    if fd < 0:
        raise OSError(ctypes.get_errno(), 'OPENAT_FAILED')
    return fd


def read_fd(fd, maximum):
    pieces, size = [], 0
    while size <= maximum:
        chunk = os.read(fd, min(8192, maximum+1-size))
        if not chunk:
            break
        pieces.append(chunk)
        size += len(chunk)
    require(size <= maximum, 'READ_BOUND')
    return b''.join(pieces).decode('ascii', 'strict')


def read_at(directory, name, maximum=MAX_FILE):
    fd = open_at(directory, name, os.O_RDONLY)
    try:
        return read_fd(fd, maximum)
    finally:
        os.close(fd)


def read_path(path, maximum=MAX_FILE):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        return read_fd(fd, maximum)
    finally:
        os.close(fd)


def key_values(text, allowed, unit=None):
    result = {}
    for line in text.splitlines():
        row = line.split()
        if not row or row[0].rstrip(':') not in allowed:
            continue
        key = row[0].rstrip(':')
        require(key not in result and len(row) == (3 if unit else 2), 'COUNTER_FORMAT')
        require(unit is None or row[2] == unit, 'COUNTER_UNIT')
        result[key] = numeric(row[1]) * (1024 if unit == 'kB' else 1)
    return result


def device_stat(text):
    values = text.split()
    # Unknown layouts are not silently re-labelled. Missing newer fields remain absent.
    require(len(values) in [11, 15, 17], 'DEVICE_STAT_LAYOUT')
    return dict(zip(STAT_FIELDS, [numeric(v) for v in values]))


def io_values(text, selected, limits=False):
    result = {}
    allowed = ('rbps', 'wbps', 'riops', 'wiops') if limits else ('rbytes', 'wbytes', 'rios', 'wios')
    for line in text.splitlines():
        parts = line.split()
        require(parts and match(r'[0-9]{1,6}:[0-9]{1,9}', parts[0]), 'IO_DEVICE_FORMAT')
        if parts[0] not in selected:
            continue
        require(parts[0] not in result, 'IO_DEVICE_DUPLICATE')
        values = {}
        for part in parts[1:]:
            pair = part.split('=')
            require(len(pair) == 2, 'IO_FIELD_FORMAT')
            k, v = pair
            if k not in allowed:
                continue
            require(k not in values, 'IO_FIELD_DUPLICATE')
            values[k] = None if limits and v == 'max' else numeric(v)
        result[parts[0]] = values
    return result


def counter_delta(before, after, gauges=()):
    # Counters can reset/wrap. Never turn that into a negative/huge rate.
    keys = set(before) | set(after)
    invalid = [k for k in keys if k not in before or k not in after or (k not in gauges and after[k] < before[k])]
    if invalid:
        return {'available': False, 'reason': 'counter-reset-or-layout-change'}
    return {'available': True, 'deltas': {k: after[k]-before[k] for k in keys if k not in gauges},
            'gauges_at_end': {k: after[k] for k in gauges if k in after}}


def process_fields(text):
    prefix, rest = text.rsplit(')', 1)
    pid = int(prefix.split('(', 1)[0])
    values = rest.split()
    require(len(values) >= 20, 'PROCESS_STAT_FORMAT')
    return {'pid': pid, 'state': values[0], 'start_ticks': numeric(values[19])}


def membership(text):
    require(match(r'0::(/[^\n]*)\n?', text), 'PURE_V2_MEMBERSHIP')
    value = text.strip().split('::')[1]
    require('..' not in value.split('/') and '//' not in value, 'MEMBERSHIP_PATH')
    return '/sys/fs/cgroup' + ('' if value == '/' else value)


def reject_constant(value):
    raise Rejected('JSON_CONSTANT')


def unique_object(pairs):
    result = {}
    for k, v in pairs:
        require(k not in result, 'JSON_DUPLICATE')
        result[k] = v
    return result


def checked_plan(path, digest):
    raw = read_path(path, 16384).encode('ascii')
    require(match(r'[a-f0-9]{64}', digest) and hashlib.sha256(raw).hexdigest() == digest, 'PLAN_DIGEST')
    plan = json.loads(raw.decode('ascii'), object_pairs_hook=unique_object, parse_constant=reject_constant)
    keys = {'schema', 'observer_sha256', 'label', 'pid', 'start_ticks', 'cgroup', 'cgroup_identity',
            'boot_id', 'devices', 'duration_seconds', 'output'}
    require(type(plan) is dict and set(plan) == keys and plan['schema'] == PLAN_SCHEMA, 'PLAN_SCHEMA')
    with open(__file__, 'rb') as stream:
        source = stream.read(MAX_FILE+1)
    require(len(source) <= MAX_FILE and plan['observer_sha256'] == hashlib.sha256(source).hexdigest(), 'OBSERVER_SOURCE')
    require(plan['label'] in ['dbs', 'hisdbs', 'selftest'] and integer(plan['pid'], 1) and integer(plan['start_ticks'], 1), 'PLAN_PROCESS')
    require(integer(plan['duration_seconds'], 1) and plan['duration_seconds'] <= MAX_SECONDS, 'PLAN_DURATION')
    require(match(r'[a-f0-9-]{36}', plan['boot_id']), 'BOOT_FORMAT')
    group = plan['cgroup']
    require(isinstance(group, TEXT) and (group == '/sys/fs/cgroup' or group.startswith('/sys/fs/cgroup/'))
            and group == os.path.realpath(group) and '..' not in group.split('/'), 'CGROUP_PATH')
    require(type(plan['cgroup_identity']) is list and len(plan['cgroup_identity']) == 2
            and all(integer(v, 1) for v in plan['cgroup_identity']), 'CGROUP_IDENTITY_FORMAT')
    require(type(plan['devices']) is list and 1 <= len(plan['devices']) <= MAX_DEVICES, 'PLAN_DEVICE_BOUND')
    seen = set()
    for dev in plan['devices']:
        require(type(dev) is dict and set(dev) == {'major_minor', 'sysfs', 'identity'}, 'DEVICE_SCHEMA')
        name, path = dev['major_minor'], dev['sysfs']
        require(match(r'[0-9]{1,6}:[0-9]{1,9}', name) and name not in seen, 'DEVICE_NUMBER')
        require(isinstance(path, TEXT) and path.startswith('/sys/devices/') and '..' not in path.split('/')
                and path == os.path.realpath(path), 'DEVICE_PATH')
        require(type(dev['identity']) is list and len(dev['identity']) == 2
                and all(integer(v, 1) for v in dev['identity']), 'DEVICE_IDENTITY_FORMAT')
        seen.add(name)
    output = plan['output']
    require(isinstance(output, TEXT) and output.startswith('/var/tmp/crg-') and '..' not in output.split('/')
            and match(r'[a-z0-9][a-z0-9-]{0,80}\.json', os.path.basename(output))
            and os.path.isdir(os.path.dirname(output)) and os.path.dirname(output) == os.path.realpath(os.path.dirname(output))
            and not os.path.lexists(output), 'FRESH_PRIVATE_OUTPUT')
    return plan


class Observer(object):
    def __init__(self, plan):
        self.plan, self.fds, self.device_fds = plan, [], {}
        self.output_created = False
        try:
            self.proc = self.directory('/proc/'+str(plan['pid']))
            self.group = self.directory(plan['cgroup'])
            require(identity(os.fstat(self.group)) == plan['cgroup_identity'], 'CGROUP_INSTANCE')
            for dev in plan['devices']:
                fd = self.directory(dev['sysfs'])
                require(identity(os.fstat(fd)) == dev['identity'], 'DEVICE_INSTANCE')
                self.device_fds[dev['major_minor']] = fd
                device_stat(read_at(fd, 'stat', 4096))
            self.check_identity()
        except BaseException:
            self.close()
            raise

    def directory(self, path):
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0))
        self.fds.append(fd)
        return fd

    def check_identity(self):
        require(read_path('/proc/sys/kernel/random/boot_id', 128).strip() == self.plan['boot_id'], 'BOOT_CHANGED')
        process = process_fields(read_at(self.proc, 'stat', 4096))
        require(process['pid'] == self.plan['pid'] and process['start_ticks'] == self.plan['start_ticks']
                and process['state'] not in ['X', 'Z'], 'PROCESS_INSTANCE')
        require(membership(read_at(self.proc, 'cgroup', 4096)) == self.plan['cgroup'], 'CGROUP_MEMBERSHIP')
        require(identity(os.lstat(self.plan['cgroup'])) == self.plan['cgroup_identity'], 'CGROUP_REPLACED')
        for dev in self.plan['devices']:
            name = dev['major_minor']
            require(os.path.realpath('/sys/dev/block/'+name) == dev['sysfs']
                    and identity(os.lstat(dev['sysfs'])) == dev['identity'], 'DEVICE_REPLACED')
            require(read_at(self.device_fds[name], 'dev', 128).strip() == name, 'DEVICE_NUMBER_CHANGED')
        return process

    @staticmethod
    def optional(reader, parser):
        try:
            return {'available': True, 'value': parser(reader())}
        except (OSError, IOError, UnicodeError, ValueError, Rejected) as error:
            reason = str(error) if isinstance(error, Rejected) else 'read-unavailable'
            return {'available': False, 'reason': reason}

    def group_value(self, name, text):
        if name in GROUP_KEYS:
            return key_values(text, GROUP_KEYS[name])
        if name in ['io.stat', 'io.max']:
            return io_values(text, self.device_fds, name == 'io.max')
        fields = text.split()
        if name == 'cpu.max':
            require(len(fields) == 2, 'CPU_MAX_FORMAT')
            return {'quota': None if fields[0] == 'max' else numeric(fields[0]), 'period': numeric(fields[1])}
        require(len(fields) == 1, 'SCALAR_FORMAT')
        return None if name == 'memory.max' and fields[0] == 'max' else numeric(fields[0])

    def snapshot(self):
        started, cpu = clock(1), clock(2)
        row = {'epoch': time.time(), 'monotonic': started, 'process': self.check_identity(), 'devices': {}, 'cgroup': {}}
        for name, fd in sorted(self.device_fds.items()):
            row['devices'][name] = self.optional(lambda fd=fd: read_at(fd, 'stat', 4096), device_stat)
        row['host_memory_bytes'] = self.optional(lambda: read_path('/proc/meminfo'), lambda text: key_values(text, MEM_KEYS, 'kB'))
        row['host_vmstat_raw_units'] = self.optional(lambda: read_path('/proc/vmstat'), lambda text: key_values(text, VM_KEYS))
        for name in GROUP_FILES:
            row['cgroup'][name] = self.optional(lambda name=name: read_at(self.group, name), lambda text, name=name: self.group_value(name, text))
        self.check_identity()  # Discard whole row if the pinned target/device changed.
        row.update(ended_epoch=time.time(), ended_monotonic=clock(1), collection_seconds=clock(1)-started,
                   observer_cpu_seconds=clock(2)-cpu)
        require(len(json.dumps(row).encode('ascii')) <= MAX_ROW, 'ROW_BOUND')
        return row

    def close(self):
        for fd in self.fds:
            os.close(fd)
        self.fds = []


def execute(plan, observer, first_sample=None):
    parent = observer.directory(os.path.dirname(plan['output']))
    fd = open_at(parent, os.path.basename(plan['output']), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    observer.output_created = True
    stream = os.fdopen(fd, 'wb')
    started, cpu, rows, size = clock(1), clock(2), [], 0
    report = {'schema': 'crg-device-state-observer-report-v1', 'phase': 'incomplete', 'plan': plan,
              'sample_period_seconds': 1, 'maximum_seconds': MAX_SECONDS, 'maximum_devices': MAX_DEVICES,
              'maximum_report_bytes': MAX_REPORT, 'started_epoch': time.time(), 'samples': rows,
              'block_device_opens_signals_and_control_writes': 0,
              'interpretation': {'separate_reads_are_not_atomic': True, 'parent_child_devices_must_not_be_added': True,
                                 'device_counters_are_shared_not_one_request_or_container': True,
                                 'in_flight_is_a_gauge_not_monotonic_counter': True,
                                 'kernel_counter_resets_or_field_changes_require_unknown_delta': True,
                                 'missing_optional_fields_are_unknown': True, 'causal_chain_or_stable_acceptance_proven': False}}
    try:
        for index in range(plan['duration_seconds']+1):
            delay = started+index-clock(1)
            if delay > 0:
                time.sleep(delay)
            row = observer.snapshot()
            count = len(json.dumps(row).encode('ascii'))
            require(size+count < MAX_REPORT-65536, 'REPORT_BOUND')
            rows.append(row)
            size += count
            if len(rows) == 1 and first_sample is not None:
                first_sample(row)
        report['phase'] = 'observed'
    except (OSError, IOError, UnicodeError, ValueError, Rejected) as error:
        report['reason'] = str(error) if isinstance(error, Rejected) else 'read-unavailable'
    except KeyboardInterrupt:
        report['reason'] = 'observer-interrupted'
    finally:
        try:
            report.update(ended_epoch=time.time(), elapsed_seconds=clock(1)-started, observer_cpu_seconds=clock(2)-cpu,
                          sample_count=len(rows), maximum_collection_seconds=max([r['collection_seconds'] for r in rows]) if rows else None)
            raw = (json.dumps(report, sort_keys=True, separators=(',', ':'))+'\n').encode('ascii')
            require(len(raw) <= MAX_REPORT, 'FINAL_REPORT_BOUND')
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        finally:
            stream.close()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    observer = None
    try:
        require(sys.platform.startswith('linux') and _clock is not None and _openat is not None, 'LINUX_CLOCK_OPENAT_REQUIRED')
        plan = checked_plan(args.plan, args.plan_sha256)
        observer = Observer(plan)
        if not args.execute:
            print(json.dumps({'phase': 'ready', 'executed': False, 'output_created': False}))
            return 0
        require(os.environ.get('CRG_DEVICE_OBSERVER') == 'authorized-disposable-readonly-only', 'EXPLICIT_LAB_MARKER')
        def interrupted(signum, frame):
            raise KeyboardInterrupt()
        for number in [signal.SIGTERM, signal.SIGINT, signal.SIGALRM]:
            signal.signal(number, interrupted)
        signal.alarm(plan['duration_seconds']+15)
        def first(row):
            print(json.dumps({'phase': 'observing', 'sample_count': 1, 'epoch': row['epoch']}))
            sys.stdout.flush()
        result = execute(plan, observer, first)
        print(json.dumps({k: result[k] for k in ['phase', 'sample_count', 'elapsed_seconds', 'observer_cpu_seconds']}))
        return 0 if result['phase'] == 'observed' else 2
    except (OSError, IOError, UnicodeError, Rejected, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'phase': 'rejected', 'reason': str(error) if isinstance(error, Rejected) else 'invalid-or-unavailable',
                          'output_created': bool(observer and observer.output_created)}))
        return 1
    finally:
        if sys.platform.startswith('linux'):
            signal.alarm(0)
        if observer is not None:
            observer.close()


if __name__ == '__main__':
    sys.exit(main())
