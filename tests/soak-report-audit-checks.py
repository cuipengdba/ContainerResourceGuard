#!/usr/bin/env python3
"""Synthetic report tests only: no runtime or seven-day acceptance claim."""
import datetime
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('soak_audit', Path(__file__).with_name('soak-report-audit.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
PINS = {key: char * 64 for key, char in zip(
    ('agent_sha256', 'cache_sha256', 'worker_sha256', 'campaign_script_sha256', 'engine_script_sha256'),
    'abcde')}


def fixture(phase='acceptance'):
    seconds = 604800 if phase == 'acceptance' else 86400
    offsets = [300] + list(range(21600, seconds, 21600))
    start = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    report = dict(schema='crg-vendor-campaign-v1', phase='passed', test_phase=phase,
                  requested_seconds=seconds, source_run_id='202601010001' if phase == 'enforce' else None,
                  criteria={'host_available_min_bytes': 8 * 1024**3,
                            'disk_free_min_bytes': 20 * 1024**3, 'host_sample_seconds': 60,
                            'OOM_kill_delta_max': 0, 'backup_offsets_seconds': offsets},
                  roles={}, backups=[], **PINS)
    for role in ['dbs', 'hisdbs']:
        checksum = [16384, 134225920, 67108864, '10b3b8214172d3b698258a128e9c6687', 0]
        workload = dict(schema='crg-vendor-soak-v1', phase='passed', test_phase=phase,
                        requested_duration_seconds=seconds, elapsed_seconds=seconds + .1,
                        threads_stopped=True, payload_integrity=True, primary_not_restarted=True,
                        interrupted=False, primary_start_time_initial='same-primary',
                        primary_start_time_final='same-primary', initial_checksum=checksum,
                        final_checksum=list(checksum), started_utc=start.isoformat(),
                        measurement_finished_utc=(start + datetime.timedelta(seconds=seconds)).isoformat(),
                        criteria={'sql_period_seconds': 2, 'api_period_seconds': 5,
                                  'maximum_errors': 0, 'maximum_seconds': 5,
                                  'p95_upper_bound_seconds': 1, 'minimum_scheduled_samples_fraction': .98},
                        latency_bucket_upper_seconds=[.001, .005, .01, .02, .05, .1, .25, .5, 1, 2, 5, 'over-5'])
        if phase == 'enforce':
            workload['source_run_id'] = '202601010001'
        for kind, period in [('sql', 2), ('api', 5)]:
            attempts = seconds // period
            workload[kind] = dict(attempts=attempts, successes=attempts, errors=0, max_seconds=.001,
                                  histogram=[attempts] + [0] * 11, p95_bucket_upper_seconds=.001,
                                  sample_coverage=1.0)
        report['roles'][role] = {
            'workload': workload,
            'fixed_controls': {key: 'value' for key in ['cpu.max', 'memory.max', 'io.max',
                                                       'pids.max', 'cpu.weight', 'io.weight',
                                                       'memory.high', 'memory.swap.max']},
            'samples': [dict(elapsed_seconds=i * 60, agent_same_process=True,
                             cache_same_process=True, PID1_same_process=True,
                             memory_events={'oom_kill': 0}) for i in range(seconds // 60)]}
    for offset in offsets:
        report['backups'].append(dict(phase='passed', content_phase='content-passed-native-pending',
                                     exit=0, native_workload_validation='passed-with-entire-campaign',
                                     offset_seconds=offset, content_started_epoch=start.timestamp() + offset,
                                     content_ended_epoch=start.timestamp() + offset + 30,
                                     roles={r: dict(checks=10, cleanup=True, native_pending=True)
                                            for r in ['dbs', 'hisdbs']}))
    return report


class Checks(unittest.TestCase):
    def test_complete_synthetic_reports(self):
        for phase in ['baseline', 'enforce', 'acceptance']:
            with self.subTest(phase=phase):
                r = audit.audit(fixture(phase), phase, PINS,
                                '202601010001' if phase == 'enforce' else None)
                self.assertEqual(r['phase'], 'passed')
                self.assertTrue(r['continuous_report_accepted'])
                self.assertFalse(r['release_accepted'])
                self.assertFalse(r['runtime_cleanup_verified'])

    def test_running_is_pending(self):
        r = fixture();r['phase'] = 'measuring';r['roles'] = {};r['backups'] = []
        self.assertEqual(audit.audit(r, 'acceptance', PINS)['phase'], 'pending')

    def test_failed_report_never_pending(self):
        r = fixture();r['phase'] = 'failed'
        with self.assertRaisesRegex(audit.Rejected, 'CAMPAIGN_NOT_ACCEPTED'):
            audit.audit(r, 'acceptance', PINS)

    def test_invalid_evidence(self):
        cases = [
            ('wrong source', 'SOURCE_DIGEST', lambda r: r.update(agent_sha256='f' * 64)),
            ('short request', 'CAMPAIGN_DURATION', lambda r: r.update(requested_seconds=600)),
            ('borrowed prior data', 'SOURCE_RUN', lambda r: r.update(source_run_id='202601010001')),
            ('wrong native source', 'NATIVE_SOURCE_RUN', lambda r: r['roles']['dbs']['workload'].update(source_run_id='202601010001')),
            ('relaxed gates', 'CAMPAIGN_CRITERIA', lambda r: r['criteria'].update(host_sample_seconds=120)),
            ('short actual run', 'NATIVE_DURATION', lambda r: r['roles']['dbs']['workload'].update(elapsed_seconds=600)),
            ('native errors', 'NATIVE_ERRORS', lambda r: r['roles']['dbs']['workload']['sql'].update(errors=1)),
            ('boolean error count', 'NATIVE_ERRORS', lambda r: r['roles']['dbs']['workload']['sql'].update(errors=False)),
            ('native too slow', 'NATIVE_MAXIMUM', lambda r: r['roles']['dbs']['workload']['api'].update(max_seconds=5.1)),
            ('nonfinite duration', 'NATIVE_DURATION', lambda r: r['roles']['dbs']['workload'].update(elapsed_seconds=float('nan'))),
            ('inaccurate p95', 'NATIVE_P95', lambda r: r['roles']['dbs']['workload']['api'].update(p95_bucket_upper_seconds=1)),
            ('lost native samples', 'NATIVE_SAMPLE_COVERAGE', lambda r: r['roles']['dbs']['workload']['sql'].update(attempts=1)),
            ('inconsistent histogram', 'NATIVE_HISTOGRAM', lambda r: r['roles']['dbs']['workload']['api']['histogram'].__setitem__(0, 1)),
            ('unjoined threads', 'NATIVE_INTEGRITY', lambda r: r['roles']['dbs']['workload'].update(threads_stopped=False)),
            ('changed primary', 'PRIMARY_IDENTITY', lambda r: r['roles']['dbs']['workload'].update(primary_start_time_final='new')),
            ('changed payload', 'PAYLOAD_CHECKSUM', lambda r: r['roles']['dbs']['workload']['final_checksum'].__setitem__(3, 'changed')),
            ('lost host samples', 'HOST_SAMPLE_COVERAGE', lambda r: r['roles']['dbs'].update(samples=[])),
            ('host sample gap', 'HOST_SAMPLE_GAP', lambda r: r['roles']['dbs']['samples'][1].update(elapsed_seconds=121)),
            ('changed guard', 'GUARD_OR_PID1', lambda r: r['roles']['dbs']['samples'][-1].update(cache_same_process=False)),
            ('OOM', 'OOM_KILL_DELTA', lambda r: r['roles']['dbs']['samples'][-1]['memory_events'].update(oom_kill=1)),
            ('missing cycle', 'ENGINE_CYCLE_COUNT', lambda r: r['backups'].pop()),
            ('pending cycle', 'ENGINE_CYCLE_NOT_ACCEPTED', lambda r: r['backups'][0].update(phase='content-passed-native-pending')),
            ('unclean cycle', 'ENGINE_CONTENT_OR_CLEANUP', lambda r: r['backups'][0]['roles']['dbs'].update(cleanup=False)),
            ('cycle outside native', 'ENGINE_NATIVE_ENVELOPE', lambda r: r['backups'][-1].update(content_ended_epoch=9999999999)),
            ('cleanup error', 'CAMPAIGN_CLEANUP', lambda r: r.update(cleanup_errors=['pending'])),
        ]
        for name, code, mutate in cases:
            with self.subTest(name=name):
                r = fixture();mutate(r)
                with self.assertRaisesRegex(audit.Rejected, code):
                    audit.audit(r, 'acceptance', PINS)

    def test_json_input(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'report.json'
            for blob, code in [('"value"', 'REPORT_OBJECT'),
                               ('{"phase":1,"phase":2}', 'DUPLICATE_JSON_KEY'),
                               ('{"value":NaN}', 'NONFINITE_JSON'), ('{', 'REPORT_JSON')]:
                p.write_text(blob, encoding='utf-8')
                with self.subTest(code=code), self.assertRaisesRegex(audit.Rejected, code):
                    audit.load_report(p)
            p.write_text(json.dumps(fixture('baseline')), encoding='utf-8')
            value, digest = audit.load_report(p)
            self.assertEqual(value['test_phase'], 'baseline')
            self.assertEqual(len(digest), 64)


if __name__ == '__main__':
    unittest.main()
