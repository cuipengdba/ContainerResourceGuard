#!/usr/bin/env python3
"""Offline, bounded review of byte-exact pressure/device/PG evidence.

Reads an evidence archive or the private collected directory. Does not connect
to a node, change controls, run a workload, or infer causality from overlap.
"""
import argparse
import collections
import gzip
import hashlib
import io
import json
from pathlib import Path

MAX_TOTAL = 64 * 1024 * 1024


def require(value, reason):
    if not value:
        raise ValueError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_files(path, archive):
    if archive:
        require(path.stat().st_size <= 8 * 1024 * 1024, 'ARCHIVE_BOUND')
        with gzip.GzipFile(fileobj=io.BytesIO(path.read_bytes())) as stream:
            raw = stream.read(MAX_TOTAL + 1)
        require(len(raw) <= MAX_TOTAL, 'EXPANSION_BOUND')
        bundle = json.loads(raw)
        require(bundle['schema'] == 'crg-pressure342-terminal-exact-evidence-v1', 'EVIDENCE_SCHEMA')
        values = {name: row['exact_utf8'].encode('utf-8') for name, row in bundle['files'].items()}
        manifest = bundle['manifest']
    else:
        manifest = json.loads((path / 'manifest.json').read_bytes())
        values = {}
        for name, row in manifest['files'].items():
            parts = name.split('/')
            require(not name.startswith('/') and '\\' not in name and all(x not in ['', '.', '..'] for x in parts), 'RELATIVE_NAME')
            source = path.joinpath(*parts)
            require(source.is_file() and not source.is_symlink() and source.stat().st_size <= 32 * 1024 * 1024, 'FILE_BOUND')
            values[name] = source.read_bytes()
    require(1 <= len(manifest['files']) <= 96 and set(values) == set(manifest['files']), 'MANIFEST_MEMBERS')
    require(sum(len(v) for v in values.values()) <= MAX_TOTAL, 'TOTAL_BOUND')
    for name, raw in values.items():
        row = manifest['files'][name]
        require(len(raw) == row['bytes'] and digest(raw) == row['sha256'], 'FILE_DIGEST:' + name)
    return values


def available(row, name):
    value = row['cgroup'][name]
    return value['value'] if value['available'] else None


def counter_delta(before, after):
    if before is None or after is None or set(before) != set(after) or any(after[k] < before[k] for k in before):
        return {'available': False, 'reason': 'missing-reset-or-layout-change'}
    return {'available': True, 'deltas': {k: after[k] - before[k] for k in before}}


def interval(before, after):
    seconds = after['monotonic'] - before['monotonic']
    require(seconds > 0 and after['epoch'] >= before['epoch'], 'INTERVAL_CLOCK_ORDER')
    left, right = available(before, 'io.stat'), available(after, 'io.stat')
    controls_a, controls_b = available(before, 'io.max'), available(after, 'io.max')
    io_deltas = {}
    for name in sorted(set(left or {}) | set(right or {})):
        value = counter_delta((left or {}).get(name), (right or {}).get(name))
        if value['available']:
            value['rates_per_second'] = {k: n / seconds for k, n in value['deltas'].items()}
        io_deltas[name] = value
    devices = {}
    for name in before['devices']:
        a, b = before['devices'][name], after['devices'][name]
        if not a['available'] or not b['available']:
            devices[name] = {'available': False, 'reason': 'missing-device-counters'}
            continue
        av, bv = a['value'], b['value']
        # in_flight is a gauge, not an accumulated counter. Keep layers separate.
        counters = ['reads_completed', 'writes_completed', 'read_sectors_512bytes', 'write_sectors_512bytes', 'io_ms', 'weighted_io_ms']
        value = counter_delta({k: av[k] for k in counters}, {k: bv[k] for k in counters})
        value.update(in_flight_at_start=av['in_flight'], in_flight_at_end=bv['in_flight'])
        devices[name] = value
    return {'started_epoch': before['epoch'], 'ended_epoch': after['epoch'], 'seconds': seconds,
            'control_endpoints_equal': controls_a == controls_b, 'io_max_start': controls_a, 'io_max_end': controls_b,
            'cgroup_io_by_layer': io_deltas, 'device_raw_delta_by_layer': devices,
            'cpu_delta': counter_delta(available(before, 'cpu.stat'), available(after, 'cpu.stat'))}


def task_observations(samples, start, end):
    rows = []
    for sample in samples:
        if not start <= sample['epoch'] <= end:
            continue
        for task in sample['tasks']:
            if task['stat']['state'] == 'D':
                rows.append({'epoch': sample['epoch'], 'tid': task['stat']['pid'],
                             'start_ticks': task['stat']['start_ticks'], 'wchan': task['wchan'],
                             'wait_detail': task.get('wait_detail', {'available': False, 'reason': 'not-captured'})})
    return rows


def analyze(values):
    report = json.loads(values['report.json'])
    require(report['schema'] == 'crg-business-memory-pressure-device-pgwait-report-v1' and report['phase'] in ['passed', 'failed'], 'TERMINAL_REPORT')
    require(report['namespace_absent'] and report['original_config_bytes_and_profile_absence_restored'], 'RECORDED_CLEANUP')
    out = {'schema': 'crg-pressure-device-pg-offline-review-v1', 'terminal_phase': report['phase'],
           'terminal_reason': report.get('reason'), 'main_checks': len(report['tests']), 'roles': {},
           'inputs_sha256': {k: digest(v) for k, v in values.items()},
           'limits': ['Overlap is observation, not IO causality.', 'Device layers are not independent disks and must not be summed.',
                      'PG snapshots select this run native SQL client; other API database backends are not covered.',
                      'Optional unavailable fields stay unknown; no unavailable value becomes zero.',
                      'Device/PG/thread reads are separate snapshots; counter brackets are not request-owned IO.'],
           'original_business_gate_waived': False, 'stable_release_accepted': False}
    for role, item in report['roles'].items():
        boot = item['boots'][-1]
        native = json.loads(values[role + '/native/load.json'])
        diagnostics = json.loads(values[role + '/native-diagnostics.json'])
        device = json.loads(values[role + '/devices.json'])
        thread = json.loads(values[role + '/threads.json'])
        require(digest(values[role + '/native-diagnostics.json']) == native['native_diagnostics']['report_sha256'], 'NATIVE_DIAGNOSTIC_BINDING')
        require(diagnostics['run_id'] == native['run_id'] and diagnostics['schema'] == 'crg-native-request-pg-diagnostics-v2', 'RUN_BINDING')
        require(device['plan']['cgroup'] == thread['plan']['cgroup'] == boot['cgroup'] and device['plan']['pid'] == thread['plan']['pid']
                and device['plan']['start_ticks'] == thread['plan']['start_ticks'], 'TARGET_BINDING')
        require(device['sample_count'] == len(device['samples']) and thread['sample_count'] == len(thread['samples']), 'SAMPLE_COUNT')
        intervals = [interval(a, b) for a, b in zip(device['samples'], device['samples'][1:])]
        errors = [r for r in diagnostics['requests'] if not r['success'] or not r['within_original_5seconds']]
        require(len(errors) == native['sql']['errors'] + native['api']['errors'], 'ERROR_COUNT')
        windows = []
        for request in errors:
            start, end = request['started_epoch'], request['ended_epoch']
            selected = [r for r in intervals if r['started_epoch'] <= end and r['ended_epoch'] >= start]
            pg = [s for s in diagnostics['pg_samples'] if s['started_epoch'] <= end and s['ended_epoch'] >= start]
            windows.append({'request': request, 'strict_request_D_observations': task_observations(thread['samples'], start, end),
                            'PG_samples_with_independent_wait_intervals': pg,
                            'device_counter_brackets': selected,
                            'all_error_after_last_reload': start > max(r['ended_epoch'] for r in boot['reload_intervals'])})
        drows = task_observations(thread['samples'], float('-inf'), float('inf'))
        pg_waits = [s['pg_wait'] for s in diagnostics['pg_samples']]
        stacks = [r['kernel_wait'].get('kernel_stack', {'available': False, 'reason': 'not-captured'}) for w in pg_waits for r in w['targets']]
        maximum_rates = {}
        for name in device['samples'][0]['devices']:
            rates = [r['cgroup_io_by_layer'][name]['rates_per_second'] for r in intervals
                     if name in r['cgroup_io_by_layer'] and r['cgroup_io_by_layer'][name]['available']]
            maximum_rates[name] = {k: max(v[k] for v in rates) for k in ['rbytes', 'wbytes', 'rios', 'wios']} if rates else None
        out['roles'][role] = {'native_phase': native['phase'], 'native_elapsed_seconds': native['elapsed_seconds'],
            'native_SQL': native['sql'], 'native_API': native['api'], 'requests': len(diagnostics['requests']),
            'reload_intervals': len(boot['reload_intervals']), 'engine_content_checks': len(boot['engine']['roles'][role]['checks']),
            'PG_samples': len(diagnostics['pg_samples']), 'PG_wait_available_samples': sum(w['available'] for w in pg_waits),
            'PG_kernel_stack_available': sum(s['available'] for s in stacks), 'PG_kernel_stack_unknown': sum(not s['available'] for s in stacks),
            'thread_samples': len(thread['samples']), 'D_observations': len(drows),
            'D_tid_instances': [list(v) for v in sorted(set((r['tid'], r['start_ticks']) for r in drows))],
            'D_descriptor_counts': dict(collections.Counter(r['wait_detail'].get('descriptor', {}).get('path', 'unknown') for r in drows)),
            'device_samples': len(device['samples']), 'device_report_phase': device['phase'], 'device_report_reason': device.get('reason'),
            'device_counter_intervals': len(intervals), 'maximum_cgroup_rates_per_second_by_layer': maximum_rates,
            'whole_device_observer_cpu_seconds': boot['device_observer']['whole_child_cpu_seconds'],
            'whole_thread_observer_cpu_seconds': boot['thread_observer']['whole_child_cpu_seconds'],
            'native_internal_thread_cpu_seconds': boot['native_request_pg']['internal_thread_CPU_seconds'],
            'error_windows': windows, 'IO_causality_proven': False}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--directory', type=Path)
    group.add_argument('--evidence', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = analyze(read_files(args.evidence or args.directory, args.evidence is not None))
    raw = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(raw)
        print(json.dumps({'phase': 'reviewed', 'output': str(args.output), 'terminal_phase': result['terminal_phase'],
                          'main_checks': result['main_checks'], 'roles': list(result['roles'])}))
    else:
        print(raw, end='')


if __name__ == '__main__':
    main()
