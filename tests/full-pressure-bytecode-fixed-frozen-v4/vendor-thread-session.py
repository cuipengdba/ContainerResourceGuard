#!/usr/bin/env python3
"""Test-only ownership and lifecycle for the frozen read-only thread observer.

Never signals the observed process. wait4 accounts for this child alone, including
startup hashing and final report writing; sampling CPU remains a separate value.
"""
import collections
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import time

MAX_REPORT = 32 * 1024 * 1024


class Rejected(Exception):
    pass


def require(value, reason):
    if not value:
        raise Rejected(reason)


def bounded(path, maximum):
    with Path(path).open('rb') as stream:
        raw = stream.read(maximum + 1)
    require(len(raw) <= maximum, 'SESSION_READ_BOUND')
    return raw


def instance(pid):
    parts = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()
    return int(parts[19]), parts[0]


def listener_owner(group):
    """Find a unique 8090 LISTEN socket owner in this cgroup, without argv."""
    candidates = []
    pids = bounded(Path(group)/'cgroup.procs', 65536).decode().splitlines()
    require(len(pids) <= 4096, 'LISTENER_PROCESS_BOUND')
    for value in pids:
        try:
            proc = Path('/proc', value)
            tcp = bounded(proc/'net/tcp', 1024 * 1024).decode().splitlines()[1:]
            inodes = {row.split()[9] for row in tcp
                      if row.split()[1].endswith(':1F9A') and row.split()[3] == '0A'}
            fds = list((proc/'fd').iterdir())
            require(len(fds) <= 256, 'LISTENER_FD_BOUND')
            owns = False
            for fd in fds:
                try:
                    link = os.readlink(fd)
                    owns |= link.startswith('socket:[') and link[8:-1] in inodes
                except FileNotFoundError:
                    continue
            if owns:
                candidates.append(int(value))
        except (FileNotFoundError, ProcessLookupError):
            continue
    require(len(candidates) == 1, 'UNIQUE_OWN_8090_LISTENER')
    pid = candidates[0]
    ticks, state = instance(pid)
    require(state not in ['Z', 'X'], 'LISTENER_GONE')
    return {'pid': pid, 'start_ticks': ticks,
            'executable_sha256': hashlib.sha256(bounded(Path('/proc', str(pid), 'exe'), 128*1024*1024)).hexdigest(),
            'executable_path': os.readlink(Path('/proc', str(pid), 'exe'))}


def preserve_business_error(work, finish, record_error):
    try:
        result = work()
    except BaseException:
        try:
            finish()
        except BaseException as error:
            # Even a diagnostic save failure must not replace the first error.
            try:
                record_error(error)
            except BaseException:
                pass
        raise
    finish()
    return result


class Session:
    def __init__(self, source, source_sha256, root, label, record):
        self.source, self.source_sha = Path(source), source_sha256
        self.root, self.label, self.record = Path(root), label, record
        self.child, self.pidfd, self.stderr, self.ticks = None, None, None, None
        self.reaped = False
        self.record.update(phase='not-started', target_signals_or_control_writes=0)

    def owns_child(self):
        try:
            ticks, state = instance(self.child.pid)
            args = bounded(Path('/proc', str(self.child.pid), 'cmdline'), 8192).split(b'\0')
            return ticks == self.ticks and state not in ['Z', 'X'] and os.fsencode(self.source) in args
        except (FileNotFoundError, ProcessLookupError):
            return False

    def start(self, target, group, duration=900):
        require(self.child is None and hashlib.sha256(self.source.read_bytes()).hexdigest() == self.source_sha, 'SESSION_FROZEN_SOURCE')
        plan = {'schema': 'crg-vendor-thread-observer-plan-v1', 'observer_sha256': self.source_sha,
                'label': self.label, 'pid': target['pid'], 'start_ticks': target['start_ticks'],
                'executable_sha256': target['executable_sha256'], 'cgroup': str(group),
                'duration_seconds': duration, 'output': str(self.root/(self.label+'-threads.json'))}
        planpath = self.root/(self.label+'-thread-plan.json')
        raw = (json.dumps(plan, sort_keys=True)+'\n').encode()
        with planpath.open('xb') as stream:
            os.chmod(planpath, 0o600)
            stream.write(raw)
        self.plan = plan
        self.record.update(phase='starting', plan=plan, plan_sha256=hashlib.sha256(raw).hexdigest(),
                           listener_executable_path=target.get('executable_path'), launch_epoch=time.time())
        self.stderr = (self.root/(self.label+'-thread-stderr.log')).open('xb')
        self.stderr_path = Path(self.stderr.name)
        os.chmod(self.stderr_path, 0o600)
        self.launch_mono = time.monotonic()
        self.child = subprocess.Popen(['python3', str(self.source), '--plan', str(planpath), '--plan-sha256', self.record['plan_sha256'], '--execute'],
                                      stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=self.stderr,
                                      env=dict(os.environ, CRG_THREAD_OBSERVER='authorized-disposable-loopback-only'), bufsize=0)
        self.ticks = instance(self.child.pid)[0]
        self.pidfd = os.pidfd_open(self.child.pid)
        self.record.update(observer_pid=self.child.pid, observer_start_ticks=self.ticks, observer_entry=str(self.source), pidfd_used=True)
        require(self.owns_child(), 'SESSION_CHILD_INSTANCE')
        ready, _, _ = select.select([self.child.stdout], [], [], 15)
        require(ready, 'SESSION_START_15S')
        # The frozen observer writes one short, flushed JSON line only after the
        # first complete sample. No signal is sent before this handshake.
        line = self.child.stdout.readline(4097)
        require(line.endswith(b'\n') and len(line) <= 4096, 'SESSION_HANDSHAKE_BOUND')
        event = json.loads(line)
        require(event.get('phase') == 'observing' and event.get('sample_count') == 1, 'SESSION_FIRST_SAMPLE')
        self.record.update(phase='observing', first_sample_handshake=event,
                           startup_until_first_sample_seconds=time.monotonic()-self.launch_mono)

    def signal_child(self, signum):
        require(self.pidfd is not None and self.owns_child(), 'SESSION_SIGNAL_IDENTITY')
        signal.pidfd_send_signal(self.pidfd, signum)

    def reap(self, seconds):
        deadline = time.monotonic()+seconds
        while True:
            pid, status, usage = os.wait4(self.child.pid, os.WNOHANG)
            if pid:
                self.reaped = True
                self.child.returncode = os.waitstatus_to_exitcode(status)
                self.record.update(exit=self.child.returncode, whole_child_cpu_seconds=usage.ru_utime+usage.ru_stime,
                                   whole_child_maximum_rss_kib=usage.ru_maxrss, whole_child_block_input_units=usage.ru_inblock,
                                   whole_child_block_output_units=usage.ru_oublock, observer_original_instance_gone=True)
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(.05)

    def stop(self):
        if self.child is None or self.reaped:
            return
        began = time.monotonic()
        try:
            if self.owns_child():
                self.signal_child(signal.SIGTERM)
                self.record['term_requested_epoch'] = time.time()
            if not self.reap(15):
                self.signal_child(signal.SIGKILL)
                self.record['own_observer_forced_kill'] = True
                require(self.reap(5), 'SESSION_CHILD_NOT_REAPED')
            self.record.update(stop_and_final_flush_seconds=time.monotonic()-began,
                               whole_child_wall_seconds=time.monotonic()-self.launch_mono)
            tail = self.child.stdout.read(8193)
            require(len(tail) <= 8192, 'SESSION_STDOUT_BOUND')
            self.record['terminal_stdout'] = tail.decode('utf-8', 'strict')
            self.stderr.close()
            require(self.stderr_path.stat().st_size == 0, 'SESSION_STDERR')
            raw = bounded(self.plan['output'], MAX_REPORT)
            data = json.loads(raw)
            require(data['plan'] == self.plan and data['target_signals_or_control_writes'] == 0
                    and data['process_and_cgroup_identity_pinned'] and data['sample_count'] == len(data['samples']), 'SESSION_REPORT_BINDING')
            accepted = (data['phase'] == 'observed' and self.child.returncode == 0) or (
                data['phase'] == 'incomplete' and data.get('reason') == 'observer-interrupted'
                and self.child.returncode == 2 and 'term_requested_epoch' in self.record)
            require(accepted and not self.record.get('own_observer_forced_kill'), 'SESSION_INCOMPLETE_OR_FORCED')
            rows = data['samples']
            require(rows, 'SESSION_NO_SAMPLES')
            gaps = [b['monotonic']-a['monotonic'] for a, b in zip(rows, rows[1:])]
            availability = {name: sum(r['cgroup'][name]['available'] for r in rows) for name in rows[0]['cgroup']}
            states = collections.Counter(t['stat']['state'] for r in rows for t in r['tasks'])
            self.record.update(phase='collected', raw_report_path=self.plan['output'], raw_report_bytes=len(raw),
                               raw_report_sha256=hashlib.sha256(raw).hexdigest(), report_phase=data['phase'], report_reason=data.get('reason'),
                               sample_count=len(rows), first_sample_epoch=rows[0]['epoch'], last_sample_epoch=rows[-1]['epoch'],
                               maximum_sample_gap_seconds=max(gaps, default=None), sampling_cpu_seconds=data['observer_cpu_seconds'],
                               maximum_collection_seconds=data['maximum_collection_seconds'], sampling_elapsed_seconds=data['elapsed_seconds'],
                               task_races=sum(r['task_races'] for r in rows), truncated_samples=sum(r['tasks_truncated'] for r in rows),
                               maximum_task_count=max(r['task_count'] for r in rows), task_state_counts=dict(states),
                               cgroup_file_available_sample_counts=availability,
                               missing_values_are_unknown=True, full_samples_embedded_in_business_report=False)
        except BaseException as error:
            self.record.update(phase='diagnostic-failed', diagnostic_error=str(error) if isinstance(error, Rejected) else type(error).__name__)
            raise
        finally:
            if self.reaped:
                if self.pidfd is not None:
                    os.close(self.pidfd)
                    self.pidfd = None
                self.child.stdout.close()
                if self.stderr and not self.stderr.closed:
                    self.stderr.close()
