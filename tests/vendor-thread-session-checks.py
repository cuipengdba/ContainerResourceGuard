#!/usr/bin/env python3
"""Actual Linux child lifecycle checks; only creates/signals its own sleep/helper."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
import sys
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('session', Path(__file__).with_name('vendor-thread-session.py'))
session = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', type=Path, required=True)
    args = parser.parse_args()
    root = args.work_dir
    assert sys.platform == 'linux' and os.environ.get('CRG_THREAD_SESSION_SELFTEST') == 'authorized-disposable-test-node-only'
    assert str(root).startswith('/var/tmp/crg-') and '..' not in root.parts and not root.exists()
    root.mkdir(mode=0o700)
    child = subprocess.Popen(['sleep', '60'])
    checks, records = [], {}
    def check(name, ok):
        checks.append({'name': name, 'passed': bool(ok)})
        assert ok, name
    try:
        ticks = session.instance(child.pid)[0]
        proc = Path('/proc', str(child.pid))
        membership = (proc/'cgroup').read_text()
        assert membership.startswith('0::/') and len(membership.splitlines()) == 1
        group = Path('/sys/fs/cgroup')/membership.strip().split('::')[1].lstrip('/')
        target = {'pid': child.pid, 'start_ticks': ticks, 'executable_sha256': hashlib.sha256((proc/'exe').read_bytes()).hexdigest()}
        source = Path(__file__).with_name('vendor-thread-observer.py')
        sha = hashlib.sha256(source.read_bytes()).hexdigest()
        def controls():
            result = {}
            for name in ['cpu.max', 'memory.max', 'io.max']:
                try:
                    result[name] = {'available': True, 'value': (group/name).read_text().strip()}
                except OSError as error:
                    result[name] = {'available': False, 'reason': type(error).__name__}
            return result
        # SSH's user-session scope may not expose controllers. This qualifies
        # child ownership/lifecycle, never claims container controller coverage.
        before = controls()
        for name, duration in [('term', 900), ('natural', 1)]:
            folder = root/name
            folder.mkdir(mode=0o700)
            record = {}
            records[name] = record
            s = session.Session(source, sha, folder, 'selftest', record)
            try:
                s.start(target, group, duration)
                check(name+'-first-sample-handshake-and-own-pidfd', record['phase'] == 'observing' and s.owns_child() and s.pidfd is not None)
                if name == 'term':
                    saved = s.ticks
                    s.ticks += 1
                    try:
                        s.signal_child(15)
                    except session.Rejected as error:
                        check('wrong-start-refuses-signal', str(error) == 'SESSION_SIGNAL_IDENTITY')
                    else:
                        check('wrong-start-refuses-signal', False)
                    finally:
                        s.ticks = saved
                else:
                    time.sleep(1.3)
                s.stop()
                check(name+'-reaped-and-exact-wait4-accounting', s.reaped and record['observer_original_instance_gone']
                      and record['whole_child_cpu_seconds'] >= record['sampling_cpu_seconds'] and record['phase'] == 'collected')
                check(name+'-expected-terminal', record['report_phase'] == ('incomplete' if name == 'term' else 'observed')
                      and record['exit'] == (2 if name == 'term' else 0))
                check(name+'-target-same-no-control-writes', session.instance(child.pid)[0] == ticks
                      and child.poll() is None and before == controls())
                s.stop()
                check(name+'-second-stop-idempotent', s.reaped and s.pidfd is None)
            finally:
                if not s.reaped:
                    s.stop()
        first = RuntimeError('ORIGINAL_BUSINESS_ERROR')
        seen = []
        def fail_business():
            raise first
        def fail_diagnostic():
            raise RuntimeError('DIAGNOSTIC_ERROR')
        try:
            session.preserve_business_error(fail_business, fail_diagnostic, lambda e: seen.append(str(e)))
        except RuntimeError as error:
            check('original-business-error-object-preserved', error is first and seen == ['DIAGNOSTIC_ERROR'])
        else:
            check('original-business-error-object-preserved', False)
        try:
            session.preserve_business_error(lambda: 1, fail_diagnostic, lambda e: None)
        except RuntimeError as error:
            check('diagnostic-failure-not-hidden-on-business-success', str(error) == 'DIAGNOSTIC_ERROR')
        else:
            check('diagnostic-failure-not-hidden-on-business-success', False)
        check('successful-work-result-preserved', session.preserve_business_error(lambda: 27, lambda: None, lambda e: None) == 27)
    finally:
        child.terminate()
        child.wait(timeout=5)
        out = {'phase': 'passed' if len(checks) == 14 and all(c['passed'] for c in checks) else 'failed',
               'checks': checks, 'records': records, 'selftest_scope_controls': before,
               'selftest_target_gone': not Path('/proc', str(child.pid)).exists(),
               'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [source, Path(__file__), Path(__file__).with_name('vendor-thread-session.py')]}}
        (root/'checks-result.json').write_text(json.dumps(out, indent=2)+'\n')
        (root/'checks-result.json').chmod(0o600)
    print(json.dumps({'phase': out['phase'], 'checks': len(checks), 'selftest_target_gone': out['selftest_target_gone']}))
    return 0 if out['phase'] == 'passed' and out['selftest_target_gone'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
