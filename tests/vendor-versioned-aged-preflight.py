#!/usr/bin/env python3
"""Read-only lineage gate for the exact versioned R78 seven-day lab component.

Reuses the immutable reviewed reader, without editing its R57 plan or seal.
This lab tool never creates files, workloads, locks or resource settings.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
BASE_SHA = 'b82c3a4e50969ac73c49322a7755eb4e40d277741e67270d7845b7e32b016439'
AUDITOR_SHA = '4feb3e7fad630e37245c837fc85e90dec4e10a086e5fe96a4bc299f4ad481eb8'
HERE = Path(__file__).resolve()
for filename, expected in [('vendor-aged-preflight.py', BASE_SHA), ('soak-report-audit.py', AUDITOR_SHA)]:
    if hashlib.sha256(HERE.with_name(filename).read_bytes()).hexdigest() != expected:
        raise ValueError('FROZEN_READER_SOURCE')
spec = importlib.util.spec_from_file_location('versioned_aged_base', HERE.with_name('vendor-aged-preflight.py'))
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
require, Rejected = base.require, base.Rejected

PINS = {
    'schema': 'crg-versioned-aged-postflight-plan-v1',
    'source_revision': 'd3706f3ea7ad279fea818e5ad1aa62ac5d3f8710',
    'binary_sha256': 'dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8',
    'embedded_version': 'v1.0.0',
    'cache_sha256': '757ba385a0ee4bdadc968b96b5c3e69fd44353060e5ab28520fd6f73a59902de',
    'base_preflight_sha256': BASE_SHA,
    'auditor_sha256': AUDITOR_SHA,
    'component_plan_sha256': 'e992ae7926fbd204af0ae6d51de349b304787bcd18687158452e3fde3cbd6dde',
    'component_root': '/var/tmp/crg-seven-day78-20261111',
    'runner_root': '/var/tmp/crg-r78-20261111',
    'namespace': 'crg-vendor-lab-acceptance78-20261111',
    'postflight_root': '/var/tmp/crg-aged-postflight80-20261111',
    'postflight_namespace': 'crg-vendor-lab-aged80-20261111',
    'run_id': '20261111078',
    'native_seconds': 604800,
    'component_checks': 11,
    'roles': ['dbs', 'hisdbs'],
}
CRITERIA = {
    'PG_API_managed_seconds': 300, 'cache_after_ready_seconds': 45,
    'new_native_smoke_seconds_each_role': 600, 'errors': 0,
    'request_max_seconds': 5, 'p95_bucket_upper_seconds': 1,
    'coverage_min': 0.98, 'payload_bytes_each_role': 67108864,
    'same_manual_budget_as_continuous': {
        'cpu_cores': 7.2, 'memory_max_bytes': 20001980416,
        'read_write_bps': 67108864, 'read_write_iops': 4096,
    },
}


def validate_contract(plan):
    require(isinstance(plan, dict), 'PLAN_SHAPE')
    for key, expected in PINS.items():
        require(plan.get(key) == expected and type(plan.get(key)) is type(expected), 'VERSIONED_BINDING_' + key)
    require(json.dumps(plan.get('postflight_criteria'), sort_keys=True) == json.dumps(CRITERIA, sort_keys=True)
            and plan.get('P10_complete') is False,
            'VERSIONED_POSTFLIGHT_CRITERIA')


def load_plan(path, expected):
    plan, actual = base.read_json(path)
    require(actual == expected and base.re.fullmatch(r'[0-9a-f]{64}', expected), 'PLAN_DIGEST')
    validate_contract(plan)
    for key in ['component_root', 'runner_root', 'postflight_root']:
        base.lab_root(plan[key])
    require(base.digest(HERE)['sha256'] == plan.get('preflight_sha256'), 'PREFLIGHT_SOURCE')
    require(base.digest(HERE.with_name('vendor-aged-preflight.py'))['sha256'] == BASE_SHA,
            'BASE_PREFLIGHT_SOURCE')
    require(base.digest(HERE.with_name('soak-report-audit.py'))['sha256'] == AUDITOR_SHA,
            'AUDITOR_SOURCE')
    return plan, actual


def component(plan):
    validate_contract(plan)
    state, inputs = base.component(plan)
    require(inputs[2]['build_info']['version'] == plan['embedded_version'], 'EMBEDDED_VERSION')
    return state, inputs


def capture(plan, plan_digest, state, inputs):
    seal = base.capture(plan, plan_digest, state, inputs)
    for role, row in seal['roles'].items():
        # Measuring campaign reports keep samples; the final workload field is
        # added only at termination. Bind the actual running native report now.
        native, _ = base.read_json(Path(plan['component_root'])/'fixture'/(role+'-business')/
                                   ('postgresql/basebackup/crg-soak-'+plan['run_id']+'/load.json'))
        require(native['phase'] == 'running' and native['run_id'] == plan['run_id']
                and native['requested_duration_seconds'] == plan['native_seconds']
                and row['native_started_utc'] == native['started_utc']
                and row['primary_start'] == native['primary_start_time_initial'], 'LIVE_NATIVE_LINEAGE')
    seal['phase'] = 'lineage-captured-not-accepted'
    return seal


def readiness(plan, plan_digest, seal, seal_digest, expected_seal, state, inputs):
    require(seal_digest == expected_seal, 'SEAL_DIGEST')
    require(seal.get('schema') == 'crg-aged-lineage-seal-v1'
            and seal.get('seal_is_not_acceptance') is True
            and seal.get('plan_sha256') == plan_digest and seal.get('launch') == inputs[1]
            and seal.get('source_revision') == plan['source_revision']
            and seal.get('binary_sha256') == plan['binary_sha256']
            and seal.get('namespace_uid') == inputs[2]['namespace_uid']
            and set(seal.get('roles', {})) == set(plan['roles']), 'SEAL_BINDING')
    if state['phase'] == 'pending':
        return state
    require(state['phase'] == 'component-accepted', 'COMPONENT_STATE')
    result = base.verify_lineage(plan, plan_digest, seal, inputs)
    result['component'] = state
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--seal', type=Path)
    parser.add_argument('--seal-sha256')
    args = parser.parse_args()
    if args.capture and (args.seal or args.seal_sha256) or not args.capture and not (args.seal and args.seal_sha256):
        parser.error('choose --capture or both --seal/--seal-sha256')
    try:
        require(sys.platform == 'linux' and os.geteuid() == 0, 'LINUX_TEST_NODE_ROOT_REQUIRED')
        plan, plan_digest = load_plan(args.plan, args.plan_sha256)
        state, inputs = component(plan)
        if args.capture:
            result = capture(plan, plan_digest, state, inputs)
        else:
            seal, actual = base.read_json(args.seal)
            result = readiness(plan, plan_digest, seal, actual, args.seal_sha256, state, inputs)
    except Rejected as error:
        result = {'phase': 'rejected', 'reason': str(error), 'postflight_allowed': False, 'P10_complete': False}
    except (OSError, TypeError, KeyError, AttributeError, ValueError, RecursionError, subprocess.SubprocessError):
        result = {'phase': 'rejected', 'reason': 'INPUT_SHAPE_READ_OR_INVENTORY', 'postflight_allowed': False, 'P10_complete': False}
    print(json.dumps(result, indent=2))
    return 2 if result['phase'] == 'pending' else 1 if result['phase'] == 'rejected' else 0


if __name__ == '__main__':
    sys.exit(main())
