#!/usr/bin/env python3
"""Read-only real seven-day capture adapter, preserving the frozen reader bytes.

Repairs two pre-existing capture-only plumbing omissions: role list and
path_clean binding. No resource, Pod, process or filesystem mutations.
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
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
READER_SHA='f2e167f3d8996fa2d716826a39d6520a8ef125fc286770f469bcd5c086c541e2'
if hashlib.sha256((HERE/'lineage.py').read_bytes()).hexdigest()!=READER_SHA:raise ValueError('FROZEN_READER_SOURCE')
spec=importlib.util.spec_from_file_location('source37_capture_reader',HERE/'lineage.py')
g=importlib.util.module_from_spec(spec);sys.modules[spec.name]=g;spec.loader.exec_module(g)
BINDING=g.BINDING;BINDING_SHA256=g.BINDING_SHA256
require,Rejected=g.require,g.Rejected
read_json,digest,directory=g.read_json,g.digest,g.directory
namespace,group,command=g.namespace,g.group,g.command
immutable_files,CONTROLS,DIRECTORIES=g.immutable_files,g.CONTROLS,g.DIRECTORIES
path_clean=g.base.path_clean


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


def capture_exact(state, inputs):
    require(state['phase'] == 'pending' and state.get('capture_allowed') is True,
            'CAPTURE_ONLY_DURING_FRESH_SEVEN_DAY')
    for name in ['baseline', 'enforce']:
        require(state['reports'][name]['audit']['phase'] == 'passed'
                and inputs[2]['phases'][name]['native_accepted'] is True,
                'CAPTURE_REQUIRES_BOTH_ORIGINAL24H')
    # Original complete capture body preserves Pod/cgroup/source/process/native,
    # directory/file/log/journal identity checks. User changed managed memory to high.
    p = dict(BINDING, run_id=BINDING['seven_day_run_id'], roles=['dbs', 'hisdbs'])
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


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',action='store_true');a=parser.parse_args(argv)
    try:
        require(sys.platform=='linux' and os.geteuid()==0,'LINUX_TEST_NODE_ROOT_REQUIRED')
        state,inputs=g.component()
        result=capture_exact(state,inputs) if a.capture else state
    except Rejected as error:
        result={'phase':'rejected','reason':str(error),'postflight_allowed':False}
    except (OSError,TypeError,KeyError,AttributeError,ValueError,RecursionError,subprocess.SubprocessError):
        result={'phase':'rejected','reason':'INPUT_SHAPE_READ_OR_INVENTORY','postflight_allowed':False}
    result.update(P10_complete=False,release_accepted=False);print(json.dumps(result,indent=2))
    return 2 if result['phase']=='pending' else 1 if result['phase']=='rejected' else 0


if __name__=='__main__':sys.exit(main())
