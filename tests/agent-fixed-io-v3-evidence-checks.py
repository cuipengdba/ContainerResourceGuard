#!/usr/bin/env python3
"""Check the V3 evidence reader using real A1/B1/B2 and synthetic negatives.

No node connection, signals, controller writes or vendor workload are executed.
Changed fixtures have consistently recomputed artifact digests; they are never
represented as new vendor observations.
"""
import argparse
import copy
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--evidence',type=Path)
    parser.add_argument('--b1-evidence',type=Path)
    parser.add_argument('--b2-evidence',type=Path)
    args=parser.parse_args();repo=args.repo.resolve()
    evidence=args.evidence or repo/'docs/test-evidence/agent-activity449-a1.json.gz'
    path=repo/'tests/analyze-agent-fixed-io-comparison-v3.py'
    spec=importlib.util.spec_from_file_location('fixed_activity_v3_review',path)
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    original_files,original_proof=reader.read_evidence(evidence)
    original=reader.review_arm(original_files,original_proof,'a1')
    assert original['eligible'] and original['SQL_errors']==original['API_errors']==0
    rows=[{'name':'actual-A1-full-evidence-independently-eligible','passed':True,'synthetic':False}]
    b1_files,b1_proof=reader.read_evidence(args.b1_evidence or repo/'docs/test-evidence/agent-activity449-b1.json.gz')
    b1=reader.review_arm(b1_files,b1_proof,'b1')
    assert b1['eligible'] and b1['SQL_errors']==b1['API_errors']==0
    rows.append({'name':'actual-B1-full-paused-and-resumed-evidence-independently-eligible','passed':True,'synthetic':False})
    b2_files,b2_proof=reader.read_evidence(args.b2_evidence or repo/'docs/test-evidence/agent-activity449-b2.json.gz')
    b2=reader.review_arm(b2_files,b2_proof,'b2')
    assert b2['phase']==b2['native_phase']=='failed' and b2['reason']=='NATIVE_COMPLETION_EXIT'
    assert b2['actual_seconds']>=600 and b2['SQL_errors']==2 and b2['API_errors']==5
    assert 'native' not in json.loads(b2_files['arms/b2/report.json'])['roles']['dbs']['boots'][0]
    rows.append({'name':'actual-failed-B2-retains-full-raw-native-without-duplicate-summary','passed':True,'synthetic':False})
    with tempfile.TemporaryDirectory(prefix='crg-v3-evidence-negatives-') as folder:
        target=Path(folder)/'synthetic.json.gz'

        def exercise(label,change,reason=None,failed_check=None,arm='a1'):
            files=copy.deepcopy(original_files if arm=='a1' else b1_files);proof=copy.deepcopy(original_proof if arm=='a1' else b1_proof)
            change(files,proof)
            manifest={'schema':'crg-agent-fixed-io-exact-files-v2','files':{name:{'bytes':len(raw),'sha256':reader.sha(raw)} for name,raw in files.items()}}
            raw=json.dumps(proof).encode()
            bundle={'schema':'crg-agent-fixed-io-exact-evidence-v2','manifest':manifest,'files':{name:{'exact_utf8':raw.decode()} for name,raw in files.items()},'independent_exact_utf8':raw.decode(),'independent_sha256':reader.sha(raw)}
            target.write_bytes(gzip.compress(json.dumps(bundle).encode(),mtime=0))
            values,independent=reader.read_evidence(target)
            try:
                result=reader.review_arm(values,independent,arm)
            except ValueError as error:
                assert reason is not None and str(error)==reason,(label,str(error),reason)
            else:
                assert reason is None and result['eligible'] is False and result['checks'][failed_check] is False,(label,result)
            rows.append({'name':label,'passed':True,'synthetic':True})

        def rebind(files,proof,report_change=None,native_change=None,arm='a1'):
            prefix='arms/'+arm+'/';report=json.loads(files[prefix+'report.json']);snapshot=json.loads(files['comparison-snapshot.json'])
            if native_change:
                native=json.loads(files[prefix+'dbs/native/load.json']);native_change(native)
                raw=json.dumps(native).encode();files[prefix+'dbs/native/load.json']=raw
                report['roles']['dbs']['boots'][0]['native']=native
                snapshot['arms'][arm]['native_report_sha256']=reader.sha(raw)
            if report_change:report_change(report)
            raw=json.dumps(report).encode();files[prefix+'report.json']=raw
            digest=reader.sha(raw);snapshot['arms'][arm]['report_sha256']=digest
            snapshot['arms'][arm]['eligibility']['eligible']=True
            snapshot['arms'][arm]['eligibility']['checks']={key:True for key in snapshot['arms'][arm]['eligibility']['checks']}
            proof['arms'][arm]['report_sha256']=digest
            raw=json.dumps(snapshot).encode();files['comparison-snapshot.json']=raw
            proof['comparison_snapshot_exact_utf8']=raw.decode();proof['comparison_sha256']=reader.sha(raw)

        def changed_source(files,proof):files['sources/vendor-agent-fixed-io-comparison-v3.py']+=b'\n'
        exercise('consistent-digests-changed-frozen-executor-rejected',changed_source,'FROZEN_EXECUTOR_AND_PLAN')
        def changed_qualification(files,proof):files['sources/error-boundary-qualification.json']+=b'\n'
        exercise('consistent-digests-changed-node-qualification-rejected',changed_qualification,'QUALIFIED_SOURCE:error-boundary-qualification.json')
        def wrong_namespace(files,proof):proof['arms']['a1']['namespace']+='-synthetic'
        exercise('wrong-cleaned-namespace-rejected',wrong_namespace,'EXACT_ARM_NAMESPACE')
        def missing_helper(files,proof):del proof['instances']['a1-0-helper']
        exercise('missing-independent-helper-identity-rejected',missing_helper,'ALL_SEVEN_INDEPENDENT_ARM_IDENTITIES')
        def wrong_helper(files,proof):proof['instances']['a1-0-helper']['expected_start_ticks']+=1
        exercise('wrong-helper-birth-rejected',wrong_helper,'EXACT_CLEANUP_IDENTITY:helper')
        def unbound_native(files,proof):
            native=json.loads(files['arms/a1/dbs/native/load.json']);native['elapsed_seconds']=599
            files['arms/a1/dbs/native/load.json']=json.dumps(native).encode()
        exercise('changed-native-not-bound-to-snapshot-rejected',unbound_native,'EXACT_NATIVE_REPORT_BINDING')
        def unequal_native(files,proof):rebind(files,proof,lambda report:report['roles']['dbs']['boots'][0]['native'].update(elapsed_seconds=599))
        exercise('boot-and-raw-native-disagreement-rejected',unequal_native,'NATIVE_BOOT_AND_RAW_EQUAL')
        def missing_passed_native(files,proof):rebind(files,proof,lambda report:report['roles']['dbs']['boots'][0].pop('native'))
        exercise('missing-duplicate-on-passed-arm-still-rejected',missing_passed_native,'FAILED_NATIVE_RAW_REQUIRED_WITHOUT_DUPLICATE')
        def short_native(files,proof):rebind(files,proof,native_change=lambda native:native.update(elapsed_seconds=599))
        exercise('fully-rebound-short-native-remains-ineligible',short_native,failed_check='original_full600')
        def missing_activity(files,proof):rebind(files,proof,lambda report:report['roles']['dbs']['boots'][0]['agent_activity'].update(samples=[]))
        exercise('forged-summary-pass-missing-activity-ineligible',missing_activity,failed_check='matched_full_activity_samples')
        def wrong_parent(files,proof):rebind(files,proof,lambda report:report['roles']['dbs']['boots'][0]['activity_parent_observation'].update(helper_parent_pid=1))
        exercise('forged-summary-pass-wrong-helper-parent-ineligible',wrong_parent,failed_check='actual_sourced_helper_identity')
        def changed_kernel(files,proof):rebind(files,proof,lambda report:report['roles']['dbs']['boots'][0]['samples'][0]['actual_kernel_readbacks'].update({'cpu.max':'1 100000'}))
        exercise('forged-summary-pass-changed-kernel-quota-ineligible',changed_kernel,failed_check='fixed_original_numeric_values')
        def early_end(files,proof):rebind(files,proof,lambda report:report['roles']['dbs']['boots'][0]['agent_activity'].update(effective_activity_ended_epoch=0))
        exercise('forged-summary-pass-early-activity-end-ineligible',early_end,failed_check='full600_activity_envelope')
        def wrong_resume(files,proof):rebind(files,proof,lambda report:report['roles']['dbs']['boots'][0]['agent_activity']['session'].update(resumed_same_instance=False),arm='b1')
        exercise('B1-missing-same-instance-resume-ineligible',wrong_resume,failed_check='activity_session_closed',arm='b1')
        def wrong_signals(files,proof):rebind(files,proof,lambda report:report['roles']['dbs']['boots'][0]['agent_activity']['session'].update(CONT_count=0),arm='b1')
        exercise('B1-missing-matched-CONT-ineligible',wrong_signals,failed_check='activity_session_closed',arm='b1')
        def CPU_progress(files,proof):
            def change(report):report['roles']['dbs']['boots'][0]['agent_activity']['samples'][0]['user_ticks']+=1
            rebind(files,proof,change,arm='b1')
        exercise('B1-CPU-progress-during-claimed-pause-ineligible',CPU_progress,failed_check='matched_full_activity_samples',arm='b1')
        def watchdog_resume(files,proof):rebind(files,proof,lambda report:report['roles']['dbs']['boots'][0]['agent_activity']['session']['watchdog'].update(CONT_count=1),arm='b1')
        exercise('B1-early-watchdog-resume-ineligible',watchdog_resume,failed_check='same_watchdog_normal_close',arm='b1')
    out={'schema':'crg-agent-fixed-io-v3-evidence-checks-v1','phase':'passed','observed_local_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'reader_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'tests':rows,
         'scope':'three real A1/B1/B2 replays and seventeen local synthetic rejection cases; failed B2 remains a business failure; no new vendor workload',
         'whole_ABBA_accepted':False,'original32_accepted':False,'stable_release_accepted':False}
    print(json.dumps(out,indent=2));return 0


if __name__=='__main__':
    raise SystemExit(main())
