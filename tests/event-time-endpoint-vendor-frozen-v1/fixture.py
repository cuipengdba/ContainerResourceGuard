import pathlib,json,subprocess,time,traceback,hashlib,os,shutil,re,uuid,importlib.util,signal
root=pathlib.Path('/var/tmp/crg-bpf692-diagnostic-20261112');source=pathlib.Path('/var/tmp/crg-business-20261110');candidates=pathlib.Path(__file__).parent;legacy=pathlib.Path('/var/tmp/crg-high638-tools-20261112');ns='crg-vendor-lab-bpf692-20261112';created=False
report={'schema':'crg-vendor-event-time-kernel-endpoint-bounded-v1','phase':'preparing','roles':{},'tests':[],'business_accepted':False,'formal600_accepted':False,'causal_attribution_accepted':False,'stable_release_accepted':False,'scope':'fresh original vendor paths; tool qualification and one 120s diagnostic per role with original +30s engine content load, not a formal600 business retry','sources':{'v10':{'revision':'180c86ad7986a76526a41575cc1c176d5da98a9c','binary_sha256':'6088721cd4846f95b3b71c82f9884e1909797a199d962b50519c9e013de98b4e'}}}
planraw=(candidates/'plan.json').read_bytes();plan=json.loads(planraw)
assert plan['job_sha256']==hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest() and plan['namespace']==ns and plan['output']==str(root)
for name,digest in plan['source_sha256'].items():assert hashlib.sha256((candidates/name).read_bytes()).hexdigest()==digest
assert hashlib.sha256((legacy/'vendor-memory-high-pressure-core.py').read_bytes()).hexdigest()=='7f331574f797a96eaed11605164c8b7ef56927e457ee417b9ac12ebff15c8a38'
spec=importlib.util.spec_from_file_location('pressure_core',legacy/'vendor-memory-high-pressure-core.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
spec=importlib.util.spec_from_file_location('direct_bpf_diagnostic',candidates/'vendor-diagnostic.py');diagnostic=importlib.util.module_from_spec(spec);spec.loader.exec_module(diagnostic)

def interrupted(signum,frame):raise RuntimeError('isolated pressure driver interrupted')

def run(a,check=True,timeout=60,**kw):
 r=subprocess.run(a,capture_output=True,text=True,timeout=timeout,**kw)
 if check and r.returncode:raise RuntimeError('test command failed, exit='+str(r.returncode))
 return r

def create(o):
 r=subprocess.run(['kubectl','create','-f','-'],input=json.dumps(o),capture_output=True,text=True,timeout=30)
 if r.returncode:raise RuntimeError('fixture create failed')

def ex(role,*a,**kw):return run(['kubectl','exec','-n',ns,role+'-business','-c',role,'--',*a],**kw)

def save():(root/'report.json').write_text(json.dumps(report,indent=2))

def record(name,passed,**extra):
 report['tests'].append(dict(name=name,passed=bool(passed),**extra));save()
 if not passed:raise AssertionError(name)

def reserve(minimum=8):
 available=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 if available<minimum*1024**3 or shutil.disk_usage(root).free<20*1024**3:raise RuntimeError('node reserve threshold reached')
 return available

def delete_pod(role):
 m=json.loads(run(['kubectl','get','pod','-n',ns,role+'-business','-o','json']).stdout)
 if m['metadata']['labels'].get('managed-by')!='crg-vendor-test' or m['metadata']['namespace']!=ns:raise RuntimeError('cleanup ownership mismatch')
 run(['kubectl','delete','pod','-n',ns,role+'-business','--wait=true','--timeout=120s'],timeout=130)

signal.signal(signal.SIGTERM,interrupted)
try:
 root.mkdir(mode=0o700,exist_ok=False);report['job_sha256']=plan['job_sha256'];report['plan_sha256']=hashlib.sha256(planraw).hexdigest();save();reserve(28)
 for name,digest in {'fixture/containercacheguard':'757ba385a0ee4bdadc968b96b5c3e69fd44353060e5ab28520fd6f73a59902de','fixture/dbs/supervisor.sh':'4dce0b38e6c01a9effe08457dc31206a0abaf7ff14eb9ec59dace97a6f1c0211','fixture/hisdbs/supervisor.sh':'4dce0b38e6c01a9effe08457dc31206a0abaf7ff14eb9ec59dace97a6f1c0211'}.items():
  if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('original private fixture digest changed')
 gates=root/'gates';gates.mkdir(mode=0o700);aux=root/'aux';aux.mkdir(mode=0o700);shutil.copyfile('/usr/bin/etcd',aux/'etcd');(aux/'etcd').chmod(0o755)
 if run(['kubectl','get','namespace',ns],False).returncode==0:raise RuntimeError('namespace already exists')
 create({'apiVersion':'v1','kind':'Namespace','metadata':{'name':ns,'labels':{'managed-by':'crg-vendor-test'}}});created=True
 create({'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'deny-all','namespace':ns},'spec':{'podSelector':{},'policyTypes':['Ingress','Egress']}})
 images=json.loads((source/'vendor-import.json').read_text())['images']
 for index,(candidate,role,bandwidth) in enumerate([('v10','dbs',64),('v10','hisdbs',64)]):
  key=candidate+'-'+role+'-bw'+str(bandwidth);pod_created=False;campaign_job=None;execution=None;folder=None;original_config=None;item={'phase':'preparing','candidate_branch':candidate,'role':role,'declared_read_write_bps':bandwidth*1024**2};report['roles'][key]=item;save()
  try:
   available=reserve(28);case_root=root/key;case_root.mkdir(mode=0o700);folder=case_root/(role+'-business');folder.mkdir(mode=0o700)
   for n in ['postgresql','dbs','highgo','log','core','sql','hbp-runtime','resource-state','cache-state','etcd','ccg','crg','crg-config']:(folder/n).mkdir(mode=0o700)
   for n in ['bin','scripts','config']:(folder/'ccg'/n).mkdir(mode=0o700)
   cachepath='/home/ccg-backups/dbs' if role=='dbs' else '/opt/PUC-784/ccg-backups/hisdbs'
   shutil.copyfile(source/'fixture'/role/'supervisor.sh',folder/'ccg/scripts/business-supervisor.sh')
   shutil.copyfile(source/'fixture/containercacheguard',folder/'ccg/bin/containercacheguard');(folder/'ccg/bin/containercacheguard').chmod(0o755)
   binary=candidates/'binaries/crg-linux-amd64'
   if hashlib.sha256(binary.read_bytes()).hexdigest()!=report['sources'][candidate]['binary_sha256']:raise RuntimeError('candidate binary differs from recorded source-qualified digest')
   shutil.copyfile(binary,folder/'crg/crg');(folder/'crg/crg').chmod(0o755)
   shutil.copyfile(candidates/'examples/optional-agent.sh',folder/'crg/optional-agent.sh')
   cache=json.loads((source/'fixture'/role/'cache.json').read_text());cache['state_file']=cachepath+'/status.json';(folder/('ccg/config/'+role+'.json')).write_text(json.dumps(cache))
   (folder/'crg-config/config.json').write_text(json.dumps({'resource_mode':'manual','limits':{'cpu_cores':7.2,'memory_high':'20001980416B','io_read_bps':str(bandwidth)+'MiB','io_write_bps':str(bandwidth)+'MiB','io_read_iops':4096,'io_write_iops':4096},'data_paths':['/opt/postgresql']}))
   env=json.loads((source/'fixture'/role/'env.json').read_text());secret=uuid.uuid4().hex
   env.update(MY_POD_NAMESPACE=ns,MY_POD_NAME=role+'-realpath-0',PGPASSWORD=secret,CCG_BIN='/opt/ccg/bin/containercacheguard',CCG_CONFIG='/opt/ccg/config/'+role+'.json',CRG_BIN='/opt/crg/crg',CRG_CONFIG='/etc/crg/config.json',CRG_HELPER_SCRIPT='/opt/crg/optional-agent.sh',YSP_PRODUCT_TYPE='PUC-DBS')
   pg=(source/'fixture'/role/'postgres.yml').read_text();pg=re.sub(r'(?m)^(\s+password:).*$',r'\1 '+secret,pg).replace('namespace: /crg-isolated/','namespace: /crg-realpaths/')
   (folder/'postgres.yml').write_text(pg);(folder/'postgres.yml').chmod(0o600)
   shutil.copyfile('/etc/localtime',folder/'localtime');(folder/'timezone').write_text('Asia/Shanghai\n')
   vols=[];mounts=[]
   def volume(name,path,target,readonly=False,file=False):
    vols.append({'name':name,'hostPath':{'path':str(path),'type':'File' if file else 'Directory'}});mounts.append({'name':name,'mountPath':target,'readOnly':readonly})
   for n,target,readonly in [('postgresql','/opt/postgresql',False),('dbs','/opt/dbs',False),('highgo','/opt/highgo',False),('log','/var/log',False),('core','/opt/local/tmp/core',False),('hbp-runtime','/var/run/.hbp',False),('cache-state',cachepath,False),('resource-state','/tmp/containerresourceguard',False),('ccg','/opt/ccg',True),('crg','/opt/crg',True),('crg-config','/etc/crg',False)]:volume(n,folder/n,target,readonly)
   volume('pgconfig',folder/'postgres.yml','/home/config/postgres.yml',True,True);volume('localtime',folder/'localtime','/etc/localtime',False,True);volume('timezone',folder/'timezone','/etc/timezone',False,True)
   if role=='dbs':
    volume('sql',folder/'sql','/opt/dbs/sql');mounts.append({'name':'sql','mountPath':'/opt/sql'})
   else:
    vols.append({'name':'data','emptyDir':{}});mounts.append({'name':'data','mountPath':'/data'})
   for name,target,empty in [('shm','/dev/shm',{'medium':'Memory','sizeLimit':'1Gi'}),('hbp','/opt/hbp',{})]:vols.append({'name':name,'emptyDir':empty});mounts.append({'name':name,'mountPath':target})
   volume('gate',gates,'/network-gates',True)
   vols.extend([{'name':'aux','hostPath':{'path':str(aux),'type':'Directory'}},{'name':'etcd','hostPath':{'path':str(folder/'etcd'),'type':'Directory'}}])
   start='i=0; while [ ! -f "/network-gates/$CRG_TEST_POD_UID" ]; do i=$((i+1)); [ "$i" -lt 120 ] || exit 92; sleep 1; done; exec /bin/bash /opt/ccg/scripts/business-supervisor.sh'
   envs=[{'name':k,'value':v} for k,v in env.items()]+[{'name':'CRG_TEST_POD_UID','valueFrom':{'fieldRef':{'fieldPath':'metadata.uid'}}}]
   pod={'apiVersion':'v1','kind':'Pod','metadata':{'name':role+'-business','namespace':ns,'labels':{'managed-by':'crg-vendor-test'}},'spec':{'automountServiceAccountToken':False,'enableServiceLinks':False,'restartPolicy':'Never','terminationGracePeriodSeconds':30,'containers':[{'name':role,'image':images[role]['tag'],'imagePullPolicy':'Never','command':['/bin/bash','-c',start],'env':envs,'securityContext':{'privileged':True},'resources':{'requests':{'cpu':'100m','memory':'256Mi'},'limits':{'cpu':'8','memory':'20Gi'}},'volumeMounts':mounts},{'name':'isolated-dcs','image':images[role]['tag'],'imagePullPolicy':'Never','command':['/aux/etcd','--name','isolated','--data-dir','/isolated-etcd','--listen-client-urls','http://127.0.0.1:2379','--advertise-client-urls','http://127.0.0.1:2379','--listen-peer-urls','http://127.0.0.1:2380','--initial-advertise-peer-urls','http://127.0.0.1:2380','--initial-cluster','isolated=http://127.0.0.1:2380'],'resources':{'requests':{'cpu':'10m','memory':'32Mi'},'limits':{'cpu':'1','memory':'256Mi'}},'volumeMounts':[{'name':'aux','mountPath':'/aux','readOnly':True},{'name':'etcd','mountPath':'/isolated-etcd'}]}],'volumes':vols}}
   private=folder/'pod.json';private.write_text(json.dumps(pod));private.chmod(0o600);create(pod);pod_created=True
   run(['kubectl','wait','-n',ns,'--for=condition=Ready','pod/'+role+'-business','--timeout=90s'],timeout=100)
   meta=json.loads(run(['kubectl','get','pod','-n',ns,role+'-business','-o','json']).stdout);cid=next(x['containerID'].split('://')[1] for x in meta['status']['containerStatuses'] if x['name']==role)
   pid=json.loads(run(['crictl','inspect',cid]).stdout)['info']['pid'];group=pathlib.Path('/sys/fs/cgroup')/next(x.split('::',1)[1].lstrip('/') for x in pathlib.Path('/proc',str(pid),'cgroup').read_text().splitlines() if x.startswith('0::'))
   if group.name!='cri-containerd-'+cid+'.scope':raise RuntimeError('self leaf mismatch')
   extra_files=['pids.max','cpu.weight','io.weight','memory.max','memory.swap.max'];extra_original={f:(group/f).read_text().strip() for f in extra_files};runtime_original=core.controls(group)
   if extra_original['memory.max']!='21474836480':raise RuntimeError('runtime hard memory cap differs from frozen 20GiB')
   if runtime_original['cpu.max']!='800000 100000' or runtime_original['memory.high']!='max' or runtime_original['io.max']!='':raise RuntimeError('fresh runtime originals differ')
   item['external_memory_max_bytes']=21474836480
   run(['nsenter','-t',str(pid),'-n','--','ip','link','set','dev','eth0','down'])
   if 'state DOWN' not in run(['nsenter','-t',str(pid),'-n','--','ip','-o','link','show','dev','eth0']).stdout:raise RuntimeError('network gate not isolated')
   started=time.monotonic();(gates/meta['metadata']['uid']).write_text('isolated\n');item={'phase':'booting','resource_mode':'manual','candidate_branch':candidate,'memory_reserve_before_bytes':available,'declared_read_write_bps':bandwidth*1024**2,'original_start_script_unmodified':True,'same_container_mount_paths':True,'original_ccg_readonly':True};report['roles'][key]=item;report['phase']='testing-'+key;save()
   deadline=time.monotonic()+300
   while time.monotonic()<deadline:
    reserve()
    try:
     q=ex(role,'su','-','postgres','-c','/opt/postgresql/pgsql/bin/pg_isready -h 127.0.0.1 -p 5432 -t 2',check=False,timeout=max(0.01,min(15,deadline-time.monotonic())))
     item['last_readiness_probe']={'exit':q.returncode,'output':(q.stdout+q.stderr)[-1500:]};save()
     status=folder/'resource-state/status.json'
     if q.returncode==0 and status.exists() and json.loads(status.read_text()).get('state')=='managed' and time.monotonic()<deadline:
      api="import urllib2,json; r=urllib2.urlopen(urllib2.Request('http://127.0.0.1:8090/test',data='{}',headers={'Content-Type':'application/json'}),timeout=3); assert r.getcode()==200; assert json.loads(r.read(1024))['Result']=='000'"
      a=ex(role,'python','-c',api,check=False,timeout=max(0.01,min(10,deadline-time.monotonic())))
      item['last_api_probe']={'exit':a.returncode};save()
      if a.returncode==0 and time.monotonic()<deadline:break
    except subprocess.TimeoutExpired:
     item['readiness_observation_timeouts']=item.get('readiness_observation_timeouts',0)+1;save()
    time.sleep(max(0,min(3,deadline-time.monotonic())))
   else:raise RuntimeError(role+' original PG/API readiness/managed budget not met within declared 300s')
   item['ready_and_managed_seconds']=time.monotonic()-started;state=json.loads(status.read_text());item['automatic_io']=state.get('automatic_io');save()
   startup_ok=(state['state']=='managed' and state.get('automatic_io') is None and not (folder/'crg-config/io-profile.json').exists())
   mountinfo=ex(role,'findmnt','-n','-o','OPTIONS','/opt/ccg').stdout.strip();readonly_ok=('ro' in mountinfo.split(','))
   cachefile=folder/'cache-state/status.json';cache_started=time.monotonic();cache_deadline=min(started+300,cache_started+45)
   while time.monotonic()<cache_deadline:
    if cachefile.exists() and json.loads(cachefile.read_text()).get('action')=='enforce':break
    time.sleep(min(1,max(0,cache_deadline-time.monotonic())))
   item['cache_enforce_observation_seconds']=time.monotonic()-cache_started
   cache_ok=(cachefile.exists() and json.loads(cachefile.read_text()).get('action')=='enforce' and time.monotonic()<=started+300)
   actual_active={f:(group/f).read_text().strip() for f in ['cpu.max','memory.high','io.max']}
   io_settings=[x for x in state['plan']['settings'] if x['file']=='io.max']
   expected_active={'cpu.max':'720000 100000','memory.high':'20001980416','io.max':io_settings[0]['device']+' rbps=67108864 wbps=67108864 riops=4096 wiops=4096'} if len(io_settings)==1 else {}
   item['actual_active_controls']=actual_active;item['expected_active_controls']=expected_active
   identities=[]
   for member in (group/'cgroup.procs').read_text().splitlines():
    proc=pathlib.Path('/proc',member)
    try:
     stat=(proc/'stat').read_text();fields=stat[stat.rfind(')')+2:].split();identities.append({'pid':int(member),'start_ticks':int(fields[19]),'program':pathlib.Path(os.readlink(proc/'exe')).name,'is_main':int(member)==pid})
    except FileNotFoundError:pass
   item['fixture_identity']={'pod_uid':meta['metadata']['uid'],'group':str(group),'pod_parent':str(group.parent),'processes':identities}
   item['external_memory_max_bytes']=21474836480
   controls_ok=(set(x['file'] for x in state['items'])=={'cpu.max','memory.high','io.max'} and all(x['state']=='applied' for x in state['items']) and actual_active==expected_active and all((group/f).read_text().strip()==v for f,v in extra_original.items()))
   daily=list((folder/'log/crg').glob('crg-*.log'));events=[json.loads(x) for file in daily for x in file.read_text().splitlines()]
   if not any(x['event']=='resource_status' and x.get('fields',{}).get('memory_policy')=='high-reclaim-throttle' for x in events):raise RuntimeError('high policy absent from daily logs')
   logs_ok=(bool(daily) and all(file.stat().st_mode&0o777==0o600 for file in daily) and any(x['event']=='cgroup_detected' and x.get('fields',{}).get('check',{}).get('cgroup_version')=='v2' for x in events))
   record(key+'-original-start-and-three-controls-with-v2-daily-logs',startup_ok and controls_ok and logs_ok)
   original_config=(folder/'crg-config/config.json').read_bytes();item['original_config_sha256']=hashlib.sha256(original_config).hexdigest()
   execution=core.PressureExecution(root,ns,role,folder,group,item,report,save,record,run,ex,reserve)
   agents=execution.processes(group,'/opt/crg/crg');caches=execution.processes(group,'/opt/ccg/bin/containercacheguard')
   record(key+'-one-current-Agent-fresh-cache-readonly-CCG',readonly_ok and cache_ok and len(agents)==len(caches)==1 and agents[0][2]==core.PINS['binary'] and caches[0][2]=='757ba385a0ee4bdadc968b96b5c3e69fd44353060e5ab28520fd6f73a59902de')
   profile=folder/'crg-config/io-profile.json';profile.write_bytes(pathlib.Path('/var/tmp/crg-r30-20261110/actual/v10/config/io-profile.json').read_bytes());profile.chmod(0o600)
   if hashlib.sha256(profile.read_bytes()).hexdigest()!=core.PINS['profile']:raise RuntimeError('original measured profile differs')
   item.update(identity=state['plan']['environment']['identity'],primary_start=execution.sql(role,'SELECT pg_postmaster_start_time();'),reload_intervals=[],samples=[],runtime_original_controls=runtime_original)
   diagnostic.run_fixture({'root':root,'legacy':legacy,'role':role,'ns':ns,'folder':folder,'group':group,'row':item,'execution':execution,'core':core,'check':record,'save':save,'run':run,'ex':ex,'reserve':reserve})
   disabled=json.loads(ex(role,'/opt/crg/crg','disable','--config','/etc/crg/config.json',timeout=30).stdout)
   item['disabled']=disabled
   record(key+'-explicit-disable-restores-true-runtime-originals',disabled['state']=='restored' and core.controls(group)==runtime_original)
   item['phase']='diagnostic-fixture-completed';save()
  except Exception as error:item.update(phase='failed',error=str(error),traceback=traceback.format_exc());save()
  finally:
   if campaign_job is not None and campaign_job.poll() is None:
    campaign_job.terminate()
    try:campaign_job.wait(timeout=45)
    except subprocess.TimeoutExpired:campaign_job.kill();campaign_job.wait(timeout=15)
   if execution is not None:
    if execution.engine_job is not None and execution.engine_job.poll() is None:
     execution.engine_job.terminate()
     try:execution.engine_job.wait(timeout=120)
     except subprocess.TimeoutExpired:item['engine_cleanup_pending']=True
    for stream in [execution.engine_log,execution.worker_log]:
     if stream is not None and not stream.closed:stream.close()
   if pod_created:
    delete_pod(role);item['own_pod_removed']=True
    for identity in item.get('fixture_identity',{}).get('processes',[]):
     p=pathlib.Path('/proc',str(identity['pid']))
     if p.exists() and int((p/'stat').read_text().rsplit(')',1)[1].split()[19])==identity['start_ticks']:raise RuntimeError('owned original process survived Pod deletion')
    item['own_leaf_absent']=not group.exists();item['own_parent_absent']=not group.parent.exists()
    if not item['own_leaf_absent'] or not item['own_parent_absent']:raise RuntimeError('owned cgroup survived deletion')
   if folder is not None:
    config=folder/'crg-config/config.json';temp=config.with_name('high638.restore');temp.write_bytes(original_config if original_config is not None else json.dumps(core.MANUAL).encode());temp.chmod(0o600);temp.replace(config)
    profile=folder/'crg-config/io-profile.json'
    if profile.exists():
     if profile.is_symlink() or hashlib.sha256(profile.read_bytes()).hexdigest()!=core.PINS['profile']:raise RuntimeError('owned test profile changed before cleanup')
     profile.unlink()
    target=folder/'crg-config/high638.target.json'
    if target.exists():
     if target.is_symlink():raise RuntimeError('owned config target changed')
     target.unlink()
    item['original_config_and_profile_absence_restored']=json.loads(config.read_text())==core.MANUAL and (not item.get('original_config_sha256') or hashlib.sha256(config.read_bytes()).hexdigest()==item['original_config_sha256']) and not profile.exists()
   save()
   save()
 report['phase']='completed' if all(v['phase']=='diagnostic-fixture-completed' for v in report['roles'].values()) else 'failed'
except Exception as e:report.update(phase='failed',error=str(e),traceback=traceback.format_exc())
finally:
 if created:
  m=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout)
  if m['metadata']['labels'].get('managed-by')!='crg-vendor-test':raise RuntimeError('namespace cleanup ownership mismatch')
  run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=150s'],False,160);absent=run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json'],False);report['namespace_absent']=absent.returncode==0 and not absent.stdout.strip()
 if root.exists():save()
print(json.dumps({'phase':report['phase'],'checks':len(report['tests']),'error':report.get('error')}))

raise SystemExit(0 if report['phase']=='completed' and report.get('namespace_absent') is True and len(report['roles'])==2 and len(report['tests'])==22 and all(x.get('original_config_and_profile_absence_restored') and x.get('own_leaf_absent') and x.get('own_parent_absent') for x in report['roles'].values()) else 1)
