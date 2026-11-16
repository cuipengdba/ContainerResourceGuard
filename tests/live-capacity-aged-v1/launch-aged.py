#!/usr/bin/env python3
"""Detach the exact aged wrapper once, only after original terminal readiness.

A launch receipt is not an executor exit receipt or release qualification.
Ambiguous release and failed attempts remain guarded, never automatically retried.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
CONTRACT_SHA='341b4585e6d9d319b1ae5f2c47006f0df34d1e99c93705b49858e1f6a86a9312'
ENTRY=Path('/var/tmp/crg-runner1971-tools-20261116/tests/live-capacity-aged-v1/runner-v3.py')
ROOT=Path('/var/tmp/crg-aged-source37-launch-v3-20261116')
PARENT=Path('/var/tmp')
HANDOFFS=[]


def require(ok,reason):
    if not ok:raise ValueError(reason)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def checked_sources(cfg):
    require(cfg['entry']==str(ENTRY) and cfg['launch_root']==str(ROOT),'FIXED_LAUNCH_PATHS')
    base=Path(cfg['wrapper_tools'])
    for p in [base,*base.parents]:require(not p.is_symlink(),'SOURCE_SYMLINK')
    for name,expected in cfg['files_sha256'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,'RELATIVE_SOURCE')
        path=base/name;require(not path.is_symlink() and path.is_file() and path.stat().st_nlink==1,'REGULAR_SOURCE')
        require(all(not p.is_symlink() for p in path.parents),'SOURCE_PARENT_SYMLINK')
        require(sha(path.read_bytes())==expected,'FROZEN_WRAPPER_SOURCE')


def load_runtime():
    raw=(HERE/'launch-contract.json').read_bytes();require(sha(raw)==CONTRACT_SHA,'LAUNCH_CONTRACT_SHA')
    cfg=json.loads(raw);checked_sources(cfg)
    spec=importlib.util.spec_from_file_location('source37_detach_wrapper',ENTRY)
    w=importlib.util.module_from_spec(spec);sys.modules[spec.name]=w;spec.loader.exec_module(w)
    e,_=w.load_executor();return w,e,cfg


BOOTSTRAP="""import hashlib,os,sys
from pathlib import Path
if sys.stdin.buffer.read(1)!=b'G':sys.exit(125)
if hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()!=sys.argv[2]:sys.exit(126)
fd=os.open('/dev/null',os.O_RDONLY);os.dup2(fd,0);os.close(fd)
os.execv(sys.executable,[sys.executable,'-B',sys.argv[1],*sys.argv[3:]])
"""


def launch_once(w,e,cfg,authority,authority_sha):
    ready,plan=e.readiness(authority,authority_sha)
    require(ready.get('postflight_allowed') is True and plan is not None,'READINESS_CHANGED')
    checked_sources(cfg)
    for p in [ROOT,*ROOT.parents]:require(not p.is_symlink(),'LAUNCH_ROOT_SYMLINK')
    require(ROOT.parent==PARENT,'LAUNCH_PARENT')
    # Different from wrapper ROOT: never pre-create its exclusive runner directory.
    require(not w.ROOT.exists() and not w.ROOT.is_symlink(),'WRAPPER_ATTEMPT_ALREADY_EXISTS')
    os.umask(0o077);ROOT.mkdir(mode=0o700,exist_ok=False);w.sync_dir(ROOT.parent)
    intent={'schema':'crg-aged-detached-intent-v1','entry':str(ENTRY),
        'wrapper_sha256':cfg['files_sha256']['tests/live-capacity-aged-v1/runner-v3.py'],
        'launcher_sha256':sha(w.regular(Path(__file__).resolve())),'contract_sha256':CONTRACT_SHA,
        'authority_sha256':authority_sha,'launcher_pid':os.getpid(),'launcher_start_ticks':w.start_ticks(os.getpid()),
        'started_utc':w.utc(),'automatic_retry_allowed':False,'P10_complete':False,'release_accepted':False}
    w.save(ROOT/'intent.json',intent)
    child=None;out=None;err=None;attempted=False;released=False;received=[];old={}
    def note(signum,frame):received.append(signum)
    for number in [signal.SIGINT,signal.SIGTERM]:old[number]=signal.signal(number,note)
    try:
        out=os.fdopen(os.open(ROOT/'stdout.log',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'wb')
        err=os.fdopen(os.open(ROOT/'stderr.log',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'wb')
        require(not received,'INTERRUPTED_BEFORE_SPAWN')
        args=[sys.executable,'-B','-c',BOOTSTRAP,str(ENTRY),intent['wrapper_sha256'],
            '--authority',str(authority),'--authority-sha256',authority_sha,'--execute']
        child=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=out,stderr=err,start_new_session=True,close_fds=True)
        ticks=w.start_ticks(child.pid)
        w.save(ROOT/'start.json',dict(intent,pid=child.pid,start_ticks=ticks,
            bootstrap_sha256=sha(BOOTSTRAP.encode()),release_attempted=False))
        # Child has already been spawned with the original signal mask. Only the
        # parent's commit section defers signals; after commit no cancellation is claimed.
        mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
        try:
            require(not received,'INTERRUPTED_BEFORE_RELEASE')
            attempted=True;child.stdin.write(b'G');child.stdin.flush();released=True;child.stdin.close()
        finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
        result=dict(intent,schema='crg-aged-detached-launch-v1',phase='handed-off-not-qualified',
            pid=child.pid,start_ticks=ticks,release_attempted=True,release_flushed=True,
            launcher_signals=received,handed_off_utc=w.utc(),stdin_after_bootstrap='/dev/null',
            session_leader_expected=child.pid,process_exit_observed=child.poll(),
            executor_exit_receipt_available=False,qualification_accepted=False)
        w.save(ROOT/'launch.json',result);HANDOFFS.append(child);return result,child
    except BaseException as error:
        if child is not None:
            try:
                if child.stdin and not child.stdin.closed:child.stdin.close()
            except OSError:pass # preserve the original failure and retained guard
            if not attempted:child.wait() # proven EOF before any release attempt
            else:HANDOFFS.append(child) # ambiguous release: retain identity, never retry/kill
        w.save(ROOT/'error.json',{'schema':'crg-aged-detached-error-v1','reason':type(error).__name__,
            'pid':child.pid if child else None,'release_attempted':attempted,'release_flushed':released,
            'ended_utc':w.utc(),'automatic_retry_allowed':False,'manual_inspection_required':True})
        raise
    finally:
        for number,handler in old.items():signal.signal(number,handler)
        for stream in [out,err]:
            if stream is not None:stream.close()


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--launch',action='store_true')
    p.add_argument('--authority',type=Path);p.add_argument('--authority-sha256');a=p.parse_args(argv)
    if bool(a.authority)!=bool(a.authority_sha256):p.error('supply actual authority and its trusted digest together')
    try:
        require(sys.platform=='linux' and os.geteuid()==0,'LINUX_TEST_NODE_ROOT_REQUIRED')
        w,e,cfg=load_runtime();result,plan=e.readiness(a.authority,a.authority_sha256)
        if a.launch and result.get('postflight_allowed') is True:
            require(os.environ.get('CRG_AGED_POSTFLIGHT')=='authorized-disposable-test-node-only','EXPLICIT_LAB_MARKER')
            require(a.authority is not None and re.fullmatch('[0-9a-f]{64}',a.authority_sha256 or ''),'TRUSTED_AUTHORITY_PAIR')
            result,_=launch_once(w,e,cfg,a.authority,a.authority_sha256)
        result.update(P10_complete=False,release_accepted=False)
    except (OSError,TypeError,KeyError,AttributeError,ValueError,subprocess.SubprocessError) as error:
        result={'phase':'rejected','reason':str(error) if isinstance(error,ValueError) else type(error).__name__,
            'P10_complete':False,'release_accepted':False}
    print(json.dumps(result,indent=2));return 2 if result['phase']=='pending' else 1 if result['phase']=='rejected' else 0


if __name__=='__main__':sys.exit(main())
