import pathlib,json,subprocess,time,traceback,hashlib,os,shutil,math,platform,signal
w=pathlib.Path('/var/tmp/crg-final1404-tools-20261115');out=pathlib.Path('/var/tmp/crg-final1404-overhead-20261115');ns='crg-final1404-overhead-20261115';created=False;cases={};duration=1800
report={'phase':'preparing','source':'ced461705ebc27315a59aefe463f9b4af47130a3','scope':'three isolated placeholder PID1 containers; Agent only, not vendor business performance','criteria':{'actual_seconds':1800,'warmup_seconds':45,'sample_period_seconds':10,'interval_seconds':15,'CPU_single_core_percent_max':.1,'RSS_max_bytes':20*1024*1024,'stable_status_min_write_interval_seconds':299,'healthy_write_bytes_max':8*1024*1024,'fault_write_bytes_max':16*1024*1024,'host_available_min_bytes':8*1024**3,'host_disk_free_min_bytes':20*1024**3,'OOM_kill_delta_max':0,'io_cap_bps':65536,'io_cap_iops':8},'cases':{},'started':time.time(),'memory_policy':'high-reclaim-throttle','external_memory_max_bytes':268435456}
report['kernel']=platform.release();report['architecture']=platform.machine();report['job_sha256']=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
fields=['cpu.max','memory.max','io.max','pids.max','cpu.weight','io.weight','memory.high','memory.swap.max']
def process_identity(pid):
 text=pathlib.Path('/proc',str(pid),'stat').read_text();f=text[text.rfind(')')+2:].split()
 return {'pid':pid,'start_ticks':int(f[19])}
def controls(group):return {name:(group/name).read_text().strip() for name in fields}

def run(a,check=True,timeout=40):
 r=subprocess.run(a,capture_output=True,text=True,timeout=timeout)
 if check and r.returncode:raise RuntimeError(r.stderr[-1000:]+r.stdout[-1000:])
 return r
def create(o):
 r=subprocess.run(['kubectl','create','-f','-'],input=json.dumps(o),capture_output=True,text=True,timeout=30)
 if r.returncode:raise RuntimeError(r.stderr)
def save():
 temp=out/'report.candidate';temp.write_text(json.dumps(report,indent=2));temp.replace(out/'report.json')
def memavailable():return int(next(l.split()[1] for l in pathlib.Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
def protect():
 if memavailable()<report['criteria']['host_available_min_bytes'] or shutil.disk_usage(out).free<report['criteria']['host_disk_free_min_bytes']:raise RuntimeError('host reserve threshold')
def agentpid(g):
 found=[]
 for line in (g/'cgroup.procs').read_text().splitlines():
  p=pathlib.Path('/proc')/line
  try:
   args=(p/'cmdline').read_bytes().split(b'\0')
   if len(args)>1 and args[1]==b'run' and pathlib.Path(os.readlink(p/'exe')).name=='crg-linux-amd64':found.append(int(line))
  except (OSError,ValueError):pass
 if len(found)!=1:raise RuntimeError('not exactly one own Agent')
 return found[0]
def sample(c):
 p=pathlib.Path('/proc')/str(c['pid']);stat=(p/'stat').read_text();f=stat[stat.rfind(')')+2:].split()
 status={l.split(':',1)[0]:l.split(':',1)[1].strip() for l in (p/'status').read_text().splitlines() if ':' in l}
 io={l.split(':')[0]:int(l.split(':')[1]) for l in (p/'io').read_text().splitlines()}
 s=json.loads((c['state']/'status.json').read_text());events=dict(l.split() for l in (c['group']/'memory.events').read_text().splitlines())
 stamp=(c['state']/'status.json').stat().st_mtime_ns
 r={'elapsed_seconds':time.monotonic()-started,'CPU_seconds':(int(f[11])+int(f[12]))/os.sysconf('SC_CLK_TCK'),'start_ticks':int(f[19]),'RSS_bytes':int(status['VmRSS'].split()[0])*1024,'write_bytes':io['write_bytes'],'wchar':io['wchar'],'OOM_kills':int(events['oom_kill']),'status_mtime_ns':stamp,'state':s['state'],'metrics_state':s.get('metrics',{}).get('state'),'events_state':s.get('events',{}).get('state'),'status_bytes':(c['state']/'status.json').stat().st_size,'journal_bytes':(c['state']/'journal.json').stat().st_size}
 r['daily_log_bytes']=sum(q.stat().st_size for q in (c['state']/'logs').glob('crg-*.log'))
 # Recheck only these fixture-owned processes and all8 actual controls.
 if process_identity(c['main_pid'])!=c['main_identity'] or pathlib.Path('/proc',str(c['main_pid']),'cgroup').read_text()!=c['membership']:raise RuntimeError('placeholder PID1 identity changed')
 if agentpid(c['group'])!=c['pid'] or pathlib.Path('/proc',str(c['pid']),'cgroup').read_text()!=c['membership']:raise RuntimeError('one-to-one Agent identity changed')
 actual=controls(c['group'])
 if actual!=c['expected_controls']:raise RuntimeError('actual fixture controls changed during overhead sample')
 r['actual_controls_unchanged']=True

 for f in ['metrics.prom','events.jsonl']:
  q=c['state']/f
  if q.exists() and not q.is_symlink():r[f+'_bytes']=q.stat().st_size
 return r
def stopped(signum,frame):raise RuntimeError('explicit overhead fixture stop requested')
signal.signal(signal.SIGTERM,stopped)
try:
 if os.geteuid()!=0 or platform.system()!='Linux' or platform.machine()!='x86_64' or os.environ.get('CRG_FINAL1404_OVERHEAD')!='authorized-disposable-test-node-only':raise RuntimeError('explicit authorized native test fixture required')
 plan=json.loads((w/'overhead-plan.json').read_bytes())
 if hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()!=plan['job_sha256']:raise RuntimeError('frozen job differs')
 for name,digest in plan['source_sha256'].items():
  if hashlib.sha256((w/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('frozen input differs')
 qualification=json.loads((w/'qualification.json').read_bytes())
 if qualification['phase']!='passed' or qualification['source_revision']!=report['source'] or qualification['version']!='v1.0.0' or qualification['actual_total_checks']!=284 or not qualification['all_actual_controller_programs_match_frozen_final_ELFs']:raise RuntimeError('fixed final284 qualification missing')
 report['qualification_sha256']=hashlib.sha256((w/'qualification.json').read_bytes()).hexdigest();report['plan_sha256']=hashlib.sha256((w/'overhead-plan.json').read_bytes()).hexdigest()
 if out.exists():raise RuntimeError('output already exists')
 out.mkdir(mode=0o700);save();protect()
 info=json.loads(run([str(w/'binaries/crg-linux-amd64'),'build-info']).stdout)
 if info.get('revision')!=report['source'] or info.get('arch')!='amd64' or info.get('os')!='linux' or info.get('go_version')!='go1.27.3' or info.get('version')!='v1.0.0':raise RuntimeError('candidate build-info differs')
 if info.get('memory_policy')!='high-reclaim-throttle; percentages may be exceeded; external hard limits retained' or info.get('io_percent_policy')!='calibrated-read-write-bandwidth; IOPS manual only; external IOPS retained':raise RuntimeError('final policy differs')
 report['build_info']=info
 report['binary_sha256']=hashlib.sha256((w/'binaries/crg-linux-amd64').read_bytes()).hexdigest()
 if report['binary_sha256']!='9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8':raise RuntimeError('candidate digest differs from frozen plan')
 if run(['kubectl','get','namespace',ns],False).returncode==0:raise RuntimeError('namespace exists')
 create({'apiVersion':'v1','kind':'Namespace','metadata':{'name':ns,'labels':{'managed-by':'crg-overhead-test'}}});created=True;report['namespace_uid']=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout)['metadata']['uid'];save()
 create({'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'deny-all','namespace':ns},'spec':{'podSelector':{},'policyTypes':['Ingress','Egress']}})
 for name in ['healthy','export-failure','readonly']:
  state=out/name;state.mkdir(mode=0o700)
  if name=='export-failure':
   (state/'marker').write_text('preserve');(state/'metrics.prom').symlink_to('/crgstate/marker');(state/'events.jsonl').symlink_to('/crgstate/marker')
  config={'resource_mode':'manual','limits':{'cpu_cores':.25,'memory_high':'128MiB','io_read_bps':'64KiB','io_write_bps':'64KiB','io_read_iops':8,'io_write_iops':8},'data_paths':['/crgstate'],'state_dir':'/crgstate','interval_seconds':15,'metrics_enabled':True,'events_enabled':True,'log_dir':'/crgstate/logs'}
  (out/(name+'.json')).write_text(json.dumps(config))
  volumes=[{'name':'program','hostPath':{'path':str(w),'type':'Directory'}},{'name':'work','hostPath':{'path':str(out),'type':'Directory'}},{'name':'state','hostPath':{'path':str(state),'type':'Directory'}}]
  mounts=[{'name':'program','mountPath':'/opt/crg','readOnly':True},{'name':'work','mountPath':'/fixture','readOnly':True},{'name':'state','mountPath':'/crgstate'}]
  if name=='readonly':volumes.append({'name':'cgroup','hostPath':{'path':'/sys/fs/cgroup','type':'Directory'}});mounts.append({'name':'cgroup','mountPath':'/sys/fs/cgroup','readOnly':True})
  pod={'apiVersion':'v1','kind':'Pod','metadata':{'name':name,'namespace':ns},'spec':{'automountServiceAccountToken':False,'terminationGracePeriodSeconds':10,'restartPolicy':'Never','containers':[{'name':'self','image':'db_puc/dbs:V7.0.12.001.02.56','imagePullPolicy':'Never','command':['/bin/bash','/opt/crg/examples/supervisor.sh','/bin/bash','-c','while :; do sleep 300; done'],'env':[{'name':'CRG_BIN','value':'/opt/crg/binaries/crg-linux-amd64'},{'name':'CRG_CONFIG','value':'/fixture/'+name+'.json'}],'securityContext':{'privileged':True},'resources':{'requests':{'cpu':'10m','memory':'16Mi'},'limits':{'cpu':'1','memory':'256Mi'}},'volumeMounts':mounts}],'volumes':volumes}}
  create(pod);run(['kubectl','wait','-n',ns,'--for=condition=Ready','pod/'+name,'--timeout=90s'],timeout=100)
  m=json.loads(run(['kubectl','get','pod','-n',ns,name,'-o','json']).stdout);cid=m['status']['containerStatuses'][0]['containerID'].split('://')[1]
  mainpid=json.loads(run(['crictl','inspect',cid]).stdout)['info']['pid'];own=next(l.split('::',1)[1] for l in pathlib.Path('/proc/%d/cgroup'%mainpid).read_text().splitlines() if l.startswith('0::'));g=pathlib.Path('/sys/fs/cgroup')/own.lstrip('/')
  if g.name!='cri-containerd-'+cid+'.scope' or '/kubepods.slice/' not in str(g):raise RuntimeError('not own leaf')
  if m['metadata']['namespace']!=ns or any(m['spec'].get(k,False) for k in ['hostNetwork','hostPID','hostIPC']) or mainpid<=1 or any(pathlib.Path('/proc',str(mainpid),'ns',kind).stat().st_ino==pathlib.Path('/proc/1/ns',kind).stat().st_ino for kind in ['net','pid','mnt']):raise RuntimeError('fixture namespace identity guard failed')
  if name=='readonly':
   mounts=pathlib.Path('/proc/%d/mountinfo'%mainpid).read_text().splitlines()
   own_mount=[l.split(' - ',1)[0].split() for l in mounts if l.split(' - ',1)[0].split()[4]=='/sys/fs/cgroup']
   if not own_mount or not all('ro' in f[5].split(',') for f in own_mount):raise RuntimeError('fixture cgroup mount is not actually read-only')
  end=time.monotonic()+90
  while not (state/'status.json').exists():
   if time.monotonic()>end:raise RuntimeError('startup status deadline')
   time.sleep(.3)
  s=json.loads((state/'status.json').read_text());settings=s['plan']['settings'];dev=next(x['device'] for x in settings if x['file']=='io.max')
  if name=='readonly':
   # Fixture-owned external cap, not a capability of the read-only Agent.
   (g/'io.max').write_text(dev+' rbps=65536 wbps=65536 riops=8 wiops=8\n')
  elif not all(x['state']=='applied' for x in s['items']):raise RuntimeError('not fully limited '+name)
  daily=list((state/'logs').glob('crg-*.log'));events=[json.loads(x) for f in daily for x in f.read_text().splitlines()]
  if not any(x['event']=='resource_status' and x.get('fields',{}).get('memory_policy')=='high-reclaim-throttle' for x in events):raise RuntimeError('high policy absent from daily logs')
  if not daily or not all(f.stat().st_mode&0o777==0o600 for f in daily) or not any(x['event']=='cgroup_detected' and x.get('fields',{}).get('check',{}).get('cgroup_version')=='v2' for x in events):raise RuntimeError('daily0600/v2 logs absent')
  pid=agentpid(g)
  if hashlib.sha256(pathlib.Path('/proc/%d/exe'%pid).read_bytes()).hexdigest()!=report['binary_sha256']:raise RuntimeError('unexpected running binary')
  actual=controls(g)
  if actual['io.max']!=dev+' rbps=65536 wbps=65536 riops=8 wiops=8':raise RuntimeError('fixed actual IO budget differs')
  if name!='readonly' and (actual['cpu.max']!='25000 100000' or actual['memory.high']!='134217728' or actual['memory.max']!='268435456' or len(s['items'])!=3):raise RuntimeError('fixed actual three-resource budget differs')
  cases[name]={'state':state,'group':g,'pid':pid,'main_pid':mainpid,'main_identity':process_identity(mainpid),'membership':pathlib.Path('/proc',str(mainpid),'cgroup').read_text(),'expected_controls':actual}
  report['cases'][name]={'samples':[],'cgroup_readonly':name=='readonly','fixture_external_IO':name=='readonly','settings':settings,'actual_controls':actual,'fixture_identity':{'pod_uid':m['metadata']['uid'],'container_id':cid,'group':str(g),'pod_parent':str(g.parent),'main':process_identity(mainpid),'Agent':process_identity(pid)}}
 report['phase']='warming';save()
 warm=time.monotonic()
 while time.monotonic()-warm<45:protect();time.sleep(1)
 started=time.monotonic();report['measurement_started_utc_epoch']=time.time();report['phase']='measuring';save();next_sample=started
 while True:
  protect()
  for name,c in cases.items():report['cases'][name]['samples'].append(sample(c))
  save();elapsed=time.monotonic()-started
  if elapsed>=duration:break
  next_sample+=10;time.sleep(max(0,min(next_sample,started+duration)-time.monotonic()))
 report['measurement_elapsed_seconds']=time.monotonic()-started
 for name,item in report['cases'].items():
  samples=item['samples'];a=samples[0];b=samples[-1];elapsed=b['elapsed_seconds']-a['elapsed_seconds'];writes=[];last=a['status_mtime_ns']
  for x in samples[1:]:
   if x['status_mtime_ns']!=last:writes.append(x['status_mtime_ns']);last=x['status_mtime_ns']
  cpu=(b['CPU_seconds']-a['CPU_seconds'])/elapsed*100;rss=max(x['RSS_bytes'] for x in samples);write_bytes=b['write_bytes']-a['write_bytes'];budget=8*1024**2 if name=='healthy' else 16*1024**2
  item['result']={'CPU_single_core_percent':cpu,'max_RSS_bytes':rss,'write_bytes_delta':write_bytes,'wchar_delta':b['wchar']-a['wchar'],'status_write_count':len(writes),'status_min_write_gap_seconds':min([(j-i)/1e9 for i,j in zip(writes,writes[1:])] or [300]),'OOM_kill_delta':b['OOM_kills']-a['OOM_kills'],'elapsed_seconds':elapsed,'same_Agent_process':all(x['start_ticks']==a['start_ticks'] for x in samples)}
  d=item['result'];item['passed']=elapsed>=duration-1 and cpu<=.1 and rss<=20*1024**2 and write_bytes<=budget and d['status_min_write_gap_seconds']>=299 and d['OOM_kill_delta']==0 and d['same_Agent_process']
  if name=='export-failure':item['passed']=item['passed'] and (cases[name]['state']/'marker').read_text()=='preserve' and all(x['metrics_state']=='unavailable' and x['events_state']=='unavailable' for x in samples)
  if name=='readonly':item['passed']=item['passed'] and all(x['state']=='degraded' for x in samples)
 report['phase']='passed' if all(x['passed'] for x in report['cases'].values()) else 'failed'
except Exception as e:
 report['phase']='failed';report['error']=str(e);report['traceback']=traceback.format_exc()
 if created:
  for name in ['healthy','export-failure','readonly']:
   try:(out/(name+'-failure.log')).write_text(run(['kubectl','logs','-n',ns,name,'--tail=20'],check=False).stdout)
   except Exception:pass
finally:
 if created:
  try:
   m=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout)
   if m['metadata']['uid']!=report['namespace_uid'] or m['metadata']['labels'].get('managed-by')!='crg-overhead-test':raise RuntimeError('cleanup label mismatch')
   run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=150s'],check=False,timeout=160);absent=run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json'],False);report['namespace_absent']=absent.returncode==0 and not absent.stdout.strip()
  except Exception as e:report['cleanup_error']=str(e)
 if out.exists():report['ended']=time.time();save()
print(json.dumps({'phase':report['phase'],'error':report.get('error'),'results':{k:v.get('result') for k,v in report['cases'].items()}}))

raise SystemExit(0 if report['phase']=='passed' and report.get('namespace_absent') is True and not report.get('cleanup_error') else 1)
