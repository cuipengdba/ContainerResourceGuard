from pathlib import Path
import datetime, hashlib, json, os, select, subprocess, sys, time, traceback

w=Path(__file__).parent; f=json.loads((w/'manifest.json').read_text()); root=Path(f['output']); root.mkdir(mode=0o700)
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def identity(pid):
    fields=Path('/proc',str(pid),'stat').read_bytes().rsplit(b')',1)[1].split()
    return {'pid':pid,'start_ticks':int(fields[19]),'parent_pid':int(fields[1]),'cgroup':Path('/proc',str(pid),'cgroup').read_text().strip()[3:]}
owner=identity(os.getpid()); (w/'worker.json').write_text(json.dumps(owner))
report={'schema':'crg-raw-preserving-admission-drain-own-v1','phase':'running','checks':[],'cases':{},'owned_processes':{},'source_sha256':f['source_sha256'],'forced_own_cleanup':False,'vendor_admission_qualified':False,'vendor_business_or_Pod_started':False}
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
    row.update(collector_exit=q.returncode,terminal=terminal,stderr_utf8=stderr,stream={'path':output.name,'bytes':len(raw),'sha256':sha(raw)},summary={k:r.get(k) for k in ['phase','reason','incomplete','function_pair_issues','perf_lost_samples','bpf_output_failures','stage_scope_errors','stage_scope_remaining_entries','program_ids','control_program_ids','map_ids','admission']});save()
    a=r.get('admission',{})
    check(name+':actual-hooks-bounds-accounting-and-cleanup',q.returncode==0 and not stderr and terminal['complete_report_written'] and r['phase']=='collected' and r['all_hooks_attached_before_ready'] and r['all_owned_handles_closed'] and not r['diagnostic_errors'] and not r['cleanup_errors'] and r['perf_lost_samples']==r['bpf_output_failures']==r['stage_scope_errors']==r['stage_scope_remaining_entries']==0 and len(r['program_ids'])==40 and len(r['control_program_ids'])==1 and len(r['map_ids'])==7 and r['perf_mapped_budget']['actual_mapped_bytes']==r['perf_mapped_budget_after_drain']['actual_mapped_bytes']<=16*1024*1024 and a['closing_requested'] and a['probe_invocations_in_flight_after_detach']==a['admission_errors']==0 and a['kernel_boundary_event_counter']==a['retained_raw_boundary_events'] and not a['retained_raw_invalid_events'])
    return r
def finish_probe(name,p):
    send(p,'finish');p.wait(timeout=5);extra=p.stdout.read(16385);err=p.stderr.read(16385);check(name+':probe-natural-exit-and-private-write-file-cleaned',p.returncode==0 and not extra and not err and not buffers.get(id(p)) and not (root/('write-'+str(p.pid)+'.data')).exists())
def in_window(events,burst):return [e for e in events if burst['begin_ns']<=e['monotonic_ns']<=burst['end_ns']]
try:
    for filename,want in f['source_sha256'].items():assert sha((w/filename).read_bytes())==want
    probe=root/'own-http-with-blocked-pipe.py';probe.write_bytes((w/'probe.py').read_bytes());probe.chmod(0o600)
    unit=subprocess.run([str(w/'pairing.test'),'-test.v'],capture_output=True,timeout=15);assert len(unit.stdout)<=262144 and len(unit.stderr)<=16384
    report['Go_tests']={'exit':unit.returncode,'stdout_utf8':unit.stdout.decode(),'stderr_utf8':unit.stderr.decode()};check('original-Go-tests-and-three-raw-admission-policy-regressions',unit.returncode==0 and not unit.stderr and all(name in unit.stdout.decode() for name in ['TestAdmissionViewNeverErasesWholeRawFailureOrBoundaryRecord','TestAdmissionAnalysisRejectsActualAccountingAndDrainFailures','TestAdmissionNestedFramesUseOriginalStrictPairer']))
    name='regular-normal';p,hello,row=target(name);q,output=collector(name,'admission',p,row,500);ready(name,q,p,True);case=report['cases'][name]
    send(p,'burst');case['post']=message(p);case['post_quiescent']=syscall_state(p,hello['tid']);r=finish_collector(name,q,output);a=r['admission']
    pre=in_window(r['events'],case['pre']);post=in_window(r['events'],case['post']);names=['iomap_iter','iomap_write_iter','iomap_write_begin','__filemap_get_folio','folio_wait_stable','__iomap_write_begin','iomap_write_end']
    case['post_stage_pairs_each_actual_write']=[{n:{direction:sum(e['call']==n and e['direction']==direction and c['begin_ns']<=e['monotonic_ns']<=c['end_ns'] for e in post) for direction in ['function_enter','function_exit']} for n in names} for c in case['post']['calls']]
    check('normal-original-raw-and-admitted-views-complete-with-all32-write-stages',not pre and not r['incomplete'] and not a['original_whole_raw_stream_incomplete'] and not a['admitted_stream_incomplete'] and a['admitted_calls_quiesced_before_detach'] and len(case['post']['calls'])==32 and all(c['bytes']==143 for c in case['post']['calls']) and all(v['function_enter']>=1 and v['function_enter']==v['function_exit'] for call in case['post_stage_pairs_each_actual_write'] for v in call.values()))
    leader=[v for v in a['final_thread_states'] if v['tid']==hello['tid']];layout=r['kernel_metadata_layout']['fields']['task_struct.start_boottime']
    check('actual-BTF-task-start-key-matches-owned-leader-proc-start-ticks',len(leader)==1 and leader[0]['pid']==p.pid and leader[0]['task_start_boottime_ns']*os.sysconf('SC_CLK_TCK')//1000000000==row['start_ticks'] and layout['size_bytes']==8 and layout['validated_type']=='integer')
    plan={**case['plan'],'vendor_fixture':{}};invalid=root/'invalid-vendor-closing-plan.json';invalid.write_text(json.dumps(plan));invalid.chmod(0o600);invalid_output=root/'invalid-vendor-closing-stream.json';env=os.environ.copy();env.update(CRG_DIRECT_BPF='authorized-disposable-loopback-only',CRG_DIRECT_BPF_VENDOR='owned-fresh-vendor-fixture-only')
    bad=subprocess.run([str(w/'direct-bpf'),'--plan',str(invalid),'--output',str(invalid_output),'--execute'],env=env,capture_output=True,timeout=5);raw=invalid_output.read_bytes();bad_report=json.loads(raw);report['rejected_vendor_closing']={'exit':bad.returncode,'report_utf8':raw.decode(),'report_sha256':sha(raw)}
    check('qualification-closing-progress-rejects-vendor-before-any-BPF-object',bad.returncode==1 and not bad.stderr and bad_report['reason']=='QUALIFICATION_CLOSING_PROGRESS_SCOPE' and not bad_report['program_ids'] and not bad_report['control_program_ids'] and not bad_report['map_ids'])
    finish_probe(name,p)
    name='inflight-start';p,hello,row=target(name);send(p,'block');about=message(p);blocked=syscall_state(p,hello['tid'],hello['pipe_write_fd']);q,output=collector(name,'admission',p,row);ready(name,q,p,False);case=report['cases'][name];case['blocked_syscall_observation']=blocked
    send(p,'release');case['released_write']=message(p);case['post_quiescent']=syscall_state(p,hello['tid']);r=finish_collector(name,q,output);a=r['admission'];exits=[e for e in r['events'] if e['call']=='write' and e['direction']=='exit' and e.get('return')==4096]
    check('cold-inflight-exit-retained-and-whole-raw-failure-never-reset',len(exits)==1 and exits[0].get('admission_boundary')=='boundary' and r['incomplete'] and a['original_whole_raw_stream_incomplete'] and not a['admitted_stream_incomplete'] and a['retained_raw_boundary_events']>=1 and a['admitted_syscall_pairs'] and not any(v['entry'].get('fd')==hello['pipe_write_fd'] for v in a['admitted_syscall_pairs']))
    finish_probe(name,p)
    for name,release in [('inflight-drained',True),('inflight-timeout',False)]:
        p,hello,row=target(name);q,output=collector(name,'admission',p,row);ready(name,q,p,False);case=report['cases'][name];send(p,'block');message(p);case['blocked_syscall_observation']=syscall_state(p,hello['tid'],hello['pipe_write_fd']);begin_closing(name,q)
        if release:send(p,'release');case['released_write_after_closing']=message(p)
        r=finish_collector(name,q,output,True);a=r['admission'];pairs=[v for v in a['admitted_syscall_pairs'] if v['entry']['call']=='write' and v['entry'].get('fd')==hello['pipe_write_fd'] and v['entry'].get('count')==4096]
        if release:
            check('closing-drains-existing-pipe-call-with-real-return-before-detach',a['admitted_calls_quiesced_before_detach'] and not a['drain_timed_out'] and not a['admitted_stream_incomplete'] and len(pairs)==1 and pairs[0]['exit']['return']==4096 and not any(v['syscall_enter_hook'] or v['function_depth'] for v in a['final_thread_states']))
        else:
            check('blocked-call-over-one-second-remains-explicitly-incomplete',a['drain_timed_out'] and a['maximum_admission_drain_milliseconds']==1000 and 1000000000<=case['terminal_observed_monotonic_ns']-case['closing']['observed_monotonic_ns']<4000000000 and not a['admitted_calls_quiesced_before_detach'] and a['admitted_stream_incomplete'] and r['incomplete'] and not pairs and any(v['syscall_enter_hook'] for v in a['final_thread_states']))
            send(p,'release');case['released_write_after_collector_terminal']=message(p)
        finish_probe(name,p)
    name='closing-new-regular';p,hello,row=target(name);q,output=collector(name,'admission',p,row);ready(name,q,p,False);case=report['cases'][name];send(p,'block');message(p);case['blocked_syscall_observation']=syscall_state(p,hello['tid'],hello['pipe_write_fd']);begin_closing(name,q)
    send(p,'burst-then-release');case['closing_burst']=message(p);assert case['closing_burst']['phase']=='closing-regular-burst-finished';case['released_write_after_new_regular_calls']=message(p);r=finish_collector(name,q,output,True);a=r['admission']
    burst=case['closing_burst'];events=in_window(r['events'],burst);entered=[e for e in events if e['call']=='write' and e['direction']=='enter' and e.get('fd')==hello['regular_fd'] and e.get('count')==143]
    case['raw_new_regular_enter_count']=len(entered);case['original_five_raw_boundary_events']=sum(e['call'] in ['xfs_file_buffered_write','iomap_file_buffered_write','folio_wait_writeback','balance_dirty_pages','rwsem_down_write_slowpath'] and e.get('admission_boundary')=='boundary' for e in events)
    check('closing-rejects-new-thread-calls-retains-raw-and-creates-no-stage-gate',burst['tid']!=hello['tid'] and len(burst['calls'])==32 and all(c['bytes']==143 for c in burst['calls']) and len(entered)==32 and all(e.get('admission_boundary')=='boundary' for e in entered) and case['original_five_raw_boundary_events']>=64 and not any(e['call'] in names for e in events) and not any(e['tid']==burst['tid'] for v in a['admitted_syscall_pairs'] for e in [v['entry'],v['exit']]) and a['admitted_calls_quiesced_before_detach'] and not a['drain_timed_out'] and not a['admitted_stream_incomplete'])
    finish_probe(name,p)
    report['phase']='passed-own-admission-drain-only-whole-raw-failures-preserved'
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
