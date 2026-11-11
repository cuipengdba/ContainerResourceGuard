#!/usr/bin/env python3
"""Exercise failure orchestration and replay actual interrupted PG evidence.

Lifecycle branches use explicit doubles: this is not new business acceptance or
another native-signal qualification. Actual pidfd/vendor-image qualifications
are independently pinned by the frozen executor's readiness checks.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode=True
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--work-dir',type=Path,required=True)
args=p.parse_args()
assert sys.platform=='linux' and os.environ.get('CRG_FINAL_WAIT_CHECKS')=='authorized-disposable-test-node-only'
assert str(args.work_dir).startswith('/var/tmp/crg-') and '..' not in args.work_dir.parts and not args.work_dir.exists()
here=Path(__file__).parent;entry=here/'vendor-business-memory-pressure-final-wait.py'
spec=importlib.util.spec_from_file_location('final_wait_checks_target',entry)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
args.work_dir.mkdir(mode=0o700)
checks=[];events=[];original_session=m.session.Session


def check(name,value):
    checks.append({'name':name,'passed':bool(value)})
    assert value,name


class Drain:
    def __init__(self,failure=None,close_error=None):
        self.calls=[];self.failure=failure;self.close_error=close_error
    def finish_after_failure(self,error,timeout):
        self.calls.append((error,timeout));events.append('drain')
        if self.failure:raise self.failure
    def close(self):
        events.append('close')
        if self.close_error:raise self.close_error


class Observer:
    def __init__(self,source,digest,root,role,record):
        assert digest==m.WAIT_CONTRACT['observer_sha256']
        self.record=record;record.update(phase='collected',first_sample_epoch=1,last_sample_epoch=100)
    def stop(self):
        events.append('observer-stop')
        if getattr(self,'failure',None):raise self.failure


class Fixture:
    run=m.Execution.business_native
    failed_engine_interval=m.Execution.failed_engine_interval
    collect=m.Execution.collect_native_diagnostic
    def __init__(self,name,error=None,drain_error=None,collector_error=None,save_error=None,close_error=None):
        self.root=args.work_dir/name;self.root.mkdir(mode=0o700)
        self.row={'reload_intervals':[{'started_epoch':10,'ended_epoch':20}]}
        self.error=error;self.drain=Drain(drain_error,close_error)
        self.collector_error=collector_error;self.save_error=save_error
        self.worker=None
    def save(self):
        if self.save_error:raise self.save_error
    def _business_native_original(self,role,folder,group,row):
        events.append('business');self.native_drain=self.drain
        if self.error:raise self.error
        return 'business-result'
    def collect_native_diagnostic(self,role,folder,row):
        events.append('collector')
        if self.collector_error:raise self.collector_error


def invoke(f):
    events.clear()
    try:return f.run('dbs',f.root,Path('/unused'),f.row),None
    except BaseException as error:return None,error


def replay_partial(role,qualification):
    f=Fixture('partial-'+role)
    actual=qualification['roles'][role]['runtime'];native=actual['native'];data=actual['diagnostic']
    assert native['run_id'].endswith('0' if role=='dbs' else '1')
    f.plan={'run_id':native['run_id'][:-1]}
    output=f.root/('postgresql/basebackup/crg-soak-'+native['run_id']);output.mkdir(parents=True,mode=0o700)
    raw=(json.dumps(data,sort_keys=True,separators=(',',':'))+'\n').encode()
    assert hashlib.sha256(raw).hexdigest()==actual['diagnostic_sha256']
    (output/'load.json').write_text(json.dumps(native));(output/'native-diagnostics.json').write_bytes(raw)
    try:f.collect(role,f.root,f.row)
    except m.Rejected as error:assert str(error)=='NATIVE_PG_SAMPLING_COVERAGE'
    else:raise AssertionError('partial PG evidence accepted as600s')
    record=f.row['native_request_pg']
    check(role+'-actual-interrupted-native-partial-retained-and-rejected-as600s',
          record['phase']=='failed' and record['native_phase']=='failed' and record['native_interrupted']
          and record['partial_not600s'] and record['native_elapsed_seconds']<600
          and record['raw_report_sha256']==actual['diagnostic_sha256']
          and hashlib.sha256((f.root/(role+'-native-diagnostics.json')).read_bytes()).hexdigest()==actual['diagnostic_sha256']
          and record['original_native_SQL']==native['sql'] and record['original_native_API']==native['api'])


try:
    m.session.Session=Observer
    f=Fixture('normal');value,error=invoke(f)
    check('normal-success-collects-closes-without-early-TERM',error is None and value=='business-result' and not f.drain.calls and events==['business','observer-stop','collector','close'])
    original=RuntimeError('original-business-failure')
    f=Fixture('business-error',error=original);_,error=invoke(f)
    check('original-business-object-drains-before-observer-and-collector',error is original and f.drain.calls==[(original,120)] and events==['business','drain','observer-stop','collector','close'])
    f=Fixture('identity-error',error=original,drain_error=m.native_session.Rejected('NATIVE_SESSION_SIGNAL_IDENTITY'));_,error=invoke(f)
    check('identity-failure-keeps-original-and-still-collects',error is original and events==['business','drain','observer-stop','collector','close'] and f.row['diagnostic_cleanup_errors']==['NATIVE_SESSION_SIGNAL_IDENTITY'])
    f=Fixture('timeout-error',error=original,drain_error=m.native_session.Rejected('NATIVE_SESSION_FINAL_FLUSH_TIMEOUT'));_,error=invoke(f)
    check('cleanup-timeout-keeps-original-without-retry-or-kill',error is original and len(f.drain.calls)==1 and 'collector' in events and f.row['diagnostic_cleanup_errors']==['NATIVE_SESSION_FINAL_FLUSH_TIMEOUT'])
    f=Fixture('collector-error',error=original,collector_error=m.Rejected('NATIVE_DIAGNOSTIC_NOT_FINAL'));_,error=invoke(f)
    check('collector-rejection-keeps-original-and-closes',error is original and events[-1]=='close' and f.row['diagnostic_cleanup_errors']==['NATIVE_DIAGNOSTIC_NOT_FINAL'])
    f=Fixture('observer-error',error=original)
    def observer_failure(role,folder,group,row):
        self=f;self.native_drain=self.drain;self.thread_session.failure=m.session.Rejected('observer-stop-failed');raise original
    f._business_native_original=observer_failure;_,error=invoke(f)
    check('observer-stop-failure-still-collects-and-keeps-original',error is original and events[-2:]==['collector','close'] and 'observer-stop-failed' in f.row['diagnostic_cleanup_errors'])
    f=Fixture('save-error',error=original,save_error=OSError('save-failed'));_,error=invoke(f)
    check('recording-failure-never-masks-business-error',error is original and 'collector' in events and events[-1]=='close')
    f=Fixture('close-error',error=original,close_error=OSError('close-failed'));_,error=invoke(f)
    check('pidfd-close-failure-never-masks-business-error',error is original and events[-1]=='close')
    diagnostic=m.Rejected('diagnostic-failure')
    f=Fixture('success-invalid-diagnostic',collector_error=diagnostic);_,error=invoke(f)
    check('successful-business-does-not-hide-diagnostic-failure',error is diagnostic and not f.drain.calls and events[-1]=='close')
    f=Fixture('failed-engine')
    path=Path('/var/tmp/crg-business-pressure203-20261111/dbs-engine/business-backup.json');raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='4b2cd9cd98267f2afae707b0fd7ebbb7d18f78e6dfc0d33a84637501ae954dc6'
    target=f.root/'dbs-engine';target.mkdir(mode=0o700);(target/'business-backup.json').write_bytes(raw)
    f.failed_engine_interval('dbs',f.row);interval=f.row['diagnostic_failed_engine_interval'];engine=json.loads(raw)
    check('actual-failed-engine-interval-archived-without-business-pass',interval['started_epoch']==engine['started'] and interval['ended_epoch']==engine['ended'] and interval['diagnostic_only_not_business_acceptance'] and 'engine_interval' not in f.row and 'engine' not in f.row)
    item=m.FINAL_CONTRACT['real_qualification'];raw=Path(item['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==item['sha256']
    q=json.loads(raw)
    for role in ['dbs','hisdbs']:replay_partial(role,q)
finally:
    m.session.Session=original_session
    result={'schema':'crg-final-wait-integration-checks-v1','phase':'passed' if len(checks)==12 and all(v['passed'] for v in checks) else 'failed',
            'checks':checks,'executor_sha256':hashlib.sha256(entry.read_bytes()).hexdigest(),
            'lifecycle_branches_use_explicit_doubles':True,'actual_interrupted_PG_reports_replayed':True,
            'new_process_signals_SQL_business_or_control_writes':False,'full600s_accepted':False}
    dest=args.work_dir/'checks-result.json';dest.write_text(json.dumps(result,indent=2)+'\n');dest.chmod(0o600)
print(json.dumps({'phase':result['phase'],'checks':len(checks)}))
raise SystemExit(0 if result['phase']=='passed' else 1)
