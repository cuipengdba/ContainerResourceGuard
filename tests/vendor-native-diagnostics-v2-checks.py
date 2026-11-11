from __future__ import division, print_function
"""Probe-thread fault isolation with explicit callback doubles; no database."""
import argparse
import gc
import hashlib
import json
import os
import sys
import threading
import time
import types

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--work-dir', required=True)
args = parser.parse_args()
assert sys.platform.startswith('linux') and os.environ.get('CRG_NATIVE_V2_CHECKS') == 'authorized-disposable-test-node-only'
assert args.work_dir.startswith('/var/tmp/crg-') and '..' not in args.work_dir.split('/') and not os.path.lexists(args.work_dir)
os.mkdir(args.work_dir, 0o700)
source = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor-native-diagnostics-v2.py')
module = types.ModuleType('native_v2_checks')
module.__file__ = source
raw = open(source, 'rb').read()
exec(compile(raw, source, 'exec'), module.__dict__)
checks, cases = [], {}
secret = 'private-diagnostic-failure-must-not-be-retained'
row = ['123', '1794390000.123456', 'active', 'Lock', 'transactionid', '1794390001', None, '{124}', 'fixture-update']


def check(name, value):
    checks.append({'name': name, 'passed': bool(value)})
    assert value, name


class Connection(object):
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class Sampler(object):
    def sample(self, callback):
        return {'available': True, 'targets': [], 'signals_or_control_writes': 0}


def fail(*unused):
    raise RuntimeError(secret)


def probe(name, factory, query=None, budget=False):
    module.create_wait_sampler = factory
    connections = []
    def connect():
        c = Connection()
        connections.append(c)
        return c
    d = module.Diagnostics('202611113220', threading.Lock(), threading.Event(), time.time,
                           connect, query or (lambda c, s, t: [row]), '0'*64)
    if budget:
        d.pg_bytes = module.base.PG_BUDGET
    d.start()
    until = time.time()+2
    while not d.data['pg_samples'] and d.summary['phase'] == 'observing' and time.time() < until:
        time.sleep(.01)
    still_running = not d.stop.is_set()
    d.stop.set()
    d.join()
    folder = args.work_dir+'/'+name
    os.mkdir(folder, 0o700)
    d.finalize(folder)
    cases[name] = {'data': d.data, 'summary': d.summary, 'workload_stop_was_unset': still_running,
                   'all_diagnostic_connections_closed': all(c.closed for c in connections)}
    assert d.summary['probe_thread_stopped'] and still_running and all(c.closed for c in connections)
    return d, folder


original_factory = module.create_wait_sampler
try:
    d, folder = probe('normal', lambda run: Sampler())
    check('unique-run-in-native-selection', "application_name='crg-disposable-soak-202611113220'" in d.activity_sql
          and "application_name='crg-disposable-soak'" not in d.activity_sql and d.activity_sql.startswith('SELECT '))
    check('decimal-backend-identity-preserved', d.data['pg_samples'][0]['rows'][0]['backend_start_epoch_text'] == row[1])
    check('normal-probe-closes-and-keeps-business-stop-unset', cases['normal']['all_diagnostic_connections_closed'] and cases['normal']['workload_stop_was_unset'])
    check('normal-bounded-complete-report', d.summary['diagnostic_complete'] and d.summary['pg_wait_samples'] == 1
          and d.summary['report_bytes'] <= 8*1024*1024)
    path = folder+'/native-diagnostics.json'
    saved = open(path, 'rb').read()
    d.finalize(folder)
    check('existing-final-report-not-replaced', saved == open(path, 'rb').read() and d.summary['phase'] == 'report-write-failed')
    d, unused = probe('initialization-failure', fail)
    check('initialization-failure-keeps-native-sample-and-redacts', d.data['pg_samples'][0]['available'] and d.summary['pg_wait_errors'] == 1 and secret not in json.dumps(d.data))
    check('initialization-failure-visible-in-final-artifact', not d.summary['diagnostic_complete'])
    class Broken(object):
        sample = staticmethod(fail)
    d, unused = probe('collection-exception', lambda run: Broken())
    check('collection-exception-does-not-stop-business', d.data['pg_samples'][0]['available'] and d.summary['pg_wait_errors'] == 1 and secret not in json.dumps(d.data))
    class Unavailable(object):
        def sample(self, callback):
            return {'available': False, 'reason': 'bounded-query-failed', 'targets': []}
    d, unused = probe('collection-unavailable', lambda run: Unavailable())
    check('failed-wait-query-closes-only-observer-connection', cases['collection-unavailable']['all_diagnostic_connections_closed'] and d.summary['pg_wait_errors'] == 1)
    class UnknownTarget(object):
        def sample(self, callback):
            return {'available': True, 'targets': [{'kernel_wait': {'available': False, 'reason': 'OSError'}}]}
    d, unused = probe('unknown-optional-metadata', lambda run: UnknownTarget())
    check('unreadable-optional-metadata-stays-unknown', d.summary['pg_wait_unknown_targets'] == 1 and d.summary['pg_wait_errors'] == 0
          and not d.data['pg_samples'][0]['pg_wait']['targets'][0]['kernel_wait']['available'])
    d, unused = probe('native-query-failure', lambda run: Sampler(), query=fail)
    check('native-query-failure-not-hidden-by-wait-layer', not d.data['pg_samples'][0]['available'] and d.summary['pg_errors'] == 1
          and d.summary['pg_wait_errors'] == 1 and not d.summary['diagnostic_complete'] and secret not in json.dumps(d.data))
    d, unused = probe('report-budget', lambda run: Sampler(), budget=True)
    check('capacity-stops-probe-without-business-stop', d.summary['phase'] == 'capacity-exceeded' and d.summary['dropped_pg_samples'] == 1)
    try:
        module.frozen('vendor-native-diagnostics.py', '0'*64)
    except ValueError:
        check('dependency-hash-mismatch-rejected', True)
    else:
        check('dependency-hash-mismatch-rejected', False)
    original_frozen = module.frozen
    def ephemeral(name, digest):
        value = types.ModuleType('ephemeral_qualification_module')
        exec(compile("import os\nclass Sampler(object):\n def __init__(self,run):self.initial=os.name\n def name(self):return os.name\n", 'explicit-lifetime-double', 'exec'), value.__dict__)
        return value
    module.frozen = ephemeral
    try:
        sampler = original_factory('202611113220')
        gc.collect()
        check('dynamic-module-alive-during-and-after-sampler-construction', sampler.initial == 'posix' and sampler.name() == 'posix'
              and sampler._source_module.__dict__['os'] is not None)
    finally:
        module.frozen = original_frozen
    previous = os.environ.pop('CRG_PG_WAIT', None)
    try:
        d, unused = probe('actual-missing-PG-marker', original_factory)
        check('actual-missing-marker-fails-open-before-PG-proc-access', d.data['pg_samples'][0]['available'] and d.summary['pg_wait_errors'] == 1
              and not d.summary['diagnostic_complete'] and d.wait_sampler is None and d.data['pg_samples'][0]['pg_wait']['error']['class'] == 'Rejected')
    finally:
        if previous is not None:
            os.environ['CRG_PG_WAIT'] = previous
finally:
    result = {'schema': 'crg-native-v2-checks-v1', 'phase': 'passed' if len(checks) == 15 and all(c['passed'] for c in checks) else 'failed',
              'checks': checks, 'cases': cases, 'helper_sha256': hashlib.sha256(raw).hexdigest(),
              'python': sys.version.split()[0], 'callbacks_are_test_doubles': True, 'real_PG_or_business_used': False}
    with open(args.work_dir+'/qualification.json', 'w') as stream:
        stream.write(json.dumps(result, indent=2)+'\n')
print(json.dumps({'phase': result['phase'], 'checks': len(checks)}))
sys.exit(0 if result['phase'] == 'passed' else 1)
