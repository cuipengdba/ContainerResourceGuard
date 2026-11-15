#!/usr/bin/env python3
"""Bounded read-only socket ownership snapshot for a prevalidated test PID.

The caller must authorize the target container. No signals, namespace changes,
resource writes, command lines or environment reads. Not an atomic port lock.
"""
import datetime
import os
from pathlib import Path
import re
import time


def identity(pid, proc_root=Path('/proc')):
    p = Path(proc_root) / str(pid)
    fields = (p / 'stat').read_bytes().rsplit(b')', 1)[1].split()
    return {'pid': int(pid), 'start_ticks': int(fields[19]),
            'net_namespace_inode': (p / 'ns/net').stat().st_ino,
            'cgroup_membership': (p / 'cgroup').read_text()}


def collect(expected, ports=(55432, 55433), *, proc_root=Path('/proc'),
            max_seconds=2.0, max_processes=32768, max_fds=65536,
            max_sockets=256, max_table_bytes=1048576):
    """Return partial/unknown on loss of identity, permissions or read bounds.

    Listener/owner observations are interval evidence, never proof a port is
    reserved/free. Shared network namespaces can have owners in another cgroup.
    """
    start = time.monotonic()
    ports = tuple(sorted(set(ports)))
    if (not ports or any(type(p) is not int or not 1 <= p <= 65535 for p in ports)
            or len(ports) > 16 or type(expected.get('pid')) is not int
            or expected['pid'] <= 0 or expected.get('start_ticks', 0) <= 0
            or expected.get('net_namespace_inode', 0) <= 0
            or not expected.get('cgroup_membership')
            or not 0 < max_seconds <= 10
            or any(type(v) is not int or v <= 0 for v in
                   [max_processes, max_fds, max_sockets, max_table_bytes])):
        raise ValueError('invalid target, ports or positive read bounds')
    proc_root = Path(proc_root)
    result = {'schema': 'crg-readonly-port-owners-v1', 'phase': 'partial',
              'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'target': dict(expected), 'ports': list(ports), 'listeners': [],
              'issues': [], 'counts': {'processes': 0, 'fds': 0},
              'atomic_snapshot': False, 'port_availability_claimed': False,
              'target_identity_stable': False}
    class Bound(Exception):
        pass
    def issue(kind):
        if kind not in result['issues']:
            result['issues'].append(kind)
    def deadline():
        if time.monotonic() - start > max_seconds:
            raise Bound('time-budget')
    def same_target():
        return identity(expected['pid'], proc_root) == expected
    try:
        if not same_target():
            raise Bound('target-identity-mismatch-before-read')
        for table in ['tcp', 'tcp6', 'unix']:
            deadline()
            try:
                with (proc_root / str(expected['pid']) / 'net' / table).open('rb') as stream:
                    raw = stream.read(max_table_bytes + 1)
                if len(raw) > max_table_bytes:
                    issue('table-byte-limit-' + table)
                    continue
                for line in raw.decode('ascii').splitlines()[1:]:
                    deadline()
                    fields = line.split()
                    if table == 'unix':
                        if len(fields) < 7:
                            raise ValueError('short unix row')
                        if fields[4] != '0001' or not int(fields[3], 16) & 0x10000:
                            continue
                        path = fields[7] if len(fields) > 7 else ''
                        match = re.search(r'(?:^|/)\.s\.PGSQL\.(\d+)$', path)
                        if match is None or int(match.group(1)) not in ports:
                            continue
                        port, inode = int(match.group(1)), fields[6]
                        endpoint = path
                    else:
                        if len(fields) < 10:
                            raise ValueError('short tcp row')
                        if fields[3] != '0A':
                            continue
                        port = int(fields[1].rsplit(':', 1)[1], 16)
                        if port not in ports:
                            continue
                        inode, endpoint = fields[9], fields[1]
                    if not inode.isdigit() or int(inode) <= 0:
                        raise ValueError('invalid socket inode')
                    if len(result['listeners']) >= max_sockets:
                        raise Bound('listener-count-limit')
                    result['listeners'].append({'table': table, 'port': port,
                                                'inode': inode, 'endpoint': endpoint,
                                                'owners': [], 'owner_resolution': 'unresolved'})
            except (OSError, ValueError, UnicodeError) as error:
                issue('table-unavailable-or-malformed-' + table + '-' + type(error).__name__)
        by_inode = {}
        for row in result['listeners']:
            by_inode.setdefault(row['inode'], []).append(row)
        # Do not inspect any command line or environment, including non-targets.
        if by_inode:
            with os.scandir(proc_root) as processes:
                for entry in processes:
                    deadline()
                    if not entry.name.isdigit():
                        continue
                    result['counts']['processes'] += 1
                    if result['counts']['processes'] > max_processes:
                        raise Bound('process-count-limit')
                    try:
                        before = identity(int(entry.name), proc_root)
                        if before['net_namespace_inode'] != expected['net_namespace_inode']:
                            continue
                        p = proc_root / entry.name
                        matches = {}
                        with os.scandir(p / 'fd') as descriptors:
                            for fd in descriptors:
                                deadline()
                                result['counts']['fds'] += 1
                                if result['counts']['fds'] > max_fds:
                                    raise Bound('fd-count-limit')
                                try:
                                    value = os.readlink(fd.path)
                                except FileNotFoundError:
                                    continue
                                match = re.fullmatch(r'socket:\[(\d+)\]', value)
                                if match is not None and match.group(1) in by_inode:
                                    matches[fd.name] = match.group(1)
                        if matches:
                            command = (p / 'comm').read_text().strip()[:64]
                            try:
                                cwd = os.readlink(p / 'cwd')
                            except OSError:
                                cwd = None
                            stable = identity(int(entry.name), proc_root) == before
                            if not stable:
                                issue('owner-identity-changed')
                                continue
                            for fd, inode in matches.items():
                                try:
                                    if os.readlink(p / 'fd' / fd) != 'socket:[' + inode + ']':
                                        issue('owner-fd-changed')
                                        continue
                                except FileNotFoundError:
                                    issue('owner-fd-disappeared')
                                    continue
                                owner = dict(before, fd=int(fd), comm=command,
                                             cwd_observed=cwd,
                                             same_cgroup=before['cgroup_membership'] == expected['cgroup_membership'])
                                for row in by_inode[inode]:
                                    row['owners'].append(owner)
                                    row['owner_resolution'] = 'observed-stable-owner'
                    except (FileNotFoundError, ProcessLookupError):
                        # Process races can hide a short-lived owner. Keep unknown.
                        issue('process-disappeared-during-scan')
                    except (OSError, ValueError) as error:
                        issue('process-unavailable-' + type(error).__name__)
        result['target_identity_stable'] = same_target()
        if not result['target_identity_stable']:
            issue('target-identity-changed-after-read')
        if any(not row['owners'] for row in result['listeners']):
            issue('listener-owner-unresolved')
    except Bound as error:
        issue(str(error))
    except (OSError, ValueError, IndexError) as error:
        issue('target-unavailable-or-malformed-' + type(error).__name__)
    result['phase'] = 'complete' if result['target_identity_stable'] and not result['issues'] else 'partial'
    result['elapsed_seconds'] = time.monotonic() - start
    return result
