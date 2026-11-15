import pathlib,json,subprocess,time,traceback,hashlib,os,shutil,re,uuid,sys,signal
candidates=pathlib.Path('/var/tmp/crg-percent1287-tools-20261115');plan=json.loads((candidates/'plan.json').read_bytes());role_argument=sys.argv[1];assert role_argument in ['dbs','hisdbs']
root=pathlib.Path(plan['output'])/role_argument;source=pathlib.Path('/var/tmp/crg-business-20261110');ns=plan['namespaces'][role_argument];created=False;namespace_uid=None
assert os.geteuid()==0 and os.uname().machine=='x86_64' and os.environ.get('CRG_PERCENT1287_BUSINESS')=='authorized-disposable-test-node-only'
assert root==pathlib.Path('/var/tmp/crg-percent1287-results-20261115')/role_argument and ns=='crg-vendor-lab-percent1287-'+role_argument+'-20261115'
assert not root.exists()
def interrupted(signum,frame):raise RuntimeError('isolated percentage driver interrupted')
signal.signal(signal.SIGTERM,interrupted)
for name,want in plan['source_sha256'].items():assert hashlib.sha256((candidates/name).read_bytes()).hexdigest()==want
assert plan['job_sha256']==hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
report={'resource_mode':'percent','declared_test_budget':{'config':plan['configuration'],'reference_budget':plan['budget'],'IO_basis':'default20 actual public4fouraxis to public5bandwidth; real automaticprofile retained'},'phase':'waiting-for-default20-control-checks','scope':'actual public programs in vendor clones at original mount paths; CLOSED business gate, control-layer migration only, no SQL/API/cache business acceptance','roles':{},'tests':[]}
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
 root.mkdir(mode=0o700,exist_ok=False);report.update(job_sha256=plan['job_sha256'],plan_sha256=hashlib.sha256((candidates/'plan.json').read_bytes()).hexdigest(),role=role_argument,namespace=ns,memory_policy='high-reclaim-throttle',sources={k:{'revision':v['source_revision'],'binary_sha256':v['binary_sha256']} for k,v in plan['programs'].items()});save()
 previous=pathlib.Path('/var/tmp/crg-high960-pressure-20261113/report.json');assert hashlib.sha256(previous.read_bytes()).hexdigest()==plan['previous960_report_sha256']
 prior=run(['kubectl','get','namespace','crg-vendor-lab-high960-20261113','--ignore-not-found','-o','json']);assert not prior.stdout.strip()
 for name,want in plan['private_fixture_sha256'].items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==want
 import importlib.util
 spec=importlib.util.spec_from_file_location('manual_maintenance_contract',candidates/'tests/percent-contract.py');policy_contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy_contract)
 report['build_info']={}
 for name,bound in plan['programs'].items():
  info=json.loads(run([str(candidates/'binaries'/name),'build-info']).stdout);assert info['revision']==bound['source_revision'] and info['version']==bound['embedded_version'] and info['lock_protocol']=='cgroup-inode-flock+state-agent-lock-v1' and 1 in info['journal_versions'] and info['memory_policy']=='high-reclaim-throttle; percentages may be exceeded; external hard limits retained';report['build_info'][name]=info
 assert report['build_info']['candidate']['io_percent_policy']=='calibrated-read-write-bandwidth; IOPS manual only; external IOPS retained'
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
 for index,(candidate,role) in enumerate([('owned',role_argument),('external',role_argument)]):
  key=candidate+'-'+role;pod_created=False;campaign_job=None;native_log=None;folder=None;group=None;item={'phase':'preparing','candidate_branch':candidate,'role':role,'configuration':plan['configuration']};report['roles'][key]=item;save()
  try:
   if index:assert 'prior_case' in locals() and report['roles']['owned-'+role]['phase']=='short-acceptance-passed' and report['roles']['owned-'+role]['own_leaf_absent'] and report['roles']['owned-'+role]['own_parent_absent']
   available=reserve(28);case_root=root/key;case_root.mkdir(mode=0o700);folder=root/('owned-'+role)/(role+'-business')
   if index==0:folder.mkdir(mode=0o700)
   if index==0:
    for n in ['postgresql','dbs','highgo','log','core','sql','hbp-runtime','resource-state','cache-state','etcd','ccg','crg','crg-config','recovery','staging']:(folder/n).mkdir(mode=0o700)
    for n in ['bin','scripts','config']:(folder/'ccg'/n).mkdir(mode=0o700)
    cachepath='/home/ccg-backups/dbs' if role=='dbs' else '/opt/PUC-784/ccg-backups/hisdbs'
    shutil.copyfile(source/'fixture'/role/'supervisor.sh',folder/'ccg/scripts/business-supervisor.sh')
    shutil.copyfile(source/'fixture/containercacheguard',folder/'ccg/bin/containercacheguard');(folder/'ccg/bin/containercacheguard').chmod(0o755)
    binary=candidates/'binaries/previous'
    if hashlib.sha256(binary.read_bytes()).hexdigest()!=report['sources']['previous']['binary_sha256']:raise RuntimeError('candidate binary differs from recorded source-qualified digest')
    shutil.copyfile(binary,folder/'crg/crg');(folder/'crg/crg').chmod(0o755)
    shutil.copyfile(candidates/'binaries/candidate',folder/'staging/crg');(folder/'staging/crg').chmod(0o755)
    shutil.copyfile(candidates/'examples/optional-agent.sh',folder/'crg/optional-agent.sh')
    cache=json.loads((source/'fixture'/role/'cache.json').read_text());cache['state_file']=cachepath+'/status.json';(folder/('ccg/config/'+role+'.json')).write_text(json.dumps(cache))
    (folder/'crg-config/config.json').write_text(plan['configuration_exact_utf8'])
    env=json.loads((source/'fixture'/role/'env.json').read_text());secret=uuid.uuid4().hex
    env.update(MY_POD_NAMESPACE=ns,MY_POD_NAME=role+'-realpath-0',PGPASSWORD=secret,CCG_BIN='/opt/ccg/bin/containercacheguard',CCG_CONFIG='/opt/ccg/config/'+role+'.json',CRG_BIN='/opt/crg/crg',CRG_CONFIG='/etc/crg/config.json',CRG_HELPER_SCRIPT='/opt/crg/optional-agent.sh',YSP_PRODUCT_TYPE='PUC-DBS')
    pg=(source/'fixture'/role/'postgres.yml').read_text();pg=re.sub(r'(?m)^(\s+password:).*$',r'\1 '+secret,pg).replace('namespace: /crg-isolated/','namespace: /crg-realpaths/')
    (folder/'postgres.yml').write_text(pg);(folder/'postgres.yml').chmod(0o600)
    shutil.copyfile('/etc/localtime',folder/'localtime');(folder/'timezone').write_text('Asia/Shanghai\n')
   vols=[];mounts=[]
   def volume(name,path,target,readonly=False,file=False):
    vols.append({'name':name,'hostPath':{'path':str(path),'type':'File' if file else 'Directory'}});mounts.append({'name':name,'mountPath':target,'readOnly':readonly})
   for n,target,readonly in [('postgresql','/opt/postgresql',False),('dbs','/opt/dbs',False),('highgo','/opt/highgo',False),('log','/var/log',False),('core','/opt/local/tmp/core',False),('hbp-runtime','/var/run/.hbp',False),('cache-state',cachepath,False),('resource-state','/tmp/containerresourceguard',False),('ccg','/opt/ccg',True),('crg','/opt/crg',False),('crg-config','/etc/crg',False)]:volume(n,folder/n,target,readonly)
   volume('recovery',folder/'recovery','/recovery');volume('staging',folder/'staging','/staging',True)
   volume('pgconfig',folder/'postgres.yml','/home/config/postgres.yml',True,True);volume('localtime',folder/'localtime','/etc/localtime',False,True);volume('timezone',folder/'timezone','/etc/timezone',False,True)
   if role=='dbs':
    volume('sql',folder/'sql','/opt/dbs/sql');mounts.append({'name':'sql','mountPath':'/opt/sql'})
   else:
    vols.append({'name':'data','emptyDir':{}});mounts.append({'name':'data','mountPath':'/data'})
   for name,target,empty in [('shm','/dev/shm',{'medium':'Memory','sizeLimit':'1Gi'}),('hbp','/opt/hbp',{})]:vols.append({'name':name,'emptyDir':empty});mounts.append({'name':name,'mountPath':target})
   volume('gate',gates,'/network-gates',True)
   vols.extend([{'name':'aux','hostPath':{'path':str(aux),'type':'Directory'}},{'name':'etcd','hostPath':{'path':str(folder/'etcd'),'type':'Directory'}}])
   start='i=0; while [ ! -f "/network-gates/$CRG_TEST_POD_UID" ]; do i=$((i+1)); [ "$i" -lt 900 ] || exit 92; sleep 1; done; exec /bin/bash /opt/ccg/scripts/business-supervisor.sh'
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
   item['fixture_identity']['processes']=[]
   for member in (group/'cgroup.procs').read_text().splitlines():
    try:
     fields=pathlib.Path('/proc',member,'stat').read_bytes().rsplit(b')',1)[1].split();item['fixture_identity']['processes'].append({'pid':int(member),'start_ticks':int(fields[19])})
    except (FileNotFoundError,ProcessLookupError):pass
   save()
   # Business gate stays CLOSED throughout this controls-only test.
   runtime={f:(group/f).read_text().strip() for f in policy_contract.FILES};host_cpus=sum((int(v.split('-')[-1])-int(v.split('-')[0])+1) for v in pathlib.Path('/sys/devices/system/cpu/online').read_text().strip().split(','));host_mem=int(next(v.split()[1] for v in pathlib.Path('/proc/meminfo').read_text().splitlines() if v.startswith('MemTotal:')))*1024;page=os.sysconf('SC_PAGESIZE')
   for ancestor in [group.parent,*group.parent.parents]:
    if not str(ancestor).startswith('/sys/fs/cgroup'):break
    for f in ['cpu.max','memory.max','memory.high']:
     path=ancestor/f
     if path.exists():
      value=path.read_text().split();assert value[0]=='max' or (f=='cpu.max' and int(value[0])/int(value[1])>=8) or (f!='cpu.max' and int(value[0])>=21474836480),'FIXTURE_ANCESTOR_CONSTRAINT'
   initial_pid1=ex(role,'cat','/proc/1/stat').stdout.split()[21];config_path=folder/'crg-config/config.json';profile_path=folder/'crg-config/io-profile.json';statefile=folder/'resource-state/journal.json';item.update(runtime_baseline=runtime,host_capacity={'cpus':host_cpus,'memory_bytes':host_mem,'page_bytes':page},business_gate_opened=False);save()
   def controls():return {f:(group/f).read_text().strip() for f in policy_contract.FILES}
   def read(path):return json.loads(path.read_bytes())
   def no_writer():
    found=[]
    for member in (group/'cgroup.procs').read_text().splitlines():
     try:
      argv=pathlib.Path('/proc',member,'cmdline').read_bytes().split(b'\0')
      if len(argv)>1 and pathlib.Path(os.fsdecode(argv[0])).name=='crg' and argv[1]==b'run':found.append(member)
     except (FileNotFoundError,ProcessLookupError):pass
    return not found
   def cli(command,*args,executor='/opt/crg/crg',timeout=90):
    assert no_writer();reserve();q=ex(role,executor,command,'--config','/etc/crg/config.json',*args,check=False,timeout=timeout);item.setdefault('commands',[]).append({'command':command,'executor':executor,'exit':q.returncode,'stdout':q.stdout,'stderr':q.stderr});save();reserve();assert q.returncode==0,command+' failed';return json.loads(q.stdout)
   def snapshot(name):
    value={'controls':controls(),'journal':read(statefile),'status':read(folder/'resource-state/status.json'),'profile_sha256':hashlib.sha256(profile_path.read_bytes()).hexdigest(),'profile_mtime_ns':profile_path.stat().st_mtime_ns};item.setdefault('snapshots',{})[name]=value;save();return value
   def exact_restored():return controls()==runtime and read(statefile)=={'version':1,'identity':identity,'target':str(group),'mutations':{}} and ex(role,'cat','/proc/1/stat').stdout.split()[21]==initial_pid1 and no_writer()
   def verify(version,name):
    value=snapshot(name);contract.verify(value['status'],value['controls'],value['journal'],version);assert value['status']['plan']['environment']['host_online_cpus']==host_cpus and value['status']['plan']['environment']['host_memory_bytes']==host_mem;return value
   if index==0:
    record(key+'-actual-old-public-program-and-closed-gate',hashlib.sha256((folder/'crg/crg').read_bytes()).hexdigest()==plan['programs']['previous']['binary_sha256'] and not (gates/meta['metadata']['uid']).exists())
    record(key+'-independent-known-runtime-before-calibration',runtime['cpu.max']=='800000 100000' and runtime['memory.max']=='21474836480' and runtime['memory.high']=='max' and runtime['io.max']=='')
    cli('run','--once',timeout=180);profile=read(profile_path);contract=policy_contract.Contract(runtime,profile,host_cpus,host_mem,page);identity=read(statefile)['identity'];value=verify(4,'old-four-axis');profile_bytes=profile_path.read_bytes();profile_stamp=profile_path.stat().st_mtime_ns
    record(key+'-real-three-sample-default-automatic-calibration',value['status'].get('automatic_io',{}).get('state')=='calibrated' and len(profile['devices'][0]['measurements'])==3)
    record(key+'-old-default20-four-axis-independent-readback',value['controls']==contract.controls(4))
    record(key+'-old-journal-own-identity-and-originals',value['journal']['identity']==identity and value['journal']['target']==str(group))
    record(key+'-old-once-exits-and-PID1-unchanged',no_writer() and ex(role,'cat','/proc/1/stat').stdout.split()[21]==initial_pid1)
    held=statefile.read_bytes();before=controls();cli('quiesce');record(key+'-quiesce-preserves-values-and-journal',controls()==before and statefile.read_bytes()==held)
    result=cli('binary-install','--install-dir','/opt/crg','--backup-dir','/recovery/forward','--previous-sha256',plan['programs']['previous']['binary_sha256'],'--candidate-sha256',plan['programs']['candidate']['binary_sha256'],executor='/staging/crg');record(key+'-actual-public-new-binary-installed',result['state']=='installed' and hashlib.sha256((folder/'crg/crg').read_bytes()).hexdigest()==plan['programs']['candidate']['binary_sha256'])
    cli('enable');cli('run','--once');value=verify(5,'new-bandwidth');record(key+'-owned-IOPS-restored-with-new-BPS-only',value['controls']==contract.controls(5) and policy_contract.axes(value['controls']['io.max'],contract.device)['riops']=='max' and policy_contract.axes(value['controls']['io.max'],contract.device)['wiops']=='max')
    record(key+'-same-identity-and-profile-reused',value['journal']['identity']==identity and profile_path.read_bytes()==profile_bytes and profile_path.stat().st_mtime_ns==profile_stamp and value['status']['automatic_io']['state']=='reused')
    record(key+'-owned-originals-retained-by-new-program',all(value['journal']['mutations'][k]['original']==read_json['original'] for k,read_json in item['snapshots']['old-four-axis']['journal']['mutations'].items()))
    record(key+'-other-five-values-and-PID1-unchanged',all(controls()[f]==runtime[f] for f in ['memory.max','pids.max','cpu.weight','io.weight','memory.swap.max']) and ex(role,'cat','/proc/1/stat').stdout.split()[21]==initial_pid1)
    cli('disable');record(key+'-disable-restores-eight-runtime-originals',exact_restored())
    cli('enable');cli('run','--once');value=verify(5,'active-before-rebuild');prior_case={'identity':identity,'container_id':cid,'group':str(group),'profile_bytes':profile_bytes,'profile_stamp':profile_stamp,'active_journal':statefile.read_bytes(),'logs':{p.name:p.read_bytes() for p in (folder/'log/crg').glob('crg-*.log')}};record(key+'-active-owned-journal-left-for-real-ID-change',bool(value['journal']['mutations']) and no_writer() and config_path.read_bytes()==b'{}')
   else:
    assert cid!=prior_case['container_id'] and str(group)!=prior_case['group'];old_journal=statefile.read_bytes();assert old_journal==prior_case['active_journal'];dev=read(profile_path)['devices'][0]['device'];assert controls()['io.max']==''
    (group/'io.max').write_text(dev+' riops=197 wiops=149');runtime=controls();item['runtime_baseline']=runtime;contract=policy_contract.Contract(runtime,read(profile_path),host_cpus,host_mem,page);save()
    record(key+'-new-container-keeps-actual-persistent-active-journal',cid!=prior_case['container_id'] and old_journal==prior_case['active_journal'] and hashlib.sha256((folder/'crg/crg').read_bytes()).hexdigest()==plan['programs']['candidate']['binary_sha256'])
    record(key+'-own-new-leaf-external-IOPS-baseline',policy_contract.axes(runtime['io.max'],dev)=={'rbps':'max','wbps':'max','riops':'197','wiops':'149'})
    cli('run','--once');identity=read(statefile)['identity'];value=verify(5,'new-ID-external-IOPS');record(key+'-new-identity-archives-previous-active-journal',identity!=prior_case['identity'] and (folder/'resource-state/journal.previous.json').read_bytes()==old_journal)
    record(key+'-new-BPS-retains-external-IOPS',policy_contract.axes(value['controls']['io.max'],dev)==contract.new_io)
    record(key+'-default-CPU-memory-and-three-controls',value['controls']['cpu.max']==contract.cpu and value['controls']['memory.high']==contract.high and set(v['file'] for v in value['status']['items'])=={'cpu.max','memory.high','io.max'})
    record(key+'-same-profile-no-second-calibration',profile_path.read_bytes()==prior_case['profile_bytes'] and profile_path.stat().st_mtime_ns==prior_case['profile_stamp'] and value['status']['automatic_io']['state']=='reused')
    record(key+'-journal-records-new-external-baseline',policy_contract.axes(value['journal']['mutations']['io.max:'+dev]['original'])==contract.baseline)
    record(key+'-unmanaged-five-controls-unchanged',all(controls()[f]==runtime[f] for f in ['memory.max','pids.max','cpu.weight','io.weight','memory.swap.max']))
    daily={p.name:p.read_bytes() for p in (folder/'log/crg').glob('crg-*.log')};events=[json.loads(line) for raw in daily.values() for line in raw.decode().splitlines()];record(key+'-daily-log-prefix-retained-with-v2-events',bool(prior_case['logs']) and all(daily[k].startswith(v) and len(daily[k])>len(v) for k,v in prior_case['logs'].items()) and any(v['event']=='cgroup_detected' and v.get('fields',{}).get('check',{}).get('cgroup_version')=='v2' for v in events))
    cli('disable');record(key+'-disable-restores-new-external-baseline-and-empty-journal',exact_restored() and config_path.read_bytes()==b'{}')
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
   if native_log is not None:native_log.close()
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
 report['phase']='passed' if len(report['roles'])==2 and len(report['tests'])==24 and all(v['passed'] for v in report['tests']) and all(v['phase']=='short-acceptance-passed' for v in report['roles'].values()) else 'failed'
except Exception as e:report.update(phase='failed',error=str(e),traceback=traceback.format_exc())
finally:
 if created:
  m=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout)
  if m['metadata']['labels'].get('managed-by')!='crg-vendor-test' or m['metadata']['uid']!=namespace_uid:raise RuntimeError('namespace cleanup ownership mismatch')
  run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=150s'],False,160);absent=run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json'],False);report['namespace_absent']=absent.returncode==0 and not absent.stdout.strip()
 if root.exists():save()
print(json.dumps({'phase':report['phase'],'checks':len(report['tests']),'error':report.get('error')}));raise SystemExit(0 if report['phase']=='passed' and report.get('namespace_absent') else 1)
