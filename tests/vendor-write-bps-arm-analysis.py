#!/usr/bin/env python3
"""Reproduce one completed R272 arm from pinned JSON evidence, entirely offline.

The input directory contains manifest.json and report/native/request-pg/threads/
engine.json (or their .gz forms). No workload, live /proc, signal, or controller
operation is performed. An arm never certifies the original release acceptance.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
import os
from pathlib import Path

MAXIMUM = 33554432
EXECUTOR = 'bc4b46a8b43a6d6b787f6bc65b1c229774a02102af44a87f6f1b61610fda2a93'
PLAN = 'b3b355e10ed21aca6e652e1ffb36c2ddadd1a5820393988b5b03de7e10425027'
BINARY = 'dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8'
ARMS = {'a1': 37470104, 'b': 67108864, 'a2': 37470104}
METRICS = {'rbytes': 'rbps', 'wbytes': 'wbps', 'rios': 'riops', 'wios': 'wiops'}


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    need(path.is_file() and path.stat().st_size <= MAXIMUM, 'input missing/oversized: ' + str(path))
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rb') as f:
        raw = f.read(MAXIMUM + 1)
    need(len(raw) <= MAXIMUM, 'decompressed input too large')
    return json.loads(raw), raw


def available(sample, name):
    value = sample['cgroup'][name]
    return value['value'] if value['available'] else None


def pairs(text):
    if text is None:
        return None
    rows = [line.split() for line in text.splitlines()]
    need(all(len(r) == 2 and r[1].isdigit() for r in rows), 'invalid counter rows')
    need(len({r[0] for r in rows}) == len(rows), 'duplicate counter')
    return {k: int(v) for k, v in rows}


def devices(text):
    if text is None:
        return None
    out = {}
    for line in text.splitlines():
        parts = line.split()
        need(len(parts) >= 2 and parts[0] not in out, 'invalid/duplicate device')
        values = {}
        for field in parts[1:]:
            k, v = field.split('=')
            need(k not in values and (v.isdigit() or v == 'max'), 'invalid device field')
            values[k] = None if v == 'max' else int(v)
        out[parts[0]] = values
    return out


def distribution(values):
    values = sorted(values)
    return {'count': len(values), 'minimum': values[0], 'median': values[(len(values)-1)//2],
            'p95_nearest_rank': values[math.ceil(len(values)*.95)-1], 'maximum': values[-1]} if values else None


def io_summary(rows):
    out = {'intervals': len(rows), 'seconds': sum(r['seconds'] for r in rows), 'devices_do_not_add_parent_and_child': {}}
    for dev in sorted({d for r in rows for d in r['io']}):
        valid = [r for r in rows if r['io'].get(dev, {}).get('available')]
        duration = sum(r['seconds'] for r in valid)
        out['devices_do_not_add_parent_and_child'][dev] = {
            'valid_intervals': len(valid), 'unknown_intervals': len(rows)-len(valid),
            'seconds': duration, 'metrics': {k: {
                'counter_delta': sum(r['io'][dev]['deltas'][k] for r in valid),
                'counter_delta_per_second': sum(r['io'][dev]['deltas'][k] for r in valid)/duration if duration else None,
                'interval_rates': distribution([r['io'][dev]['rates'][k] for r in valid]),
                'ratios_to_constant_cap': distribution([r['io'][dev]['ratios'][k] for r in valid if r['io'][dev]['ratios'][k] is not None]),
            } for k in METRICS}}
    return out


def analyze(directory, arm):
    manifest, _ = load(directory/'manifest.json')
    names = ['report', 'native', 'request-pg', 'threads', 'engine']
    need(set(manifest) == {n+'.json' for n in names}, 'unexpected manifest inputs')
    data, hashes = {}, {}
    for name in names:
        filename = name+'.json'
        path = directory/filename
        value, raw = load(path if path.exists() else directory/(filename+'.gz'))
        need(sha(raw) == manifest[filename]['sha256'] and len(raw) == manifest[filename]['bytes'], 'input digest/size mismatch: '+name)
        need('/'+arm+'/' in manifest[filename]['remote'], 'arm path mismatch')
        data[name], hashes[filename] = value, sha(raw)
    report, native, requests, threads, engine = [data[n] for n in names]
    need(report['schema'] == 'crg-write-bps-diagnostic-arm-v1' and report['arm'] == arm and report['write_bps'] == ARMS[arm], 'arm identity mismatch')
    need(report['executor_sha256'] == EXECUTOR and report['plan_sha256'] == PLAN and report['binary_sha256'] == BINARY, 'frozen input mismatch')
    need(report['phase'] in ['passed', 'failed'] and report['namespace_absent'] and report['original_config_bytes_and_profile_absence_restored'], 'arm not terminal/restored')
    need(not report['release_accepted'] and not report['original_release_acceptance_executed'], 'scope mismatch')
    boot = report['roles']['dbs']['boots'][-1]
    diag = boot['native_request_pg']
    need(hashes['native.json'] == diag['native_report_sha256'], 'native cross-reference mismatch')
    need(hashes['request-pg.json'] == diag['raw_report_sha256'] == native['native_diagnostics']['report_sha256'], 'request cross-reference mismatch')
    need(hashes['threads.json'] == boot['thread_observer']['raw_report_sha256'] and threads['plan'] == boot['thread_observer']['plan'], 'thread cross-reference mismatch')
    need(engine == boot['engine'], 'engine cross-reference mismatch')
    need(native['schema'] == 'crg-vendor-soak-v1' and native['run_id'] == requests['run_id'] == '202611112720', 'native identity mismatch')
    need(requests['schema'] == 'crg-native-request-pg-diagnostics-v1' and threads['schema'] == 'crg-vendor-thread-wait-observer-report-v1', 'diagnostic schema mismatch')
    need(requests['worker_sha256'] == '50ea0454d17d5412a9d4085472ed89831e4408f60aa0fa0ca2dfd905a2bacb1f', 'native worker changed')
    need(threads['target_signals_or_control_writes'] == 0 and native['native_diagnostics']['business_signals_cancellations_or_control_writes'] == 0, 'observer scope changed')
    need(native['requested_duration_seconds'] == 600 and native['criteria'] == {
        'api_period_seconds': 5, 'maximum_errors': 0, 'maximum_seconds': 5,
        'minimum_scheduled_samples_fraction': .98, 'p95_upper_bound_seconds': 1, 'sql_period_seconds': 2}, 'original native criteria changed')
    need(native['initial_checksum'][2] == 67108864 and native['final_checksum'][2] == 67108864, 'payload changed')
    need(len(requests['requests']) <= 1024 and len(requests['pg_samples']) <= 901 and len(threads['samples']) <= 901, 'sample bound exceeded')
    for kind in ['sql', 'api']:
        need(sum(r['kind'] == kind for r in requests['requests']) == native[kind]['attempts'], 'request count mismatch')
    samples = threads['samples']
    need(len(samples) >= 2, 'insufficient samples')
    transitions = boot['reload_intervals']
    intervals = []
    for old, new in zip(samples, samples[1:]):
        dt = new['monotonic']-old['monotonic']
        need(dt > 0 and new['epoch'] > old['epoch'] and abs(new['epoch']-old['epoch']-dt) < .05, 'sample clock discontinuity')
        a, b = devices(available(old, 'io.stat')), devices(available(new, 'io.stat'))
        ac, bc = devices(available(old, 'io.max')), devices(available(new, 'io.max'))
        transition = any(v['started_epoch'] <= new['epoch'] and v['ended_epoch'] >= old['epoch'] for v in transitions)
        row = {'first_epoch': old['epoch'], 'last_epoch': new['epoch'], 'seconds': dt,
               'overlaps_policy_transition': transition, 'controls': {k: available(new, k) for k in ['cpu.max', 'memory.max', 'io.max']}, 'io': {}}
        for dev in sorted(set(a or {}) | set(b or {})):
            if not a or not b or dev not in a or dev not in b or any(k not in a[dev] or k not in b[dev] or b[dev][k] < a[dev][k] for k in METRICS):
                row['io'][dev] = {'available': False, 'reason': 'missing-counter-or-reset'}
                continue
            delta = {k: b[dev][k]-a[dev][k] for k in METRICS}
            cap = ac.get(dev) if ac and bc and ac.get(dev) == bc.get(dev) and not transition else None
            row['io'][dev] = {'available': True, 'deltas': delta, 'rates': {k: v/dt for k, v in delta.items()},
                              'ratios': {k: delta[k]/dt/cap[limit] if cap and cap.get(limit) else None for k, limit in METRICS.items()}}
        intervals.append(row)
    d_samples = [{'epoch': s['epoch'], 'task': t} for s in samples for t in s['tasks'] if t['stat']['state'] == 'D']
    runs = []
    by_task = defaultdict(list)
    for d in d_samples:
        by_task[(d['task']['stat']['pid'], d['task']['stat']['start_ticks'])].append(d)
    for (tid, start), hits in sorted(by_task.items()):
        groups = []
        for hit in hits:
            if not groups or hit['epoch']-groups[-1][-1]['epoch'] > 1.1:
                groups.append([])
            groups[-1].append(hit)
        runs.extend({'tid': tid, 'start_ticks': start, 'first_epoch': g[0]['epoch'], 'last_epoch': g[-1]['epoch'], 'samples': len(g),
                     'sample_span_seconds_not_continuous_wait_duration': g[-1]['epoch']-g[0]['epoch']} for g in groups)
    errors = [r for r in requests['requests'] if not r['success'] or not r['within_original_5seconds']]
    windows = []
    for request in errors:
        selected = [r for r in intervals if r['first_epoch'] <= request['ended_epoch'] and r['last_epoch'] >= request['started_epoch']]
        pg_rows, excluded = [], 0
        if request['kind'] == 'sql':
            for pg in requests['pg_samples']:
                if pg['started_epoch'] <= request['ended_epoch'] and pg['ended_epoch'] >= request['started_epoch']:
                    for row in pg.get('rows', []):
                        if row['pid'] != request['backend_pid']:
                            continue
                        observed = request['connection_observed_epoch']
                        if (not row['identity_available'] or observed is None or row['backend_start_epoch'] > observed
                                or pg['started_epoch'] < observed):
                            excluded += 1
                            continue
                        pg_rows.append({'sample_started_epoch': pg['started_epoch'], 'sample_ended_epoch': pg['ended_epoch'], **row})
        identities = sorted({(r['pid'], r['backend_start_epoch']) for r in pg_rows})
        memory = [pairs(available(s, 'memory.stat')) for s in samples if request['started_epoch'] <= s['epoch'] <= request['ended_epoch']]
        windows.append({'request': request, 'D_samples_strictly_within_request': sum(request['started_epoch'] <= d['epoch'] <= request['ended_epoch'] for d in d_samples),
                        'D_samples_in_IO_bracket_including_possible_outside_samples': sum(any(r['first_epoch'] <= d['epoch'] <= r['last_epoch'] for r in selected) for d in d_samples),
                        'bracket_IO': io_summary(selected), 'bracket_controls': {k: sorted({r['controls'][k] for r in selected}, key=str) for k in ['cpu.max', 'memory.max', 'io.max']},
                        'overlaps_recorded_policy_transition': any(r['overlaps_policy_transition'] for r in selected),
                        'seconds_after_last_transition': request['started_epoch']-max(t['ended_epoch'] for t in transitions),
                        'memory_during_request': {k: distribution([m[k] for m in memory if m is not None and k in m]) for k in ['file_dirty', 'file_writeback', 'anon', 'shmem']},
                        'PG_identity_join': 'one-temporally-eligible-pid-and-backend-start' if len(identities) == 1 else 'unknown-or-ambiguous',
                        'PG_identity_candidates': identities, 'PG_rows_excluded_for_identity_or_sample_boundary': excluded,
                        'PG_rows': pg_rows, 'blocking_pids_null_is_not_a_no_blockers_measurement': True})
    need(len(errors) == diag['error_count'], 'error count mismatch')
    def deltas(name):
        first, last = pairs(available(samples[0], name)), pairs(available(samples[-1], name))
        return {k: last[k]-v if last[k] >= v else None for k, v in first.items() if k in last} if first and last else None
    details = Counter((d['task'].get('wait_detail', {}).get('syscall', {}).get('operation'),
                       d['task'].get('wait_detail', {}).get('descriptor', {}).get('path')) for d in d_samples)
    stacks = Counter(tuple(d['task'].get('wait_detail', {}).get('kernel_stack', {}).get('frames', [])) for d in d_samples)
    probes = engine['roles']['dbs']['probes']
    failed_probes = [v for v in probes if v.get('api_ok') is False or v.get('api_seconds', 0) > 5
                     or v.get('api_inner', {}).get('request_ok') is False or v.get('api_inner', {}).get('request_seconds', 0) > 5]
    native_checks = {'elapsed600': native['elapsed_seconds'] >= 600, 'not_interrupted': not native['interrupted'],
                     'threads_stopped': native['threads_stopped'], 'payload_integrity': native['payload_integrity'], 'primary_not_restarted': native['primary_not_restarted'],
                     **{kind+'_'+key: value for kind in ['sql', 'api'] for key, value in {
                         'errors0': native[kind]['errors'] == 0, 'max_at_most5': native[kind]['max_seconds'] <= 5,
                         'p95_at_most1': isinstance(native[kind]['p95_bucket_upper_seconds'], (int, float)) and native[kind]['p95_bucket_upper_seconds'] <= 1,
                         'coverage_at_least98percent': native[kind]['sample_coverage'] >= .98}.items()}}
    return {'schema': 'crg-write-bps-arm-offline-analysis-v1', 'arm': arm, 'write_bps': ARMS[arm],
            'input_sha256': hashes, 'analysis_source_sha256': sha(Path(__file__).read_bytes()),
            'arm_phase': report['phase'], 'arm_reason': report.get('reason'), 'native_phase': native['phase'],
            'native_seconds': native['elapsed_seconds'], 'SQL': native['sql'], 'API': native['api'],
            'native_original_criteria_checks': native_checks, 'all_native_criteria_passed': all(native_checks.values()),
            'local_checks': len(report['tests']), 'reload_intervals': len(transitions),
            'native_final_flush': boot['native_final_flush'], 'errors': windows,
            'thread_observer_actual': {k: threads.get(k) for k in ['phase', 'reason', 'elapsed_seconds', 'sample_count', 'observer_cpu_seconds', 'maximum_collection_seconds']},
            'D_samples': len(d_samples), 'D_runs': runs,
            'D_operations_and_paths': [{'operation': op, 'path': path, 'samples': count} for (op, path), count in details.items()],
            'D_stack_variants': [{'frames': list(frames), 'samples': count} for frames, count in stacks.items()],
            'whole_thread_sample_IO': io_summary(intervals), 'cpu_stat_deltas': deltas('cpu.stat'), 'memory_event_deltas': deltas('memory.events'),
            'PSI_available_sample_counts': {k: sum(available(s, k) is not None for s in samples) for k in ['cpu.pressure', 'memory.pressure', 'io.pressure']},
            'engine': {'phase': engine['phase'], 'content_checks': len(engine['roles']['dbs']['checks']), 'probe_count': len(probes),
                       'failed_or_above5s_API_probes': failed_probes},
            'interpretation': {'read_only_offline': True, 'IO_counters_are_not_physical_completion_bandwidth': True,
                               'temporary_ratio_above1_is_not_limit_violation': True, 'sample_spans_are_not_continuous_wait_proof': True,
                               'separate_proc_reads_are_not_atomic': True, 'D_thread_request_role_or_causal_chain_proven': False,
                               'original32_two_role_percentage_acceptance_executed': False},
            'stable_release_accepted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--arm', choices=ARMS, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.directory, args.arm)
    raw = (json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')
    need(len(raw) <= MAXIMUM, 'output bound exceeded')
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(raw)
    print(json.dumps({'output': str(args.output), 'sha256': sha(raw), 'arm': args.arm,
                      'native_phase': result['native_phase'], 'SQL_errors': result['SQL']['errors'],
                      'API_errors': result['API']['errors'], 'D_samples': result['D_samples'],
                      'all_native_criteria_passed': result['all_native_criteria_passed'], 'stable_release_accepted': False}))


if __name__ == '__main__':
    main()
