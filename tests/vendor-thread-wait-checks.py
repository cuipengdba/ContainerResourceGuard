#!/usr/bin/env python3
"""Parser/privacy guards and actual procfs capture of one own blocked pipe child.

The real fixture waits in interruptible S state, not simulated D or vendor I/O.
No target signals, ptrace attachment, memory reads or control writes are used.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time

sys.dont_write_bytecode=True
here=Path(__file__).parent
def module(name):
    spec=importlib.util.spec_from_file_location(name,here/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
wait=module('vendor-thread-wait');base=module('vendor-thread-observer')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--work-dir',type=Path,required=True);args=parser.parse_args();root=args.work_dir
    assert sys.platform=='linux' and os.environ.get('CRG_THREAD_WAIT_SELFTEST')=='authorized-disposable-test-node-only'
    assert str(root).startswith('/var/tmp/crg-') and '..' not in root.parts and not root.exists();root.mkdir(mode=0o700)
    checks=[];p=None;proc_fd=None;task_fd=None;actual=None
    def check(name,value):checks.append({'name':name,'passed':bool(value)});assert value,name
    def call(number=74,fd='0x3'):return str(number)+' '+fd+' '+' '.join(['0xdeadbeef']*7)+'\n'
    membership=Path('/proc/self/cgroup').read_text().strip();assert membership.startswith('0::/')
    group=Path('/sys/fs/cgroup')/membership[3:].lstrip('/')
    def controls():return {name:(group/name).read_text() if (group/name).exists() else None for name in ['cpu.max','memory.max','io.max']}
    before=controls()
    try:
        parsed=wait.syscall(call(),'linux-x86_64')
        check('native-x86-64-fsync-FD-decoded',parsed['operation']=='fsync' and parsed['fd']==3)
        check('other-registers-pointers-PC-SP-never-recorded','deadbeef' not in json.dumps(parsed) and set(parsed)=={'available','number','abi','operation','FD_argument_available','fd'})
        check('running-is-explicit-unknown',wait.syscall('running\n','linux-x86_64')=={'available':False,'reason':'task-running'})
        check('outside-systemcall-is-explicit-unknown',wait.syscall('-1 0xdeadbeef 0xdeadbeef\n','linux-x86_64')['reason']=='outside-system-call')
        unknown=wait.syscall(call(),'unknown');check('unknown-ABI-does-not-decode-FD',unknown['operation']=='unknown' and not unknown['FD_argument_available'] and 'fd' not in unknown)
        check('futex-pointer-never-treated-as-file-descriptor',not wait.syscall(call(202),'linux-x86_64')['FD_argument_available'])
        try:wait.syscall('74 arbitrary-private-data','linux-x86_64')
        except wait.Rejected as error:check('malformed-syscall-refused-with-fixed-reason',str(error)=='SYSCALL_FORMAT')
        else:check('malformed-syscall-refused-with-fixed-reason',False)
        frames=wait.kernel_stack('[<ffffffffdeadbeef>] folio_wait_writeback+0x10/0x20\n[<0>] __x64_sys_fsync+0x1/0x2\n')
        check('kernel-symbols-retained-with-addresses-offsets-discarded',frames['frames']==['folio_wait_writeback','__x64_sys_fsync'] and 'deadbeef' not in json.dumps(frames) and '0x' not in json.dumps(frames))
        frames=wait.kernel_stack('[<0>] example_wait+0x1/0x2\n'*30);check('kernel-frames-bounded-and-truncation-explicit',len(frames['frames'])==12 and frames['truncated'])
        check('approved-vendor-log-path-retained',wait.fd_metadata('/opt/dbs/log/DBS.log')['path']=='/opt/dbs/log/DBS.log')
        check('unapproved-path-redacted','private-token' not in json.dumps(wait.fd_metadata('/root/private-token')))
        check('deleted-suffix-reported-without-path-corruption',wait.fd_metadata('/opt/dbs/log/DBS.log (deleted)')=={'kind':'allowlisted-path','path':'/opt/dbs/log/DBS.log','deleted':True})
        check('path-traversal-redacted',wait.fd_metadata('/opt/dbs/log/../../private-token')['kind']=='redacted-other-path')
        check('path-newlines-redacted','private-token' not in json.dumps(wait.fd_metadata('/opt/dbs/log/\nprivate-token')))
        p=subprocess.Popen([sys.executable,'-c',"import os,sys;sys.stdout.write('ready\\n');sys.stdout.flush();assert os.read(0,1)==b'x'"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert select.select([p.stdout],[],[],5)[0] and p.stdout.readline()==b'ready\n';time.sleep(.05)
        proc_fd=os.open('/proc/'+str(p.pid),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        task_fd=os.open('task/'+str(p.pid),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=proc_fd)
        expected=base.stat_fields(base.read_at(task_fd,'stat'));abi=wait.executable_abi(proc_fd)
        check('actual-child-ELF-ABI-detected',abi=='linux-x86_64')
        began=time.monotonic();actual=wait.capture(task_fd,proc_fd,expected,base.read_at,base.stat_fields,abi);elapsed=time.monotonic()-began
        check('actual-blocked-pipe-read-systemcall-captured',actual['available'] and actual['syscall']['available'] and actual['syscall']['operation']=='read' and actual['syscall']['fd']==0)
        check('actual-pipe-metadata-has-no-inode-or-contents',actual['descriptor']=={'available':True,'kind':'pipe'})
        stack=actual['kernel_stack'];check('actual-kernel-stack-or-explicit-unknown',bool(stack.get('frames')) if stack['available'] else bool(stack.get('reason')))
        check('actual-child-same-start-and-no-signal',p.poll() is None and base.stat_fields(base.read_at(task_fd,'stat'))['start_ticks']==expected['start_ticks'] and actual['task_identity_rechecked'] and actual['separate_reads_not_atomic'])
        wrong=dict(expected,start_ticks=expected['start_ticks']+1)
        check('changed-task-start-discards-capture',wait.capture(task_fd,proc_fd,wrong,base.read_at,base.stat_fields,abi)['reason']=='TASK_CHANGED')
        def denied(*args):raise PermissionError('private-token-never-record')
        denied_result=wait.capture(task_fd,proc_fd,expected,denied,base.stat_fields,abi)
        check('permission-denial-is-unknown-with-no-arbitrary-message',denied_result['reason']=='PermissionError' and 'private-token' not in json.dumps(denied_result))
        count=[0]
        def changing(fd,name,maximum=65536):
            if name=='syscall':
                count[0]+=1
                if count[0]==2:return 'running\n'
            return base.read_at(fd,name,maximum)
        check('syscall-race-discards-FD-and-stack-inference',wait.capture(task_fd,proc_fd,expected,changing,base.stat_fields,abi)['reason']=='SYSCALL_CHANGED')
        check('original-controls-unchanged',controls()==before)
        p.stdin.write(b'x');p.stdin.flush();p.stdin.close();p.wait(timeout=5)
        check('own-child-exits-naturally-with-no-signals',p.returncode==0 and not p.stderr.read())
    finally:
        for fd in [task_fd,proc_fd]:
            if fd is not None:os.close(fd)
        if p is not None and p.poll() is None:
            p.stdin.close()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
        result={'schema':'crg-thread-wait-checks-v1','phase':'passed' if len(checks)==24 and all(v['passed'] for v in checks) else 'failed',
                'checks':checks,'actual_pipe_capture':actual,'actual_capture_seconds':elapsed if actual is not None else None,
                'own_child_reaped':p is not None and p.returncode is not None,'original_controls_unchanged':controls()==before,
                'actual_fixture_state':'S interruptible pipe wait; not D or vendor business','full_pressure_or_business_accepted':False,
                'source_sha256':{name:hashlib.sha256((here/name).read_bytes()).hexdigest() for name in ['vendor-thread-wait.py','vendor-thread-wait-checks.py','vendor-thread-observer.py']}}
        path=root/'checks-result.json';path.write_text(json.dumps(result,indent=2)+'\n');path.chmod(0o600)
    print(json.dumps({'phase':result['phase'],'checks':len(checks)}))
    return 0 if result['phase']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
