#!/usr/bin/env python3
"""Synthetic fault checks only; no native duration or business acceptance."""
import copy
import datetime
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve()
spec = importlib.util.spec_from_file_location('fresh1880_gate', HERE.with_name('lineage.py'))
g = importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
spec = importlib.util.spec_from_file_location('original_audit_fixtures', HERE.parents[1]/'soak-report-audit-checks.py')
f = importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
B = g.BINDING


def data():
    campaigns = {}
    for index, stage in enumerate(B['stages']):
        name = stage['phase'];v = f.fixture(name);v.update(B['campaign_pins'])
        v.update(source_run_id=stage.get('source_run_id'))
        delta = datetime.timedelta(seconds=index*86410)
        for role in v['roles'].values():
            n = role['workload']
            n['run_id'] = stage['run_id']
            for key in ['started_utc', 'measurement_finished_utc']:
                n[key] = (datetime.datetime.fromisoformat(n[key])+delta).isoformat()
            if name == 'enforce':n['source_run_id'] = stage['source_run_id']
        for cycle in v['backups']:
            for key in ['content_started_epoch', 'content_ended_epoch']:cycle[key] += delta.total_seconds()
        campaigns[name] = v
    launch = dict(pid=100, start_ticks=101, entry=str(Path(B['runner_root'])/'runner.py'))
    outer = dict(sources={'candidate1':{'revision':B['source_revision'],'binary_sha256':B['binary_sha256']}},
        version='v1.0.0', job_sha256=B['long_job_sha256'], plan_sha256=B['long_plan_sha256'],
        runtime_inherited=False, stable_release_accepted=False, namespace=B['namespace'], namespace_uid='owned',
        phase='passed', tests=[{'name':n,'passed':True} for n in sorted(g.expected_checks())],
        phases={}, roles={}, cleanup={}, namespace_absent=True, aged_fixture_retained=True, postflight_required=True)
    for stage in B['stages']:
        name = stage['phase'];outer['phases'][name] = dict(native_accepted=True,exit=0,
            run_id=stage['run_id'],requested_seconds=stage['seconds'],source_run_id=stage.get('source_run_id'),
            output=str(Path(B['component_root'])/('campaign-'+name)),
            campaign_original_absent=True, report_sha256=hashlib.sha256(name.encode()).hexdigest(),actual_cycles=stage['cycles'])
    for role in ['dbs','hisdbs']:
        key='candidate1-'+role+'-bw64'
        outer['roles'][key] = dict(fixture_identity={'group':'/nonexistent-crg-gate/'+role,'pod_parent':'/nonexistent-crg-parent/'+role},
            primary_start='same-primary',original_controls={'cpu.max':'original'},enforce_controls={'cpu.max':'new'},enforce_journal={'identity':'owned'},
            enforce_transition={'same_fixed_processes':True,'before':{'fixed_processes':{'pid':1},'controls':{'cpu.max':'original'}},
                'after':{'fixed_processes':{'pid':1},'controls':{'cpu.max':'new'}},'exact_journal':{'identity':'owned'}})
        outer['cleanup'][key]=dict(leaf_absent=True,parent_absent=True,all_registered_absent=True,registered_processes=[{'pid':200,'start_ticks':201}])
    receipt=dict(exit=0,job_sha256=B['long_job_sha256'],plan_sha256=B['long_plan_sha256'])
    return outer,campaigns,launch,receipt


def run_component(outer,campaigns,launch,receipt,live=False):
    def read(path,*args):
        if path.name=='report.json' and path.parent.name.startswith('campaign-'):
            phase=path.parent.name.removeprefix('campaign-');return campaigns[phase],hashlib.sha256(phase.encode()).hexdigest()
        if path.name=='report.json':return outer,'a'*64
        if path.name=='worker.json':return dict(pid=102,start_ticks=103,entry=str(Path(B['runner_root'])/'job.py')),'b'*64
        if path.name=='exit.json':return receipt,'c'*64
        raise AssertionError('unexpected read')
    def exists(path):
        if path.name=='exit.json':return receipt is not None
        return path.name=='report.json' and path.parent.name.startswith('campaign-') and path.parent.name.removeprefix('campaign-') in campaigns
    with patch.object(g,'source_inputs',return_value=({'source_sha256':{},'private_fixture_sha256':{}},launch)),patch.object(g,'read_json',side_effect=read),patch.object(Path,'exists',exists),patch.object(g,'process_live',return_value=live),patch.object(g.base,'proc',return_value={'live':False}):
        return g.component()


class Checks(unittest.TestCase):
    def test_complete_synthetic_three_stages_is_only_lineage_prerequisite(self):
        state,_=run_component(*data());self.assertEqual(state['phase'],'component-accepted')
        self.assertFalse(state['postflight_allowed']);self.assertFalse(state['release_accepted'])
        self.assertEqual([state['reports'][n]['audit']['accepted_engine_cycles'] for n in ['baseline','enforce','acceptance']],[4,4,28])

    def test_contract_rejects_every_changed_binding(self):
        if sys.platform=='linux':g.contract(copy.deepcopy(B))
        for key in B:
            wrong=copy.deepcopy(B);wrong[key]=None
            with self.subTest(key=key),self.assertRaisesRegex(g.Rejected,'FROZEN_SOURCE37_CONTRACT'):g.contract(wrong)

    def test_original_capture_guards_preserved_except_user_memory_policy(self):
        expected=inspect.getsource(g.base.capture).replace('def capture(','def capture_core(',1).replace("{'cpu.max', 'memory.max', 'io.max'}","{'cpu.max', 'memory.high', 'io.max'}")
        self.assertEqual(inspect.getsource(g.capture_core).strip(),expected.strip())

    def test_early_or_foreign_campaign_and_errors_are_rejected_by_original_auditor(self):
        mutations=[lambda v:v.update(requested_seconds=600),
            lambda v:v.update(agent_sha256='f'*64),lambda v:v['roles']['dbs']['workload'].update(elapsed_seconds=600),
            lambda v:v['roles']['dbs']['workload']['sql'].update(errors=1),
            lambda v:v['roles']['hisdbs']['workload']['api'].update(max_seconds=5.1),
            lambda v:v['roles']['dbs']['workload']['sql'].update(sample_coverage=.5),lambda v:v['backups'].pop()]
        reasons=['CAMPAIGN_DURATION_OR_PHASE','SOURCE_DIGEST','NATIVE_DURATION','NATIVE_ERRORS','NATIVE_MAXIMUM','NATIVE_SAMPLE_COVERAGE','ENGINE_CYCLE_COUNT']
        for index,mutate in enumerate(mutations):
            values=data();mutate(values[1]['acceptance'])
            with self.subTest(case=index),self.assertRaisesRegex(g.Rejected,reasons[index]):run_component(*values)

    def test_real_campaign_shape_has_no_top_level_run_id_and_rejects_old_phase_identity(self):
        values=data();self.assertNotIn('run_id',values[1]['acceptance'])
        run_component(*values)
        values[0]['phases']['acceptance']['run_id']='20261111078'
        with self.assertRaisesRegex(g.Rejected,'FRESH_PHASE_RUN_ID'):run_component(*values)

    def test_main_checks_cannot_be_missing_extra_or_false(self):
        for which in ['missing','extra','false']:
            values=data();tests=values[0]['tests']
            if which=='missing':tests.pop()
            elif which=='extra':tests.append({'name':'easier-check','passed':True})
            else:tests[0]['passed']=False
            with self.subTest(case=which),self.assertRaises(g.Rejected):run_component(*values)

    def test_terminal_requires_exact_exit_and_dead_original_handles(self):
        for value in [False,1,None]:
            values=data();values[3]['exit']=value
            with self.subTest(value=value),self.assertRaises(g.Rejected):run_component(*values)
        with self.assertRaises(g.Rejected):run_component(*data(),live=True)

    def test_old_clock_cleanup_transition_or_primary_cannot_transfer(self):
        mutations=[lambda v:v.update(runtime_inherited=True),lambda v:v['cleanup']['candidate1-dbs-bw64'].update(leaf_absent=False),
            lambda v:v['roles']['candidate1-dbs-bw64']['enforce_transition']['after']['fixed_processes'].update(pid=2),
            lambda v:v['roles']['candidate1-hisdbs-bw64'].update(primary_start='other')]
        for index,mutate in enumerate(mutations):
            values=data();mutate(values[0])
            with self.subTest(case=index),self.assertRaises(g.Rejected):run_component(*values)

    def test_native_stage_overlap_rejected(self):
        values=data()
        for role in values[1]['acceptance']['roles'].values():role['workload']['started_utc']='2026-01-01T00:00:00+00:00'
        with self.assertRaisesRegex(g.Rejected,'ORIGINAL_STAGE_ORDER'):run_component(*values)

    def test_live_baseline_is_pending_even_with_no_acceptance_report(self):
        values=list(data());values[0]['phase']='measuring-baseline';values[0]['tests']=[]
        values[1]={'baseline':values[1]['baseline']};values[1]['baseline']['phase']='measuring';values[3]=None
        state,_=run_component(*values,live=True)
        self.assertEqual(state['phase'],'pending');self.assertFalse(state['capture_allowed']);self.assertFalse(state['postflight_allowed'])
        with self.assertRaises(g.Rejected):run_component(*values,live=False)

    def test_baseline_or_enforce_cannot_capture_seven_day_lineage(self):
        for phase in ['measuring-baseline','measuring-enforce']:
            with patch.object(g,'capture_core',side_effect=AssertionError('must not touch any capture input')):
                with self.assertRaisesRegex(g.Rejected,'CAPTURE_ONLY_DURING_FRESH_SEVEN_DAY'):
                    g.capture({'phase':'pending','capture_allowed':False,'component_phase':phase},None)

    def test_capture_requires_original24h_accepted_before_seven_day(self):
        state={'phase':'pending','capture_allowed':True,'reports':{'baseline':{'audit':{'phase':'pending'}}}}
        with patch.object(g,'capture_core',side_effect=AssertionError('must not capture')):
            with self.assertRaisesRegex(g.Rejected,'CAPTURE_REQUIRES_BOTH_ORIGINAL24H'):g.capture(state,(None,None,{}))

    def test_old_or_changed_seal_never_grants_postflight(self):
        state={'phase':'pending','reports':{n:{'sha256':n} for n in ['baseline','enforce']}}
        with self.assertRaisesRegex(g.Rejected,'SEAL_DIGEST'):g.readiness(state,None,{},'a'*64,'b'*64)
        with self.assertRaisesRegex(g.Rejected,'FRESH_THREE_PHASE_SEAL'):g.readiness(state,None,{},'a'*64,'a'*64)


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Checks)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({'scope':'synthetic fault checks only, not native duration/business/postflight acceptance',
        'phase':'passed' if result.wasSuccessful() else 'failed','tests_run':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),'reader_sha256':hashlib.sha256(HERE.with_name('lineage.py').read_bytes()).hexdigest(),
        'binding_sha256':g.BINDING_SHA256,'release_accepted':False}))
    sys.exit(0 if result.wasSuccessful() else 1)
