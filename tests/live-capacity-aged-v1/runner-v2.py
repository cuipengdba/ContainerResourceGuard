#!/usr/bin/env python3
"""One foreground lab execution, guarded by original aged readiness.

Pending/default calls write nothing. This is not the product supervisor.
An interrupted or ambiguous attempt is retained and never automatically retried.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
CONTRACT_SHA='9ce84bef5751fa4f5259c4ccfdc1f395e238bbe022a8e8bf766e8b7666adf863'
ROOT=Path('/var/tmp/crg-aged-source37-runner-v2-20261116')
PARENT=Path('/var/tmp')
ENTRY=Path('/var/tmp/crg-aged1952-tools-20261116/tests/live-capacity-aged-v1/executor-v2.py')


def require(ok,reason):
    if not ok:raise ValueError(reason)


def digest(raw):return hashlib.sha256(raw).hexdigest()


def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def regular(path):
    path=Path(path)
    require(path.is_absolute() and '..' not in path.parts,'ABSOLUTE_CLEAN_PATH')
    for p in [*reversed(path.parents),path]:require(not p.is_symlink(),'SYMLINK_INPUT')
    info=path.lstat();require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_size<=32*1024**2,'REGULAR_BOUNDED_INPUT')
    with path.open('rb') as stream:
        raw=stream.read();after=os.fstat(stream.fileno())
    require((info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),'INPUT_CHANGED')
    return raw


def load_executor():
    raw=regular(HERE/'runner-v2-contract.json');require(digest(raw)==CONTRACT_SHA,'RUNNER_CONTRACT_SHA')
    contract=json.loads(raw);require(contract['entry']==str(ENTRY) and contract['root']==str(ROOT),'EXACT_RUNNER_PATHS')
    root=Path(contract['executor_tools'])
    for name,expected in contract['files_sha256'].items():
        require('..' not in Path(name).parts and not Path(name).is_absolute(),'SOURCE_RELATIVE_PATH')
        require(digest(regular(root/name))==expected,'FROZEN_EXECUTOR_INPUT')
    spec=importlib.util.spec_from_file_location('source37_runner_executor_v2',ENTRY)
    e=importlib.util.module_from_spec(spec);sys.modules[spec.name]=e;spec.loader.exec_module(e)
    require(e.CONTRACT_SHA==contract['executor_contract_sha256'],'EXECUTOR_CONTRACT_SHA')
    return e,contract


def sync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def exclusive(path,raw):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
    sync_dir(path.parent)


def save(path,value):exclusive(path,(json.dumps(value,indent=2)+'\n').encode())


def start_ticks(pid):
    raw=Path('/proc',str(pid),'stat').read_text();tail=raw.rsplit(')',1)[1].split()
    require(int(raw.split('(',1)[0])==pid and tail[0]!='Z','CHILD_PROCESS_IDENTITY')
    return int(tail[19])


# The child cannot execute the workload before its PID/start identity is durable.
# exec keeps that exact PID/start. EOF or any different byte exits without execution.
BOOTSTRAP="""import hashlib,os,sys
from pathlib import Path
if sys.stdin.buffer.read(1)!=b'G':sys.exit(125)
if hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()!=sys.argv[2]:sys.exit(126)
os.execv(sys.executable,[sys.executable,'-B',sys.argv[1],*sys.argv[3:]])
"""


def run_once(e,contract,authority,authority_sha):
    result,plan=e.readiness(authority,authority_sha)
    require(result.get('postflight_allowed') is True and plan is not None,'READINESS_CHANGED')
    # Exclusive root is the non-repeatable attempt guard; never remove/reuse it.
    for p in [*reversed(ROOT.parents),ROOT]:require(not p.is_symlink(),'RUNNER_ROOT_SYMLINK')
    require(ROOT.parent==PARENT,'RUNNER_ROOT_PARENT')
    os.umask(0o077);ROOT.mkdir(mode=0o700,exist_ok=False);sync_dir(ROOT.parent)
    invocation={'schema':'crg-source37-aged-invocation-v2','entry':str(ENTRY),
        'executor_sha256':contract['files_sha256']['tests/live-capacity-aged-v1/executor-v2.py'],
        'contract_sha256':e.CONTRACT_SHA,'authority_sha256':authority_sha,
        'wrapper_sha256':digest(regular(Path(__file__).resolve())),
        'runner_contract_sha256':CONTRACT_SHA,'started_utc':utc(),
        'supervisor_pid':os.getpid(),'supervisor_start_ticks':start_ticks(os.getpid()),
        'P10_complete':False,'release_accepted':False}
    save(ROOT/'intent.json',invocation)
    child=None;old={};interrupted=[];released=False
    def forward(signum,frame):
        interrupted.append(signum)
        if len(interrupted)==1 and child is not None and released and child.poll() is None:
            try:
                if start_ticks(child.pid)==ticks:os.kill(child.pid,signal.SIGTERM)
            except (FileNotFoundError,ProcessLookupError,ValueError):pass
    for s in [signal.SIGINT,signal.SIGTERM]:old[s]=signal.signal(s,forward)
    started=time.monotonic();out=None;err=None
    try:
        out=os.fdopen(os.open(ROOT/'stdout.log',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'wb')
        err=os.fdopen(os.open(ROOT/'stderr.log',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'wb')
        require(not interrupted,'INTERRUPTED_BEFORE_SPAWN')
        args=[sys.executable,'-B','-c',BOOTSTRAP,str(ENTRY),invocation['executor_sha256'],
            '--authority',str(authority),'--authority-sha256',authority_sha,'--execute']
        child=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=out,stderr=err,start_new_session=True)
        ticks=start_ticks(child.pid)
        save(ROOT/'start.json',dict(invocation,pid=child.pid,start_ticks=ticks,
            bootstrap_sha256=digest(BOOTSTRAP.encode()),workload_released=False))
        require(not interrupted,'INTERRUPTED_BEFORE_RELEASE')
        child.stdin.write(b'G');child.stdin.flush();released=True;child.stdin.close()
        # Wait for the actual direct child. No timeout, synthetic exit, killpg or restart.
        code=child.wait();elapsed=time.monotonic()-started
        for stream in [out,err]:stream.flush();os.fsync(stream.fileno())
        report_path=Path(e.CONTRACT['work_root'])/'report.json'
        report_raw=regular(report_path) if report_path.exists() else None
        receipt=dict(invocation,schema='crg-source37-aged-exit-v2',pid=child.pid,start_ticks=ticks,
            exit=code,elapsed_seconds=elapsed,ended_utc=utc(),interrupted=interrupted,
            report_sha256=digest(report_raw) if report_raw is not None else None,
            stdout_sha256=digest(regular(ROOT/'stdout.log')),stderr_sha256=digest(regular(ROOT/'stderr.log')),
            workload_released=released,qualification_accepted=False)
        save(ROOT/'exit.json',receipt)
        return {'phase':'exited','exit':code,'receipt_sha256':digest(regular(ROOT/'exit.json')),
            'elapsed_seconds':elapsed,'qualification_accepted':False,'P10_complete':False,'release_accepted':False}
    except BaseException as error:
        # A pre-release child sees EOF and cannot execute. A released child is left
        # identifiable for manual inspection if the supervisor itself fails.
        if child is not None and not released:
            if child.stdin and not child.stdin.closed:child.stdin.close()
            child.wait()
        save(ROOT/'supervisor-error.json',{'schema':'crg-source37-aged-supervisor-error-v2',
            'reason':type(error).__name__,'child_pid':child.pid if child else None,
            'workload_released':released,'ended_utc':utc(),'automatic_retry_allowed':False})
        raise
    finally:
        for s,handler in old.items():signal.signal(s,handler)
        for stream in [out,err]:
            if stream is not None:stream.close()


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true')
    p.add_argument('--authority',type=Path);p.add_argument('--authority-sha256');a=p.parse_args(argv)
    if bool(a.authority)!=bool(a.authority_sha256):p.error('supply the actual authority and trusted digest together')
    try:
        require(sys.platform=='linux' and os.geteuid()==0,'LINUX_TEST_NODE_ROOT_REQUIRED')
        e,contract=load_executor();result,plan=e.readiness(a.authority,a.authority_sha256)
        if a.execute and result.get('postflight_allowed') is True:
            require(os.environ.get('CRG_AGED_POSTFLIGHT')=='authorized-disposable-test-node-only','EXPLICIT_LAB_MARKER')
            require(a.authority is not None and re.fullmatch('[0-9a-f]{64}',a.authority_sha256 or ''),'TRUSTED_AUTHORITY_PAIR')
            result=run_once(e,contract,a.authority,a.authority_sha256)
        result.update(P10_complete=False,release_accepted=False)
    except (OSError,TypeError,KeyError,AttributeError,ValueError,subprocess.SubprocessError) as error:
        result={'phase':'rejected','reason':str(error) if isinstance(error,ValueError) else type(error).__name__,
            'P10_complete':False,'release_accepted':False}
    print(json.dumps(result,indent=2))
    return 2 if result['phase']=='pending' else (0 if result['phase']=='exited' and result['exit']==0 else 1 if result['phase'] in ['rejected','exited'] else 0)


if __name__=='__main__':sys.exit(main())
