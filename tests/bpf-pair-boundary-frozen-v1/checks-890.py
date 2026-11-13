from pathlib import Path
import datetime, hashlib, json, os, select, subprocess, sys, time, traceback

w=Path(__file__).parent; f=json.loads((w/'manifest.json').read_text()); root=Path(f['output']); root.mkdir(mode=0o700)
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def identity(pid):
    fields=Path('/proc',str(pid),'stat').read_bytes().rsplit(b')',1)[1].split()
    return {'pid':pid,'start_ticks':int(fields[19]),'parent_pid':int(fields[1]),'cgroup':Path('/proc',str(pid),'cgroup').read_text().strip()[3:]}
owner=identity(os.getpid()); (w/'worker.json').write_text(json.dumps(owner))
report={'schema':'crg-controlled-BPF-pair-boundaries-v1','phase':'running','checks':[],'cases':{},'owned_processes':{},'source_sha256':f['source_sha256'],'forced_own_cleanup':False,'vendor_admission_qualified':False,'vendor_business_or_Pod_started':False}
children=[]
def save():(w/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
def check(name,value):
    report['checks'].append({'name':name,'passed':bool(value)}); save()
    assert value,name
def alive(row):
    try:return identity(row['pid'])['start_ticks']==row['start_ticks']
    except (FileNotFoundError,ProcessLookupError):return False
def message(p,timeout=5):
    assert select.select([p.stdout],[],[],timeout)[0],'owned child message timeout'
    line=p.stdout.readline(16385); assert 0<len(line)<=16384
    return json.loads(line)
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
    plan={'owner_pid':owner['pid'],'owner_start_ticks':owner['start_ticks'],'pid':p.pid,'start_ticks':target_identity['start_ticks'],'executable_sha256':sha(Path('/proc',str(p.pid),'exe').read_bytes()),'probe_path':str(root/'own-http-with-blocked-pipe.py'),'probe_sha256':f['source_sha256']['probe.py'],'cgroup':target_identity['cgroup'],'maximum_seconds':15,'qualification_pair_attach_pause_milliseconds':pause}
    plan_path=root/(name+'-plan.json'); plan_path.write_text(json.dumps(plan)+'\n'); plan_path.chmod(0o600)
    output=root/(name+'-stream.json'); env=os.environ.copy(); env['CRG_DIRECT_BPF']='authorized-disposable-loopback-only'
    q=subprocess.Popen([str(w/('legacy-bpf' if variant=='legacy' else 'direct-bpf')),'--plan',str(plan_path),'--output',str(output),'--execute'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1,env=env)
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
    q.stdin.close(); q.wait(timeout=5); stdout=q.stdout.read(16385); stderr=q.stderr.read(16385); assert len(stdout)<=16384 and len(stderr)<=16384
    terminal=json.loads(stdout); raw=output.read_bytes(); assert len(raw)<=32*1024*1024
    r=json.loads(raw); row=report['cases'][name]; row.update(collector_exit=q.returncode,terminal=terminal,stderr_utf8=stderr,stream={'path':output.name,'bytes':len(raw),'sha256':sha(raw)},summary={k:r.get(k) for k in ['phase','reason','incomplete','function_pair_issues','perf_lost_samples','bpf_output_failures','stage_scope_errors','stage_scope_remaining_entries','program_ids','map_ids','target_activation_before_put_observed_monotonic_ns','target_activation_after_put_observed_monotonic_ns','all_hooks_attached_observed_monotonic_ns','target_activation_after_all_hooks']})
    save()
    check(name+':original-bounds-loss-and-cleanup',q.returncode==0 and not stderr and terminal['complete_report_written'] and r['phase']=='collected' and r['all_hooks_attached_before_ready'] and r['all_owned_handles_closed'] and not r['diagnostic_errors'] and not r['cleanup_errors'] and r['perf_lost_samples']==r['bpf_output_failures']==r['stage_scope_errors']==r['stage_scope_remaining_entries']==0 and len(r['program_ids'])==40 and len(r['map_ids'])==5 and r['perf_mapped_budget']['actual_mapped_bytes']==r['perf_mapped_budget_after_drain']['actual_mapped_bytes']<=16*1024*1024 and not r['raw_target_memory_pointers_buffers_payload_saved'] and r['target_signals_or_control_writes']==0)
    return r
def finish_probe(name,p):
    send(p,'finish');p.wait(timeout=5);extra=p.stdout.read(16385);err=p.stderr.read(16385);check(name+':probe-natural-exit-and-private-write-file-cleaned',p.returncode==0 and not extra and not err and not (root/('write-'+str(p.pid)+'.data')).exists())
def in_window(events,burst):return [e for e in events if burst['begin_ns']<=e['monotonic_ns']<=burst['end_ns']]
try:
    for filename,want in f['source_sha256'].items():assert sha((w/filename).read_bytes())==want
    probe=root/'own-http-with-blocked-pipe.py'; probe.write_bytes((w/'probe.py').read_bytes());probe.chmod(0o600)
    unit=subprocess.run([str(w/'pairing.test'),'-test.v'],capture_output=True,timeout=15); assert len(unit.stdout)<=262144 and len(unit.stderr)<=16384
    report['Go_tests']={'exit':unit.returncode,'stdout_utf8':unit.stdout.decode(),'stderr_utf8':unit.stderr.decode()}; check('all-original-Go-tests-and-own-pause-scope-test',unit.returncode==0 and not unit.stderr and b'--- PASS: TestQualificationPairPauseRejectsVendorAndUnboundedInputs' in unit.stdout)
    for name,variant in [('legacy-gap','legacy'),('ordered-gap','ordered')]:
        p,hello,row=target(name); q,output=collector(name,variant,p,row,500);ready(name,q,p,True)
        case=report['cases'][name]; assert case['pre']['end_ns']<case['ready']['all_hooks_attached_observed_monotonic_ns']
        send(p,'burst');case['post']=message(p);case['post_quiescent']=syscall_state(p,hello['tid']);r=finish_collector(name,q,output)
        pre=in_window(r['events'],case['pre']);post=in_window(r['events'],case['post']);case['pre_event_count']=len(pre);case['post_event_count']=len(post)
        case['pre_inner_enters']=sum(e['call']=='__iomap_write_begin' and e['direction']=='function_enter' for e in pre);case['pre_inner_exits']=sum(e['call']=='__iomap_write_begin' and e['direction']=='function_exit' for e in pre)
        if variant=='legacy':
            check('legacy-half-installed-pair-reproduces-strict-failure-without-output-loss',not r['target_activation_after_all_hooks'] and case['pre_inner_enters']==32 and case['pre_inner_exits']==0 and r['incomplete'] and bool(r['function_pair_issues']))
        else:
            names=['iomap_iter','iomap_write_iter','iomap_write_begin','__filemap_get_folio','folio_wait_stable','__iomap_write_begin','iomap_write_end']
            case['post_stage_counts']={n:sum(e['call']==n and e['direction']=='function_enter' for e in post) for n in names}
            check('ordered-target-activation-excludes-partial-install-and-retains-post-ready-stages',r['target_activation_after_all_hooks'] and not pre and not r['incomplete'] and not r['function_pair_issues'] and all(v==32 for v in case['post_stage_counts'].values()))
        finish_probe(name,p)
    for name,before_attach in [('ordered-inflight-at-start',True),('ordered-inflight-at-detach',False)]:
        p,hello,row=target(name)
        if before_attach:
            send(p,'block'); about=message(p); blocked=syscall_state(p,hello['tid'],hello['pipe_write_fd'])
        q,output=collector(name,'ordered',p,row);ready(name,q,p,False);case=report['cases'][name]
        if not before_attach:
            send(p,'block'); about=message(p); blocked=syscall_state(p,hello['tid'],hello['pipe_write_fd'])
        assert about['phase']=='about-to-block';case['blocked_syscall_observation']=blocked
        if before_attach:
            send(p,'release');case['released_write']=message(p);case['post_quiescent']=syscall_state(p,hello['tid'])
        r=finish_collector(name,q,output)
        if not before_attach:send(p,'release');case['released_write_after_collector_terminal']=message(p)
        entry=[e for e in r['events'] if e['call']=='write' and e['direction']=='enter' and e.get('fd')==hello['pipe_write_fd'] and e.get('count')==4096]
        exit4096=[e for e in r['events'] if e['call']=='write' and e['direction']=='exit' and e.get('return')==4096]
        case['blocked_write_enter_events']=len(entry);case['blocked_write_exit4096_events']=len(exit4096)
        check(name+':remaining-unpaired-boundary-explicitly-incomplete',r['target_activation_after_all_hooks'] and r['incomplete'] and ((not entry and len(exit4096)==1) if before_attach else (len(entry)==1 and not exit4096)))
        finish_probe(name,p)
    report['phase']='passed-controlled-experiment-candidate-not-vendor-qualified'
except BaseException as error:report.update(phase='failed',error_class=type(error).__name__,error=str(error),traceback=traceback.format_exc())
finally:
    for kind,p,row in reversed(children):
        if p.poll() is None:
            report['forced_own_cleanup']=True; report['phase']='failed'
            try:
                assert alive(row)
                if kind=='collector':p.stdin.close();p.wait(timeout=5)
                else:p.terminate();p.wait(timeout=5)
            except BaseException as error:report.setdefault('cleanup_errors',[]).append({'kind':kind,'identity':row,'error':str(error)})
    report['all_original_child_identities_absent']=all(not alive(row) for _,_,row in children);report['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
    (w/'exit.json').write_text(json.dumps({'exit':0 if report['phase'].startswith('passed-') else 1}));print(json.dumps({'phase':report['phase'],'checks':len(report['checks']),'error':report.get('error')}))
