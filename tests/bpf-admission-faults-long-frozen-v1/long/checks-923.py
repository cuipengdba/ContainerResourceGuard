from pathlib import Path
import datetime, hashlib, json, os, select, subprocess, sys, time, traceback

w=Path(__file__).parent; f=json.loads((w/'manifest.json').read_text()); root=Path(f['output']); root.mkdir(mode=0o700)
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def identity(pid):
    fields=Path('/proc',str(pid),'stat').read_bytes().rsplit(b')',1)[1].split()
    return {'pid':pid,'start_ticks':int(fields[19]),'parent_pid':int(fields[1]),'cgroup':Path('/proc',str(pid),'cgroup').read_text().strip()[3:]}
owner=identity(os.getpid()); (w/'worker.json').write_text(json.dumps(owner))
report={'schema':'crg-own-admission-paired600-and-flood-v1','phase':'running','checks':[],'cases':{},'owned_processes':{},'source_sha256':f['source_sha256'],'forced_own_cleanup':False,'vendor_admission_qualified':False,'vendor_business_or_Pod_started':False}
children=[]
def save():
    p=w/'qualification.next';p.write_text(json.dumps(report,indent=2)+'\n');os.replace(str(p),str(w/'qualification.json'))
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
        chunk=os.read(p.stdout.fileno(),4096); assert chunk,'owned child ended before message';data+=chunk;assert len(data)<=131072
    line,rest=data.split(b'\n',1);buffers[key]=rest;assert 0<len(line)<=65536;return json.loads(line)
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
def collector(name,variant,p,target_identity,pause=0,max_seconds=660,reader_delay=0):
    plan={'owner_pid':owner['pid'],'owner_start_ticks':owner['start_ticks'],'pid':p.pid,'start_ticks':target_identity['start_ticks'],'executable_sha256':sha(Path('/proc',str(p.pid),'exe').read_bytes()),'probe_path':str(root/'own-http-with-blocked-pipe.py'),'probe_sha256':f['source_sha256']['probe.py'],'cgroup':target_identity['cgroup'],'maximum_seconds':max_seconds,'qualification_reader_delay_milliseconds':reader_delay,'qualification_pair_attach_pause_milliseconds':pause,'qualification_closing_progress':False}
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
def finish_collector(name,q,output):
    q.stdin.close();terminal=message(q,6);report['cases'][name]['terminal_observed_monotonic_ns']=time.monotonic_ns();q.wait(timeout=5)
    extra=q.stdout.read(16385);err=q.stderr.read(16385);assert not extra and not buffers.get(id(q)) and len(err)<=16384
    raw=output.read_bytes();assert len(raw)<=32*1024*1024;r=json.loads(raw)
    report['cases'][name].update(collector_exit=q.returncode,terminal=terminal,stderr_utf8=err,stream={'path':output.name,'bytes':len(raw),'sha256':sha(raw)},summary={k:r.get(k) for k in ['phase','reason','incomplete','perf_lost_samples','bpf_output_failures','stage_scope_errors','stage_scope_remaining_entries','program_ids','control_program_ids','map_ids','collector_cpu_seconds','collector_maxrss_kB','elapsed_seconds']});save()
    a=r.get('admission',{})
    check(name+':actual40-hooks-control7maps-stable-budget-and-closed-handles',q.returncode==0 and not err and terminal['complete_report_written'] and r['phase']=='collected' and r['all_hooks_attached_before_ready'] and r['all_owned_handles_closed'] and not r['diagnostic_errors'] and not r['cleanup_errors'] and len(r['program_ids'])==40 and len(r['control_program_ids'])==1 and len(r['map_ids'])==7 and r['perf_mapped_budget']['actual_mapped_bytes']==r['perf_mapped_budget_after_drain']['actual_mapped_bytes']==3244032 and r['stage_scope_errors']==r['stage_scope_remaining_entries']==0 and a['admission_errors']==a['probe_invocations_in_flight_after_detach']==a['retained_raw_invalid_events']==0 and a['kernel_boundary_event_counter']==a['retained_raw_boundary_events'])
    return r

def finish_probe(name,p):
    send(p,'finish');p.wait(timeout=5);extra=p.stdout.read(16385);err=p.stderr.read(16385);check(name+':probe-natural-exit-and-private-write-file-cleaned',p.returncode==0 and not extra and not err and not buffers.get(id(p)) and not (root/('write-'+str(p.pid)+'.data')).exists())
def in_window(events,burst):return [e for e in events if burst['begin_ns']<=e['monotonic_ns']<=burst['end_ns']]
import math,socket

def progress(value):
    next_path=w/'progress.next';next_path.write_text(json.dumps(value)+'\n');os.replace(str(next_path),str(w/'progress.json'))

def close_probe(name,p,operations=None):
    send(p,'finish');p.wait(timeout=5)
    extra=p.stdout.read(16385);err=p.stderr.read(16385)
    check(name+':natural-probe-exit-and-private-data-cleanup',p.returncode==0 and not extra and not err and not buffers.get(id(p)) and (operations is None or not Path(operations['file']['path']).exists()))

try:
    for filename,digest in f['source_sha256'].items():assert sha((w/filename).read_bytes())==digest
    probe=root/'own-http-with-blocked-pipe.py';probe.write_bytes((w/'probe.py').read_bytes());probe.chmod(0o600)
    unit=subprocess.run([str(w/'pairing.test'),'-test.v'],capture_output=True,timeout=15)
    report['Go_tests']={'exit':unit.returncode,'stdout_utf8':unit.stdout.decode(),'stderr_utf8':unit.stderr.decode()}
    check('unchanged-candidate-Go-regressions',unit.returncode==0 and not unit.stderr and len(unit.stdout)<262144 and unit.stdout.endswith(b'PASS\n'))
    baseline,bhello,brow=target('baseline');p,hello,row=target('long')
    q,output=collector('long','unchanged-910-admission',p,row,max_seconds=660);ready('long',q,p,False)
    case=report['cases']['long'];invalid={**case['plan'],'maximum_seconds':1201}
    bad_path=root/'invalid1201-plan.json';bad_path.write_text(json.dumps(invalid));bad_path.chmod(0o600)
    bad_output=root/'invalid1201-report.json';env=os.environ.copy();env['CRG_DIRECT_BPF']='authorized-disposable-loopback-only'
    bad=subprocess.run([str(w/'direct-bpf'),'--plan',str(bad_path),'--output',str(bad_output),'--execute'],env=env,capture_output=True,timeout=5)
    bad_raw=bad_output.read_bytes();bad_r=json.loads(bad_raw);report['invalid1201']={'exit':bad.returncode,'report_utf8':bad_raw.decode(),'sha256':sha(bad_raw)}
    check('duration1201-rejected-before-BPF-allocation',bad.returncode==1 and not bad.stderr and bad_r['reason']=='OWNED_PROBE_SCOPE' and not bad_r['program_ids'] and not bad_r['control_program_ids'] and not bad_r['map_ids'])
    send(baseline,'long');bstart=message(baseline);send(p,'long');start=message(p)
    assert bstart['phase']==start['phase']=='long-started'
    requests={'baseline':[],'long':[]};report['long_starts']={'baseline':bstart,'long':start}
    handles={'baseline':(baseline,bhello),'long':(p,hello)}
    state={'phase':'own-paired600-running','baseline_target':brow,'target':row,'collector':report['owned_processes']['long-collector'],'starts':report['long_starts'],'actual_requests_each':0}
    progress(state);save();due0=max(start['started_ns'],bstart['started_ns'])/1e9
    for index in range(120):
        time.sleep(max(0,due0+index*5-time.monotonic()))
        for name in (['baseline','long'] if index%2==0 else ['long','baseline']):
            child,h=handles[name];began=time.monotonic_ns()
            assert child.poll() is None
            with socket.create_connection(('127.0.0.1',h['port']),timeout=4) as connection:
                local=connection.getsockname()[1];connection.sendall(b'GET /test HTTP/1.0\r\n\r\n');data=b''
                while True:
                    part=connection.recv(4096)
                    if not part:break
                    data+=part;assert len(data)<=1024
            requests[name].append({'client_port':local,'server_port':h['port'],'started_ns':began,'finished_ns':time.monotonic_ns(),'request_ok':data==b'HTTP/1.0 200 OK\r\nContent-Length: 3\r\n\r\n000','socket_timeout_seconds':4})
        if index%12==0:
            state['actual_requests_each']=index+1;progress(state)
    operations={'baseline':message(baseline,8),'long':message(p,8)};report['long_operations']=operations;report['long_requests']=requests
    r=finish_collector('long',q,output)
    check('both-actual600-and120-four-second-loopback-requests',all(v['phase']=='long-finished' and v['elapsed_seconds']>=600 and len(v['calls'])==120 and v['bytes_written']==17160 for v in operations.values()) and all(len(v)==120 and all(i['request_ok'] and i['socket_timeout_seconds']==4 for i in v) for v in requests.values()))
    ops=operations['long'];writes=[v for v in r['pairs'] if v['entry']['call']=='write' and v['entry'].get('fd')==ops['file']['fd'] and ops['started_ns']<=v['entry']['monotonic_ns']<=v['exit']['monotonic_ns']<=ops['finished_ns']]
    names={'iomap_iter','iomap_write_iter','iomap_write_begin','__filemap_get_folio','__iomap_write_begin','iomap_write_end','balance_dirty_pages_ratelimited_flags'}
    stages=[v for v in r['function_pairs'] if v['entry']['call'] in names|{'folio_wait_stable'}]
    inside=lambda a,b:a['entry']['tid']==b['entry']['tid'] and b['entry']['monotonic_ns']<=a['entry']['monotonic_ns']<=a['exit']['monotonic_ns']<=b['exit']['monotonic_ns']
    metadata=lambda e:e.get('fd_metadata',{}).get('kind')=='regular_file' and e['fd_metadata'].get('inode')==ops['file']['inode'] and e['fd_metadata'].get('device_major')==ops['file']['major'] and e['fd_metadata'].get('device_minor')==ops['file']['minor']
    check('all120-real-143-byte-writes-metadata-and-required-stages',len(writes)==120 and all(metadata(v['entry']) and v['entry'].get('count')==v['exit'].get('return')==143 and all(any(a['entry']['call']==n and inside(a,v) for a in stages) for n in names) for v in writes) and all(sum(inside(a,v) for v in writes)==1 for a in stages))
    bindings=[]
    for request in requests['long']:
        counts={direction:sum(v['entry']['call']==call and v['entry'].get('fd_metadata',{}).get('source')=='event-time-safe-kernel-metadata' and v['entry']['fd_metadata'].get('local_port')==request['server_port'] and v['entry']['fd_metadata'].get('remote_port')==request['client_port'] and request['started_ns']<=v['entry']['monotonic_ns']<=v['exit']['monotonic_ns']<=request['finished_ns'] for v in r['pairs']) for direction,call in [('receive','recvfrom'),('send','sendto')]}
        bindings.append({'client_port':request['client_port'],**counts})
    report['long_port_bindings']=bindings
    check('all120-requests-have-exact-event-time-receive-and-send-ports',all(v['receive']>0 and v['send']>0 for v in bindings))
    a=r['admission']
    check('new-candidate-whole-raw-and-admitted-streams-complete-after600',not r['incomplete'] and not r['function_pair_issues'] and not a['admitted_stream_incomplete'] and a['admitted_calls_quiesced_before_detach'] and not a['drain_timed_out'] and a['admission_errors']==a['retained_raw_invalid_events']==0 and r['perf_lost_samples']==r['bpf_output_failures']==0)
    report['overhead_observation']={'concurrent_reference_not_isolated_causal_measurement':True,'target_cpu_seconds':{n:v['measured_target_cpu_seconds'] for n,v in operations.items()},'target_maxrss_kB':{n:v['target_maxrss_kB_observed_before_final_report'] for n,v in operations.items()},'collector_cpu_seconds':r['collector_cpu_seconds'],'collector_maxrss_kB_before_serialization':r['collector_maxrss_kB'],'collector_total_elapsed_seconds':r['elapsed_seconds'],'collector_perf_mmap_bytes':r['perf_mapped_budget']['actual_mapped_bytes'],'does_not_claim_CR_Guard_production_Agent_budget':True}
    check('collector-and-both-target-CPU-RSS-observations-recorded',all(math.isfinite(v['measured_target_cpu_seconds']) and v['measured_target_cpu_seconds']>=0 and v['target_maxrss_kB_observed_before_final_report']>0 for v in operations.values()) and r['collector_cpu_seconds']>0 and r['collector_maxrss_kB']>0)
    close_probe('baseline',baseline,operations['baseline']);close_probe('long',p,ops)
    name='flood';flood,fhello,frow=target(name);fq,fout=collector(name,'unchanged-910-admission',flood,frow,max_seconds=15,reader_delay=1000);ready(name,fq,flood,False)
    send(flood,'flood');report['flood_operations']=message(flood,8);assert report['flood_operations']['phase']=='flood-finished' and report['flood_operations']['actual_calls']==100000
    fr=finish_collector(name,fq,fout)
    check('original100000-call-flood-loss-is-visible-and-never-complete',fr['incomplete'] and fr['admission']['admitted_stream_incomplete'] and fr['perf_lost_samples']+fr['bpf_output_failures']>0 and len(fr['events'])<=20000)
    close_probe(name,flood)
    assert len(report['checks'])==13
    report['phase']='passed-own-paired600-and-flood-not-vendor-business-qualified'
    state.update(phase=report['phase'],actual_requests_each=120,actual_seconds_each={n:v['elapsed_seconds'] for n,v in operations.items()});progress(state)
except BaseException as error:report.update(phase='failed',error_class=type(error).__name__,error=str(error),traceback=traceback.format_exc())
finally:
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
