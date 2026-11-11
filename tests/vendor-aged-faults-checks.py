#!/usr/bin/env python3
"""Synthetic gate/isolation checks; never evidence of actual aged fault success."""
import copy
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
    value = importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

tool = module('faults', 'vendor-aged-faults.py')
fixtures = module('old_checks', 'vendor-aged-postflight-checks.py')


class Checks(unittest.TestCase):
    def test_postflight_requires_actual_complete_proof_and_new_ids(self):
        post = {'mode': 'short-rehearsal', 'run_id': '20261111060'}
        report = {'schema': 'crg-aged-execution-report-v1', 'phase': 'passed', 'mode': post['mode'],
                  'plan_sha256': 'a'*64, 'executor_sha256': tool.POSTFLIGHT_SHA,
                  'source_revision': tool.aged.PINS['revision'], 'binary_sha256': tool.aged.PINS['binary'],
                  'criteria': tool.aged.CRITERIA, 'postflight_executed': True, 'aged_fixture_retained': True,
                  'namespace_absent': True, 'P10_complete': False, 'release_accepted': False,
                  'tests': [{'name': str(i), 'passed': True} for i in range(36)], 'roles': {}}
        for role, suffix in [('dbs', '0'), ('hisdbs', '1')]:
            native = fixtures.native();native['run_id'] = post['run_id']+suffix
            report['roles'][role] = {'phase': 'postflight-component-passed', 'native': native,
                                    'boots': [{'container_id': str(i), 'identity': str(i), 'primary_start': str(i)} for i in range(2)]}
        tool.postflight_proof(report, post, 'a'*64)
        mutations = [lambda r: r.update(namespace_absent=False), lambda r: r.update(mode='seven-day-postflight'),
                     lambda r: r.update(P10_complete=True), lambda r: r['tests'].pop(),
                     lambda r: r['tests'][0].update(name='1'), lambda r: r['tests'][0].update(passed=False),
                     lambda r: r['roles']['dbs']['boots'][1].update(identity='0'),
                     lambda r: r['roles']['hisdbs']['native'].update(elapsed_seconds=599)]
        for mutate in mutations:
            value = copy.deepcopy(report);mutate(value)
            with self.assertRaises(tool.Rejected):tool.postflight_proof(value, post, 'a'*64)

    def test_long_pending_checks_original_binding_and_creates_nothing(self):
        post = fixtures.execution_plan();lineage = {'postflight_root': post['work_root'], 'postflight_namespace': post['namespace'],
                'component_root': '/var/tmp/crg-seven-day57-20261111', 'run_id': '20261111057'}
        launch = {'pid': 123, 'start_ticks': 456}
        seal = {'launch': launch}
        with patch.object(tool.gate, 'load_plan', return_value=(lineage, post['lineage_plan_sha256'])), \
             patch.object(tool.gate, 'component', return_value=({'phase': 'pending'}, (None, launch))), \
             patch.object(tool.gate, 'read_json', return_value=(seal, post['lineage_seal_sha256'])) as read, \
             patch.object(tool, 'postflight_proof', side_effect=AssertionError('no postflight yet')), \
             patch.object(tool, 'no_other_mounts', side_effect=AssertionError('no mount execution yet')):
            result = tool.readiness({'mode': 'seven-day-aged-faults'}, post)
            self.assertEqual(result['phase'], 'pending');self.assertFalse(result['fault_execution_allowed'])
            self.assertEqual(read.call_count, 1)
            changed = copy.deepcopy(post);changed['roles']['dbs']['aged_run_id'] = '202611110510'
            with self.assertRaisesRegex(tool.Rejected, 'FROZEN_LONG_ROLE_BINDING'):tool.readiness({'mode': 'seven-day-aged-faults'}, changed)
            seal['launch'] = {'pid': 999}
            with self.assertRaisesRegex(tool.Rejected, 'AGED_SEAL_BINDING'):tool.readiness({'mode': 'seven-day-aged-faults'}, post)

    def test_execute_pending_does_not_construct_executor(self):
        with patch.object(sys, 'argv', ['test', '--plan', 'unused', '--plan-sha256', 'a'*64, '--execute']), \
             patch.object(tool.sys, 'platform', 'linux'), patch.object(tool.os, 'geteuid', create=True, return_value=0), \
             patch.object(tool, 'checked_plan', return_value=({}, {}, {})), \
             patch.object(tool, 'readiness', return_value={'phase': 'pending', 'fault_execution_allowed': False}), \
             patch.object(tool, 'Execution', side_effect=AssertionError('no execution before completion')), \
             patch.object(sys, 'stdout', new_callable=io.StringIO):
            self.assertEqual(tool.main(), 2)

    def test_short_plan_cannot_qualify_long_mode_or_weaken_criteria(self):
        value = {'schema': 'crg-aged-fault-plan-v1', 'mode': 'short-rehearsal', 'criteria': tool.CRITERIA,
                 'cases': tool.KINDS, 'pins': tool.aged.PINS}
        with patch.object(tool.gate, 'read_json', return_value=(value, 'a'*64)):
            with self.assertRaisesRegex(tool.Rejected, 'FAULT_PLAN_CONTRACT'):tool.checked_plan(Path('unused'), 'a'*64, False)
            value['criteria'] = dict(tool.CRITERIA, TERM_seconds=30)
            with self.assertRaisesRegex(tool.Rejected, 'FAULT_PLAN_CONTRACT'):tool.checked_plan(Path('unused'), 'a'*64, True)

    @unittest.skipUnless(os.name == 'posix', 'POSIX lab paths and modes')
    def test_all_pod_mounts_checked_including_non_fixture_and_parent_alias(self):
        for path in ['/var/tmp/crg-aged/dbs-business/postgresql', '/var/tmp/crg-aged', '/var/tmp/else/../crg-aged/dbs-business']:
            pod = {'spec': {'volumes': [{'name': 'data', 'hostPath': {'path': path}}]}}
            with patch.object(tool.gate, 'command', return_value=json.dumps({'items': [pod]})):
                with self.assertRaisesRegex(tool.Rejected, 'AGED_DATA_ALREADY_MOUNTED'):
                    tool.no_other_mounts([Path('/var/tmp/crg-aged/dbs-business')])
        monitor = {'spec': {'volumes': [{'name': 'root', 'hostPath': {'path': '/'}}],
                   'containers': [{'name': 'monitor', 'securityContext': {'allowPrivilegeEscalation': False,
                       'capabilities': {'drop': ['ALL'], 'add': ['SYS_TIME']}},
                       'volumeMounts': [{'name': 'root', 'mountPath': '/host/root', 'readOnly': True}]}]}}
        with patch.object(tool.gate, 'command', return_value=json.dumps({'items': [monitor]})):
            tool.no_other_mounts([Path('/var/tmp/crg-aged/dbs-business')])
        for change in ['writable', 'privileged', 'SYS_ADMIN', 'direct']:
            pod = copy.deepcopy(monitor);c = pod['spec']['containers'][0]
            if change == 'writable':c['volumeMounts'][0]['readOnly'] = False
            elif change == 'privileged':c['securityContext']['privileged'] = True
            elif change == 'SYS_ADMIN':c['securityContext']['capabilities']['add'] = ['SYS_ADMIN']
            else:pod['spec']['volumes'][0]['hostPath']['path'] = '/var/tmp/crg-aged/dbs-business'
            with patch.object(tool.gate, 'command', return_value=json.dumps({'items': [pod]})):
                with self.assertRaisesRegex(tool.Rejected, 'AGED_DATA_ALREADY_MOUNTED'):
                    tool.no_other_mounts([Path('/var/tmp/crg-aged/dbs-business')])

    @unittest.skipUnless(os.name == 'posix', 'POSIX lab paths and modes')
    def test_copy_preserves_source_and_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);source = root/'source';source.mkdir();p = source/'journal.json';p.write_text('old identity');p.chmod(0o600)
            before = tool.tree_snapshot(source);tool.copy_tree(source, root/'copy')
            self.assertEqual(tool.tree_snapshot(source), before)
            self.assertEqual((root/'copy/journal.json').read_text(), 'old identity')
            (source/'link').symlink_to(p)
            with self.assertRaisesRegex(tool.Rejected, 'STATE_TREE_SYMLINK'):tool.tree_snapshot(source)

    @unittest.skipUnless(os.name == 'posix', 'POSIX lab paths')
    def test_fault_pod_only_redirects_helpers_keeps_aged_data_and_private_env(self):
        folder = Path('/var/tmp/crg-old/dbs-business');case = Path('/var/tmp/crg-fault/case');work = case.parent
        main = {'name': 'dbs', 'imagePullPolicy': 'Never', 'resources': {'limits': {'cpu': '8', 'memory': '20Gi'}},
                'command': ['/bin/bash', '-c', 'gate; exec /bin/bash /opt/ccg/scripts/business-supervisor.sh'],
                'env': [{'name': n, 'value': 'keep'} for n in ['MY_POD_NAMESPACE', 'PGPASSWORD', 'CRG_BIN', 'CRG_CONFIG', 'CRG_HELPER_SCRIPT']],
                'volumeMounts': [{'name': n, 'mountPath': target, 'readOnly': n in ['crg', 'ccg']} for n, target in
                                [('postgresql', '/opt/postgresql'), ('ccg', '/opt/ccg'), ('crg', '/opt/crg'), ('crg-config', '/etc/crg'), ('resource-state', '/tmp/containerresourceguard')]]}
        pod = {'kind': 'Pod', 'metadata': {'name': 'dbs-business', 'namespace': 'old', 'labels': {'managed-by': 'crg-vendor-test'}},
               'spec': {'restartPolicy': 'Never', 'automountServiceAccountToken': False, 'containers': [main,
                        {'name': 'isolated-dcs', 'imagePullPolicy': 'Never', 'command': ['/aux/etcd', '--listen-client-urls', 'http://127.0.0.1:2379']}],
                        'volumes': [{'name': n, 'hostPath': {'path': str(folder/n)}} for n in ['postgresql', 'ccg', 'crg', 'crg-config', 'resource-state']]}}
        original = copy.deepcopy(pod)
        for kind in tool.KINDS:
            changed = tool.fault_pod(pod, 'dbs', folder, 'crg-vendor-lab-fault', work, case, kind)
            self.assertEqual(pod, original);vols = {v['name']: v for v in changed['spec']['volumes']}
            current = changed['spec']['containers'][0];mounts = {v['name']: v for v in current['volumeMounts']}
            self.assertEqual(vols['postgresql'], pod['spec']['volumes'][0]);self.assertEqual(current['command'], main['command'])
            self.assertEqual(current['env'][1], main['env'][1]);self.assertEqual(current['resources'], main['resources'])
            self.assertEqual(vols['resource-state']['hostPath']['path'], str(case/'resource-state'))
            self.assertTrue(mounts['crg']['readOnly']);self.assertTrue(mounts['ccg']['readOnly'])
            self.assertEqual(mounts['resource-state']['readOnly'], kind == 'state-readonly')
            self.assertFalse('staging' in vols or 'recovery' in vols)
            self.assertEqual(vols['ccg']['hostPath']['path'], str(case/'ccg') if kind == 'rollback' else str(folder/'ccg'))

    def test_existing_target_rejected_before_report_write(self):
        with tempfile.TemporaryDirectory() as temp:
            plan = {'work_root': temp, 'namespace': 'crg-vendor-lab-owned', 'mode': 'short-rehearsal'}
            with patch.object(tool.gate, 'digest', return_value={'sha256': 'source'}):run = tool.Execution(plan, 'plan', {}, {})
            with patch.object(run, 'save', side_effect=AssertionError('must not touch existing directory')):
                with self.assertRaises(FileExistsError):run.execute({})
            self.assertEqual(list(Path(temp).iterdir()), [])


if __name__ == '__main__':unittest.main(verbosity=2)
