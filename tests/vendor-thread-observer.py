#!/usr/bin/env python3
"""Bounded read-only diagnosis of one disposable vendor process and its cgroup.

Not a product agent. No target signals, control writes, command lines, environment,
process memory, user stacks or file-descriptor contents are collected. Default is
read-only preflight; explicit execution writes only one new private report.
"""
import argparse
import contextlib
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sys
import time

SCHEMA = 'crg-vendor-thread-observer-plan-v1'
MAX_THREADS, MAX_SECONDS, MAX_FILE = 64, 900, 65536
MAX_RECORD, MAX_REPORT = 32768, 32 * 1024 * 1024
GROUP_FILES = ('cpu.stat', 'io.stat', 'memory.current', 'memory.stat',
               'memory.events', 'cpu.pressure', 'memory.pressure', 'io.pressure',
               'cpu.max', 'memory.max', 'io.max')
STATUS_KEYS = {'State', 'Threads', 'VmRSS', 'RssAnon', 'RssFile', 'RssShmem',
               'VmSwap', 'voluntary_ctxt_switches', 'nonvoluntary_ctxt_switches'}


class Rejected(Exception):
    pass


def require(value, reason):
    if not value:
        raise Rejected(reason)


def read_at(directory, name, maximum=MAX_FILE):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
    try:
        raw = bytearray()
        while len(raw) <= maximum:
            chunk = os.read(fd, min(8192, maximum + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        require(len(raw) <= maximum, 'READ_BOUND')
        return raw.decode('utf-8', 'strict')
    finally:
        os.close(fd)


def stat_fields(text):
    # A comm can contain spaces and parentheses. Field 3 starts after final ')'.
    before, rest = text.rsplit(')', 1)
    pid = int(before.split('(', 1)[0].strip())
    parts = rest.split()
    require(len(parts) >= 40, 'PROC_STAT_FIELDS')
    return {'pid': pid, 'state': parts[0], 'minor_faults': int(parts[7]),
            'major_faults': int(parts[9]), 'user_ticks': int(parts[11]),
            'system_ticks': int(parts[12]), 'threads': int(parts[17]),
            'start_ticks': int(parts[19]), 'block_io_ticks': int(parts[39])}


def limited_status(text):
    result = {}
    for line in text.splitlines():
        key, separator, value = line.partition(':')
        if separator and key in STATUS_KEYS:
            require(re.fullmatch(r'[A-Za-z0-9_ ()\t-]{1,80}', value.strip()), 'STATUS_VALUE')
            result[key] = value.strip()
    return result


def pure_v2_path(text):
    match = re.fullmatch(r'0::(/[^\n]*)\n?', text)
    require(match and '..' not in Path(match[1]).parts, 'PURE_V2_MEMBERSHIP')
    return match[1]


def checked_plan(path, expected):
    with path.open('rb') as stream:
        raw = stream.read(16385)
    require(len(raw) <= 16384 and re.fullmatch('[0-9a-f]{64}', expected)
            and hashlib.sha256(raw).hexdigest() == expected, 'PLAN_DIGEST')
    plan = json.loads(raw)
    keys = {'schema', 'observer_sha256', 'label', 'pid', 'start_ticks',
            'executable_sha256', 'cgroup', 'duration_seconds', 'output'}
    require(type(plan) is dict and set(plan) == keys and plan['schema'] == SCHEMA, 'PLAN_SCHEMA')
    require(plan['observer_sha256'] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'OBSERVER_SOURCE')
    require(plan['label'] in ['dbs', 'hisdbs', 'selftest']
            and type(plan['pid']) is int and plan['pid'] > 1
            and type(plan['start_ticks']) is int and plan['start_ticks'] > 0
            and type(plan['duration_seconds']) is int and 1 <= plan['duration_seconds'] <= MAX_SECONDS,
            'PLAN_TARGET_OR_DURATION')
    require(type(plan['executable_sha256']) is str and re.fullmatch('[0-9a-f]{64}', plan['executable_sha256']), 'EXECUTABLE_DIGEST')
    group, output = Path(plan['cgroup']), Path(plan['output'])
    require(group.is_absolute() and '..' not in group.parts and group == group.resolve()
            and (str(group) == '/sys/fs/cgroup' or str(group).startswith('/sys/fs/cgroup/')), 'CGROUP_PATH')
    require(output.is_absolute() and '..' not in output.parts and str(output).startswith('/var/tmp/crg-')
            and re.fullmatch('[a-z0-9][a-z0-9-]{0,80}\\.json', output.name)
            and output.parent.is_dir() and output.parent == output.parent.resolve()
            and not os.path.lexists(output), 'FRESH_PRIVATE_OUTPUT')
    return plan


class Observer:
    def __init__(self, plan):
        self.plan, self.proc_fd, self.group_fd = plan, None, None
        self.output_created = False
        try:
            self.proc_fd = os.open('/proc/' + str(plan['pid']), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            self.group_fd = os.open(plan['cgroup'], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            self.group_identity = self.identity(os.fstat(self.group_fd))
            executable = os.stat('exe', dir_fd=self.proc_fd)
            require(executable.st_size <= 128 * 1024 * 1024, 'EXECUTABLE_SIZE_BOUND')
            self.exe_identity = self.identity(executable)
            fd = os.open('exe', os.O_RDONLY, dir_fd=self.proc_fd)
            try:
                digest = hashlib.sha256()
                total = 0
                while True:
                    block = os.read(fd, 1024 * 1024)
                    if not block:
                        break
                    total += len(block)
                    require(total <= 128 * 1024 * 1024, 'EXECUTABLE_SIZE_BOUND')
                    digest.update(block)
                require(digest.hexdigest() == plan['executable_sha256'], 'EXECUTABLE_IDENTITY')
            finally:
                os.close(fd)
            self.check_identity()
        except BaseException:
            self.close()
            raise

    @staticmethod
    def identity(value):
        return [value.st_dev, value.st_ino]

    def check_identity(self):
        fields = stat_fields(read_at(self.proc_fd, 'stat'))
        require(fields['pid'] == self.plan['pid'] and fields['start_ticks'] == self.plan['start_ticks']
                and fields['state'] not in ['Z', 'X'], 'PROCESS_INSTANCE')
        require(self.identity(os.stat('exe', dir_fd=self.proc_fd)) == self.exe_identity, 'EXECUTABLE_CHANGED')
        membership = pure_v2_path(read_at(self.proc_fd, 'cgroup'))
        require(str(Path('/sys/fs/cgroup') / membership.lstrip('/')) == self.plan['cgroup'], 'CGROUP_MEMBERSHIP')
        require(self.identity(os.stat(self.plan['cgroup'], follow_symlinks=False)) == self.group_identity, 'CGROUP_REPLACED')
        return fields

    def optional(self, directory, name, maximum=MAX_FILE):
        try:
            return {'available': True, 'value': read_at(directory, name, maximum).strip()}
        except (OSError, Rejected, UnicodeError) as error:
            # No arbitrary exception text or hidden file data in diagnostics.
            return {'available': False, 'reason': type(error).__name__}

    def snapshot(self):
        started, cpu = time.monotonic(), time.process_time()
        row = {'epoch': time.time(), 'monotonic': started, 'process': self.check_identity(),
               'cgroup': {name: self.optional(self.group_fd, name) for name in GROUP_FILES},
               'status': limited_status(read_at(self.proc_fd, 'status')), 'tasks': [], 'task_races': 0}
        with contextlib.ExitStack() as stack:
            task_fd = os.open('task', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.proc_fd)
            stack.callback(os.close, task_fd)
            tids = sorted(int(name) for name in os.listdir(task_fd) if name.isdigit())
            row['task_count'], row['tasks_truncated'] = len(tids), len(tids) > MAX_THREADS
            for tid in tids[:MAX_THREADS]:
                fd = None
                try:
                    fd = os.open(str(tid), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=task_fd)
                    fields = stat_fields(read_at(fd, 'stat'))
                    require(fields['pid'] == tid, 'TASK_IDENTITY')
                    task = {'stat': fields, 'wchan': self.optional(fd, 'wchan', 256),
                            'schedstat': self.optional(fd, 'schedstat', 256)}
                    after = stat_fields(read_at(fd, 'stat'))
                    require(after['pid'] == tid and after['start_ticks'] == fields['start_ticks'], 'TASK_CHANGED')
                    row['tasks'].append(task)
                except (OSError, Rejected):
                    row['task_races'] += 1
                finally:
                    if fd is not None:
                        os.close(fd)
        self.check_identity()  # Discard the whole sample if target changed mid-read.
        row.update(collection_seconds=time.monotonic()-started, observer_cpu_seconds=time.process_time()-cpu)
        require(len(json.dumps(row).encode()) <= MAX_RECORD, 'RECORD_BOUND')
        return row

    def close(self):
        for name in ['proc_fd', 'group_fd']:
            fd = getattr(self, name)
            if fd is not None:
                os.close(fd)
                setattr(self, name, None)


def execute(plan, observer, first_sample=None):
    # Buffered in memory, then one final write/fsync; no per-sample disk load.
    output = Path(plan['output'])
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    observer.output_created = True
    stream = os.fdopen(fd, 'wb')
    started, cpu, rows, size = time.monotonic(), time.process_time(), [], 0
    report = {'schema': 'crg-vendor-thread-observer-report-v1', 'phase': 'incomplete',
              'plan': plan, 'process_and_cgroup_identity_pinned': True,
              'sample_period_seconds': 1, 'maximum_threads': MAX_THREADS,
              'maximum_seconds': MAX_SECONDS, 'maximum_report_bytes': MAX_REPORT,
              'started_epoch': time.time(), 'samples': rows, 'target_signals_or_control_writes': 0}
    try:
        for index in range(plan['duration_seconds']+1):
            delay = started + index - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            row = observer.snapshot()
            encoded_size = len(json.dumps(row).encode())
            require(size + encoded_size < MAX_REPORT - 65536, 'REPORT_BOUND')
            rows.append(row)
            size += encoded_size
            if len(rows) == 1 and first_sample is not None:
                first_sample(row)
        report['phase'] = 'observed'
    except (OSError, Rejected, UnicodeError) as error:
        report['reason'] = str(error) if isinstance(error, Rejected) else type(error).__name__
    except KeyboardInterrupt:
        report['reason'] = 'observer-interrupted'
    finally:
        try:
            report.update(ended_epoch=time.time(), elapsed_seconds=time.monotonic()-started,
                          observer_cpu_seconds=time.process_time()-cpu, sample_count=len(rows),
                          maximum_collection_seconds=max([r['collection_seconds'] for r in rows], default=None))
            raw = (json.dumps(report, separators=(',', ':'))+'\n').encode()
            require(len(raw) <= MAX_REPORT, 'FINAL_REPORT_BOUND')
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            report['phase'] = 'report-write-failed'
            raise
        finally:
            stream.close()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    observer = None
    try:
        require(sys.platform == 'linux', 'LINUX_ONLY')
        plan = checked_plan(args.plan, args.plan_sha256)
        observer = Observer(plan)
        if not args.execute:
            print(json.dumps({'phase': 'ready', 'executed': False, 'output_created': False}))
            return 0
        require(os.environ.get('CRG_THREAD_OBSERVER') == 'authorized-disposable-loopback-only', 'EXPLICIT_LAB_MARKER')
        def interrupted(signum, frame):
            raise KeyboardInterrupt()
        for signum in [signal.SIGTERM, signal.SIGINT, signal.SIGALRM]:
            signal.signal(signum, interrupted)
        signal.alarm(plan['duration_seconds'] + 15)
        report = execute(plan, observer, lambda row: print(json.dumps({'phase':'observing', 'sample_count':1, 'epoch':row['epoch']}), flush=True))
        print(json.dumps({key: report[key] for key in ['phase', 'sample_count', 'elapsed_seconds', 'observer_cpu_seconds']}))
        return 0 if report['phase'] == 'observed' else 2
    except (OSError, Rejected, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'phase': 'rejected', 'reason': str(error) if isinstance(error, Rejected) else type(error).__name__,
                          'executed': bool(observer and observer.output_created)}))
        return 1
    finally:
        if sys.platform == 'linux':
            signal.alarm(0)
        if observer is not None:
            observer.close()


if __name__ == '__main__':
    raise SystemExit(main())
