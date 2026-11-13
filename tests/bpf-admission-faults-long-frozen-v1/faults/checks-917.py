from pathlib import Path
import datetime, hashlib, json, os, select, subprocess, sys, time, traceback

w=Path(__file__).parent; f=json.loads((w/'manifest.json').read_text()); root=Path(f['output']); root.mkdir(mode=0o700)
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def identity(pid):
    fields=Path('/proc',str(pid),'stat').read_bytes().rsplit(b')',1)[1].split()
    return {'pid':pid,'start_ticks':int(fields[19]),'parent_pid':int(fields[1]),'cgroup':Path('/proc',str(pid),'cgroup').read_text().strip()[3:]}
owner=identity(os.getpid()); (w/'worker.json').write_text(json.dumps(owner))
report={'schema':'crg-injected-own-admission-faults-v1','phase':'running','checks':[],'cases':{},'owned_processes':{},'source_sha256':f['source_sha256'],'forced_own_cleanup':False,'vendor_admission_qualified':False,'vendor_business_or_Pod_started':False}
children=[]
def save():(w/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
def check(name,value):
    report['checks'].append({'name':name,'passed':bool(value)}); save()
    assert value,name
def alive(row):
    try:return identity(row['pid'])['start_ticks']==row['start_ticks']
    except (FileNotFoundError,ProcessLookupError):return False
buffers={}
def message(p,timeout=5):
    deadline=time.monotonic()+timeout; key=id(p); data=buffers.get(key,b'')
    while b'\n' not in data:
        remaining=deadline-time.monotonic(); assert remaining>0 and select.select([p.stdout],[],[],remaining)[0],'owned child message timeout'
        chunk=os.read(p.stdout.fileno(),4096); assert chunk,'owned child ended before message';data+=chunk;assert len(data)<=32768
    line,rest=data.split(b'\n',1);buffers[key]=rest;assert 0<len(line)<=16384;return json.loads(line)
def send(p,command):p.stdin.write(command+'\n');p.stdin.flush()
def syscall_state(target,tid,fd=None):
    until=time.monotonic()+5
    while time.monotonic()<until:
        fields=Path('/proc',str(target.pid),'task',str(tid),'syscall').read_text().split()
        if fields and fields[0]!='running':
            number=int(fields[0],0)
            if fd is not None and number==1 and int(fields[1],0)==fd and int(fields[3],0)==4096:
                return {'observed_monotonic_ns':time.monotonic_ns(),'syscall_number':number,'fd':fd,'count':4096,'tid':tid,'verified_blocked_write':True}
            if fd is None and number==0 and int(fields[1],0)==0:
                return {'observed_monotonic_ns':time.monotonic_ns(),'syscall_number':number,'fd':0,'tid':tid,'verified_waiting_for_next_own_command':True}
        time.sleep(.005)
    raise AssertionError('exact owned syscall state not observed')
def target(name):
    p=subprocess.Popen([sys.executable,str(root/'own-http-with-blocked-pipe.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
    row=identity(p.pid); report['owned_processes'][name+'-probe']=row; children.append(('probe',p,row)); hello=message(p); assert hello['phase']=='ready' and hello['pid']==p.pid
    return p,hello,row
def collector(name,variant,p,target_identity,pause=0):
    plan={'owner_pid':owner['pid'],'owner_start_ticks':owner['start_ticks'],'pid':p.pid,'start_ticks':target_identity['start_ticks'],'executable_sha256':sha(Path('/proc',str(p.pid),'exe').read_bytes()),'probe_path':str(root/'own-http-with-blocked-pipe.py'),'probe_sha256':f['source_sha256']['probe.py'],'cgroup':target_identity['cgroup'],'maximum_seconds':15,'qualification_pair_attach_pause_milliseconds':pause,'qualification_closing_progress':True}
    plan_path=root/(name+'-plan.json'); plan_path.write_text(json.dumps(plan)+'\n'); plan_path.chmod(0o600)
    output=root/(name+'-stream.json'); env=os.environ.copy(); env['CRG_DIRECT_BPF']='authorized-disposable-loopback-only'
    q=subprocess.Popen([str(w/'direct-bpf'),'--plan',str(plan_path),'--output',str(output),'--execute'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1,env=env)
    row=identity(q.pid); report['owned_processes'][name+'-collector']=row; children.append(('collector',q,row)); report['cases'][name]={'variant':variant,'plan':plan,'probe_identity':target_identity,'collector_identity':row};save()
    return q,output
def ready(name,q,p,with_gap):
    first=message(q,8); row=report['cases'][name]
    if with_gap:
        assert first['phase']=='qualification-pair-enter-attached' and first['pause_milliseconds']==500
        row['gap']=first; send(p,'burst'); row['pre']=message(p)
        assert row['pre']['phase']=='burst-finished' and row['pre']['end_ns']<first['observed_monotonic_ns']+500000000
        first=message(q,8)
    assert first['phase']=='ready',first
    row['ready']=first; save()
def begin_closing(name,q):
    q.stdin.close(); closing=message(q,3);assert closing['phase']=='admission-closing';report['cases'][name]['closing']=closing;save()
def finish_collector(name,q,output,already_closing=False):
    if not already_closing:begin_closing(name,q)
    terminal=message(q,5);report['cases'][name]['terminal_observed_monotonic_ns']=time.monotonic_ns();q.wait(timeout=5);stdout=q.stdout.read(16385);stderr=q.stderr.read(16385);assert not buffers.get(id(q)) and not stdout and len(stderr)<=16384
    raw=output.read_bytes();assert len(raw)<=32*1024*1024;r=json.loads(raw);row=report['cases'][name]
    row.update(collector_exit=q.returncode,terminal=terminal,stderr_utf8=stderr,stream={'path':output.name,'bytes':len(raw),'sha256':sha(raw)},summary={k:r.get(k) for k in ['phase','reason','incomplete','function_pair_issues','perf_lost_samples','bpf_output_failures','stage_scope_errors','stage_scope_remaining_entries','program_ids','control_program_ids','map_ids']});save()
    a=r.get('admission',{})
    check(name+':actual-hooks-bounds-explicit-fault-reporting-and-cleanup',q.returncode==0 and not stderr and terminal['complete_report_written'] and r['phase']=='collected' and r['all_hooks_attached_before_ready'] and r['all_owned_handles_closed'] and not r['diagnostic_errors'] and not r['cleanup_errors'] and r['perf_lost_samples']==r['bpf_output_failures']==r['stage_scope_errors']==r['stage_scope_remaining_entries']==0 and len(r['program_ids'])==40 and len(r['control_program_ids'])==1 and len(r['map_ids'])==7 and r['perf_mapped_budget']['actual_mapped_bytes']==r['perf_mapped_budget_after_drain']['actual_mapped_bytes']<=16*1024*1024 and a['closing_requested'] and a['probe_invocations_in_flight_after_detach']==0 and a['kernel_boundary_event_counter']==a['retained_raw_boundary_events'] and ((a['admission_errors']>0 and a['retained_raw_invalid_events']>0) if name in ['capacity-full','depth-overflow','syscall-active-mismatch'] else (a['admission_errors']==0 and not a['retained_raw_invalid_events'])))
    return r
def finish_probe(name,p):
    send(p,'finish');p.wait(timeout=5);extra=p.stdout.read(16385);err=p.stderr.read(16385);check(name+':probe-natural-exit-and-private-write-file-cleaned',p.returncode==0 and not extra and not err and not buffers.get(id(p)) and not (root/('write-'+str(p.pid)+'.data')).exists())
def in_window(events,burst):return [e for e in events if burst['begin_ns']<=e['monotonic_ns']<=burst['end_ns']]
import ctypes, errno, struct

class MapOperation(ctypes.Structure):
    _fields_=[('fd',ctypes.c_uint32),('padding',ctypes.c_uint32),('key',ctypes.c_uint64),('value',ctypes.c_uint64),('flags',ctypes.c_uint64)]

class OwnedMapFault:
    def __init__(self,name,p,q):
        assert os.uname().machine=='x86_64'
        self.name=name;self.p=p;self.q=q;self.fd=None
        self.case=report['cases'][name];self.map_id=None
        self.lib=ctypes.CDLL(None,use_errno=True);self.lib.syscall.restype=ctypes.c_long
        self.guard()
        ids=set(self.case['ready']['map_ids']);assert len(ids)==7
        matches=[]
        for candidate in ids:
            result=subprocess.run(['bpftool','-j','map','show','id',str(candidate)],capture_output=True,timeout=3)
            assert result.returncode==0 and not result.stderr and len(result.stdout)<=16384
            value=json.loads(result.stdout)
            if isinstance(value,list):assert len(value)==1;value=value[0]
            assert value['id']==candidate
            if value['name']=='crg901_admit':
                assert value['type']=='hash' and value['bytes_key']==value['bytes_value']==16 and value['max_entries']==1024
                matches.append(value)
        assert len(matches)==1
        self.map_id=matches[0]['id'];self.case['owned_fault_map_metadata']=matches[0]
        self.guard()
        attributes=(ctypes.c_uint32*3)(self.map_id,0,0)
        fd=self.lib.syscall(321,14,ctypes.byref(attributes),ctypes.sizeof(attributes))
        assert fd>=0,('map get fd',ctypes.get_errno())
        self.fd=fd
        try:self.guard()
        except BaseException:os.close(self.fd);self.fd=None;raise
        check(name+':fault-map-FD-bound-to-live-owned-exact-collector',True)

    def guard(self):
        row=self.case['collector_identity'];target=self.case['probe_identity']
        assert self.q.poll() is None and self.p.poll() is None and alive(row) and alive(target)
        assert row['parent_pid']==target['parent_pid']==owner['pid']
        assert sha(Path('/proc',str(self.q.pid),'exe').read_bytes())==f['source_sha256']['direct-bpf']
        assert Path('/proc',str(self.p.pid),'cmdline').read_bytes().split(b'\0')[:2]==[os.fsencode(sys.executable),os.fsencode(root/'own-http-with-blocked-pipe.py')]
        if self.map_id is not None:
            owned=set()
            for entry in Path('/proc',str(self.q.pid),'fdinfo').iterdir():
                try:lines=entry.read_text().splitlines()
                except FileNotFoundError:continue
                owned.update(int(v.split(':',1)[1].strip()) for v in lines if v.startswith('map_id:'))
            assert self.map_id in owned
        if self.fd is not None:
            held=Path('/proc/self/fdinfo',str(self.fd)).read_text().splitlines()
            assert [int(v.split(':',1)[1].strip()) for v in held if v.startswith('map_id:')]==[self.map_id]

    def call(self,command,key,value=None,flags=0):
        assert self.fd is not None and len(key)==16
        assert int.from_bytes(key[:8],'little')>>32==self.p.pid and int.from_bytes(key[8:],'little')>0
        k=ctypes.create_string_buffer(key);v=ctypes.create_string_buffer(value if value is not None else b'\0'*16)
        assert value is None or len(value)==16
        attributes=MapOperation(self.fd,0,ctypes.addressof(k),ctypes.addressof(v),flags)
        result=self.lib.syscall(321,command,ctypes.byref(attributes),ctypes.sizeof(attributes))
        if result<0:raise OSError(ctypes.get_errno(),os.strerror(ctypes.get_errno()))
        return bytes(v.raw[:16])

    def update(self,key,value,flags=0):
        self.guard();self.call(2,key,value,flags)

    def delete(self,key):
        self.guard();self.call(3,key)

    def snapshot(self):
        self.guard();rows=[];previous=None
        while True:
            k=ctypes.create_string_buffer(previous) if previous is not None else None
            nxt=ctypes.create_string_buffer(16)
            attributes=MapOperation(self.fd,0,ctypes.addressof(k) if k is not None else 0,ctypes.addressof(nxt),0)
            result=self.lib.syscall(321,4,ctypes.byref(attributes),ctypes.sizeof(attributes))
            if result<0:
                assert ctypes.get_errno()==errno.ENOENT;break
            key=bytes(nxt.raw[:16]);value=self.call(1,key)
            assert not any(v['key_hex']==key.hex() for v in rows) and len(rows)<1024
            rows.append({'key_hex':key.hex(),'value_hex':value.hex()});previous=key
        return sorted(rows,key=lambda v:v['key_hex'])

    def close(self):
        if self.fd is not None:os.close(self.fd);self.fd=None

def key_for(pid,tid,start):return struct.pack('<QQ',(pid<<32)|tid,start)
def value_for(syscall=0,depth=0):return struct.pack('<IIQ',syscall,depth,0)

def primed(name,p,hello,m):
    send(p,'burst');row=message(p);assert row['phase']=='burst-finished' and len(row['calls'])==32
    report['cases'][name]['prime_burst']=row
    syscall_state(p,hello['tid'])
    snapshot=m.snapshot();assert len(snapshot)==1
    key=bytes.fromhex(snapshot[0]['key_hex']);value=bytes.fromhex(snapshot[0]['value_hex'])
    assert int.from_bytes(key[:8],'little')==(p.pid<<32)|hello['tid'] and value==value_for()
    report['cases'][name]['before_fault_snapshot']=snapshot
    return key

fault_handles=[]
try:
    for filename,digest in f['source_sha256'].items():assert sha((w/filename).read_bytes())==digest
    probe=root/'own-http-with-blocked-pipe.py';probe.write_bytes((w/'probe.py').read_bytes());probe.chmod(0o600)
    unit=subprocess.run([str(w/'pairing.test'),'-test.v'],capture_output=True,timeout=15)
    assert len(unit.stdout)<=262144 and len(unit.stderr)<=16384
    report['Go_tests']={'exit':unit.returncode,'stdout_utf8':unit.stdout.decode(),'stderr_utf8':unit.stderr.decode()}
    check('same-candidate-original-Go-and-admission-regressions',unit.returncode==0 and not unit.stderr and unit.stdout.endswith(b'PASS\n'))
    for name in ['capacity-full','depth-overflow','syscall-active-mismatch','stale-task-start-key']:
        p,hello,row=target(name);q,output=collector(name,'unchanged-910-admission',p,row);ready(name,q,p,False)
        m=OwnedMapFault(name,p,q);fault_handles.append(m);case=report['cases'][name]
        if name=='capacity-full':
            assert not m.snapshot()
            for i in range(1024):
                key=key_for(p.pid,1048576+i,i+1);m.call(2,key,value_for(),1)
            case['fault_kind']='synthetic-own-map-capacity-1024-no-actual1024-thread-churn'
            case['after_injection_snapshot']=m.snapshot();assert len(case['after_injection_snapshot'])==1024
        else:
            key=primed(name,p,hello,m)
            if name=='stale-task-start-key':
                stale=key_for(p.pid,hello['tid'],int.from_bytes(key[8:],'little')-1)
                injected=value_for(3,2);m.update(stale,injected,1);case['stale_key_hex']=stale.hex()
                case['fault_kind']='synthetic-stale-start-key-collision-not-OS-TID-reuse'
            else:
                injected=value_for(depth=64) if name=='depth-overflow' else value_for(3,0)
                m.update(key,injected);case['fault_kind']='injected-state-before-real-kernel-probe'
            case['injected_value_hex']=injected.hex();case['after_injection_snapshot']=m.snapshot()
        send(p,'burst');case['fault_burst']=message(p);assert len(case['fault_burst']['calls'])==32
        syscall_state(p,hello['tid']);case['after_real_kernel_probe_snapshot']=m.snapshot()
        if name=='stale-task-start-key':
            values={v['key_hex']:v['value_hex'] for v in case['after_real_kernel_probe_snapshot']}
            assert values[key.hex()]==value_for().hex() and values[stale.hex()]==injected.hex()
            m.delete(stale);case['fault_cleanup_before_closing_snapshot']=m.snapshot()
            assert case['fault_cleanup_before_closing_snapshot']==case['before_fault_snapshot']
        m.close();r=finish_collector(name,q,output);a=r['admission']
        if name=='stale-task-start-key':
            check('same-pid-tid-different-start-key-never-consumed-poison-state',not r['incomplete'] and not a['admitted_stream_incomplete'] and a['admission_errors']==a['retained_raw_invalid_events']==0 and a['admitted_calls_quiesced_before_detach'] and not a['drain_timed_out'] and len(a['final_thread_states'])==1)
        else:
            check(name+':real-kernel-fault-visible-in-raw-and-overall-failure',r['incomplete'] and a['admitted_stream_incomplete'] and a['admission_errors']>0 and a['retained_raw_invalid_events']>0 and a['retained_raw_invalid_events']==sum(e.get('admission_boundary')=='invalid' for e in r['events']))
            if name=='capacity-full':assert len(a['final_thread_states'])==1024 and a['admitted_calls_quiesced_before_detach']
            else:assert a['drain_timed_out'] and not a['admitted_calls_quiesced_before_detach']
        finish_probe(name,p)
    assert len(report['checks'])==17
    report['phase']='passed-own-injected-admission-faults-not-actual-TID-reuse-or-vendor-qualified'
except BaseException as error:report.update(phase='failed',error_class=type(error).__name__,error=str(error),traceback=traceback.format_exc())
finally:
    for handle in fault_handles:handle.close()
    report['all_fault_map_FDs_closed']=all(handle.fd is None for handle in fault_handles)
    for kind,p,row in reversed(children):
        if p.poll() is None:
            report['forced_own_cleanup']=True;report['phase']='failed'
            try:
                assert alive(row)
                if kind=='collector':
                    if not p.stdin.closed:p.stdin.close()
                    p.wait(timeout=5)
                else:p.terminate();p.wait(timeout=5)
            except BaseException as error:report.setdefault('cleanup_errors',[]).append({'kind':kind,'identity':row,'error':str(error)})
    for name,case in report['cases'].items():
        output=root/(name+'-stream.json')
        if output.exists() and 'stream' not in case:
            raw=output.read_bytes();assert len(raw)<=32*1024*1024;r=json.loads(raw);case.update(stream={'path':output.name,'bytes':len(raw),'sha256':sha(raw)},failure_report_summary={k:r.get(k) for k in ['phase','reason','program_ids','control_program_ids','map_ids','all_owned_handles_closed','diagnostic_errors','cleanup_errors']})
    report['all_original_child_identities_absent']=all(not alive(row) for _,_,row in children);report['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();(w/'exit.json').write_text(json.dumps({'exit':0 if report['phase'].startswith('passed-') else 1}));print(json.dumps({'phase':report['phase'],'checks':len(report['checks']),'error':report.get('error')}))
