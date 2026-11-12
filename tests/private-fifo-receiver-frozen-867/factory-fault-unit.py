from pathlib import Path
import hashlib,importlib.util,json,os,sys,tempfile,types

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
factory=Path(sys.argv[1]);hook_source=Path(sys.argv[2]);receiver=Path(sys.argv[3]);shim=Path(sys.argv[4]).read_bytes();m=load(factory,'fifo_factory');hook=load(hook_source,'original_pressure_hook');r=load(receiver,'private_receiver');cases=[]
for variant in ['normal','business-error','start-after-channel-error','stop-error','export-error','cleanup-error','save-error','concurrent-proxy-replacement']:
    with tempfile.TemporaryDirectory(prefix='crg-factory864-') as directory:
        root=Path(directory);tmp=root/'tmp';tmp.mkdir();out=root/'out';out.mkdir();work=[];observers=[];primary=ValueError('original-business');optional=PermissionError('optional-diagnostic');delegate=object();replacement=object()
        class Execution:
            ns=m.NAMESPACE;plan={'run_id':m.RUN_ID}
            def __init__(self):self.root=out
            def save(self):
                if variant=='save-error':raise optional
            def business_native(self,*args):
                work.append(True)
                if variant=='business-error':raise primary
                return primary
        core=types.SimpleNamespace(PressureExecution=Execution,subprocess=delegate)
        def make(execution,role,folder,group,row,detail):
            observer=m.Observer(core,None,execution,role,folder,group,row,detail);observers.append(observer)
            def start():
                c=r.Channel(tmp,observer.run_id,os.geteuid(),os.getegid(),shim,lambda:True);observer.channel=c;c.prepare();c.start();observer.delegate=delegate;observer.proxy=m.ProcessProxy(delegate,observer);core.subprocess=observer.proxy
                if variant=='stop-error':
                    original_stop=c.stop
                    def denied():original_stop();raise optional
                    c.stop=denied
                if variant=='export-error':(out/'dbs-transport-annotations.jsonl').write_bytes(b'keep-existing')
                if variant=='cleanup-error':
                    original_cleanup=c.cleanup
                    def denied_cleanup():original_cleanup();raise optional
                    c.cleanup=denied_cleanup
                if variant=='concurrent-proxy-replacement':core.subprocess=replacement
                if variant=='start-after-channel-error':raise optional
            observer.start=start;return observer
        hook.install(core,make);execution=Execution();row={};caught=None;returned=None
        try:returned=execution.business_native('dbs',root/'fixture',root/'group',row)
        except BaseException as error:caught=error
        assert work==[True] and len(observers)==1;observer=observers[0];status=observer.channel.status();assert status['cleaned'] and status['reader_closed'] and not status['thread_alive'] and status['directory_fd_closed'] and status['parent_fd_closed'] and not list(tmp.iterdir())
        if variant=='business-error':assert caught is primary
        else:assert caught is None and returned is primary
        if variant=='concurrent-proxy-replacement':assert core.subprocess is replacement
        else:assert core.subprocess is delegate
        if variant in ['start-after-channel-error','stop-error','export-error','cleanup-error','save-error','concurrent-proxy-replacement']:assert row['full_BPF_diagnostic']['diagnostic_failed']
        if variant=='export-error':assert (out/'dbs-transport-annotations.jsonl').read_bytes()==b'keep-existing'
        if variant not in ['stop-error','export-error']:assert (out/'dbs-transport-annotations.jsonl').read_bytes()==b''
        observer.finish();assert work==[True]
        cases.append({'variant':variant,'passed':True,'original_result_or_same_exception_preserved':True,'real_channel_reader_and_all_own_files_cleaned':True})
print(json.dumps({'schema':'crg-private-fifo-factory-fault-unit-v1','phase':'passed','factory_sha256':hashlib.sha256(factory.read_bytes()).hexdigest(),'receiver_sha256':hashlib.sha256(receiver.read_bytes()).hexdigest(),'cases':cases,'synthetic_core_only_not_vendor_full600':True}))
