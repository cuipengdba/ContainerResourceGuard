import pathlib,json,subprocess,time,traceback,hashlib,os,shutil,re,uuid,sys,signal
candidates=pathlib.Path('/var/tmp/crg-bandwidth1210-tools-20261114');plan=json.loads((candidates/'plan.json').read_bytes());role_argument=sys.argv[1];assert role_argument in ['dbs','hisdbs']
root=pathlib.Path(plan['output'])/role_argument;source=pathlib.Path('/var/tmp/crg-business-20261110');ns=plan['namespaces'][role_argument];created=False;namespace_uid=None
assert os.geteuid()==0 and os.uname().machine=='x86_64' and os.environ.get('CRG_BANDWIDTH1210_BUSINESS')=='authorized-disposable-test-node-only'
assert root==pathlib.Path('/var/tmp/crg-bandwidth1210-results-20261114')/role_argument and ns=='crg-vendor-lab-bandwidth1210-'+role_argument+'-20261114'
assert not root.exists()
def interrupted(signum,frame):raise RuntimeError('isolated default20 driver interrupted')
signal.signal(signal.SIGTERM,interrupted)
for name,want in plan['source_sha256'].items():assert hashlib.sha256((candidates/name).read_bytes()).hexdigest()==want
assert plan['job_sha256']==hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
report={'resource_mode':'percent','declared_test_budget':{'config':{},'cpu_percent':20,'memory_percent':20,'io_percent':20,'IO_basis':'fresh automatic calibration, no directory/output/profile override'},'phase':'waiting-for-automatic-calibration-checks','scope':'same container paths and read-only CCG mount as read-only deployment inventory; fresh private test-node backing directories and loopback DCS, no production data; original business/image/database parameters','roles':{},'tests':[]}
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
 result=run(['kubectl','delete','pod','-n',ns,role+'-business','--wait=true','--timeout=120s'],check=False,timeout=130);item['pod_delete_command']={'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr};save()
 if result.returncode:raise RuntimeError('own Pod deletion failed within original120s')
try:
 root.mkdir(mode=0o700,exist_ok=False);report.update(job_sha256=plan['job_sha256'],plan_sha256=hashlib.sha256((candidates/'plan.json').read_bytes()).hexdigest(),role=role_argument,namespace=ns,memory_policy='high-reclaim-throttle',sources={'preview5':{'revision':plan['source_revision'],'binary_sha256':plan['source_sha256']['binaries/crg-linux-amd64']}});save()
 previous=pathlib.Path('/var/tmp/crg-high960-pressure-20261113/report.json');assert hashlib.sha256(previous.read_bytes()).hexdigest()==plan['previous960_report_sha256']
 prior=run(['kubectl','get','namespace','crg-vendor-lab-high960-20261113','--ignore-not-found','-o','json']);assert not prior.stdout.strip()
 for name,want in plan['private_fixture_sha256'].items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==want
 info=json.loads(run([str(candidates/'binaries/crg-linux-amd64'),'build-info']).stdout);assert info['revision']==plan['source_revision'] and info['version']==plan['candidate_version'] and info['io_percent_policy']=='calibrated-read-write-bandwidth; IOPS manual only; external IOPS retained' and info['memory_policy']=='high-reclaim-throttle; percentages may be exceeded; external hard limits retained';report['build_info']=info
 (root/'tools').mkdir(mode=0o700)
 for name in ['vendor-soak-load.py','vendor-soak-campaign.py','vendor-engine-smoke.py']:shutil.copyfile(candidates/'tests'/name,root/'tools'/name)
 report['phase']='preparing';save()
 gates=root/'gates';gates.mkdir(mode=0o700)
 aux=root/'aux';aux.mkdir(mode=0o700);shutil.copyfile('/usr/bin/etcd',aux/'etcd');(aux/'etcd').chmod(0o755)
 if run(['kubectl','get','namespace',ns],False).returncode==0:raise RuntimeError('namespace already exists')
 create({'apiVersion':'v1','kind':'Namespace','metadata':{'name':ns,'labels':{'managed-by':'crg-vendor-test'}}});created=True
 namespace_uid=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout)['metadata']['uid'];report['namespace_uid']=namespace_uid;save()
 create({'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'deny-all','namespace':ns},'spec':{'podSelector':{},'policyTypes':['Ingress','Egress']}})
 images=json.loads((source/'vendor-import.json').read_text())['images']
 for index,(candidate,role,bandwidth) in enumerate([('preview5',role_argument,20)]):
  key=candidate+'-'+role+'-default20';pod_created=False;campaign_job=None;folder=None;group=None;item={'phase':'preparing','candidate_branch':candidate,'role':role,'percentages':{'cpu_percent':20,'memory_percent':20,'io_percent':20}};report['roles'][key]=item;save()
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
   (folder/'crg-config/config.json').write_text('{}')
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
   actual_image=next(v['imageID'] for v in meta['status']['containerStatuses'] if v['name']==role);assert actual_image.rsplit('sha256:',1)[-1]==plan['expected_original_image_sha256'][role],'ORIGINAL_IMAGE_CHANGED'
   item['original_image_id']=actual_image
   if meta['metadata']['namespace']!=ns or meta['metadata']['labels'].get('managed-by')!='crg-vendor-test' or any(meta['spec'].get(k,False) for k in ['hostNetwork','hostPID','hostIPC']):raise RuntimeError('fixture host namespace guard')
   if pid<=1 or any(pathlib.Path('/proc',str(pid),'ns',kind).stat().st_ino==pathlib.Path('/proc/1/ns',kind).stat().st_ino for kind in ['net','pid','mnt']):raise RuntimeError('fixture namespace separation guard')
   item['fixture_identity']={'pod_uid':meta['metadata']['uid'],'container_id':cid,'init_pid':pid,'init_start_ticks':int(pathlib.Path('/proc',str(pid),'stat').read_bytes().rsplit(b')',1)[1].split()[19]),'group':str(group),'pod_parent':str(group.parent)}
   fixture_identity=item['fixture_identity']
   extra_files=['pids.max','cpu.weight','io.weight','memory.max','memory.swap.max'];extra_original={f:(group/f).read_text().strip() for f in extra_files}
   run(['nsenter','-t',str(pid),'-n','--','ip','link','set','dev','eth0','down'])
   if 'state DOWN' not in run(['nsenter','-t',str(pid),'-n','--','ip','-o','link','show','dev','eth0']).stdout:raise RuntimeError('network gate not isolated')
   started=time.monotonic();(gates/meta['metadata']['uid']).write_text('isolated\n');item={'phase':'booting','resource_mode':'percent','candidate_branch':candidate,'memory_reserve_before_bytes':available,'percentages':{'cpu_percent':20,'memory_percent':20,'io_percent':20},'original_start_script_unmodified':True,'same_container_mount_paths':True,'original_ccg_readonly':True};item['original_image_id']=actual_image;item['fixture_identity']=fixture_identity;report['roles'][key]=item;report['phase']='testing-'+key;save()
   deadline=time.monotonic()+300
   while time.monotonic()<deadline:
    reserve()
    try:
     q=ex(role,'su','-','postgres','-c','/opt/postgresql/pgsql/bin/pg_isready -h 127.0.0.1 -p 5432 -t 2',check=False,timeout=max(0.01,min(15,deadline-time.monotonic())))
     item['last_readiness_probe']={'exit':q.returncode,'output':(q.stdout+q.stderr)[-1500:]};save()
     status=folder/'resource-state/status.json'
     if q.returncode==0 and time.monotonic()<deadline:
      item.setdefault('first_pg_ready_seconds',time.monotonic()-started)
      api="import urllib2,json; r=urllib2.urlopen(urllib2.Request('http://127.0.0.1:8090/test',data='{}',headers={'Content-Type':'application/json'}),timeout=3); assert r.getcode()==200; assert json.loads(r.read(1024))['Result']=='000'"
      a=ex(role,'python','-c',api,check=False,timeout=max(0.01,min(10,deadline-time.monotonic())))
      item['last_api_probe']={'exit':a.returncode}
      if a.returncode==0:item.setdefault('first_api_ready_seconds',time.monotonic()-started)
      save()
      if a.returncode==0 and status.exists() and json.loads(status.read_text()).get('state')=='managed' and time.monotonic()<deadline:break
    except subprocess.TimeoutExpired:
     item['readiness_observation_timeouts']=item.get('readiness_observation_timeouts',0)+1;save()
    time.sleep(max(0,min(3,deadline-time.monotonic())))
   else:raise RuntimeError(role+' original PG/API readiness/managed budget not met within declared 300s')
   item['ready_and_managed_seconds']=time.monotonic()-started;state=json.loads(status.read_text());item['automatic_io']=state.get('automatic_io');save()
   record(key+'-real-path-original-startup-default20-and-automatic-profile',state['state']=='managed' and state['plan']['percentages']=={'cpu_percent':20,'memory_percent':20,'io_percent':20} and state.get('automatic_io',{}).get('state')=='calibrated' and (folder/'crg-config/io-profile.json').exists())
   profile=json.loads((folder/'crg-config/io-profile.json').read_text());item['profile']={'version':profile['version'],'method':profile['method'],'devices':[{k:x[k] for k in ['device','read_bps','write_bps','read_iops','write_iops']} for x in profile['devices']]};env=state['plan']['environment'];item['host_basis']={k:env[k] for k in ['host_online_cpus','host_memory_bytes']};settings={x['file']:x for x in state['plan']['settings']}
   expected_cpu=str(int(env['host_online_cpus']*20/100*100000))+' 100000';expected_mem=str(int(env['host_memory_bytes']*20/100)//4096*4096);chosen=state['automatic_io']['selection']['device'];device=next(x for x in profile['devices'] if x['device']==chosen);expected_io='rbps=%d wbps=%d riops=max wiops=max'%tuple(device[k]*20//100 for k in ['read_bps','write_bps']);assert profile['version']==2 and len(device['measurements'])==3 and all(device[k]==sorted(v[k] for v in device['measurements'])[1] for k in ['read_bps','write_bps','read_iops','write_iops'])
   record(key+'-default20-uses-host-capacity-and-calibrated-IO',settings['cpu.max']['value']==expected_cpu and settings['memory.high']['value']==expected_mem and settings['io.max']['value']==expected_io and (group/'cpu.max').read_text().strip()==expected_cpu and (group/'memory.high').read_text().strip()==expected_mem and (group/'io.max').read_text().strip()==chosen+' '+expected_io)
   item['actual_three_controls']={f:(group/f).read_text().strip() for f in ['cpu.max','memory.high','io.max']};save()
   mountinfo=ex(role,'findmnt','-n','-o','OPTIONS','/opt/ccg').stdout.strip();record(key+'-original-CCG-mount-stays-readonly','ro' in mountinfo.split(','))
   cachefile=folder/'cache-state/status.json';cache_started=time.monotonic();cache_deadline=min(started+300,cache_started+45)
   while time.monotonic()<cache_deadline:
    if cachefile.exists() and json.loads(cachefile.read_text()).get('action')=='enforce':break
    time.sleep(min(1,max(0,cache_deadline-time.monotonic())))
   item['cache_enforce_observation_seconds']=time.monotonic()-cache_started
   record(key+'-original-cache-independent-enforce',cachefile.exists() and json.loads(cachefile.read_text()).get('action')=='enforce' and time.monotonic()<=started+300)
   record(key+'-only-three-resource-controls-and-other-values-preserved',set(x['file'] for x in state['items'])=={'cpu.max','memory.high','io.max'} and all((group/f).read_text().strip()==v for f,v in extra_original.items()))
   daily=list((folder/'log/crg').glob('crg-*.log'));events=[json.loads(x) for file in daily for x in file.read_text().splitlines()]
   if not any(x['event']=='resource_status' and x.get('fields',{}).get('memory_policy')=='high-reclaim-throttle' for x in events):raise RuntimeError('high policy missing from daily log')
   record(key+'-daily-logs-report-v2-before-business-campaign',bool(daily) and all(file.stat().st_mode&0o777==0o600 for file in daily) and any(x['event']=='cgroup_detected' and x.get('fields',{}).get('check',{}).get('cgroup_version')=='v2' for x in events))
   processes=[]
   for member in (group/'cgroup.procs').read_text().splitlines():
    p=pathlib.Path('/proc',member)
    try:
     fields=(p/'stat').read_bytes().rsplit(b')',1)[1].split();exe=os.readlink(p/'exe');processes.append({'pid':int(member),'start_ticks':int(fields[19]),'executable':exe,'sha256':hashlib.sha256((p/'exe').read_bytes()).hexdigest() if exe in ['/opt/crg/crg','/opt/ccg/bin/containercacheguard'] else None})
    except (FileNotFoundError,ProcessLookupError):pass
   item['fixture_identity']['processes']=processes
   agents=[v for v in processes if v['executable']=='/opt/crg/crg'];caches=[v for v in processes if v['executable']=='/opt/ccg/bin/containercacheguard'];journal=json.loads((folder/'resource-state/journal.json').read_bytes())
   record(key+'-one-current-Agent-cache-and-owned-high-only-journal',len(agents)==len(caches)==1 and agents[0]['sha256']==plan['source_sha256']['binaries/crg-linux-amd64'] and caches[0]['sha256']==plan['private_fixture_sha256']['fixture/containercacheguard'] and len(state['items'])==3 and all(x['state']=='applied' for x in state['items']) and {v['file'] for v in journal['mutations'].values()}=={'cpu.max','memory.high','io.max'} and (folder/'crg-config/config.json').read_bytes()==b'{}')
   item['journal']=journal;item['configuration_exact_utf8']='{}';item['full_profile']=profile;item['runtime_original_other_controls']=extra_original;item['initial_controls']={f:(group/f).read_text().strip() for f in ['cpu.max','memory.high','io.max','memory.max','pids.max','cpu.weight','io.weight','memory.swap.max']};save()
   campaign=case_root/('campaign-'+role);agent=hashlib.sha256((folder/'crg/crg').read_bytes()).hexdigest();ccg=hashlib.sha256((folder/'ccg/bin/containercacheguard').read_bytes()).hexdigest()
   args=['python3',str(root/'tools/vendor-soak-campaign.py'),'--namespace',ns,'--fixture-root',str(case_root),'--work-dir',str(campaign),'--role',role,'--smoke-enforce','--run-id',plan['run_ids'][role],'--test-phase','smoke','--seconds','600','--agent-sha256',agent,'--cache-sha256',ccg]
   with (root/(key+'-campaign.log')).open('xb') as log:
    job=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=log,stderr=log);campaign_job=job
    while job.poll() is None:reserve();time.sleep(5)
   native=json.loads((campaign/'report.json').read_text());item['campaign_report']=native;item['campaign_exit']=job.returncode;save();record(key+'-600s-native-and-backup-sync-independent-restore',job.returncode==0 and native['phase']=='passed')
   item['phase']='short-acceptance-passed';save()
  except Exception as error:
   item.update(phase='failed',error=str(error),traceback=traceback.format_exc())
   if folder is not None:
    snapshot=folder/'resource-state/status.json'
    if snapshot.exists():
     st=json.loads(snapshot.read_text());item['last_resource_snapshot']={k:st[k] for k in ['state','automatic_io','items','plan'] if k in st}
   save()
  finally:
   if campaign_job is not None and campaign_job.poll() is None:
    campaign_job.terminate()
    try:campaign_job.wait(timeout=45)
    except subprocess.TimeoutExpired:campaign_job.kill();campaign_job.wait(timeout=15)
   if pod_created:
    if group is not None and group.exists():
     item['final_controls']={f:(group/f).read_text().strip() for f in ['cpu.max','memory.max','io.max','pids.max','cpu.weight','io.weight','memory.high','memory.swap.max'] if (group/f).exists()};item['final_memory_events']=(group/'memory.events').read_text();save()
    delete_pod(role);item['own_pod_removed']=True
    if group is not None:
     item['own_leaf_absent']=not group.exists();item['own_parent_absent']=not group.parent.exists()
     for identity in item.get('fixture_identity',{}).get('processes',[]):
      p=pathlib.Path('/proc',str(identity['pid']),'stat');assert not p.exists() or int(p.read_bytes().rsplit(b')',1)[1].split()[19])!=identity['start_ticks']
     if not item['own_leaf_absent'] or not item['own_parent_absent']:raise RuntimeError('own cgroup survived Pod deletion')
   save()
 report['phase']='passed' if len(report['roles'])==1 and len(report['tests'])==8 and all(v['passed'] for v in report['tests']) and all(v['phase']=='short-acceptance-passed' for v in report['roles'].values()) else 'failed'
except Exception as e:report.update(phase='failed',error=str(e),traceback=traceback.format_exc())
finally:
 if created:
  m=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout)
  if m['metadata']['labels'].get('managed-by')!='crg-vendor-test' or m['metadata']['uid']!=namespace_uid:raise RuntimeError('namespace cleanup ownership mismatch')
  run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=150s'],False,160);absent=run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json'],False);report['namespace_absent']=absent.returncode==0 and not absent.stdout.strip()
 if root.exists():save()
print(json.dumps({'phase':report['phase'],'checks':len(report['tests']),'error':report.get('error')}));raise SystemExit(0 if report['phase']=='passed' and report.get('namespace_absent') else 1)
