from __future__ import division, print_function
"""Python 2/3 read-only PG/proc metadata for a uniquely tagged test run.

No SQL body, registers, FD contents, signals or control writes are returned.
The caller provides a bounded read-only SELECT callback in the PG PID namespace.
"""
import ctypes
import hashlib
import json
import os
import re
import types

READER_SHA = '0fa377189ded92e2b5a9e182871e0494c8af4bc73920b8eb25d03ba9937995c6'
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor-device-state-observer.py')
with open(path, 'rb') as stream:
    raw = stream.read(65537)
if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != READER_SHA:
    raise ValueError('PG_WAIT_FROZEN_READER')
reader = types.ModuleType('pg_wait_frozen_reader')
reader.__file__ = path
exec(compile(raw, path, 'exec'), reader.__dict__)

MAX_TARGETS, MAX_SAMPLE, MAX_TARGET = 4, 8192, 1900
PGDATA = '/opt/postgresql/pgdata'
PGEXE = '/opt/postgresql/pgsql/bin/postgres'
FD_CALLS = {0: 'read', 1: 'write', 3: 'close', 17: 'pread64', 18: 'pwrite64',
            19: 'readv', 20: 'writev', 74: 'fsync', 75: 'fdatasync', 306: 'syncfs'}


class Rejected(Exception):
    pass


def require(value, reason):
    if not value:
        raise Rejected(reason)


def match(pattern, value):
    return isinstance(value, reader.TEXT) and re.match(pattern+r'\Z', value) is not None


def reason(error):
    if isinstance(error, (Rejected, reader.Rejected)):
        return str(error)
    name = type(error).__name__
    return name if name in ['OSError', 'IOError', 'ValueError', 'UnicodeDecodeError', 'FileNotFoundError', 'ProcessLookupError', 'PermissionError'] else 'unavailable'


def app_name(run):
    require(match(r'[0-9]{8,14}', run), 'PG_WAIT_RUN')
    return 'crg-disposable-soak-'+run


def selection_sql(run):
    app = app_name(run)
    return ("SELECT datname,application_name,pid::text,extract(epoch FROM backend_start)::text,state,wait_event_type,wait_event "
            "FROM pg_stat_activity WHERE datname='postgres' AND application_name='"+app+"' "
            "AND pid<>pg_backend_pid() ORDER BY pid LIMIT 5")


def selected(rows, run):
    require(type(rows) is list and len(rows) <= MAX_TARGETS, 'PG_WAIT_ROW_BOUND_OR_TRUNCATED')
    out, seen = [], set()
    for row in rows:
        require(type(row) is list and len(row) == 7, 'PG_WAIT_COLUMNS')
        require(row[:2] == ['postgres', app_name(run)], 'PG_WAIT_RUN_CONTEXT')
        require(match(r'[0-9]{1,10}', row[2]) and 1 < int(row[2]) < 2**31, 'PG_WAIT_PID')
        require(match(r'[0-9]{1,12}(?:\.[0-9]{1,9})?', row[3]) and float(row[3]) > 0, 'PG_WAIT_BACKEND_START')
        require(row[2] not in seen, 'PG_WAIT_DUPLICATE_PID')
        seen.add(row[2])
        require(row[4] is None or match(r'[A-Za-z ()]{1,80}', row[4]), 'PG_WAIT_STATE')
        require(all(v is None or match(r'[A-Za-z0-9_]{1,80}', v) for v in row[5:]), 'PG_WAIT_LABEL')
        out.append({'pid': int(row[2]), 'backend_start_epoch_text': row[3], 'state': row[4],
                    'wait_event_type': row[5], 'wait_event': row[6]})
    return out


def fd_metadata(value, run):
    deleted = value.endswith(' (deleted)')
    if deleted:
        value = value[:-10]
    if match(r'pipe:\[[0-9]+\]', value):
        return {'kind': 'pipe'}
    if match(r'socket:\[[0-9]+\]', value):
        return {'kind': 'socket'}
    if value.startswith('anon_inode:'):
        return {'kind': 'anonymous-inode'}
    allowed = (PGDATA+'/', '/opt/postgresql/pg_log/', '/opt/postgresql/basebackup/crg-soak-'+run+'/')
    if len(value) <= 512 and match(r'/[A-Za-z0-9_./-]+', value) and '..' not in value.split('/') and '//' not in value and value.startswith(allowed):
        return {'kind': 'allowlisted-path', 'path': value, 'deleted': deleted}
    return {'kind': 'redacted-other-path', 'deleted': deleted}


def syscall(text, abi):
    values = text.split()
    if values == ['running']:
        return {'available': False, 'reason': 'task-running'}
    require(values and match(r'-?[0-9]{1,12}', values[0]), 'PG_WAIT_SYSCALL')
    number = int(values[0])
    if number == -1:
        require(len(values) == 3 and all(match(r'0x[0-9a-fA-F]{1,16}', v) for v in values[1:]), 'PG_WAIT_SYSCALL')
        return {'available': False, 'reason': 'outside-system-call'}
    require(number >= 0 and len(values) == 9 and all(match(r'0x[0-9a-fA-F]{1,16}', v) for v in values[1:]), 'PG_WAIT_SYSCALL')
    result = {'available': True, 'number': number, 'abi': abi, 'operation': 'unknown'}
    if abi == 'linux-x86_64' and number in FD_CALLS:
        result['operation'] = FD_CALLS[number]
        if int(values[1], 16) <= 65535:
            result['fd'] = int(values[1], 16)
    return result


def kernel_stack(text):
    frames, unknown = [], 0
    lines = text.splitlines()
    for line in lines[:32]:
        value = re.match(r'\s*(?:\[<[0-9a-fA-F]+>\]\s*)?([A-Za-z_][A-Za-z0-9_.]{0,95})(?:\+0x[0-9a-fA-F]+/0x[0-9a-fA-F]+)?(?:\s+\[[A-Za-z0-9_]+\])?\s*\Z', line)
        if value:
            if len(frames) < 8:
                frames.append(value.group(1))
        elif line.strip():
            unknown += 1
    return {'available': bool(lines), 'frames': frames, 'unknown_lines': unknown,
            'truncated': len(lines) > 8, 'addresses_and_offsets_recorded': False}


_readlinkat = getattr(ctypes.CDLL(None, use_errno=True), 'readlinkat')
_readlinkat.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t]
_readlinkat.restype = ctypes.c_long


def readlink(directory, name):
    require(match(r'(?:exe|cwd|[0-9]{1,5})', name), 'PG_WAIT_LINK_NAME')
    buffer = ctypes.create_string_buffer(513)
    length = _readlinkat(directory, name.encode('ascii'), buffer, 513)
    if length < 0:
        raise OSError(ctypes.get_errno(), 'READLINKAT_FAILED')
    require(length < 513, 'PG_WAIT_LINK_BOUND')
    return buffer.raw[:length].decode('ascii', 'strict')


class Sampler(object):
    def __init__(self, run):
        require(os.environ.get('CRG_PG_WAIT') == 'authorized-disposable-readonly-only', 'PG_WAIT_LAB_MARKER')
        self.run, self.sql, self.pins = run, selection_sql(run), {}
        self.group = reader.membership(reader.read_path('/proc/self/cgroup', 4096))
        self.boot = reader.read_path('/proc/sys/kernel/random/boot_id', 128).strip()
        require(PGDATA == os.path.realpath(PGDATA) and os.path.isdir(PGDATA), 'PG_WAIT_ACTUAL_DATA_DIRECTORY')
        self.data_identity = reader.identity(os.stat(PGDATA))
        fd = os.open(PGEXE, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            self.executable_identity = reader.identity(os.fstat(fd))
            header = os.read(fd, 20)
        finally:
            os.close(fd)
        require(header[:4] == b'\x7fELF', 'PG_WAIT_EXECUTABLE')
        self.abi = 'linux-x86_64' if len(header) == 20 and header[:6] == b'\x7fELF\x02\x01' and header[18:20] == b'\x3e\x00' else 'unknown'

    def identity(self, directory, expected=None):
        require(reader.read_path('/proc/sys/kernel/random/boot_id', 128).strip() == self.boot, 'PG_WAIT_BOOT_CHANGED')
        require(reader.identity(os.stat(PGDATA)) == self.data_identity and PGDATA == os.path.realpath(PGDATA), 'PG_WAIT_DATA_CHANGED')
        value = reader.process_fields(reader.read_at(directory, 'stat', 4096))
        require(value['state'] not in ['Z', 'X'], 'PG_WAIT_PROCESS_GONE')
        if expected:
            require(all(value[k] == expected[k] for k in ['pid', 'start_ticks']), 'PG_WAIT_PROCESS_CHANGED')
        require(reader.membership(reader.read_at(directory, 'cgroup', 4096)) == self.group, 'PG_WAIT_CGROUP_CHANGED')
        require(readlink(directory, 'cwd') == PGDATA and readlink(directory, 'exe') == PGEXE, 'PG_WAIT_EXE_OR_DATA_CONTEXT')
        require(reader.identity(os.stat('/proc/%d/exe' % value['pid'])) == self.executable_identity, 'PG_WAIT_EXECUTABLE_CHANGED')
        uid = [line.split()[1:] for line in reader.read_at(directory, 'status').splitlines() if line.startswith('Uid:')]
        require(len(uid) == 1 and len(uid[0]) == 4 and all(v == str(os.geteuid()) for v in uid[0]), 'PG_WAIT_UID_CONTEXT')
        return value

    def capture(self, row):
        directory, descriptors = None, None
        try:
            directory = os.open('/proc/%d' % row['pid'], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            process = self.identity(directory)
            require(process['pid'] == row['pid'], 'PG_WAIT_PROCESS_PID')
            key = (row['pid'], row['backend_start_epoch_text'])
            require(key not in self.pins or process['start_ticks'] == self.pins[key], 'PG_WAIT_PROCESS_CHANGED')
            result = {'available': True, 'process': process, 'separate_reads_not_atomic': True}
            try:
                text = reader.read_at(directory, 'syscall', 512)
                call = syscall(text, self.abi)
                result['syscall'] = call
                if 'fd' in call:
                    descriptors = reader.open_at(directory, 'fd', os.O_RDONLY | os.O_DIRECTORY)
                    link = readlink(descriptors, str(call['fd']))
                    result['descriptor'] = fd_metadata(link, self.run)
                    require(readlink(descriptors, str(call['fd'])) == link, 'PG_WAIT_FD_CHANGED')
                require(reader.read_at(directory, 'syscall', 512) == text, 'PG_WAIT_SYSCALL_CHANGED')
            except Exception as error:
                result.update(syscall={'available': False, 'reason': reason(error)}, descriptor={'kind': 'unknown'})
            try:
                result['kernel_stack'] = kernel_stack(reader.read_at(directory, 'stack', 4096))
            except Exception as error:
                result['kernel_stack'] = {'available': False, 'reason': reason(error)}
            self.identity(directory, process)
            require(len(json.dumps(result).encode('ascii')) <= MAX_TARGET, 'PG_WAIT_TARGET_BOUND')
            return result
        except Exception as error:
            return {'available': False, 'reason': reason(error), 'separate_reads_not_atomic': True}
        finally:
            for fd in [descriptors, directory]:
                if fd is not None:
                    os.close(fd)

    def sample(self, query):
        began, cpu = reader.clock(1), reader.clock(3)
        result = {'schema': 'crg-pg-wait-snapshot-v1', 'run_id': self.run, 'started_monotonic': began,
                  'available': False, 'targets': [], 'signals_or_control_writes': 0, 'missing_values_are_unknown': True,
                  'separate_reads_not_atomic': True, 'backend_start_is_not_proc_start_ticks': True}
        try:
            before = selected(query(self.sql, 1), self.run)
            pending = [(row, self.capture(row)) for row in before]
            after = {(r['pid'], r['backend_start_epoch_text']) for r in selected(query(self.sql, 1), self.run)}
            new_pins = {}
            for row, metadata in pending:
                key = (row['pid'], row['backend_start_epoch_text'])
                if key not in after:
                    metadata = {'available': False, 'reason': 'PG_WAIT_BACKEND_CHANGED', 'separate_reads_not_atomic': True}
                elif metadata['available']:
                    fd = None
                    try:
                        fd = os.open('/proc/%d' % row['pid'], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                        self.identity(fd, metadata['process'])
                        new_pins[key] = metadata['process']['start_ticks']
                        metadata['identity_rechecked_after_SQL'] = True
                    except Exception as error:
                        metadata = {'available': False, 'reason': reason(error), 'separate_reads_not_atomic': True}
                    finally:
                        if fd is not None:
                            os.close(fd)
                result['targets'].append(dict(row, kernel_wait=metadata))
            self.pins = new_pins
            result['available'] = True
        except Exception as error:
            result.update(reason=reason(error), targets=[])
            self.pins = {}
        result.update(ended_monotonic=reader.clock(1), collection_seconds=reader.clock(1)-began,
                      observer_thread_cpu_seconds=reader.clock(3)-cpu)
        if len(json.dumps(result).encode('ascii')) > MAX_SAMPLE:
            result.update(available=False, reason='PG_WAIT_SAMPLE_BOUND', targets=[])
        return result
