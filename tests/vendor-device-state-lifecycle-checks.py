#!/usr/bin/env python3
"""Linux host checks of a naturally exiting fixture and an owned observer's TERM.

Never signals the target fixture/business process. Uses pidfd for only the
observer child created here. Original observer source and prior reports stay fixed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

SOURCE_SHA = '0fa377189ded92e2b5a9e182871e0494c8af4bc73920b8eb25d03ba9937995c6'


def fields(pid):
    return Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()


def instance_gone(pid, start):
    try:
        return int(fields(pid)[19]) != start
    except (FileNotFoundError, ProcessLookupError):
        return True


def plan_for(pid, output):
    group = Path('/sys/fs/cgroup')/Path('/proc', str(pid), 'cgroup').read_text().strip().split('::')[1].lstrip('/')
    devices = []
    for name in ['253:0', '8:2', '8:0']:
        p = Path('/sys/dev/block', name).resolve()
        s = p.stat()
        devices.append({'major_minor': name, 'sysfs': str(p), 'identity': [s.st_dev, s.st_ino]})
    s = group.stat()
    return {'schema': 'crg-device-state-observer-plan-v1', 'observer_sha256': SOURCE_SHA, 'label': 'selftest',
            'pid': pid, 'start_ticks': int(fields(pid)[19]), 'cgroup': str(group), 'cgroup_identity': [s.st_dev, s.st_ino],
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'devices': devices,
            'duration_seconds': 3, 'output': str(output)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tools', required=True, type=Path)
    p.add_argument('--work-dir', required=True, type=Path)
    args = p.parse_args()
    assert sys.platform == 'linux' and os.environ.get('CRG_DEVICE_LIFECYCLE') == 'authorized-own-observer-only'
    root = args.work_dir
    assert str(root).startswith('/var/tmp/crg-') and '..' not in root.parts and root.parent == root.parent.resolve() and not root.exists()
    source = args.tools/'vendor-device-state-observer.py'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA
    os.umask(0o077)
    root.mkdir(mode=0o700)
    report = {'schema': 'crg-device-observer-lifecycle-qualification-v1', 'phase': 'running', 'checks': [],
              'observer_source_sha256': SOURCE_SHA, 'lifecycle_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'target_signals': 0, 'owned_observer_TERM_count': 0, 'KILL_count': 0}
    def launch(plan, name):
        raw = (json.dumps(plan, sort_keys=True, separators=(',', ':'))+'\n').encode()
        path = root/(name+'-plan.json')
        path.write_bytes(raw)
        child = subprocess.Popen([sys.executable, str(source), '--plan', str(path), '--plan-sha256', hashlib.sha256(raw).hexdigest(), '--execute'],
                                 env=dict(os.environ, CRG_DEVICE_OBSERVER='authorized-disposable-readonly-only', PYTHONDONTWRITEBYTECODE='1'),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        start = int(fields(child.pid)[19])
        report.setdefault('observer_instances', []).append({'pid': child.pid, 'start_ticks': start, 'entry': str(source)})
        assert select.select([child.stdout], [], [], 5)[0], 'FIRST_SAMPLE_TIMEOUT'
        line = child.stdout.readline(4096)
        assert json.loads(line)['phase'] == 'observing'
        return child, start, line
    try:
        # This test-created child exits by itself. Its unreaped Z identity is rejected.
        target = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(1.5)'])
        value = plan_for(target.pid, root/'target-exit.json')
        child, start, first = launch(value, 'target-exit')
        stdout, stderr = child.communicate(timeout=8)
        target.wait(timeout=3)
        raw = Path(value['output']).read_bytes()
        result = json.loads(raw)
        assert child.returncode == 2 and not stderr and result['phase'] == 'incomplete' and result['reason'] == 'PROCESS_INSTANCE'
        assert 1 <= result['sample_count'] < 4 and all(r['process']['start_ticks'] == value['start_ticks'] for r in result['samples'])
        assert instance_gone(child.pid, start)
        report['checks'].append({'name': 'actual-target-natural-exit-stops-and-discards-changed-row', 'passed': True,
                                 'target_pid': target.pid, 'target_start_ticks': value['start_ticks'], 'observer_pid': child.pid,
                                 'observer_start_ticks': start, 'exit': child.returncode, 'raw_report_sha256': hashlib.sha256(raw).hexdigest(), 'report': result})
        value = plan_for(os.getpid(), root/'observer-stop.json')
        child, start, first = launch(value, 'observer-stop')
        descriptor = os.pidfd_open(child.pid, 0)
        try:
            assert int(fields(child.pid)[19]) == start and str(source).encode() in Path('/proc', str(child.pid), 'cmdline').read_bytes().split(b'\0')
            signal.pidfd_send_signal(descriptor, signal.SIGTERM)
            report['owned_observer_TERM_count'] += 1
        finally:
            os.close(descriptor)
        stdout, stderr = child.communicate(timeout=8)
        raw = Path(value['output']).read_bytes()
        result = json.loads(raw)
        assert child.returncode == 2 and not stderr and result['phase'] == 'incomplete' and result['reason'] == 'observer-interrupted'
        assert 1 <= result['sample_count'] < 4 and int(fields(os.getpid())[19]) == value['start_ticks']
        assert instance_gone(child.pid, start) and (Path(value['output']).stat().st_mode & 0o777) == 0o600
        report['checks'].append({'name': 'pidfd-TERM-only-owned-observer-flushes-partial-without-signalling-target', 'passed': True,
                                 'observer_pid': child.pid, 'observer_start_ticks': start, 'exit': child.returncode,
                                 'raw_report_sha256': hashlib.sha256(raw).hexdigest(), 'report': result})
        report['phase'] = 'passed'
    except BaseException as error:
        report.update(phase='failed', reason_class=type(error).__name__, reason=str(error)[:200])
    finally:
        (root/'qualification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'phase': report['phase'], 'checks': len(report['checks']), 'owned_observer_TERM_count': report['owned_observer_TERM_count'],
                      'target_signals': report['target_signals'], 'KILL_count': report['KILL_count'], 'reason': report.get('reason')}))
    return 0 if report['phase'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
