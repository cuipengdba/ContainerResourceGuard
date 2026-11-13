from pathlib import Path
import datetime,hashlib,importlib.util,json,os,resource,select,subprocess,sys,time,traceback

w=Path(__file__).parent;f=json.loads((w/'manifest.json').read_text());sha=lambda raw:hashlib.sha256(raw).hexdigest();run_id='2026111288200';child=None;c=None;child_identity=None
def identity(pid):
    fields=Path('/proc',str(pid),'stat').read_bytes().rsplit(b')',1)[1].split();return {'pid':pid,'start_ticks':int(fields[19])}
owner=identity(os.getpid());(w/'worker.json').write_text(json.dumps(owner));report={'schema':'crg-private-receiver-own-long600-v1','phase':'running','checks':[],'source_sha256':f['source_sha256'],'run_id':run_id,'actual_vendor_business_or_HTTP_or_BPF_started':False,'synthetic_receiver_records_only':True}
def save():(w/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
def check(name,passed):
    report['checks'].append({'name':name,'passed':bool(passed)});save()
    if not passed:raise AssertionError(name)
def absent(row):
    try:return identity(row['pid'])['start_ticks']!=row['start_ticks']
    except (FileNotFoundError,ProcessLookupError):return True
began=time.monotonic();cpu=time.process_time();before_children=resource.getrusage(resource.RUSAGE_CHILDREN)
try:
    for name,want in f['source_sha256'].items():assert sha((w/name).read_bytes())==want
    check('all-frozen-sources-exact-SHA',True)
    spec=importlib.util.spec_from_file_location('long_receiver',w/'receiver.py');receiver=importlib.util.module_from_spec(spec);spec.loader.exec_module(receiver);root=w/'channels';root.mkdir(mode=0o700)
    c=receiver.Channel(root,run_id,os.geteuid(),os.getegid(),(w/'sitecustomize.py').read_bytes(),lambda:identity(os.getpid())==owner);c.prepare();c.start();check('private-owned-FIFO-and-real-reader-ready',c.status()['started'] and c.thread.is_alive())
    child=subprocess.Popen([sys.executable,str(w/'writer.py'),str(root/c.name/'annotations.fifo')],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1);child_identity=identity(child.pid);report['writer_identity']=child_identity;save()
    assert select.select([child.stdout],[],[],5)[0];hello=json.loads(child.stdout.readline(8193));report['writer_ready']=hello
    check('exact-owned-frozen-writer-ready-once',hello['phase']=='ready' and hello['pid']==child_identity['pid'] and hello['start_ticks']==child_identity['start_ticks'] and hello['source_sha256']==f['source_sha256']['sitecustomize.py'])
    while child.poll() is None:
        assert time.monotonic()-began<615
        report['progress']={'elapsed_seconds':time.monotonic()-began,'receiver':c.status(),'writer_same_identity':not absent(child_identity)};save();time.sleep(10)
    out=child.stdout.read(8193);err=child.stderr.read(8193);assert len(out)<=8192 and len(err)<=8192;report.update(writer_exit=child.returncode,writer_terminal_stdout_utf8=out,writer_terminal_stderr_utf8=err);terminal=json.loads(out);report['writer_terminal']=terminal
    c.stop();raw=c.raw();annotations=c.annotations();report['annotation_bytes']=len(raw);report['annotation_sha256']=sha(raw);report['actual_records']=len(annotations)
    check('writer-real600-seconds-and-exact121-synthetic-records',child.returncode==0 and not err and terminal['phase']=='finished' and terminal['elapsed_seconds']>=600 and terminal['records']==121 and len(annotations)==121 and [v['iteration'] for v in annotations]==list(range(121)) and all(v['synthetic_receiver_probe'] for v in annotations))
    check('exact-bounded-stream-SHA-byte-count-and-no-silent-drops',len(raw)==terminal['exact_expected_bytes'] and sha(raw)==terminal['exact_expected_sha256'] and not c.status()['errors'] and not c.status()['incomplete'] and c.status()['observed_bytes']==len(raw)<=1048576)
    with (w/'annotations.jsonl').open('xb') as output:os.chmod(w/'annotations.jsonl',0o600);output.write(raw);output.flush();os.fsync(output.fileno())
    c.cleanup();status=c.status();report['channel']=status;report['original_writer_absent']=absent(child_identity);check('real-reader-thread-FDs-channel-and-writer-cleaned',status['cleaned'] and status['reader_closed'] and status['stopped'] and not status['thread_alive'] and status['directory_fd_closed'] and status['parent_fd_closed'] and not (root/c.name).exists() and report['original_writer_absent'])
    elapsed=time.monotonic()-began;spent=time.process_time()-cpu;after_children=resource.getrusage(resource.RUSAGE_CHILDREN);report['cost']={'setup_through_export_cleanup_elapsed_seconds':elapsed,'receiver_parent_process_CPU_seconds':spent,'receiver_fraction_of_one_CPU':spent/elapsed,'criterion_fraction_of_one_CPU':.01,'writer_child_CPU_seconds':after_children.ru_utime+after_children.ru_stime-before_children.ru_utime-before_children.ru_stime,'whole_parent_MaxRSS_kB_observed':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'RSS_observation_not_a_memory_limit':True,'imports_and_final_report_serialization_not_in_CPU_window':True}
    check('receiver-own600-setup-through-cleanup-CPU-within-one-percent-core',elapsed>=600 and 0<=spent<=elapsed*.01)
    report['phase']='passed'
except BaseException as error:report.update(phase='failed',error_class=type(error).__name__,error=str(error),traceback=traceback.format_exc())
finally:
    try:
        if child is not None and child.poll() is None:
            assert not absent(child_identity);report['forced_own_writer_stop']=True;child.terminate();child.wait(timeout=5)
        if c is not None:
            c.stop()
            if not c.cleaned:c.cleanup()
            report['final_channel']=c.status()
    except BaseException as error:report.update(phase='failed',cleanup_error_class=type(error).__name__,cleanup_error=str(error))
    report['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();(w/'exit.json').write_text(json.dumps({'exit':0 if report['phase']=='passed' else 1}));print(json.dumps({'phase':report['phase'],'checks':len(report['checks']),'error':report.get('error')}))
