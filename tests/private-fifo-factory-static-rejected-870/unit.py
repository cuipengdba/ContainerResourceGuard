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
with tempfile.TemporaryDirectory(prefix='crg-factory-start869-') as directory:
    root=Path(directory);tools=root/'tools';tools.mkdir();(tools/'native-private-fifo.py').write_bytes(receiver.read_bytes());out=root/'out';out.mkdir();group=root/'group';group.mkdir();folder=root/'fixture';folder.mkdir()
    m.TOOLS=tools;m.ROOT=out;launched=[];sessions=[];sentinel=object();run_id='2026111286900'
    class Delegate:
        def Popen(self,args,*extra,**kwargs):launched.append((args,extra,kwargs));return sentinel
    delegate=Delegate();listener={'pid':77,'executable_sha256':'unit-only-vendor-SHA','executable_path':'/opt/dbs/bin/dbs'}
    class Collector:
        def __init__(self,context,name,plan):self.context=context;self.name=name;self.plan=plan;self.child=None;self.record={};self.executed=None;sessions.append(self)
        def launch(self,execute):
            self.executed=execute
            if execute:assert observer.channel.status()['started'] and observer.channel.thread.is_alive()
            return execute
        def finish(self):
            return None if self.executed else {'phase':'preflight-readonly','owned_vendor_fixture_validated':True,'hooks':list(range(40)),'program_ids':None,'map_ids':None}
    helper=types.SimpleNamespace(VENDOR_SHA=listener['executable_sha256'],identity=lambda pid:{'pid':pid,'start_ticks':123,'cgroup':'unit-control-cgroup'},Collector=Collector)
    class Execution:
        ns=m.NAMESPACE;root=out;plan={'run_id':run_id[:-1]};worker=types.SimpleNamespace(poll=lambda:0)
        def identity(self,role):return {'metadata':{'uid':'unit-pod-uid'}},'unit-container-id',os.getpid(),group
        def processes(self,*args):return [(listener['pid'],123,'unit-only-vendor-SHA')]
        def run(self,args):
            assert args==['kubectl','get','namespace',m.NAMESPACE,'-o','json'];return types.SimpleNamespace(stdout=json.dumps({'metadata':{'uid':'unit-namespace-uid'}}))
        def ex(self,role,*args):
            assert role=='dbs'
            if args==('id','-u','postgres'):value=str(os.geteuid())
            elif args==('id','-g','postgres'):value=str(os.getegid())
            else:
                assert args==('sha256sum','/tmp/crg-transport-'+run_id+'/sitecustomize.py');value=hashlib.sha256(Path(args[1]).read_bytes()).hexdigest()+'  '+args[1]
            return types.SimpleNamespace(stdout=value)
        def save(self):pass
    core=types.SimpleNamespace(subprocess=delegate,session=types.SimpleNamespace(listener_owner=lambda value:listener));record={};observer=m.Observer(core,helper,Execution(),'dbs',folder,group,{},record)
    try:
        observer.start();assert [v.executed for v in sessions]==[False,True] and core.subprocess is observer.proxy and observer.channel.status()['started']
        command=['kubectl','exec','-n',m.NAMESPACE,'dbs-business','-c','dbs','--','su','-','postgres','-c',m.native_command('dbs',run_id)]
        assert core.subprocess.Popen(command,stdin='same-input',stdout='same-output',stderr='same-error') is sentinel
        assert len(launched)==1 and launched[0][2]=={'stdin':'same-input','stdout':'same-output','stderr':'same-error'} and 'CRG_VENDOR_TRANSPORT_FIFO=/tmp/crg-transport-'+run_id+'/annotations.fifo' in launched[0][0][-1] and record['native_launch_count']==1 and record['native_source_unchanged']
    finally:observer.finish()
    status=observer.channel.status();assert status['cleaned'] and status['reader_closed'] and not status['thread_alive'] and status['directory_fd_closed'] and status['parent_fd_closed'] and core.subprocess is delegate and not Path('/tmp/crg-transport-'+run_id).exists()
    assert (out/'dbs-transport-annotations.jsonl').read_bytes()==b''
    cases.append({'variant':'actual-Observer-start-loads-pinned-receiver-prepares-before-collector-proxies-once-and-cleans','passed':True,'only-collector-and-Kubernetes-identity-are-synthetic':True,'real-host-private-FIFO-thread-module-load-and-command-rewrite':True,'vendor-native-or-BPF-not-executed':True})
print(json.dumps({'schema':'crg-private-fifo-factory-fault-unit-v1','phase':'passed','factory_sha256':hashlib.sha256(factory.read_bytes()).hexdigest(),'receiver_sha256':hashlib.sha256(receiver.read_bytes()).hexdigest(),'cases':cases,'synthetic_core_only_not_vendor_full600':True}))
