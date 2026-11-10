#!/usr/bin/env python3
"""Read-only capture and prerequisite checks for the frozen seven-day lab run.

This is a test tool. It never starts/stops workloads or writes resources/files.
Capture stdout privately; it contains lab identities but no configuration data.
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

spec = importlib.util.spec_from_file_location('soak_audit', Path(__file__).with_name('soak-report-audit.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
require, Rejected = audit.require, audit.Rejected
CONTROLS = ['cpu.max', 'memory.max', 'io.max', 'pids.max', 'cpu.weight',
            'io.weight', 'memory.high', 'memory.swap.max']
DIRECTORIES = ['postgresql', 'resource-state', 'cache-state', 'crg-config', 'log', 'ccg', 'crg']


def immutable_files(role):
    return ['crg-config/config.json', 'crg/crg', 'crg/optional-agent.sh', 'ccg/bin/containercacheguard',
            'ccg/scripts/business-supervisor.sh', 'ccg/config/'+role+'.json', 'postgres.yml', 'pod.json']


def path_clean(path):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts, 'ABSOLUTE_PATH')
    for parent in [path, *path.parents]:
        require(not parent.is_symlink(), 'SYMLINK_PATH')
    return path


def lab_root(value):
    p = path_clean(value)
    require(p.parent == Path('/var/tmp') and re.fullmatch(r'crg-[a-z0-9-]+', p.name), 'LAB_ROOT')
    return p


def read_json(path, maximum=8 * 1024**2):
    path = path_clean(path);info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= maximum, 'BOUNDED_JSON')
    return audit.load_report(path)


def digest(path, length=None):
    path = path_clean(path);info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'REGULAR_FILE')
    size = info.st_size if length is None else length
    require(type(size) is int and 0 <= size <= 1_000_000_000 and info.st_size >= size, 'FILE_SIZE')
    h = hashlib.sha256();remaining = size
    with path.open('rb') as stream:
        while remaining:
            chunk = stream.read(min(65536, remaining));require(bool(chunk), 'SHORT_FILE')
            h.update(chunk);remaining -= len(chunk)
        after = os.fstat(stream.fileno())
    require((info.st_dev, info.st_ino) == (after.st_dev, after.st_ino)
            and after.st_size >= size, 'FILE_CHANGED')
    if length is None:
        require((info.st_size, info.st_mtime_ns) == (after.st_size, after.st_mtime_ns), 'FILE_CHANGED')
    return {'sha256': h.hexdigest(), 'size': size, 'device': info.st_dev,
            'inode': info.st_ino, 'mode': stat.S_IMODE(info.st_mode)}


def directory(path):
    p = path_clean(path);s = p.stat();require(stat.S_ISDIR(s.st_mode), 'DIRECTORY')
    return {'device': s.st_dev, 'inode': s.st_ino}


def proc(pid, entry, start=None):
    require(type(pid) is int and pid > 1, 'PROCESS_PID')
    try:
        p = Path('/proc', str(pid));text = (p/'stat').read_text()
        fields = text[text.rfind(')') + 2:].split();ticks = int(fields[19])
        exact = entry.encode() in (p/'cmdline').read_bytes().split(b'\0')
        return {'live': fields[0] != 'Z' and exact and (start is None or ticks == start),
                'start_ticks': ticks}
    except (FileNotFoundError, ProcessLookupError):
        return {'live': False}


def command(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    require(result.returncode == 0, 'READ_ONLY_INVENTORY')
    return result.stdout


def namespace(name):
    value = command(['kubectl', 'get', 'namespace', name, '--ignore-not-found', '-o', 'json'])
    return json.loads(value) if value.strip() else None


def load_plan(path, expected):
    plan, actual = read_json(path)
    require(actual == expected and re.fullmatch(r'[0-9a-f]{64}', expected), 'PLAN_DIGEST')
    require(plan.get('schema') == 'crg-aged-postflight-plan-v1', 'PLAN_SCHEMA')
    require(plan.get('native_seconds') == 604800 and plan.get('component_checks') == 11
            and plan.get('roles') == ['dbs', 'hisdbs'] and plan.get('run_id') == '20261111057', 'PLAN_CRITERIA')
    for name in ['component_root', 'runner_root', 'postflight_root']:
        lab_root(plan[name])
    require(len({plan[n] for n in ['component_root', 'runner_root', 'postflight_root']}) == 3, 'ROOT_OVERLAP')
    for name in ['namespace', 'postflight_namespace']:
        require(re.fullmatch(r'crg-vendor-lab-[a-z0-9-]+', plan[name]), 'NAMESPACE_NAME')
    require(plan['namespace'] != plan['postflight_namespace'], 'NAMESPACE_OVERLAP')
    require(digest(Path(__file__))['sha256'] == plan['preflight_sha256'], 'PREFLIGHT_SOURCE')
    require(digest(Path(__file__).with_name('soak-report-audit.py'))['sha256'] == plan['auditor_sha256'], 'AUDITOR_SOURCE')
    return plan, actual


def component(plan):
    root, runner = Path(plan['component_root']), Path(plan['runner_root'])
    frozen, frozen_digest = read_json(runner/'acceptance-plan.json')
    require(frozen_digest == plan['component_plan_sha256'], 'COMPONENT_PLAN')
    require(frozen['source_revision'] == plan['source_revision']
            and frozen['binary_sha256'] == plan['binary_sha256'], 'COMPONENT_SOURCE')
    for filename, key in [('acceptance-job.py', 'job_sha256'), ('acceptance-runner.py', 'runner_sha256'),
                          ('campaign-wrapper.py', 'campaign_wrapper_sha256')]:
        require(digest(runner/filename)['sha256'] == frozen[key], 'RUNTIME_TOOL_SOURCE')
    launch, launch_digest = read_json(runner/'launch.json')
    require(launch['entry'] == str(runner/'acceptance-runner.py')
            and launch['job_sha256'] == frozen['job_sha256']
            and launch['source_revision'] == plan['source_revision']
            and launch['binary_sha256'] == plan['binary_sha256'], 'LAUNCH_SOURCE')
    require(type(launch['start_ticks']) is int and launch['start_ticks'] > 0, 'LAUNCH_TICKS')
    handle = proc(launch['pid'], launch['entry'], launch['start_ticks'])
    outer, outer_digest = read_json(root/'report.json')
    require(outer['sources']['v10'] == {'revision': plan['source_revision'], 'binary_sha256': plan['binary_sha256']}
            and outer['job_sha256'] == frozen['job_sha256'] and outer['requested_seconds'] == 604800
            and outer['continuous_component_only'] is True and outer['P10_complete'] is False, 'OUTER_SOURCE_OR_SCOPE')
    receipt_path = runner/'acceptance.exit.json'
    receipt = read_json(receipt_path)[0] if receipt_path.exists() else None
    require(outer['phase'] != 'failed' and (receipt is None or receipt.get('exit') == 0), 'COMPONENT_FAILED')
    pins = {'agent_sha256': plan['binary_sha256'], 'cache_sha256': plan['cache_sha256'],
            'worker_sha256': frozen['helper_sha256']['tests/vendor-soak-load.py'],
            'campaign_script_sha256': frozen['helper_sha256']['tests/vendor-soak-campaign.py'],
            'engine_script_sha256': frozen['helper_sha256']['tests/vendor-engine-smoke.py']}
    campaign, campaign_digest = read_json(root/'campaign-acceptance/report.json', 256 * 1024**2)
    result = audit.audit(campaign, 'acceptance', pins)
    if outer['phase'] != 'passed' or receipt is None:
        require(handle['live'] and receipt is None, 'RUNNER_NOT_LIVE_OR_UNVERIFIED_TERMINAL')
        return {'phase': 'pending', 'runner_identity_verified_live': True,
                'campaign_phase': campaign['phase'], 'postflight_allowed': False,
                'P10_complete': False}, (frozen, launch, outer, campaign)
    require(not handle['live'] and result['phase'] == 'passed', 'RUNTIME_NOT_TERMINAL')
    require(type(receipt['exit']) is int and receipt['exit'] == 0
            and receipt['job_sha256'] == frozen['job_sha256'], 'EXIT_RECEIPT')
    tests = outer.get('tests', [])
    require(len(tests) == 11 and len({x['name'] for x in tests}) == 11
            and all(x.get('passed') is True for x in tests), 'COMPONENT_CHECKS')
    require(outer.get('namespace_absent') is True and outer.get('aged_fixture_retained') is True
            and outer.get('postflight_and_final_release_audit_required') is True, 'COMPONENT_CLEANUP')
    require(not receipt.get('cleanup_forced') and not outer.get('cleanup_forced'), 'FORCED_CLEANUP')
    return {'phase': 'component-accepted', 'runner_identity_verified_gone': True,
            'component_report_sha256': outer_digest, 'campaign_report_sha256': campaign_digest,
            'launch_receipt_sha256': launch_digest, 'P10_complete': False}, (frozen, launch, outer, campaign)


def group(pid, cid):
    membership = Path('/proc', str(pid), 'cgroup').read_text()
    lines = [line.split('::', 1)[1] for line in membership.splitlines() if line.startswith('0::')]
    require(len(lines) == 1, 'PURE_V2_MEMBERSHIP')
    path = path_clean(Path('/sys/fs/cgroup')/lines[0].lstrip('/'))
    require(path != Path('/sys/fs/cgroup') and path.is_relative_to('/sys/fs/cgroup')
            and path.name == 'cri-containerd-' + cid + '.scope', 'SELF_CGROUP_LEAF')
    return path


def capture(plan, plan_digest, state, inputs):
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
                and {v['file'] for v in status['items']} == {'cpu.max', 'memory.max', 'io.max'}
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


def verify_lineage(plan, plan_digest, seal, inputs):
    frozen, launch, outer, campaign = inputs
    require(seal.get('schema') == 'crg-aged-lineage-seal-v1' and seal.get('seal_is_not_acceptance') is True
            and seal.get('plan_sha256') == plan_digest and seal.get('namespace_uid') == outer['namespace_uid']
            and seal.get('launch') == launch and seal.get('source_revision') == plan['source_revision']
            and seal.get('binary_sha256') == plan['binary_sha256']
            and set(seal.get('roles', {})) == {'dbs', 'hisdbs'}, 'SEAL_BINDING')
    require(namespace(plan['namespace']) is None, 'OLD_NAMESPACE_STILL_PRESENT')
    require(namespace(plan['postflight_namespace']) is None
            and not Path(plan['postflight_root']).exists(), 'POSTFLIGHT_TARGET_NOT_FRESH')
    for role, row in seal['roles'].items():
        folder = Path(plan['component_root'])/'fixture'/(role+'-business')
        require(set(row['directories']) == set(DIRECTORIES)
                and set(row['files']) == set(immutable_files(role))
                and set(row['containers']) == {role, 'isolated-dcs'}, 'SEAL_MEMBER_SET')
        require(row['native_started_utc'] == campaign['roles'][role]['workload']['started_utc']
                and row['primary_start'] == campaign['roles'][role]['workload']['primary_start_time_initial'], 'NATIVE_LINEAGE')
        for old in row['containers'].values():
            p = path_clean(old['cgroup'])
            require(re.fullmatch(r'[0-9a-f]{64}', old['container_id'])
                    and p.is_relative_to('/sys/fs/cgroup') and p.name == 'cri-containerd-'+old['container_id']+'.scope'
                    and not p.exists(), 'OLD_CONTAINER_CGROUP_STILL_PRESENT')
        for name, original in row['directories'].items():
            require(directory(folder/name) == original, 'AGED_DIRECTORY_REPLACED')
        for name, original in row['files'].items():
            require(digest(folder/name) == original, 'AGED_INPUT_CHANGED')
        journal, value = read_json(folder/'resource-state/journal.json')
        require(value == row['journal_sha256'] and journal['identity'] == row['journal_identity']
                and stat.S_IMODE((folder/'resource-state/journal.json').stat().st_mode) == 0o600, 'AGED_JOURNAL_CHANGED')
        for name, original in row['log_prefixes'].items():
            require(re.fullmatch(r'crg-[0-9]{4}-[0-9]{2}-[0-9]{2}\.log', name), 'SEALED_LOG_NAME')
            current = digest(folder/'log/crg'/name, original['size'])
            require(current == original, 'AGED_LOG_PREFIX_CHANGED')
        logs = list((folder/'log/crg').glob('crg-*.log'))
        require(len(logs) >= 7 and sum(p.stat().st_size for p in logs) <= 1_000_000_000
                and all(stat.S_IMODE(p.stat().st_mode) == 0o600 and not p.is_symlink() for p in logs), 'AGED_DAILY_LOGS')
    return {'phase': 'ready-for-postflight', 'postflight_allowed': True,
            'postflight_executed': False, 'P10_complete': False, 'release_accepted': False}


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
            result['phase'] = 'lineage-captured-not-accepted'
        else:
            seal, actual = read_json(args.seal)
            require(actual == args.seal_sha256, 'SEAL_DIGEST')
            if state['phase'] == 'pending':
                require(seal.get('plan_sha256') == plan_digest and seal.get('launch') == inputs[1], 'SEAL_BINDING')
                result = state
            else:
                result = verify_lineage(plan, plan_digest, seal, inputs)
                result['component'] = state
    except Rejected as error:
        result = {'phase': 'rejected', 'reason': str(error), 'postflight_allowed': False, 'P10_complete': False}
    except (OSError, TypeError, KeyError, AttributeError, ValueError, RecursionError, subprocess.SubprocessError):
        result = {'phase': 'rejected', 'reason': 'INPUT_SHAPE_READ_OR_INVENTORY', 'postflight_allowed': False, 'P10_complete': False}
    print(json.dumps(result, indent=2))
    return 2 if result['phase'] == 'pending' else 1 if result['phase'] == 'rejected' else 0


if __name__ == '__main__':
    sys.exit(main())
