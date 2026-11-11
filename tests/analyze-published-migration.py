#!/usr/bin/env python3
"""Read-only, bounded review of published-version controlled migration evidence."""
import argparse
import ast
import datetime
import decimal
import gzip
import hashlib
import json
from pathlib import Path


def load(path):
    with gzip.open(path, 'rb') as stream:
        raw = stream.read(32 * 1024 * 1024 + 1)
    if len(raw) > 32 * 1024 * 1024:
        raise ValueError('evidence exceeds bounds')
    archive = json.loads(raw)
    if archive['schema'] != 'crg-published-migration-evidence-v1' or archive['raw_private_state_excluded'] is not True:
        raise ValueError('unexpected evidence contract')
    files = {}
    for name, entry in archive['files'].items():
        raw = entry['text'].encode('utf-8')
        if len(raw) != entry['bytes'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('evidence digest mismatch: ' + name)
        files[name] = raw
    return files


def native_checks(value):
    checks = {'phase': value.get('phase') == 'passed',
              'actual600': value.get('requested_duration_seconds') == 600 and value.get('elapsed_seconds', 0) >= 600,
              'uninterrupted': value.get('interrupted') is False and value.get('threads_stopped') is True,
              'same_primary': value.get('primary_not_restarted') is True and
              value.get('primary_start_time_initial') == value.get('primary_start_time_final'),
              '64MiB_payload': value.get('payload_integrity') is True and
              value.get('initial_checksum', [])[:4] == value.get('final_checksum', [])[:4] and
              len(value.get('initial_checksum', [])) >= 4 and value['initial_checksum'][0] == 16384 and
              value['initial_checksum'][2] == 67108864}
    bounds = value.get('latency_bucket_upper_seconds', [])
    for kind, period in [('sql', 2), ('api', 5)]:
        item = value.get(kind, {})
        attempts = item.get('attempts', 0)
        histogram = item.get('histogram', [])
        p95, cumulative = None, 0
        if attempts > 0 and len(bounds) == len(histogram):
            for limit, count in zip(bounds, histogram):
                cumulative += count
                if cumulative >= attempts * .95:
                    p95 = limit
                    break
        checks[kind + '_SLA'] = (attempts > 0 and attempts == item.get('successes', 0) + item.get('errors', 0) and
                                attempts == sum(histogram) and item.get('errors') == 0 and
                                item.get('max_seconds', 6) <= 5 and attempts / (600 / period) >= .98 and
                                isinstance(p95, (int, float)) and p95 <= 1)
    return checks


def analyze(path):
    files = load(path)
    plan = json.loads(files['plan.json'])
    source = files['source.py']
    tree = ast.parse(source)
    frozen = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and
                  any(isinstance(t, ast.Name) and t.id == 'FROZEN_PLAN' for t in n.targets))
    if plan != dict(frozen, executor_sha256=hashlib.sha256(source).hexdigest()):
        raise ValueError('plan/source binding mismatch')
    terminal = json.loads(files['independent-terminal.json'])
    report = json.loads(files['report.json'])
    if hashlib.sha256(files['report.json']).hexdigest() != terminal['report_sha256'] or report != terminal['report']:
        raise ValueError('independent report binding mismatch')
    checks = {'source_matches_report': report.get('job_sha256') == plan['executor_sha256'],
              'plan_matches_report': report.get('plan_sha256') == hashlib.sha256(files['plan.json']).hexdigest(),
              'both_roles': set(report.get('roles', {})) == {'dbs', 'hisdbs'},
              'published_binary_identities': all(report.get('sources', {}).get(k, {}).get('binary_sha256') ==
                  plan['programs'][k]['binary_sha256'] for k in ['previous', 'candidate']),
              'all26': len(report.get('tests', [])) == 26 and len({x['name'] for x in report.get('tests', [])}) == 26 and
              all(x['passed'] is True for x in report.get('tests', [])),
              'terminal_passed': report.get('phase') == 'passed' and terminal['exit']['exit'] == 0,
              'namespace_absent': report.get('namespace_absent') is True and terminal.get('namespace_absent') is True,
              'original_instances_gone': set(terminal['processes']) == {'runner', 'worker'} and
              all(v['same_instance_present'] is False for v in terminal['processes'].values()),
              'both_pod_cgroups_absent': terminal.get('both_pod_uids_pinned_from_network_gate') is True and
              len(terminal.get('pod_parent_cgroups', {})) == 2 and
              all(not v['pod_cgroup_paths_present'] for v in terminal['pod_parent_cgroups'].values()),
              'frozen_inputs_retained': len(terminal.get('frozen_inputs_still_match', {})) >= len(plan['inputs_sha256']) and
              all(v is True for v in terminal.get('frozen_inputs_still_match', {}).values())}
    roles = {}
    for role in ['dbs', 'hisdbs']:
        item = report.get('roles', {}).get(role, {})
        native = item.get('native', {})
        scope = native_checks(native)
        scope['13_role_checks'] = len([v for v in report.get('tests', []) if v['name'].startswith(role + '-')]) == 13
        snapshots = item.get('invariant_snapshots', [])
        scope['phase_vectors_recorded'] = len(snapshots) >= 8
        scope['all_invariants'] = bool(snapshots) and all(all(v['checks'].values()) for v in snapshots)
        phase_counts = {v['mutation_count'] for v in snapshots}
        scope['both_journal_phases'] = 0 in phase_counts and any(v > 0 for v in phase_counts)
        original_hashes = {v['actual_original_map_sha256'] for v in snapshots if v['mutation_count'] > 0}
        scope['originals_recaptured'] = len(original_hashes) == 1
        unrelated = ['cpu.weight', 'pids.max', 'io.weight', 'memory.high', 'memory.swap.max']
        vectors = [v['actual_controls'] for v in snapshots]
        scope['unrelated_controls_constant'] = bool(vectors) and all(all(v[f] == vectors[0][f] for f in unrelated) for v in vectors)
        scope['declared_cpu_memory_phases'] = bool(snapshots)
        scope['declared_IO_phases'] = bool(snapshots)
        quota = str(int(decimal.Decimal(str(plan['budget']['cpu_cores'])) * 100000)) + ' 100000'
        for snapshot in snapshots:
            applied = snapshot['mutation_count'] > 0
            actual = snapshot['actual_controls']
            scope['declared_cpu_memory_phases'] &= (actual['cpu.max'].strip() == (quota if applied else '800000 100000') and
                actual['memory.max'].strip() == (str(plan['budget']['memory_max_bytes']) if applied else '21474836480'))
            lines = [v.split() for v in actual['io.max'].splitlines() if v.strip()]
            if applied:
                expected = {key: str(plan['budget'][kind]) for key, kind in
                            [('rbps', 'read_write_bps'), ('wbps', 'read_write_bps'),
                             ('riops', 'read_write_iops'), ('wiops', 'read_write_iops')]}
                scope['declared_IO_phases'] &= len(lines) == 1 and dict(v.split('=', 1) for v in lines[0][1:]) == expected
            else:
                scope['declared_IO_phases'] &= not lines
        scope['original_protocol_refused'] = any(v['name'] == role + '-unadvertised-old-protocol-installer-refuses-without-replacement' and v['passed'] for v in report.get('tests', []))
        for field in ['private_active_state_backup', 'private_state_backup']:
            value = item.get(field, {})
            scope[field] = value.get('bytes', 0) > 0 and len(value.get('sha256', '')) == 64 and value.get('raw_private_contents_not_published') is True
        independent = terminal.get('roles', {}).get(role, {})
        scope['rollback_binary_retained'] = (independent.get('installed_binary_sha256') == plan['programs']['previous']['binary_sha256'] and
            independent.get('saved_old_binary_sha256') == plan['programs']['previous']['binary_sha256'])
        scope['final_journal_empty_disabled'] = (independent.get('journal_after_final_disable', {}).get('mutation_count') == 0 and
            independent.get('journal_after_final_disable', {}).get('disabled_marker_present') is True)
        scope['leaf_cgroup_absent'] = independent.get('container_cgroup_absent') is True
        scope['independent_private_backups'] = True
        for field, filename in [('private_active_state_backup', 'active-state-before-disable.json'),
                                ('private_state_backup', 'state-before-migration.json')]:
            metadata = independent.get('private_backups', {}).get(filename, {})
            scope['independent_private_backups'] &= (metadata.get('mode') == '0o600' and metadata.get('raw_excluded') is True and
                metadata.get('sha256') == item.get(field, {}).get('sha256') and metadata.get('bytes', 0) > 0)
        intervals = item.get('maintenance_intervals', [])
        scope['operations_within_native600'] = False
        if native.get('started_utc') and intervals:
            started = datetime.datetime.fromisoformat(native['started_utc'].replace('Z', '+00:00')).timestamp()
            scope['operations_within_native600'] = len(intervals) >= 15 and all(started <= v['started_epoch'] <= v['ended_epoch'] < started + 600 for v in intervals)
        roles[role] = {'checks': scope, 'actual_seconds': native.get('elapsed_seconds'),
                       'SQL_errors': native.get('sql', {}).get('errors'), 'API_errors': native.get('api', {}).get('errors')}
    passed = all(checks.values()) and all(all(v['checks'].values()) for v in roles.values())
    return {'schema': 'crg-published-migration-independent-analysis-v1', 'phase': 'passed' if passed else 'not-accepted',
            'checks': checks, 'roles': roles, 'stable_release_accepted': False,
            'scope': 'published rc3/current controlled disable-restore migration only; original quiescent/two-prior-published-minor/percentage/long-term gates remain'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--output', type=Path)
    p.add_argument('--require-pass', action='store_true')
    args = p.parse_args()
    value = analyze(args.evidence)
    text = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(text)
    else:
        print(text, end='')
    return 1 if args.require_pass and value['phase'] != 'passed' else 0


if __name__ == '__main__':
    raise SystemExit(main())
