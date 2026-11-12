import signal,datetime,hashlib,importlib.util,json,os,pathlib,select,socket,subprocess,sys,threading,time,traceback
P=pathlib.Path;root=P('/var/tmp/crg-trace661-checks-20261112');root.mkdir(mode=0o700,exist_ok=False)
source=P('/var/tmp/crg-trace661-tools-20261112/vendor-perf-metadata.py');spec=importlib.util.spec_from_file_location('metadata',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
program='''import json,os,socket,threading,time
r,w=os.pipe();os.set_blocking(w,False)
while True:
 try:os.write(w,b'x'*4096)
 except BlockingIOError:break
s=socket.socket();s.bind(('127.0.0.1',0));s.listen(1)
print(json.dumps({'port':s.getsockname()[1],'write_fd':w}),flush=True)
input()
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
target_path=root/'own-http-with-blocked-pipe.py';target_path.write_text(program);target_path.chmod(0o600)
report={'schema':'crg-perf-metadata-host-qualification-v1','phase':'running','node_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'checks':[],'target_business_processes':0,'target_signals_or_control_writes':0};child=None;stream=None
def check(name,value):
 report['checks'].append({'name':name,'passed':bool(value)});assert value,name
try:
 old=os.environ.pop('CRG_PERF_METADATA',None)
 try:m.Stream([]);rejected=False
 except m.Rejected as e:rejected=str(e)=='EXPLICIT_LAB_MARKER'
 check('missing-marker-rejected-before-opening-target',rejected)
 os.environ['CRG_PERF_METADATA']=m.MARKER
 child=subprocess.Popen([sys.executable,str(target_path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
 assert select.select([child.stdout],[],[],5)[0];ready=json.loads(child.stdout.readline());report['own_target']={'pid':child.pid,**m.identity(child.pid),'executable_sha256':hashlib.sha256(P('/proc',str(child.pid),'exe').read_bytes()).hexdigest()};target=report['own_target']
 try:m.Stream([{**target,'start_ticks':target['start_ticks']+1}]);rejected=False
 except m.Rejected as e:rejected=str(e)=='TARGET_IDENTITY'
 check('mismatched-real-start-ticks-rejected',rejected)
 stream=m.Stream([target]);stream.start();check('real-perf-enable-ack-before-request',stream.ready);child.stdin.write('\n');child.stdin.flush()
 request={};done=threading.Event()
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
 client_thread=threading.Thread(target=client);client_thread.start();end=time.monotonic()+8
 while not done.is_set() and time.monotonic()<end:stream.pump(.05)
 check('original-own-loopback-request-completes-without-target-signals',done.is_set() and request.get('status_ok') and child.poll() is None)
 client_thread.join(1)
 for _ in range(5):stream.pump(.02)
 result=stream.finish();report.update(stream=result,request=request);check('stream-closes-cleanly-and-target-still-running',not result['diagnostic_errors'] and result['record_exit']==-signal.SIGINT and result['script_exit']==0 and child.poll() is None)
 writes=[v for v in result['pairs'] if v['entry']['call']=='write' and v['entry']['fd']==ready['write_fd']]
 check('actual-negative-EAGAIN-return-retained',any(v['exit']['return']==-11 for v in writes))
 blocked=[v for v in writes if 450000000<=v['elapsed_ns']<=2000000000 and v['exit']['return']==4096];check('actual-half-second-blocked-write-paired',len(blocked)==1)
 recv=[v for v in result['pairs'] if v['entry']['call']=='recvfrom' and v['entry']['fd_metadata'].get('remote_port')==request['client_port'] and v['entry']['fd_metadata'].get('local_port')==request['server_port']]
 sent=[v for v in result['pairs'] if v['entry']['call']=='sendto' and any(v['entry']['fd']==a['entry']['fd'] for a in recv)]
 check('same-thread-exact-loopback-connection-wraps-blocking-write',any(a['entry']['tid']==blocked[0]['entry']['tid']==z['entry']['tid'] and a['exit']['monotonic_ns']<=blocked[0]['entry']['monotonic_ns']<blocked[0]['exit']['monotonic_ns']<=z['entry']['monotonic_ns'] for a in recv for z in sent))
 child.stdin.write('\n');child.stdin.flush();child.wait(timeout=3);check('own-target-natural-exit-no-business-or-raw-files',child.returncode==0 and set(v.name for v in root.iterdir())=={target_path.name} and not result['raw_perf_files_target_buffers_addresses_or_payload_saved'])
 report['phase']='passed'
except BaseException as e:report.update(phase='failed',error_class=type(e).__name__,error=str(e),traceback=traceback.format_exc())
finally:
 if stream is not None:
  try:report['stream']=stream.finish()
  except BaseException as e:report['finish_error_class']=type(e).__name__
 if child is not None:
  if child.poll() is None:
   try:child.stdin.close();child.wait(timeout=3)
   except (OSError,subprocess.TimeoutExpired):child.kill();child.wait(timeout=2);report['forced_own_target_cleanup']=True
  report['own_target_exit']=child.returncode
  report['own_target_stderr']=child.stderr.read(4096)
 report['ended_node_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();(root/'report.json').write_text(json.dumps(report,indent=2)+'\n');(root/'report.json').chmod(0o600)
report['summary']={k:report.get(k) for k in ['phase','node_utc','error','checks','own_target_exit','forced_own_target_cleanup','finish_error_class']};report['summary']['stream']={k:report.get('stream',{}).get(k) for k in ['record_exit','script_exit','diagnostic_errors','stderr_present','collector_CPU_seconds','elapsed_seconds']}
print(json.dumps(report));raise SystemExit(0 if report['phase']=='passed' else 1)
