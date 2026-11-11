#!/usr/bin/env python3
"""Check collection/error precedence using actual short PG qualification data.

No new SQL, processes, resource controls or business workloads are started.
The short reports must be rejected as incomplete 600-second evidence.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--work-dir', type=Path, required=True)
args = parser.parse_args()
assert sys.platform == 'linux' and os.environ.get('CRG_NATIVE_PRESSURE_DIAGNOSTICS_CHECKS') == 'authorized-disposable-test-node-only'
assert str(args.work_dir).startswith('/var/tmp/crg-') and '..' not in args.work_dir.parts and not args.work_dir.exists()
here = Path(__file__).parent
entry = here/'vendor-business-memory-pressure-native-diagnostics.py'
assert hashlib.sha256(entry.read_bytes()).hexdigest() == '855ed517d136e52d6812ea0eb6f07ad27e54b73841f85b039e0864e6957cdd0c'
spec = importlib.util.spec_from_file_location('native_pressure_collector', entry)
module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
qualified = Path(module.DIAGNOSTIC_CONTRACT['qualification_report'])
raw = qualified.read_bytes()
assert hashlib.sha256(raw).hexdigest() == module.DIAGNOSTIC_CONTRACT['qualification_report_sha256']
qualification = json.loads(raw)
assert qualification['phase'] == 'passed'
args.work_dir.mkdir(mode=0o700)
checks = []


def check(name, value):
    checks.append({'name': name, 'passed': bool(value)})
    assert value, name


class Fixture:
    collect = module.Execution.collect_native_diagnostic

    def __init__(self, name, role, case, tamper=False):
        self.folder = args.work_dir/name
        self.folder.mkdir(mode=0o700)
        self.root = self.folder/'output';self.root.mkdir(mode=0o700)
        original = qualification['roles'][role]['real_pg']['cases'][case]
        self.plan = {'run_id': original['run_id'][:-1]}
        self.row = {}
        self.role = role
        self.data = json.loads(json.dumps(original['diagnostics']))
        self.native = json.loads(json.dumps(original['load']))
        if tamper:
            self.data['worker_sha256'] = '0'*64
        data = (json.dumps(self.data, sort_keys=True, separators=(',', ':'))+'\n').encode()
        if not tamper:
            assert hashlib.sha256(data).hexdigest() == original['diagnostics_sha256']
        target = self.folder/('postgresql/basebackup/crg-soak-'+original['run_id'])
        target.mkdir(parents=True, mode=0o700)
        (target/'load.json').write_text(json.dumps(self.native))
        (target/'native-diagnostics.json').write_bytes(data)

    def save(self):
        path = self.root/'saved.json';path.write_text(json.dumps(self.row));path.chmod(0o600)


try:
    f = Fixture('short-normal', 'dbs', 'normal')
    try:
        f.collect(f.role, f.folder, f.row)
    except module.Rejected as error:
        check('actual12s-normal-never-accepted-as600s', str(error) == 'NATIVE_PG_SAMPLING_COVERAGE' and f.row['native_request_pg']['phase'] == 'failed' and f.row['native_request_pg']['native_phase'] == 'passed')
    else:
        check('actual12s-normal-never-accepted-as600s', False)
    check('bounded-raw-evidence-retained-on-coverage-rejection', hashlib.sha256((f.root/'dbs-native-diagnostics.json').read_bytes()).hexdigest() == f.native['native_diagnostics']['report_sha256'])
    f = Fixture('short-lock', 'hisdbs', 'own-table-lock')
    original = RuntimeError('original-business-error')
    cleanup = []
    def business_failure():
        raise original
    try:
        module.session.preserve_business_error(business_failure, lambda:f.collect(f.role, f.folder, f.row), lambda error:cleanup.append(str(error)))
    except RuntimeError as error:
        check('original-business-error-object-wins-over-collector-rejection', error is original and cleanup == ['NATIVE_PG_SAMPLING_COVERAGE'])
    else:
        check('original-business-error-object-wins-over-collector-rejection', False)
    record = f.row['native_request_pg']
    check('actual-lock-native-failure-and-client-PID-error-retained', record['native_phase'] == 'failed' and record['original_native_SQL']['errors'] == record['error_count'] == 1 and record['errors'][0]['backend_pid'] > 1 and record['errors'][0]['error']['code'].startswith('sql-') and record['PG_samples'] == 17)
    f = Fixture('business-success', 'dbs', 'normal')
    try:
        module.session.preserve_business_error(lambda:'original-business-success', lambda:f.collect(f.role, f.folder, f.row), lambda error:None)
    except module.Rejected as error:
        check('successful-business-still-exposes-diagnostic-rejection', str(error) == 'NATIVE_PG_SAMPLING_COVERAGE')
    else:
        check('successful-business-still-exposes-diagnostic-rejection', False)
    f = Fixture('wrong-source', 'dbs', 'normal', tamper=True)
    try:
        f.collect(f.role, f.folder, f.row)
    except module.Rejected as error:
        check('wrong-diagnostic-source-refused-before-counting-acceptance', str(error) == 'NATIVE_DIAGNOSTIC_IDENTITY' and f.row['native_request_pg']['phase'] == 'failed')
    else:
        check('wrong-diagnostic-source-refused-before-counting-acceptance', False)
finally:
    result = {'schema':'crg-native-pressure-collection-checks-v1', 'phase':'passed' if len(checks)==6 and all(v['passed'] for v in checks) else 'failed',
              'checks':checks,'qualification_report_sha256':hashlib.sha256(raw).hexdigest(),'executor_sha256':hashlib.sha256(entry.read_bytes()).hexdigest(),
              'new_SQL_or_business_or_control_writes':False,'full600s_accepted':False}
    path=args.work_dir/'checks-result.json';path.write_text(json.dumps(result,indent=2)+'\n');path.chmod(0o600)
print(json.dumps({'phase':result['phase'],'checks':len(checks)}))
raise SystemExit(0 if result['phase']=='passed' else 1)
