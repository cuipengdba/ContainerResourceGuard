#!/usr/bin/env python3
"""Opt-in, isolated vendor-image memory.high checks; never a product controller."""
import argparse,hashlib,json,os,pathlib,re,signal,subprocess,time,traceback
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',required=True,type=pathlib.Path);p.add_argument('--plan-sha256',required=True);a=p.parse_args()
assert os.geteuid()==0 and os.environ.get('CRG_MEMORY_HIGH_TEST')=='authorized-isolated-vendor-images-only'
raw=a.plan.read_bytes();assert hashlib.sha256(raw).hexdigest()==a.plan_sha256;plan=json.loads(raw)
tools=pathlib.Path(plan['tools']);root=pathlib.Path(plan['output']);ns=plan['namespace'];assert re.fullmatch('crg-memory-high[0-9]+-[0-9]+',ns)
assert str(tools).startswith('/var/tmp/crg-memory-high') and str(root).startswith('/var/tmp/crg-memory-high') and not root.exists()
for name,want in plan['files'].items():assert hashlib.sha256((tools/name).read_bytes()).hexdigest()==want
os.umask(0o077);root.mkdir(mode=0o700)
report={'schema':'crg-vendor-memory-high-v1','phase':'running','plan_sha256':a.plan_sha256,'source_revision':plan['source_revision'],'binary_sha256':plan['files']['crg'],'kernel':os.uname().release,'scope':'isolated placeholder PID1 in original vendor images; no original business data or service startup','tests':[],'roles':{},'owned_cgroups':[],'owned_processes':[],'cleanup':{},'stable_release_accepted':False}
def save():
 q=root/'report.candidate';q.write_text(json.dumps(report,indent=2)+'\n');q.replace(root/'report.json')
def record(name,passed,**values):
 report['tests'].append(dict(name=name,passed=bool(passed),**values));save();assert passed,name
def run(cmd,timeout=30,check=True,input=None):
 q=subprocess.run([str(x) for x in cmd],input=input,capture_output=True,text=True,timeout=timeout)
 if check and q.returncode:raise RuntimeError(json.dumps({'operation':cmd[:3],'exit':q.returncode,'stderr':q.stderr[-1600:],'stdout':q.stdout[-1600:]}))
 return q
def create(v):return json.loads(run(['kubectl','create','-f','-','-o','json'],input=json.dumps(v)).stdout)
def get(kind,name):
 q=run(['kubectl','get',kind,name,'-n',ns,'-o','json','--ignore-not-found']);return json.loads(q.stdout) if q.stdout.strip() else None
def proc(pid):
 s=pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split();return {'pid':pid,'start_ticks':int(s[19])}
fields=['memory.max','memory.high','cpu.max','io.max','memory.swap.max','pids.max','cpu.weight','io.weight']
def controls(g):return {n:(g/n).read_text().strip() for n in fields}
def sample(g):
 def pairs(n):return {k:int(v) for k,v in (l.split() for l in (g/n).read_text().splitlines())}
 return {'current':int((g/'memory.current').read_text()),'stat':pairs('memory.stat'),'events':pairs('memory.events'),'controls':controls(g),'monotonic':time.monotonic()}
def ex(pod,*cmd,**kw):return run(['kubectl','exec','-n',ns,pod,'--',*cmd],**kw)
def call(pod,config,legacy=False,cmd='run',expected_exit=0):
 command=['/tools/legacy-crg' if legacy else '/tools/crg',cmd,'--config','/work/'+config]
 if cmd=='run':command+=['--once']
 start=time.monotonic();q=ex(pod,*command,check=False,timeout=35)
 row={'exit':q.returncode,'stdout':q.stdout,'stderr':q.stderr,'elapsed_seconds':time.monotonic()-start};report.setdefault('commands',[]).append(row);save()
 assert q.returncode==expected_exit,row;return json.loads(q.stdout)
def config(folder,name,limits,state='state'):
 (folder/name).write_text(json.dumps({'resource_mode':'manual','limits':limits,'state_dir':'/work/'+state,'log_dir':'/work/logs','io_calibration':'off'}))
def launch(role,round_id,folder,privileged=True):
 src=plan['roles'][role];name=role+'-'+round_id
 volumes=[{'name':'tools','hostPath':{'path':str(tools),'type':'Directory'}},{'name':'work','hostPath':{'path':str(folder),'type':'Directory'}}]
 mounts=[{'name':'tools','mountPath':'/tools','readOnly':True},{'name':'work','mountPath':'/work'}]
 secure={'privileged':True} if privileged else {'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']}}
 create({'apiVersion':'v1','kind':'Pod','metadata':{'name':name,'namespace':ns,'labels':{'managed-by':'crg-memory-high-test'}},'spec':{'nodeName':src['node'],'restartPolicy':'Never','automountServiceAccountToken':False,'enableServiceLinks':False,'activeDeadlineSeconds':420,'terminationGracePeriodSeconds':3,'containers':[{'name':role,'image':src['image'],'imagePullPolicy':'Never','command':['/bin/bash','-c','while :; do sleep 1; done'],'securityContext':secure,'resources':{'requests':{'cpu':'50m','memory':'32Mi'},'limits':{'cpu':'2','memory':'512Mi'}},'volumeMounts':mounts}],'volumes':volumes}})
 uid=get('pod',name)['metadata']['uid'];run(['kubectl','wait','-n',ns,'--for=condition=Ready','pod/'+name,'--timeout=60s'],timeout=70)
 v=get('pod',name);s=v['status']['containerStatuses'][0];assert s['imageID']==src['image_id'] and s['restartCount']==0
 cid=s['containerID'].split('://')[1];pid=json.loads(run(['crictl','inspect',cid]).stdout)['info']['pid'];member=pathlib.Path('/proc',str(pid),'cgroup').read_text().strip();assert member.startswith('0::/') and '\n' not in member
 g=pathlib.Path('/sys/fs/cgroup')/member[3:].lstrip('/');assert cid in str(g) and uid.replace('-','_') in str(g).replace('-','_')
 main=proc(pid);report['owned_processes'].append(main);report['owned_cgroups']+=list(dict.fromkeys([str(g),str(g.parent)]));save()
 if privileged:run(['nsenter','-t',str(pid),'-n','--','ip','link','set','dev','eth0','down'])
 original=controls(g);assert original['memory.max']==str(512<<20) and original['memory.high']=='max'
 return {'name':name,'uid':uid,'container_id':cid,'main':main,'group':str(g),'original':original,'image_id':s['imageID'],'privileged':privileged}
def delete(item):
 assert proc(item['main']['pid'])==item['main']
 run(['kubectl','delete','pod',item['name'],'-n',ns,'--wait=true','--timeout=45s'],timeout=55)
 deadline=time.monotonic()+15;g=pathlib.Path(item['group'])
 while (g.exists() or g.parent.exists()) and time.monotonic()<deadline:time.sleep(.2)
 assert get('pod',item['name']) is None and not g.exists() and not g.parent.exists()
 item['pod_and_cgroups_absent']=True;save()
save()
try:
 assert not run(['kubectl','get','namespace',ns,'--ignore-not-found']).stdout.strip()
 create({'apiVersion':'v1','kind':'Namespace','metadata':{'name':ns,'labels':{'managed-by':'crg-memory-high-test'}}})
 create({'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'deny-all','namespace':ns},'spec':{'podSelector':{},'policyTypes':['Ingress','Egress']}})
 for role in ['dbs','hisdbs']:
  folder=root/role;folder.mkdir(mode=0o700);config(folder,'legacy.json',{'memory_max':'256MiB'});config(folder,'high.json',{'memory_high':'64MiB'});config(folder,'conflict.json',{'memory_max':'128MiB'},'conflict');config(folder,'conflict-high.json',{'memory_high':'64MiB'},'conflict')
  row={'boots':[]};report['roles'][role]=row;item=launch(role,'first',folder);row['boots'].append(item);save();pod=item['name'];g=pathlib.Path(item['group']);initial=sample(g)
  old=call(pod,'legacy.json',legacy=True);record(role+'-published-legacy-hard-cap',old['state']=='managed' and controls(g)['memory.max']==str(256<<20) and controls(g)['memory.high']=='max')
  new=call(pod,'legacy.json');j=json.loads((folder/'state/journal.json').read_text());record(role+'-owned-hard-cap-restored-before-high',controls(g)['memory.max']==str(512<<20) and controls(g)['memory.high']==str(256<<20) and 'memory.max:' not in j['mutations'] and new['plan']['memory_policy']=='high-reclaim-throttle',status=new)
  fill="import os; f=open('/work/clean-cache','wb'); b=b'x'*(1024*1024); [f.write(b) for _ in range(160)]; f.flush(); os.fsync(f.fileno()); f.close()"
  ex(pod,'python','-c',fill,timeout=35);before=sample(g);record(role+'-clean-cache-fixture',before['current']>128<<20 and before['stat']['file']>128<<20,before=before)
  value=call(pod,'high.json');time.sleep(2);after=sample(g);record(role+'-below-usage-high-reclaims-file-cache',after['controls']['memory.high']==str(64<<20) and after['controls']['memory.max']==str(512<<20) and before['current']-after['current']>=32<<20 and before['stat']['file']-after['stat']['file']>=32<<20 and after['events']['oom_kill']==initial['events']['oom_kill'] and after['events']['oom']==initial['events']['oom'],after=after,status=value)
  restored=call(pod,'high.json',cmd='restore');record(role+'-restore-retains-runtime-hard-limit',restored['state']=='restored' and controls(g)==item['original'])
  ex(pod,'rm','/work/clean-cache')
  anon="import os,time; b=bytearray(96*1024*1024); open('/work/anon-ready','w').write(str(os.getpid())); time.sleep(40)"
  ex(pod,'/bin/bash','-c',"nohup python -c "+__import__('shlex').quote(anon)+" crg-high-anon-probe-v1 >/work/anon.out 2>/work/anon.err </dev/null &",timeout=15)
  deadline=time.monotonic()+12
  while not (folder/'anon-ready').exists() and time.monotonic()<deadline:time.sleep(.2)
  assert (folder/'anon-ready').exists();probes=[]
  for rawpid in (g/'cgroup.procs').read_text().split():
   try:
    if b'crg-high-anon-probe-v1' in pathlib.Path('/proc',rawpid,'cmdline').read_bytes():probes.append(proc(int(rawpid)))
   except FileNotFoundError:pass
  assert len(probes)==1;probe=probes[0];report['owned_processes'].append(probe);anon_before=sample(g);assert anon_before['stat']['anon']>=96<<20
  # A sustained unreclaimable set throttles the writer too. Observe from the
  # host, then release ONLY the fixture's allocation before awaiting CLI exit.
  started=time.monotonic();writer=subprocess.Popen(['kubectl','exec','-n',ns,pod,'--','/tools/crg','run','--config','/work/high.json','--once'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  deadline=time.monotonic()+20
  while controls(g)['memory.high']!=str(64<<20) and writer.poll() is None and time.monotonic()<deadline:time.sleep(.05)
  time.sleep(2);anon_after=sample(g);record(role+'-anonymous-working-set-may-exceed-high',proc(probe['pid'])==probe and anon_after['current']>64<<20 and anon_after['controls']['memory.high']==str(64<<20) and anon_after['events']['oom']==initial['events']['oom'] and anon_after['events']['oom_kill']==initial['events']['oom_kill'],before=anon_before,after=anon_after,probe=probe,CLI_still_running_at_observation=writer.poll() is None)
  assert proc(probe['pid'])==probe;os.kill(probe['pid'],signal.SIGTERM)
  stdout,stderr=writer.communicate(timeout=35);duration=time.monotonic()-started;value=json.loads(stdout);report.setdefault('commands',[]).append({'exit':writer.returncode,'stdout':stdout,'stderr':stderr,'elapsed_seconds':duration,'fixture_allocation_released_before_wait':True})
  record(role+'-writer-recovers-after-fixture-allocation-release',writer.returncode==0 and value['state']=='managed' and controls(g)['memory.high']==str(64<<20),elapsed_seconds=duration)
  call(pod,'high.json',cmd='restore')
  (g/'memory.high').write_text(str(32<<20));external=call(pod,'high.json');record(role+'-stricter-external-high-preserved',controls(g)['memory.high']==str(32<<20) and external['state']=='degraded');call(pod,'high.json',cmd='restore');assert controls(g)['memory.high']==str(32<<20);(g/'memory.high').write_text('max')
  call(pod,'conflict.json',legacy=True);(g/'memory.max').write_text(str(384<<20));conflict=call(pod,'conflict-high.json');record(role+'-external-hard-change-not-restored',controls(g)['memory.max']==str(384<<20) and controls(g)['memory.high']==str(64<<20) and conflict['state']=='degraded' and json.loads((folder/'conflict/journal.json').read_text())['mutations']['memory.max:']['conflict'],status=conflict)
  incomplete=call(pod,'conflict-high.json',cmd='restore',expected_exit=1);assert incomplete['state']=='degraded' and controls(g)['memory.max']==str(384<<20);(g/'memory.max').write_text(str(512<<20));assert controls(g)==item['original']
  logs=list((folder/'logs').glob('crg-*.log'));events=[json.loads(l) for path in logs for l in path.read_text().splitlines()];record(role+'-daily-private-v2-and-policy-logs',len(logs)==1 and all(x.stat().st_mode&0o777==0o600 for x in logs) and any(x['event']=='cgroup_detected' and x.get('fields',{}).get('check',{}).get('cgroup_version')=='v2' for x in events) and any('high-reclaim-throttle' in json.dumps(x) for x in events))
  record(role+'-same-primary-identity-through-tests',proc(item['main']['pid'])==item['main']);first_identity=new['plan']['environment']['identity'];delete(item)
  item=launch(role,'second',folder);row['boots'].append(item);pod=item['name'];g=pathlib.Path(item['group']);fresh=call(pod,'high.json');record(role+'-new-id-rediscovered-and-old-journal-archived',item['uid']!=row['boots'][0]['uid'] and item['container_id']!=row['boots'][0]['container_id'] and fresh['plan']['environment']['identity']!=first_identity and (folder/'state/journal.previous.json').is_file() and controls(g)['memory.max']==str(512<<20) and controls(g)['memory.high']==str(64<<20))
  (folder/'percent.json').write_text(json.dumps({'cpu_percent':1,'memory_percent':.1,'io_percent':20,'io_calibration':'off','state_dir':'/work/percent-state','log_dir':'/work/logs'}));doctor=call(pod,'percent.json',cmd='doctor');settings={x['file']:x['value'] for x in doctor['settings']};expected=int(doctor['environment']['host_memory_bytes']*.1/100)//os.sysconf('SC_PAGESIZE')*os.sysconf('SC_PAGESIZE');record(role+'-independent-percent-plans-high',settings.get('memory.high')==str(min(expected,64<<20)) and 'memory.max' not in settings,plan=doctor)
  call(pod,'high.json',cmd='restore');record(role+'-new-id-restore',controls(g)==item['original']);delete(item)
  readonly=root/(role+'-readonly');readonly.mkdir(mode=0o700);config(readonly,'high.json',{'memory_high':'64MiB'});item=launch(role,'readonly',readonly,False);row['boots'].append(item);pod=item['name'];g=pathlib.Path(item['group']);denied=call(pod,'high.json');record(role+'-no-permission-keeps-placeholder-alive',denied['state']=='degraded' and all(x['state']!='applied' for x in denied['items']) and controls(g)==item['original'] and proc(item['main']['pid'])==item['main'],status=denied);delete(item)
 report['phase']='passed'
except Exception as exc:
 report.update(phase='failed',error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
finally:
 save()
 try:
  q=get('namespace',ns)
  if q:
   assert q['metadata']['labels'].get('managed-by')=='crg-memory-high-test';run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=50s'],timeout=60)
  report['cleanup']={'namespace_absent':get('namespace',ns) is None,'all_owned_cgroups_absent':all(not pathlib.Path(g).exists() for g in report['owned_cgroups'])}
  if not all(report['cleanup'].values()):report['phase']='failed'
 except Exception as exc:report.update(phase='failed',cleanup_error=str(exc))
 save()
 raise SystemExit(0 if report['phase']=='passed' else 1)
