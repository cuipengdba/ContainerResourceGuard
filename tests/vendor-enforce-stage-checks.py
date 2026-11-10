#!/usr/bin/env python3
"""Negative acceptance-gate tests; never invokes Kubernetes or applies limits."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('vendor_stage', ROOT/'tests/vendor-enforce-stage.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


def manifest():
    roles = {}
    for index, role in enumerate(['dbs', 'hisdbs']):
        cid = str(index+1)*64
        roles[role] = {'container_id': cid, 'pod_uid': '01234567-89ab-cdef-0123-456789abcdef',
                       'main': {'pid': 100+index, 'ppid': 50, 'start_ticks': 1000},
                       'helper': {'pid': 200+index, 'ppid': 100+index, 'start_ticks': 1010},
                       'actors': {'crg': [{'pid': 300+index, 'ppid': 200+index, 'start_ticks': 1020, 'sha256': stage.OLD}],
                                  'containercacheguard': [{'pid': 400+index, 'ppid': 100+index, 'start_ticks': 1010, 'sha256': stage.CACHE}]},
                       'controls': dict(zip(stage.CONTROLS, ['800000 100000', '21474836480', '', '1000', '100', 'default 100', 'max', '0'])),
                       'membership': '0::/kubepods.slice/cri-containerd-'+cid+'.scope\n',
                       'cgroup': '/sys/fs/cgroup/kubepods.slice/cri-containerd-'+cid+'.scope'}
    return {'schema': 'crg-vendor-enforce-stage-v1', 'kind': 'formal', 'namespace': stage.FORMAL_NAMESPACE,
            'namespace_uid': '01234567-89ab-cdef-0123-456789abcdef',
            'fixture_root': '/var/tmp/crg-business-20261110',
            'baseline_work_dir': '/var/tmp/crg-baseline24h-20261110',
            'tools_root': '/var/tmp/crg-baseline-tools-20261110',
            'candidate_binary': '/var/tmp/crg-candidate/crg',
            'source_run_id': '202611100705', 'new_run_id': '202611110810',
            'fixture_sources': dict(stage.FIXTURE_SOURCES), 'roles': roles}


class GateTests(unittest.TestCase):
    def setUp(self):
        receipt = json.loads((ROOT/'docs/test-results-observe-first-adoption.json').read_text(encoding='utf-8'))
        self.actual = receipt['roles']['baseline-dbs']['native']

    def test_actual_short_native_evidence_never_becomes_formal(self):
        self.assertTrue(stage.accepted_native(self.actual, 600))
        self.assertFalse(stage.accepted_native(self.actual, 86400))
        for key, value in [('phase', 'running'), ('threads_stopped', False), ('payload_integrity', False),
                           ('primary_not_restarted', False), ('interrupted', True), ('elapsed_seconds', 599.999),
                           ('elapsed_seconds', float('inf'))]:
            with self.subTest(key=key, value=value):
                item = copy.deepcopy(self.actual);item[key] = value
                self.assertFalse(stage.accepted_native(item, 600))

    def test_request_budget_cannot_be_relaxed_by_summary_fields(self):
        for kind in ['sql', 'api']:
            for key, value in [('errors', 1), ('max_seconds', 5.001), ('max_seconds', -1),
                               ('p95_bucket_upper_seconds', 2), ('sample_coverage', .979),
                               ('sample_coverage', float('inf'))]:
                with self.subTest(kind=kind, key=key):
                    item = copy.deepcopy(self.actual);item[kind][key] = value
                    self.assertFalse(stage.accepted_native(item, 600))
        item = copy.deepcopy(self.actual)
        item['sql']['histogram'] = [0]*12
        self.assertFalse(stage.accepted_native(item, 600))
        item = copy.deepcopy(self.actual);item['final_checksum'][2] -= 4096
        self.assertFalse(stage.accepted_native(item, 600))

    def test_formal_manifest_is_not_a_generic_target_selector(self):
        original = manifest();stage.validate_manifest(original)
        for key, value in [('namespace', 'production'), ('fixture_root', '/var/tmp/crg-business-20261110/../other'),
                           ('source_run_id', '202611100704'), ('new_run_id', '202611100705'),
                           ('baseline_work_dir', '/var/tmp/crg-other'), ('kind', 'force')]:
            with self.subTest(key=key):
                item = copy.deepcopy(original);item[key] = value
                with self.assertRaises(RuntimeError):stage.validate_manifest(item)
        item = copy.deepcopy(original);item['fixture_sources']['crg'] = stage.NEW
        with self.assertRaises(RuntimeError):stage.validate_manifest(item)
        item = copy.deepcopy(original);item['roles']['dbs']['membership'] += '5:cpu:/other\n'
        with self.assertRaises(RuntimeError):stage.validate_manifest(item)
        item = copy.deepcopy(original);item['roles']['dbs']['helper']['ppid'] += 1
        with self.assertRaises(RuntimeError):stage.validate_manifest(item)

    def test_rehearsal_cannot_be_used_to_shorten_original_baseline(self):
        item = manifest();item['kind'] = 'rehearsal'
        with self.assertRaises(RuntimeError):stage.validate_manifest(item)
        item.update(namespace='crg-vendor-lab-stage20-20261110', fixture_root='/var/tmp/crg-stage-rehearsal-20',
                    baseline_work_dir='/var/tmp/crg-stage-rehearsal-20/baseline')
        stage.validate_manifest(item)
        item['fixture_root'] = '/var/tmp/crg-business-20261110'
        with self.assertRaises(RuntimeError):stage.validate_manifest(item)

    def test_missing_gate_prevents_even_lock_or_output_creation(self):
        obj = stage.Stage(manifest())
        with patch.object(obj, 'preflight', return_value=False), patch.object(stage.os, 'open') as opened, patch.object(stage.subprocess, 'run') as command:
            with self.assertRaises(RuntimeError):obj.perform('/var/tmp/crg-enforce-stage-must-not-exist')
            opened.assert_not_called();command.assert_not_called()
        self.assertIsNone(obj.output)
        self.assertEqual(obj.disabled, [])

    def test_checker_reports_a_closed_gate_without_mutating(self):
        obj = stage.Stage(manifest())
        self.assertFalse(obj.check('missing', lambda: stage.require(False, 'fixed refusal')))
        self.assertEqual(obj.report['checks']['missing'], {'passed': False, 'failure_class': 'RuntimeError', 'detail': 'fixed refusal'})
        self.assertIsNone(obj.output)

    def test_corrupted_or_linked_input_never_becomes_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'receipt.json';path.write_text('{broken', encoding='utf-8')
            with self.assertRaises(json.JSONDecodeError):stage.read_json(path)
            with self.assertRaises(RuntimeError):stage.bounded(path, 1)
            linked = Path(folder)/'alias.json'
            try:linked.hardlink_to(path)
            except OSError:self.skipTest('hard links unavailable')
            with self.assertRaises(RuntimeError):stage.bounded(path)

    def test_running_or_content_only_campaign_is_not_terminal(self):
        for phase in ['running', 'measuring', 'content-passed-native-pending']:
            self.assertFalse(stage.accepted_campaign({'phase': phase}, 86400, 'baseline'))

    def test_full_campaign_requires_both_native_intervals_and_every_cycle(self):
        # Synthetic oracle fixture, not a new business result. Native positive
        # data comes from the archived actual600s receipt.
        start = stage.epoch(self.actual['started_utc'])
        samples = [{'elapsed_seconds': n*60, 'agent_same_process': True,
                    'cache_same_process': True, 'PID1_same_process': True} for n in range(10)]
        report = {'phase': 'passed', 'test_phase': 'smoke', 'requested_seconds': 600,
                  'agent_sha256': stage.OLD, 'cache_sha256': stage.CACHE,
                  'campaign_script_sha256': stage.TOOLS['vendor-soak-campaign.py'],
                  'worker_sha256': stage.TOOLS['vendor-soak-load.py'],
                  'engine_script_sha256': stage.TOOLS['vendor-engine-smoke.py'],
                  'criteria': {'backup_offsets_seconds': [30]},
                  'roles': {r: {'workload': copy.deepcopy(self.actual), 'samples': copy.deepcopy(samples)} for r in ['dbs', 'hisdbs']},
                  'backups': [{'phase': 'passed', 'offset_seconds': 30,
                               'native_workload_validation': 'passed-with-entire-campaign',
                               'content_started_epoch': start+30, 'content_ended_epoch': start+90,
                               'roles': {r: {'checks': 10, 'cleanup': True, 'native_pending': True} for r in ['dbs', 'hisdbs']}}]}
        self.assertTrue(stage.accepted_campaign(report, 600, 'smoke'))
        newer = copy.deepcopy(report);newer['agent_sha256'] = stage.NEW
        self.assertFalse(stage.accepted_campaign(newer, 600, 'smoke'))
        self.assertTrue(stage.accepted_campaign(newer, 600, 'smoke', agent_sha256=stage.NEW))
        newer.update(campaign_script_sha256=stage.SMOKE_TOOLS['vendor-soak-campaign.py'],
                     engine_script_sha256=stage.SMOKE_TOOLS['vendor-engine-smoke.py'])
        self.assertFalse(stage.accepted_campaign(newer, 600, 'smoke', agent_sha256=stage.NEW))
        self.assertTrue(stage.accepted_campaign(newer, 600, 'smoke', agent_sha256=stage.NEW, tools=stage.SMOKE_TOOLS))
        for change in ['native', 'sample_gap', 'sample_identity', 'sample_nonfinite', 'missing_cycle',
                       'outside_interval', 'cleanup', 'pending_cycle', 'source', 'campaign_cleanup']:
            with self.subTest(change=change):
                item = copy.deepcopy(report)
                if change == 'native':item['roles']['hisdbs']['workload']['api']['errors'] = 1
                elif change == 'sample_gap':item['roles']['dbs']['samples'][4]['elapsed_seconds'] += 121
                elif change == 'sample_identity':item['roles']['dbs']['samples'][4]['PID1_same_process'] = False
                elif change == 'sample_nonfinite':item['roles']['dbs']['samples'][4]['elapsed_seconds'] = float('nan')
                elif change == 'missing_cycle':item['backups'] = []
                elif change == 'outside_interval':item['backups'][0]['content_started_epoch'] = start-1
                elif change == 'cleanup':item['backups'][0]['roles']['hisdbs']['cleanup'] = False
                elif change == 'pending_cycle':item['backups'][0]['native_workload_validation'] = 'pending'
                elif change == 'source':item['engine_script_sha256'] = '0'*64
                elif change == 'campaign_cleanup':item['cleanup_errors'] = ['pending']
                self.assertFalse(stage.accepted_campaign(item, 600, 'smoke'))

    def test_malformed_receipts_close_gates(self):
        for value in [None, [], '', {'phase': 'passed'}, {'phase': 'passed', 'requested_duration_seconds': 600, 'elapsed_seconds': '600'}]:
            self.assertFalse(stage.accepted_native(value, 600))
            self.assertFalse(stage.accepted_campaign(value, 600, 'smoke'))

    def test_scheduled_hold_does_not_add_check_latency_to_every_interval(self):
        clock = [100.0];observed = []
        def check():
            observed.append(clock[0]);clock[0] += .3
        elapsed, count = stage.observe_for(120, 2, check, now=lambda: clock[0], sleep=lambda s: clock.__setitem__(0, clock[0]+s))
        self.assertEqual((elapsed, count), (120, 60))
        self.assertEqual(observed, [100+2*n for n in range(60)])

    def test_slow_hold_checks_skip_slots_without_catching_up_in_bursts(self):
        clock = [0.0];observed = []
        def check():
            observed.append(clock[0]);clock[0] += 2.5
        elapsed, count = stage.observe_for(120, 2, check, now=lambda: clock[0], sleep=lambda s: clock.__setitem__(0, clock[0]+s))
        self.assertEqual((elapsed, count), (120, 30))
        self.assertLess(count, 59)  # Existing coverage gate still refuses.
        self.assertEqual(observed, [4*n for n in range(30)])

    def test_source_hash_alone_does_not_prove_required_workload_interface(self):
        self.assertTrue(stage.tool_interfaces(ROOT/'tests', smoke=True))
        self.assertEqual({name: stage.digest(ROOT/'tests'/name) for name in stage.SMOKE_TOOLS}, stage.SMOKE_TOOLS)
        with tempfile.TemporaryDirectory() as folder:
            # A legacy-shaped source can support the formal phase while
            # lacking the managed smoke and selected-role interfaces.
            for name in stage.TOOLS:
                data = (ROOT/'tests'/name).read_text(encoding='utf-8')
                data = '\n'.join(line for line in data.splitlines() if "add_argument('--smoke-enforce'" not in line and 'add_argument("--role"' not in line)
                (Path(folder)/name).write_text(data, encoding='utf-8')
            self.assertTrue(stage.tool_interfaces(folder, smoke=False))
            self.assertFalse(stage.tool_interfaces(folder, smoke=True))


if __name__ == '__main__':
    unittest.main()
