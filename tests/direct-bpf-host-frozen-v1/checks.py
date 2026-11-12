import datetime,hashlib,json,os,pathlib,select,socket,subprocess,sys,threading,time,traceback

P=pathlib.Path
w=P(__file__).parent
root=P('/var/tmp/crg-bpf669-checks-20261112')
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
report={'schema':'crg-direct-BPF-owned-probe-qualification-v1','phase':'running','planned_checks':14,'node_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':[],'cases':{},'owned_processes':{},'target_business_processes':0,'target_signals_or_control_writes':0,'forced_own_cleanup':False,'source_sha256':{n:hashlib.sha256((w/n).read_bytes()).hexdigest() for n in ['main.go','go.mod','go.sum','direct-bpf','checks.py','runner.py']}}
children=[];collectors=[]
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
try:
 child,ready,plan=new_target('normal-target')
 v,r=command('marker-missing',plan,True,False)
 check('missing-marker-rejected-before-target-or-BPF-opening',v.returncode==1 and r['reason']=='EXPLICIT_LAB_MARKER' and not r.get('map_ids') and r['target_pid']==0)
 v,r=command('wrong-start',{**plan,'start_ticks':plan['start_ticks']+1},True)
 check('actual-target-start-mismatch-rejected-without-BPF-loading',v.returncode==1 and r['reason']=='TARGET_IDENTITY' and not r.get('map_ids'))
 v,r=command('default-readonly',plan)
 check('default-preflight-validates-real-formats-without-BPF-loading',v.returncode==0 and r['phase']=='preflight-readonly' and len(r['hooks'])==12 and not r.get('program_ids') and not r.get('map_ids'))
 helper,message=command('normal',plan,True,async_=True)
 check('all-twelve-real-hooks-attached-before-request',len(message['program_ids'])==12 and len(message['map_ids'])==3 and message['cgroup_id']>0)
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
 flood,_,plan=new_target('flood-target',500);helper,_=command('flood',plan,True,async_=True);flood.stdin.write('flood\n');flood.stdin.flush()
 assert select.select([flood.stdout],[],[],6)[0] and flood.stdout.readline().strip()=='DONE'
 time.sleep(.8);r=finish('flood',helper)
 check('real-full-ring-output-loss-explicitly-marks-diagnostic-incomplete',helper.returncode==0 and r['phase']=='collected' and r['incomplete'] and r['qualification_reader_delay_milliseconds']==500 and r['bpf_output_failures']>0 and r['perf_lost_samples']>=0)
 check('loss-path-closes-all-owned-handles-without-target-control',r['all_owned_handles_closed'] and not r['diagnostic_errors'] and not r['cleanup_errors'] and flood.poll() is None and not r['target_signals_or_control_writes'])
 natural(flood)
 check('flood-target-exits-naturally-no-raw-perf-or-core-artifacts',flood.returncode==0 and not flood.stderr.read(4096) and all(v.suffix in ['.py','.json'] for v in root.iterdir()))
 assert len(report['checks'])==report['planned_checks'];report['phase']='passed'
except BaseException as e:report.update(phase='failed',error_class=type(e).__name__,error=str(e),traceback=traceback.format_exc())
finally:
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
 report['ended_node_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 (root/'report.json').write_text(json.dumps(report,indent=2)+'\n');(root/'report.json').chmod(0o600)
print(json.dumps({'phase':report['phase'],'checks':report['checks'],'error':report.get('error')}))
raise SystemExit(0 if report['phase']=='passed' else 1)
