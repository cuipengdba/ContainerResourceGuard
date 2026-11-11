#!/usr/bin/env python3
"""Actual host-only observer lifecycle; no target signals or control writes.

Device IDs here are a qualification fixture, not product discovery settings.
Business error precedence cases are explicit doubles, not business acceptance.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
here = Path(__file__).parent
spec = importlib.util.spec_from_file_location('device_session_checks_target', here/'vendor-device-session.py')
session = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, required=True)
    args = parser.parse_args()
    root = args.work_dir
    assert sys.platform == 'linux' and os.environ.get('CRG_DEVICE_SESSION_CHECKS') == 'authorized-own-observer-only'
    assert str(root).startswith('/var/tmp/crg-') and '..' not in root.parts and root.parent == root.parent.resolve() and not root.exists()
    os.umask(0o077)
    root.mkdir(mode=0o700)
    source = here/'vendor-device-state-observer.py'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == session.OBSERVER_SHA
    report = {'schema': 'crg-device-session-qualification-v1', 'phase': 'running', 'checks': [], 'records': {},
              'target_signals': 0, 'product_control_writes': 0,
              'scope': 'Linux host session orchestration; original Python2 observer qualification remains separate',
              'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [source, here/'vendor-device-session.py', Path(__file__)]}}
    active = []
    target = {'pid': os.getpid(), 'start_ticks': session.instance(os.getpid())[0]}
    membership = Path('/proc/self/cgroup').read_text().strip().splitlines()
    assert len(membership) == 1 and membership[0].startswith('0::/')
    group = Path('/sys/fs/cgroup')/membership[0].split('::')[1].lstrip('/')
    devices = []
    for name in ['253:0', '8:2', '8:0']:
        path = Path('/sys/dev/block', name).resolve()
        info = path.stat()
        devices.append({'major_minor': name, 'sysfs': str(path), 'identity': [info.st_dev, info.st_ino]})
    def controls():
        result = {}
        for name in ['cpu.max', 'memory.max', 'io.max']:
            try:
                result[name] = {'available': True, 'value': (group/name).read_text()}
            except OSError as error:
                result[name] = {'available': False, 'reason': type(error).__name__}
        return result
    before = controls()
    def check(name, value):
        report['checks'].append({'name': name, 'passed': bool(value)})
        assert value, name
    def new(name, entry=source, label='selftest'):
        folder = root/name
        folder.mkdir(mode=0o700)
        record = {}
        report['records'][name] = record
        obj = session.Session(entry, folder, label, record)
        active.append(obj)
        return obj, record, folder
    def reject(name, expected, change=None, report_bytes=None, **kwargs):
        obj, record, folder = new(name, **kwargs)
        if change:
            change(obj, folder)
        try:
            obj.start(target, group, devices, 1)
        except session.Rejected as error:
            output = folder/'selftest-devices.json'
            preserved = output.read_bytes() == report_bytes if report_bytes is not None else not output.exists()
            check(name, str(error) == expected and obj.child is None and preserved)
        else:
            check(name, False)
    try:
        for name, duration in [('term', 3), ('natural', 1)]:
            obj, record, folder = new(name)
            obj.start(target, group, devices, duration)
            check(name+'-first-real-sample-owned-pidfd', record['phase'] == 'observing' and obj.owns_child() and obj.pidfd is not None)
            if name == 'term':
                saved = obj.ticks
                obj.ticks += 1
                try:
                    obj.signal_child(15)
                except session.Rejected as error:
                    check('wrong-child-start-ticks-refuses-signal', str(error) == 'DEVICE_SESSION_SIGNAL_IDENTITY' and record['owned_observer_TERM_count'] == 0)
                else:
                    check('wrong-child-start-ticks-refuses-signal', False)
                finally:
                    obj.ticks = saved
            else:
                deadline = time.monotonic()+5
                while time.monotonic() < deadline:
                    if session.instance(obj.child.pid)[1] == 'Z':
                        break
                    time.sleep(.02)
                else:
                    raise AssertionError('natural observer did not exit')
            obj.stop()
            check(name+'-real-report-exact-child-wait4', obj.reaped and obj.pidfd is None and record['phase'] == 'collected'
                  and record['whole_child_cpu_seconds'] >= record['sampling_cpu_seconds'] and record['whole_child_maximum_rss_kib'] <= 131072)
            check(name+'-expected-terminal-and-signal-counts', record['report_phase'] == ('incomplete' if name == 'term' else 'observed')
                  and record['exit'] == (2 if name == 'term' else 0) and record['owned_observer_TERM_count'] == (1 if name == 'term' else 0)
                  and record['owned_observer_KILL_count'] == 0 and record['full_duration_observed'] == (name == 'natural'))
            check(name+'-report-and-plan-private', (folder/'selftest-devices.json').stat().st_mode & 0o777 == 0o600
                  and (folder/'selftest-device-plan.json').stat().st_mode & 0o777 == 0o600)
            original = dict(record)
            obj.stop()
            check(name+'-stop-idempotent-target-unchanged', original == record and session.instance(target['pid'])[0] == target['start_ticks'] and before == controls())
        # An unreaped Z target and a reaped /proc directory are different real
        # states. The latter must stay read-unavailable, not invent an identity.
        for name, early_reap in [('target-zombie', False), ('target-reaped', True)]:
            fixture = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(1.5)'])
            try:
                selected = {'pid': fixture.pid, 'start_ticks': session.instance(fixture.pid)[0]}
                obj, record, folder = new(name)
                obj.start(selected, group, devices, 3)
                if early_reap:
                    fixture.wait(timeout=5)
                deadline = time.monotonic()+5
                while time.monotonic() < deadline:
                    if session.instance(obj.child.pid)[1] == 'Z':
                        break
                    time.sleep(.02)
                else:
                    raise AssertionError('observer did not stop after target exit')
                obj.stop()
                data = json.loads((folder/'selftest-devices.json').read_bytes())
                check(name+'-incomplete-evidence-preserves-only-original-target-samples', obj.reaped
                      and record['report_reason'] == ('read-unavailable' if early_reap else 'PROCESS_INSTANCE')
                      and not record['full_duration_observed'] and record['owned_observer_TERM_count'] == record['owned_observer_KILL_count'] == 0
                      and 1 <= len(data['samples']) < 4 and all(r['process']['start_ticks'] == selected['start_ticks'] for r in data['samples']))
            finally:
                fixture.wait(timeout=5)
        def wrong_source(obj, folder):
            entry = folder/'changed.py'
            entry.write_bytes(source.read_bytes()+b'\n# changed fixture\n')
            obj.source = entry
        reject('wrong-source-rejected-before-spawn', 'DEVICE_SESSION_FROZEN_SOURCE', change=wrong_source)
        reject('shared-root-rejected-before-spawn', 'DEVICE_SESSION_PRIVATE_ROOT', change=lambda obj, folder: folder.chmod(0o755))
        reject('existing-report-not-overwritten', 'DEVICE_SESSION_FRESH_REPORT', report_bytes=b'kept',
               change=lambda obj, folder: (folder/'selftest-devices.json').write_bytes(b'kept'))
        def symlink_source(obj, folder):
            entry = folder/'linked.py'
            entry.symlink_to(source)
            obj.source = entry
        reject('symlink-source-rejected-before-spawn', 'DEVICE_SESSION_FROZEN_SOURCE', change=symlink_source)
        reject('invalid-label-rejected-before-spawn', 'DEVICE_SESSION_LABEL', label='other')
        obj, record, folder = new('oversized-duration')
        try:
            obj.start(target, group, devices, 901)
        except session.Rejected as error:
            check('duration-901-rejected-before-spawn', str(error) == 'DEVICE_SESSION_DURATION' and obj.child is None)
        else:
            check('duration-901-rejected-before-spawn', False)
        obj, record, folder = new('wrong-target-start')
        try:
            obj.start(dict(target, start_ticks=target['start_ticks']+1), group, devices, 1)
        except session.Rejected as error:
            check('actual-startup-rejection-preserves-first-error', str(error) in ['DEVICE_SESSION_FIRST_SAMPLE', 'DEVICE_SESSION_START_EOF']
                  and record['start_error'] == str(error) and not obj.handshake and not (folder/'selftest-devices.json').exists())
        else:
            check('actual-startup-rejection-preserves-first-error', False)
        check('actual-startup-rejection-reaps-closes-without-target-signal', obj.reaped and obj.pidfd is None and record['exit'] == 1
              and record['owned_observer_TERM_count'] == record['owned_observer_KILL_count'] == 0)
        # Exercise a real incomplete pipe line, not a mocked select/readline.
        short = subprocess.Popen([sys.executable, '-c', "import sys,time;sys.stdout.write('{');sys.stdout.flush();time.sleep(.4)"],
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        pipe, _, _ = new('unterminated-handshake')
        pipe.child = short
        began = time.monotonic()
        try:
            pipe._first_line(.1)
        except session.Rejected as error:
            check('actual-unterminated-line-has-bounded-deadline', str(error) == 'DEVICE_SESSION_START_15S' and time.monotonic()-began < 1)
        else:
            check('actual-unterminated-line-has-bounded-deadline', False)
        finally:
            short.wait(timeout=3)
            short.stdout.close()
            pipe.child = None
        original = RuntimeError('ORIGINAL_BUSINESS_FAILURE')
        seen = []
        def fail_work():
            raise original
        def fail_finish():
            raise RuntimeError('DIAGNOSTIC_SAVE_FAILURE')
        try:
            session.finish_preserving_business(fail_work, fail_finish, lambda e: seen.append(str(e)))
        except RuntimeError as error:
            check('explicit-double-business-error-object-preserved', error is original and seen == ['DIAGNOSTIC_SAVE_FAILURE'])
        else:
            check('explicit-double-business-error-object-preserved', False)
        try:
            session.finish_preserving_business(lambda: 7, fail_finish, lambda e: None)
        except RuntimeError as error:
            check('explicit-double-diagnostic-failure-not-accepted-as-pass', str(error) == 'DIAGNOSTIC_SAVE_FAILURE')
        else:
            check('explicit-double-diagnostic-failure-not-accepted-as-pass', False)
        check('explicit-double-success-result-preserved', session.finish_preserving_business(lambda: 27, lambda: None, lambda e: None) == 27)
        check('all-target-identities-and-original-controls-unchanged', session.instance(target['pid'])[0] == target['start_ticks'] and before == controls())
    except BaseException as error:
        report.update(phase='failed', reason_class=type(error).__name__, reason=str(error)[:200])
    finally:
        errors = []
        for obj in active:
            try:
                obj.stop()
            except BaseException as error:
                errors.append(type(error).__name__)
        report['cleanup_errors'] = errors
        report['observer_instances'] = [{'pid': obj.child.pid, 'start_ticks': obj.ticks, 'entry': str(obj.source),
                                         'reaped': obj.reaped, 'pidfd_closed': obj.pidfd is None}
                                        for obj in active if obj.child is not None]
        report['original_controls_unchanged'] = before == controls()
        if report['phase'] == 'running':
            report['phase'] = ('passed' if len(report['checks']) == 26 and all(c['passed'] for c in report['checks'])
                               and not errors and report['original_controls_unchanged'] else 'failed')
        dest = root/'qualification.json'
        dest.write_text(json.dumps(report, indent=2)+'\n')
        dest.chmod(0o600)
    print(json.dumps({'phase': report['phase'], 'checks': len(report['checks']), 'reason': report.get('reason'),
                      'cleanup_errors': report['cleanup_errors']}))
    return 0 if report['phase'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
