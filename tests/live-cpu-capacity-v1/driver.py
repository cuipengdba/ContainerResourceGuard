"""Real CPU hotplug on an exclusive disposable hosted VM, never a user node."""
from pathlib import Path
import argparse,hashlib,json,os,platform,re,shutil,signal,subprocess,tempfile,time,traceback,uuid
P=argparse.ArgumentParser();P.add_argument('--binary',type=Path,required=True);P.add_argument('--holder',type=Path,required=True);P.add_argument('--plan',type=Path,required=True);P.add_argument('--output',type=Path,required=True);P.add_argument('--arch',required=True);A=P.parse_args()
assert os.geteuid()==0 and platform.system()=='Linux' and os.environ.get('CRG_CPU_HOTPLUG_TEST')=='exclusive-ephemeral-github-vm-only' and os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
PLAN=json.loads(A.plan.read_bytes());SHA=lambda b:hashlib.sha256(b).hexdigest();NONCE=uuid.uuid4().hex;LABEL='crg.cpu-hotplug-ci';TAG='crg-hotplug:'+NONCE
A.output=A.output.resolve();A.output.mkdir(parents=True,exist_ok=False);PRIVATE=Path(tempfile.mkdtemp(prefix='crg-cpu-hotplug-')).resolve();ITEMS=[];CPU=None
R={'schema':'crg-live-cpu-capacity-native-v1','phase':'preparing','driver_sha256':SHA(Path(__file__).read_bytes()),'plan_sha256':SHA(A.plan.read_bytes()),'source_revision':PLAN['source_revision'],'binary_sha256':SHA(A.binary.read_bytes()),'arch':A.arch,'kernel':platform.release(),'tests':[],'cases':[],'hotplug_events':[],'cleanup':{},'scope':PLAN['scope']}
FIELDS=['cpu.max','memory.max','memory.high','io.max','pids.max','cpu.weight','io.weight','memory.swap.max']
def save():
 p=A.output/'report.tmp';p.write_text(json.dumps(R,indent=2)+'\n');p.replace(A.output/'report.json')
def check(name,value,**extra):R['tests'].append({'name':name,'passed':bool(value),**extra});save()
def run(args,timeout=30,required=True):
 r=subprocess.run([str(x) for x in args],capture_output=True,timeout=timeout)
 if r.returncode and required:
  R['last_command_failure']={'argv':list(map(str,args)),'exit':r.returncode,'stdout':r.stdout.decode(errors='replace')[-8192:],'stderr':r.stderr.decode(errors='replace')[-8192:]};save();raise RuntimeError('fixture command failed')
 return r
def identity(pid):
 f=Path('/proc',str(pid),'stat').read_bytes().rsplit(b')',1)[1].split();return {'pid':int(pid),'start_ticks':int(f[19])}
def alive(p):
 try:return identity(p['pid'])==p and Path('/proc',str(p['pid']),'stat').read_bytes().rsplit(b')',1)[1].split()[0]!=b'Z'
 except (FileNotFoundError,ProcessLookupError):return False
def mask():return Path('/sys/devices/system/cpu/online').read_text().strip()
def numbers(value):return {n for part in value.split(',') for n in range(int(part.split('-')[0]),int(part.split('-')[-1])+1)}
INITIAL=mask();INITIAL_CPUS=numbers(INITIAL)
def owned(item):
 m=json.loads(run(['docker','inspect',item['id']]).stdout)[0]
 assert m['Id']==item['id'] and m['Config']['Labels'].get(LABEL)==NONCE and m['State']['Pid']==item['main']['pid'] and alive(item['main']) and Path('/proc',str(item['main']['pid']),'cgroup').read_text()==item['membership'] and item['group'].stat().st_ino==item['inode']
 return m
def controls(item):owned(item);return {n:(item['group']/n).read_text().strip() for n in FIELDS}
def actors(item):
 owned(item);found=[]
 for pid in (item['group']/'cgroup.procs').read_text().split():
  try:
   p=Path('/proc',pid)
   if (p/'cmdline').read_bytes().split(b'\0')[:2]==[b'/crg',b'run']:
    assert SHA((p/'exe').read_bytes())==R['binary_sha256'];v=identity(pid);found.append(v)
    if v not in item['seen']:item['seen'].append(v)
  except (FileNotFoundError,ProcessLookupError):pass
 assert len(found)<=1;return found
def ex(item,*args,**kw):owned(item);return run(['docker','exec',item['id'],*args],**kw)
def toggle(online):
 assert CPU and CPU['path'].stat().st_ino==CPU['inode'] and CPU['path'].stat().st_dev==CPU['device']
 before=mask();expected=set(INITIAL_CPUS) if online else INITIAL_CPUS-{CPU['number']}
 assert numbers(before) in [INITIAL_CPUS,INITIAL_CPUS-{CPU['number']}]
 CPU['path'].write_text('1' if online else '0')
 deadline=time.monotonic()+5
 while numbers(mask())!=expected and time.monotonic()<deadline:time.sleep(.05)
 after=mask();assert numbers(after)==expected
 R['hotplug_events'].append({'before':before,'after':after,'cpu':CPU['number'],'online':online,'monotonic':time.monotonic(),'actual_sysfs_write':True});save()
def snapshot(item,label):
 owned(item);n=len(numbers(mask()));quota=10000 if item['tight'] else n*20000;expected=str(quota)+' 100000';deadline=time.monotonic()+10;state=None
 while time.monotonic()<deadline:
  try:state=json.loads((item['folder']/'state/status.json').read_bytes())
  except (FileNotFoundError,ValueError):time.sleep(.1);continue
  if state.get('plan',{}).get('environment',{}).get('host_online_cpus')==n and controls(item)['cpu.max']==expected:break
  time.sleep(.2)
 assert state is not None
 raw=(item['folder']/'state/status.json').read_bytes();state=json.loads(raw);assert len(raw)<1024**2
 path=item['out']/(label+'-status.json');path.write_bytes(raw)
 fresh=ex(item,'/crg','doctor','--config','/etc/crg/config.json');freshvalue=json.loads(fresh.stdout);(item['out']/(label+'-fresh-plan.json')).write_bytes(fresh.stdout)
 actual=controls(item);who=actors(item);metadata=state.get('plan',{}).get('environment',{});samples=item['record']['samples'];samples.append({'label':label,'online_mask':mask(),'online_count':n,'expected_cpu_max':expected,'actual_controls':actual,'reported_online_cpus':metadata.get('host_online_cpus'),'fresh_cli_online_cpus':freshvalue['environment']['host_online_cpus'],'agent':who,'status_file':path.name,'status_sha256':SHA(raw),'fresh_plan_sha256':SHA(fresh.stdout),'journal_present':(item['folder']/'state/journal.json').exists()})
 prefix=item['name']+':'+label
 check(prefix+':same-single-Agent-and-PID1',who==[item['agent']] and alive(item['main']))
 check(prefix+':current-host-capacity-in-live-status',metadata.get('host_online_cpus')==n,actual=metadata.get('host_online_cpus'),expected=n)
 check(prefix+':live-percent-kernel-quota',actual['cpu.max']==expected,actual=actual['cpu.max'],expected=expected)
 check(prefix+':fresh-CLI-agrees-with-independent-host',freshvalue['environment']['host_online_cpus']==n)
 check(prefix+':other-seven-controls-retained',all(actual[k]==item['original'][k] for k in FIELDS if k!='cpu.max'))
 assert numbers(mask())==numbers(samples[-1]['online_mask']);save()
def launch(name,tight):
 folder=PRIVATE/name;folder.mkdir();out=A.output/name;out.mkdir()
 for n in ['config','state']:(folder/n).mkdir(mode=0o700)
 cfg={'cpu_percent':20,'memory_percent':20,'io_percent':20,'io_calibration':'off','state_dir':'/state','log_dir':'/state/logs','interval_seconds':1}
 (folder/'config/config.json').write_text(json.dumps(cfg))
 args=['docker','run','-d','--name','crg-hotplug-'+NONCE+'-'+name,'--label',LABEL+'='+NONCE,'--network','none','--cgroupns','host','--privileged','--memory','512m','--memory-swap','512m','--cpus',str(len(INITIAL_CPUS)),
 '--mount','type=bind,src=/sys/fs/cgroup,dst=/sys/fs/cgroup','--mount','type=bind,src=/sys/devices/system/cpu,dst=/host/sys/devices/system/cpu,readonly']
 for n,target in [('config','/etc/crg'),('state','/state')]:args+=['--mount','type=bind,src='+str(folder/n)+',dst='+target]
 cid=run(args+[TAG]).stdout.decode().strip();assert re.fullmatch('[0-9a-f]{64}',cid);m=json.loads(run(['docker','inspect',cid]).stdout)[0];pid=m['State']['Pid'];membership=Path('/proc',str(pid),'cgroup').read_text();assert re.fullmatch('0::/[^\n]*\n',membership)
 group=Path('/sys/fs/cgroup')/membership.strip().split('::')[1].lstrip('/');assert group.resolve()==group and group.name in [cid,'docker-'+cid+'.scope']
 assert m['Config']['Labels'].get(LABEL)==NONCE and m['HostConfig']['CgroupnsMode']=='host' and m['HostConfig']['NetworkMode']=='none' and all(Path('/proc',str(pid),'ns',n).stat().st_ino!=Path('/proc/1/ns',n).stat().st_ino for n in ['pid','mnt','net'])
 item={'name':name,'id':cid,'main':identity(pid),'group':group,'inode':group.stat().st_ino,'membership':membership,'folder':folder,'out':out,'tight':tight,'seen':[]};ITEMS.append(item)
 (group/'memory.high').write_text(str(384*1024**2))
 if tight:(group/'cpu.max').write_text('10000 100000')
 item['original']=controls(item);item['oom']=dict(x.split() for x in (group/'memory.events').read_text().splitlines())['oom_kill']
 item['record']={'name':name,'container_id':cid,'PID1':item['main'],'cgroup':str(group),'original_controls':item['original'],'tight_external_cap':tight,'configuration':cfg,'samples':[]};R['cases'].append(item['record'])
 stdout=(out/'agent.stdout').open('wb');stderr=(out/'agent.stderr').open('wb');job=subprocess.Popen(['docker','exec',cid,'/crg','run','--config','/etc/crg/config.json'],stdout=stdout,stderr=stderr);item['job']=(job,stdout,stderr)
 deadline=time.monotonic()+20
 while time.monotonic()<deadline:
  who=actors(item)
  if who and (folder/'state/status.json').exists():item['agent']=who[0];break
  assert job.poll() is None;time.sleep(.1)
 else:raise RuntimeError('candidate start deadline')
 return item
def finish(item):
 if item.get('removed'):return
 owned(item);who=actors(item)
 if who:
  p=who[0];assert alive(p);os.kill(p['pid'],signal.SIGTERM)
 if 'job' in item:
  job,stdout,stderr=item['job'];job.wait(timeout=15);stdout.close();stderr.close()
 assert not actors(item)
 result=ex(item,'/crg','restore','--config','/etc/crg/config.json',required=False);value=json.loads(result.stdout);(item['out']/'restore.json').write_bytes(result.stdout)
 check(item['name']+':restore-original-eight-controls',result.returncode==0 and value['state']=='restored' and controls(item)==item['original'])
 journal=item['folder']/'state/journal.json'
 if journal.exists():assert not json.loads(journal.read_bytes())['mutations']
 else:assert item['tight'] and len(item['record']['samples'])==5 and all(not row['journal_present'] and row['actual_controls']==item['original'] for row in item['record']['samples'])
 check(item['name']+':no-OOM-kill',dict(x.split() for x in (item['group']/'memory.events').read_text().splitlines())['oom_kill']==item['oom'])
 owned(item);run(['docker','rm','-f',item['id']]);item['removed']=True
 check(item['name']+':owned-container-leaf-and-processes-absent',not item['group'].exists() and not alive(item['main']) and all(not alive(p) for p in item['seen']))
 for n in ['journal.json','status.json']:
  p=item['folder']/'state'/n
  if p.exists():(item['out']/n).write_bytes(p.read_bytes())
 item['record']['registered_agents']=item['seen'];save()
try:
 assert R['binary_sha256']==PLAN['binary_sha256'][A.arch] and R['driver_sha256']==PLAN['test_inputs_sha256']['tests/live-cpu-capacity-v1/driver.py'] and len(INITIAL_CPUS)>=2 and 0 in INITIAL_CPUS
 assert platform.machine() in {'amd64':['x86_64'],'arm64':['aarch64','arm64']}[A.arch] and not run(['docker','ps','-q']).stdout.strip() and json.loads(run(['docker','context','inspect']).stdout)[0]['Endpoints']['docker']['Host']=='unix:///var/run/docker.sock'
 number=max(INITIAL_CPUS);path=Path('/sys/devices/system/cpu/cpu'+str(number)+'/online');assert number!=0 and path.read_text().strip()=='1';CPU={'number':number,'path':path,'inode':path.stat().st_ino,'device':path.stat().st_dev};R['initial_online_mask']=INITIAL;R['selected_CPU']={k:str(v) if isinstance(v,Path) else v for k,v in CPU.items()};save()
 image=PRIVATE/'image';image.mkdir()
 for src,n in [(A.binary,'crg'),(A.holder,'hold')]:shutil.copyfile(src,image/n);(image/n).chmod(0o755)
 (image/'Dockerfile').write_text('FROM scratch\nCOPY crg hold /\nENTRYPOINT ["/hold"]\n');run(['docker','build','--label',LABEL+'='+NONCE,'-t',TAG,image],timeout=90)
 for name,tight in [('uncapped-percent',False),('external-cap',True)]:
  item=launch(name,tight);snapshot(item,'initial')
  for cycle in range(2):
   toggle(False);snapshot(item,'offline-'+str(cycle));toggle(True);snapshot(item,'online-'+str(cycle))
  finish(item)
 R['phase']='passed' if all(t['passed'] for t in R['tests']) else 'failed'
except BaseException as error:R.update(phase='failed',error=type(error).__name__+': '+str(error),traceback=traceback.format_exc())
finally:
 errors=[]
 try:
  if CPU:toggle(True)
 except BaseException as error:errors.append('CPU restore: '+str(error))
 for item in ITEMS:
  try:finish(item)
  except BaseException as error:errors.append('fixture cleanup: '+str(error))
 try:
  result=run(['docker','image','inspect',TAG],required=False)
  if result.returncode==0:
   meta=json.loads(result.stdout)[0];assert meta['Config'].get('Labels',{}).get(LABEL)==NONCE;run(['docker','image','rm',TAG])
 except BaseException as error:errors.append('image cleanup: '+str(error))
 R['cleanup']={'errors':errors,'original_online_mask_restored':mask()==INITIAL,'all_owned_containers_removed':all(i.get('removed') for i in ITEMS),'private_files_retained_for_VM_disposal':True}
 if errors or mask()!=INITIAL:R['phase']='failed'
 save()
print(json.dumps({'phase':R['phase'],'checks':len(R['tests']),'passed':sum(t['passed'] for t in R['tests']),'failed':[t['name'] for t in R['tests'] if not t['passed']],'error':R.get('error'),'cleanup':R['cleanup']}));raise SystemExit(0 if R['phase']=='passed' else 1)
