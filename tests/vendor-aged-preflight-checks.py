#!/usr/bin/env python3
"""Synthetic/local-filesystem tests; no elapsed seven-day runtime is claimed."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    value = importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


gate = module('aged_gate', 'vendor-aged-preflight.py')
reports = module('audit_checks', 'soak-report-audit-checks.py')


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def component_fixture(base, passed=False):
    runner, root = base/'runner', base/'component';runner.mkdir();root.mkdir()
    frozen = {'source_revision': '1'*40, 'binary_sha256': reports.PINS['agent_sha256'],
              'helper_sha256': {'tests/vendor-soak-load.py': reports.PINS['worker_sha256'],
                               'tests/vendor-soak-campaign.py': reports.PINS['campaign_script_sha256'],
                               'tests/vendor-engine-smoke.py': reports.PINS['engine_script_sha256']}}
    for filename, key in [('acceptance-job.py', 'job_sha256'), ('acceptance-runner.py', 'runner_sha256'),
                          ('campaign-wrapper.py', 'campaign_wrapper_sha256')]:
        p = runner/filename;p.write_bytes(filename.encode());frozen[key] = hashlib.sha256(p.read_bytes()).hexdigest()
    write(runner/'acceptance-plan.json', frozen)
    plan = {'component_root': str(root), 'runner_root': str(runner),
            'source_revision': frozen['source_revision'], 'binary_sha256': frozen['binary_sha256'],
            'cache_sha256': reports.PINS['cache_sha256'],
            'component_plan_sha256': hashlib.sha256((runner/'acceptance-plan.json').read_bytes()).hexdigest()}
    launch = dict(pid=1234, entry=str(runner/'acceptance-runner.py'), start_ticks=42,
                  job_sha256=frozen['job_sha256'], source_revision=plan['source_revision'],
                  binary_sha256=plan['binary_sha256'])
    write(runner/'launch.json', launch)
    outer = dict(phase='passed' if passed else 'seven-day-native-measurement',
                 sources={'v10': {'revision': plan['source_revision'], 'binary_sha256': plan['binary_sha256']}},
                 job_sha256=frozen['job_sha256'], requested_seconds=604800,
                 continuous_component_only=True, P10_complete=False, namespace_uid='owned-namespace',
                 tests=[{'name': str(i), 'passed': True} for i in range(11)],
                 namespace_absent=True, aged_fixture_retained=True,
                 postflight_and_final_release_audit_required=True)
    write(root/'report.json', outer)
    campaign = reports.fixture()
    if not passed:campaign.update(phase='measuring', roles={}, backups=[])
    write(root/'campaign-acceptance/report.json', campaign)
    if passed:write(runner/'acceptance.exit.json', {'exit': 0, 'job_sha256': frozen['job_sha256']})
    return plan


def lineage_fixture(base):
    plan = dict(component_root=str(base/'aged'), postflight_root=str(base/'not-created'),
                namespace='crg-vendor-lab-owned', postflight_namespace='crg-vendor-lab-post',
                source_revision='1'*40, binary_sha256='a'*64)
    launch = {'pid': 1234, 'start_ticks': 42};outer = {'namespace_uid': 'owned'}
    campaign = reports.fixture()
    seal = dict(schema='crg-aged-lineage-seal-v1', seal_is_not_acceptance=True,
                plan_sha256='pinned-plan', namespace_uid='owned', launch=launch,
                source_revision=plan['source_revision'], binary_sha256=plan['binary_sha256'], roles={})
    for role in ['dbs', 'hisdbs']:
        folder = Path(plan['component_root'])/'fixture'/(role+'-business')
        row = {'directories': {}, 'files': {}, 'containers': {}, 'log_prefixes': {},
               'native_started_utc': campaign['roles'][role]['workload']['started_utc'],
               'primary_start': campaign['roles'][role]['workload']['primary_start_time_initial']}
        for name in gate.DIRECTORIES:
            p = folder/name;p.mkdir(parents=True, exist_ok=True);row['directories'][name] = gate.directory(p)
        for name in gate.immutable_files(role):
            p = folder/name;p.parent.mkdir(parents=True, exist_ok=True);p.write_bytes(b'stable input')
            row['files'][name] = gate.digest(p)
        for index, name in enumerate([role, 'isolated-dcs']):
            cid = hashlib.sha256((str(base)+role+name).encode()).hexdigest()
            row['containers'][name] = {'container_id': cid, 'cgroup': '/sys/fs/cgroup/cri-containerd-'+cid+'.scope'}
        journal = folder/'resource-state/journal.json';write(journal, {'identity': 'old-'+role});journal.chmod(0o600)
        row.update(journal_identity='old-'+role, journal_sha256=hashlib.sha256(journal.read_bytes()).hexdigest())
        for day in range(1, 8):
            p = folder/'log/crg'/('crg-2026-01-%02d.log' % day)
            p.parent.mkdir(parents=True, exist_ok=True);p.write_bytes(b'{"event":"old"}\n');p.chmod(0o600)
            if day == 1:row['log_prefixes'][p.name] = gate.digest(p)
        p = folder/'log/crg/crg-2026-01-01.log'
        with p.open('ab') as stream:stream.write(b'{"event":"appended"}\n')
        seal['roles'][role] = row
    return plan, seal, ({}, launch, outer, campaign)


class Checks(unittest.TestCase):
    def test_paths_and_prefixes(self):
        with self.assertRaisesRegex(gate.Rejected, 'ABSOLUTE_PATH'):gate.path_clean(Path('relative'))
        with tempfile.TemporaryDirectory() as work:
            with self.assertRaisesRegex(gate.Rejected, 'LAB_ROOT'):gate.lab_root(work)
            p = Path(work)/'log';p.write_bytes(b'initial')
            before = gate.digest(p)
            with p.open('ab') as stream:stream.write(b'appended')
            self.assertEqual(gate.digest(p, before['size']), before)
            with self.assertRaisesRegex(gate.Rejected, 'FILE_SIZE'):gate.digest(p, 1000)

    def test_pending_requires_actual_live_handle(self):
        with tempfile.TemporaryDirectory() as work:
            plan = component_fixture(Path(work))
            with patch.object(gate, 'proc', return_value={'live': True}):
                result, _ = gate.component(plan)
                self.assertEqual(result['phase'], 'pending');self.assertFalse(result['postflight_allowed'])
            with patch.object(gate, 'proc', return_value={'live': False}):
                with self.assertRaisesRegex(gate.Rejected, 'RUNNER_NOT_LIVE'):gate.component(plan)

    def test_completed_component_still_not_release(self):
        with tempfile.TemporaryDirectory() as work:
            plan = component_fixture(Path(work), passed=True)
            with patch.object(gate, 'proc', return_value={'live': False}):
                result, _ = gate.component(plan)
                self.assertEqual(result['phase'], 'component-accepted');self.assertFalse(result['P10_complete'])
            with patch.object(gate, 'proc', return_value={'live': True}):
                with self.assertRaisesRegex(gate.Rejected, 'RUNTIME_NOT_TERMINAL'):gate.component(plan)

    def test_rejected_terminal_or_wrong_source(self):
        changes = [('failed', lambda x: x.update(phase='failed'), 'COMPONENT_FAILED'),
                   ('wrong program', lambda x: x['sources']['v10'].update(binary_sha256='f'*64), 'OUTER_SOURCE'),
                   ('wrong scope', lambda x: x.update(P10_complete=True), 'OUTER_SOURCE'),
                   ('incomplete checks', lambda x: x['tests'].pop(), 'COMPONENT_CHECKS'),
                   ('cleanup pending', lambda x: x.update(namespace_absent=False), 'COMPONENT_CLEANUP')]
        for name, change, reason in changes:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as work:
                plan = component_fixture(Path(work), passed=True);p = Path(plan['component_root'])/'report.json'
                value = json.loads(p.read_text());change(value);write(p, value)
                with patch.object(gate, 'proc', return_value={'live': False}), self.assertRaisesRegex(gate.Rejected, reason):
                    gate.component(plan)

    @unittest.skipUnless(os.name == 'posix', 'POSIX file permissions and old cgroup path shape')
    def test_lineage_is_only_permission_to_run_postflight(self):
        with tempfile.TemporaryDirectory() as work:
            plan, seal, inputs = lineage_fixture(Path(work))
            with patch.object(gate, 'namespace', return_value=None):
                result = gate.verify_lineage(plan, 'pinned-plan', seal, inputs)
            self.assertTrue(result['postflight_allowed']);self.assertFalse(result['postflight_executed'])
            self.assertFalse(result['P10_complete']);self.assertFalse(result['release_accepted'])

    @unittest.skipUnless(os.name == 'posix', 'POSIX file permissions and old cgroup path shape')
    def test_lineage_rejects_replaced_or_changed_state(self):
        for kind, reason in [('namespace', 'OLD_NAMESPACE'), ('target', 'POSTFLIGHT_TARGET'),
                             ('input', 'AGED_INPUT'), ('journal', 'AGED_JOURNAL'),
                             ('prefix', 'AGED_LOG_PREFIX'), ('prefix-short', 'FILE_SIZE'), ('member', 'SEAL_MEMBER_SET'),
                             ('source', 'SEAL_BINDING')]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as work:
                plan, seal, inputs = lineage_fixture(Path(work));folder = Path(plan['component_root'])/'fixture/dbs-business'
                response = None
                if kind == 'namespace':response = {'metadata': {'uid': 'still-present'}}
                if kind == 'target':Path(plan['postflight_root']).mkdir()
                if kind == 'input':(folder/'crg-config/config.json').write_bytes(b'changed')
                if kind == 'journal':write(folder/'resource-state/journal.json', {'identity': 'wrong'})
                if kind == 'prefix':(folder/'log/crg/crg-2026-01-01.log').write_bytes(b'{"event":"bad"}\n')
                if kind == 'prefix-short':(folder/'log/crg/crg-2026-01-01.log').write_bytes(b'changed')
                if kind == 'member':seal['roles']['dbs']['files']['../foreign'] = {}
                if kind == 'source':seal['binary_sha256'] = 'f'*64
                with patch.object(gate, 'namespace', return_value=response), self.assertRaisesRegex(gate.Rejected, reason):
                    gate.verify_lineage(plan, 'pinned-plan', seal, inputs)

    @unittest.skipUnless(os.name == 'posix', 'Symlink and hardlink modes are tested on Linux')
    def test_symlinks_and_hardlinks_rejected(self):
        with tempfile.TemporaryDirectory() as work:
            folder = Path(work);p = folder/'file';p.write_bytes(b'data')
            link = folder/'link';link.symlink_to(p)
            with self.assertRaisesRegex(gate.Rejected, 'SYMLINK_PATH'):gate.digest(link)
            hard = folder/'hard';os.link(p, hard)
            with self.assertRaisesRegex(gate.Rejected, 'REGULAR_FILE'):gate.digest(hard)


if __name__ == '__main__':
    unittest.main()
