#!/usr/bin/env python3
"""Host-only real concurrent thread/device sessions; no database workload.

Test-owned workload callbacks exercise success and failure orchestration, never
claim the original two-role/32-check/600-second business gate.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
here = Path(__file__).parent
pins = {'vendor-thread-session.py': '35f65518ce56f5b889c82041a1c45c87d9f3284ab6bd59cc39752bf78fdc8bce',
        'vendor-thread-wait-observer.py': 'c904c1d13b41f7f5c5b517e0dc1aa8348126665fcf8fe97e232a92f2dedf0c02',
        'vendor-thread-wait.py': 'fceb41233f46c869d00f844642b842a35341270cbe37d126ef41685ab1a179f6'}
for name, want in pins.items():
    assert hashlib.sha256((here/name).read_bytes()).hexdigest() == want
def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), here/(name+'.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value
bridge, thread = load('vendor-device-business-session'), load('vendor-thread-session')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, required=True)
    root = parser.parse_args().work_dir
    assert sys.platform == 'linux' and os.environ.get('CRG_DEVICE_BUSINESS_CHECKS') == 'authorized-own-observers-only'
    assert str(root).startswith('/var/tmp/crg-') and '..' not in root.parts and root.parent == root.parent.resolve() and not root.exists()
    os.umask(0o077)
    root.mkdir(mode=0o700)
    target = {'pid': os.getpid(), 'start_ticks': thread.instance(os.getpid())[0],
              'executable_sha256': hashlib.sha256(Path('/proc/self/exe').read_bytes()).hexdigest()}
    group = Path('/sys/fs/cgroup')/Path('/proc/self/cgroup').read_text().strip().split('::')[1].lstrip('/')
    devices = []
    for number in ['253:0', '8:2', '8:0']:
        path = Path('/sys/dev/block', number).resolve()
        info = path.stat()
        devices.append({'major_minor': number, 'sysfs': str(path), 'identity': [info.st_dev, info.st_ino]})
    def controls():
        out = {}
        for name in ['cpu.max', 'memory.max', 'io.max']:
            try:
                out[name] = {'available': True, 'value': (group/name).read_text()}
            except OSError as error:
                out[name] = {'available': False, 'reason': type(error).__name__}
        return out
    before = controls()
    files = [*pins, 'vendor-device-state-observer.py', 'vendor-device-session.py',
             'vendor-device-business-session.py', 'vendor-device-business-session-checks.py']
    report = {'schema': 'crg-device-business-session-qualification-v1', 'phase': 'running', 'checks': [], 'cases': {},
              'source_sha256': {n: hashlib.sha256((here/n).read_bytes()).hexdigest() for n in files},
              'target_signals_or_control_writes': 0, 'new_SQL_API_or_backup_workload': False,
              'scope': 'Host-only concurrent read-only observers plus explicit workload callbacks; not full vendor business acceptance'}
    active = []
    def check(name, value):
        report['checks'].append({'name': name, 'passed': bool(value)})
        assert value, name
    try:
        for name in ['normal', 'device-start-failed', 'business-and-device-failed', 'interval-outside', 'save-failed']:
            folder = root/name
            folder.mkdir(mode=0o700)
            row = {'reload_intervals': []}
            report['cases'][name] = row
            inner = thread.Session(here/'vendor-thread-wait-observer.py', pins['vendor-thread-wait-observer.py'], folder, 'selftest', row.setdefault('thread_observer', {}))
            entry = here/'vendor-device-state-observer.py'
            if name in ['device-start-failed', 'business-and-device-failed']:
                entry = folder/'changed-source.py'
                entry.write_bytes((here/'vendor-device-state-observer.py').read_bytes()+b'\n# wrong fixture\n')
            def save():
                if name == 'save-failed':
                    raise OSError('test-owned-save-failure')
            obj = bridge.Session(inner, entry, folder, 'selftest', devices, row, save)
            active.append(obj)
            obj.start(target, group, 3)
            check(name+'-original-thread-starts-even-when-device-or-save-fails', inner.record['phase'] == 'observing' and inner.owns_child())
            began = time.time()
            row['reload_intervals'].append({'started_epoch': began, 'ended_epoch': began+.05})
            if name == 'interval-outside':
                row['reload_intervals'][0]['started_epoch'] = began-10
            # A valid second sample brackets the test callback's short interval.
            time.sleep(1.25)
            original = RuntimeError('ORIGINAL_TEST_WORK_FAILURE')
            seen, calls = [], []
            def work():
                calls.append('original-work-executed')
                if name == 'business-and-device-failed':
                    raise original
                return 'original-work-result'
            value, failure = None, None
            try:
                value = bridge.device.finish_preserving_business(work, obj.stop, lambda e: seen.append(type(e).__name__))
            except BaseException as error:
                failure = error
            if name == 'normal':
                good = failure is None and value == 'original-work-result' and row['device_observer']['integration_phase'] == 'collected-intervals-covered'
            elif name == 'business-and-device-failed':
                good = failure is original and bool(seen)
            elif name == 'interval-outside':
                good = isinstance(failure, bridge.device.Rejected) and str(failure) == 'DEVICE_BUSINESS_INTERVAL_ENVELOPE'
            elif name == 'save-failed':
                good = isinstance(failure, OSError)
            else:
                good = isinstance(failure, bridge.device.Rejected) and str(failure) == 'DEVICE_SESSION_FROZEN_SOURCE'
            check(name+'-original-result-or-first-error-kept-and-diagnostic-failure-visible', good and calls == ['original-work-executed'])
            check(name+'-both-owned-children-reaped-and-pidfds-closed', inner.reaped and inner.pidfd is None
                  and (obj.device.child is None or (obj.device.reaped and obj.device.pidfd is None))
                  and inner.record['whole_child_maximum_rss_kib'] <= 131072
                  and (obj.device.child is None or row['device_observer']['whole_child_maximum_rss_kib'] <= 131072))
            snapshot = json.dumps(row, sort_keys=True)
            obj.stop()
            check(name+'-stop-idempotent-target-and-controls-unchanged', json.dumps(row, sort_keys=True) == snapshot
                  and thread.instance(target['pid'])[0] == target['start_ticks'] and before == controls())
        report['phase'] = 'passed'
    except BaseException as error:
        report.update(phase='failed', reason_class=type(error).__name__, reason=str(error)[:200])
    finally:
        cleanup = []
        for obj in active:
            try:
                obj.stop()
            except BaseException as error:
                cleanup.append(type(error).__name__)
        report['cleanup_errors'] = cleanup
        report['original_controls_unchanged'] = before == controls()
        report['observer_instances'] = []
        for obj in active:
            for child in [obj.inner, obj.device]:
                if child.child is not None:
                    report['observer_instances'].append({'pid': child.child.pid, 'start_ticks': child.ticks, 'entry': str(child.source),
                                                          'reaped': child.reaped, 'pidfd_closed': child.pidfd is None})
        if cleanup or not report['original_controls_unchanged'] or len(report['checks']) != 20:
            report['phase'] = 'failed'
        dest = root/'qualification.json'
        dest.write_text(json.dumps(report, indent=2)+'\n')
        dest.chmod(0o600)
    print(json.dumps({'phase': report['phase'], 'checks': len(report['checks']), 'reason': report.get('reason'), 'cleanup_errors': cleanup}))
    return 0 if report['phase'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
