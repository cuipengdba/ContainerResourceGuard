#!/usr/bin/env python3
"""Test-only, pidfd-bound final flush of one identified native load worker.

Used only AFTER a business failure is fixed as the primary outcome. Never sends
signals to DBS, PostgreSQL, API, Agents, process groups, or a whole cgroup.
The cleanup deadline is not extra accepted business time. No forced kill.
"""
import hashlib
import os
from pathlib import Path
import re
import select
import signal
import time


class Rejected(Exception):
    pass


def require(value, reason):
    if not value:
        raise Rejected(reason)


def bounded(path, maximum):
    with Path(path).open('rb') as stream:
        raw = stream.read(maximum + 1)
    require(len(raw) <= maximum, 'NATIVE_SESSION_READ_BOUND')
    return raw


def source_digest(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        raw = stream.read(65537)
    require(len(raw) <= 65536, 'NATIVE_SESSION_SOURCE_BOUND')
    return hashlib.sha256(raw).hexdigest()


class Session:
    def __init__(self, group, entry, run_id, seconds, worker_sha256, record):
        self.group = Path(group)
        self.entry, self.run_id, self.seconds = str(entry), run_id, seconds
        self.worker_sha, self.record = worker_sha256, record
        self.pidfd, self.identity = None, None
        require(self.group.is_dir() and not self.group.is_symlink()
                and str(self.group.resolve()).startswith('/sys/fs/cgroup/'), 'NATIVE_SESSION_GROUP')
        require(re.fullmatch(r'[0-9]{1,24}', run_id) and type(seconds) is int and 1 <= seconds <= 900
                and re.fullmatch(r'[0-9a-f]{64}', worker_sha256), 'NATIVE_SESSION_CONTRACT')
        path = Path(self.entry)
        require(path.is_absolute() and len(self.entry)<=512 and '..' not in path.parts and path.suffix == '.py'
                and (str(path).startswith('/tmp/crg-') or str(path).startswith('/var/tmp/crg-')), 'NATIVE_SESSION_ENTRY')
        self.expected = [self.entry, '--run-id', run_id, '--seconds', str(seconds), '--test-phase', 'smoke']
        self.record.update(phase='not-attached', run_id=run_id, requested_seconds=seconds,
                           worker_sha256=worker_sha256, signals_sent=0,
                           signal_scope='one exact native test worker only', forced_kill=False,
                           oversized_unrelated_argv_ignored=0,
                           complete600s_accepted=False)

    def snapshot(self, pid):
        proc = Path('/proc', str(pid))
        try:
            # An unrelated process (e.g. SSH python -c) can have a huge argv.
            # Such argv cannot equal our <=512-byte entry and seven fixed args.
            # Bound the read and skip it without weakening exact worker binding.
            with (proc/'cmdline').open('rb') as stream:
                command = stream.read(8193)
            if len(command)>8192:
                self.record['oversized_unrelated_argv_ignored']+=1
                return None
            args = command.split(b'\0')
            if args and args[-1] == b'':
                args.pop()
            if len(args) != len(self.expected)+1 or args[1:] != [os.fsencode(v) for v in self.expected]:
                return None
            if re.fullmatch(rb'python(?:[23](?:\.[0-9]+)?)?', os.path.basename(args[0])) is None:
                return None
            membership = bounded(proc/'cgroup', 65536).decode().splitlines()
            if len(membership) != 1 or not membership[0].startswith('0::/'):
                return None
            group = Path('/sys/fs/cgroup')/membership[0][3:].lstrip('/')
            if group != self.group:
                return None
            stat = bounded(proc/'stat', 8192).decode().rsplit(')', 1)[1].split()
            if stat[0] in ['Z', 'X']:
                return None
            source = proc/'root'/self.entry.lstrip('/')
            require(source_digest(source) == self.worker_sha, 'NATIVE_SESSION_SOURCE_IDENTITY')
            return {'pid': pid, 'start_ticks': int(stat[19]), 'cgroup': str(self.group),
                    'entry': self.entry, 'worker_sha256': self.worker_sha,
                    'executable_sha256': hashlib.sha256(bounded(proc/'exe', 128*1024*1024)).hexdigest(),
                    'argv_sha256': hashlib.sha256(b'\0'.join(args)).hexdigest()}
        except (FileNotFoundError, ProcessLookupError):
            return None

    def attach(self):
        require(self.pidfd is None and self.identity is None, 'NATIVE_SESSION_ALREADY_ATTACHED')
        pids = bounded(self.group/'cgroup.procs', 65536).decode().splitlines()
        require(len(pids) <= 4096 and all(v.isdecimal() for v in pids), 'NATIVE_SESSION_PROCESS_BOUND')
        candidates = [value for value in (self.snapshot(int(v)) for v in pids) if value is not None]
        require(len(candidates) == 1, 'NATIVE_SESSION_UNIQUE_WORKER')
        identity = candidates[0]
        fd = os.pidfd_open(identity['pid'])
        try:
            require(self.snapshot(identity['pid']) == identity, 'NATIVE_SESSION_ATTACH_RACE')
        except BaseException:
            os.close(fd)
            raise
        self.pidfd, self.identity = fd, identity
        self.record.update(phase='attached', identity=identity.copy(), pidfd_used=True, attached_epoch=time.time())
        return identity.copy()

    def exited(self):
        require(self.pidfd is not None, 'NATIVE_SESSION_NOT_ATTACHED')
        return bool(select.select([self.pidfd], [], [], 0)[0])

    def signal_term(self):
        require(self.pidfd is not None and self.identity is not None
                and not self.exited() and self.snapshot(self.identity['pid']) == self.identity,
                'NATIVE_SESSION_SIGNAL_IDENTITY')
        signal.pidfd_send_signal(self.pidfd, signal.SIGTERM)
        self.record.update(term_requested_epoch=time.time(), signals_sent=self.record['signals_sent']+1)

    def finish_after_failure(self, business_error, timeout=120):
        require(isinstance(business_error, BaseException), 'NATIVE_SESSION_REQUIRES_BUSINESS_FAILURE')
        require(type(timeout) in [int, float] and 0 < timeout <= 120, 'NATIVE_SESSION_CLEANUP_BOUND')
        require(self.pidfd is not None, 'NATIVE_SESSION_NOT_ATTACHED')
        began = time.monotonic()
        self.record.update(phase='finishing-after-business-failure', business_error_class=type(business_error).__name__,
                           cleanup_started_epoch=time.time(), cleanup_budget_seconds=timeout)
        try:
            if not self.exited():
                self.signal_term()
            deadline = began + timeout
            while not self.exited():
                remaining = deadline-time.monotonic()
                require(remaining > 0, 'NATIVE_SESSION_FINAL_FLUSH_TIMEOUT')
                select.select([self.pidfd], [], [], min(.1, remaining))
            self.record.update(phase='worker-exited', original_worker_exited=True,
                               worker_exit_code_unknown=True, cleanup_ended_epoch=time.time())
        except BaseException as error:
            self.record.update(phase='failed', reason=str(error) if isinstance(error, Rejected) else type(error).__name__)
            raise
        finally:
            self.record['cleanup_elapsed_seconds'] = time.monotonic()-began

    def close(self):
        if self.pidfd is not None:
            os.close(self.pidfd)
            self.pidfd = None
