"""Full original pressure integration, restricted to one fresh fixed fixture.

The frozen core business method and native worker bytes stay unchanged. The
collector is an optional host diagnostic, not the container's CRG Agent.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,shlex,stat,subprocess,time

TOOLS=Path('/var/tmp/crg-high960-tools-20261113')
ROOT=Path('/var/tmp/crg-high960-pressure-20261113')
NAMESPACE='crg-vendor-lab-high960-20261113'
RUN_ID='20261113960'
CORE_SHA='7f331574f797a96eaed11605164c8b7ef56927e457ee417b9ac12ebff15c8a38'
WORKER_SHA='bbb86c6af6c472674ebf108686052d5676207b8470b69dbf34fdeb5197cff29b'
SHIM_SHA='92d7f4352d0f413efbed0e49495d4ad0ff36f74f617a2291173a7e36e28b06b2'
RECEIVER_SHA='83b52b5cbbbe14740c783bebe8c01264cd38ff9a3b1749429b3b106fe7a279c8'
HOOK_SHA='babb481f90262678416d276d7b81ab95a600a7fea53589266de1898ec50f1d4e'
VENDOR_HELPER_SHA='34aaab089f7f50bb24caf2ec8ca50b256ddb35594355e1d7b41f2323e8a8b856'
PREFIX=b'CRG_TRANSPORT_V1 '
class Rejected(Exception):pass
def require(value,reason):
    if not value:raise Rejected(reason)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def private_json(path,value,maximum=8*1024*1024):
    raw=(json.dumps(value,separators=(',',':'))+'\n').encode()
    require(len(raw)<=maximum,'SUMMARY_OUTPUT_BOUND')
    with Path(path).open('xb') as stream:
        os.chmod(path,0o600);stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return artifact(path,maximum)
def artifact(path,maximum=32*1024*1024):
    path=Path(path);before=path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=maximum,'PRIVATE_ARTIFACT_SHAPE')
    fd=os.open(str(path),os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
    with os.fdopen(fd,'rb') as stream:
        current=os.fstat(stream.fileno());require((current.st_dev,current.st_ino)==(before.st_dev,before.st_ino),'ARTIFACT_IDENTITY')
        digest=hashlib.sha256();size=0
        while True:
            chunk=stream.read(min(1024*1024,maximum+1-size))
            if not chunk:break
            digest.update(chunk);size+=len(chunk);require(size<=maximum,'ARTIFACT_READ_BOUND')
    after=path.lstat();require((after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)==(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) and size==before.st_size,'ARTIFACT_CHANGED')
    return {'filename':path.name,'bytes':size,'sha256':digest.hexdigest()}
def native_command(role,run_id):
    return 'CRG_VENDOR_SOAK_TEST=disposable-loopback-only CRG_VENDOR_NATIVE_DIAGNOSTICS=qualified-disposable-loopback-only CRG_PG_WAIT=authorized-disposable-readonly-only python /tmp/crg-business-reload-'+run_id+'.py --run-id '+run_id+' --seconds 600 --test-phase smoke'
def augment_native_call(args,namespace,role,run_id,shim_directory):
    expected=['kubectl','exec','-n',namespace,role+'-business','-c',role,'--','su','-','postgres','-c',native_command(role,run_id)]
    if args!=expected:return args,False
    require(shim_directory=='/tmp/crg-transport-'+run_id,'FIXED_SHIM_PATH')
    result=list(args)
    result[-1]='PYTHONDONTWRITEBYTECODE=1 CRG_VENDOR_TRANSPORT=qualified-disposable-loopback-only CRG_VENDOR_TRANSPORT_FIFO='+shlex.quote(shim_directory+'/annotations.fifo')+' PYTHONPATH='+shlex.quote(shim_directory)+'${PYTHONPATH:+:$PYTHONPATH} '+result[-1]
    return result,True
def read_annotations(path,run_id):
    raw=Path(path).read_bytes();require(len(raw)<=1024*1024,'ANNOTATION_LOG_BOUND');rows=[]
    for line in raw.splitlines():
        if not line.startswith(PREFIX):continue
        require(len(line)+1<=512 and len(rows)<1024,'ANNOTATION_RECORD_BOUND')
        value=json.loads(line[len(PREFIX):]);require(value['run_id']==run_id and value['kind']=='urlopen-headers','ANNOTATION_SCOPE');rows.append(value)
    return rows
def associate_requests(stream,native_requests,annotations,run_id):
    requests=[v for v in native_requests if v['kind']=='api'];by_iteration={}
    for value in annotations:
        require(value['run_id']==run_id and type(value['iteration']) is int and value['iteration']>=0,'ANNOTATION_ITERATION')
        require(value['iteration'] not in by_iteration,'DUPLICATE_ANNOTATION_ITERATION');by_iteration[value['iteration']]=value
    rows=[]
    for request in requests:
        annotation=by_iteration.get(request['iteration']);began=int(request['started_monotonic']*1e9);ended=int(request['ended_monotonic']*1e9)
        row={'native_request':request,'transport':annotation,'business_success':request['success'],'full_original_request_started_ns':began,'full_original_request_ended_ns':ended,'causal_attribution_accepted':False}
        valid=bool(annotation and annotation.get('socket_timeout_seconds')==4 and began<=annotation.get('started_monotonic_ns',-1)<=annotation.get('finished_monotonic_ns',-1)<=ended and type(annotation.get('local_port')) is int and 0<annotation['local_port']<65536 and annotation.get('server_port')==8090)
        row['annotation_complete_within_original_request']=valid
        selected=[]
        if valid:
            for pair in stream.get('pairs',[]):
                meta=pair['entry'].get('fd_metadata',{});stamp=pair['entry']['monotonic_ns']
                if pair['entry']['call'] in ['recvfrom','sendto','write'] and meta.get('source')=='event-time-safe-kernel-metadata' and meta.get('remote_port')==annotation['local_port'] and meta.get('local_port')==8090 and began<=stamp:
                    selected.append(pair)
        row['receive_pairs_within_original_request']=sum(v['entry']['call']=='recvfrom' and v['entry']['monotonic_ns']<=ended for v in selected)
        row['send_pairs_within_original_request']=sum(v['entry']['call'] in ['sendto','write'] and v['exit'].get('return',0)>0 and v['entry']['monotonic_ns']<=ended for v in selected)
        # Preserve late records as diagnostics. They never make a timed-out
        # native request successful and do not prove a particular write caused it.
        row['same_ports_after_original_end']=[p for p in selected if p['entry']['monotonic_ns']>ended] if not request['success'] else []
        rows.append(row)
    return {'requests':rows,'original_API_requests':len(requests),'annotations':len(annotations),'every_API_has_one_complete_annotation':len(requests)==len(annotations) and len({v['iteration'] for v in requests})==len(requests) and all(v['annotation_complete_within_original_request'] for v in rows),'every_successful_API_has_exact_receive_and_send_in_original_window':bool(rows) and all(not v['business_success'] or v['receive_pairs_within_original_request']>0 and v['send_pairs_within_original_request']>0 for v in rows),'original_native_success_flags_unchanged':True,'late_same_ports_do_not_prove_same_socket_or_causality':True}

class ProcessProxy:
    def __init__(self,delegate,observer):self.delegate,self.observer=delegate,observer
    def __getattr__(self,name):return getattr(self.delegate,name)
    def Popen(self,args,*rest,**kwargs):
        chosen=args;owner=self.observer;matched=False
        try:
            chosen,matched=augment_native_call(args,owner.execution.ns,owner.role,owner.run_id,owner.shim_directory)
            if matched:
                owner.record['native_launch_count']=owner.record.get('native_launch_count',0)+1
                owner.record['native_source_unchanged']=True;owner.record['annotation_env_added_only_to_exact_native_command']=True
        except Exception as exc:
            owner.record.setdefault('diagnostic_errors',[]).append({'action':'native-command-annotation','error_class':type(exc).__name__});owner.record['diagnostic_failed']=True
            chosen=args
        # The real Popen call is outside the diagnostic catch. Its original
        # exception is propagated once, with no fallback launch or retry.
        child=self.delegate.Popen(chosen,*rest,**kwargs)
        if matched:
            try:owner.remember_native_child(child)
            except Exception as exc:
                # A diagnostic must never retry the original launch, replace
                # the returned child, or replace the business exception.
                try:
                    owner.record.setdefault('diagnostic_errors',[]).append({'action':'capture-original-native-child','error_class':type(exc).__name__});owner.record['diagnostic_failed']=True
                except Exception:pass
        return child

class Observer:
    def __init__(self,core,helper,execution,role,folder,group,row,record):
        self.core,self.helper,self.execution,self.role=core,helper,execution,role
        self.folder,self.group,self.row,self.record=Path(folder),Path(group),row,record
        self.run_id=execution.plan['run_id']+('0' if role=='dbs' else '1');self.shim_directory='/tmp/crg-transport-'+self.run_id
        self.capture={'BPF_sessions':{}};self.sessions=[];self.collector=None;self.proxy=None;self.delegate=None;self.finished=False;self.channel=None;self.transport_annotations=None;self.native_child=None;self.native_child_capture_count=0
    def remember_native_child(self,child):
        self.native_child_capture_count+=1
        require(self.native_child is None,'MULTIPLE_ORIGINAL_NATIVE_CHILDREN')
        require(child is not None,'MISSING_ORIGINAL_NATIVE_CHILD')
        self.native_child=child
    def original_native_exited(self):
        # The business method deliberately clears execution.worker after
        # checking the original exit status. Retain the actual Popen object;
        # never infer this child's identity from a mutable business slot.
        status={'captured':self.native_child is not None,'capture_count':self.native_child_capture_count,'exited':False,'pid':None,'exit_code':None}
        if self.native_child is not None:
            try:
                status['pid']=self.native_child.pid;status['exit_code']=self.native_child.poll();status['exited']=status['exit_code'] is not None
            except Exception as exc:
                self.record.setdefault('diagnostic_errors',[]).append({'action':'poll-original-native-child','error_class':type(exc).__name__});self.record['diagnostic_failed']=True
        self.record['original_native_child']=status
        return status['capture_count']==1 and status['exited']
    def save(self):
        projected={}
        for name,value in self.capture['BPF_sessions'].items():
            target={k:v for k,v in value.items() if k!='report'};stream=value.get('report')
            if stream is not None:
                output=self.execution.root/(self.role+'-'+name+'-bpf.json');target['report_artifact']=artifact(output)
                target['summary']={k:stream.get(k) for k in ['phase','reason','target_pid','target_start_ticks','cgroup_id','program_ids','control_program_ids','map_ids','perf_lost_samples','bpf_output_failures','incomplete','diagnostic_errors','cleanup_errors','all_owned_handles_closed','detached_stream_drained_to_deadline','stage_scope_errors','stage_scope_remaining_entries','perf_mapped_budget','perf_mapped_budget_after_drain','collector_maxrss_kB','collector_cpu_seconds','elapsed_seconds','function_pair_issues']}
                if stream.get('admission') is not None:
                    target['summary']['admission']={k:v for k,v in stream['admission'].items() if k not in ['admitted_syscall_pairs','admitted_function_pairs']}
                target['summary'].update(events=len(stream.get('events') or []),syscall_pairs=len(stream.get('pairs') or []),function_pairs=len(stream.get('function_pairs') or []),hook_count=len(stream.get('hooks') or []))
            projected[name]=target
        self.record['sessions']=projected;self.execution.save()
    def diagnostic_check(self,name,passed):
        self.record.setdefault('checks',[]).append({'name':name,'passed':bool(passed)})
        if not passed:
            self.record['diagnostic_failed']=True
            self.record.setdefault('diagnostic_errors',[]).append({'action':name,'error_class':'DiagnosticCheckFailed'})
    def start(self):
        require(self.execution.ns==NAMESPACE and self.execution.root==ROOT and self.role in ['dbs','hisdbs'],'FIXED_FULL_PRESSURE_SCOPE')
        meta,cid,init,actual=self.execution.identity(self.role);require(actual==self.group,'FIXTURE_LEAF')
        nsmeta=json.loads(self.execution.run(['kubectl','get','namespace',self.execution.ns,'-o','json']).stdout)
        listener=self.core.session.listener_owner(self.group);related=self.execution.processes(self.group,'/opt/dbs/bin/'+self.role)
        require(1<=len(related)<=2 and listener['executable_sha256']==self.helper.VENDOR_SHA and listener['executable_path']=='/opt/dbs/bin/'+self.role and any(v[0]==listener['pid'] for v in related),'EXACT_VENDOR_LISTENER')
        target=self.helper.identity(listener['pid']);owner=self.helper.identity(os.getpid());init_info=self.helper.identity(init)
        scope={'namespace':NAMESPACE,'namespace_uid':nsmeta['metadata']['uid'],'pod':self.role+'-business','pod_uid':meta['metadata']['uid'],'container_id':cid,'role':self.role,'fixture_root':str(self.folder),'container_init_pid':init,'container_init_start_ticks':init_info['start_ticks']}
        plan={'owner_pid':owner['pid'],'owner_start_ticks':owner['start_ticks'],'pid':target['pid'],'start_ticks':target['start_ticks'],'executable_sha256':self.helper.VENDOR_SHA,'cgroup':target['cgroup'],'maximum_seconds':1200,'qualification_reader_delay_milliseconds':0,'vendor_fixture':scope}
        self.record.update(phase='starting',scope=scope,selected_vendor_listener=listener,planned_maximum_seconds=1200)
        context={'root':self.execution.root,'role':self.role,'row':self.capture,'save':self.save}
        pre=self.helper.Collector(context,'full-readonly-preflight',plan);self.sessions.append(pre)
        require(not pre.launch(False),'READONLY_PREFLIGHT_EXECUTED');stream=pre.finish()
        require(stream['phase']=='preflight-readonly' and stream['owned_vendor_fixture_validated'] and len(stream['hooks'])==40 and not stream.get('program_ids') and not stream.get('map_ids'),'FULL_SCOPE_PREFLIGHT')
        raw=(TOOLS/'sitecustomize.py').read_bytes();require(sha(raw)==SHIM_SHA,'FROZEN_TRANSPORT_SHIM')
        receiver=load('native-private-fifo.py',RECEIVER_SHA)
        uid=int(self.execution.ex(self.role,'id','-u','postgres').stdout.strip());gid=int(self.execution.ex(self.role,'id','-g','postgres').stdout.strip())
        def same_container():
            current=self.helper.identity(init)
            return current['start_ticks']==init_info['start_ticks'] and current['cgroup']==init_info['cgroup'] and self.group.exists()
        self.channel=receiver.Channel(Path('/proc',str(init),'root/tmp'),self.run_id,uid,gid,raw,same_container)
        self.channel.prepare();self.channel.start();self.record['transport_channel']=self.channel.status()
        require(self.execution.ex(self.role,'sha256sum',self.shim_directory+'/sitecustomize.py').stdout.split()[0]==SHIM_SHA,'TRANSPORT_SHIM_COPY')
        self.delegate=self.core.subprocess;self.proxy=ProcessProxy(self.delegate,self);self.core.subprocess=self.proxy
        collector=self.helper.Collector(context,'full600',plan);self.sessions.append(collector);self.collector=collector
        require(collector.launch(True),'FULL_COLLECTOR_READY');self.record['phase']='collecting';self.save()
    def stop_session(self,session):
        try:return session.finish()
        except Exception:
            child=session.child
            if child is not None and child.poll() is None:
                expected=session.record.get('identity',{});actual=self.helper.identity(child.pid)
                require(actual['pid']==expected.get('pid') and actual['start_ticks']==expected.get('start_ticks'),'OWN_COLLECTOR_IDENTITY_BEFORE_STOP')
                self.record['forced_own_collector_cleanup']=True;child.terminate()
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    actual=self.helper.identity(child.pid);require(actual['start_ticks']==expected['start_ticks'],'OWN_COLLECTOR_IDENTITY_BEFORE_KILL');child.kill();child.wait(timeout=5)
            raise
        finally:
            if session.child is not None and session.child.poll() is not None:
                try:
                    if session.out.exists():session.record['raw_output_artifact']=artifact(session.out)
                    stdout=session.child.stdout.read(8193);require(len(stdout)<=8192,'COLLECTOR_TERMINAL_BOUND');session.record['terminal_stdout']=stdout
                except Exception as exc:self.record.setdefault('diagnostic_errors',[]).append({'action':'collector-terminal-metadata','error_class':type(exc).__name__})
    def finish_channel(self):
        if self.channel is None:return
        primary=None
        try:
            self.channel.stop();raw=self.channel.raw();require(len(raw)<=1048576,'ANNOTATION_CHANNEL_BOUND')
            path=self.execution.root/(self.role+'-transport-annotations.jsonl')
            with path.open('xb') as output:os.chmod(path,0o600);output.write(raw);output.flush();os.fsync(output.fileno())
            self.record['annotation_artifact']=artifact(path,1048576)
            self.transport_annotations=self.channel.annotations()
        except Exception as exc:
            primary=exc;self.record.setdefault('diagnostic_errors',[]).append({'action':'transport-stop-or-export','error_class':type(exc).__name__})
        finally:
            try:self.channel.cleanup()
            except Exception as exc:
                if primary is None:primary=exc
                self.record.setdefault('diagnostic_errors',[]).append({'action':'transport-cleanup','error_class':type(exc).__name__})
            self.record['transport_channel']=self.channel.status()
        if primary is not None:raise primary

    def finish(self):
        if self.finished:return
        self.finished=True;primary=None;stream=None
        try:
            for session in reversed(self.sessions):
                try:
                    value=self.stop_session(session)
                    if session is self.collector:stream=value
                except Exception as exc:
                    if primary is None:primary=exc
                    self.record.setdefault('diagnostic_errors',[]).append({'action':'collector-stop','error_class':type(exc).__name__})
        finally:
            if self.proxy is not None:
                if self.core.subprocess is self.proxy:self.core.subprocess=self.delegate
                else:self.record.setdefault('diagnostic_errors',[]).append({'action':'restore-subprocess-proxy','error_class':'ConcurrentReplacement'})
        try:self.finish_channel()
        except Exception as exc:
            if primary is None:primary=exc
        if stream is not None:
            # Always save original report metadata and paired stages before
            # considering port association or diagnostic acceptance.
            context={'role':self.role,'row':self.capture,'save':self.save}
            self.helper.persist_paired_function_summary(context,stream)
            diagnostics={'paired_wait_timing':self.capture['paired_wait_timing'],'iomap_stage_timing':self.capture['iomap_stage_timing']}
            try:
                require(self.transport_annotations is not None,'CHANNEL_ANNOTATIONS_UNAVAILABLE');annotations=self.transport_annotations
                native_path=self.execution.root/(self.role+'-native-diagnostics.json');raw=native_path.read_bytes();require(len(raw)<=8*1024*1024,'ORIGINAL_NATIVE_DIAGNOSTIC_BOUND');native=json.loads(raw)
                require(native['run_id']==self.run_id and native['worker_sha256']==WORKER_SHA,'ORIGINAL_NATIVE_DIAGNOSTIC_SCOPE')
                diagnostics.update(original_native_diagnostic_artifact=artifact(native_path,8*1024*1024),annotations=annotations,request_associations=associate_requests(stream,native['requests'],annotations,self.run_id))
            except Exception as exc:
                diagnostics['request_annotation_error_class']=type(exc).__name__;self.diagnostic_check('full-original-request-annotations-available',False)
            stages=diagnostics['iomap_stage_timing'];paired=diagnostics['paired_wait_timing']
            self.diagnostic_check('full-stream-zero-loss-paired-scope-and-clean-detach',stream['phase']=='collected' and stream.get('reason')=='controller-stdin' and not stream['incomplete'] and stream['perf_lost_samples']==stream['bpf_output_failures']==stream['stage_scope_errors']==stream['stage_scope_remaining_entries']==0 and not stream['function_pair_issues'] and stream['all_owned_handles_closed'] and stream['detached_stream_drained_to_deadline'])
            admission=stream.get('admission') or {}
            self.diagnostic_check('full-admitted-window-raw-flags-and-bounded-drain',admission.get('admitted_calls_quiesced_before_detach') is True and admission.get('drain_timed_out') is False and admission.get('maximum_admission_drain_milliseconds')==1000 and admission.get('admission_errors')==admission.get('probe_invocations_in_flight_after_detach')==admission.get('retained_raw_invalid_events')==0 and admission.get('admitted_stream_incomplete') is False and admission.get('kernel_boundary_event_counter')==admission.get('retained_raw_boundary_events')==sum(v.get('admission_boundary')=='boundary' for v in stream['events']))
            self.diagnostic_check('full-actual40-hooks-one-control-program-seven-maps',len(stream.get('program_ids') or [])==40 and len(stream.get('control_program_ids') or [])==1 and len(stream.get('map_ids') or [])==7)
            self.diagnostic_check('full-stage-timing-seven-required-and-precise-scope',paired['all_observed_positive_log_writes_have_paired_xfs_and_iomap'] and stages['all_eligible_log_writes_have_seven_required_stages'] and stages['all_scoped_function_pairs_within_exact_eligible_syscall'])
            budget=stream.get('perf_mapped_budget') or {}
            self.diagnostic_check('full-measured-perf-mmap-budget-stable-after-drain',bool(budget) and budget==stream.get('perf_mapped_budget_after_drain') and 0<budget.get('actual_mapped_bytes',0)<=16777216 and stream.get('collector_maxrss_kB',0)>0)
            association=diagnostics.get('request_associations',{})
            self.diagnostic_check('full-request-ports-in-original-business-windows',association.get('every_API_has_one_complete_annotation',False) and association.get('every_successful_API_has_exact_receive_and_send_in_original_window',False))
            self.diagnostic_check('one-native-command-annotated-no-forced-collector-cleanup',self.record.get('native_launch_count')==1 and not self.record.get('forced_own_collector_cleanup'))
            channel=self.record.get('transport_channel') or {}
            self.diagnostic_check('private-transport-channel-bounded-cleaned-and-original-native-exited',channel.get('started') and channel.get('stopped') and channel.get('reader_closed') and not channel.get('thread_alive') and channel.get('cleaned') and channel.get('directory_fd_closed') and channel.get('parent_fd_closed') and not channel.get('incomplete',True) and self.original_native_exited())
            try:
                terminal=json.loads(self.collector.record['terminal_stdout'].strip());descriptor=self.collector.record['raw_output_artifact']
                written=terminal['phase']=='finished' and terminal['complete_report_written'] and terminal['intended_report_bytes']==descriptor['bytes'] and terminal['report_limit_bytes']==33554432
            except Exception:written=False
            self.diagnostic_check('full-report-durable-complete-terminal-and-exact-file-bytes',written)
            diagnostics['checks']=self.record['checks'];self.record['summary_artifact']=private_json(self.execution.root/(self.role+'-full600-summary.json'),diagnostics)
        self.record['phase']='collected' if stream is not None else 'not-collected';self.save()
        if primary is not None:raise primary

def load(name,digest):
    path=TOOLS/name;require(sha(path.read_bytes())==digest,'FROZEN_INTEGRATION_HELPER')
    spec=importlib.util.spec_from_file_location(name.replace('-','_'),path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def install(core):
    require(sha(Path(core.__file__).read_bytes())==CORE_SHA,'ORIGINAL_PRESSURE_CORE_CHANGED')
    require(not getattr(core.PressureExecution,'_crg_full_pressure_observer_installed',False),'DUPLICATE_FULL_OBSERVER')
    hook=load('full-pressure-hook.py',HOOK_SHA);helper=load('vendor-diagnostic.py',VENDOR_HELPER_SHA)
    original_init=core.PressureExecution.__init__
    def initialize(self,*args,**kwargs):
        original_init(self,*args,**kwargs);self.plan['run_id']=RUN_ID
    original=hook.install(core,lambda execution,role,folder,group,row,record:Observer(core,helper,execution,role,folder,group,row,record))
    core.PressureExecution.__init__=initialize
    core._crg_original_business_method=original
    return original

def verify_preconditions(plan,report,run):
    contract=plan['full_pressure_diagnostic_contract']
    for label in ['own56','report_output','transport_images']:
        requirement=contract['prerequisites'][label];raw=Path(requirement['path']).read_bytes();require(sha(raw)==requirement['sha256'],'EXACT_DIAGNOSTIC_PREREQUISITE_'+label)
        value=json.loads(raw);require(value['phase']=='passed','DIAGNOSTIC_PREREQUISITE_PHASE_'+label)
        require(len(value['checks'])==requirement['checks'] and all(v['passed'] for v in value['checks']),'DIAGNOSTIC_PREREQUISITE_CHECKS_'+label)
    require(plan['criteria']['native_seconds_each_role']==600 and plan['criteria']['main_checks']==32 and plan['criteria']['maximum_errors']==0,'ORIGINAL_FULL_PRESSURE_CRITERIA')
    require(contract['original_core_sha256']==CORE_SHA and contract['original_native_worker_sha256']==WORKER_SHA,'ORIGINAL_WORKLOAD_SOURCE')
    old_root=Path('/var/tmp/crg-high638-pressure-20261112');prior=json.loads((old_root/'report.json').read_bytes());exit_value=json.loads(Path('/var/tmp/crg-high638-tools-20261112/exit.json').read_bytes())
    require(prior['phase']=='failed' and len(prior['tests'])==26 and exit_value['exit']==1 and prior['namespace_absent'],'ORIGINAL_FULL_PRESSURE_ATTEMPT5_FAILURE')
    for value in prior['roles'].values():
        native=value['native'];require(native['requested_duration_seconds']==600 and native['elapsed_seconds']>=600 and native['sql']['errors']==0 and native['api']['errors']==1,'ORIGINAL_FULL_PRESSURE_API_FAILURES')
        require(value['own_leaf_absent'] and value['own_parent_absent'] and value['original_config_and_profile_absence_restored'],'PREVIOUS_FULL_FIXTURE_CLEANUP')
    require(not run(['kubectl','get','namespace','crg-vendor-lab-high638-20261112','--ignore-not-found','-o','json']).stdout.strip(),'PREVIOUS_FULL_NAMESPACE_PRESENT')
    previous=contract['previous_full817_failure'];raw=Path(previous['report_path']).read_bytes();require(sha(raw)==previous['report_sha256'],'EXACT_ORIGINAL_FULL817_REPORT')
    old=json.loads(raw);require(old['phase']=='failed' and old['namespace_absent'] and len(old['tests'])==29 and all(v['passed'] for v in old['tests']),'ORIGINAL_FULL817_FAILURE_RETAINED')
    require(old['job_sha256']==previous['job_sha256'] and old['plan_sha256']==previous['plan_sha256'],'ORIGINAL_FULL817_JOB_IDENTITY')
    terminal=json.loads(Path('/var/tmp/crg-high817-tools-20261112/exit.json').read_bytes());require(terminal['exit']==1 and terminal['artifact_index_complete'],'PREVIOUS_FULL817_TERMINAL')
    for name,value in old['roles'].items():
        native=value['native'];require(native['elapsed_seconds']>=600 and native['requested_duration_seconds']==600 and native['sql']['errors']==0 and native['api']['errors']==(2 if name=='v10-dbs-bw64' else 0) and len(value['reload_intervals'])==11,'ORIGINAL_FULL817_BUSINESS_FAILURE_AND_FULL_WORKLOAD')
        require(value['own_leaf_absent'] and value['own_parent_absent'] and value['original_config_and_profile_absence_restored'],'PREVIOUS_FULL817_CLEANUP')
        require(any(v['action']=='start' and v['error_class']=='TypeError' for v in value['full_BPF_diagnostic']['diagnostic_errors']),'ORIGINAL_FULL817_NULL_PREFLIGHT_FAILURE')
    require(not run(['kubectl','get','namespace','crg-vendor-lab-high817-20261112','--ignore-not-found','-o','json']).stdout.strip(),'PREVIOUS_FULL817_NAMESPACE_PRESENT')
    for label,requirement in contract['admission_prerequisites'].items():
        raw=Path(requirement['path']).read_bytes();require(len(raw)<=1048576 and sha(raw)==requirement['sha256'],'EXACT_ADMISSION_PREREQUISITE_'+label)
        value=json.loads(raw);require(value['phase']==requirement['phase'] and len(value['checks'])==requirement['checks'] and all(v['passed'] for v in value['checks']) and not value['forced_own_cleanup'],'ADMISSION_PREREQUISITE_RESULT_'+label)
        require(value['source_sha256']['direct-bpf']==requirement['qualified_ELF_sha256'],'ADMISSION_PREREQUISITE_ELF_'+label)
    require(all(sha((TOOLS/name).read_bytes())==digest for name,digest in contract['unchanged_qualified_Go_sources'].items()),'QUALIFIED_KERNEL_ADMISSION_SOURCES_CHANGED')
    previous831=contract['previous_full831_business_pass_diagnostic_failure'];raw=Path(previous831['report_path']).read_bytes();require(sha(raw)==previous831['report_sha256'],'EXACT_PREVIOUS_FULL831_REPORT')
    previous=json.loads(raw);require(previous['phase']=='passed' and len(previous['tests'])==32 and all(v['passed'] for v in previous['tests']) and previous['namespace_absent'],'PREVIOUS_FULL831_BUSINESS_RESULT_CHANGED')
    require(any(v.get('full_BPF_diagnostic',{}).get('diagnostic_failed') for v in previous['roles'].values()),'PREVIOUS_FULL831_DIAGNOSTIC_FAILURE_LOST')
    require(not run(['kubectl','get','namespace','crg-vendor-lab-high831-20261112','--ignore-not-found','-o','json']).stdout.strip(),'PREVIOUS_FULL831_NAMESPACE_PRESENT')
    previous930=contract['previous_full930_business_pass_private_cleanup_failure'];raw=Path(previous930['report_path']).read_bytes();require(sha(raw)==previous930['report_sha256'],'EXACT_PREVIOUS_FULL930_REPORT')
    value=json.loads(raw);require(value['phase']=='passed' and len(value['tests'])==32 and all(v['passed'] for v in value['tests']) and value['namespace_absent'] and len(value['roles'])==2 and all(any(c['name']=='private-transport-channel-bounded-cleaned-and-original-native-exited' and not c['passed'] for c in row['full_BPF_diagnostic']['checks']) for row in value['roles'].values()),'PREVIOUS_FULL930_BUSINESS_AND_CLEANUP_FAILURE_CHANGED')
    require(not run(['kubectl','get','namespace','crg-vendor-lab-high930-20261113','--ignore-not-found','-o','json']).stdout.strip(),'PREVIOUS_FULL930_NAMESPACE_PRESENT')
    prerequisite=contract['bytecode_and_export_prerequisite'];raw=Path(prerequisite['report_path']).read_bytes();require(len(raw)<=1048576 and sha(raw)==prerequisite['report_sha256'],'EXACT_BYTECODE_EXPORT_QUALIFICATION')
    value=json.loads(raw);require(value['phase']=='passed' and len(value['checks'])==22 and all(c['passed'] for c in value['checks']) and value['namespace_absent'] and value['source_sha256']==prerequisite['source_sha256'],'BYTECODE_EXPORT_QUALIFICATION_RESULT')
    require(not run(['kubectl','get','namespace','crg-vendor-lab-bytecode943-20261113','--ignore-not-found','-o','json']).stdout.strip(),'BYTECODE_QUALIFICATION_NAMESPACE_PRESENT')
    require(sha((TOOLS/'qualified-bytecode-factory943.py').read_bytes())==prerequisite['source_sha256']['factory.py'] and sha((TOOLS/'qualified-bytecode-export943.py').read_bytes())==prerequisite['source_sha256']['artifact-transfer.py'],'QUALIFIED_BYTECODE_FACTORY_AND_EXPORT_SOURCE_BINDING')
    previous950=contract['previous_full950_native_handle_check_failure'];raw=Path(previous950['report_path']).read_bytes();require(sha(raw)==previous950['report_sha256'],'EXACT_PREVIOUS_FULL950_REPORT')
    value=json.loads(raw);require(value['phase']=='passed' and len(value['tests'])==32 and all(c['passed'] for c in value['tests']) and value['namespace_absent'] and len(value['roles'])==2 and all(row['native_exit']==0 and row['full_BPF_diagnostic']['transport_channel']['cleaned'] and [c['name'] for c in row['full_BPF_diagnostic']['checks'] if not c['passed']]==['private-transport-channel-bounded-cleaned-and-original-native-exited'] for row in value['roles'].values()),'ORIGINAL_FULL950_BUSINESS_AND_DIAGNOSTIC_FAILURE_CHANGED')
    require(not run(['kubectl','get','namespace','crg-vendor-lab-high950-20261113','--ignore-not-found','-o','json']).stdout.strip(),'PREVIOUS_FULL950_NAMESPACE_PRESENT')
    prerequisite=contract['native_child_lifecycle_prerequisite'];raw=(TOOLS/'native-child-qualification.json').read_bytes();require(len(raw)<=1048576 and sha(raw)==prerequisite['report_sha256'],'EXACT_NATIVE_CHILD_QUALIFICATION')
    value=json.loads(raw);require(value['phase']=='passed' and len(value['checks'])==3 and all(c['passed'] for c in value['checks']) and len(value['results']['native-child15']['report']['cases'])==15 and value['results']['native-child15']['report']['all_own_child_handles_reaped_and_streams_closed'],'NATIVE_CHILD_LIFECYCLE_QUALIFICATION')
    require(sha((TOOLS/'qualified-native-child-factory958.py').read_bytes())==prerequisite['factory_sha256'] and sha((TOOLS/'native-child-unit.py').read_bytes())==prerequisite['unit_sha256'],'QUALIFIED_NATIVE_CHILD_FACTORY_SOURCE_BINDING')
    report['original_full950_failure_and_real_child15_qualification_retained']=True
    report['original_full930_failure_and_bytecode_export22_qualification_retained']=True
    report['original_full831_business_pass_and_diagnostic_failure_retained']=True
    report['original_full817_failure_retained']=True
    report['original_full_pressure_attempt5_failure_retained']=True;report['optional_full_diagnostic_contract']=contract
