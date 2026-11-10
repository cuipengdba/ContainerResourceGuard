#!/usr/bin/env python3
"""Read a frozen campaign report; never start jobs or declare release acceptance."""
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sys


class Rejected(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise Rejected(code)


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def timestamp(value):
    require(isinstance(value, str), 'TIMESTAMP')
    try:
        parsed = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(parsed.tzinfo is not None, 'TIMESTAMP')
        return parsed.timestamp()
    except (ValueError, OverflowError):
        raise Rejected('TIMESTAMP') from None


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def load_report(path):
    require(path.is_file() and not path.is_symlink(), 'REPORT_FILE')
    require(path.stat().st_size <= 256 * 1024**2, 'REPORT_SIZE')
    with path.open('rb') as stream:
        blob = stream.read(256 * 1024**2 + 1)
    require(len(blob) <= 256 * 1024**2, 'REPORT_SIZE')
    try:
        value = json.loads(blob, object_pairs_hook=unique_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(Rejected('NONFINITE_JSON')))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise Rejected('REPORT_JSON') from None
    require(isinstance(value, dict), 'REPORT_OBJECT')
    return value, hashlib.sha256(blob).hexdigest()


def audit(report, phase, pins, source_run_id=None):
    require(phase in ('baseline', 'enforce', 'acceptance'), 'EXPECTED_PHASE')
    seconds = 604800 if phase == 'acceptance' else 86400
    require(report.get('schema') == 'crg-vendor-campaign-v1', 'CAMPAIGN_SCHEMA')
    require(report.get('test_phase') == phase and report.get('requested_seconds') == seconds,
            'CAMPAIGN_DURATION_OR_PHASE')
    require((phase == 'enforce' and isinstance(source_run_id, str)
             and re.fullmatch(r'[0-9]{8,12}', source_run_id))
            or (phase != 'enforce' and source_run_id is None), 'EXPECTED_SOURCE_RUN')
    require(report.get('source_run_id') == source_run_id, 'SOURCE_RUN')
    for key, digest in pins.items():
        require(re.fullmatch(r'[0-9a-f]{64}', digest) is not None, 'EXPECTED_DIGEST')
        require(report.get(key) == digest, 'SOURCE_DIGEST')
    require(set(pins) == {'agent_sha256', 'cache_sha256', 'worker_sha256',
                          'campaign_script_sha256', 'engine_script_sha256'}, 'PIN_SET')
    offsets = [300] + list(range(21600, seconds, 21600))
    require(report.get('criteria') == {
        'host_available_min_bytes': 8 * 1024**3,
        'disk_free_min_bytes': 20 * 1024**3,
        'host_sample_seconds': 60, 'OOM_kill_delta_max': 0,
        'backup_offsets_seconds': offsets}, 'CAMPAIGN_CRITERIA')
    status = report.get('phase')
    require(status in ('preparing', 'measuring', 'passed'), 'CAMPAIGN_NOT_ACCEPTED')
    if status != 'passed':
        return {'phase': 'pending', 'requested_seconds': seconds,
                'continuous_report_accepted': False, 'release_accepted': False,
                'runtime_cleanup_verified': False}
    require(not report.get('cleanup_errors'), 'CAMPAIGN_CLEANUP')
    roles = report.get('roles', {})
    require(set(roles) == {'dbs', 'hisdbs'}, 'ROLE_SET')
    windows = {}
    for role, row in roles.items():
        workload = row.get('workload', {})
        require(workload.get('schema') == 'crg-vendor-soak-v1'
                and workload.get('phase') == 'passed'
                and workload.get('test_phase') == phase
                and workload.get('requested_duration_seconds') == seconds, 'NATIVE_PHASE')
        elapsed = workload.get('elapsed_seconds')
        require(number(elapsed) and elapsed >= seconds, 'NATIVE_DURATION')
        for flag in ('threads_stopped', 'payload_integrity', 'primary_not_restarted'):
            require(workload.get(flag) is True, 'NATIVE_INTEGRITY_OR_PROCESS')
        require(workload.get('interrupted') is False, 'NATIVE_INTERRUPTED')
        require(workload.get('source_run_id') == source_run_id, 'NATIVE_SOURCE_RUN')
        require(workload.get('primary_start_time_initial')
                and workload['primary_start_time_initial'] == workload.get('primary_start_time_final'),
                'PRIMARY_IDENTITY')
        before, after = workload.get('initial_checksum', []), workload.get('final_checksum', [])
        require(len(before) == 5 and len(after) == 5
                and before[:3] == [16384, 134225920, 67108864]
                and before[:4] == after[:4], 'PAYLOAD_CHECKSUM')
        require(workload.get('criteria') == {
            'sql_period_seconds': 2, 'api_period_seconds': 5,
            'maximum_errors': 0, 'maximum_seconds': 5,
            'p95_upper_bound_seconds': 1, 'minimum_scheduled_samples_fraction': .98},
            'NATIVE_CRITERIA')
        bounds = [.001, .005, .01, .02, .05, .1, .25, .5, 1, 2, 5, 'over-5']
        require(workload.get('latency_bucket_upper_seconds') == bounds, 'NATIVE_BUCKETS')
        for kind, period in [('sql', 2), ('api', 5)]:
            item = workload.get(kind, {})
            attempts, hist = item.get('attempts'), item.get('histogram', [])
            require(type(attempts) is int and attempts >= seconds / period * .98,
                    'NATIVE_SAMPLE_COVERAGE')
            require(type(item.get('errors')) is int and item['errors'] == 0
                    and type(item.get('successes')) is int and item['successes'] == attempts,
                    'NATIVE_ERRORS')
            require(number(item.get('max_seconds')) and 0 <= item['max_seconds'] <= 5,
                    'NATIVE_MAXIMUM')
            require(len(hist) == len(bounds) and all(type(x) is int and x >= 0 for x in hist)
                    and sum(hist) == attempts, 'NATIVE_HISTOGRAM')
            cumulative = 0
            for index, count in enumerate(hist):
                cumulative += count
                if cumulative >= attempts * .95:
                    p95 = bounds[index]
                    break
            require(number(p95) and p95 <= 1
                    and item.get('p95_bucket_upper_seconds') == p95, 'NATIVE_P95')
            require(number(item.get('sample_coverage'))
                    and abs(item['sample_coverage'] - attempts / (seconds / period)) < 1e-9,
                    'NATIVE_SAMPLE_COVERAGE')
        start = timestamp(workload.get('started_utc'))
        end = timestamp(workload.get('measurement_finished_utc'))
        require(end >= start, 'NATIVE_WINDOW')
        windows[role] = (start, end)
        controls = row.get('fixed_controls', {})
        require(set(controls) == {'cpu.max', 'memory.max', 'io.max', 'cpu.weight',
                                  'pids.max', 'memory.high', 'memory.swap.max', 'io.weight'},
                'CONTROL_SET')
        require(all(isinstance(value, str) for value in controls.values()), 'CONTROL_VALUES')
        samples = row.get('samples', [])
        require(len(samples) >= seconds / 60 * .98, 'HOST_SAMPLE_COVERAGE')
        previous = None
        oom = None
        for sample in samples:
            elapsed = sample.get('elapsed_seconds')
            require(number(elapsed) and elapsed >= 0
                    and (previous is None or 0 <= elapsed - previous <= 120), 'HOST_SAMPLE_GAP')
            previous = elapsed
            require(all(sample.get(key) is True for key in
                        ('agent_same_process', 'cache_same_process', 'PID1_same_process')),
                    'GUARD_OR_PID1_IDENTITY')
            current = sample.get('memory_events', {}).get('oom_kill')
            require(type(current) is int and current >= 0 and (oom is None or current == oom),
                    'OOM_KILL_DELTA')
            oom = current
    cycles = report.get('backups', [])
    require(len(cycles) == len(offsets), 'ENGINE_CYCLE_COUNT')
    for cycle, offset in zip(cycles, offsets):
        require(cycle.get('phase') == 'passed' and cycle.get('content_phase') == 'content-passed-native-pending'
                and type(cycle.get('exit')) is int and cycle['exit'] == 0
                and cycle.get('native_workload_validation') == 'passed-with-entire-campaign',
                'ENGINE_CYCLE_NOT_ACCEPTED')
        require(number(cycle.get('offset_seconds')) and cycle['offset_seconds'] >= offset,
                'ENGINE_CYCLE_OFFSET')
        start, end = cycle.get('content_started_epoch'), cycle.get('content_ended_epoch')
        require(number(start) and number(end) and start <= end, 'ENGINE_CYCLE_WINDOW')
        require(set(cycle.get('roles', {})) == set(roles), 'ENGINE_ROLE_SET')
        for role, value in cycle['roles'].items():
            require(value.get('checks') == 10 and value.get('cleanup') is True
                    and value.get('native_pending') is True, 'ENGINE_CONTENT_OR_CLEANUP')
            require(windows[role][0] <= start <= end <= windows[role][1], 'ENGINE_NATIVE_ENVELOPE')
    return {'phase': 'passed', 'requested_seconds': seconds, 'roles': sorted(roles),
            'accepted_engine_cycles': len(cycles), 'continuous_report_accepted': True,
            'release_accepted': False, 'runtime_cleanup_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--phase', required=True, choices=['baseline', 'enforce', 'acceptance'])
    parser.add_argument('--source-run-id')
    for flag in ('agent', 'cache', 'worker', 'campaign-script', 'engine-script'):
        parser.add_argument('--' + flag + '-sha256', required=True)
    args = parser.parse_args()
    try:
        value, digest = load_report(args.report)
        pins = {key: getattr(args, key) for key in ('agent_sha256', 'cache_sha256', 'worker_sha256',
                                                   'campaign_script_sha256', 'engine_script_sha256')}
        result = audit(value, args.phase, pins, args.source_run_id)
        result['report_sha256'] = digest
    except Rejected as error:
        result = {'phase': 'rejected', 'reason': str(error), 'release_accepted': False}
    except (OSError, TypeError, KeyError, AttributeError, ValueError, OverflowError, RecursionError):
        result = {'phase': 'rejected', 'reason': 'REPORT_SHAPE_OR_READ', 'release_accepted': False}
    print(json.dumps(result, sort_keys=True))
    return {'passed': 0, 'pending': 2, 'rejected': 1}[result['phase']]


if __name__ == '__main__':
    sys.exit(main())
