#!/usr/bin/env python3
"""Read-only source37/fresh1880 lineage gate. Capture is never acceptance.

No execute option, signals, Pod/resource changes, or filesystem writes.
The old aged executor remains unavailable for this new lineage.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve()
BINDING_SHA256 = '5602de6f0d920048247a1df38d8e66307364a22d0d5567bc5674a35ec6df057a'
binding_raw = HERE.with_name('binding.json').read_bytes()
if hashlib.sha256(binding_raw).hexdigest() != BINDING_SHA256:
    raise ValueError('FROZEN_SOURCE37_BINDING')
BINDING = json.loads(binding_raw)
TESTS = HERE.parents[1]
for name, key in [('vendor-aged-preflight.py', 'base_reader_sha256'),
                  ('soak-report-audit.py', 'auditor_sha256')]:
    if hashlib.sha256((TESTS/name).read_bytes()).hexdigest() != BINDING[key]:
        raise ValueError('FROZEN_ORIGINAL_READER_SOURCE')
spec = importlib.util.spec_from_file_location('source37_aged_base', TESTS/'vendor-aged-preflight.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
require, Rejected = base.require, base.Rejected
read_json, digest, directory = base.read_json, base.digest, base.directory
namespace, group, command = base.namespace, base.group, base.command
immutable_files, CONTROLS, DIRECTORIES = base.immutable_files, base.CONTROLS, base.DIRECTORIES


def contract(value):
    require(value == BINDING, 'FROZEN_SOURCE37_CONTRACT')
    require(len(value['uploaded_sha256']) == 19 and len(value['stages']) == 3
            and sum(v['seconds'] for v in value['stages']) == 777600,
            'ORIGINAL_DURATIONS_AND_INPUTS')
    for name in ['component_root', 'runner_root', 'postflight_root']:
        base.lab_root(value[name])
    require(len({value[k] for k in ['component_root', 'runner_root', 'postflight_root']}) == 3,
            'ROOT_OVERLAP')


def expected_checks():
    suffixes = ['real-path-original-startup-observe-without-resource-writes',
                'original-CCG-mount-stays-readonly', 'original-cache-independent-enforce',
                'observe-three-planned-controls-and-all-eight-originals-preserved',
                'daily-logs-report-v2-before-business-campaign',
                'one-exact-Agent-cache-and-initial-primary']
    return {f'candidate1-{r}-bw64-{s}' for r in ['dbs', 'hisdbs'] for s in suffixes} | {
        p+'-both-native-full-duration-and-all-cycles' for p in ['baseline', 'enforce', 'acceptance']
    } | {'same-container-and-guards-observe-to-enforce-exact-budget'}


def checks(report, terminal):
    values = report['tests']; names = [v['name'] for v in values]
    require(len(set(names)) == len(names) and set(names) <= expected_checks()
            and all(v.get('passed') is True for v in values), 'ORIGINAL_MAIN_CHECKS')
    if terminal:
        require(set(names) == expected_checks() and len(names) == 16, 'ALL16_MAIN_CHECKS')


def source_inputs():
    contract(BINDING); tools = Path(BINDING['runner_root'])
    for n, h in BINDING['uploaded_sha256'].items():
        require(digest(tools/n)['sha256'] == h, 'FROZEN19_SOURCE')
    for n, row in BINDING['sole_launch_bindings'].items():
        value, h = read_json(tools/n)
        require(h == row['sha256'] and all(value[k] == row[k] for k in ['pid', 'start_ticks', 'entry']),
                'EXACT_ORIGINAL_LAUNCH_HANDLE')
    plan, actual = read_json(tools/'plan.json')
    require(actual == BINDING['long_plan_sha256'] and plan['job_sha256'] == BINDING['long_job_sha256']
            and plan['stages'] == BINDING['stages'] and plan['campaign_pins'] == BINDING['campaign_pins']
            and plan['source_revision'] == BINDING['source_revision'], 'LONG_PLAN')
    launch, _ = read_json(tools/'launch.json')
    require(launch['entry'] == str(tools/'runner.py') and launch['single_launch_guard'] is True
            and launch['plan_sha256'] == actual and launch['job_sha256'] == plan['job_sha256']
            and launch['source_sha256'] == BINDING['uploaded_sha256'], 'SOLE_LAUNCH_BINDING')
    return plan, launch


def process_live(value):
    return base.proc(value['pid'], value['entry'], value['start_ticks'])['live']


def component():
    plan, launch = source_inputs(); tools = Path(BINDING['runner_root'])
    root = Path(BINDING['component_root']); outer, outer_digest = read_json(root/'report.json')
    require(outer['sources']['candidate1'] == {'revision': BINDING['source_revision'],
            'binary_sha256': BINDING['binary_sha256']} and outer['job_sha256'] == BINDING['long_job_sha256']
            and outer['plan_sha256'] == BINDING['long_plan_sha256'] and outer['version'] == 'v1.0.0'
            and outer['runtime_inherited'] is False and outer['stable_release_accepted'] is False
            and outer['namespace'] == BINDING['namespace'], 'OUTER_SOURCE_AND_SCOPE')
    require(outer['phase'] != 'failed' and not outer.get('cleanup_errors'), 'COMPONENT_FAILED')
    checks(outer, outer['phase'] == 'passed')
    receipt = read_json(tools/'exit.json')[0] if (tools/'exit.json').exists() else None
    worker, _ = read_json(tools/'worker.json')
    require(worker['entry'] == str(tools/'job.py'), 'WORKER_SOURCE')
    campaigns = {}; reports = {}; all_accepted = True
    for stage in BINDING['stages']:
        name = stage['phase']; path = root/('campaign-'+name)/'report.json'
        if not path.exists():
            all_accepted = False;continue
        campaign, h = read_json(path, 256*1024**2)
        phase_item = outer['phases'][name]
        require(phase_item['run_id'] == stage['run_id']
                and phase_item['requested_seconds'] == stage['seconds']
                and phase_item['source_run_id'] == stage.get('source_run_id')
                and phase_item['output'] == str(root/('campaign-'+name)), 'FRESH_PHASE_RUN_ID')
        audited = base.audit.audit(campaign, name, BINDING['campaign_pins'], stage.get('source_run_id'))
        require(audited['phase'] in ['passed', 'pending'], 'CAMPAIGN_AUDIT')
        campaigns[name] = campaign; reports[name] = {'sha256': h, 'audit': audited}
        if audited['phase'] != 'passed':all_accepted = False
        if outer['phase'] == 'passed':
            item = outer['phases'][name]
            require(item['native_accepted'] is True and item['exit'] == 0
                    and item['campaign_original_absent'] is True and item['report_sha256'] == h
                    and item['actual_cycles'] == stage['cycles'] == audited['accepted_engine_cycles'],
                    'ORIGINAL_PHASE_ACCEPTANCE')
    bridge = {'helper_sha256': plan['source_sha256'],
              'private_original_fixture_sha256': plan['private_fixture_sha256']}
    inputs = (bridge, launch, outer, campaigns.get('acceptance'))
    if outer['phase'] != 'passed' or receipt is None:
        require(receipt is None and process_live(launch) and process_live(worker), 'LIVE_ORIGINAL_HANDLES')
        return {'phase': 'pending', 'component_phase': outer['phase'], 'postflight_allowed': False,
                'capture_allowed': outer['phase'] == 'measuring-acceptance',
                'runner_identity_verified_live': True, 'reports': reports,
                'P10_complete': False, 'release_accepted': False}, inputs
    require(type(receipt['exit']) is int and receipt['exit'] == 0
            and receipt['job_sha256'] == BINDING['long_job_sha256']
            and receipt['plan_sha256'] == BINDING['long_plan_sha256']
            and not process_live(launch) and not process_live(worker), 'EXACT_TERMINAL_RECEIPT')
    require(all_accepted and set(campaigns) == {'baseline', 'enforce', 'acceptance'}, 'ALL_THREE_NATIVE_DURATIONS')
    require(outer['namespace_absent'] is True and outer['aged_fixture_retained'] is True
            and outer['postflight_required'] is True and len(outer['cleanup']) == 2,
            'OWNED_CLEANUP_AND_RETAINED_DATA')
    for role in ['dbs', 'hisdbs']:
        key = 'candidate1-'+role+'-bw64'; row = outer['roles'][key]; cleaned = outer['cleanup'][key]
        require(cleaned['leaf_absent'] and cleaned['parent_absent'] and cleaned['all_registered_absent']
                and not Path(row['fixture_identity']['group']).exists()
                and not Path(row['fixture_identity']['pod_parent']).exists(), 'OLD_GROUPS_NOT_ABSENT')
        require(all(not base.proc(x['pid'], '', x['start_ticks'])['live']
                    for x in cleaned['registered_processes']), 'OLD_REGISTERED_PROCESSES')
        t = row['enforce_transition']
        require(t['same_fixed_processes'] is True and t['before']['fixed_processes'] == t['after']['fixed_processes']
                and t['before']['controls'] == row['original_controls']
                and t['after']['controls'] == row['enforce_controls']
                and t['exact_journal'] == row['enforce_journal'], 'SAME_CONTAINER_EXACT_TRANSITION')
        end = None
        for name in ['baseline', 'enforce', 'acceptance']:
            native = campaigns[name]['roles'][role]['workload']
            stage = next(s for s in BINDING['stages'] if s['phase'] == name)
            require(native['run_id'] == stage['run_id'], 'EXACT_FRESH_NATIVE_RUN')
            require(native['primary_start_time_initial'] == native['primary_start_time_final'] == row['primary_start'],
                    'SAME_PRIMARY_ALL_STAGES')
            start = base.audit.timestamp(native['started_utc']); finished = base.audit.timestamp(native['measurement_finished_utc'])
            require(end is None or end <= start, 'ORIGINAL_STAGE_ORDER');end = finished
    return {'phase': 'component-accepted', 'component_report_sha256': outer_digest,
            'reports': reports, 'postflight_allowed': False, 'P10_complete': False,
            'release_accepted': False}, inputs


def capture_core(plan, plan_digest, state, inputs):
    require(state['phase'] == 'pending' and state.get('runner_identity_verified_live'), 'CAPTURE_REQUIRES_ACTIVE_COMPONENT')
    frozen, launch, outer, campaign = inputs
    require(campaign['phase'] == 'measuring', 'CAPTURE_REQUIRES_MEASUREMENT')
    meta = namespace(plan['namespace'])
    require(meta and meta['metadata']['uid'] == outer['namespace_uid']
            and meta['metadata']['labels'].get('managed-by') == 'crg-vendor-test', 'NAMESPACE_IDENTITY')
    seal = {'schema': 'crg-aged-lineage-seal-v1', 'plan_sha256': plan_digest,
            'source_revision': plan['source_revision'], 'binary_sha256': plan['binary_sha256'],
            'namespace_uid': outer['namespace_uid'], 'launch': launch,
            'capture_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'seal_is_not_acceptance': True, 'P10_complete': False, 'roles': {}}
    for role in plan['roles']:
        folder = path_clean(Path(plan['component_root'])/'fixture'/(role+'-business'))
        pod = json.loads(command(['kubectl', 'get', 'pod', '-n', plan['namespace'], role+'-business', '-o', 'json']))
        require(pod['metadata']['labels'].get('managed-by') == 'crg-vendor-test'
                and not any(pod['spec'].get(k) for k in ['hostPID', 'hostNetwork', 'hostIPC']), 'POD_OWNERSHIP')
        row = {'pod_uid': pod['metadata']['uid'], 'containers': {}, 'directories': {}, 'files': {}, 'log_prefixes': {}}
        statuses = pod['status']['containerStatuses']
        require({x['name'] for x in statuses} == {role, 'isolated-dcs'}
                and all(x['restartCount'] == 0 for x in statuses), 'CONTAINER_SET_OR_RESTART')
        main_group = None
        for item in statuses:
            require(item['containerID'].startswith('containerd://'), 'CONTAINER_RUNTIME')
            cid = item['containerID'].split('://', 1)[1]
            require(re.fullmatch(r'[0-9a-f]{64}', cid), 'CONTAINER_ID')
            pid = json.loads(command(['crictl', 'inspect', cid]))['info']['pid'];g = group(pid, cid)
            row['containers'][item['name']] = {'container_id': cid, 'cgroup': str(g), **directory(g)}
            if item['name'] == role:main_group = g
        controls = {name: (main_group/name).read_text().strip() for name in CONTROLS}
        require(controls == campaign['roles'][role]['fixed_controls'], 'FIXED_CONTROLS')
        guards = {'agent': [], 'cache': [], 'native': []}
        for value in (main_group/'cgroup.procs').read_text().splitlines():
            try:
                p = Path('/proc', value);argv = (p/'cmdline').read_bytes().split(b'\0')
                for kind, entry in [('agent', '/opt/crg/crg'), ('cache', '/opt/ccg/bin/containercacheguard')]:
                    if entry.encode() in argv and len(argv) > 1 and argv[1] == b'run':
                        guards[kind].append(hashlib.sha256((p/'exe').read_bytes()).hexdigest())
                entry = '/tmp/crg-soak-load-' + plan['run_id'] + '.py'
                if entry.encode() in argv:guards['native'].append(int(value))
            except (FileNotFoundError, ProcessLookupError):pass
        require(guards['agent'] == [plan['binary_sha256']] and guards['cache'] == [plan['cache_sha256']]
                and len(guards['native']) == 1, 'ONE_SOURCE_QUALIFIED_PROCESS_EACH')
        native, _ = read_json(folder/('postgresql/basebackup/crg-soak-'+plan['run_id']+'/load.json'))
        require(native['phase'] == 'running' and native['requested_duration_seconds'] == 604800, 'NATIVE_RUNNING')
        status, _ = read_json(folder/'resource-state/status.json');journal, journal_digest = read_json(folder/'resource-state/journal.json')
        require(status['state'] == 'managed' and journal['version'] == 1
                and status['plan']['environment']['identity'] == journal['identity']
                and {v['file'] for v in status['items']} == {'cpu.max', 'memory.high', 'io.max'}
                and all(v['state'] == 'applied' for v in status['items'])
                and stat.S_IMODE((folder/'resource-state/journal.json').stat().st_mode) == 0o600, 'AGED_RESOURCE_STATE')
        row.update(controls=controls, journal_identity=journal['identity'], journal_sha256=journal_digest,
                   native_started_utc=native['started_utc'], primary_start=native['primary_start_time_initial'])
        for name in DIRECTORIES:
            row['directories'][name] = directory(folder/name)
        for name in immutable_files(role):
            row['files'][name] = digest(folder/name)
        require(row['files']['crg/crg']['sha256'] == plan['binary_sha256']
                and row['files']['ccg/bin/containercacheguard']['sha256'] == plan['cache_sha256']
                and row['files']['crg/optional-agent.sh']['sha256'] == frozen['helper_sha256']['examples/optional-agent.sh']
                and row['files']['ccg/scripts/business-supervisor.sh']['sha256'] == frozen['private_original_fixture_sha256']['fixture/'+role+'/supervisor.sh'], 'AGED_PROGRAM_SOURCE')
        for log in sorted((folder/'log/crg').glob('crg-*.log')):
            require(re.fullmatch(r'crg-[0-9]{4}-[0-9]{2}-[0-9]{2}\.log', log.name), 'DAILY_LOG_NAME')
            row['log_prefixes'][log.name] = digest(log)
            require(row['log_prefixes'][log.name]['mode'] == 0o600, 'DAILY_LOG_MODE')
        require(bool(row['log_prefixes']), 'DAILY_LOG_MISSING')
        seal['roles'][role] = row
    require(seal['roles']['dbs']['directories']['postgresql'] != seal['roles']['hisdbs']['directories']['postgresql'], 'ROLE_DATA_SHARED')
    return seal



def capture(state, inputs):
    require(state['phase'] == 'pending' and state.get('capture_allowed') is True,
            'CAPTURE_ONLY_DURING_FRESH_SEVEN_DAY')
    for name in ['baseline', 'enforce']:
        require(state['reports'][name]['audit']['phase'] == 'passed'
                and inputs[2]['phases'][name]['native_accepted'] is True,
                'CAPTURE_REQUIRES_BOTH_ORIGINAL24H')
    # Original complete capture body preserves Pod/cgroup/source/process/native,
    # directory/file/log/journal identity checks. User changed managed memory to high.
    p = dict(BINDING, run_id=BINDING['seven_day_run_id'])
    value = capture_core(p, BINDING_SHA256, state, inputs)
    for role, row in value['roles'].items():
        original = inputs[2]['roles']['candidate1-'+role+'-bw64']
        require(row['controls'] == original['enforce_controls']
                and row['controls']['cpu.max'] == '720000 100000'
                and row['controls']['memory.high'] == '20001980416'
                and row['controls']['memory.max'] == '21474836480'
                and all(row['controls'][n] == original['original_controls'][n]
                    for n in ['memory.max', 'memory.swap.max', 'pids.max', 'cpu.weight', 'io.weight'])
                and re.fullmatch(r'[0-9]+:[0-9]+ rbps=67108864 wbps=67108864 riops=4096 wiops=4096', row['controls']['io.max']),
                'CAPTURE_EXACT_MANUAL_HIGH_AND_EXTERNAL_CONTROLS')
        native, _ = read_json(Path(BINDING['component_root'])/'fixture'/(role+'-business')/
            ('postgresql/basebackup/crg-soak-'+BINDING['seven_day_run_id']+'/load.json'))
        require(native['run_id'] == BINDING['seven_day_run_id'] and native['phase'] == 'running'
                and native['requested_duration_seconds'] == 604800, 'EXACT_SEVEN_DAY_NATIVE')
    value['fresh_three_phase_binding'] = {'binding_sha256': BINDING_SHA256,
        'long_plan_sha256': BINDING['long_plan_sha256'],
        'baseline_report_sha256': state['reports']['baseline']['sha256'],
        'enforce_report_sha256': state['reports']['enforce']['sha256']}
    value.update(phase='lineage-captured-not-accepted', postflight_allowed=False)
    return value


def readiness(state, inputs, seal, actual, expected):
    require(actual == expected and re.fullmatch('[0-9a-f]{64}', expected), 'SEAL_DIGEST')
    wanted = {'binding_sha256': BINDING_SHA256, 'long_plan_sha256': BINDING['long_plan_sha256'],
        'baseline_report_sha256': state['reports']['baseline']['sha256'],
        'enforce_report_sha256': state['reports']['enforce']['sha256']}
    require(seal.get('fresh_three_phase_binding') == wanted, 'FRESH_THREE_PHASE_SEAL')
    require(seal.get('launch') == inputs[1] and seal.get('plan_sha256') == BINDING_SHA256
            and seal.get('source_revision') == BINDING['source_revision']
            and seal.get('binary_sha256') == BINDING['binary_sha256'], 'SOURCE37_SEAL_BINDING')
    if state['phase'] == 'pending':return state
    require(state['phase'] == 'component-accepted', 'COMPONENT_NOT_ACCEPTED')
    # Original retained directory/file/journal/prefix/log7days and fresh-target checks.
    p = dict(BINDING, run_id=BINDING['seven_day_run_id'])
    result = base.verify_lineage(p, BINDING_SHA256, seal, inputs)
    result['component'] = state
    result['executor_available'] = False
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', action='store_true')
    p.add_argument('--seal', type=Path);p.add_argument('--seal-sha256')
    a = p.parse_args()
    if a.capture and a.seal or bool(a.seal) != bool(a.seal_sha256):p.error('choose capture or a complete seal pair')
    try:
        require(sys.platform == 'linux' and os.geteuid() == 0, 'LINUX_TEST_NODE_ROOT_REQUIRED')
        state, inputs = component()
        if a.capture:result = capture(state, inputs)
        elif a.seal:
            seal, actual = read_json(a.seal);result = readiness(state, inputs, seal, actual, a.seal_sha256)
        else:result = state
    except Rejected as error:
        result = {'phase': 'rejected', 'reason': str(error), 'postflight_allowed': False}
    except (OSError, TypeError, KeyError, AttributeError, ValueError, RecursionError, subprocess.SubprocessError):
        result = {'phase': 'rejected', 'reason': 'INPUT_SHAPE_READ_OR_INVENTORY', 'postflight_allowed': False}
    result.update(P10_complete=False, release_accepted=False)
    print(json.dumps(result, indent=2))
    return 2 if result['phase'] == 'pending' else 1 if result['phase'] == 'rejected' else 0


if __name__ == '__main__':
    sys.exit(main())
