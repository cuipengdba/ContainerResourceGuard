#!/usr/bin/env python3
"""Review the frozen IOPS contrast from local byte-exact terminal archives.

This is an offline evidence reader, not a workload or a controller. The native
error-only summary is insufficient without preparation, diagnostics and cleanup.
"""
import argparse
import copy
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def terminal_files(path):
    require(path.stat().st_size <= 8 * 1024 * 1024, 'ARCHIVE_BOUND')
    with gzip.GzipFile(fileobj=io.BytesIO(path.read_bytes())) as stream:
        raw = stream.read(64 * 1024 * 1024 + 1)
    require(len(raw) <= 64 * 1024 * 1024, 'EXPANSION_BOUND')
    bundle = json.loads(raw)
    require(bundle['schema'] == 'crg-write-iops-terminal-exact-evidence-v1', 'TERMINAL_SCHEMA')
    files = {name: row['exact_utf8'].encode('utf-8') for name, row in bundle['files'].items()}
    manifest = bundle['manifest']['files']
    require(set(files) == set(manifest) and 1 <= len(files) <= 96, 'MANIFEST_MEMBERS')
    for name, value in files.items():
        require(len(value) == manifest[name]['bytes'] and sha(value) == manifest[name]['sha256'], 'FILE_DIGEST:' + name)
    independent_raw = bundle['independent_terminal_exact_utf8'].encode('utf-8')
    require(sha(independent_raw) == bundle['independent_terminal_sha256'], 'INDEPENDENT_DIGEST')
    return files, json.loads(independent_raw)


def reviewer():
    path = Path(__file__).with_name('analyze-write-iops-arm.py')
    require(sha(path.read_bytes()) == '457fdf382bedadd6fcd628d1174dccb7d359acb9f7848821e869c6962b57bc38', 'ARM_REVIEWER_CHANGED')
    spec = importlib.util.spec_from_file_location('frozen_iops_arm_reader', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def analyze(terminal, arm_paths):
    files, independent = terminal_files(terminal)
    comparison = json.loads(files['comparison.json'])
    plan = json.loads(files['tools/comparison-plan-linux.json'])
    require(sha(files['comparison.json']) == independent['report_sha256'], 'COORDINATOR_BINDING')
    require(comparison['phase'] in ['diagnostic-completed', 'failed'], 'NONTERMINAL_COMPARISON')
    require(comparison['executor_sha256'] == sha(files['sources/vendor-write-iops-comparison.py'])
            == '30e92d64f2faede76efa115ebdedb0ec344567587b6c39c28bb1f8b7cc04de3d', 'EXECUTOR_BINDING')
    require(comparison['plan_sha256'] == sha(files['tools/comparison-plan-linux.json'])
            == '3ae2a159dc9d40eea442e70f15cffcc09f91357545ab4311625bd2275b65599a', 'PLAN_BINDING')
    require(comparison['baseline_frozen_before_any_arm'] and set(comparison['clones']) == {'a1', 'b', 'a2'}, 'COLD_BASELINES')
    require(independent['all_recorded_original_instances_independently_gone']
            and independent['all_three_namespaces_independently_absent']
            and independent['source_critical_bytes_and_clean_state_preserved']
            and independent['clone_program_configuration_and_profile_restored']
            and independent['prior_R342_report_unchanged'], 'INDEPENDENT_CLEANUP')
    require(all(v['original_instance_gone'] for v in independent['instances'].values()), 'ORIGINAL_INSTANCE_REMAINS')
    policies = [copy.deepcopy(item['derived_business']['policies']) for item in plan['arms']]
    require([p[0]['limits'].pop('io_write_iops') for p in policies] == [135, 4096, 135]
            and policies[0] == policies[1] == policies[2], 'SINGLE_VARIABLE_CONTRAST')
    gates = json.loads(files['tools/gates.json'])
    require(gates['phase'] == 'passed' and len(gates['observations']) == 12
            and gates['no_business_executed'] and gates['target_and_namespaces_absent'], 'PRECHECKS')
    a = reviewer()
    rows = {}
    for name in ['a1', 'b', 'a2']:
        if name not in comparison['arms']:
            rows[name] = {'available': False, 'eligible_for_contrast': False, 'reasons': ['arm-not-executed']}
            continue
        require(name in arm_paths, 'MISSING_ARM_ARCHIVE:' + name)
        values = a.read_files(arm_paths[name], True)
        report = json.loads(values['report.json'])
        require(sha(values['report.json']) == comparison['arms'][name]['report_sha256']
                == independent['arms'][name]['report_sha256']
                == sha(files['arms/' + name + '/report.json']), 'ARM_BINDING:' + name)
        review = a.analyze(values)['roles']['dbs']
        native = json.loads(values['dbs/native/load.json'])
        boot = report['roles']['dbs']['boots'][-1]
        engine = boot['engine']['roles']['dbs']
        summary = native['native_diagnostics']
        checks = {
            'full600_uninterrupted': native['elapsed_seconds'] >= 600 and not native['interrupted'] and native['threads_stopped'],
            'native_payload_and_primary': native['payload_integrity'] and native['primary_not_restarted'],
            'eleven_reload_intervals': len(boot['reload_intervals']) == 11,
            'all_recorded_main_checks_passed': bool(report['tests']) and all(row['passed'] for row in report['tests']),
            'ten_engine_content_checks': len(engine['checks']) == 10 and all(row['passed'] for row in engine['checks']),
            'engine_temporary_content_cleaned': engine['temporary_servers_stopped_and_copies_removed']
                and engine['own_fixture_schema_restore_database_snapshot_removed'],
            'native_diagnostics_complete': summary['diagnostic_complete'] and summary['probe_thread_stopped']
                and all(summary[k] == 0 for k in ['dropped_requests', 'dropped_pg_samples', 'pg_errors', 'pg_wait_errors',
                    'pg_truncated_samples', 'recorder_internal_errors', 'business_signals_cancellations_or_control_writes']),
            'native_interval_envelopes': boot['native_request_pg']['engine_and_reload_envelopes_covered'],
            'thread_interval_envelopes': boot['thread_observer']['engine_and_reload_interval_envelopes_covered'],
            'device_interval_envelopes': boot['device_observer']['engine_and_reload_interval_envelopes_covered'],
            'device_sampling_gap': boot['device_observer']['maximum_sample_gap_seconds'] is not None
                and boot['device_observer']['maximum_sample_gap_seconds'] <= 3,
            'diagnostic_cleanup_no_errors': not boot.get('diagnostic_cleanup_errors')
                and not boot['device_observer'].get('integration_errors'),
            'device_no_KILL': boot['device_observer']['owned_observer_KILL_count'] == 0,
            'recorded_cleanup': report['namespace_absent'] and report['original_config_bytes_and_profile_absence_restored'],
        }
        if 'native_final_flush' in boot:
            checks['native_no_termination'] = boot['native_final_flush']['signals_sent'] == 0 and not boot['native_final_flush']['forced_kill']
        rows[name] = {'available': True, 'phase': report['phase'], 'reason': report.get('reason'),
            'native_phase': native['phase'], 'native_elapsed_seconds': native['elapsed_seconds'],
            'SQL_errors': native['sql']['errors'], 'API_errors': native['api']['errors'],
            'main_checks': len(report['tests']), 'engine_content_checks': len(engine['checks']), 'reload_intervals': len(boot['reload_intervals']),
            'eligibility_checks': checks, 'eligible_for_contrast': all(checks.values()),
            'reasons': [k for k, v in checks.items() if not v],
            'D_observations': review['D_observations'], 'D_descriptor_counts': review['D_descriptor_counts'],
            'strict_D_observations_per_error': [len(e['strict_request_D_observations']) for e in review['error_windows']],
            'PG_kernel_stack_unknown': review['PG_kernel_stack_unknown'], 'thread_samples': review['thread_samples'],
            'device_samples': review['device_samples'], 'PG_samples': review['PG_samples'],
            'maximum_thread_sample_gap_seconds': boot['thread_observer']['maximum_sample_gap_seconds'],
            'maximum_device_sample_gap_seconds': boot['device_observer']['maximum_sample_gap_seconds'],
            'thread_truncated_samples': boot['thread_observer']['truncated_samples'],
            'arm_archive_sha256': sha(arm_paths[name].read_bytes()), 'exact_report_sha256': sha(values['report.json'])}
    eligible = comparison['phase'] == 'diagnostic-completed' and all(row['eligible_for_contrast'] for row in rows.values())
    errors = [rows[n]['SQL_errors'] + rows[n]['API_errors'] for n in ['a1', 'b', 'a2']] if eligible else None
    pattern = bool(eligible and errors[0] > 0 and errors[1] == 0 and errors[2] > 0 and rows['b']['native_phase'] == 'passed')
    return {'schema': 'crg-write-iops-independent-offline-review-v1', 'arms': rows,
        'all_three_structurally_eligible': eligible, 'SQL_plus_API_errors': errors,
        'preplanned_A_fail_B_pass_A_fail_pattern_observed': pattern,
        'conclusion': 'preplanned-IOPS-pattern-observed-with-confounds' if pattern else 'inconclusive',
        'coordinator_error_only_interpretation': comparison.get('interpretation'),
        'terminal_archive_sha256': sha(terminal.read_bytes()), 'independent_original_instances_gone': len(independent['instances']),
        'limits': plan['comparison_limits'], 'shared_backend_cache_and_order_confounds_remain': True,
        'observer900s_full_duration_claimed': False, 'IO_causality_or_product_defect_proven': False,
        'original32_two_role_percentage_acceptance_waived': False, 'stable_release_accepted': False, 'P10_complete': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--terminal', type=Path, required=True)
    for name in ['a1', 'b', 'a2']:
        p.add_argument('--' + name, type=Path)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    result = analyze(args.terminal, {n: getattr(args, n) for n in ['a1', 'b', 'a2'] if getattr(args, n) is not None})
    raw = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(raw)
        print(json.dumps({'output': str(args.output), 'eligible': result['all_three_structurally_eligible'], 'conclusion': result['conclusion']}))
    else:
        print(raw, end='')


if __name__ == '__main__':
    main()
