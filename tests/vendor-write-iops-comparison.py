#!/usr/bin/env python3
"""Diagnostic DBS A/B/A on three complete, cold reflink clones of one baseline.

Only the write-IOPS trajectory differs between arms. This deliberately uses
manual mode and is NOT the original percentage/two-role release acceptance.
Default invocation only checks prerequisites. No product/controller code changes.
"""
import argparse
import ast
import copy
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import textwrap
import time
import types

sys.dont_write_bytecode = True
ROOT = Path('/var/tmp/crg-writeiops360-20261111')
TOOLS = Path('/var/tmp/crg-memory342-tools-20261111')
ORIGINAL = TOOLS/'vendor-business-memory-pressure-device-pgwait.py'
ORIGINAL_SHA = '71007a5560f26b48b916d1311bdb1509082ca3074da6ec18576d9812b5a4397a'
FAILURE_SHA = 'db851a15b3a95b88ed58a4af7981537782e62f5797fff126a40ca93e16c09a67'
SOURCE = Path('/var/tmp/crg-realpaths64-20261111/v10-dbs-bw64/dbs-business')
CONTROL_SHA = '383369440339bcc6a5a403530190b64ba5236e76719cc3140bc4197a63868218'
CONFIG_SHA = '08ed1a0de3a2b9f74e3af3608600e9716ecc80c36921148c2cb21d9c9de46550'
RUN = '20261111360'
ARMS = [('a1', 135), ('b', 4096), ('a2', 135)]


def sha(raw): return hashlib.sha256(raw).hexdigest()


def need(value, message):
    if not value: raise ValueError(message)


def load_original():
    need(sha(ORIGINAL.read_bytes()) == ORIGINAL_SHA, 'original source changed')
    spec = importlib.util.spec_from_file_location('writeiops_frozen_pressure342', ORIGINAL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manual(write_iops):
    return {'resource_mode': 'manual', 'limits': {'cpu_cores': 7.2,
        'memory_max': '20001980416B', 'io_read_bps': '64700080B',
        'io_write_bps': '37470104B', 'io_read_iops': 83, 'io_write_iops': write_iops}}


def policies(write_iops):
    second = manual(108)
    second['limits'].update(cpu_cores=6, memory_max='19335249920B',
                            io_read_bps='51760064B', io_write_bps='29976083B', io_read_iops=66, io_write_iops=108)
    return [manual(write_iops), second]


# Every edit to the frozen business method is explicit, counted and recorded.
# Scheduling, payload, pressure helper, generations, deadlines, cleanup and
# independent kernel/process/PG checks remain in the original method.
EDITS = [
    ("dict(POLICIES[1],io_percent=101)", "dict(POLICIES[1],limits=dict(POLICIES[1]['limits'],io_write_bps='bad'))", 1),
    ("rejected='io_percent'", "rejected='io_write_bps'", 1),
    ("d['plan']['percentages']==POLICIES[1]", "d['plan']['resource_mode']=='manual'", 1),
    ("policy=dict(POLICIES[0],memory_percent=20)",
     "policy=dict(POLICIES[0],limits=dict(POLICIES[0]['limits'],memory_max=str(target)+'B'))", 1),
    ("d['plan']['percentages']==policy", "d['plan']['resource_mode']=='manual'", 2),
    ("'manual-to-percent-during-engine'", "'manual-boot-to-measured-numeric-during-engine'", 1),
    ("'three-independent-percentages-during-native'", "'manual-second-policy-during-native'", 1),
    ("'percent-to-manual-three-resources'", "'manual-return-to-boot-controls'", 1),
    ("'pressure-test-return-to-percent30'", "'pressure-test-manual-memory30-equivalent'", 1),
    ("'released-memory20-returns-to-percent30'", "'released-manual-memory20-returns-to30-equivalent'", 1),
]


def derive(module, write_iops):
    original = ORIGINAL.read_text()
    cls = next(n for n in ast.parse(original).body if isinstance(n, ast.ClassDef) and n.name == 'Execution')
    node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_business_native_original')
    before = textwrap.dedent('\n'.join(original.splitlines()[node.lineno-1:node.end_lineno]))+'\n'
    after = before
    for old, new, count in EDITS:
        need(after.count(old) == count, 'unexpected substitution count: '+old)
        after = after.replace(old, new)
    expected = copy.deepcopy(module.EXPECTED)
    expected[0]['io.max'] = '253:0 rbps=64700080 wbps=37470104 riops=83 wiops='+str(write_iops)
    scope = dict(module.__dict__, POLICIES=policies(write_iops), EXPECTED=expected)
    exec(compile(after, str(Path(__file__))+'::manual-business', 'exec'), scope)
    return scope['_business_native_original'], {
        'original_method_sha256': sha(before.encode()), 'derived_method_sha256': sha(after.encode()),
        'substitutions': [{'old': old, 'new': new, 'count': count} for old, new, count in EDITS],
        'policies': policies(write_iops), 'numeric_readbacks': expected}


def manifest(root):
    """Metadata of the ENTIRE tree; regular-file content is copied by FICLONE.

    This is not advertised as a full-content SHA verification of every file.
    Critical config, program and PG control content are checked separately.
    """
    need(root.is_dir() and not root.is_symlink(), 'unsafe manifest root')
    rows = []
    for current, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs+files):
            path = Path(current)/name
            s = path.lstat()
            need(s.st_dev == root.stat().st_dev, 'nested device in baseline')
            need(stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode) or stat.S_ISLNK(s.st_mode), 'special baseline file')
            row = [str(path.relative_to(root)), s.st_mode, s.st_uid, s.st_gid, s.st_mtime_ns]
            if stat.S_ISREG(s.st_mode): row.append(s.st_size)
            if stat.S_ISLNK(s.st_mode): row.append(os.readlink(path))
            rows.append(row)
            need(len(rows) <= 50000, 'baseline manifest bound')
    rows.sort()
    raw = json.dumps(rows, separators=(',', ':')).encode()
    return rows, sha(raw)


def check_source(module):
    module.base.no_other_mounts([SOURCE])
    need(SOURCE.resolve() == SOURCE and not (SOURCE/'postgresql/pgdata').is_symlink(), 'source path changed')
    need(not (SOURCE/'postgresql/pgdata/postmaster.pid').exists(), 'source postmaster present')
    need(not (SOURCE/'crg-config/io-profile.json').exists(), 'source profile appeared')
    for name, digest in [('crg-config/config.json', CONFIG_SHA),
                         ('postgresql/pgdata/global/pg_control', CONTROL_SHA),
                         ('crg/crg', module.PINS['binary']),
                         ('ccg/bin/containercacheguard', module.PINS['cache'])]:
        need(sha((SOURCE/name).read_bytes()) == digest, 'source content changed: '+name)
    component = SOURCE/'postgresql/pgsql'
    result = subprocess.run([str(component/'bin/pg_controldata'), '-D', str(SOURCE/'postgresql/pgdata')],
        env=dict(os.environ, LD_LIBRARY_PATH=str(component/'lib'), LC_ALL='C'),
        capture_output=True, text=True, timeout=10)
    need(result.returncode == 0 and any(line.startswith('Database cluster state:') and
         line.split(':', 1)[1].strip() == 'shut down' for line in result.stdout.splitlines()), 'source not cleanly shut down')


def plan_value(module):
    source_plan = json.loads((TOOLS/'pressure-plan.json').read_bytes())
    return {'schema': 'crg-write-iops-comparison-plan-v1', 'work_root': str(ROOT),
        'executor_sha256': sha(Path(__file__).read_bytes()), 'original_executor_sha256': ORIGINAL_SHA,
        'original_plan_sha256': sha((TOOLS/'pressure-plan.json').read_bytes()),
        'prior_failed_report_sha256': FAILURE_SHA, 'source_folder': str(SOURCE),
        'source_pg_control_sha256': CONTROL_SHA, 'run_id_identical_on_separate_clones': RUN,
        'pins': module.PINS, 'criteria': module.base.CRITERIA,
        'scope': 'DBS-only manual-mode causal diagnostic; not original32/two-role/percentage acceptance',
        'arms': [{'name': name, 'write_iops': iops, 'derived_business': derive(module, iops)[1],
                  'namespace': 'crg-vendor-lab-writeiops360-'+name+'-20261111'} for name, iops in ARMS],
        'unchanged_source_roles': source_plan['roles'], 'release_accepted': False,
        'contrast': {'axis': 'policy-A write IOPS only', 'A1_A2_wiops': 135, 'B_wiops': 4096,
            'unchanged_policy_B_wiops': 108, 'unchanged_boot_wiops': 4096,
            'support_pattern': 'valid full600s A1 errors, B zero errors, A2 errors; otherwise inconclusive',
            'meaning': 'diagnostic contrast only; no automatic product budget increase or original gate waiver'},
        'comparison_limits': ['new-inode cold clones differ from R342 reused source',
            'sequential arms share backend with original unmodified long tests',
            'cache and IO state are not reset or claimed equal',
            'no inference from B alone; A must reproduce and repeat for support']}


def readiness(module):
    need(not os.path.lexists(ROOT), 'comparison root already exists')
    source_plan = json.loads((TOOLS/'pressure-plan.json').read_bytes())
    need(sha((TOOLS/'pressure-plan.json').read_bytes()) == 'c6581999c64e84ae9e833fd43117e71374159f388ffeea91aa905de5b2ac4098', 'original plan changed')
    for name, digest in json.loads((TOOLS/'gates.json').read_bytes())['files'].items():
        need(sha((TOOLS/name).read_bytes()) == digest, 'qualified input changed: '+name)
    module.device_pg_readiness(source_plan)
    module.diagnostic_readiness(source_plan)
    module.final_wait_readiness(source_plan)
    failed, digest = module.gate.read_json(Path('/var/tmp/crg-business-pressure342-20261111/report.json'))
    need(digest == FAILURE_SHA and failed['phase'] == 'failed' and failed['reason'] == 'NATIVE_COMPLETION_EXIT'
        and failed['namespace_absent'] and failed['original_config_bytes_and_profile_absence_restored'], 'R342 failure not preserved')
    for row in failed['roles'].values():
        need(all(not Path(boot['cgroup']).exists() for boot in row['boots']), 'R342 cgroup still exists')
    for name in ['pressure-launch.json', 'pressure-worker.json']:
        p = json.loads((TOOLS/name).read_bytes())
        need(not module.gate.proc(p['pid'], p['entry'], p['start_ticks'])['live'], 'R342 process still exists')
    for name, _ in ARMS:
        need(module.gate.namespace('crg-vendor-lab-writeiops360-'+name+'-20261111') is None, 'namespace already exists')
    check_source(module)
    need(shutil.disk_usage('/var/tmp').free >= 64*1024**3, 'clone disk reserve')
    available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                         if line.startswith('MemAvailable:')))*1024
    need(available >= module.base.CRITERIA['clone_host_available_bytes'], 'clone host memory reserve')
    q = subprocess.run(['xfs_info', '/'], capture_output=True, text=True, timeout=10)
    need(q.returncode == 0 and 'reflink=1' in q.stdout, 'reflink filesystem unavailable')
    return {'phase': 'ready', 'executed': False, 'release_accepted': False}


def save(value):
    path = ROOT/'comparison.next'
    with path.open('w') as out:
        os.chmod(path, 0o600)
        json.dump(value, out, indent=2)
        out.flush(); os.fsync(out.fileno())
    path.replace(ROOT/'comparison.json')


def clone_all(module, report):
    rows, digest = manifest(SOURCE)
    report['source_manifest'] = {'metadata_sha256': digest, 'entries': len(rows), 'content_verification':
        'cp --reflink=always exit0 + entire tree metadata + distinct regular-file inodes + critical content SHA; not full-content SHA'}
    save(report)
    for name, _ in ARMS:
        parent = ROOT/'clones'/name
        parent.mkdir(parents=True, mode=0o700)
        target = parent/'dbs-business'
        need(not os.path.lexists(target) and target.parent.resolve() == parent, 'unsafe clone target')
        check_source(module)
        result = subprocess.run(['cp', '--reflink=always', '--archive', '--one-file-system', '--',
                                 str(SOURCE), str(target)], capture_output=True, text=True, timeout=180)
        need(result.returncode == 0, 'reflink clone failed: '+result.stderr[:512])
        cloned_rows, cloned_digest = manifest(target)
        need(cloned_rows == rows and cloned_digest == digest, 'clone tree metadata mismatch')
        for row in rows:
            original, cloned = SOURCE/row[0], target/row[0]
            if stat.S_ISREG(row[1]): need(original.stat().st_ino != cloned.stat().st_ino, 'clone hardlinked to source')
        for filename in ['crg-config/config.json', 'crg/crg', 'ccg/bin/containercacheguard',
                         'postgresql/pgdata/global/pg_control']:
            need(sha((target/filename).read_bytes()) == sha((SOURCE/filename).read_bytes()), 'clone critical content mismatch')
        report['clones'][name] = {'folder': str(target), 'metadata_sha256': cloned_digest,
                                  'critical_content_sha_verified': True, 'distinct_regular_file_inodes': True}
        save(report)
    check_source(module)
    need(manifest(SOURCE)[0] == rows, 'source changed during freeze')
    report['baseline_frozen_before_any_arm'] = True
    save(report)


def execute_arm(module, item, plan_digest):
    name, iops = item['name'], item['write_iops']
    source_plan = json.loads((TOOLS/'pressure-plan.json').read_bytes())
    arm_plan = copy.deepcopy(source_plan)
    arm_plan.update(work_root=str(ROOT/'runs'/name), namespace=item['namespace'], run_id=RUN,
                    mode='write-iops-causal-diagnostic')
    folder = ROOT/'clones'/name/'dbs-business'
    arm_plan['roles']['dbs']['folder'] = str(folder)
    function, derivation = derive(module, iops)

    def adapt(original, role, cloned_folder, namespace, work):
        need(role == 'dbs' and cloned_folder == folder, 'unexpected diagnostic role')
        pod = copy.deepcopy(original)
        for volume in pod['spec']['volumes']:
            if 'hostPath' not in volume or volume['name'] in ['gate', 'aux']: continue
            path = Path(volume['hostPath']['path'])
            need(path.is_relative_to(SOURCE), 'foreign source mount')
            volume['hostPath']['path'] = str(folder/path.relative_to(SOURCE))
        return module.base.adapt_pod(pod, role, cloned_folder, namespace, work)

    base_proxy = types.SimpleNamespace(**dict(module.base.__dict__, adapt_pod=adapt))
    role_function = module.rebind(module.reload.Execution.role, base=base_proxy)

    class Execution(module.Execution):
        def __init__(self):
            super().__init__(arm_plan, plan_digest)
            self._business_native_original = types.MethodType(function, self)
            self.report.update(schema='crg-write-iops-diagnostic-arm-v1',
                scope='DBS-only diagnostic on complete cold baseline clone; not original32/two-role/percentage acceptance',
                executor_sha256=sha(Path(__file__).read_bytes()), arm=name, write_iops=iops,
                derived_business=derivation, historical_failure_resolved=False,
                original_release_acceptance_executed=False, release_accepted=False)

        def role(self, role):
            if role == 'hisdbs':
                self.report['HISDBS_not_run_in_DBS_causal_diagnostic'] = True
                self.save()
                return
            return role_function(self, role)

    return Execution().execute({'phase': 'ready-for-DBS-causal-diagnostic', 'release_accepted': False})



def record_native(module, report, name):
    path=ROOT/'clones'/name/'dbs-business'/'postgresql/basebackup'/('crg-soak-'+RUN+'0')/'load.json'
    if not path.exists():
        report['arms'][name]['native_terminal']={'available':False,'reason':'no-native-report'}
        save(report);return
    native,digest=module.gate.read_json(path)
    report['arms'][name]['native_terminal']={'available':True,'sha256':digest,'phase':native['phase'],
        'elapsed_seconds':native.get('elapsed_seconds'),'interrupted':native.get('interrupted',False),
        'SQL_errors':native.get('sql',{}).get('errors'),'API_errors':native.get('api',{}).get('errors')}
    save(report)


def interpret(report):
    records=[report['arms'][n].get('native_terminal',{}) for n in ['a1','b','a2']]
    valid=all(v.get('available') and v.get('phase') in ['passed','failed'] and not v.get('interrupted')
        and v.get('elapsed_seconds',0)>=600 and type(v.get('SQL_errors')) is int and type(v.get('API_errors')) is int for v in records)
    errors=[v['SQL_errors']+v['API_errors'] for v in records] if valid else None
    pattern=valid and errors[0]>0 and errors[1]==0 and errors[2]>0
    return {'all_three_actual600s':valid,'SQL_plus_API_errors':errors,'preplanned_A_fail_B_pass_A_fail_pattern_observed':bool(pattern),
        'conclusion':'preplanned-IOPS-pattern-observed-with-confounds' if pattern else 'inconclusive',
        'shared_backend_cache_and_order_confounds_remain':True,'original32_and_percentage_two_role_gate_accepted':False,
        'universal_IO_causality_or_product_defect_proven':False,'stable_release_accepted':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    try:
        need(sys.platform == 'linux' and os.geteuid() == 0, 'Linux root required')
        module = load_original()
        raw = args.plan.read_bytes()
        plan = json.loads(raw)
        need(sha(raw) == args.plan_sha256 and plan == plan_value(module), 'frozen comparison plan mismatch')
        ready = readiness(module)
        if not args.execute:
            print(json.dumps(ready)); return 0
        need(os.environ.get('CRG_WRITE_IOPS_COMPARISON') == 'authorized-disposable-test-node-only', 'explicit lab marker required')
        def interrupted(signum, frame): raise KeyboardInterrupt()
        signal.signal(signal.SIGTERM, interrupted)
        readiness(module)
        os.umask(0o077)
        ROOT.mkdir(mode=0o700)
        (ROOT/'runs').mkdir(mode=0o700)
        report = {'schema': 'crg-write-iops-comparison-v1', 'phase': 'cloning',
            'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'executor_sha256': sha(Path(__file__).read_bytes()), 'plan_sha256': sha(raw),
            'release_accepted': False, 'original_release_acceptance_executed': False,
            'clones': {}, 'arms': {}, 'prior_R342_failure_unchanged': True}
        save(report)
        try:
            clone_all(module, report)
            for item in plan['arms']:
                name = item['name']
                report['phase'] = 'running-'+name; save(report)
                result = execute_arm(module, item, sha(raw))
                path = ROOT/'runs'/name/'report.json'
                report['arms'][name] = {'phase': result['phase'], 'reason': result.get('reason'),
                    'report_path': str(path), 'report_sha256': sha(path.read_bytes()),
                    'checks': len(result['tests']), 'namespace_absent': result.get('namespace_absent'),
                    'clone_config_restored': result.get('original_config_bytes_and_profile_absence_restored')}
                save(report)
                need(result.get('namespace_absent') and result.get('original_config_bytes_and_profile_absence_restored'), 'arm cleanup incomplete; no next arm')
                need(all(not Path(boot['cgroup']).exists() for row in result['roles'].values() for boot in row['boots']), 'arm cgroup remains; no next arm')
                record_native(module,report,name)
                check_source(module)
                need(not str(result.get('reason','')).startswith(('RELOAD_DEADLINE_', 'NATIVE_PREPARATION_')), 'arm preparation or reload fixture failed; no next arm')
            report['interpretation'] = interpret(report)
            report['phase'] = 'diagnostic-completed'
        except BaseException as error:
            report.update(phase='failed', reason=str(error) if isinstance(error, (ValueError, module.Rejected)) else type(error).__name__)
        finally:
            report['ended_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            save(report)
        print(json.dumps({'phase': report['phase'], 'arms': report['arms'], 'release_accepted': False}))
        return 0 if report['phase'] == 'diagnostic-completed' else 1
    except BaseException as error:
        print(json.dumps({'phase': 'rejected', 'reason': str(error) if isinstance(error, ValueError) else type(error).__name__,
                          'executed': False, 'release_accepted': False}))
        return 1


if __name__ == '__main__': raise SystemExit(main())
