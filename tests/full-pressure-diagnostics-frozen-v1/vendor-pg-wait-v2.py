from __future__ import division, print_function
"""Separately versioned PG stack-error metadata; original sampler stays frozen.

The original run selection, process context, limits and before/after identity
checks remain mandatory. Only stack reads gain open/read/close errno metadata.
"""
import hashlib
import json
import os
import types


def load(filename, digest, name):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        raw = b''
        while len(raw) <= 32768:
            chunk = os.read(fd, min(8192, 32769-len(raw)))
            if not chunk:
                break
            raw += chunk
    finally:
        os.close(fd)
    if len(raw) > 32768 or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('PG_WAIT_V2_FROZEN_SOURCE')
    module = types.ModuleType(name)
    module.__file__ = path
    exec(compile(raw, path, 'exec'), module.__dict__)
    return module


base = load('vendor-pg-wait.py', '09c330fb06f5ebedddbf4fca108c3b7d4e0f74ca97d3e565292b41ad5391ed69', 'pg_wait_v2_frozen_base')
errors = load('vendor-proc-read-error.py', 'cd9653252535bbc0d5100599c89073532c0d40a7b1eeabe74eac8c2950c575ab', 'pg_wait_v2_qualified_errors')
reader, Rejected, reason, require = base.reader, base.Rejected, base.reason, base.require
app_name, selection_sql, selected = base.app_name, base.selection_sql, base.selected
syscall, fd_metadata, readlink, kernel_stack = base.syscall, base.fd_metadata, base.readlink, base.kernel_stack
MAX_TARGET, MAX_SAMPLE = base.MAX_TARGET, base.MAX_SAMPLE


def read_stack(directory):
    descriptor = None
    stage = 'open'
    result = None
    try:
        descriptor = reader.open_at(directory, 'stack', os.O_RDONLY)
        stage = 'read'
        text = reader.read_fd(descriptor, 4096)
        result = kernel_stack(text)
    except (OSError, IOError) as error:
        result = errors.metadata(error, stage)
    except Exception as error:
        result = {'available': False, 'reason': reason(error)}
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except (OSError, IOError) as error:
                if result is None or result.get('available'):
                    result = errors.metadata(error, 'close')
                else:
                    result['close_failed'] = True
    return result


class Sampler(base.Sampler):
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
            result['kernel_stack'] = read_stack(directory)
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
        result = base.Sampler.sample(self, query)
        result['schema'] = 'crg-pg-wait-snapshot-v2'
        return result
