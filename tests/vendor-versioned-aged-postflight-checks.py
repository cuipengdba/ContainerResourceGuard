#!/usr/bin/env python3
"""Exact-candidate postflight contract checks; no synthetic elapsed acceptance."""
import ast
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    value = importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


tool = module('versioned_execution', 'vendor-versioned-aged-postflight.py')
original_checks = module('original_execution_checks', 'vendor-aged-postflight-checks.py')


def plan(short=False):
    value = dict(copy.deepcopy(tool.SHORT_BINDINGS if short else tool.LONG_BINDINGS),
                 mode='short-rehearsal' if short else 'seven-day-postflight',
                 worker='/var/tmp/crg-r78-20261111/tests/vendor-soak-load.py',
                 previous_binary='/var/tmp/crg-r71-20261111/binaries/previous')
    value['roles'] = {role: {'folder': ('/var/tmp/crg-realpaths64-20261111/v10-'+role+'-bw64/'+role+'-business'
                                      if short else '/var/tmp/crg-seven-day78-20261111/fixture/'+role+'-business'),
                            'aged_run_id': '20261111064'+('0' if role == 'dbs' else '1') if short else '20261111078',
                            'pod_sha256': role+'-pod'} for role in ['dbs', 'hisdbs']}
    if short:value['rehearsal_proof_sha256'] = 'proof'
    return value


class Checks(unittest.TestCase):
    def test_runtime_methods_remain_equal_to_frozen_template(self):
        original = Path(__file__).with_name('vendor-aged-postflight.py')
        self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), tool.TEMPLATE_SHA)
        old, new = ast.parse(original.read_text(encoding='utf-8')), ast.parse(Path(tool.__file__).read_text(encoding='utf-8'))
        for name in ['controls', 'adapt_pod', 'validate_native']:
            self.assertEqual(ast.dump(next(n for n in old.body if isinstance(n, ast.FunctionDef) and n.name == name)),
                             ast.dump(next(n for n in new.body if isinstance(n, ast.FunctionDef) and n.name == name)))
        def methods(tree):
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Execution')
            return {n.name: ast.dump(n) for n in cls.body if isinstance(n, ast.FunctionDef) and n.name != '__init__'}
        self.assertEqual(methods(old), methods(new))

    def test_original_native_thresholds_are_recomputed(self):
        with patch.object(original_checks, 'tool', tool):
            original_checks.Checks().test_native_recomputes_original_thresholds()

    def test_bindings_reject_old_binary_run_and_arbitrary_targets(self):
        for short in [False, True]:
            p = plan(short);tool.fixed_bindings(p, short)
            for key in ['work_root', 'namespace', 'run_id', 'worker', 'previous_binary']:
                changed = copy.deepcopy(p);changed[key] = 'other'
                with self.subTest(short=short, key=key), self.assertRaises(tool.Rejected):tool.fixed_bindings(changed, short)
            changed = copy.deepcopy(p);changed['roles']['dbs']['aged_run_id'] = '20261111057'
            with self.assertRaisesRegex(tool.Rejected, 'FIXED_AGED_ROLE'):tool.fixed_bindings(changed, short)
            with self.assertRaisesRegex(tool.Rejected, 'MODE_MISMATCH'):tool.fixed_bindings(p, not short)

    def test_checked_plan_rejects_changed_contract_before_inventory(self):
        p = dict(plan(), schema='crg-versioned-aged-execution-v1', criteria=copy.deepcopy(tool.CRITERIA),
                 pins=copy.deepcopy(tool.PINS), embedded_version='v1.0.0')
        for key, value in [('schema', 'crg-aged-execution-v1'), ('embedded_version', 'dev'),
                           ('criteria', dict(tool.CRITERIA, native_seconds_each_role=30)),
                           ('pins', dict(tool.PINS, binary='f'*64))]:
            changed = copy.deepcopy(p);changed[key] = value
            with patch.object(tool.gate, 'read_json', return_value=(changed, 'a'*64)), self.assertRaisesRegex(tool.Rejected, 'EXECUTION_PLAN_CONTRACT'):
                tool.checked_plan(Path('unused'), 'a'*64, False)
        with patch.object(tool.gate, 'read_json', return_value=(p, 'a'*64)), self.assertRaisesRegex(tool.Rejected, 'EXECUTION_PLAN_DIGEST'):
            tool.checked_plan(Path('unused'), 'b'*64, False)

    def test_pending_uses_exact_lineage_without_inventory_or_writes(self):
        p = plan();frozen = {'fixed': True};state = {'phase': 'pending', 'runner_identity_verified_live': True, 'postflight_allowed': False}
        inputs = ('frozen', 'launch', 'outer', 'campaign');seal = {'private': 'seal'}
        with patch.object(tool.lineage, 'load_plan', return_value=(frozen, tool.LINEAGE_PLAN_SHA)), \
             patch.object(tool.gate, 'read_json', return_value=(seal, tool.LINEAGE_SEAL_SHA)), \
             patch.object(tool.lineage, 'component', return_value=(state, inputs)), \
             patch.object(tool.lineage, 'readiness', return_value=state) as gate, \
             patch.object(tool, 'no_other_mounts', side_effect=AssertionError('pending must not inspect terminal data')):
            self.assertIs(tool.readiness(p), state)
            gate.assert_called_once_with(frozen, tool.LINEAGE_PLAN_SHA, seal, tool.LINEAGE_SEAL_SHA, tool.LINEAGE_SEAL_SHA, state, inputs)

    def test_terminal_still_requires_full_lineage_and_unused_sources(self):
        p = plan();frozen = {};inputs = ();state = {'phase': 'component-accepted'}
        ready = {'phase': 'ready-for-postflight', 'postflight_allowed': True, 'postflight_executed': False, 'P10_complete': False}
        with patch.object(tool.lineage, 'load_plan', return_value=(frozen, tool.LINEAGE_PLAN_SHA)), \
             patch.object(tool.gate, 'read_json', return_value=({}, tool.LINEAGE_SEAL_SHA)), \
             patch.object(tool.lineage, 'component', return_value=(state, inputs)), \
             patch.object(tool.lineage, 'readiness', return_value=ready), patch.object(tool, 'no_other_mounts') as mounts:
            self.assertFalse(tool.readiness(p)['postflight_executed'])
            mounts.assert_called_once_with([Path(x['folder']) for x in p['roles'].values()])

    def test_short_requires_own_completed_source_and_stopped_runner(self):
        p = plan(True);proof = {'phase': 'passed', 'namespace_absent': True,
            'tests': [{'name': str(x), 'passed': True} for x in range(12)], 'sources': {'v10': {'revision': tool.PINS['revision'], 'binary_sha256': tool.PINS['binary']}},
            'build_info': {'version': 'v1.0.0'}, 'job_sha256': '4bb896692b38ddb6dd7c28a9e019c81b4727f2f0ebcd664ca2f2318331d2de77'}
        launch = dict(pid=123, start_ticks=456, entry='/var/tmp/crg-r64-20261111/business-runner.py',
                      job_sha256=proof['job_sha256'], binary_sha256=tool.PINS['binary'], source_revision=tool.PINS['revision'])
        def read(path):
            if path.name == 'report.json':return proof, 'proof'
            if path.name == 'launch.json':return launch, 'launch'
            if path.name == 'business.exit.json':return {'exit': 0, 'job_sha256': proof['job_sha256']}, 'exit'
            value = original_checks.native();value['run_id'] = path.parent.name.removeprefix('crg-soak-');return value, 'native'
        def digest(path):
            value = tool.PINS['binary'] if path.name == 'crg' else tool.PINS['cache'] if path.name == 'containercacheguard' else ('hisdbs' if 'hisdbs' in str(path) else 'dbs')+'-pod'
            return {'sha256': value}
        with patch.object(tool.gate, 'read_json', side_effect=read), patch.object(tool.gate, 'digest', side_effect=digest), \
             patch.object(tool.gate, 'namespace', return_value=None), patch.object(tool.gate, 'proc', return_value={'live': False}), patch.object(tool, 'no_other_mounts'):
            self.assertTrue(tool.readiness(p)['postflight_allowed']);self.assertFalse(tool.readiness(p)['seven_day_accepted'])
            with patch.object(tool.gate, 'proc', return_value={'live': True}), self.assertRaisesRegex(tool.Rejected, 'SHORT_RUNNER_NOT_TERMINAL'):tool.readiness(p)
            proof['sources']['v10']['binary_sha256'] = 'f'*64
            with self.assertRaisesRegex(tool.Rejected, 'SHORT_PROOF'):tool.readiness(p)

    @unittest.skipUnless(os.name == 'posix', 'POSIX mount containment; Linux executes every case')
    def test_source_mount_guard_allows_only_constrained_readonly_ancestors(self):
        folder = Path('/var/tmp/crg-seven-day78-20261111/fixture/dbs-business')
        pod = {'spec': {'volumes': [{'name': 'root', 'hostPath': {'path': '/'}}], 'containers': [{
            'securityContext': {'allowPrivilegeEscalation': False, 'capabilities': {'drop': ['ALL'], 'add': ['SYS_TIME']}},
            'volumeMounts': [{'name': 'root', 'readOnly': True}]}]}}
        def invoke(value):
            with patch.object(tool.gate, 'command', return_value=json.dumps({'items': [value]})):tool.no_other_mounts([folder])
        invoke(pod)
        cases = [lambda p: p['spec']['volumes'][0]['hostPath'].update(path=str(folder)),
                 lambda p: p['spec']['containers'][0]['volumeMounts'][0].update(readOnly=False),
                 lambda p: p['spec']['containers'][0]['volumeMounts'][0].update(mountPropagation='Bidirectional'),
                 lambda p: p['spec']['containers'][0]['securityContext'].update(privileged=True),
                 lambda p: p['spec']['containers'][0]['securityContext'].update(allowPrivilegeEscalation=True),
                 lambda p: p['spec']['containers'][0]['securityContext']['capabilities'].update(add=['SYS_ADMIN']),
                 lambda p: p['spec']['containers'][0]['securityContext']['capabilities'].update(drop=[])]
        for mutate in cases:
            changed = copy.deepcopy(pod);mutate(changed)
            with self.assertRaisesRegex(tool.Rejected, 'AGED_DATA_ALREADY_MOUNTED'):invoke(changed)

    def test_cleanup_and_existing_root_stay_protected(self):
        with patch.object(original_checks, 'tool', tool):
            original_checks.Checks().test_cleanup_checks_uid_without_requiring_live_business()
            original_checks.Checks().test_no_report_write_before_exclusive_work_root()

    def test_execute_pending_marker_and_fresh_gate_precede_any_work(self):
        p = plan();pending = {'phase': 'pending', 'postflight_allowed': False}
        ready = {'phase': 'ready-for-postflight', 'postflight_allowed': True}
        for values, marker, expected in [([pending], '', 'pending'), ([ready], '', 'EXPLICIT_LAB_MARKER'),
                                          ([ready, pending], 'authorized-disposable-test-node-only', 'READINESS_CHANGED')]:
            with patch.object(sys, 'argv', ['tool', '--plan', 'unused', '--plan-sha256', 'a'*64, '--execute']), \
                 patch.object(sys, 'platform', 'linux'), patch.object(tool.os, 'geteuid', return_value=0, create=True), \
                 patch.dict(os.environ, {'CRG_AGED_POSTFLIGHT': marker}), patch.object(tool, 'checked_plan', return_value=p), \
                 patch.object(tool, 'readiness', side_effect=values), patch.object(tool, 'Execution') as execution, patch('sys.stdout', new_callable=io.StringIO) as output:
                code = tool.main();execution.assert_not_called();text = output.getvalue()
                self.assertIn(expected, text);self.assertEqual(code, 2 if expected == 'pending' else 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
