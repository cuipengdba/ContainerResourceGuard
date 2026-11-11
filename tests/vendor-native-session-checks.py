#!/usr/bin/env python3
"""Actual Linux pidfd tests; signals only children created by this selftest.

Dummy helper output is lifecycle evidence, never database or 600-second evidence.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
spec=importlib.util.spec_from_file_location('native_session',Path(__file__).with_name('vendor-native-session.py'))
session=importlib.util.module_from_spec(spec);spec.loader.exec_module(session)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir',type=Path,required=True)
    args=parser.parse_args();root=args.work_dir
    assert sys.platform=='linux' and os.environ.get('CRG_NATIVE_SESSION_SELFTEST')=='authorized-disposable-test-node-only'
    assert str(root).startswith('/var/tmp/crg-') and '..' not in root.parts and not root.exists()
    root.mkdir(mode=0o700)
    entry=root/'fixture.py'
    entry.write_text('''import json,os,pathlib,signal,sys,time
run=sys.argv[sys.argv.index('--run-id')+1];root=pathlib.Path(__file__).parent
stop=[False];ignore=os.environ.get('CRG_FIXTURE_IGNORE_TERM')=='1'
def term(number,frame):
 if not ignore:stop[0]=True
signal.signal(signal.SIGTERM,term)
(root/(run+'-ready')).write_text(str(os.getpid()))
began=time.monotonic()
while not stop[0]:
 if os.environ.get('CRG_FIXTURE_NATURAL_EXIT')=='1' and time.monotonic()-began>=1:break
 time.sleep(.02)
(root/(run+'-final.json')).write_text(json.dumps({'interrupted':stop[0],'pid':os.getpid()}))
''',encoding='utf-8');entry.chmod(0o444)
    digest=hashlib.sha256(entry.read_bytes()).hexdigest()
    membership=Path('/proc/self/cgroup').read_text().strip();assert membership.startswith('0::/')
    group=Path('/sys/fs/cgroup')/membership[3:].lstrip('/')
    def controls():
        out={}
        for name in ['cpu.max','memory.max','io.max']:
            p=group/name;out[name]=p.read_text() if p.exists() else None
        return out
    before=controls();children=[];sessions=[];checks=[];records={}
    def check(name,value):
        checks.append({'name':name,'passed':bool(value)});assert value,name
    def child(run,extra_args=(),**flags):
        p=subprocess.Popen([sys.executable,str(entry),'--run-id',run,'--seconds','600','--test-phase','smoke',*extra_args],
                           env=dict(os.environ,**flags),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        children.append(p);deadline=time.monotonic()+5
        while not (root/(run+'-ready')).exists() or (root/(run+'-ready')).read_text()!=str(p.pid):
            assert p.poll() is None and time.monotonic()<deadline;time.sleep(.01)
        return p
    def attach(name,run,worker_sha=digest):
        record={};records[name]=record;s=session.Session(group,entry,run,600,worker_sha,record);sessions.append(s);s.attach();return s
    def rejects(name,callback,reason):
        try:callback()
        except session.Rejected as error:check(name,str(error)==reason)
        else:check(name,False)
    try:
        decoy=child('202611112164',extra_args=['x'*10000])
        p=child('202611112160');s=attach('term','202611112160')
        check('actual-unique-child-bound-with-start-cgroup-source-exe-and-pidfd',s.identity['pid']==p.pid and s.identity['start_ticks']>0 and s.pidfd is not None)
        check('oversized-unrelated-argv-cannot-hide-or-select-worker',s.record['oversized_unrelated_argv_ignored']>=1 and decoy.poll() is None)
        original=s.identity['start_ticks'];s.identity['start_ticks']+=1
        rejects('wrong-start-refuses-signal',s.signal_term,'NATIVE_SESSION_SIGNAL_IDENTITY');s.identity['start_ticks']=original
        check('wrong-start-left-child-running',p.poll() is None and s.record['signals_sent']==0)
        rejects('no-business-failure-cannot-terminate-load',lambda:s.finish_after_failure(None),'NATIVE_SESSION_REQUIRES_BUSINESS_FAILURE')
        rejects('over120second-cleanup-refused',lambda:s.finish_after_failure(RuntimeError(),121),'NATIVE_SESSION_CLEANUP_BOUND')
        rejects('wrong-run-does-not-select-other-worker',lambda:attach('wrong-run','202611112169'),'NATIVE_SESSION_UNIQUE_WORKER')
        rejects('wrong-source-refuses-attach',lambda:attach('wrong-source','202611112160','0'*64),'NATIVE_SESSION_SOURCE_IDENTITY')
        check('all-refusals-left-correct-child-and-controls-unchanged',p.poll() is None and controls()==before and s.record['signals_sent']==0)
        s.finish_after_failure(RuntimeError('original failure'),5);p.wait(timeout=2)
        final=json.loads((root/'202611112160-final.json').read_bytes())
        check('TERM-allows-own-final-file-with-interrupted-identity',final=={'interrupted':True,'pid':p.pid} and s.record['signals_sent']==1 and s.record['original_worker_exited'])
        check('cleanup-is-not-complete600s-or-known-exit-code',not s.record['complete600s_accepted'] and s.record['worker_exit_code_unknown'] and not s.record['forced_kill'])
        s.close();s.close();check('pidfd-close-idempotent',s.pidfd is None)
        p=child('202611112161',CRG_FIXTURE_IGNORE_TERM='1');s=attach('timeout','202611112161')
        rejects('unresponsive-own-worker-times-out-with-no-force-kill',lambda:s.finish_after_failure(RuntimeError(),.2),'NATIVE_SESSION_FINAL_FLUSH_TIMEOUT')
        check('timeout-keeps-worker-live-for-original-cleanup',p.poll() is None and not s.record['forced_kill'] and s.record['signals_sent']==1)
        p.kill();p.wait(timeout=2);s.close()
        p=child('202611112162',CRG_FIXTURE_NATURAL_EXIT='1');s=attach('natural','202611112162');p.wait(timeout=3)
        s.finish_after_failure(RuntimeError(),1);s.close()
        check('already-exited-worker-is-never-signaled',s.record['signals_sent']==0 and not json.loads((root/'202611112162-final.json').read_bytes())['interrupted'])
        a=child('202611112163');c=child('202611112163')
        rejects('duplicate-exact-workers-refused',lambda:attach('duplicate','202611112163'),'NATIVE_SESSION_UNIQUE_WORKER')
        check('duplicate-refusal-signals-neither-worker',a.poll() is None and c.poll() is None)
        check('all-control-values-preserved',controls()==before)
    finally:
        for s in sessions:s.close()
        for p in children:
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=2)
                except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2)
        out={'schema':'crg-native-session-checks-v1','phase':'passed' if len(checks)==18 and all(v['passed'] for v in checks) else 'failed',
             'checks':checks,'records':records,'selftest_only_children_all_reaped':all(p.returncode is not None for p in children),
             'original_controls_unchanged':controls()==before,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(__file__).with_name('vendor-native-session.py')]},
             'real_PG_or_vendor_business_executed':False,'full600s_accepted':False}
        path=root/'checks-result.json';path.write_text(json.dumps(out,indent=2)+'\n');path.chmod(0o600)
    print(json.dumps({'phase':out['phase'],'checks':len(checks)}))
    return 0 if out['phase']=='passed' else 1


if __name__=='__main__':
    raise SystemExit(main())
