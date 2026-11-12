import pathlib,json,subprocess,time,traceback,hashlib,os,shutil,re,uuid,importlib.util,signal
root=pathlib.Path('/var/tmp/crg-high613-pressure-20261112');source=pathlib.Path('/var/tmp/crg-business-20261110');candidates=pathlib.Path('/var/tmp/crg-high613-tools-20261112');ns='crg-vendor-lab-high613-20261112';created=False
report={'resource_mode':'manual','declared_test_budget':{'cpu_cores':7.2,'memory_high_bytes':20001980416,'bandwidth_cases_MiB_per_second':[64],'read_write_iops':4096},'phase':'waiting-for-automatic-calibration-checks','scope':'memory.high full32: same original CPU/IO/SLA budgets; two high apply/release checks replace obsolete hard-max defer/retry; same container paths and read-only CCG mount as read-only deployment inventory; fresh private test-node backing directories and loopback DCS, no production data; original business/image/database parameters','roles':{},'tests':[]}
spec=importlib.util.spec_from_file_location('pressure_core',candidates/'vendor-memory-high-pressure-core.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
def interrupted(signum,frame):raise RuntimeError('isolated pressure driver interrupted')
signal.signal(signal.SIGTERM,interrupted)
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
try:
 planraw=(candidates/'plan.json').read_bytes();plan=json.loads(planraw);report['plan_sha256']=hashlib.sha256(planraw).hexdigest()
 if plan['namespace']!=ns or plan['output']!=str(root) or plan['job_sha256']!=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest():raise RuntimeError('frozen high-pressure plan differs')
 for name,want in plan['source_sha256'].items():
  if hashlib.sha256((candidates/name).read_bytes()).hexdigest()!=want:raise RuntimeError('frozen pressure dependency differs')
 qualification=json.loads((candidates/'native-v3-qualification.json').read_text())
 if qualification['phase']!='passed' or len(qualification['checks'])!=101 or not all(v['passed'] for v in qualification['checks']) or qualification.get('business_accepted') is True:raise RuntimeError('native tool qualification required, distinct from business acceptance')
 previous=json.loads(pathlib.Path('/var/tmp/crg-high610-pressure-20261112/report.json').read_text());receipt=json.loads(pathlib.Path('/var/tmp/crg-high610-tools-20261112/exit.json').read_text())
 if previous['phase']!='failed' or len(previous['tests'])!=4 or receipt['exit']!=1 or not previous['namespace_absent']:raise RuntimeError('first pressure preparation failure not terminal and cleaned')
 if any(v.get('error')!='EDGE_TIMED_API_COPY' or len(v.get('reload_intervals',[])) or not v.get('own_leaf_absent') or not v.get('own_parent_absent') or not v.get('original_config_and_profile_absence_restored') for v in previous['roles'].values()):raise RuntimeError('first pressure preparation failure differs')
 absent=run(['kubectl','get','namespace','crg-vendor-lab-high610-20261112','--ignore-not-found','-o','json'])
 if absent.stdout.strip():raise RuntimeError('first pressure preparation namespace present')
 report['first_attempt_failure_before_native_preserved']=True
 report['native_tool_qualification_sha256']=hashlib.sha256((candidates/'native-v3-qualification.json').read_bytes()).hexdigest();report['original_failure_still_unproven']=True
 if os.geteuid()!=0 or os.uname().machine!='x86_64' or os.environ.get('CRG_HIGH613_PRESSURE')!='authorized-disposable-test-node-only':raise RuntimeError('explicit authorized native test fixture required')
 expected={'tests/vendor-soak-load.py': 'ba87ef2d646b723eb8419de25ffcd736f7a5b0925716f4b638761dff70bb2461', 'tests/vendor-soak-campaign.py': 'b49d5a73654c5cf7c93b04851f3409eea318b3a9c71c0e8f601f252a3dda07ea', 'tests/vendor-engine-smoke.py': 'b0d4fe313156743ff1424b46eb58c5ab5b8e1f2c91851420023f5f018dd08e5c', 'examples/optional-agent.sh': 'f7e7208f58bac7066d75d49cb17199b720e3d05bb5953e2a7a7800f881b54b79', 'binaries/crg-linux-amd64': '6088721cd4846f95b3b71c82f9884e1909797a199d962b50519c9e013de98b4e', 'identity-qualification.json': '5bcb84aaf61dd3f7d9d1978483fc30be13aab726ca13f79c78802cc005d9ef70', 'integration-qualification.json': '0671b09e69a6f70741aa28636cc54e9144f5a16fc7c7ee37d07088c5481dec1c'}
 for name,digest in expected.items():
  if hashlib.sha256((candidates/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('fixture member differs from frozen source')
 identity=json.loads((candidates/'identity-qualification.json').read_text());ci=json.loads((candidates/'integration-qualification.json').read_text())
 if identity.get('phase')!='published-preview4-built-and-local-package-checks-passed' or identity.get('version')!='v1.0.0-preview.4' or identity.get('production_files_exactly_equal_to_180')!=50 or ci.get('phase')!='passed' or ci.get('version')!='v1.0.0-preview.4' or ci.get('controller_checks')!=88 or len(ci.get('CI',[]))!=4 or ci.get('all_eight_files_equal_Windows_each_cell') is not True or identity.get('source_revision')!='180c86ad7986a76526a41575cc1c176d5da98a9c' or ci.get('source_revision')!='180c86ad7986a76526a41575cc1c176d5da98a9c':raise RuntimeError('exact versioned artifact qualifications missing')
 if identity['file_sha256']['crg-linux-amd64']!=expected['binaries/crg-linux-amd64'] or identity['local_integrity_checks']['count']!=14 or not all(x['passed'] is True for x in identity['local_integrity_checks']['checks']) or identity['native_AMD64_build_identity_probe']['version_output']!='v1.0.0-preview.4' or identity['native_AMD64_build_identity_probe']['binary_sha256']!=expected['binaries/crg-linux-amd64'] or identity['same_host_fresh_checkout_reproduction']['byte_equal'] is not True:raise RuntimeError('versioned package identity checks incomplete')
 for cell in ci['CI']:
  if cell['identity']['actual']['crg-linux-amd64']!=expected['binaries/crg-linux-amd64'] or cell['report']['phase']!='passed' or len(cell['report']['tests'])!=22 or not all(x['passed'] is True for x in cell['report']['tests']) or not all(x is True for x in cell['report']['cleanup'].values()):raise RuntimeError('versioned native cell incomplete')
 for name,digest in {'fixture/containercacheguard': '757ba385a0ee4bdadc968b96b5c3e69fd44353060e5ab28520fd6f73a59902de', 'fixture/dbs/supervisor.sh': '4dce0b38e6c01a9effe08457dc31206a0abaf7ff14eb9ec59dace97a6f1c0211', 'fixture/hisdbs/supervisor.sh': '4dce0b38e6c01a9effe08457dc31206a0abaf7ff14eb9ec59dace97a6f1c0211'}.items():
  if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('original private cache/supervisor fixture source changed')
 info=json.loads(run([str(candidates/'binaries/crg-linux-amd64'),'build-info']).stdout)
 if info.get('revision')!='180c86ad7986a76526a41575cc1c176d5da98a9c' or info.get('arch')!='amd64' or info.get('version')!='v1.0.0-preview.4':raise RuntimeError('candidate metadata differs')
 report['sources']={'v10':{'revision':'180c86ad7986a76526a41575cc1c176d5da98a9c','binary_sha256':'6088721cd4846f95b3b71c82f9884e1909797a199d962b50519c9e013de98b4e'}};report['build_info']=info
 report['job_sha256']=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
 if info.get('memory_policy')!='high-reclaim-throttle; percentages may be exceeded; external hard limits retained' or ci.get('memory_policy')!='high-reclaim-throttle' or identity.get('memory_policy')!='high-reclaim-throttle':raise RuntimeError('high memory policy not qualified')
 report['memory_policy']='high-reclaim-throttle'
 previous=json.loads(pathlib.Path('/var/tmp/crg-high544-realpaths-20261112/report.json').read_text())
 if previous.get('phase')!='failed' or len(previous.get('tests',[]))!=10 or not all(x['passed'] for x in previous['tests']) or previous.get('job_sha256')!='708c61937263d08a560c7ba929696ff7a8d473323cc294dc8892aea107e83973' or previous.get('namespace_absent') is not True or json.loads(pathlib.Path('/var/tmp/crg-high544-tools-20261112/business.exit.json').read_text()).get('exit')!=1:raise RuntimeError('prior failed campaign preparation not terminal and cleaned')
 previous_ns=run(['kubectl','get','namespace','crg-high544-business-20261112','--ignore-not-found','-o','json'],False)
 if previous_ns.returncode or previous_ns.stdout.strip():raise RuntimeError('prior failed namespace still exists')
 for role in ['dbs','hisdbs']:
  log=pathlib.Path('/var/tmp/crg-high544-realpaths-20261112')/('v10-'+role+'-bw64-campaign.log')
  if hashlib.sha256(log.read_bytes()).hexdigest()!='b463b1cf0f44bcf9b923f469157cce7031fe4c5a5027116464fefaf8b82e2aea':raise RuntimeError('original namespace guard rejection not retained')
 root.mkdir(mode=0o700,exist_ok=False);report['phase']='waiting-for-exact-source-overhead-terminal-cleanup';save()
 deadline=time.monotonic()+5400
 while time.monotonic()<deadline:
  reserve()
  p=pathlib.Path('/var/tmp/crg-high542-overhead-20261112/report.json');e=pathlib.Path('/var/tmp/crg-high542-tools-20261112/overhead.exit.json')
  if p.exists() and e.exists():
   d=json.loads(p.read_text());receipt=json.loads(e.read_text())
   if d.get('phase') in ['passed','failed']:
    if d.get('phase')!='passed' or d.get('source')!='180c86ad7986a76526a41575cc1c176d5da98a9c' or d.get('namespace_absent') is not True or receipt.get('exit')!=0:raise RuntimeError('exact-source overhead not accepted; no business Pod created')
    if d.get('binary_sha256')!=expected['binaries/crg-linux-amd64'] or d.get('build_info',{}).get('version')!='v1.0.0-preview.4' or d.get('measurement_elapsed_seconds',0)<1800 or d.get('job_sha256')!='f78e7152bc78fd8344e2bf113e4f98b94f4cfd0391969137df68924f51749e2c' or receipt.get('job_sha256')!=d['job_sha256'] or len(d.get('cases',{}))!=3 or not all(x.get('passed') is True for x in d['cases'].values()):raise RuntimeError('own versioned overhead is not complete and accepted')
    absent=run(['kubectl','get','namespace','crg-high542-overhead-20261112','--ignore-not-found','-o','json'],False)
    if absent.returncode or absent.stdout.strip():raise RuntimeError('overhead namespace independently not absent')
    report['overhead_report_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();break
  time.sleep(5)
 else:raise RuntimeError('overhead acceptance did not become terminal; no business Pod created')
 prior=pathlib.Path('/var/tmp/crg-realpaths12-20261110/report.json')
 if not prior.is_file() or json.loads(prior.read_text()).get('phase')!='passed' or json.loads(prior.read_text()).get('namespace_absent') is not True:raise RuntimeError('prior manual business fixture not passed and cleaned')
 absent=run(['kubectl','get','namespace','crg-vendor-lab-realpaths12-20261110','--ignore-not-found','-o','json'],False)
 if absent.returncode or absent.stdout.strip():raise RuntimeError('prior manual business namespace independently not absent')
 (root/'tools').mkdir(mode=0o700)
 for name in ['vendor-soak-load.py','vendor-soak-campaign.py','vendor-engine-smoke.py']:shutil.copyfile(candidates/'tests'/name,root/'tools'/name)
 report['phase']='preparing';save()
 gates=root/'gates';gates.mkdir(mode=0o700)
 aux=root/'aux';aux.mkdir(mode=0o700);shutil.copyfile('/usr/bin/etcd',aux/'etcd');(aux/'etcd').chmod(0o755)
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
   execution.business_native(role,folder,group,item)
   disabled=json.loads(ex(role,'/opt/crg/crg','disable','--config','/etc/crg/config.json',timeout=30).stdout)
   item['disabled']=disabled
   record(key+'-explicit-disable-restores-true-runtime-originals',disabled['state']=='restored' and core.controls(group)==runtime_original)
   item['phase']='short-acceptance-passed';save()
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
    config=folder/'crg-config/config.json';temp=config.with_name('high613.restore');temp.write_bytes(original_config if original_config is not None else json.dumps(core.MANUAL).encode());temp.chmod(0o600);temp.replace(config)
    profile=folder/'crg-config/io-profile.json'
    if profile.exists():
     if profile.is_symlink() or hashlib.sha256(profile.read_bytes()).hexdigest()!=core.PINS['profile']:raise RuntimeError('owned test profile changed before cleanup')
     profile.unlink()
    target=folder/'crg-config/high613.target.json'
    if target.exists():
     if target.is_symlink():raise RuntimeError('owned config target changed')
     target.unlink()
    item['original_config_and_profile_absence_restored']=json.loads(config.read_text())==core.MANUAL and (not item.get('original_config_sha256') or hashlib.sha256(config.read_bytes()).hexdigest()==item['original_config_sha256']) and not profile.exists()
   save()
   save()
 report['phase']='passed' if all(v['phase']=='short-acceptance-passed' for v in report['roles'].values()) else 'failed'
except Exception as e:report.update(phase='failed',error=str(e),traceback=traceback.format_exc())
finally:
 if created:
  m=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout)
  if m['metadata']['labels'].get('managed-by')!='crg-vendor-test':raise RuntimeError('namespace cleanup ownership mismatch')
  run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=150s'],False,160);absent=run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json'],False);report['namespace_absent']=absent.returncode==0 and not absent.stdout.strip()
 if root.exists():save()
print(json.dumps({'phase':report['phase'],'checks':len(report['tests']),'error':report.get('error')}))

raise SystemExit(0 if report['phase']=='passed' and report.get('namespace_absent') is True and len(report['roles'])==2 and len(report['tests'])==32 and all(x.get('original_config_and_profile_absence_restored') and x.get('own_leaf_absent') and x.get('own_parent_absent') for x in report['roles'].values()) else 1)
