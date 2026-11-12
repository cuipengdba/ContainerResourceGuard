import datetime,hashlib,json,os,pathlib,select,socket,subprocess,sys,threading,time,traceback

P=pathlib.Path
w=P(__file__).parent
root=P('/var/tmp/crg-bpf760-checks-20261112')
root.mkdir(mode=0o700,exist_ok=False)
binary=w/'direct-bpf'
marker='authorized-disposable-loopback-only'
program='''import json,os,socket,threading,time
r,w=os.pipe();os.set_blocking(w,False)
while True:
 try:os.write(w,b'x'*4096)
 except BlockingIOError:break
s=socket.socket();s.bind(('127.0.0.1',0));s.listen(1)
print(json.dumps({'port':s.getsockname()[1],'write_fd':w}),flush=True)
mode=input()
if mode=='dirty':
 import fcntl
 from pathlib import Path
 root=Path(__file__).parent;files=[];opened=[];began=time.monotonic_ns()
 opened_at=time.monotonic_ns();f=os.open(str(root/'own-dirty.bin'),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_APPEND,0o600);opened.append(f)
 st=os.fstat(f);files.append({'opened_monotonic_ns':opened_at,'fd':f,'inode':st.st_ino,'major':os.major(st.st_dev),'minor':os.minor(st.st_dev),'mode':st.st_mode,'flags':fcntl.fcntl(f,fcntl.F_GETFL),'path':str(root/'own-dirty.bin')})
 # Separate open file descriptions avoid f_pos_lock serializing the test
 # before the inode lock. The second append must contend on this own inode.
 other=os.open(str(root/'own-dirty.bin'),os.O_WRONLY|os.O_APPEND)
 st=os.fstat(other);contender={'fd':other,'inode':st.st_ino,'major':os.major(st.st_dev),'minor':os.minor(st.st_dev),'mode':st.st_mode,'flags':fcntl.fcntl(other,fcntl.F_GETFL)}
 payload=b'x'*1048576;started=threading.Event();calls={}
 def writer():
  calls['writer_tid']=threading.get_native_id();calls['writer_started_ns']=time.monotonic_ns();calls['writer_bytes']=0
  for index in range(32):
   assert os.write(f,payload)==1048576;calls['writer_bytes']+=1048576
   if index==15:started.set()
  calls['writer_finished_ns']=time.monotonic_ns()
 thread=threading.Thread(target=writer);thread.start();assert started.wait(50);time.sleep(.05)
 calls['contender_tid']=threading.get_native_id();calls['contender_started_ns']=time.monotonic_ns();assert os.write(other,b'z'*143)==143;calls['contender_finished_ns']=time.monotonic_ns();thread.join(55);assert not thread.is_alive() and calls['writer_bytes']==33554432;payload=None;os.close(other)
 os.fsync(f)
 opened_at=time.monotonic_ns();f=os.open(str(root/'own-sync.bin'),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_DSYNC,0o600);opened.append(f)
 st=os.fstat(f);files.append({'opened_monotonic_ns':opened_at,'fd':f,'inode':st.st_ino,'major':os.major(st.st_dev),'minor':os.minor(st.st_dev),'mode':st.st_mode,'flags':fcntl.fcntl(f,fcntl.F_GETFL),'path':str(root/'own-sync.bin')})
 assert os.write(f,b'y'*4096)==4096;os.fsync(f)
 print(json.dumps({'done':True,'files':files,'bytes_written':33558671,'calls':calls,'contender':contender,'started_ns':began,'finished_ns':time.monotonic_ns()}),flush=True)
 try:input()
 finally:
  for f,info in zip(opened,files):
   st=os.fstat(f);assert st.st_ino==info['inode'];os.close(f);path=Path(info['path']);assert not path.is_symlink() and path.stat().st_ino==info['inode'];path.unlink()
 s.close();os.close(r);os.close(w);raise SystemExit(0)
if mode=='scope':
 import fcntl
 from pathlib import Path
 path=Path(__file__).parent/'own-scope.bin';f=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);st=os.fstat(f);calls=[]
 info={'fd':f,'inode':st.st_ino,'major':os.major(st.st_dev),'minor':os.minor(st.st_dev),'mode':st.st_mode,'flags':fcntl.fcntl(f,fcntl.F_GETFL),'path':str(path)}
 for size in [0,1,4096,4097]:
  before=time.monotonic_ns();ret=os.write(f,b'x'*size);after=time.monotonic_ns();assert ret==size;calls.append({'count':size,'return':ret,'started_ns':before,'finished_ns':after,'tid':threading.get_native_id()})
 print(json.dumps({'done':True,'file':info,'calls':calls,'bytes_written':8194}),flush=True)
 try:input()
 finally:
  assert os.fstat(f).st_ino==info['inode'];os.close(f);assert not path.is_symlink() and path.stat().st_ino==info['inode'];path.unlink()
 s.close();os.close(r);os.close(w);raise SystemExit(0)
if mode=='fast':
 records=[]
 for _ in range(32):
  c,a=s.accept();local=c.getsockname()[1];remote=c.getpeername()[1];fd=c.fileno()
  start=time.monotonic_ns();c.recv(4096);c.sendall(b'HTTP/1.0 200 OK\\r\\nContent-Length: 3\\r\\n\\r\\n000');c.close()
  records.append({'fd':fd,'local_port':local,'remote_port':remote,'started_ns':start,'closed_ns':time.monotonic_ns()})
 # AF_UNIX and UDP are sockets but must never be labeled TCP endpoints.
 u,v=socket.socketpair();unixfd=u.fileno();unixstart=time.monotonic_ns();v.send(b'x');u.recv(1);unixend=time.monotonic_ns();u.close();v.close()
 u=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);v=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);u.bind(('127.0.0.1',0));udpfd=u.fileno();udpstart=time.monotonic_ns();v.sendto(b'x',u.getsockname());u.recvfrom(1);udpend=time.monotonic_ns();u.close();v.close()
 invalidstart=time.monotonic_ns()
 for fd in [-1,65536]:
  try:os.close(fd)
  except OSError:pass
 invalidend=time.monotonic_ns()
 print(json.dumps({'done':True,'connections':records,'non_tcp':[{'fd':unixfd,'started_ns':unixstart,'ended_ns':unixend},{'fd':udpfd,'started_ns':udpstart,'ended_ns':udpend}],'invalid_start_ns':invalidstart,'invalid_end_ns':invalidend}),flush=True)
 s.close();os.close(r);os.close(w);input();raise SystemExit(0)
if mode=='flood':
 f=os.open('/dev/null',os.O_WRONLY)
 for _ in range(100000):os.write(f,b'x')
 os.close(f);print('DONE',flush=True);input();raise SystemExit(0)
c,a=s.accept();c.recv(4096)
try:os.write(w,b'x'*4096)
except BlockingIOError:pass
os.set_blocking(w,True)
def drain():
 time.sleep(.5)
 while os.read(r,8192):pass
t=threading.Thread(target=drain);t.start();os.write(w,b'x'*4096);os.close(w);t.join();os.close(r)
c.sendall(b'HTTP/1.0 200 OK\\r\\nContent-Length: 3\\r\\n\\r\\n000');c.close();s.close()
input()
'''
probe=root/'own-http-with-blocked-pipe.py'
probe.write_text(program);probe.chmod(0o600)
report={'schema':'crg-direct-BPF-kernel-endpoint-own-fast-qualification-v1','phase':'running','planned_checks':44,'node_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':[],'cases':{},'owned_processes':{},'target_business_processes':0,'target_signals_or_control_writes':0,'forced_own_cleanup':False,'source_sha256':{n:hashlib.sha256((w/n).read_bytes()).hexdigest() for n in ['main.go','kernel.go','layout.go','wait.go','function.go','function_test.go','scope.go','pairing.test','vendor.go','go.mod','go.sum','direct-bpf','checks.py','runner.py']}}
children=[];collectors=[];own_group=None;root_controls_before=None
def identity(pid):
 f=P('/proc',str(pid),'stat').read_bytes().rsplit(b')',1)[1].split()
 return {'pid':pid,'start_ticks':int(f[19]),'parent_pid':int(f[1]),'cgroup':P('/proc',str(pid),'cgroup').read_text().strip()[3:]}
def check(name,value):
 report['checks'].append({'name':name,'passed':bool(value)})
 assert value,name
def new_target(name,delay=0):
 c=subprocess.Popen([sys.executable,str(probe)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
 children.append(c);report['owned_processes'][name]=identity(c.pid)
 assert select.select([c.stdout],[],[],5)[0]
 ready=json.loads(c.stdout.readline());v=identity(c.pid)
 plan={'owner_pid':os.getpid(),'owner_start_ticks':identity(os.getpid())['start_ticks'],'pid':c.pid,'start_ticks':v['start_ticks'],'executable_sha256':hashlib.sha256(P('/proc',str(c.pid),'exe').read_bytes()).hexdigest(),'probe_path':str(probe),'probe_sha256':hashlib.sha256(probe.read_bytes()).hexdigest(),'cgroup':v['cgroup'],'maximum_seconds':12,'qualification_reader_delay_milliseconds':delay}
 return c,ready,plan
def command(name,plan,execute=False,authorized=True,async_=False):
 path=root/(name+'-plan.json');path.write_text(json.dumps(plan)+'\n');path.chmod(0o600);output=root/(name+'-stream.json')
 env=os.environ.copy();env.pop('CRG_DIRECT_BPF',None)
 if authorized:env['CRG_DIRECT_BPF']=marker
 args=[str(binary),'--plan',str(path),'--output',str(output)]
 if execute:args.append('--execute')
 if not async_:
  v=subprocess.run(args,stdin=subprocess.DEVNULL,capture_output=True,text=True,env=env,timeout=5)
  result=json.loads(output.read_text());report['cases'][name]={'exit':v.returncode,'stderr_present':bool(v.stderr),'report':result};return v,result
 c=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env,bufsize=1)
 collectors.append((name,c,output));report['owned_processes'][name]=identity(c.pid)
 assert select.select([c.stdout],[],[],5)[0],'collector-ready-timeout'
 raw=c.stdout.readline();message=json.loads(raw)
 if message.get('phase')!='ready':
  c.wait(timeout=3);result=json.loads(output.read_text());report['cases'][name]={'exit':c.returncode,'report':result};raise AssertionError('collector-start:'+result.get('reason','unknown'))
 return c,message
def finish(name,c):
 c.stdin.close();c.wait(timeout=4);result=json.loads((root/(name+'-stream.json')).read_text());stderr=c.stderr.read(4096)
 report['cases'][name]={'exit':c.returncode,'stderr_present':bool(stderr),'report':result}
 return result
def natural(c):c.stdin.write('\n');c.stdin.flush();c.wait(timeout=3)
def wait_metadata_events(events,name):
 return [event for event in events if event['call']==name and event['direction']=='metadata']

def wait_domain_regression():
 data={'call':'balance_dirty_pages','direction':'metadata','integer_fields':{'pause':1,'paused':0,'dirty':2,'bdi_dirty':3,'cgroup_ino':4}}
 entered={'call':'balance_dirty_pages','direction':'function_enter'};exited={'call':'balance_dirty_pages','direction':'function_exit'}
 assert wait_metadata_events([entered,data,exited],'balance_dirty_pages')==[data]
 malformed={**data,'integer_fields':{}};selected=wait_metadata_events([entered,malformed,exited],'balance_dirty_pages')
 assert selected==[malformed] and set(selected[0]['integer_fields'])!={'pause','paused','dirty','bdi_dirty','cgroup_ino'}
 return {'same_named_function_events_excluded':True,'actual_metadata_retained':True,'malformed_metadata_not_filtered_away':True}

def file_lifetime_writes(pairs,info,finished):
 return [p['entry'] for p in pairs if p['entry']['call']=='write' and p['entry'].get('fd')==info['fd'] and info['opened_monotonic_ns']<=p['entry']['monotonic_ns']<=finished]

def file_metadata_matches(writes,info):
 return bool(writes) and all(v.get('fd_metadata',{}).get('source')=='event-time-safe-kernel-file-metadata' and v['fd_metadata'].get('inode')==info['inode'] and v['fd_metadata'].get('device_major')==info['major'] and v['fd_metadata'].get('device_minor')==info['minor'] and v['fd_metadata'].get('file_mode')==info['mode'] and v['fd_metadata'].get('file_flags')==info['flags'] for v in writes)

def file_lifetime_regression():
 info={'fd':7,'opened_monotonic_ns':300,'inode':11,'major':253,'minor':0,'mode':33152,'flags':36865}
 earlier={'call':'write','fd':7,'monotonic_ns':200,'fd_metadata':{'source':'event-time-safe-kernel-file-metadata','inode':10,'device_major':253,'device_minor':0,'file_mode':33152,'file_flags':33793}}
 current={**earlier,'monotonic_ns':400,'fd_metadata':{**earlier['fd_metadata'],'inode':11,'file_flags':36865}}
 pairs=[{'entry':earlier},{'entry':current}];selected=file_lifetime_writes(pairs,info,500)
 assert selected==[current] and file_metadata_matches(selected,info) and not file_metadata_matches([earlier,current],info)
 wrong={**current,'fd_metadata':{**current['fd_metadata'],'inode':12}}
 assert not file_metadata_matches(file_lifetime_writes([{'entry':wrong}],info,500),info)
 assert not file_metadata_matches(file_lifetime_writes(pairs,{**info,'opened_monotonic_ns':600},700),info)
 return {'same_numeric_FD_previous_inode_excluded_by_open_time':True,'wrong_inode_inside_lifetime_rejected':True,'empty_lifetime_rejected':True,'no_metadata_filtering_used_to_choose_candidates':True}

try:
 report['file_lifetime_regression']=file_lifetime_regression();check('file-lifetime-unit-reused-FD-wrong-inode-and-empty-stream',all(report['file_lifetime_regression'].values()))
 report['wait_domain_regression']=wait_domain_regression();check('wait-domain-unit-function-events-separated-and-malformed-metadata-retained',all(report['wait_domain_regression'].values()))
 unit=subprocess.run([str(w/'pairing.test'),'-test.v'],capture_output=True,text=True,timeout=10);assert len(unit.stdout)<16384 and not unit.stderr;report['function_pair_unit']={'exit':unit.returncode,'stdout':unit.stdout,'test_binary_sha256':hashlib.sha256((w/'pairing.test').read_bytes()).hexdigest()}
 check('actual-linux-unit-nested-interleaved-missing-return-and-depth-cases',unit.returncode==0 and 'TestNestedAndInterleavedFunctionsPreserveAllFrames' in unit.stdout and 'TestMissingOrMismatchedFramesNeverBecomeComplete' in unit.stdout and 'TestDepthBoundMakesStreamIncomplete' in unit.stdout and unit.stdout.endswith('PASS\n'))
 child,ready,plan=new_target('normal-target')
 v,r=command('marker-missing',plan,True,False)
 check('missing-marker-rejected-before-target-or-BPF-opening',v.returncode==1 and r['reason']=='EXPLICIT_LAB_MARKER' and not r.get('map_ids') and r['target_pid']==0)
 v,r=command('wrong-start',{**plan,'start_ticks':plan['start_ticks']+1},True)
 check('actual-target-start-mismatch-rejected-without-BPF-loading',v.returncode==1 and r['reason']=='TARGET_IDENTITY' and not r.get('map_ids'))
 v,r=command('default-readonly',plan)
 check('default-preflight-validates-real-formats-without-BPF-loading',v.returncode==0 and r['phase']=='preflight-readonly' and len(r['hooks'])==40 and not r.get('program_ids') and not r.get('map_ids'))
 helper,message=command('normal',plan,True,async_=True)
 check('all-forty-real-hooks-and-five-maps-attached-before-request',len(message['program_ids'])==40 and len(message['map_ids'])==5 and message['cgroup_id']>0)
 child.stdin.write('\n');child.stdin.flush();request={};done=threading.Event()
 def client():
  try:
   with socket.create_connection(('127.0.0.1',ready['port']),timeout=4) as c:
    request.update(client_port=c.getsockname()[1],server_port=ready['port'],started_monotonic_ns=time.monotonic_ns());c.sendall(b'GET /test HTTP/1.0\r\n\r\n');data=b''
    while True:
     raw=c.recv(4096)
     if not raw:break
     data+=raw
    request.update(ended_monotonic_ns=time.monotonic_ns(),status_ok=data.endswith(b'000'))
  except BaseException as e:request['error_class']=type(e).__name__
  finally:done.set()
 thread=threading.Thread(target=client);thread.start();thread.join(timeout=5)
 report['request']=request
 check('original-four-second-request-and-half-second-probe-complete',done.is_set() and request.get('status_ok') and child.poll() is None)
 time.sleep(.1);r=finish('normal',helper)
 check('collector-closes-zero-loss-complete-stream-target-still-alive',helper.returncode==0 and r['phase']=='collected' and r['all_owned_handles_closed'] and r['detached_stream_drained_to_deadline'] and not r['incomplete'] and not r['diagnostic_errors'] and not r['cleanup_errors'] and r['perf_lost_samples']==0 and r['bpf_output_failures']==0 and child.poll() is None)
 writes=[v for v in r['pairs'] if v['entry']['call']=='write' and v['entry'].get('fd')==ready['write_fd']]
 check('real-negative-EAGAIN-return-retained',any(v['exit'].get('return')==-11 for v in writes))
 blocked=[v for v in writes if 450000000<=v['elapsed_ns']<=2000000000 and v['exit'].get('return')==4096]
 check('actual-half-second-blocking-write-duration-and-return',len(blocked)==1)
 recv=[v for v in r['pairs'] if v['entry']['call']=='recvfrom' and v['entry'].get('fd_metadata',{}).get('remote_port')==request['client_port'] and v['entry'].get('fd_metadata',{}).get('local_port')==request['server_port']]
 sent=[v for v in r['pairs'] if v['entry']['call']=='sendto' and any(v['entry']['fd']==a['entry']['fd'] for a in recv)]
 check('same-thread-exact-loopback-connection-wraps-blocking-write',any(a['entry']['tid']==blocked[0]['entry']['tid']==z['entry']['tid'] and a['exit']['monotonic_ns']<=blocked[0]['entry']['monotonic_ns']<blocked[0]['exit']['monotonic_ns']<=z['entry']['monotonic_ns'] and not any(v['entry']['call']=='close' and v['entry'].get('fd')==a['entry']['fd'] and a['entry']['monotonic_ns']<=v['entry']['monotonic_ns']<=z['exit']['monotonic_ns'] for v in r['pairs']) for a in recv for z in sent))
 lag=[v['decoded_monotonic_ns']-v['monotonic_ns'] for v in r['events']];report['normal_decode_delay_ns']={'minimum':min(lag),'maximum':max(lag)}
 check('all-selected-records-match-actual-target-and-cgroup',all(v['pid']==child.pid and v['cgroup_id']==message['cgroup_id'] for v in r['events']) and not r['raw_target_memory_pointers_buffers_payload_saved'] and r['target_signals_or_control_writes']==0)
 natural(child)
 check('normal-target-exits-naturally-after-collector-detaches',child.returncode==0 and not child.stderr.read(4096))
 fast,ready,plan=new_target('fast-target',500);helper,message=command('fast',plan,True,async_=True)
 fast.stdin.write('fast\n');fast.stdin.flush();requests=[]
 for i in range(32):
  with socket.create_connection(('127.0.0.1',ready['port']),timeout=4) as c:
   request={'client_port':c.getsockname()[1],'server_port':ready['port'],'started_monotonic_ns':time.monotonic_ns()};c.sendall(b'GET /test HTTP/1.0\r\n\r\n');data=b''
   while True:
    raw=c.recv(4096)
    if not raw:break
    data+=raw
   request.update(ended_monotonic_ns=time.monotonic_ns(),status_ok=data.endswith(b'000'));requests.append(request)
 assert select.select([fast.stdout],[],[],5)[0];observed=json.loads(fast.stdout.readline());report['fast_requests']=requests;report['fast_target_operations']=observed
 check('32-fast-real-connections-complete-without-artificial-response-hold',len(requests)==32 and all(v['status_ok'] and v['ended_monotonic_ns']-v['started_monotonic_ns']<4000000000 for v in requests) and observed['done'] and fast.poll() is None)
 time.sleep(.6);r=finish('fast',helper)
 check('fast-stream-zero-loss-complete-detached-and-all-handles-closed',helper.returncode==0 and r['phase']=='collected' and not r['incomplete'] and not r['diagnostic_errors'] and not r['cleanup_errors'] and r['all_owned_handles_closed'] and r['detached_stream_drained_to_deadline'] and r['perf_lost_samples']==r['bpf_output_failures']==0)
 associations=[]
 for request in requests:
  matches={}
  for call in ['recvfrom','sendto','close']:
   matches[call]=[v for v in r['pairs'] if v['entry']['call']==call and v['entry'].get('fd_metadata',{}).get('local_port')==request['server_port'] and v['entry'].get('fd_metadata',{}).get('remote_port')==request['client_port'] and v['entry'].get('fd_metadata',{}).get('source')=='event-time-safe-kernel-metadata']
  accepts=[v for v in r['pairs'] if v['entry']['call'] in ['accept','accept4'] and v['exit'].get('fd_metadata',{}).get('local_port')==request['server_port'] and v['exit'].get('fd_metadata',{}).get('remote_port')==request['client_port'] and v['exit'].get('fd_metadata',{}).get('source')=='event-time-safe-kernel-metadata']
  associations.append({'client_port':request['client_port'],'recv':len(matches['recvfrom']),'send':len(matches['sendto']),'close':len(matches['close']),'accept':len(accepts),'recv_decoded_after_client_end':any(v['entry']['decoded_monotonic_ns']>request['ended_monotonic_ns'] for v in matches['recvfrom'])})
 report['fast_associations']=associations
 check('all32-fast-endpoints-exactly-match-accept-recv-send-close-kernel-metadata',all(v['recv']>=1 and v['send']>=1 and v['close']==1 and v['accept']==1 for v in associations))
 check('closed-socket-FD-reuse-and-delayed-decoding-preserve-distinct-real-ports',len({v['fd'] for v in observed['connections']})<32 and len({v['remote_port'] for v in observed['connections']})==32 and all(v['recv_decoded_after_client_end'] for v in associations))
 non_tcp=[]
 for op in observed['non_tcp']:
  events=[v for v in r['events'] if v['call']=='recvfrom' and v['direction']=='enter' and v.get('fd')==op['fd'] and op['started_ns']<=v['monotonic_ns']<=op['ended_ns']]
  non_tcp.append(bool(events) and all(v.get('fd_metadata',{}).get('source')!='event-time-safe-kernel-metadata' for v in events))
 invalid=[v for v in r['pairs'] if v['entry']['call']=='close' and observed['invalid_start_ns']<=v['entry']['monotonic_ns']<=observed['invalid_end_ns'] and v['exit'].get('return')==-9]
 check('AF-UNIX-UDP-and-invalid-FDs-never-export-TCP-metadata',all(non_tcp) and len(invalid)==2 and all(v['entry'].get('fd_metadata',{}).get('source')!='event-time-safe-kernel-metadata' for v in invalid))
 check('fast-events-retain-only-exact-target-cgroup-and-validated-BTF-type-graph',all(v['pid']==fast.pid and v['cgroup_id']==message['cgroup_id'] for v in r['events']) and len(r['kernel_metadata_layout']['fields'])==19 and r['kernel_metadata_layout']['fields']['fdtable.fd']['validated_type']=='pointer2-to-file' and not r['raw_target_memory_pointers_buffers_payload_saved'] and r['target_signals_or_control_writes']==0)
 natural(fast);check('fast-target-exits-naturally-after-observer-detaches',fast.returncode==0 and not fast.stderr.read(4096))
 flood,_,plan=new_target('flood-target',500);helper,_=command('flood',plan,True,async_=True);flood.stdin.write('flood\n');flood.stdin.flush()
 assert select.select([flood.stdout],[],[],6)[0] and flood.stdout.readline().strip()=='DONE'
 time.sleep(.8);r=finish('flood',helper)
 check('real-full-ring-output-loss-explicitly-marks-diagnostic-incomplete',helper.returncode==0 and r['phase']=='collected' and r['incomplete'] and r['qualification_reader_delay_milliseconds']==500 and r['bpf_output_failures']>0 and r['perf_lost_samples']>=0)
 check('loss-path-closes-all-owned-handles-without-target-control',r['all_owned_handles_closed'] and not r['diagnostic_errors'] and not r['cleanup_errors'] and flood.poll() is None and not r['target_signals_or_control_writes'])
 natural(flood)
 check('flood-target-exits-naturally-no-raw-perf-or-core-artifacts',flood.returncode==0 and not flood.stderr.read(4096) and all(v.suffix in ['.py','.json'] for v in root.iterdir()))
 cgroot=P('/sys/fs/cgroup');root_controls_before={k:(cgroot/k).read_text() for k in ['cgroup.subtree_control','memory.high','io.max'] if (cgroot/k).exists()};required={'io','memory'};assert required.issubset(set((cgroot/'cgroup.subtree_control').read_text().split()))
 group=cgroot/'crg-wait760-20261112';assert not group.exists();group.mkdir();own_group=group
 st=root.stat();major,minor=os.major(st.st_dev),os.minor(st.st_dev);assert major>0 and P('/sys/dev/block',str(major)+':'+str(minor)).exists()
 (group/'memory.high').write_text('16777216');(group/'io.max').write_text(str(major)+':'+str(minor)+' wbps=1048576')
 dirty,ready,plan=new_target('dirty-target');v=identity(dirty.pid);assert v['parent_pid']==os.getpid() and v['start_ticks']==plan['start_ticks'];(group/'cgroup.procs').write_text(str(dirty.pid));v=identity(dirty.pid);assert v['cgroup']=='/crg-wait760-20261112';plan.update(cgroup=v['cgroup'],maximum_seconds=60)
 report['owned_group']={'path':str(group),'inode':group.stat().st_ino,'before_root_controls':root_controls_before,'actual_controls':{k:(group/k).read_text().strip() for k in ['memory.high','io.max']},'child_identity':v}
 check('only-new-own-child-leaf-controls-set-root-controls-unchanged',report['owned_group']['actual_controls']['memory.high']=='16777216' and all((cgroot/k).read_text()==value for k,value in root_controls_before.items()))
 helper,message=command('dirty',plan,True,async_=True);dirty.stdin.write('dirty\n');dirty.stdin.flush();assert select.select([dirty.stdout],[],[],55)[0],'dirty-workload55s';operations=json.loads(dirty.stdout.readline());report['dirty_operations']=operations
 check('bounded32MiB-parallel-append-plus-real-DSYNC-file-workload-completes',operations['done'] and operations['bytes_written']==33558671 and len(operations['files'])==2 and dirty.poll() is None)
 r=finish('dirty',helper);regular=[]
 for info in operations['files']:
  writes=file_lifetime_writes(r['pairs'],info,operations['finished_ns'])
  regular.append(file_metadata_matches(writes,info))
 check('regular-inode-device-mode-and-DSYNC-flags-match-real-fstat-fcntl',all(regular))
 balances=wait_metadata_events(r['events'],'balance_dirty_pages');folios=wait_metadata_events(r['events'],'folio_wait_writeback');report['wait_qualification']={'balance_dirty_pages_observed':len(balances),'folio_wait_writeback_observed':len(folios),'balance_runtime_qualified':bool(balances),'folio_runtime_qualified':bool(folios),'raw_pause_fields_not_interpreted_as_wait_duration':True,'collector_cgroup_matches_own_child':message['cgroup_id']==group.stat().st_ino}
 report['owned_group']['io_stat_after']=(group/'io.stat').read_text();report['owned_group']['memory_events_after']=(group/'memory.events').read_text()
 check('actual-balance-dirty-events-retain-five-signed-integers-exact-target',bool(balances) and all(v['pid']==dirty.pid and v['cgroup_id']==message['cgroup_id'] and set(v['integer_fields'])=={'paused','pause','dirty','bdi_dirty','cgroup_ino'} and isinstance(v['integer_fields']['pause'],int) for v in balances))
 check('folio-events-only-own-file-inodes-or-explicitly-unobserved',all(v['pid']==dirty.pid and v['cgroup_id']==message['cgroup_id'] and v['integer_fields']['ino'] in {f['inode'] for f in operations['files']} for v in folios) and report['wait_qualification']['folio_runtime_qualified']==bool(folios))
 check('dirty-metadata-events-do-not-break-syscall-pairing-zero-loss-detach',helper.returncode==0 and r['phase']=='collected' and not r['incomplete'] and r['perf_lost_samples']==r['bpf_output_failures']==0 and r['all_owned_handles_closed'] and r['detached_stream_drained_to_deadline'] and not r['diagnostic_errors'] and not r['cleanup_errors'])
 function_pairs=r['function_pairs'];names={'xfs_file_buffered_write','iomap_file_buffered_write','folio_wait_writeback','balance_dirty_pages','rwsem_down_write_slowpath'}
 report['function_runtime']={'actual_pair_counts':{n:sum(p['entry']['call']==n for p in function_pairs) for n in sorted(names)},'issues':r['function_pair_issues'],'same_function_nested_pairs_runtime_claim':False}
 check('five-real-function-entry-return-paths-observed-and-complete',not r['function_pair_issues'] and all(report['function_runtime']['actual_pair_counts'][n]>0 for n in names) and r['function_probes_use_PMU_only_no_tracefs_fallback'])
 calls=operations['calls'];contender=operations['contender'];own_writes=[p for p in r['pairs'] if p['entry']['call']=='write' and p['entry'].get('fd')==contender['fd'] and p['entry']['tid']==calls['contender_tid'] and calls['contender_started_ns']<=p['entry']['monotonic_ns']<=p['exit']['monotonic_ns']<=calls['contender_finished_ns']]
 check('parallel-separate-FDs-same-real-inode-contender-append-retained',len(own_writes)==1 and own_writes[0]['exit'].get('return')==143 and own_writes[0]['entry']['fd_metadata']['inode']==contender['inode']==operations['files'][0]['inode'] and own_writes[0]['entry']['fd_metadata']['file_flags']==contender['flags'])
 write=own_writes[0];locks=[p for p in function_pairs if p['entry']['call']=='rwsem_down_write_slowpath' and p['entry']['tid']==calls['contender_tid'] and write['entry']['monotonic_ns']<=p['entry']['monotonic_ns']<=p['exit']['monotonic_ns']<=write['exit']['monotonic_ns']]
 report['function_runtime']['actual_contender_syscall']=write;report['function_runtime']['same_TID_rwsem_inside_contender_write']=locks
 check('actual-blocking-rwsem-pair-inside-own-contender-append',len(locks)>=1 and max(p['elapsed_ns'] for p in locks)>=50000000 and all(p['elapsed_ns']<=write['elapsed_ns'] for p in locks))
 check('paired-functions-retain-only-own-identity-time-and-no-arguments',all(p['entry']['pid']==dirty.pid and p['exit']['pid']==dirty.pid and p['entry']['cgroup_id']==p['exit']['cgroup_id']==message['cgroup_id'] and p['entry']['tid']==p['exit']['tid'] and p['entry']['monotonic_ns']<=p['exit']['monotonic_ns'] and not any(k in p['entry'] or k in p['exit'] for k in ['fd','return','count','fd_metadata','integer_fields']) for p in function_pairs))
 stage_names={'iomap_iter','iomap_write_iter','iomap_write_begin','iomap_write_end','folio_wait_stable','__filemap_get_folio','__iomap_write_begin','balance_dirty_pages_ratelimited_flags'}
 stages=[p for p in function_pairs if p['entry']['call'] in stage_names]
 eligible=[p for p in r['pairs'] if p['entry']['call']=='write' and 1<=p['entry'].get('count',0)<=4096 and p['entry'].get('fd_metadata',{}).get('source')=='event-time-safe-kernel-file-metadata']
 large=[p for p in r['pairs'] if p['entry']['call']=='write' and p['entry'].get('count',0)>4096]
 def inside(p,call):return p['entry']['tid']==call['entry']['tid'] and call['entry']['monotonic_ns']<=p['entry']['monotonic_ns']<=p['exit']['monotonic_ns']<=call['exit']['monotonic_ns']
 report['iomap_stage_qualification']={'counts':{n:sum(p['entry']['call']==n for p in stages) for n in sorted(stage_names)},'eligible_small_regular_writes':len(eligible),'excluded_large_writes':len(large),'scope_rule':r['additional_stage_scope'],'scope_errors':r['stage_scope_errors'],'remaining_entries':r['stage_scope_remaining_entries'],'original_five_function_checks_preserved':True,'large_write_internal_stages_intentionally_unobserved':True}
 check('eight-new-real-iomap-stage-functions-observed',all(report['iomap_stage_qualification']['counts'].values()))
 check('additional-stages-contained-only-in-small-regular-file-write',bool(eligible) and all(sum(inside(p,call) for call in eligible)==1 for p in stages))
 check('large-writes-remain-visible-without-additional-page-loop-events',len(large)==32 and all(not inside(p,call) for p in stages for call in large))
 check('stage-scope-errors-and-remaining-entries-zero-all-real-cases',all(report['cases'][case]['report']['stage_scope_errors']==report['cases'][case]['report']['stage_scope_remaining_entries']==0 for case in ['normal','fast','flood','dirty']))
 check('original24-plus16-PMU-hooks-and-extra-maps-clean',len(r['hooks'])==40 and len(r['program_ids'])==40 and len(r['map_ids'])==5 and r['function_probes_use_PMU_only_no_tracefs_fallback'])
 natural(dirty);populated=(group/'cgroup.events').read_text();assert 'populated 0' in populated;group.rmdir();own_group=None
 report['owned_group']['independently_absent_before_return']=not group.exists()
 check('dirty-target-files-and-own-leaf-clean-root-controls-unchanged',dirty.returncode==0 and not dirty.stderr.read(4096) and not group.exists() and all(not P(v['path']).exists() for v in operations['files']) and all((cgroot/k).read_text()==value for k,value in root_controls_before.items()))
 scoped,ready,plan=new_target('scope-target');helper,message=command('scope',plan,True,async_=True);scoped.stdin.write('scope\n');scoped.stdin.flush();assert select.select([scoped.stdout],[],[],5)[0];boundary=json.loads(scoped.stdout.readline());report['scope_boundary_operations']=boundary;r=finish('scope',helper)
 selected=[]
 for call in boundary['calls']:
  matched=[p for p in r['pairs'] if p['entry']['call']=='write' and p['entry'].get('fd')==boundary['file']['fd'] and p['entry'].get('count',0)==call['count'] and call['started_ns']<=p['entry']['monotonic_ns']<=p['exit']['monotonic_ns']<=call['finished_ns']]
  assert len(matched)==1;selected.append(matched[0])
 check('real-small-write-boundaries-zero-one-4096-4097-and-file-identity',boundary['done'] and boundary['bytes_written']==8194 and all(p['exit'].get('return',0)==p['entry'].get('count',0) for p in selected) and file_metadata_matches([p['entry'] for p in selected],boundary['file']))
 stage_pairs=[p for p in r['function_pairs'] if p['entry']['call'] in stage_names];eligible=[p for p in selected if 1<=p['entry'].get('count',0)<=4096]
 check('new-stages-only-inside-real-one-and-4096-byte-writes',len(eligible)==2 and all(any(inside(p,call) for call in eligible) for p in stage_pairs) and all(any(p['entry']['call']=='iomap_write_begin' and inside(p,call) for p in stage_pairs) for call in eligible))
 excluded=[p for p in selected if p['entry'].get('count',0) in [0,4097]]
 check('zero-and-4097-syscalls-retained-with-no-page-loop-stages',len(excluded)==2 and not any(inside(p,call) for p in stage_pairs for call in excluded) and len(r['hooks'])==40 and not r['function_pair_issues'] and not r['incomplete'] and r['perf_lost_samples']==r['bpf_output_failures']==r['stage_scope_errors']==r['stage_scope_remaining_entries']==0 and r['all_owned_handles_closed'] and r['detached_stream_drained_to_deadline'])
 report['scope_boundary_pairs']=selected;report['scope_boundary_stage_pair_count']=len(stage_pairs);natural(scoped)
 check('scope-boundary-target-and-inode-natural-cleanup',scoped.returncode==0 and not scoped.stderr.read(4096) and not P(boundary['file']['path']).exists())
 assert len(report['checks'])==report['planned_checks'];report['phase']='passed'
except BaseException as e:report.update(phase='failed',error_class=type(e).__name__,error=str(e),traceback=traceback.format_exc())
finally:
 if report['phase']=='failed':
  report['failure_own_task_snapshots']=[]
  for child in children:
   if child.poll() is not None:continue
   try:
    actual=identity(child.pid);expected=next(v for v in report['owned_processes'].values() if v['pid']==child.pid)
    assert actual['start_ticks']==expected['start_ticks'] and actual['parent_pid']==os.getpid()
    snapshot={'identity':actual,'threads':[]}
    for task in sorted(P('/proc',str(child.pid),'task').iterdir())[:8]:
     raw=(task/'wchan').read_text().strip();assert len(raw)<=128 and all(c.isalnum() or c=='_' for c in raw)
     status=(task/'status').read_text();fields={v.split(':',1)[0]:v.split(':',1)[1].strip() for v in status.splitlines() if ':' in v};assert int(fields['Tgid'])==child.pid
     snapshot['threads'].append({'tid':int(task.name),'wchan':raw,'state':fields['State'],'memory_kB':{k:int(fields[k].split()[0]) for k in ['VmRSS','RssAnon','RssFile','RssShmem','VmSwap'] if k in fields}})
    report['failure_own_task_snapshots'].append(snapshot)
   except (OSError,AssertionError,StopIteration,ValueError):report.setdefault('failure_snapshot_errors',[]).append('OWN_CHILD_SNAPSHOT_UNAVAILABLE')
 for name,c,output in collectors:
  if c.poll() is None:
   try:c.stdin.close();c.wait(timeout=3)
   except (OSError,subprocess.TimeoutExpired):c.kill();c.wait(timeout=2);report['forced_own_cleanup']=True
  if output.exists():report['cases'][name]={'exit':c.returncode,'report':json.loads(output.read_text())}
 for c in children:
  if c.poll() is None:
   try:c.stdin.close();c.wait(timeout=3)
   except (OSError,subprocess.TimeoutExpired):c.kill();c.wait(timeout=2);report['forced_own_cleanup']=True
  report['owned_processes'][next(k for k,v in report['owned_processes'].items() if v['pid']==c.pid)]['exit']=c.returncode
 if own_group is not None:
  try:
   assert (own_group/'cgroup.events').read_text().find('populated 0')>=0;own_group.rmdir();report['owned_group_cleanup_after_failure']=True
  except Exception as e:report['owned_group_cleanup_error']=type(e).__name__
 report['ended_node_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 (root/'report.json').write_text(json.dumps(report,indent=2)+'\n');(root/'report.json').chmod(0o600)
print(json.dumps({'phase':report['phase'],'checks':report['checks'],'error':report.get('error')}))
raise SystemExit(0 if report['phase']=='passed' else 1)
