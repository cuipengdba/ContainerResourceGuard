#!/usr/bin/env python3
"""Host-only lifecycle for one frozen, read-only diagnostic observer child.

Never manages a product Agent or signals the observed target. A collected report
is evidence, not a claim that its full duration or business acceptance passed.
"""
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import stat
import subprocess
import sys
import time

OBSERVER_SHA = '0fa377189ded92e2b5a9e182871e0494c8af4bc73920b8eb25d03ba9937995c6'
MAX_REPORT = 8 * 1024 * 1024


class Rejected(Exception):
    pass


def require(value, reason):
    if not value:
        raise Rejected(reason)


def bounded(path, maximum):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        pieces, size = [], 0
        while size <= maximum:
            chunk = os.read(fd, min(8192, maximum + 1 - size))
            if not chunk:
                break
            pieces.append(chunk)
            size += len(chunk)
        require(size <= maximum, 'DEVICE_SESSION_READ_BOUND')
        return b''.join(pieces)
    finally:
        os.close(fd)


def instance(pid):
    fields = bounded('/proc/%d/stat' % pid, 4096).rsplit(b')', 1)[1].split()
    return int(fields[19]), fields[0].decode('ascii')


def finish_preserving_business(work, finish, record_error):
    try:
        result = work()
    except BaseException:
        try:
            finish()
        except BaseException as error:
            try:
                record_error(error)
            except BaseException:
                pass
        raise
    finish()
    return result


class Session:
    def __init__(self, source, root, label, record):
        self.source, self.root, self.label, self.record = Path(source), Path(root), label, record
        self.child, self.pidfd, self.ticks = None, None, None
        self.started, self.reaped, self.handshake = False, False, False
        self.stdout_buffer = b''
        self.record.update(phase='not-started', target_signals_or_control_writes=0,
                           owned_observer_TERM_count=0, owned_observer_KILL_count=0)

    def owns_child(self):
        if self.child is None or self.ticks is None or self.reaped:
            return False
        try:
            ticks, state = instance(self.child.pid)
            argv = bounded('/proc/%d/cmdline' % self.child.pid, 8192).split(b'\0')
            return ticks == self.ticks and state not in ['X', 'Z'] and os.fsencode(self.source) in argv
        except (FileNotFoundError, ProcessLookupError):
            return False

    def signal_child(self, number):
        require(number in [signal.SIGTERM, signal.SIGKILL] and self.pidfd is not None
                and self.owns_child(), 'DEVICE_SESSION_SIGNAL_IDENTITY')
        signal.pidfd_send_signal(self.pidfd, number)
        key = 'owned_observer_TERM_count' if number == signal.SIGTERM else 'owned_observer_KILL_count'
        self.record[key] += 1

    def _first_line(self, seconds):
        # readline after select can block forever on a short unterminated line.
        deadline, pieces = time.monotonic() + seconds, b''
        while True:
            remaining = deadline - time.monotonic()
            require(remaining > 0 and select.select([self.child.stdout], [], [], remaining)[0],
                    'DEVICE_SESSION_START_15S')
            chunk = os.read(self.child.stdout.fileno(), 4097 - len(pieces))
            require(chunk, 'DEVICE_SESSION_START_EOF')
            pieces += chunk
            require(len(pieces) <= 4096, 'DEVICE_SESSION_HANDSHAKE_BOUND')
            if b'\n' in pieces:
                line, self.stdout_buffer = pieces.split(b'\n', 1)
                return json.loads(line)

    def start(self, target, group, devices, duration=900):
        require(not self.started, 'DEVICE_SESSION_SINGLE_START')
        self.started = True
        try:
            require(sys.platform == 'linux' and hasattr(os, 'pidfd_open')
                    and hasattr(signal, 'pidfd_send_signal'), 'DEVICE_SESSION_PIDFD_REQUIRED')
            # Refuse an unsupported kernel before creating any child.
            descriptor = os.pidfd_open(os.getpid(), 0)
            os.close(descriptor)
            require(self.source.is_absolute() and self.source == self.source.resolve()
                    and hashlib.sha256(bounded(self.source, 65536)).hexdigest() == OBSERVER_SHA,
                    'DEVICE_SESSION_FROZEN_SOURCE')
            require(self.root.is_absolute() and str(self.root).startswith('/var/tmp/crg-')
                    and '..' not in self.root.parts and self.root == self.root.resolve()
                    and self.root.is_dir(), 'DEVICE_SESSION_PRIVATE_ROOT')
            info = self.root.stat()
            require(info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o700,
                    'DEVICE_SESSION_PRIVATE_ROOT')
            require(self.label in ['dbs', 'hisdbs', 'selftest'], 'DEVICE_SESSION_LABEL')
            require(type(duration) is int and 1 <= duration <= 900, 'DEVICE_SESSION_DURATION')
            require(type(target) is dict and set(target) == {'pid', 'start_ticks'}
                    and all(type(target[k]) is int and 0 < target[k] < 2**64 for k in target),
                    'DEVICE_SESSION_TARGET')
            group = Path(group)
            require(group.is_absolute() and group == group.resolve()
                    and (str(group) == '/sys/fs/cgroup' or str(group).startswith('/sys/fs/cgroup/'))
                    and '..' not in group.parts, 'DEVICE_SESSION_GROUP')
            info = group.stat()
            # The observer independently checks every device/target/boot before
            # and after a sample. This host does not select or benchmark devices.
            self.plan = {'schema': 'crg-device-state-observer-plan-v1', 'observer_sha256': OBSERVER_SHA,
                         'label': self.label, 'pid': target['pid'], 'start_ticks': target['start_ticks'],
                         'cgroup': str(group), 'cgroup_identity': [info.st_dev, info.st_ino],
                         'boot_id': bounded('/proc/sys/kernel/random/boot_id', 128).decode('ascii').strip(),
                         'devices': json.loads(json.dumps(devices)), 'duration_seconds': duration,
                         'output': str(self.root/(self.label+'-devices.json'))}
            require(not os.path.lexists(self.plan['output']), 'DEVICE_SESSION_FRESH_REPORT')
            raw = (json.dumps(self.plan, sort_keys=True, separators=(',', ':'))+'\n').encode('ascii')
            require(len(raw) <= 16384, 'DEVICE_SESSION_PLAN_BOUND')
            planpath = self.root/(self.label+'-device-plan.json')
            fd = os.open(planpath, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            self.record.update(phase='starting', plan=self.plan, plan_sha256=hashlib.sha256(raw).hexdigest(),
                               launch_epoch=time.time())
            self.launch_mono = time.monotonic()
            self.child = subprocess.Popen([sys.executable, str(self.source), '--plan', str(planpath),
                                           '--plan-sha256', self.record['plan_sha256'], '--execute'],
                                          stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                          env=dict(os.environ, CRG_DEVICE_OBSERVER='authorized-disposable-readonly-only',
                                                   PYTHONDONTWRITEBYTECODE='1'), bufsize=0, close_fds=True)
            self.ticks = instance(self.child.pid)[0]
            self.record.update(observer_pid=self.child.pid, observer_start_ticks=self.ticks, observer_entry=str(self.source))
            self.pidfd = os.pidfd_open(self.child.pid, 0)
            self.record['pidfd_used'] = True
            require(self.owns_child(), 'DEVICE_SESSION_CHILD_INSTANCE')
            event = self._first_line(15)
            require(event.get('phase') == 'observing' and event.get('sample_count') == 1,
                    'DEVICE_SESSION_FIRST_SAMPLE')
            self.handshake = True
            self.record.update(phase='observing', first_sample_handshake=event,
                               startup_until_first_sample_seconds=time.monotonic()-self.launch_mono)
        except BaseException as error:
            self.record.update(phase='start-failed', start_error=str(error) if isinstance(error, Rejected) else type(error).__name__)
            try:
                self.stop()
            except BaseException as cleanup_error:
                self.record['start_cleanup_error'] = (str(cleanup_error) if isinstance(cleanup_error, Rejected)
                                                       else type(cleanup_error).__name__)
            raise

    def reap(self, seconds):
        deadline = time.monotonic() + seconds
        while True:
            pid, status, usage = os.wait4(self.child.pid, os.WNOHANG)
            if pid:
                self.reaped = True
                self.child.returncode = os.waitstatus_to_exitcode(status)
                self.record.update(exit=self.child.returncode, whole_child_cpu_seconds=usage.ru_utime+usage.ru_stime,
                                   whole_child_maximum_rss_kib=usage.ru_maxrss,
                                   whole_child_block_input_units=usage.ru_inblock,
                                   whole_child_block_output_units=usage.ru_oublock,
                                   observer_original_instance_gone=True)
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(.02)

    def collect(self):
        require(self.handshake and not self.record['owned_observer_KILL_count'], 'DEVICE_SESSION_NO_VALID_HANDSHAKE_OR_KILLED')
        tail = self.stdout_buffer + self.child.stdout.read(8193)
        stderr = self.child.stderr.read(4097)
        require(len(tail) <= 8192 and len(stderr) <= 4096, 'DEVICE_SESSION_CHILD_OUTPUT_BOUND')
        self.record['terminal_stdout'] = tail.decode('ascii', 'strict')
        require(not stderr, 'DEVICE_SESSION_STDERR')
        output = Path(self.plan['output'])
        info = output.lstat()
        require(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600 and info.st_uid == os.geteuid(),
                'DEVICE_SESSION_REPORT_MODE')
        raw = bounded(output, MAX_REPORT)
        data = json.loads(raw)
        # Retain evidence identity even when a later binding check rejects it.
        self.record.update(raw_report_path=str(output), raw_report_bytes=len(raw),
                           raw_report_sha256=hashlib.sha256(raw).hexdigest(), report_phase=data.get('phase'),
                           report_reason=data.get('reason'))
        require(data.get('schema') == 'crg-device-state-observer-report-v1' and data.get('plan') == self.plan
                and data.get('block_device_opens_signals_and_control_writes') == 0
                and data.get('sample_count') == len(data.get('samples', [])), 'DEVICE_SESSION_REPORT_BINDING')
        rows = data['samples']
        require(1 <= len(rows) <= self.plan['duration_seconds']+1
                and all(r['process']['pid'] == self.plan['pid'] and r['process']['start_ticks'] == self.plan['start_ticks'] for r in rows),
                'DEVICE_SESSION_SAMPLE_BINDING')
        gaps = [b['monotonic']-a['monotonic'] for a, b in zip(rows, rows[1:])]
        require(all(g >= 0 for g in gaps), 'DEVICE_SESSION_MONOTONIC_ORDER')
        observed = data['phase'] == 'observed' and self.child.returncode == 0 and len(rows) == self.plan['duration_seconds']+1
        partial = data['phase'] == 'incomplete' and self.child.returncode == 2
        require(observed or partial, 'DEVICE_SESSION_TERMINAL_BINDING')
        self.record.update(phase='collected', full_duration_observed=observed,
                           sample_count=len(rows), first_sample_epoch=rows[0]['epoch'], last_sample_epoch=rows[-1]['epoch'],
                           maximum_sample_gap_seconds=max(gaps, default=None),
                           sampling_cpu_seconds=data['observer_cpu_seconds'], sampling_elapsed_seconds=data['elapsed_seconds'],
                           maximum_collection_seconds=data['maximum_collection_seconds'],
                           device_available_sample_counts={name: sum(r['devices'][name]['available'] for r in rows)
                                                          for name in rows[0]['devices']},
                           cgroup_file_available_sample_counts={name: sum(r['cgroup'][name]['available'] for r in rows)
                                                               for name in rows[0]['cgroup']},
                           missing_values_are_unknown=True, device_layers_must_not_be_added=True,
                           stable_or_business_acceptance_proven=False)

    def stop(self):
        if self.child is None or self.reaped:
            return
        began = time.monotonic()
        try:
            # A rejected first event/EOF is normally followed immediately by
            # natural exit. Give it one bounded second before any signal.
            if not self.reap(0 if self.handshake else 1):
                if self.owns_child():
                    try:
                        self.signal_child(signal.SIGTERM)
                        self.record['term_requested_epoch'] = time.time()
                    except ProcessLookupError:
                        # Natural exit may race the pidfd signal. Still reap
                        # the original child and retain its exact accounting.
                        pass
                if not self.reap(15):
                    self.signal_child(signal.SIGKILL)
                    require(self.reap(5), 'DEVICE_SESSION_CHILD_NOT_REAPED')
            self.record.update(stop_and_final_flush_seconds=time.monotonic()-began,
                               whole_child_wall_seconds=time.monotonic()-self.launch_mono)
            self.collect()
        except BaseException as error:
            self.record.update(phase='diagnostic-failed', diagnostic_error=str(error) if isinstance(error, Rejected) else type(error).__name__)
            raise
        finally:
            if self.reaped:
                if self.pidfd is not None:
                    os.close(self.pidfd)
                    self.pidfd = None
                self.child.stdout.close()
                self.child.stderr.close()
