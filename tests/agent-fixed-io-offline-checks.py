#!/usr/bin/env python3
"""Replay pure exception/admission checks and two synthetic evidence negatives.

No node connection, signals, controller writes or vendor workload are executed.
"""
from pathlib import Path
import argparse,ast,copy,datetime,gzip,hashlib,importlib.util,json,tempfile,types


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();repo=args.repo.resolve()
    temporary=tempfile.TemporaryDirectory(prefix='crg-fixed-activity-offline-');tools=Path(temporary.name)
    spec=importlib.util.spec_from_file_location('fixed_activity_offline_reader',repo/'tests/analyze-agent-fixed-io-comparison.py');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    original_files,original_proof=reader.read_evidence(repo/'docs/test-evidence/agent-activity441-a1.json.gz')
    collected=tools/'collected'
    for name in ['arms/a1/report.json','arms/a1/dbs/native/load.json','arms/a1/dbs/native-diagnostics.json','comparison-snapshot.json']:
     target=collected/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(original_files[name])
    path=repo/'tests/vendor-agent-fixed-io-comparison-v3.py';v3_source_raw=path.read_bytes();tree=ast.parse(v3_source_raw)
    spec=importlib.util.spec_from_file_location('fixed_activity_v3_pure',path);v3=importlib.util.module_from_spec(spec);spec.loader.exec_module(v3)
    auditpath=repo/'tests/soak-report-audit.py';spec=importlib.util.spec_from_file_location('original_business_exception',auditpath);audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    rows=[]
    def check(name,value):
     assert value,name
     rows.append({'name':name,'passed':True})
    v2=ast.parse((repo/'tests/vendor-agent-fixed-io-comparison-v2.py').read_bytes())
    method=lambda t,n:next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name==n)
    check('strict-original-eligibility-AST-unchanged',ast.dump(method(tree,'arm_eligibility'),include_attributes=False)==ast.dump(method(v2,'arm_eligibility'),include_attributes=False))
    methodnode=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='business_native')
    class ActivityError(Exception):pass
    scope={'module':types.SimpleNamespace(Rejected=audit.Rejected),'activity':types.SimpleNamespace(Rejected=ActivityError)}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[methodnode],type_ignores=[])),str(path)+'::pure-error-boundary','exec'),scope)
    boundary=scope['business_native']
    def call(error=None,save_fails=False):
     record={'activity_stage':'synthetic-unit-stage'};saved=[];token=object()
     def work(*args):
      if error is not None:raise error
      return token
     def save():
      saved.append(True)
      if save_fails:raise OSError('synthetic private recorder failure')
     execution=types.SimpleNamespace(_activity_business_native=work,save=save)
     try:result=boundary(execution,'dbs',None,None,record)
     except BaseException as received:return received,record,saved,None
     return None,record,saved,result is token
    check('original-business-exception-is-ValueError-subclass',issubclass(audit.Rejected,ValueError))
    for label,error in [('business',audit.Rejected('NATIVE_COMPLETION_EXIT')),('business-subclass',type('BusinessSubclass',(audit.Rejected,),{})('original-subclass')),('unexpected',RuntimeError('synthetic unexpected')),('interrupt',KeyboardInterrupt()),('exit',SystemExit(17))]:
     received,record,saved,_=call(error)
     check(label+'-same-error-object-and-no-activity-relabel',received is error and 'activity_error' not in record and not saved)
    for label,error in [('plain-validation',ValueError('synthetic-identity-rejection')),('activity',ActivityError('synthetic-pidfd-rejection'))]:
     received,record,saved,_=call(error)
     check(label+'-recorded-and-bounded-original-cause',isinstance(received,audit.Rejected) and received.__cause__ is error and str(received)=='ACTIVITY:'+str(error) and record['activity_error']['reason']==str(error) and len(saved)==1)
    error=ActivityError('synthetic-activity-failure');received,record,saved,_=call(error,True)
    check('recorder-failure-does-not-replace-activity-cause',received.__cause__ is error and record['activity_error']['record_write_error']=='OSError')
    check('success-return-object-preserved',call()[3] is True)
    report=json.loads((collected/'arms/a1/report.json').read_bytes());native=json.loads((collected/'arms/a1/dbs/native/load.json').read_bytes());master=json.loads((collected/'comparison-snapshot.json').read_bytes())
    review=copy.deepcopy(master['arms']['a1']['eligibility'])
    check('actual-v2-prefix-still-refused',v3.observational_continuation(report,native,review)['allowed'] is False)
    projected=copy.deepcopy(report);projected['reason']='NATIVE_COMPLETION_EXIT';projected['roles']['dbs']['boots'][0]['native_request_pg']['raw_report']=str(collected/'arms/a1/dbs/native-diagnostics.json')
    projected_review=copy.deepcopy(review);projected_review['checks']['terminal_reason']=True
    value=v3.observational_continuation(projected,native,projected_review)
    check('explicit-overflow-observation-never-qualified',value['allowed'] is True and value['qualified_arm'] is False and value['original_arm_eligible'] is False and value['strict_original_criteria_unchanged'] is True and projected_review['eligible'] is False)
    for label,key in [('short-native','actual600'),('kernel-change','fixed_original_numeric_controls'),('bad-lifecycle','session_normal_close'),('missing-engine','engine_ten_checks'),('missing-thread-device','thread_device_collected')]:
     bad=copy.deepcopy(projected_review);bad['checks'][key]=False
     check(label+'-refuses-followup',v3.observational_continuation(projected,native,bad)['allowed'] is False)
    bad=copy.deepcopy(projected);bad['roles']['dbs']['boots'][0]['diagnostic_cleanup_errors'].append('unexpected-failure')
    check('other-cleanup-error-refuses-followup',v3.observational_continuation(bad,native,projected_review)['allowed'] is False)
    with tempfile.TemporaryDirectory(prefix='crg-r447-synthetic-',dir=tools) as folder:
     original=json.loads((collected/'arms/a1/dbs/native-diagnostics.json').read_bytes())
     def variant(value):
      p=Path(folder)/'diagnostic.json';data=json.dumps(value).encode();p.write_bytes(data);r=copy.deepcopy(projected);n=copy.deepcopy(native);digest=hashlib.sha256(data).hexdigest()
      record=r['roles']['dbs']['boots'][0]['native_request_pg'];record.update(raw_report=str(p),raw_report_sha256=digest);n['native_diagnostics']['report_sha256']=digest
      return r,n
     bad=copy.deepcopy(original);next(v for v in bad['pg_samples'] if not v['pg_wait']['available'])['pg_wait']['reason']='SYNTHETIC_OTHER_COLLECTION_FAILURE';r,n=variant(bad)
     check('consistent-hashes-other-PG-error-refused',v3.observational_continuation(r,n,projected_review)['allowed'] is False)
     r,n=variant(original);n['native_diagnostics']['dropped_requests']=1
     check('dropped-request-refuses-followup',v3.observational_continuation(r,n,projected_review)['allowed'] is False)
     r,n=variant(original);n['sql']['attempts']+=1
     check('inconsistent-attempt-accounting-refused',v3.observational_continuation(r,n,projected_review)['allowed'] is False)
     r,n=variant(original);n['native_diagnostics']['report_sha256']='0'*64
     try:v3.observational_continuation(r,n,projected_review)
     except ValueError:check('diagnostic-hash-mismatch-rejected',True)
     else:raise AssertionError('hash mismatch accepted')
    check('v2-full-failure-original-bytes-preserved',hashlib.sha256((collected/'arms/a1/report.json').read_bytes()).hexdigest()=='2124c64cb82309ee2c67e3983595dfd7d223d5115fd4e659d930fab68286f3ac')

    def evidence_variant(values,proof,label):
     manifest={'schema':'crg-agent-fixed-io-exact-files-v2','files':{name:{'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()} for name,value in values.items()}}
     raw=json.dumps(proof).encode();bundle={'schema':'crg-agent-fixed-io-exact-evidence-v2','manifest':manifest,'files':{name:{'exact_utf8':value.decode()} for name,value in values.items()},'independent_exact_utf8':raw.decode(),'independent_sha256':hashlib.sha256(raw).hexdigest()}
     path=tools/(label+'.json.gz');path.write_bytes(gzip.compress(json.dumps(bundle).encode(),mtime=0));return reader.read_evidence(path)
    bad_files=copy.deepcopy(original_files);bad_files['sources/vendor-agent-fixed-io-comparison-v2.py']+=b'\n'
    values,proof=evidence_variant(bad_files,original_proof,'changed-source-consistent-manifest')
    try:reader.review_arm(values,proof,'a1')
    except ValueError as error:check('consistent-manifest-changed-frozen-source-rejected',str(error)=='FROZEN_EXECUTOR_AND_PLAN')
    else:raise AssertionError('changed frozen source accepted')
    bad_files=copy.deepcopy(original_files);proof=copy.deepcopy(original_proof);report=json.loads(bad_files['arms/a1/report.json']);report['roles']['dbs']['boots'][0]['agent_activity']['samples']=[]
    raw=json.dumps(report,indent=2).encode();digest=hashlib.sha256(raw).hexdigest();bad_files['arms/a1/report.json']=raw
    snapshot=json.loads(bad_files['comparison-snapshot.json']);summary=snapshot['arms']['a1'];summary['report_sha256']=digest;summary['eligibility']['eligible']=True;summary['eligibility']['checks']={key:True for key in summary['eligibility']['checks']}
    raw=json.dumps(snapshot,indent=2).encode();bad_files['comparison-snapshot.json']=raw;proof['comparison_snapshot_exact_utf8']=raw.decode();proof['comparison_sha256']=hashlib.sha256(raw).hexdigest();proof['arms']['a1']['report_sha256']=digest
    values,proof=evidence_variant(bad_files,proof,'summary-claims-pass-but-activity-missing');review=reader.review_arm(values,proof,'a1')
    check('consistent-hashes-forged-pass-missing-activity-ineligible',review['eligible'] is False and review['checks']['matched_full_activity_samples'] is False)

    out={'schema':'crg-agent-fixed-io-offline-checks-v1','phase':'passed','observed_local_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
     'v3_source_sha256':hashlib.sha256(v3_source_raw).hexdigest(),'original_business_exception_source_sha256':hashlib.sha256(auditpath.read_bytes()).hexdigest(),
     'tests':rows,'scope':'offline pure error-boundary and admission unit checks; projected fixtures explicitly synthetic, not a vendor workload or qualified ABBA result',
     'actual_v2_remains_ineligible':True,'new_vendor_business_executed':False,'stable_release_accepted':False}
    temporary.cleanup()
    print(json.dumps(out,indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
