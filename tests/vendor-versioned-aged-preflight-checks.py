#!/usr/bin/env python3
"""Check the versioned read-only adapter; synthetic time is never acceptance."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

path = Path(__file__).with_name('vendor-versioned-aged-preflight.py')
spec = importlib.util.spec_from_file_location('versioned_gate', path)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def plan():
    return dict(copy.deepcopy(gate.PINS), postflight_criteria=copy.deepcopy(gate.CRITERIA),
                P10_complete=False, preflight_sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def inputs():
    return ({}, {'pid': 123, 'start_ticks': 456}, {'namespace_uid': 'owned', 'build_info': {'version': 'v1.0.0'}},
            {'roles': {r: {'workload': {'started_utc': r+'-start', 'primary_start_time_initial': r+'-primary'}}
                       for r in ['dbs', 'hisdbs']}})


def seal():
    return {'schema': 'crg-aged-lineage-seal-v1', 'seal_is_not_acceptance': True,
            'plan_sha256': 'pinned-plan', 'launch': inputs()[1], 'namespace_uid': 'owned',
            'source_revision': gate.PINS['source_revision'], 'binary_sha256': gate.PINS['binary_sha256'],
            'roles': {r: {'native_started_utc': r+'-start', 'primary_start': r+'-primary'}
                      for r in ['dbs', 'hisdbs']}}


class Checks(unittest.TestCase):
    def test_exact_contract_rejects_old_run_source_and_targets(self):
        gate.validate_contract(plan())
        for key, value in gate.PINS.items():
            with self.subTest(key=key):
                wrong = plan();wrong[key] = 'other' if isinstance(value, str) else []
                with self.assertRaisesRegex(gate.Rejected, 'VERSIONED_BINDING_'):gate.validate_contract(wrong)
        for key, value in [('run_id', '20261111057'), ('binary_sha256', '3a1ce7dbf5630f8f1c823005ceb4958653c6c235b2ba5026956ca6597f1926f9')]:
            wrong = plan();wrong[key] = value
            with self.assertRaises(gate.Rejected):gate.validate_contract(wrong)

    def test_original_criteria_cannot_be_relaxed(self):
        for key, value in [('errors', 1), ('errors', False), ('PG_API_managed_seconds', 600),
                           ('new_native_smoke_seconds_each_role', 30), ('coverage_min', 0.5),
                           ('request_max_seconds', 10), ('payload_bytes_each_role', 1024)]:
            with self.subTest(key=key, value=value):
                wrong = plan();wrong['postflight_criteria'][key] = value
                with self.assertRaisesRegex(gate.Rejected, 'CRITERIA'):gate.validate_contract(wrong)
        wrong = plan();wrong['postflight_criteria']['same_manual_budget_as_continuous']['read_write_bps'] *= 2
        with self.assertRaisesRegex(gate.Rejected, 'CRITERIA'):gate.validate_contract(wrong)

    def test_component_delegates_actual_audit_and_checks_embedded_version(self):
        state = {'phase': 'pending', 'runner_identity_verified_live': True, 'postflight_allowed': False}
        p = plan();i = inputs()
        with patch.object(gate.base, 'component', return_value=(state, i)) as core:
            self.assertEqual(gate.component(p), (state, i));core.assert_called_once_with(p)
        i[2]['build_info']['version'] = 'next-compatibility-contract'
        with patch.object(gate.base, 'component', return_value=(state, i)), self.assertRaisesRegex(gate.Rejected, 'EMBEDDED_VERSION'):
            gate.component(p)
        with patch.object(gate.base, 'component', side_effect=gate.Rejected('RUNNER_NOT_LIVE')), self.assertRaisesRegex(gate.Rejected, 'RUNNER_NOT_LIVE'):
            gate.component(p)

    @unittest.skipUnless(os.name == 'posix', 'POSIX absolute lab paths; Linux executes this method')
    def test_load_plan_pins_digest_and_immutable_reader(self):
        with tempfile.TemporaryDirectory() as work:
            p = Path(work)/'plan.json';p.write_text(json.dumps(plan()))
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(gate.load_plan(p, digest)[1], digest)
            with self.assertRaisesRegex(gate.Rejected, 'PLAN_DIGEST'):gate.load_plan(p, '0'*64)
            wrong = plan();wrong['preflight_sha256'] = '0'*64;p.write_text(json.dumps(wrong))
            with self.assertRaisesRegex(gate.Rejected, 'PREFLIGHT_SOURCE'):
                gate.load_plan(p, hashlib.sha256(p.read_bytes()).hexdigest())

    def test_pending_never_calls_postflight_or_changes_files(self):
        with tempfile.TemporaryDirectory() as work:
            p = Path(work)/'sentinel';p.write_bytes(b'untouched')
            state = {'phase': 'pending', 'runner_identity_verified_live': True, 'postflight_allowed': False}
            with patch.object(gate.base, 'verify_lineage', side_effect=AssertionError('must not call')):
                result = gate.readiness(plan(), 'pinned-plan', seal(), 'sealed', 'sealed', state, inputs())
            self.assertIs(result, state);self.assertEqual(p.read_bytes(), b'untouched')
            self.assertEqual(list(Path(work).iterdir()), [p])

    def test_pending_rejects_mixed_or_unpinned_seal(self):
        state = {'phase': 'pending'}
        for key, value in [('binary_sha256', 'f'*64), ('source_revision', 'f'*40),
                           ('namespace_uid', 'other'), ('plan_sha256', 'other'), ('roles', {}),
                           ('seal_is_not_acceptance', False), ('launch', {'pid': 123})]:
            with self.subTest(key=key):
                wrong = seal();wrong[key] = value
                with self.assertRaisesRegex(gate.Rejected, 'SEAL_BINDING'):
                    gate.readiness(plan(), 'pinned-plan', wrong, 'sealed', 'sealed', state, inputs())
        with self.assertRaisesRegex(gate.Rejected, 'SEAL_DIGEST'):
            gate.readiness(plan(), 'pinned-plan', seal(), 'changed', 'sealed', state, inputs())

    def test_capture_delegates_full_live_check_and_binds_native_start(self):
        p, i, s = plan(), inputs(), seal()
        # Actual measuring campaign shape has no final workload member.
        i[3]['roles'] = {r: {'fixed_controls': {}, 'samples': []} for r in ['dbs', 'hisdbs']}
        def read_native(filename):
            role = 'hisdbs' if 'hisdbs-business' in str(filename) else 'dbs'
            return dict(phase='running', run_id=p['run_id'], requested_duration_seconds=604800,
                        started_utc=role+'-start', primary_start_time_initial=role+'-primary'), 'digest'
        with patch.object(gate.base, 'capture', return_value=copy.deepcopy(s)) as core, patch.object(gate.base, 'read_json', side_effect=read_native):
            result = gate.capture(p, 'pinned-plan', {'phase': 'pending'}, i)
            self.assertEqual(result['phase'], 'lineage-captured-not-accepted')
            core.assert_called_once_with(p, 'pinned-plan', {'phase': 'pending'}, i)
        for change in ['primary', 'run', 'phase']:
            def wrong_native(filename):
                value, digest = read_native(filename)
                if change == 'run':value['run_id'] = '20261111057'
                if change == 'phase':value['phase'] = 'passed'
                return value, digest
            wrong_seal = copy.deepcopy(s)
            if change == 'primary':wrong_seal['roles']['dbs']['primary_start'] = 'changed'
            with self.subTest(change=change), patch.object(gate.base, 'capture', return_value=wrong_seal), patch.object(gate.base, 'read_json', side_effect=wrong_native), self.assertRaisesRegex(gate.Rejected, 'LIVE_NATIVE_LINEAGE'):
                gate.capture(p, 'pinned-plan', {'phase': 'pending'}, i)

    def test_terminal_still_requires_full_lineage_and_is_not_release(self):
        p, i, s = plan(), inputs(), seal();state = {'phase': 'component-accepted', 'P10_complete': False}
        ready = {'phase': 'ready-for-postflight', 'postflight_allowed': True, 'postflight_executed': False,
                 'P10_complete': False, 'release_accepted': False}
        with patch.object(gate.base, 'verify_lineage', return_value=ready) as core:
            result = gate.readiness(p, 'pinned-plan', s, 'sealed', 'sealed', state, i)
            core.assert_called_once_with(p, 'pinned-plan', s, i)
            self.assertFalse(result['postflight_executed']);self.assertFalse(result['release_accepted'])
        with patch.object(gate.base, 'verify_lineage', side_effect=gate.Rejected('AGED_INPUT_CHANGED')), self.assertRaisesRegex(gate.Rejected, 'AGED_INPUT_CHANGED'):
            gate.readiness(p, 'pinned-plan', s, 'sealed', 'sealed', state, i)


if __name__ == '__main__':
    unittest.main()
