from __future__ import print_function
"""Bounded error metadata for future disposable read-only proc diagnostics.

No exception message, filename, stack content, register or arbitrary class name
is returned. This module does not alter any previously frozen sampler.
"""
import errno
import os

try:
    INTEGER_TYPES = (int, long)
except NameError:
    INTEGER_TYPES = (int,)

CLASSES = ('OSError', 'IOError', 'PermissionError', 'FileNotFoundError',
           'ProcessLookupError', 'BlockingIOError', 'InterruptedError')


def metadata(error, stage):
    if stage not in ('open', 'read', 'close'):
        raise ValueError('PROC_ERROR_STAGE')
    name = type(error).__name__
    number = getattr(error, 'errno', None)
    if not isinstance(number, INTEGER_TYPES) or isinstance(number, bool) or not 0 < number < 4096:
        number = None
    return {'available': False, 'reason': name if name in CLASSES else 'unavailable',
            'stage': stage, 'errno': number,
            'errno_name': errno.errorcode.get(number, 'UNKNOWN_ERRNO') if number is not None else None,
            'exception_messages_filenames_or_stack_contents_recorded': False}


def self_stack():
    if os.environ.get('CRG_PROC_ERROR_CHECKS') != 'authorized-disposable-readonly-only':
        raise ValueError('PROC_ERROR_LAB_MARKER')
    directory = descriptor = None
    stage = 'open'
    try:
        # Numeric own PID avoids following /proc/self; there is no target-PID API.
        directory = os.open('/proc/'+str(os.getpid()), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptor = os.open('/proc/'+str(os.getpid())+'/stack', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        stage = 'read'
        count = 0
        while count <= 4096:
            data = os.read(descriptor, min(1024, 4097-count))
            if not data:
                break
            count += len(data)
        if count > 4096:
            return {'available': False, 'reason': 'READ_BOUND', 'stage': 'read',
                    'errno': None, 'errno_name': None, 'raw_stack_recorded': False}
        return {'available': True, 'bytes': count, 'raw_stack_recorded': False}
    except (OSError, IOError) as error:
        return metadata(error, stage)
    finally:
        for fd in (descriptor, directory):
            if fd is not None:
                os.close(fd)
