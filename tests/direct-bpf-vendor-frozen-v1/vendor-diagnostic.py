import copy,datetime,hashlib,json,os,pathlib,select,subprocess,time
P=pathlib.Path;here=P(__file__).parent
VENDOR_SHA='bd21a02c74b4e416439d72f1cc5039280bea6399f67e2923dff6a743c189fdcb'
class Rejected(Exception):pass
def require(v,s):
 if not v:raise Rejected(s)
def identity(pid):
 p=P('/proc',str(pid));f=(p/'stat').read_bytes().rsplit(b')',1)[1].split();return {'pid':pid,'start_ticks':int(f[19]),'parent_pid':int(f[1]),'state':f[0].decode(),'cgroup':(p/'cgroup').read_text().strip()[3:]}
def read(path,maxbytes=32*1024*1024):
 raw=P(path).read_bytes();require(len(raw)<=maxbytes,'READ_BOUND');return json.loads(raw)
def private(path,data):
 raw=data if isinstance(data,bytes) else (json.dumps(data,sort_keys=True)+'\n').encode()
 with P(path).open('xb') as f:os.chmod(path,0o600);f.write(raw)
class Collector:
 def __init__(self,context,name,plan):self.c=context;self.name=name;self.plan=plan;self.child=None;self.record={};context['row'].setdefault('BPF_sessions',{})[name]=self.record
 def launch(self,execute,marker=True):
  c=self.c;self.planpath=c['root']/(c['role']+'-'+self.name+'-plan.json');self.out=c['root']/(c['role']+'-'+self.name+'-bpf.json');private(self.planpath,self.plan)
  env=dict(os.environ,CRG_DIRECT_BPF='authorized-disposable-loopback-only');env.pop('CRG_DIRECT_BPF_VENDOR',None)
  if marker:env['CRG_DIRECT_BPF_VENDOR']='owned-fresh-vendor-fixture-only'
  args=[str(here/'direct-bpf'),'--plan',str(self.planpath),'--output',str(self.out)]+(['--execute'] if execute else [])
  self.child=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env,bufsize=1)
  self.record.update(identity=identity(self.child.pid),entry=str(here/'direct-bpf'),plan=self.plan,plan_sha256=hashlib.sha256(self.planpath.read_bytes()).hexdigest());c['save']()
  require(select.select([self.child.stdout],[],[],20)[0],'COLLECTOR_READY_20S');message=json.loads(self.child.stdout.readline(4097))
  if message.get('phase')!='ready':
   self.child.wait(timeout=3);self.record.update(exit=self.child.returncode,report=read(self.out));c['save']();return False
  self.record.update(ready=message,ready_monotonic_ns=time.monotonic_ns());c['save']();return True
 def finish(self):
  if self.child is None:return None
  if self.child.poll() is None:
   if not self.child.stdin.closed:self.child.stdin.close()
   try:self.child.wait(timeout=5)
   except subprocess.TimeoutExpired:self.record['collector_exit_unknown']=True;self.c['save']();raise Rejected('COLLECTOR_EOF_5S')
  if self.out.exists():self.record.update(exit=self.child.returncode,report=read(self.out),stderr_present=bool(self.child.stderr.read(4096)))
  self.c['save']();return self.record.get('report')
def connection_pairs(stream,request):
 events=stream['pairs'];port=request.get('local_port');server=request.get('server_port');start=request['started_monotonic_ns'];end=request['finished_monotonic_ns']
 recv=[v for v in events if v['entry']['call']=='recvfrom' and v['entry'].get('fd_metadata',{}).get('kind')=='loopback_socket' and v['entry']['fd_metadata'].get('remote_port')==port and v['entry']['fd_metadata'].get('local_port')==server and start-10000000<=v['entry']['monotonic_ns']<=end]
 sent=[v for v in events if v['entry']['call'] in ['sendto','write'] and v['exit'].get('return',0)>0 and any(a['entry'].get('fd')==v['entry'].get('fd') and a['entry']['monotonic_ns']<=v['entry']['monotonic_ns']<=end+10000000 for a in recv)]
 return recv,sent
def run_fixture(c):
 role=c['role'];row=c['row'];execution=c['execution'];group=c['group'];check=c['check'];run=c['run'];ex=c['ex'];root=c['root'];folder=c['folder'];sessions=[];worker=None;workerlog=None
 meta,cid,init,actual=execution.identity(role);require(actual==group,'FIXTURE_GROUP');nsmeta=json.loads(run(['kubectl','get','namespace',c['ns'],'-o','json']).stdout)
 listener=c['core'].session.listener_owner(group);related=execution.processes(group,'/opt/dbs/bin/'+role)
 require(1<=len(related)<=2 and listener['executable_sha256']==VENDOR_SHA and listener['executable_path']=='/opt/dbs/bin/'+role and any(v[0]==listener['pid'] for v in related),'OWN_ORIGINAL_VENDOR_PROCESS_SET')
 row['selected_vendor_listener']=listener;row['related_same_vendor_ELF_instances']=related
 target=identity(listener['pid']);owner=identity(os.getpid());initinfo=identity(init)
 scope={'namespace':c['ns'],'namespace_uid':nsmeta['metadata']['uid'],'pod':role+'-business','pod_uid':meta['metadata']['uid'],'container_id':cid,'role':role,'fixture_root':str(folder),'container_init_pid':init,'container_init_start_ticks':initinfo['start_ticks']}
 plan={'owner_pid':owner['pid'],'owner_start_ticks':owner['start_ticks'],'pid':target['pid'],'start_ticks':target['start_ticks'],'executable_sha256':VENDOR_SHA,'cgroup':target['cgroup'],'maximum_seconds':180,'qualification_reader_delay_milliseconds':0,'vendor_fixture':scope}
 row['BPF_scope']=scope;c['save']()
 try:
  missing=Collector(c,'vendor-marker-missing',plan);sessions.append(missing);require(not missing.launch(True,False),'MISSING_MARKER_STARTED');v=missing.finish()
  check(role+'-missing-vendor-marker-refuses-before-BPF',v['phase']=='rejected' and v['reason']=='EXPLICIT_VENDOR_LAB_MARKER' and not v.get('program_ids') and not v.get('map_ids'))
  wrong=copy.deepcopy(plan);wrong['vendor_fixture']['namespace_uid']='00000000-0000-0000-0000-000000000000';negative=Collector(c,'wrong-namespace-uid',wrong);sessions.append(negative);require(not negative.launch(False),'READONLY_STARTED');v=negative.finish()
  check(role+'-wrong-real-namespace-UID-rejected-without-loading',v['phase']=='rejected' and v['reason']=='VENDOR_NAMESPACE_IDENTITY' and not v.get('program_ids') and not v.get('map_ids'))
  pre=Collector(c,'readonly-preflight',plan);sessions.append(pre);require(not pre.launch(False),'READONLY_STARTED');v=pre.finish()
  check(role+'-real-Pod-leaf-PID1-mount-executable-preflight-readonly',v['phase']=='preflight-readonly' and v['owned_vendor_fixture_validated'] and len(v['hooks'])==12 and not v.get('program_ids') and not v.get('map_ids'))
  qualify=Collector(c,'qualification',plan);sessions.append(qualify);require(qualify.launch(True),'VENDOR_ATTACH_FAILED')
  client=run(['nsenter','-t',str(init),'-n','--','python3',str(here/'qual-client.py')],False,timeout=8);request=json.loads(client.stdout);row['qualification_client']=request;time.sleep(.1);v=qualify.finish();recv,sent=connection_pairs(v,request)
  check(role+'-actual-vendor-connection-bound-and-clean-detach',client.returncode==0 and request['request_ok'] and recv and sent and v['all_owned_handles_closed'] and v['detached_stream_drained_to_deadline'] and not v['perf_lost_samples'] and not v['bpf_output_failures'] and not v['diagnostic_errors'] and not v['cleanup_errors'] and not v['target_signals_or_control_writes'] and identity(target['pid'])['start_ticks']==target['start_ticks'])
  row['vendor_tool_qualification_accepted']=True;c['save']()
  # One bounded diagnostic. It is deliberately not formal 600s acceptance.
  observe=Collector(c,'diagnostic120',plan);sessions.append(observe);require(observe.launch(True),'DIAGNOSTIC_ATTACH_FAILED')
  for name,entry in [('tests/vendor-soak-load.py','/tmp/crg-bpf676-original.py'),('native-transport.py','/tmp/crg-bpf676-worker.py')]:
   source=c['legacy']/name if name.startswith('tests/') else here/name;raw=source.read_bytes()
   cp=run(['kubectl','exec','-i','-n',c['ns'],role+'-business','-c',role,'--','/bin/bash','-c','set -Ce; umask 077; cat > '+entry+'; chmod 0444 '+entry],input=raw.decode())
   require(ex(role,'sha256sum',entry).stdout.split()[0]==hashlib.sha256(raw).hexdigest(),'WORKER_COPY')
  runid='20261112676'+('0' if role=='dbs' else '1');workerlog=(root/(role+'-native120.log')).open('x');os.chmod(workerlog.name,0o600)
  worker=subprocess.Popen(['kubectl','exec','-n',c['ns'],role+'-business','-c',role,'--','su','-','postgres','-c','CRG_VENDOR_SOAK_TEST=disposable-loopback-only python /tmp/crg-bpf676-worker.py --run-id '+runid+' --seconds 120 --test-phase smoke'],stdin=subprocess.DEVNULL,stdout=workerlog,stderr=workerlog)
  row['native120_exec_identity']=identity(worker.pid);load=folder/('postgresql/basebackup/crg-soak-'+runid+'/load.json');deadline=time.monotonic()+360
  while time.monotonic()<deadline:
   require(worker.poll() is None,'NATIVE_PREP_EXIT')
   if load.exists() and read(load).get('phase')=='running':break
   c['reserve']();time.sleep(.5)
  else:raise Rejected('NATIVE_PREPARATION_360S')
  original=c['core'].MANUAL;fixed=c['core'].controls(group);row['diagnostic_reload_intervals']=[]
  def change(name,policy,numeric):
   require(worker.poll() is None,'NATIVE_DIAGNOSTIC_ENDED_EARLY');began=time.monotonic_ns();mark=execution.write_config(folder,policy);deadline=time.monotonic()+60
   while time.monotonic()<deadline:
    status=read(folder/'resource-state/status.json');cfg=status.get('configuration',{})
    if (folder/'resource-state/status.json').stat().st_mtime_ns>mark and status.get('state')=='managed' and cfg.get('state')=='accepted' and all((group/k).read_text().strip()==value for k,value in numeric.items()):break
    c['reserve']();time.sleep(.25)
   else:raise Rejected('DIAGNOSTIC_RELOAD_60S')
   row['diagnostic_reload_intervals'].append({'name':name,'started_monotonic_ns':began,'ended_monotonic_ns':time.monotonic_ns(),'actual_controls':c['core'].controls(group),'configuration':cfg});c['save']()
  native_started=datetime.datetime.fromisoformat(read(load)['started_utc'].replace('Z','+00:00')).timestamp()
  while time.time()<native_started+30:c['reserve']();time.sleep(min(1,max(0,native_started+30-time.time())))
  # Keep the original campaign's +30s engine schedule and unmodified engine
  # content workload. Its result remains pending formal surrounding acceptance.
  execution.engine_log=(root/(role+'-engine.log')).open('x');os.chmod(execution.engine_log.name,0o600)
  execution.engine_job=subprocess.Popen(['python3',str(here/'engine-original.py'),'--namespace',c['ns'],'--work-dir',str(root/(role+'-engine')),'--run-id',runid+'00','--cleanup-fixture','--native-campaign-probes','--role',role],stdin=subprocess.DEVNULL,stdout=execution.engine_log,stderr=execution.engine_log)
  row['engine_exec_identity']=identity(execution.engine_job.pid);row['engine_started_offset_seconds']=time.time()-native_started;c['save']()
  change('manual-to-percent-A-during-engine',c['core'].POLICIES[0],c['core'].EXPECTED[0]);time.sleep(10);change('percent-A-to-manual-original',original,{k:fixed[k] for k in ['cpu.max','memory.high','io.max']})
  try:worker.wait(timeout=180)
  except subprocess.TimeoutExpired:raise Rejected('NATIVE120_NATURAL_COMPLETION_TIMEOUT')
  row['native120_exec_exit']=worker.returncode;row['native120']=read(load);v=observe.finish()
  try:execution.engine_job.wait(timeout=120)
  except subprocess.TimeoutExpired:row['engine_exec_exit_unknown_at_diagnostic_return']=True
  row['engine_exec_exit']=execution.engine_job.poll();engine_report=root/(role+'-engine/business-backup.json')
  if engine_report.exists():row['engine_content_report']=read(engine_report)
  transports=load.with_name('transport-events.jsonl');raw=transports.read_bytes();require(len(raw)<=1024*1024,'TRANSPORT_BOUND');requests=[json.loads(line) for line in raw.splitlines()];row['transport_requests']=requests
  native=row['native120'];row['diagnostic_request_summary']={'API_attempts':native['api']['attempts'],'API_errors':native['api']['errors'],'SQL_attempts':native['sql']['attempts'],'SQL_errors':native['sql']['errors'],'actual_seconds':native['elapsed_seconds'],'formal600_accepted':False}
  check(role+'-bounded-native120-finishes-and-client-transport-covers-every-API',native['requested_duration_seconds']==120 and native['elapsed_seconds']>=120 and not native['interrupted'] and native['threads_stopped'] and len(requests)==native['api']['attempts'] and all(v.get('socket_timeout_seconds')==4 for v in requests) and sum(not v['success'] for v in requests)==native['api']['errors'])
  associations=[]
  for request in requests:
   recv,sent=connection_pairs(v,request);writes=[]
   for w in v.get('pairs',[]):
    e=w['entry']
    if e['call']=='write' and e.get('fd_metadata',{}).get('kind')=='vendor_log' and any(a['entry']['tid']==e['tid'] and a['entry']['monotonic_ns']<=e['monotonic_ns']<=request['finished_monotonic_ns'] for a in recv):writes.append({'tid':e['tid'],'started_monotonic_ns':e['monotonic_ns'],'elapsed_ns':w['elapsed_ns'],'return':w['exit'].get('return',0),'path':e['fd_metadata']['path']})
   associations.append({'request':request,'recv_pairs':len(recv),'send_or_write_pairs':len(sent),'same_TID_vendor_log_write_candidates':writes,'causal_proof':False})
  row['request_associations']=associations;row['no_observed_output_loss_and_owned_collector_cleanly_stopped']=v['phase']=='collected' and v.get('reason')=='controller-stdin' and not v['perf_lost_samples'] and not v['bpf_output_failures'] and not v['diagnostic_errors'] and v['all_owned_handles_closed'] and v['detached_stream_drained_to_deadline'];row['syscall_pair_boundary_incomplete']=v['incomplete']
  check(role+'-diagnostic-helper-detaches-and-original-listener-survives',v['all_owned_handles_closed'] and not v['cleanup_errors'] and not v['target_signals_or_control_writes'] and identity(target['pid'])['start_ticks']==target['start_ticks'])
  row.update(business_accepted=False,causal_attribution_accepted=False,formal600_accepted=False);c['save']()
 finally:
  for session in sessions:
   try:session.finish()
   except Exception as e:row.setdefault('BPF_cleanup_errors',[]).append(type(e).__name__)
  if worker is not None and worker.poll() is None:
   # Natural bounded worker completion is preferred. Pod cleanup remains owned
   # by the outer fixture after this diagnostic fails; no business PID signal.
   try:worker.wait(timeout=180)
   except subprocess.TimeoutExpired:row['native120_exec_exit_unknown']=True
  if workerlog is not None:workerlog.close()
  c['save']()
