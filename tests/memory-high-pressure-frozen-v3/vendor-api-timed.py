from __future__ import print_function, division

"""One loopback-only diagnostic request; Python 2/3, no response data logged."""
import time
entered_epoch = time.time()
import ctypes
import json
import sys
try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen

if hasattr(time, 'monotonic'):
    monotonic = time.monotonic
else:
    class Timespec(ctypes.Structure):
        _fields_ = [('seconds', ctypes.c_long), ('nanoseconds', ctypes.c_long)]
    libc = ctypes.CDLL(None, use_errno=True)
    def monotonic():
        value = Timespec()
        if libc.clock_gettime(1, ctypes.byref(value)) != 0:
            raise RuntimeError('monotonic clock unavailable')
        return value.seconds + value.nanoseconds / 1e9

started = monotonic()
result = {'schema': 'crg-inner-api-timing-v1', 'python_entered_epoch': entered_epoch,
          'request_started_monotonic': started, 'request_started_epoch': time.time(),
          'request_ok': False}
try:
    response = urlopen(Request('http://127.0.0.1:8090/test', data=b'{}',
                       headers={'Content-Type': 'application/json'}), timeout=5)
    try:
        status = response.getcode()
        value = json.loads(response.read(1024))
    finally:
        response.close()
    result['request_ok'] = status == 200 and value.get('Result') == '000'
except Exception as error:
    # Only the class, never URL credentials, response body or arbitrary text.
    result['failure_class'] = type(error).__name__
finally:
    result['request_finished_monotonic'] = monotonic()
    result['request_seconds'] = result['request_finished_monotonic'] - started
    result['python_finished_epoch'] = time.time()
    result['pre_request_wall_seconds'] = result['request_started_epoch'] - entered_epoch
print(json.dumps(result))
raise SystemExit(0 if result['request_ok'] else 1)
