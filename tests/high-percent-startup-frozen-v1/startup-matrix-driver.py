import pathlib,json,subprocess,time,traceback,hashlib,os,shutil,re,uuid,shlex,sys,importlib.util,signal
candidates=pathlib.Path('/var/tmp/crg-startup1008-tools-20261113');plan=json.loads((candidates/'plan.json').read_bytes());role_argument=sys.argv[1];percent=int(sys.argv[2]);case_argument=role_argument+'-'+str(percent)
assert role_argument in ['dbs','hisdbs'] and percent in [20,30]
root=pathlib.Path(plan['output'])/case_argument;source=pathlib.Path('/var/tmp/crg-business-20261110');ns=plan['namespaces'][case_argument];created=False;namespace_uid=None;boot_nodes={}
assert root==pathlib.Path('/var/tmp/crg-startup1008-results-20261113')/case_argument and ns=='crg-vendor-lab-startup1008-'+case_argument+'-20261113'
spec=importlib.util.spec_from_file_location('scoped_probe',candidates/'scoped-probe.py');scoped_probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(scoped_probe)
def interrupted(signum,frame):raise RuntimeError('isolated startup matrix interrupted')
signal.signal(signal.SIGTERM,interrupted)
report={'resource_mode':'percent','declared_test_budget':{'configuration':{} if percent==20 else {'cpu_percent':30,'memory_percent':30,'io_percent':30},'percentages':{k:percent for k in ['cpu_percent','memory_percent','io_percent']},'IO_basis':'fresh automatic maximum-eligible-filesystem calibration, same exact profile retained across three boots'},'phase':'preparing','scope':'isolated original images, original real paths/start/PG/cache, exact observed original kubelet liveness; not undocumented vendor API or no-OOM guarantee','roles':{},'tests':[]}
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
 expected_uid=item['starts'][-1].get('pod_uid');assert expected_uid and m['metadata']['uid']==expected_uid
 row=item['starts'][-1]
 if row.get('group') and pathlib.Path(row['group']).exists():capture_processes(row,pathlib.Path(row['group']))
 q=run(['kubectl','delete','pod','-n',ns,role+'-business','--wait=true','--timeout=120s'],check=False,timeout=130);row['pod_delete_command']={'exit':q.returncode,'stdout':q.stdout,'stderr':q.stderr};save()
 if q.returncode:raise RuntimeError('original120s own Pod delete failed')
 deadline=time.monotonic()+30
 while any(start.get('group') and (pathlib.Path(start['group']).exists() or pathlib.Path(start['pod_parent']).exists()) for start in item['starts']) and time.monotonic()<deadline:time.sleep(.5)
 for start in item['starts']:
  if not start.get('group'):continue
  start['leaf_absent_after_delete']=not pathlib.Path(start['group']).exists();start['parent_absent_after_delete']=not pathlib.Path(start['pod_parent']).exists()
  if not start['leaf_absent_after_delete'] or not start['parent_absent_after_delete']:raise RuntimeError('own original cgroup survived deletion')
  for p in start.get('processes',[]):
   q=pathlib.Path('/proc',str(p['pid']),'stat');assert not q.exists() or int(q.read_bytes().rsplit(b')',1)[1].split()[19])!=p['start_ticks']
 save()

def capture_processes(row,group):
 rows={(v['pid'],v['start_ticks']):v for v in row.get('processes',[])}
 for member in (group/'cgroup.procs').read_text().splitlines():
  p=pathlib.Path('/proc',member)
  try:
   fields=(p/'stat').read_bytes().rsplit(b')',1)[1].split();value={'pid':int(member),'start_ticks':int(fields[19]),'program':pathlib.Path(os.readlink(p/'exe')).name};rows[(value['pid'],value['start_ticks'])]=value
  except (FileNotFoundError,ProcessLookupError):pass
 row['processes']=list(rows.values());save()
try:
 assert os.geteuid()==0 and os.uname().machine=='x86_64' and os.environ.get('CRG_STARTUP1008')=='authorized-disposable-test-node-only'
 for name,digest in plan['source_sha256'].items():assert hashlib.sha256((candidates/name).read_bytes()).hexdigest()==digest
 assert plan['job_sha256']==hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
 for name,digest in plan['private_fixture_sha256'].items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest
 previous=pathlib.Path('/var/tmp/crg-default980-results-20261113/report.json');assert hashlib.sha256(previous.read_bytes()).hexdigest()==plan['previous980_report_sha256'] and json.loads(previous.read_bytes())['phase']=='failed'
 previous_cold=pathlib.Path('/var/tmp/crg-high572-cold-20261112/report.json');assert hashlib.sha256(previous_cold.read_bytes()).hexdigest()==plan['prior_exact_high_cold_report_sha256'];c=json.loads(previous_cold.read_bytes());assert c['phase']=='passed' and len(c['tests'])==44 and all(v['passed'] for v in c['tests'])
 for previous_ns in ['crg-vendor-lab-high572-20261112','crg-vendor-lab-default980-dbs-20261113','crg-vendor-lab-default980-hisdbs-20261113']:
  assert not run(['kubectl','get','namespace',previous_ns,'--ignore-not-found','-o','json']).stdout.strip()
 assert not root.exists();root.mkdir(mode=0o700)
 report.update(job_sha256=plan['job_sha256'],plan_sha256=hashlib.sha256((candidates/'plan.json').read_bytes()).hexdigest(),memory_policy='high-reclaim-throttle',frozen_probe_spec=plan['original_probe_specs'][role_argument])
 info=json.loads(run([str(candidates/'binaries/crg-linux-amd64'),'build-info']).stdout);assert info['version']=='v1.0.0-preview.4' and info['revision']==plan['source_revision'] and info['memory_policy']=='high-reclaim-throttle; percentages may be exceeded; external hard limits retained'
 report['sources']={'preview4':{'revision':plan['source_revision'],'binary_sha256':plan['source_sha256']['binaries/crg-linux-amd64']}};report['build_info']=info;save()
 gates=root/'gates';gates.mkdir(mode=0o700)
 aux=root/'aux';aux.mkdir(mode=0o700);shutil.copyfile('/usr/bin/etcd',aux/'etcd');(aux/'etcd').chmod(0o755)
 if run(['kubectl','get','namespace',ns],False).returncode==0:raise RuntimeError('namespace already exists')
 create({'apiVersion':'v1','kind':'Namespace','metadata':{'name':ns,'labels':{'managed-by':'crg-vendor-test'}}});created=True
 namespace_uid=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout)['metadata']['uid'];report['namespace_uid']=namespace_uid;save()
 create({'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'deny-all','namespace':ns},'spec':{'podSelector':{},'policyTypes':['Ingress','Egress']}})
 images=json.loads((source/'vendor-import.json').read_text())['images']
 for index,(candidate,role,bandwidth) in enumerate([('preview4',role_argument,percent)]):
  key=candidate+'-'+role+'-percent'+str(percent)+'-startup';pod_created=False;campaign_job=None;item={'phase':'preparing','candidate_branch':candidate,'role':role,'percentages':{k:percent for k in ['cpu_percent','memory_percent','io_percent']},'starts':[]};report['roles'][key]=item;save()
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
   config={} if percent==20 else {'cpu_percent':30,'memory_percent':30,'io_percent':30};(folder/'crg-config/config.json').write_text(json.dumps(config,separators=(',',':')))
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
   business_container=next(v for v in pod['spec']['containers'] if v['name']==role);business_container.update(plan['original_probe_specs'][role])
   private=folder/'pod.json';private.write_text(json.dumps(pod));private.chmod(0o600)
   def sql(query,database='postgres',timeout=60):
    command='/opt/postgresql/pgsql/bin/psql -XAtw -h127.0.0.1 -p5432 -U postgres -d '+database+' -v ON_ERROR_STOP=1 -c '+shlex.quote(query)
    return ex(role,'su','-','postgres','-c',command,timeout=timeout).stdout.strip()
   def controls(group):return {f:(group/f).read_text().strip() for f in ['cpu.max','memory.max','io.max','pids.max','cpu.weight','io.weight','memory.high','memory.swap.max']}
   def boot(phase):
    row={'phase':phase};item['starts'].append(row);save();create(pod);item['pod_present']=True;save()
    run(['kubectl','wait','-n',ns,'--for=condition=Ready','pod/'+role+'-business','--timeout=90s'],timeout=100)
    meta=json.loads(run(['kubectl','get','pod','-n',ns,role+'-business','-o','json']).stdout);cid=next(x['containerID'].split('://')[1] for x in meta['status']['containerStatuses'] if x['name']==role)
    pid=json.loads(run(['crictl','inspect',cid]).stdout)['info']['pid']
    actual_image=next(v['imageID'] for v in meta['status']['containerStatuses'] if v['name']==role);assert actual_image.rsplit('sha256:',1)[-1]==plan['expected_original_image_sha256'][role]
    row.update(pod_uid=meta['metadata']['uid'],container_id=cid,original_image_id=actual_image,original_probe_specs={k:next(c for c in meta['spec']['containers'] if c['name']==role).get(k) for k in plan['original_probe_specs'][role]});assert row['original_probe_specs']==plan['original_probe_specs'][role];boot_nodes[row['pod_uid']]=meta['spec']['nodeName'];save()
    if pid<=1 or meta['metadata']['labels'].get('managed-by')!='crg-vendor-test' or any(meta['spec'].get(x) for x in ['hostNetwork','hostPID','hostIPC']):raise RuntimeError('foreign or host-namespace Pod')
    for namespace in ['net','pid','mnt']:
     if os.stat('/proc/%d/ns/%s'%(pid,namespace)).st_ino==os.stat('/proc/self/ns/'+namespace).st_ino:raise RuntimeError('test container shares host namespace')
    group=pathlib.Path('/sys/fs/cgroup')/next(x.split('::',1)[1].lstrip('/') for x in pathlib.Path('/proc',str(pid),'cgroup').read_text().splitlines() if x.startswith('0::'))
    if group.name!='cri-containerd-'+cid+'.scope':raise RuntimeError('cold-rebuild self leaf mismatch')
    initial=controls(group);row['container_id']=cid;row['runtime_original_controls']=initial
    row.update(group=str(group),pod_parent=str(group.parent),init_pid=pid,init_start_ticks=int(pathlib.Path('/proc',str(pid),'stat').read_bytes().rsplit(b')',1)[1].split()[19]));capture_processes(row,group)
    run(['nsenter','-t',str(pid),'-n','--','ip','link','set','dev','eth0','down'])
    if 'state DOWN' not in run(['nsenter','-t',str(pid),'-n','--','ip','-o','link','show','dev','eth0']).stdout:raise RuntimeError('network gate not isolated')
    cachefile=folder/'cache-state/status.json'
    def cache_stamp():
     try:
      st=cachefile.stat();return (st.st_ino,st.st_mtime_ns,st.st_size)
     except FileNotFoundError:return None
    previous_cache_stamp=cache_stamp()
    def current_cache_enforcing():
     current=[]
     for process in (group/'cgroup.procs').read_text().splitlines():
      try:
       p=pathlib.Path('/proc')/process;argv=p.joinpath('cmdline').read_bytes().split(b'\0')
       if len(argv)>1 and pathlib.Path(os.fsdecode(argv[0])).name=='containercacheguard' and argv[1]==b'run':current.append(hashlib.sha256(p.joinpath('exe').read_bytes()).hexdigest())
      except (FileNotFoundError,ProcessLookupError):pass
     return current==['757ba385a0ee4bdadc968b96b5c3e69fd44353060e5ab28520fd6f73a59902de'] and cache_stamp() is not None and cache_stamp()!=previous_cache_stamp and json.loads(cachefile.read_text()).get('action')=='enforce'
    doctor=json.loads(ex(role,'/opt/crg/crg','doctor','--config','/etc/crg/config.json').stdout);envinfo=doctor['environment']
    if envinfo['cgroup']!=str(group) or envinfo.get('cgroup_version')!='v2' or doctor.get('memory_policy')!='high-reclaim-throttle':raise RuntimeError('pre-gate own high environment differs')
    if initial['cpu.max']!='800000 100000' or initial['memory.max']!='21474836480' or initial['memory.high']!='max' or initial['io.max']!='':raise RuntimeError('pre-gate original runtime differs')
    cpu_online=pathlib.Path('/sys/devices/system/cpu/online').read_text().strip();cpu_count=sum(int(v.split('-')[-1])-int(v.split('-')[0])+1 for v in cpu_online.split(','));hostmem=int(next(v.split()[1] for v in pathlib.Path('/proc/meminfo').read_text().splitlines() if v.startswith('MemTotal:')))*1024;page=os.sysconf('SC_PAGE_SIZE')
    assert envinfo['host_online_cpus']==cpu_count and envinfo['host_memory_bytes']==hostmem
    row['independent_host_basis']={'online_cpu_list':cpu_online,'cpu_count':cpu_count,'MemTotal_bytes':hostmem,'page_bytes':page};row['expected_formula_before_gate']=plan['percentage_formula']
    row['IO_profile_exists_before_boot']=(folder/'crg-config/io-profile.json').exists();row['IO_profile_before_boot_sha256']=hashlib.sha256((folder/'crg-config/io-profile.json').read_bytes()).hexdigest() if row['IO_profile_exists_before_boot'] else None
    started=time.monotonic();row['gate_monotonic']=started;row['gate_epoch']=time.time();deadline=started+300;(gates/meta['metadata']['uid']).write_text('isolated');status=folder/'resource-state/status.json'
    while time.monotonic()<deadline:
     reserve();row['last_controls']=controls(group);row['memory_events']=(group/'memory.events').read_text();row.setdefault('startup_samples',[]).append({'elapsed_seconds':time.monotonic()-started,'io.stat':(group/'io.stat').read_text(),'io.pressure':(group/'io.pressure').read_text(),'cpu.stat':(group/'cpu.stat').read_text(),'memory.current':(group/'memory.current').read_text()});save()
     try:
      q=ex(role,'su','-','postgres','-c','/opt/postgresql/pgsql/bin/pg_isready -h127.0.0.1 -p5432 -t2',check=False,timeout=max(0.01,min(15,deadline-time.monotonic())))
      row['last_PG_probe_exit']=q.returncode
      if q.returncode==0 and time.monotonic()<deadline:
       row.setdefault('PG_ready_seconds',time.monotonic()-started)
       api="import urllib2,json; r=urllib2.urlopen(urllib2.Request('http://127.0.0.1:8090/test',data='{}',headers={'Content-Type':'application/json'}),timeout=3); assert r.getcode()==200; assert json.loads(r.read(1024))['Result']=='000'"
       a=ex(role,'python','-c',api,check=False,timeout=max(0.01,min(10,deadline-time.monotonic())));row['last_API_probe_exit']=a.returncode
       if a.returncode==0:row.setdefault('API_ready_seconds',time.monotonic()-started)
       if a.returncode==0 and status.exists() and json.loads(status.read_text()).get('state')=='managed' and time.monotonic()<deadline:break
     except subprocess.TimeoutExpired:row['observation_timeouts']=row.get('observation_timeouts',0)+1
     save();time.sleep(max(0,min(3,deadline-time.monotonic())))
    else:raise RuntimeError('original PG/API/managed cold-start budget not met within300s')
    row['ready_and_managed_seconds']=time.monotonic()-started;state=json.loads(status.read_text());row['resource_identity']=state['plan']['environment']['identity'];row['actual_controls']=controls(group)
    profile_raw=(folder/'crg-config/io-profile.json').read_bytes();profile=json.loads(profile_raw);assert profile['version']==2 and profile['method']=='direct-sync-qdepth1-seq1m-random4k' and len(profile['devices'])==1
    dev=profile['devices'][0];assert len(dev['measurements'])==3 and all(dev[k]==sorted(v[k] for v in dev['measurements'])[1] for k in ['read_bps','write_bps','read_iops','write_iops'])
    assert re.fullmatch('[0-9]+:[0-9]+',dev['device']) and re.fullmatch('[0-9a-f]{64}',dev['identity'])
    expected_cpu=str(cpu_count*percent*1000)+' 100000';expected_high=str((hostmem*percent//100)//page*page);expected_IO='rbps=%d wbps=%d riops=%d wiops=%d'%tuple(max(1,dev[k]*percent//100) for k in ['read_bps','write_bps','read_iops','write_iops'])
    wanted=dict(initial);wanted.update({'cpu.max':expected_cpu,'memory.high':expected_high,'io.max':dev['device']+' '+expected_IO})
    mutations={}
    for setting in [{'file':'cpu.max','value':expected_cpu},{'file':'memory.high','value':expected_high},{'file':'io.max','device':dev['device'],'device_identity':dev['identity'],'value':expected_IO}]:
     value=dict(setting,original='rbps=max wbps=max riops=max wiops=max' if setting['file']=='io.max' else initial[setting['file']],applied=setting['value']);mutations[setting['file']+':'+setting.get('device','')]=value
    expected_journal={'version':1,'identity':envinfo['identity'],'target':str(group),'mutations':mutations};row['expected_controls_from_frozen_formula']=wanted;row['expected_journal_from_runtime_originals_and_profile']=expected_journal
    row['actual_journal']=json.loads((folder/'resource-state/journal.json').read_text());row['automatic_io']=state.get('automatic_io');row['IO_profile_sha256']=hashlib.sha256(profile_raw).hexdigest();row['recorded_runtime_documents']={}
    for name,path in [('status',status),('journal',folder/'resource-state/journal.json'),('profile',folder/'crg-config/io-profile.json')]:
     raw=path.read_bytes();assert len(raw)<=1048576;row['recorded_runtime_documents'][name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'exact_utf8':raw.decode()}
    if row['actual_controls']!=wanted or row['actual_journal']!=expected_journal or row['resource_identity']!=envinfo['identity']:raise RuntimeError('actual percent high controls or exact original journal differs from frozen formula')
    record(key+'-'+phase+'-original-PG-API-and-exact-three-percent-controls',set(x['file'] for x in state['items'])=={'cpu.max','memory.high','io.max'} and len(state['items'])==3 and all(x['state']=='applied' for x in state['items']) and state['plan']['percentages']=={k:percent for k in ['cpu_percent','memory_percent','io_percent']} and state['automatic_io']['state'] in ['calibrated','reused'] and (not row['IO_profile_exists_before_boot'] if phase=='initialization' else row['IO_profile_before_boot_sha256']==row['IO_profile_sha256']))
    record(key+'-'+phase+'-original-readonly-cache-mount','ro' in ex(role,'findmnt','-n','-o','OPTIONS','/opt/ccg').stdout.strip().split(','))
    cachefile=folder/'cache-state/status.json';cache_started=time.monotonic();cache_deadline=min(started+300,cache_started+45)
    while time.monotonic()<cache_deadline:
     if current_cache_enforcing():break
     time.sleep(min(1,max(0,cache_deadline-time.monotonic())))
    row['cache_observation_seconds']=time.monotonic()-cache_started
    row['cache_current_source_and_fresh_status']=current_cache_enforcing()
    record(key+'-'+phase+'-cache-enforce-within-original-budget',row['cache_current_source_and_fresh_status'] and time.monotonic()<=started+300)
    record(key+'-'+phase+'-original-ls-probe',ex(role,'ls',check=False,timeout=10).returncode==0)
    daily=list((folder/'log/crg').glob('crg-*.log'));events=[json.loads(x) for file in daily for x in file.read_text().splitlines()]
    record(key+'-'+phase+'-daily0600-v2-high-logs-and-automatic-profile',bool(daily) and all(file.stat().st_mode&0o777==0o600 for file in daily) and any(x['event']=='cgroup_detected' and x.get('fields',{}).get('check',{}).get('cgroup_version')=='v2' for x in events) and any(x['event']=='resource_status' and x.get('fields',{}).get('memory_policy')=='high-reclaim-throttle' for x in events) and (folder/'crg-config/io-profile.json').is_file())
    agents=[]
    for process in (group/'cgroup.procs').read_text().splitlines():
     try:
      p=pathlib.Path('/proc')/process;argv=p.joinpath('cmdline').read_bytes().split(b'\0')
      if len(argv)>1 and pathlib.Path(os.fsdecode(argv[0])).name=='crg' and argv[1]==b'run':agents.append(hashlib.sha256(p.joinpath('exe').read_bytes()).hexdigest())
     except (FileNotFoundError,ProcessLookupError):pass
    record(key+'-'+phase+'-exactly-one-source-qualified-Agent',agents==[report['sources'][candidate]['binary_sha256']])
    capture_processes(row,group)
    row['memory_events']=(group/'memory.events').read_text();record(key+'-'+phase+'-no-container-OOM',dict(x.split() for x in row['memory_events'].splitlines())['oom_kill']=='0')
    row['PG_start']=sql('SELECT pg_postmaster_start_time();');save();return {'row':row,'group':group,'daily':daily,'PG_start':row['PG_start']}
   def capture_real_probe(phase,strict):
    row=item['starts'][-1];passed=False
    try:
     result=scoped_probe.observe(row,ns,role+'-business',role,boot_nodes[row['pod_uid']],reserve,save);passed=result['phase']=='passed'
    except Exception as error:row['real_kubelet_probe_error']={'class':type(error).__name__};save()
    report['tests'].append({'name':key+'-'+phase+'-actual-original-kubelet-liveness-by-exact-Pod-UID','passed':passed});save()
    if strict and not passed:raise RuntimeError('actual original kubelet probe not accepted')
   def boot_with_probe(phase):
    try:value=boot(phase)
    except Exception:
     capture_real_probe(phase,False);raise
    capture_real_probe(phase,True);return value
   first=boot_with_probe('initialization');config_hash=hashlib.sha256((folder/'crg-config/config.json').read_bytes()).hexdigest()
   schema='crg_startup_20261113r1008';db='crg_startup_restore_20261113r1008'
   sql('CREATE SCHEMA '+schema+'; CREATE TABLE '+schema+'.fixture(id bigint PRIMARY KEY,payload text NOT NULL,counter bigint NOT NULL DEFAULT 0); ALTER TABLE '+schema+'.fixture ALTER COLUMN payload SET STORAGE EXTERNAL; INSERT INTO '+schema+".fixture(id,payload) SELECT g,repeat(md5(g::text),128) FROM generate_series(1,16384) g; CREATE TABLE "+schema+'.marker(k integer PRIMARY KEY); INSERT INTO '+schema+'.marker SELECT generate_series(1,128); CHECKPOINT;',timeout=300)
   checksum="SELECT count(*),sum(id),sum(octet_length(payload)),md5(string_agg(md5(payload),'' ORDER BY id)),sum(counter) FROM "+schema+'.fixture;'
   marker='SELECT count(*),sum(k) FROM '+schema+'.marker;';before=sql(checksum);mark_before=sql(marker);item['payload_before']=before;item['marker_before']=mark_before
   record(key+'-initial-64MiB-payload-and128-marker',before.split('|')[:3]==['16384','134225920','67108864'] and mark_before=='128|8256')
   first_log_prefix={str(f.relative_to(folder/'log/crg')):f.read_bytes() for f in first['daily']};first_identity=first['row']['resource_identity'];delete_pod(role);item['pod_present']=False;save()
   record(key+'-initial-cgroup-gone-before-after-extraction-Pod',not first['group'].exists());reserve(28)
   extracted=boot_with_probe('after-extraction-recreation')
   previous=json.loads((folder/'resource-state/journal.previous.json').read_text());current=json.loads((folder/'resource-state/journal.json').read_text())
   record(key+'-after-extraction-new-ID-journal-and-unchanged-config',first['row']['container_id']!=extracted['row']['container_id'] and previous['identity']==first_identity and current['identity']==extracted['row']['resource_identity'] and current['identity']!=first_identity and hashlib.sha256((folder/'crg-config/config.json').read_bytes()).hexdigest()==config_hash)
   record(key+'-after-extraction-data-and-PG-restart-consistent',sql(checksum)==before and sql(marker)==mark_before and first['PG_start']!=extracted['PG_start'])
   record(key+'-after-extraction-daily-log-appends-across-ID-change',all((folder/'log/crg'/n).read_bytes().startswith(data) and (folder/'log/crg'/n).stat().st_size>len(data) for n,data in first_log_prefix.items()))
   dump='/opt/postgresql/basebackup/crg-before-rebuild.dump';backup_command='/opt/postgresql/pgsql/bin/pg_dump -w -h127.0.0.1 -p5432 -U postgres -Fc -n '+schema+' -f '+dump+' postgres'
   began=time.monotonic();ex(role,'su','-','postgres','-c',backup_command,timeout=300);item['logical_backup_seconds']=time.monotonic()-began
   archive=folder/'postgresql/basebackup/crg-before-rebuild.dump';backup_sha=hashlib.sha256(archive.read_bytes()).hexdigest();listing=ex(role,'su','-','postgres','-c','/opt/postgresql/pgsql/bin/pg_restore -l '+dump,timeout=30).stdout
   item.update(logical_backup_sha256=backup_sha,logical_backup_bytes=archive.stat().st_size);save()
   record(key+'-logical-backup-created-and-readable','TABLE DATA '+schema+' fixture' in listing and 'TABLE DATA '+schema+' marker' in listing and archive.stat().st_size>0 and dict(x.split() for x in (extracted['group']/'memory.events').read_text().splitlines())['oom_kill']=='0')
   log_prefix={str(f.relative_to(folder/'log/crg')):f.read_bytes() for f in extracted['daily']};old_identity=extracted['row']['resource_identity'];delete_pod(role);item['pod_present']=False;save()
   deadline=time.monotonic()+30
   while extracted['group'].exists() and time.monotonic()<deadline:time.sleep(.5)
   record(key+'-old-container-cgroup-gone-before-new-Pod',not extracted['group'].exists());reserve(28)
   second=boot_with_probe('after-backup-recreation');item['payload_after']=sql(checksum);item['marker_after']=sql(marker)
   previous=json.loads((folder/'resource-state/journal.previous.json').read_text());current=json.loads((folder/'resource-state/journal.json').read_text())
   item.update(archived_previous_journal=previous,current_recreated_journal=current,original_config_sha256=config_hash,configuration_bytes_unchanged=hashlib.sha256((folder/'crg-config/config.json').read_bytes()).hexdigest()==config_hash);save()
   record(key+'-new-container-and-journal-identity-with-same-config',extracted['row']['container_id']!=second['row']['container_id'] and old_identity!=second['row']['resource_identity'] and previous['identity']==old_identity and current['identity']==second['row']['resource_identity'] and hashlib.sha256((folder/'crg-config/config.json').read_bytes()).hexdigest()==config_hash)
   record(key+'-data-backup-and-PG-restart-consistent',item['payload_after']==before and item['marker_after']==mark_before and hashlib.sha256(archive.read_bytes()).hexdigest()==backup_sha and extracted['PG_start']!=second['PG_start'])
   record(key+'-persistent-daily-log-appends-across-ID-change',all((folder/'log/crg'/n).read_bytes().startswith(data) and (folder/'log/crg'/n).stat().st_size>len(data) for n,data in log_prefix.items()))
   sql('CREATE DATABASE '+db+';');ex(role,'su','-','postgres','-c','/opt/postgresql/pgsql/bin/pg_restore --exit-on-error -w -h127.0.0.1 -p5432 -U postgres -d '+db+' '+dump,timeout=300)
   record(key+'-logical-restore-to-independent-database-preserves64MiB-and-marker',sql(checksum,db)==before and sql(marker,db)==mark_before and sql(checksum)==before);sql('DROP DATABASE '+db+';')
   disabled=json.loads(ex(role,'/opt/crg/crg','disable','--config','/etc/crg/config.json',timeout=30).stdout);actual=controls(second['group']);item['controls_after_disable']=actual;item['final_memory_events']=(second['group']/'memory.events').read_text()
   item['final_journal']=json.loads((folder/'resource-state/journal.json').read_text())
   expected_empty={k:v for k,v in second['row']['expected_journal_from_runtime_originals_and_profile'].items() if k!='mutations'};expected_empty['mutations']={}
   if item['final_journal']!=expected_empty:raise RuntimeError('final matching empty journal differs')
   record(key+'-disable-restores-new-container-runtime-originals',disabled['state']=='restored' and actual==second['row']['runtime_original_controls'] and dict(x.split() for x in item['final_memory_events'].splitlines())['oom_kill']=='0')
   item['phase']='cold-rebuild-passed';save()
  except Exception as error:item.update(phase='failed',error=str(error),traceback=traceback.format_exc());save()
  finally:
   if item.get('pod_present'):delete_pod(role);item['pod_present']=False
   absent=run(['kubectl','get','pod','-n',ns,role+'-business','--ignore-not-found','-o','json'],False);item['own_pod_removed']=absent.returncode==0 and not absent.stdout.strip();save()
   if not item['own_pod_removed']:raise RuntimeError('own Pod absence could not be verified')
 report['phase']='passed' if len(report['roles'])==1 and all(v['phase']=='cold-rebuild-passed' for v in report['roles'].values()) else 'failed'
except Exception as e:report.update(phase='failed',error=str(e),traceback=traceback.format_exc())
finally:
 if created:
  m=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout)
  if m['metadata']['labels'].get('managed-by')!='crg-vendor-test' or m['metadata']['uid']!=namespace_uid:raise RuntimeError('namespace cleanup ownership mismatch')
  run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=150s'],False,160);absent=run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json'],False);report['namespace_absent']=absent.returncode==0 and not absent.stdout.strip()
 if root.exists():save()
print(json.dumps({'phase':report['phase'],'checks':len(report['tests']),'error':report.get('error')}))

raise SystemExit(0 if report['phase']=='passed' and report.get('namespace_absent') is True and len(report['roles'])==1 and len(report['tests'])==36 and all(x['passed'] for x in report['tests']) else 1)
