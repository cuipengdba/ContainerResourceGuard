#!/usr/bin/env python3
"""Linux qualification using only a freshly created sleep process, never business."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import select
import signal
import stat
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).parent
SOURCE = HERE/'vendor-thread-wait-observer.py'
spec = importlib.util.spec_from_file_location('thread_observer_checks_target', SOURCE)
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(root):
    checks = []
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    initial = observer.stat_fields(Path('/proc', str(child.pid), 'stat').read_text())
    membership = observer.pure_v2_path(Path('/proc', str(child.pid), 'cgroup').read_text())
    group = Path('/sys/fs/cgroup')/membership.lstrip('/')
    controls = ('cpu.max', 'memory.max', 'io.max', 'pids.max', 'cpu.weight',
                'io.weight', 'memory.high', 'memory.swap.max')
    def actual_controls():
        return {name: (group/name).read_text() if (group/name).exists() else None for name in controls}
    before = actual_controls()
    template = {'schema': observer.SCHEMA, 'observer_sha256': digest(SOURCE), 'label': 'selftest',
                'pid': child.pid, 'start_ticks': initial['start_ticks'],
                'executable_sha256': digest(Path('/proc', str(child.pid), 'exe')),
                'cgroup': str(group), 'duration_seconds': 2, 'output': str(root/'normal.json')}
    env = os.environ.copy()
    env.pop('CRG_THREAD_OBSERVER', None)
    active = dict(env, CRG_THREAD_OBSERVER='authorized-disposable-loopback-only')
    def plan(name, changes=None):
        value = dict(template, output=str(root/(name+'.json')), **(changes or {})) if not changes or 'output' not in changes else dict(template, **changes)
        path = root/(name+'-plan.json')
        path.write_text(json.dumps(value)+'\n')
        path.chmod(0o600)
        return path, value
    def command(path, sha=None):
        return [sys.executable, str(SOURCE), '--plan', str(path), '--plan-sha256', sha or digest(path)]
    def invoke(name, changes=None, execute=False, marker=True, sha=None):
        path, value = plan(name, changes)
        p = subprocess.run(command(path, sha) + (['--execute'] if execute else []), env=active if marker else env,
                           capture_output=True, text=True, timeout=12)
        return p, json.loads(p.stdout.splitlines()[-1]), value
    def record(name, passed):
        assert passed, name
        checks.append({'case': name, 'passed': True})
        progress = root/'checks-progress.json'
        progress.write_text(json.dumps({'phase':'running','checks':checks},indent=2)+'\n')
        progress.chmod(0o600)
    def rejected(name, changes=None, execute=False, marker=True, sha=None, reason=None):
        p, result, value = invoke(name, changes, execute, marker, sha)
        record(name, p.returncode==1 and p.stderr=='' and result['phase']=='rejected' and not result['executed']
               and not os.path.lexists(value['output']) and (reason is None or result['reason']==reason))
    def live_target():
        return child.poll() is None and observer.stat_fields(Path('/proc', str(child.pid), 'stat').read_text())['start_ticks']==initial['start_ticks']
    try:
        fields = ['0']*50
        for index, value in {0:'S', 7:'11', 9:'12', 11:'13', 12:'14', 17:'2', 19:'123', 39:'42'}.items():
            fields[index] = value
        parsed = observer.stat_fields('99 (name with ) parentheses) '+' '.join(fields))
        record('proc-stat-final-parenthesis-fields', parsed=={'pid':99,'state':'S','minor_faults':11,'major_faults':12,'user_ticks':13,'system_ticks':14,'threads':2,'start_ticks':123,'block_io_ticks':42})
        for text in ['1:memory:/x\n', '0::/x\n1:cpu:/x\n', '0::/../../x\n']:
            try:
                observer.pure_v2_path(text)
            except observer.Rejected:
                continue
            raise AssertionError('v1-hybrid-or-parent-membership-accepted')
        record('v1-hybrid-parent-membership-rejected', True)
        p, result, value = invoke('default-read-only')
        record('default-read-only-no-output', p.returncode==0 and p.stderr=='' and result=={'phase':'ready','executed':False,'output_created':False} and not Path(value['output']).exists())
        rejected('missing-marker', execute=True, marker=False, reason='EXPLICIT_LAB_MARKER')
        rejected('wrong-plan-digest', sha='0'*64, reason='PLAN_DIGEST')
        rejected('wrong-observer-source', {'observer_sha256':'0'*64}, reason='OBSERVER_SOURCE')
        rejected('wrong-process-start', {'start_ticks':initial['start_ticks']+1}, reason='PROCESS_INSTANCE')
        rejected('wrong-executable', {'executable_sha256':'0'*64}, reason='EXECUTABLE_IDENTITY')
        wrong_group = '/sys/fs/cgroup' if str(group)!='/sys/fs/cgroup' else '/sys/fs/cgroup/nonexistent-crg-test'
        rejected('wrong-cgroup', {'cgroup':wrong_group})
        for i, seconds in enumerate([True, 0, 901]):
            rejected('duration-bound-'+str(i), {'duration_seconds':seconds}, reason='PLAN_TARGET_OR_DURATION')
        p, result, value = invoke('normal', execute=True)
        saved = json.loads(Path(value['output']).read_text())
        normal_summary = {k:saved[k] for k in ['sample_count','elapsed_seconds','observer_cpu_seconds','maximum_collection_seconds']}
        record('actual-bounded-private-observation', p.returncode==0 and p.stderr=='' and result['phase']==saved['phase']=='observed'
               and saved['sample_count']==3 and saved['target_signals_or_control_writes']==0
               and 2<=saved['elapsed_seconds']<5 and saved['observer_cpu_seconds']<1
               and stat.S_IMODE(Path(value['output']).stat().st_mode)==0o600 and live_target()
               and all(r['process']['pid']==child.pid and r['process']['start_ticks']==initial['start_ticks'] and not r['tasks_truncated']
                       and r['tasks'] and len(r['tasks'])<=64 and len(r['cgroup'])==11 for r in saved['samples']))
        sentinel = root/'sentinel.json'
        sentinel.write_bytes(b'unchanged-private-sentinel\n')
        sentinel.chmod(0o600)
        p, result, _ = invoke('existing-output', {'output':str(sentinel)})
        record('existing-output-not-replaced', p.returncode==1 and result['reason']=='FRESH_PRIVATE_OUTPUT' and sentinel.read_bytes()==b'unchanged-private-sentinel\n')
        link = root/'symlink-output.json'
        link.symlink_to(sentinel)
        p, result, _ = invoke('symlink-output', {'output':str(link)})
        record('symlink-output-not-followed', p.returncode==1 and result['reason']=='FRESH_PRIVATE_OUTPUT' and sentinel.read_bytes()==b'unchanged-private-sentinel\n')
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            large = root/'oversized-input'
            large.write_bytes(b'x'*17)
            try:
                observer.read_at(directory, large.name, 16)
            except observer.Rejected as error:
                record('bounded-file-read', str(error)=='READ_BOUND')
            else:
                raise AssertionError('bounded-file-read')
        finally:
            os.close(directory)
        bound = observer.Observer(template)
        try:
            record('missing-observation-is-unknown', bound.optional(bound.proc_fd,'crg-nonexistent-test-file')=={'available':False,'reason':'FileNotFoundError'})
        finally:
            bound.close()
        # Signal only the observer process created here; it must flush a partial
        # report and leave the separate sleep target and all controls unchanged.
        path, value = plan('own-observer-term', {'duration_seconds':30})
        proc = subprocess.Popen(command(path)+['--execute'], env=active, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert select.select([proc.stdout],[],[],5)[0]
        assert json.loads(proc.stdout.readline())['phase']=='observing'
        assert Path(value['output']).exists() and proc.poll() is None
        proc.send_signal(signal.SIGTERM)
        stdout, stderr = proc.communicate(timeout=5)
        saved = json.loads(Path(value['output']).read_text())
        record('own-observer-TERM-flushes-without-target-signal', proc.returncode==2 and not stderr and saved['phase']=='incomplete'
               and saved['reason']=='observer-interrupted' and saved['sample_count']>=1 and live_target() and actual_controls()==before)
        path, value = plan('target-exit', {'duration_seconds':30})
        proc = subprocess.Popen(command(path)+['--execute'], env=active, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert select.select([proc.stdout],[],[],5)[0]
        assert json.loads(proc.stdout.readline())['phase']=='observing'
        assert Path(value['output']).exists() and live_target()
        child.terminate()  # Only the disposable sleep fixture owned by this run.
        child.wait(timeout=5)
        stdout, stderr = proc.communicate(timeout=5)
        saved = json.loads(Path(value['output']).read_text())
        record('original-target-exit-stops-no-rebinding', proc.returncode==2 and not stderr and saved['phase']=='incomplete'
               and saved['sample_count']>=1 and saved['elapsed_seconds']<5 and actual_controls()==before)
        result = {'phase':'passed','checks':checks,'source_sha256':digest(SOURCE),'target_was_fresh_sleep_fixture':True,
                  'original_controls_unchanged':actual_controls()==before,'business_processes_used':False,
                  'normal_observation':normal_summary,
                  'actual_cgroup':str(group),'python':sys.version.split()[0],'kernel':os.uname().release}
        (root/'checks-result.json').write_text(json.dumps(result,indent=2)+'\n')
        (root/'checks-result.json').chmod(0o600)
        return result
    finally:
        if child.poll() is None:
            assert live_target()
            child.terminate()
            child.wait(timeout=5)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir',type=Path,required=True)
    args=parser.parse_args()
    assert sys.platform=='linux' and os.environ.get('CRG_THREAD_OBSERVER_SELFTEST')=='authorized-disposable-test-node-only'
    assert str(args.work_dir).startswith('/var/tmp/crg-') and args.work_dir==args.work_dir.resolve() and not args.work_dir.exists()
    args.work_dir.mkdir(mode=0o700)
    result=run(args.work_dir)
    print(json.dumps({'phase':result['phase'],'checks':len(result['checks']),'source_sha256':result['source_sha256'],'business_processes_used':False}))


if __name__=='__main__':
    main()
