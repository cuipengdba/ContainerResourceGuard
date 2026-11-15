"""Private test-coordinator receipts and bounded read-only Pod inventory retries.

This module is not linked into CRG and never changes Kubernetes or cgroups.
Generated command output is private; publish selected, reviewed evidence only.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import stat
import subprocess
import time
import uuid

STDOUT_LIMIT = 4 * 1024**2
STDERR_LIMIT = 64 * 1024
STORE_LIMIT = 64 * 1024**2


class CommandFailure(RuntimeError):
    def __init__(self, receipt, timed_out=False, exit_code=None):
        super().__init__('test command failed; private receipt=' + str(receipt))
        self.receipt = receipt
        self.timed_out = timed_out
        self.exit_code = exit_code


def private_directory(directory):
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=False, exist_ok=True)
    info = directory.lstat()
    if (not stat.S_ISDIR(info.st_mode) or directory.resolve() != directory
            or info.st_mode & 0o077 or info.st_uid != os.geteuid()):
        raise RuntimeError('real private0700 receipt directory required')
    return directory


def write_file(path, raw):
    descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def encoded(value):
    return value.encode('utf-8', 'replace') if isinstance(value, str) else value or b''


def failure_receipt(directory, command, stdout, stderr, reason, elapsed, exit_code=None):
    directory = private_directory(directory)
    members = list(directory.iterdir())
    if any(not p.is_file() or p.is_symlink() for p in members):
        raise RuntimeError('unexpected member in private receipt directory')
    used = sum(p.stat().st_size for p in members)
    if len(members) + 3 > 512 or used + STDOUT_LIMIT + STDERR_LIMIT + 16384 > STORE_LIMIT:
        raise RuntimeError('private test receipt budget exhausted; refusing progress')
    key = uuid.uuid4().hex
    value = {'schema': 'crg-private-command-failure-v1', 'reason': reason,
             'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'elapsed_seconds': elapsed, 'exit': exit_code,
             'command_sha256': hashlib.sha256(json.dumps([str(x) for x in command]).encode()).hexdigest(),
             'command_kind': str(command[0]), 'outputs': {}}
    for name, content, limit in [('stdout', stdout, STDOUT_LIMIT), ('stderr', stderr, STDERR_LIMIT)]:
        original = encoded(content)
        retained = original[:limit]
        file = directory / (key + '.' + name)
        write_file(file, retained)
        value['outputs'][name] = {'file': file.name, 'original_bytes': len(original),
                                 'retained_bytes': len(retained), 'truncated': len(original) > limit,
                                 'retained_sha256': hashlib.sha256(retained).hexdigest()}
    path = directory / (key + '.json')
    write_file(path, (json.dumps(value, indent=2) + '\n').encode())
    return path


def recorded_run(command, directory, check=True, timeout=60, **kwargs):
    started = time.monotonic()
    if isinstance(kwargs.get('input'), str):
        kwargs['input'] = kwargs['input'].encode('utf-8')
    try:
        result = subprocess.run(command, capture_output=True, timeout=timeout, **kwargs)
    except subprocess.TimeoutExpired as error:
        path = failure_receipt(directory, command, error.stdout, error.stderr, 'timeout',
                               time.monotonic() - started)
        raise CommandFailure(path, timed_out=True) from error
    except OSError as error:
        path = failure_receipt(directory, command, b'', str(error), 'launch-error',
                               time.monotonic() - started)
        raise CommandFailure(path) from error
    result.failure_receipt = None
    if result.returncode:
        result.failure_receipt = failure_receipt(directory, command, result.stdout, result.stderr,
                                                 'nonzero-exit', time.monotonic() - started,
                                                 exit_code=result.returncode)
        if check:
            raise CommandFailure(result.failure_receipt, exit_code=result.returncode)
    result.raw_stdout, result.raw_stderr = result.stdout, result.stderr
    result.stdout = result.stdout.decode('utf-8', 'replace')
    result.stderr = result.stderr.decode('utf-8', 'replace')
    return result


def inventory(stdout, namespace):
    if len(encoded(stdout)) > STDOUT_LIMIT:
        raise ValueError('Pod inventory exceeds retained output limit')
    value = json.loads(stdout)
    if (not isinstance(value, dict) or value.get('kind') not in ['List', 'PodList']
            or value.get('apiVersion') != 'v1' or not isinstance(value.get('items'), list)):
        raise ValueError('complete v1 Pod inventory required; unknown inventory cannot authorize progress')
    blocked = []
    for item in value['items']:
        if not isinstance(item, dict) or item.get('kind') != 'Pod' or item.get('apiVersion') != 'v1':
            raise ValueError('non-Pod inventory member')
        meta = item['metadata']
        if not all(isinstance(meta.get(k), str) and meta[k] for k in ['namespace', 'name', 'uid']):
            raise ValueError('complete Pod identity required')
        if meta['namespace'].startswith('crg-vendor-lab-') and meta['namespace'] != namespace:
            blocked.append({'namespace': meta['namespace'], 'name': meta['name'], 'UID': meta['uid'],
                            'phase': item.get('status', {}).get('phase')})
    return blocked


def exclusive(namespace, directory, kubectl='kubectl', budget_seconds=15, max_attempts=3):
    """Retry failed read-only requests within ONE original15s observation budget.

    A valid nonempty exclusion list returns immediately. Invalid or unknown
    inventory fails immediately. There is no retry of a mutating command.
    """
    if not 0 < budget_seconds <= 15 or not 1 <= max_attempts <= 3:
        raise ValueError('original15s/three-attempt bounds must not be widened')
    directory = private_directory(directory)
    started = time.monotonic()
    deadline = started + budget_seconds
    attempts = []
    for number in range(max_attempts):
        remaining = deadline - time.monotonic()
        if remaining <= .01:
            break
        request_ms = max(1, int(min(10, remaining) * 1000))
        command = [kubectl, 'get', 'pods', '-A', '-o', 'json', '--request-timeout=' + str(request_ms) + 'ms']
        row = {'number': number + 1, 'remaining_budget_seconds': remaining, 'request_timeout_ms': request_ms}
        try:
            result = recorded_run(command, directory, check=False, timeout=remaining)
        except CommandFailure as error:
            row.update(exit=error.exit_code, timed_out=error.timed_out, receipt=Path(error.receipt).name)
            attempts.append(row)
            continue
        row.update(exit=result.returncode, timed_out=False,
                   stdout_sha256=hashlib.sha256(encoded(result.stdout)).hexdigest(),
                   stderr_sha256=hashlib.sha256(encoded(result.stderr)).hexdigest())
        if result.returncode:
            row['receipt'] = result.failure_receipt.name
            attempts.append(row)
            continue
        try:
            blocked = inventory(result.stdout, namespace)
        except (ValueError, KeyError, TypeError) as error:
            path = failure_receipt(directory, command, result.raw_stdout, result.raw_stderr,
                                   'invalid-inventory', time.monotonic() - started, exit_code=0)
            raise CommandFailure(path, exit_code=0) from error
        attempts.append(row)
        elapsed = time.monotonic() - started
        if elapsed >= budget_seconds:
            path = failure_receipt(directory, command, result.raw_stdout, result.raw_stderr,
                                   'valid-response-after-deadline', elapsed, exit_code=0)
            raise CommandFailure(path, timed_out=True, exit_code=0)
        return blocked, {'schema': 'crg-readonly-exclusive-query-v1', 'attempts': attempts,
                         'elapsed_seconds': elapsed, 'budget_seconds': budget_seconds,
                         'blocked': blocked, 'read_only': True}
    raise RuntimeError('read-only inventory unavailable within original budget; attempts=' + json.dumps(attempts))
