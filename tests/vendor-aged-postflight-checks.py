#!/usr/bin/env python3
"""Synthetic contract tests; never a seven-day/postflight runtime claim."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('aged_execution', Path(__file__).with_name('vendor-aged-postflight.py'))
tool = importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)


def native():
    value = {'schema': 'crg-vendor-soak-v1', 'phase': 'passed', 'run_id': '20261111060',
             'test_phase': 'smoke', 'requested_duration_seconds': 600, 'elapsed_seconds': 600.2,
             'interrupted': False, 'threads_stopped': True, 'payload_integrity': True,
             'primary_not_restarted': True, 'primary_start_time_initial': 'same', 'primary_start_time_final': 'same',
             'initial_checksum': [16384, 134225920, 67108864, 'md5', 0],
             'final_checksum': [16384, 134225920, 67108864, 'md5', 300],
             'criteria': {'sql_period_seconds': 2, 'api_period_seconds': 5, 'maximum_seconds': 5,
                          'p95_upper_bound_seconds': 1, 'maximum_errors': 0, 'minimum_scheduled_samples_fraction': .98},
             'latency_bucket_upper_seconds': [.001, .005, .01, .02, .05, .1, .25, .5, 1, 2, 5, 'over-5']}
    for kind, count in [('sql', 300), ('api', 120)]:
        value[kind] = {'attempts': count, 'successes': count, 'errors': 0, 'max_seconds': .25,
                       'histogram': [0]*6+[count]+[0]*5, 'p95_bucket_upper_seconds': .25}
    return value


def execution_plan():
    folder = '/var/tmp/crg-seven-day57-20261111/fixture/'
    return {'mode': 'seven-day-postflight', 'lineage_plan': '/var/tmp/crg-aged59-tools-20261111/aged-plan.json',
            'lineage_plan_sha256': '58a8fe7c07c7655c13e1b54a83ad8afd63646947de9b8b8929f1d089dbe2a8cb',
            'lineage_seal': '/var/tmp/crg-aged59-tools-20261111/lineage-seal.json',
            'lineage_seal_sha256': 'd45cd434b6b614141dab56742207fa245c04f59c80d4469c514e7d255fd108bd',
            'work_root': '/var/tmp/crg-aged-postflight59-20261111', 'namespace': 'crg-vendor-lab-aged59-20261111',
            'roles': {role: {'folder': str(Path(folder)/(role+'-business')), 'aged_run_id': '20261111057'} for role in ['dbs', 'hisdbs']}}


class Checks(unittest.TestCase):
    def test_native_recomputes_original_thresholds(self):
        tool.validate_native(native(), '20261111060')
        mutations = [lambda x: x.update(elapsed_seconds=599.9), lambda x: x.update(elapsed_seconds=float('nan')),
                     lambda x: x.update(test_phase='acceptance'), lambda x: x.update(threads_stopped=False),
                     lambda x: x.update(primary_start_time_final='changed'), lambda x: x.update(interrupted=True),
                     lambda x: x['final_checksum'].__setitem__(3, 'changed'),
                     lambda x: x['criteria'].__setitem__('maximum_seconds', 6),
                     lambda x: x['sql'].__setitem__('max_seconds', 5.01),
                     lambda x: x['api'].__setitem__('errors', 1),
                     lambda x: x['sql'].__setitem__('attempts', 293),
                     lambda x: x['api'].__setitem__('histogram', [0]*9+[120, 0, 0]),
                     lambda x: x['sql'].__setitem__('p95_bucket_upper_seconds', .1),
                     lambda x: x.__setitem__('latency_bucket_upper_seconds', [1]*12)]
        for mutate in mutations:
            value = native();mutate(value)
            with self.subTest(mutation=repr(mutate)), self.assertRaises(tool.Rejected):
                tool.validate_native(value, '20261111060')

    def test_pending_never_starts_or_verifies_terminal_lineage(self):
        plan = execution_plan();frozen = {'component_root': '/var/tmp/crg-seven-day57-20261111', 'run_id': '20261111057',
            'postflight_root': plan['work_root'], 'postflight_namespace': plan['namespace']}
        launch = {'pid': 1234, 'start_ticks': 44}
        seal = {'plan_sha256': plan['lineage_plan_sha256'], 'launch': launch}
        pending = {'phase': 'pending', 'runner_identity_verified_live': True, 'postflight_allowed': False}
        with patch.object(tool.gate, 'load_plan', return_value=(frozen, plan['lineage_plan_sha256'])), \
             patch.object(tool.gate, 'read_json', return_value=(seal, plan['lineage_seal_sha256'])), \
             patch.object(tool.gate, 'component', return_value=(pending, (None, launch))), \
             patch.object(tool.gate, 'verify_lineage', side_effect=AssertionError('must not run')):
            self.assertEqual(tool.readiness(plan), pending)
            changed = copy.deepcopy(plan);changed['roles']['dbs']['aged_run_id'] = '20261111051'
            with self.assertRaisesRegex(tool.Rejected, 'AGED_ROLE_BINDING'):tool.readiness(changed)

    def test_terminal_readiness_delegates_exact_seal_and_gate(self):
        plan = execution_plan();frozen = {'component_root': '/var/tmp/crg-seven-day57-20261111', 'run_id': '20261111057',
            'postflight_root': plan['work_root'], 'postflight_namespace': plan['namespace']}
        seal = {'actual': 'private'};state = {'phase': 'component-accepted'};inputs = ('frozen', 'launch', 'outer', 'campaign')
        with patch.object(tool.gate, 'load_plan', return_value=(frozen, plan['lineage_plan_sha256'])), \
             patch.object(tool.gate, 'read_json', return_value=(seal, plan['lineage_seal_sha256'])), \
             patch.object(tool.gate, 'component', return_value=(state, inputs)), \
             patch.object(tool.gate, 'verify_lineage', return_value={'phase': 'ready-for-postflight', 'postflight_allowed': True}) as verify:
            result = tool.readiness(plan);self.assertTrue(result['postflight_allowed'])
            verify.assert_called_once_with(frozen, plan['lineage_plan_sha256'], seal, inputs)
            plan['lineage_seal_sha256'] = '0'*64
            with self.assertRaisesRegex(tool.Rejected, 'FROZEN_LINEAGE_BINDING'):tool.readiness(plan)

    @unittest.skipUnless(os.name == 'posix', 'native POSIX lab paths')
    def test_pod_adaptation_preserves_original_settings_and_private_files(self):
        folder = Path('/var/tmp/crg-short/dbs-business');work = Path('/var/tmp/crg-post')
        main = {'name': 'dbs', 'image': 'private:original', 'imagePullPolicy': 'Never',
                'resources': {'limits': {'cpu': '8', 'memory': '20Gi'}},
                'command': ['/bin/bash', '-c', 'gate; exec /bin/bash /opt/ccg/scripts/business-supervisor.sh'],
                'env': [{'name': 'MY_POD_NAMESPACE', 'value': 'old'}, {'name': 'PRIVATE', 'value': 'unchanged'}],
                'volumeMounts': [{'name': 'ccg', 'mountPath': '/opt/ccg', 'readOnly': True}, {'name': 'crg', 'mountPath': '/opt/crg', 'readOnly': True}]}
        pod = {'kind': 'Pod', 'metadata': {'name': 'dbs-business', 'namespace': 'old', 'labels': {'managed-by': 'crg-vendor-test'}},
               'spec': {'restartPolicy': 'Never', 'automountServiceAccountToken': False,
                        'containers': [main, {'name': 'isolated-dcs', 'imagePullPolicy': 'Never', 'command': ['/aux/etcd', '--listen-client-urls', 'http://127.0.0.1:2379']}],
                        'volumes': [{'name': name, 'hostPath': {'path': str(path)}} for name, path in
                                    [('gate', Path('/var/tmp/crg-short/gates')), ('aux', Path('/var/tmp/crg-short/aux')), ('postgresql', folder/'postgresql')]]}}
        original = copy.deepcopy(pod)
        with patch.object(tool.gate, 'digest', return_value={'sha256': 'same'}):
            adapted = tool.adapt_pod(pod, 'dbs', folder, 'crg-vendor-lab-post', work)
            self.assertEqual(pod, original)
            changed = adapted['spec']['containers'][0]
            self.assertEqual(changed['command'], main['command']);self.assertEqual(changed['resources'], main['resources'])
            self.assertEqual(changed['env'][1], main['env'][1]);self.assertTrue(changed['volumeMounts'][0]['readOnly'])
            self.assertFalse(changed['volumeMounts'][1]['readOnly'])
            bad = copy.deepcopy(pod);bad['spec']['volumes'][-1]['hostPath']['path'] = '/etc'
            with self.assertRaisesRegex(tool.Rejected, 'FOREIGN_HOST_MOUNT'):tool.adapt_pod(bad, 'dbs', folder, 'crg-vendor-lab-post', work)
            bad = copy.deepcopy(pod);bad['spec']['hostNetwork'] = True
            with self.assertRaisesRegex(tool.Rejected, 'POD_ISOLATION'):tool.adapt_pod(bad, 'dbs', folder, 'crg-vendor-lab-post', work)

    def test_cleanup_checks_uid_without_requiring_live_business(self):
        run = tool.Execution.__new__(tool.Execution);run.ns = 'crg-vendor-lab-owned';run.pods = {'dbs': 'owned-uid'}
        calls = []
        def command(args, **kwargs):
            calls.append(args)
            class Result:stdout = ''
            value = Result()
            if len(calls) == 1:value.stdout = json.dumps({'metadata': {'uid': 'owned-uid', 'labels': {'managed-by': 'crg-vendor-test'}}})
            return value
        run.run = command
        with patch.object(run, 'identity', side_effect=AssertionError('business may already be stopped')):run.delete_pod('dbs')
        self.assertEqual(run.pods, {});self.assertEqual(calls[1][1], 'delete')
        run.pods = {'dbs': 'foreign-uid'};calls.clear()
        with self.assertRaisesRegex(tool.Rejected, 'CLEANUP_POD_UID'):run.delete_pod('dbs')
        self.assertEqual(len(calls), 1)

    def test_plan_mode_and_contract_fail_before_runtime_inventory(self):
        base = {'schema': 'crg-aged-execution-v1', 'criteria': tool.CRITERIA, 'pins': tool.PINS,
                'mode': 'short-rehearsal'}
        with patch.object(tool.gate, 'read_json', return_value=(base, 'a'*64)):
            with self.assertRaisesRegex(tool.Rejected, 'MODE_MISMATCH'):tool.checked_plan(Path('unused'), 'a'*64, False)
            with self.assertRaisesRegex(tool.Rejected, 'EXECUTION_PLAN_DIGEST'):tool.checked_plan(Path('unused'), 'b'*64, True)
            base['criteria'] = dict(tool.CRITERIA, native_seconds_each_role=30)
            with self.assertRaisesRegex(tool.Rejected, 'EXECUTION_PLAN_CONTRACT'):tool.checked_plan(Path('unused'), 'a'*64, True)

    def test_no_report_write_before_exclusive_work_root(self):
        with tempfile.TemporaryDirectory() as name:
            plan = {'work_root': name, 'namespace': 'crg-vendor-lab-fresh', 'mode': 'short-rehearsal'}
            with patch.object(tool.gate, 'digest', return_value={'sha256': 'source'}):run = tool.Execution(plan, 'plan')
            with patch.object(run, 'save', side_effect=AssertionError('existing root must reject before writes')):
                with self.assertRaises(FileExistsError):run.execute({'postflight_allowed': True})
            self.assertEqual(list(Path(name).iterdir()), [])


if __name__ == '__main__':unittest.main(verbosity=2)
