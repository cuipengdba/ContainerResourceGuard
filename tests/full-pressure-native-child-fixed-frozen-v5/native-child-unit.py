from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,tempfile,types

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
factory=Path(sys.argv[1]);hook_path=Path(sys.argv[2]);m=load(factory,'crg_native_child_factory');hook=load(hook_path,'crg_native_child_hook');cases=[];children=[];identities=[]
def own_child(code='import sys;sys.stdin.buffer.read()'):
    child=subprocess.Popen([sys.executable,'-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    children.append(child);p=Path('/proc',str(child.pid),'stat');identities.append({'pid':child.pid,'start_ticks':int(p.read_bytes().rsplit(b')',1)[1].split()[19]) if p.exists() else None});return child
def complete(child):
    if child.stdin and not child.stdin.closed:child.stdin.close()
    child.wait(timeout=5)
def setup(action=None):
    execution=types.SimpleNamespace(ns=m.NAMESPACE,plan={'run_id':m.RUN_ID},worker=None)
    record={};owner=m.Observer(None,None,execution,'dbs',Path('.'),Path('.'),{},record);calls=[]
    class Delegate:
        def Popen(self,args,*rest,**kwargs):
            calls.append((args,rest,kwargs));return action() if action else own_child()
    proxy=m.ProcessProxy(Delegate(),owner)
    args=['kubectl','exec','-n',m.NAMESPACE,'dbs-business','-c','dbs','--','su','-','postgres','-c',m.native_command('dbs',owner.run_id)]
    return execution,record,owner,proxy,args,calls
def passed(name,**extra):cases.append(dict(name=name,passed=True,**extra))
try:
    e,r,o,p,a,c=setup();child=p.Popen(a);assert child is o.native_child and len(c)==1;complete(child);e.worker=None
    assert o.original_native_exited() and r['original_native_child']['pid']==child.pid and r['original_native_child']['exit_code']==0
    passed('original-exited-and-business-slot-cleared',real_child_pid=child.pid)
    replacement=own_child();e.worker=replacement;assert replacement.poll() is None and o.original_native_exited() and r['original_native_child']['pid']==child.pid
    assert replacement.poll() is None;complete(replacement);passed('business-slot-replaced-with-live-other-child-does-not-change-captured-child')
    e,r,o,p,a,c=setup();child=p.Popen(a);unrelated=own_child();complete(unrelated);e.worker=unrelated
    assert not o.original_native_exited() and r['original_native_child']['pid']==child.pid and r['original_native_child']['exit_code'] is None and child.poll() is None
    passed('captured-child-live-is-not-inferred-exited-from-replacement')
    complete(child);assert o.original_native_exited();passed('same-captured-child-later-exit-observed-without-signal')
    e,r,o,p,a,c=setup(lambda:own_child('import sys;sys.stdin.buffer.read();sys.exit(7)'));child=p.Popen(a);complete(child);e.worker=None
    assert o.original_native_exited() and r['original_native_child']['exit_code']==7
    passed('original-nonzero-exit-preserved-as-nonzero-business-result')
    e,r,o,p,a,c=setup();ordinary=['ordinary-command'];child=p.Popen(ordinary);complete(child)
    assert c[0][0] is ordinary and not o.original_native_exited() and o.native_child is None and o.native_child_capture_count==0 and 'native_launch_count' not in r
    passed('unmatched-command-returned-once-with-no-capture')
    for matched in [True,False]:
        primary=OSError('original-launch-error')
        def fail():raise primary
        e,r,o,p,a,c=setup(fail);caught=None
        try:p.Popen(a if matched else ['ordinary-command'])
        except BaseException as exc:caught=exc
        assert caught is primary and len(c)==1 and o.native_child is None and o.native_child_capture_count==0
        passed('matched-launch-exception-identity-no-retry' if matched else 'unmatched-launch-exception-identity-no-retry')
    e,r,o,p,a,c=setup();optional=PermissionError('capture denied')
    def deny(child):raise optional
    o.remember_native_child=deny;child=p.Popen(a);assert child is children[-1] and child.poll() is None and len(c)==1 and r['diagnostic_failed'] and r['diagnostic_errors'][0]['action']=='capture-original-native-child';complete(child)
    passed('capture-failure-returns-original-child-and-records-diagnostic')
    e,r,o,p,a,c=setup()
    class Record(dict):
        def setdefault(self,*args):raise PermissionError('diagnostic record denied')
    o.record=Record();o.remember_native_child=deny;child=p.Popen(a);assert child is children[-1] and len(c)==1;complete(child)
    passed('capture-and-error-record-failure-still-return-original-child')
    e,r,o,p,a,c=setup();first=p.Popen(a);second=p.Popen(a);complete(first);complete(second)
    assert first is o.native_child and second is not first and o.native_child_capture_count==2 and not o.original_native_exited() and r['diagnostic_failed'] and len(c)==2
    passed('duplicate-exact-command-retains-first-handle-and-fails-diagnostic')
    e,r,o,p,a,c=setup();child=p.Popen(a);complete(child);original_poll=child.poll
    def fail_poll():raise optional
    child.poll=fail_poll;assert not o.original_native_exited() and r['diagnostic_failed'] and r['diagnostic_errors'][-1]['action']=='poll-original-native-child';child.poll=original_poll
    passed('poll-failure-is-recorded-without-business-result-change')
    for mode in ['return','original-business-error']:
        e,r,o,p,a,c=setup();primary=ValueError('original-business-error');value=object();original_fields={'native_exit':0,'native':{'sql':{'errors':0},'api':{'errors':0}}};before=json.dumps(original_fields,sort_keys=True);caught=None;returned=None
        def work():
            child=p.Popen(a);e.worker=child;complete(child);e.worker=None
            if mode=='original-business-error':raise primary
            return value
        def finish():
            assert o.original_native_exited()
            if mode=='original-business-error':raise optional
        try:returned=hook.preserve_original_business(work,lambda:None,finish,r,lambda:None)
        except BaseException as exc:caught=exc
        assert json.dumps(original_fields,sort_keys=True)==before and len(c)==1 and o.native_child.poll()==0
        if mode=='return':assert caught is None and returned is value and not r['diagnostic_failed']
        else:assert caught is primary and r['diagnostic_failed'] and r['original_business_error_class']=='ValueError'
        passed('hook-after-worker-cleared-preserves-'+mode)
    e,r,o,p,a,c=setup();o.shim_directory='/wrong-shim';child=p.Popen(a);complete(child)
    assert c[0][0] is a and len(c)==1 and o.native_child is None and r['diagnostic_failed']
    passed('annotation-preparation-failure-does-not-retry-or-capture-unmatched-launch')
finally:
    for child in children:
        try:complete(child)
        except Exception:
            if child.poll() is None:child.terminate();child.wait(timeout=5)
        for stream in [child.stdin,child.stdout,child.stderr]:
            if stream is not None and not stream.closed:stream.close()
cleanup=[]
for row in identities:
    path=Path('/proc',str(row['pid']),'stat');same=path.exists() and int(path.read_bytes().rsplit(b')',1)[1].split()[19])==row['start_ticks'];assert not same
    cleanup.append(dict(row,original_child_absent=True))
assert len(cases)==15 and all(v['passed'] for v in cases)
print(json.dumps({'schema':'crg-native-child-lifecycle-real-process-v1','phase':'passed','factory_sha256':hashlib.sha256(factory.read_bytes()).hexdigest(),'hook_sha256':hashlib.sha256(hook_path.read_bytes()).hexdigest(),'cases':cases,'own_real_children':cleanup,'all_own_child_handles_reaped_and_streams_closed':True,'business_workload_or_BPF_not_executed':True,'previous950_failure_not_regraded':True}))
