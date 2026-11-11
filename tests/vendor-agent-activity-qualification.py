#!/usr/bin/env python3
"""Disposable actual-vendor Agent lifecycle qualification; default CLI is inert."""
import argparse,hashlib,json,os,pathlib,signal,subprocess,sys
sys.dont_write_bytecode=True
FROZEN_PLAN = {'schema': 'crg-agent-activity-vendor-plan-v1', 'work_root': '/var/tmp/crg-agent-activity417-20261111', 'tool_root': '/var/tmp/crg-agent-activity418-tools-20261111', 'namespace': 'crg-vendor-lab-agent-activity417-20261111', 'activity_source_sha256': 'bd11d8617637336f6ed30c291764550657158d94db0d1cbff43bb86a982b569f', 'base_source_sha256': 'cc99af7bde90d0436020517376ddee82e4da31639f1c7a2c02a3e1667a2222bc', 'host_qualification_source_sha256': '75b6b9dff26a4de42699692ca75a5f8dddc71222e332f9df90662935f625c2ac', 'host_qualification_tool_sha256': 'bd11d8617637336f6ed30c291764550657158d94db0d1cbff43bb86a982b569f', 'program': {'release': 'v1.0.0-preview.2', 'source_revision': 'd3706f3ea7ad279fea818e5ad1aa62ac5d3f8710', 'binary_sha256': 'dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8'}, 'expected_checks': 32, 'roles': ['dbs', 'hisdbs'], 'budget': {'cpu_cores': 7.2, 'memory_max_bytes': 20001980416, 'read_write_bps': 67108864, 'read_write_iops': 4096}, 'scope': 'short real vendor Agent lifecycle qualification, not full600 or ABBA', 'stable_release_accepted': False}

def run_qualification(frozen_plan,plan_sha256):
 import pathlib,json,subprocess,time,traceback,hashlib,os,shutil,re,uuid,datetime
 root=pathlib.Path('/var/tmp/crg-agent-activity417-20261111');source=pathlib.Path('/var/tmp/crg-business-20261110');candidates=pathlib.Path('/var/tmp/crg-published-migration398-tools-20261111');ns='crg-vendor-lab-agent-activity417-20261111';created=False
 report={'resource_mode':'manual','declared_test_budget':{'cpu_cores':7.2,'memory_max_bytes':20001980416,'read_write_bps':67108864,'read_write_iops':4096},'phase':'waiting-for-automatic-calibration-checks','scope':'same container paths and read-only CCG mount as read-only deployment inventory; fresh private test-node backing directories and loopback DCS, no production data; original business/image/database parameters','roles':{},'tests':[]}
 report.update(schema='crg-agent-activity-vendor-qualification-v1',plan_sha256=plan_sha256,qualified_program=frozen_plan['program'],
  scope='Test-only actual Agent STOP/CONT on both original vendor paths; short lifecycle qualification, not600 business or fixed-IO ABBA acceptance')
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
  if os.geteuid()!=0 or os.uname().machine!='x86_64' or os.environ.get('CRG_AGENT_ACTIVITY')!='authorized-disposable-test-node-only':raise RuntimeError('explicit authorized native fixture required')
  expected={'tests/vendor-soak-load.py': 'ba87ef2d646b723eb8419de25ffcd736f7a5b0925716f4b638761dff70bb2461', 'tests/vendor-soak-campaign.py': 'b49d5a73654c5cf7c93b04851f3409eea318b3a9c71c0e8f601f252a3dda07ea', 'tests/vendor-engine-smoke.py': 'b0d4fe313156743ff1424b46eb58c5ab5b8e1f2c91851420023f5f018dd08e5c', 'examples/optional-agent.sh': 'f7e7208f58bac7066d75d49cb17199b720e3d05bb5953e2a7a7800f881b54b79', 'identity-qualification.json': 'd293d2c400843b1a7765d38ef14aecd8c68333cfc29259b670e0bec8790ca77e', 'integration-qualification.json': '6c7500a860f5c1a633ca8f24ca1c8b3ada09b697bbbea0496bcb58183a45a634', 'overhead-qualification.json': '68f1c207bd7e8ba430163d2c8b0228339a707d81159369678b95a1db4230d720', 'business-qualification.json': 'f680f08aeeccb500c56655dfe5dbf07982e373928d70634fea400232e2090101', 'fault-qualification.json': 'b26dd6678137d9f25f5f21bd334b030805782bbb33441b68340c597df6b69ca5', 'binaries/previous': 'f07973272313db26d359797dda4665145f7dd6490bac2a55f9084bd367faf361', 'binaries/candidate': 'dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8'}
  for name,digest in expected.items():
   if hashlib.sha256((candidates/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('frozen payload differs')
  for name,digest in {'fixture/containercacheguard': '757ba385a0ee4bdadc968b96b5c3e69fd44353060e5ab28520fd6f73a59902de', 'fixture/dbs/supervisor.sh': '4dce0b38e6c01a9effe08457dc31206a0abaf7ff14eb9ec59dace97a6f1c0211', 'fixture/hisdbs/supervisor.sh': '4dce0b38e6c01a9effe08457dc31206a0abaf7ff14eb9ec59dace97a6f1c0211'}.items():
   if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('original private helper/supervisor differs')
  identity=json.loads((candidates/'identity-qualification.json').read_text());ci=json.loads((candidates/'integration-qualification.json').read_text())
  if identity.get('phase')!='unpublished-versioned-candidate-built-and-local-package-checks-passed' or identity.get('version')!='v1.0.0' or identity.get('production_files_exactly_equal_to_d370')!=50 or ci.get('phase')!='passed' or ci.get('version')!='v1.0.0' or ci.get('controller_checks')!=88 or len(ci.get('CI',[]))!=4 or ci.get('all_eight_files_equal_Windows_each_cell') is not True or identity.get('source_revision')!='d3706f3ea7ad279fea818e5ad1aa62ac5d3f8710' or ci.get('source_revision')!='d3706f3ea7ad279fea818e5ad1aa62ac5d3f8710':raise RuntimeError('exact versioned artifact qualifications missing')
  if identity['file_sha256']['crg-linux-amd64']!=expected['binaries/candidate'] or identity['local_integrity_checks']['count']!=14 or not all(x['passed'] is True for x in identity['local_integrity_checks']['checks']) or identity['native_AMD64_build_identity_probe']['version_output']!='v1.0.0' or identity['native_AMD64_build_identity_probe']['binary_sha256']!=expected['binaries/candidate'] or identity['same_host_fresh_checkout_reproduction']['byte_equal'] is not True:raise RuntimeError('versioned package identity checks incomplete')
  for cell in ci['CI']:
   if cell['identity']['actual']['crg-linux-amd64']!=expected['binaries/candidate'] or cell['report']['phase']!='passed' or len(cell['report']['tests'])!=22 or not all(x['passed'] is True for x in cell['report']['tests']) or not all(x is True for x in cell['report']['cleanup'].values()):raise RuntimeError('versioned native cell incomplete')
  for name in ['overhead-qualification.json','business-qualification.json','fault-qualification.json']:
   value=json.loads((candidates/name).read_text())
   if value.get('phase')!='passed' or value.get('source_revision')!='d3706f3ea7ad279fea818e5ad1aa62ac5d3f8710' or value.get('binary_sha256')!=expected['binaries/candidate']:raise RuntimeError('own versioned runtime qualification differs')
  report['sources']={'previous': {'revision': '7638ee9f871287d1056e267034e0c4e46903b66e', 'binary_sha256': 'f07973272313db26d359797dda4665145f7dd6490bac2a55f9084bd367faf361', 'release_status': 'published v0.1.0-rc.3-preview.1 exact official asset'}, 'candidate': {'revision': 'd3706f3ea7ad279fea818e5ad1aa62ac5d3f8710', 'binary_sha256': 'dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8', 'release_status': 'published v1.0.0-preview.2 exact official asset'}};report['build_info']={};report['job_sha256']=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
  for name in ['previous','candidate']:
   info=json.loads(run([str(candidates/'binaries'/name),'build-info']).stdout)
   if info.get('revision')!=report['sources'][name]['revision'] or info.get('arch')!='amd64':raise RuntimeError('published source or architecture differs')
   if name=='candidate' and (info.get('lock_protocol')!='cgroup-inode-flock+state-agent-lock-v1' or 1 not in info.get('journal_versions',[])):raise RuntimeError('candidate maintenance protocol differs')
   if name=='previous' and ('lock_protocol' in info or 'journal_versions' in info):raise RuntimeError('old published protocol absence differs')
   if name=='candidate' and info.get('version')!='v1.0.0':raise RuntimeError('candidate version differs')
   report['build_info'][name]=info
  root.mkdir(mode=0o700,exist_ok=False);report['phase']='waiting-for-current-source-fault-acceptance-and-cleanup';save()
  deadline=time.monotonic()+5400
  while time.monotonic()<deadline:
   reserve();p=pathlib.Path('/var/tmp/crg-realpaths66-20261111/report.json');e=pathlib.Path('/var/tmp/crg-r66-20261111/faults.exit.json')
   if p.exists() and e.exists():
    d=json.loads(p.read_text());receipt=json.loads(e.read_text())
    if d.get('phase') in ['passed','failed']:
     if d.get('phase')!='passed' or d.get('namespace_absent') is not True or receipt.get('exit')!=0 or len(d.get('roles',{}))!=20 or len(d.get('tests',[]))!=108 or not all(x['passed'] for x in d['tests']) or d.get('sources',{}).get('v10',{}).get('revision')!='d3706f3ea7ad279fea818e5ad1aa62ac5d3f8710':raise RuntimeError('current faults not accepted; no maintenance Pod created')
     if d.get('job_sha256')!='f21f4b4bdb5e3f01316ad954b030d408310c6ac40b503fe9c620fca53461f289' or receipt.get('job_sha256')!=d['job_sha256'] or d.get('build_info',{}).get('version')!='v1.0.0' or d.get('sources',{}).get('v10',{}).get('binary_sha256')!=expected['binaries/candidate'] or len({x['name'] for x in d['tests']})!=108:raise RuntimeError('own exact versioned faults missing')
     business_path=pathlib.Path('/var/tmp/crg-realpaths64-20261111/report.json');business=json.loads(business_path.read_text());business_exit=json.loads(pathlib.Path('/var/tmp/crg-r64-20261111/business.exit.json').read_text())
     if business.get('job_sha256')!='4bb896692b38ddb6dd7c28a9e019c81b4727f2f0ebcd664ca2f2318331d2de77' or business_exit.get('job_sha256')!=business['job_sha256'] or business_exit.get('exit')!=0 or business.get('phase')!='passed' or len(business.get('tests',[]))!=12 or not all(x['passed'] is True for x in business['tests']) or d['business_prerequisite_report_sha256']!=hashlib.sha256(business_path.read_bytes()).hexdigest():raise RuntimeError('own versioned business chain differs')
     overhead_path=pathlib.Path('/var/tmp/crg-overhead-r63-20261111/report.json');overhead=json.loads(overhead_path.read_text());overhead_exit=json.loads(pathlib.Path('/var/tmp/crg-r63-20261111/overhead.exit.json').read_text())
     if overhead.get('job_sha256')!='e8937b2df8bff4bf6d2e2c7987c8de78cb2435e6d69539d3ebf9ebb5c7d12aa6' or overhead_exit.get('job_sha256')!=overhead['job_sha256'] or overhead_exit.get('exit')!=0 or overhead.get('phase')!='passed' or overhead.get('measurement_elapsed_seconds',0)<1800 or len(overhead.get('cases',{}))!=3 or not all(x['passed'] is True for x in overhead['cases'].values()) or not (d['overhead_prerequisite_report_sha256']==business['overhead_report_sha256']==hashlib.sha256(overhead_path.read_bytes()).hexdigest()):raise RuntimeError('own versioned overhead chain differs')
     overhead_namespace=run(['kubectl','get','namespace','crg-overhead-r63-20261111','--ignore-not-found','-o','json'],False)
     if overhead_namespace.returncode or overhead_namespace.stdout.strip():raise RuntimeError('own overhead namespace present')
     absent=run(['kubectl','get','namespace','crg-vendor-lab-realpaths66-20261111','--ignore-not-found','-o','json'],False)
     if absent.returncode or absent.stdout.strip():raise RuntimeError('fault namespace independently not absent')
     report['fault_prerequisite_report_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();break
   time.sleep(5)
  else:raise RuntimeError('current fault prerequisite not completed; no maintenance Pod created')
  for path,namespace in [('/var/tmp/crg-realpaths64-20261111','crg-vendor-lab-realpaths64-20261111'),('/var/tmp/crg-realpaths54-20261111','crg-vendor-lab-realpaths54-20261111')]:
   p=pathlib.Path(path)/'report.json';d=json.loads(p.read_text())
   if d.get('phase')!='passed' or d.get('namespace_absent') is not True:raise RuntimeError('prior qualified business or maintenance not passed and cleaned')
   absent=run(['kubectl','get','namespace',namespace,'--ignore-not-found','-o','json'],False)
   if absent.returncode or absent.stdout.strip():raise RuntimeError('prior namespace independently not absent')
  (root/'tools').mkdir(mode=0o700)
  for name in ['vendor-soak-load.py','vendor-soak-campaign.py','vendor-engine-smoke.py']:shutil.copyfile(candidates/'tests'/name,root/'tools'/name)
  report['phase']='preparing';save()
  gates=root/'gates';gates.mkdir(mode=0o700)
  aux=root/'aux';aux.mkdir(mode=0o700);shutil.copyfile('/usr/bin/etcd',aux/'etcd');(aux/'etcd').chmod(0o755)
  if run(['kubectl','get','namespace',ns],False).returncode==0:raise RuntimeError('namespace already exists')
  create({'apiVersion':'v1','kind':'Namespace','metadata':{'name':ns,'labels':{'managed-by':'crg-vendor-test'}}});created=True
  create({'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'deny-all','namespace':ns},'spec':{'podSelector':{},'policyTypes':['Ingress','Egress']}})
  images=json.loads((source/'vendor-import.json').read_text())['images']
  for index,role in enumerate(['dbs','hisdbs']):
   pod_created=False;nativejob=None;log=None;item={'phase':'preparing'};report['roles'][role]=item;save()
   try:
    available=reserve(28);folder=root/(role+'-business');folder.mkdir(mode=0o700)
    for n in ['postgresql','dbs','highgo','log','core','sql','hbp-runtime','resource-state','cache-state','etcd','ccg','crg','crg-config','recovery','staging']:(folder/n).mkdir(mode=0o700)
    for n in ['bin','scripts','config']:(folder/'ccg'/n).mkdir(mode=0o700)
    cachepath='/home/ccg-backups/dbs' if role=='dbs' else '/opt/PUC-784/ccg-backups/hisdbs'
    shutil.copyfile(source/'fixture'/role/'supervisor.sh',folder/'ccg/scripts/business-supervisor.sh')
    shutil.copyfile(source/'fixture/containercacheguard',folder/'ccg/bin/containercacheguard');(folder/'ccg/bin/containercacheguard').chmod(0o755)
    oldbin=candidates/'binaries/previous';newbin=candidates/'binaries/candidate'
    oldsha=hashlib.sha256(oldbin.read_bytes()).hexdigest();newsha=hashlib.sha256(newbin.read_bytes()).hexdigest()
    if oldsha!='f07973272313db26d359797dda4665145f7dd6490bac2a55f9084bd367faf361' or newsha!='dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8':raise RuntimeError('source-qualified test binary digest mismatch')
    shutil.copyfile(newbin,folder/'crg/crg');(folder/'crg/crg').chmod(0o755)
    shutil.copyfile(newbin,folder/'staging/crg');(folder/'staging/crg').chmod(0o755)
    shutil.copyfile(candidates/'examples/optional-agent.sh',folder/'crg/optional-agent.sh')
    cache=json.loads((source/'fixture'/role/'cache.json').read_text());cache['state_file']=cachepath+'/status.json';(folder/('ccg/config/'+role+'.json')).write_text(json.dumps(cache))
    (folder/'crg-config/config.json').write_text(json.dumps({'resource_mode':'manual','limits':{'cpu_cores':7.2,'memory_max':'20001980416B','io_read_bps':'64MiB','io_write_bps':'64MiB','io_read_iops':4096,'io_write_iops':4096},'data_paths':['/opt/postgresql']}))
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
    start='i=0; while [ ! -f "/network-gates/$CRG_TEST_POD_UID" ]; do i=$((i+1)); [ "$i" -lt 120 ] || exit 92; sleep 1; done; exec /bin/bash /opt/ccg/scripts/business-supervisor.sh'
    envs=[{'name':k,'value':v} for k,v in env.items()]+[{'name':'CRG_TEST_POD_UID','valueFrom':{'fieldRef':{'fieldPath':'metadata.uid'}}}]
    pod={'apiVersion':'v1','kind':'Pod','metadata':{'name':role+'-business','namespace':ns,'labels':{'managed-by':'crg-vendor-test'}},'spec':{'automountServiceAccountToken':False,'enableServiceLinks':False,'restartPolicy':'Never','terminationGracePeriodSeconds':30,'containers':[{'name':role,'image':images[role]['tag'],'imagePullPolicy':'Never','command':['/bin/bash','-c',start],'env':envs,'securityContext':{'privileged':True},'resources':{'requests':{'cpu':'100m','memory':'256Mi'},'limits':{'cpu':'8','memory':'20Gi'}},'volumeMounts':mounts},{'name':'isolated-dcs','image':images[role]['tag'],'imagePullPolicy':'Never','command':['/aux/etcd','--name','isolated','--data-dir','/isolated-etcd','--listen-client-urls','http://127.0.0.1:2379','--advertise-client-urls','http://127.0.0.1:2379','--listen-peer-urls','http://127.0.0.1:2380','--initial-advertise-peer-urls','http://127.0.0.1:2380','--initial-cluster','isolated=http://127.0.0.1:2380'],'resources':{'requests':{'cpu':'10m','memory':'32Mi'},'limits':{'cpu':'1','memory':'256Mi'}},'volumeMounts':[{'name':'aux','mountPath':'/aux','readOnly':True},{'name':'etcd','mountPath':'/isolated-etcd'}]}],'volumes':vols}}
    private=folder/'pod.json';private.write_text(json.dumps(pod));private.chmod(0o600);create(pod);pod_created=True
    run(['kubectl','wait','-n',ns,'--for=condition=Ready','pod/'+role+'-business','--timeout=90s'],timeout=100)
    meta=json.loads(run(['kubectl','get','pod','-n',ns,role+'-business','-o','json']).stdout);cid=next(x['containerID'].split('://')[1] for x in meta['status']['containerStatuses'] if x['name']==role)
    pid=json.loads(run(['crictl','inspect',cid]).stdout)['info']['pid'];run(['nsenter','-t',str(pid),'-n','--','ip','link','set','dev','eth0','down'])
    if 'state DOWN' not in run(['nsenter','-t',str(pid),'-n','--','ip','-o','link','show','dev','eth0']).stdout:raise RuntimeError('network gate not isolated')
    started=time.monotonic();(gates/meta['metadata']['uid']).write_text('isolated\n');item={'phase':'booting','resource_mode':'manual','candidate_branch':'actual-published-assets-controlled-migration','memory_reserve_before_bytes':available,'original_start_script_unmodified':True,'same_container_mount_paths':True,'original_ccg_readonly':True};report['roles'][role]=item;report['phase']='testing-'+role;save()
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
    record(role+'-real-path-original-startup-manual-accepted-budget',state['state']=='managed' and state.get('automatic_io') is None and not (folder/'crg-config/io-profile.json').exists())
    mountinfo=ex(role,'findmnt','-n','-o','OPTIONS','/opt/ccg').stdout.strip();record(role+'-original-CCG-mount-stays-readonly','ro' in mountinfo.split(','))
    cachefile=folder/'cache-state/status.json';cache_started=time.monotonic();cache_deadline=min(started+300,cache_started+45)
    while time.monotonic()<cache_deadline:
     if cachefile.exists() and json.loads(cachefile.read_text()).get('action')=='enforce':break
     time.sleep(min(1,max(0,cache_deadline-time.monotonic())))
    item['cache_enforce_observation_seconds']=time.monotonic()-cache_started
    record(role+'-original-cache-independent-enforce',cachefile.exists() and json.loads(cachefile.read_text()).get('action')=='enforce' and time.monotonic()<=started+300)
    import importlib.util
    activity_path=pathlib.Path('/var/tmp/crg-agent-activity418-tools-20261111/vendor-agent-activity-session.py')
    spec=importlib.util.spec_from_file_location('agent_activity',activity_path);activity=importlib.util.module_from_spec(spec);spec.loader.exec_module(activity)
    if hashlib.sha256(activity_path.read_bytes()).hexdigest()!=frozen_plan['activity_source_sha256']:raise RuntimeError('activity tool changed')
    cg=pathlib.Path('/sys/fs/cgroup')/next(x.split('::',1)[1].lstrip('/') for x in pathlib.Path('/proc/%s/cgroup'%pid).read_text().splitlines() if x.startswith('0::'))
    if cg.name!='cri-containerd-'+cid+'.scope':raise RuntimeError('target is not own container leaf')
    controls={f:(cg/f).read_text() for f in activity.CONTROLS}
    pid1=activity.fields(pid)['start_ticks'];oom=int(dict(x.split() for x in (cg/'memory.events').read_text().splitlines())['oom_kill'])
    def agents():
     result=[]
     for value in (cg/'cgroup.procs').read_text().splitlines():
      try:
       p=pathlib.Path('/proc')/value;argv=p.joinpath('cmdline').read_bytes().rstrip(b'\0').split(b'\0')
       if argv==[b'/opt/crg/crg',b'run',b'--config',b'/etc/crg/config.json']:
        if hashlib.sha256(p.joinpath('exe').read_bytes()).hexdigest()!=newsha:raise RuntimeError('actual Agent hash differs')
        result.append(int(value))
      except (FileNotFoundError,ProcessLookupError):pass
     return result
    found=agents()
    if len(found)!=1:raise RuntimeError('single actual Agent required')
    agent=found[0];ticks=activity.fields(agent)['start_ticks'];helper=activity.fields(agent)['ppid'];helper_ticks=activity.fields(helper)['start_ticks']
    cache=[]
    for value in (cg/'cgroup.procs').read_text().splitlines():
     try:
      p=pathlib.Path('/proc')/value;argv=p.joinpath('cmdline').read_bytes().split(b'\0')
      if pathlib.Path(os.fsdecode(argv[0])).name=='containercacheguard':
       if hashlib.sha256(p.joinpath('exe').read_bytes()).hexdigest()!='757ba385a0ee4bdadc968b96b5c3e69fd44353060e5ab28520fd6f73a59902de':raise RuntimeError('cache changed')
       cache.append((int(value),activity.fields(int(value))['start_ticks']))
     except (FileNotFoundError,ProcessLookupError):pass
    if len(cache)!=1:raise RuntimeError('single original cache required')
    owner={'schema':'crg-agent-activity-owner-v1','kind':'vendor-container','nonce':uuid.uuid4().hex,'namespace':ns,
      'pod_uid':meta['metadata']['uid'],'container_id':cid,'container_pid':pid,'container_start_ticks':pid1}
    ownerfile=root/'agent-activity-owner.json';ownerfile.write_text(json.dumps(owner));ownerfile.chmod(0o600)
    marker={'fixture_root':str(root),'nonce':owner['nonce'],'namespace':ns}
    (folder/'crg-config/agent-activity-fixture.json').write_text(json.dumps(marker))
    plan={key:owner[key] for key in ['kind','nonce','pod_uid','container_id','container_pid','container_start_ticks']}
    plan.update(fixture_root=str(root),pid=agent,start_ticks=ticks,argv=['/opt/crg/crg','run','--config','/etc/crg/config.json'],binary_sha256=newsha,cgroup=str(cg))
    item.update(activity_plan=plan,actual_controls=controls,helper={'pid':helper,'start_ticks':helper_ticks},cache=cache,activity_records={});save()
    journal=folder/'resource-state/journal.json'
    def journal_identity():
     data=json.loads(journal.read_text())
     return {k:data[k] for k in ['version','identity','target','mutations']}
    original_journal=journal_identity()
    def sql_start():
     q=ex(role,'env','PGCONNECT_TIMEOUT=4','/opt/postgresql/pgsql/bin/psql','-h','127.0.0.1','-U','postgres','-d','postgres','-X','-A','-t','-c','select pg_postmaster_start_time()',timeout=10)
     value=q.stdout.strip()
     if not value:raise RuntimeError('PG start unavailable')
     return value
    pg_started=sql_start();item['PG_start_time']=pg_started
    def invariant():
     return agents()==[agent] and activity.fields(agent)['start_ticks']==ticks and activity.fields(pid)['start_ticks']==pid1 and activity.fields(pid)['state'] not in ['T','t'] and activity.fields(helper)['start_ticks']==helper_ticks and activity.fields(helper)['state'] not in ['T','t'] and all(activity.fields(p)['start_ticks']==s and activity.fields(p)['state'] not in ['T','t'] for p,s in cache) and {f:(cg/f).read_text() for f in controls}==controls and journal_identity()==original_journal and int(dict(x.split() for x in (cg/'memory.events').read_text().splitlines())['oom_kill'])==oom
    def probes():
     q=ex(role,'python','-c',api,check=False,timeout=10)
     return q.returncode==0 and sql_start()==pg_started and invariant()
    record(role+'-owned-exact-Agent-and-original-business-identities',activity.identity(plan)['start_ticks']==ticks and probes())
    import copy
    bad=[('pid1',{'pid':pid}),('self',{'pid':os.getpid()}),('stale-ticks',{'start_ticks':ticks+1}),('wrong-exe',{'binary_sha256':'0'*64}),('wrong-cgroup',{'cgroup':str(cg)+'/wrong'}),('wrong-argv',{'argv':plan['argv']+['wrong']}),('wrong-nonce',{'nonce':'0'*32})]
    for label,patch in bad:
     candidate=copy.deepcopy(plan);candidate.update(patch);row={};reason=None
     try:
      with activity.Session(candidate,role+'-'+label,row,pause=True,lease=60):raise RuntimeError('unsafe target accepted')
     except (activity.Rejected,FileNotFoundError,ProcessLookupError) as error:reason=str(error) if isinstance(error,activity.Rejected) else type(error).__name__
     item['activity_records'][label]=row
     record(role+'-reject-'+label,reason is not None and row['STOP_count']==row['CONT_count']==0 and activity.fields(agent)['state'] not in ['T','t'] and invariant(),reason=reason)
    row={};item['activity_records']['active']=row
    with activity.Session(plan,role+'-active',row,lease=60) as session:
     sample=session.inspect();record(role+'-active-session-no-signals-business-preserved',not sample['all_threads_stopped'] and sample['control_values_preserved'] and probes())
    if row['STOP_count'] or row['CONT_count'] or row['watchdog_exit'] or row['watchdog']['CONT_count']:raise RuntimeError('active lifecycle differs')
    row={};item['activity_records']['paused']=row
    with activity.Session(plan,role+'-paused',row,pause=True,lease=60) as session:
     first=session.inspect();okay=probes();time.sleep(1);last=session.inspect()
     item['paused_samples']=[first,last]
     record(role+'-only-Agent-paused-kernel-and-business-preserved',okay and probes() and first['all_threads_stopped'] and last['all_threads_stopped'] and first['control_values_preserved'] and last['control_values_preserved'] and first['user_ticks']==last['user_ticks'] and first['system_ticks']==last['system_ticks'])
    record(role+'-normal-resume-same-instance-watchdog-reaped',row['STOP_count']==row['CONT_count']==1 and row['resumed_same_instance'] and row['watchdog_exit']==0 and row['watchdog']['CONT_count']==0 and probes())
    class Sentinel(Exception):pass
    row={};item['activity_records']['exception']=row;observed=False
    try:
     with activity.Session(plan,role+'-exception',row,pause=True,lease=60):
      if not probes():raise RuntimeError('business changed in exception case')
      raise Sentinel('original-body-error')
    except Sentinel as error:observed=str(error)=='original-body-error'
    record(role+'-exception-resumes-original-Agent-and-preserves-body-error',observed and row['STOP_count']==row['CONT_count']==1 and row['resumed_same_instance'] and row['watchdog_exit']==0 and row['watchdog']['CONT_count']==0 and probes())
    disabled=json.loads(ex(role,'/opt/crg/crg','disable','--config','/etc/crg/config.json',timeout=45).stdout)
    expected=dict(controls,**{'cpu.max':'800000 100000\n','memory.max':'21474836480\n','io.max':''})
    item['final_actual_controls']={f:(cg/f).read_text() for f in controls};save()
    record(role+'-final-disable-restores-runtime-and-retains-original-business',disabled['state']=='restored' and item['final_actual_controls']==expected and activity.fields(pid)['start_ticks']==pid1 and sql_start()==pg_started and ex(role,'python','-c',api,check=False,timeout=10).returncode==0 and all(activity.fields(p)['start_ticks']==s for p,s in cache))
    item['phase']='short-qualification-passed';save()
   except Exception as error:item.update(phase='failed',error=str(error),traceback=traceback.format_exc());save()
   finally:
    if pod_created:delete_pod(role);item['own_pod_removed']=True
    if nativejob is not None:
     try:nativejob.wait(timeout=20)
     except subprocess.TimeoutExpired:nativejob.terminate();nativejob.wait(timeout=15)
    if log is not None:log.close()
    save()
  report['phase']='passed' if all(v['phase']=='short-qualification-passed' for v in report['roles'].values()) else 'failed'
 except BaseException as e:report.update(phase='failed',error=str(e),traceback=traceback.format_exc())
 finally:
  if created:
   m=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout)
   if m['metadata']['labels'].get('managed-by')!='crg-vendor-test':raise RuntimeError('namespace cleanup ownership mismatch')
   run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=150s'],False,160);absent=run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json'],False);report['namespace_absent']=absent.returncode==0 and not absent.stdout.strip()
  if root.exists():save()
 print(json.dumps({'phase':report['phase'],'checks':len(report['tests']),'error':report.get('error')}))

 raise SystemExit(0 if report['phase']=='passed' and report.get('namespace_absent') is True and len(report['roles'])==2 and len(report['tests'])==32 and all(x['passed'] for x in report['tests']) else 1)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=pathlib.Path);p.add_argument('--plan-sha256');p.add_argument('--execute',action='store_true');args=p.parse_args()
 if args.plan is None:
  print(json.dumps({'phase':'inert','executed':False,'stable_release_accepted':False}));return 0
 try:
  if sys.platform!='linux' or os.geteuid()!=0:raise ValueError('LINUX_ROOT_REQUIRED')
  raw=args.plan.read_bytes();expected=dict(FROZEN_PLAN,executor_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest())
  if hashlib.sha256(raw).hexdigest()!=args.plan_sha256 or json.loads(raw)!=expected:raise ValueError('FROZEN_PLAN_MISMATCH')
  if os.path.lexists(expected['work_root']):raise ValueError('FRESH_TARGET_REQUIRED')
  q=subprocess.run(['kubectl','get','namespace',expected['namespace'],'--ignore-not-found','-o','json'],capture_output=True,text=True,timeout=15)
  if q.returncode or q.stdout.strip():raise ValueError('FRESH_NAMESPACE_REQUIRED')
  tool=pathlib.Path(expected['tool_root'])/'vendor-agent-activity-session.py'
  if tool.is_symlink() or hashlib.sha256(tool.read_bytes()).hexdigest()!=expected['activity_source_sha256']:raise ValueError('FROZEN_ACTIVITY_TOOL')
  host=json.loads(pathlib.Path('/var/tmp/crg-agent-activity415-20261111/report.json').read_bytes())
  if host['phase']!='passed' or len(host['tests'])!=27 or not all(v['passed'] for v in host['tests']) or host['source_sha256']!=expected['host_qualification_tool_sha256'] or host.get('cleanup_errors'):raise ValueError('HOST_QUALIFICATION_REQUIRED')
  if not args.execute:
   print(json.dumps({'phase':'ready','executed':False,'expected_checks':32,'stable_release_accepted':False}));return 0
  if os.environ.get('CRG_AGENT_ACTIVITY')!='authorized-disposable-test-node-only':raise ValueError('EXPLICIT_LAB_MARKER_REQUIRED')
  os.umask(0o077)
  def interrupted(signum,frame):raise KeyboardInterrupt()
  signal.signal(signal.SIGTERM,interrupted)
  run_qualification(expected,args.plan_sha256)
 except Exception as error:
  print(json.dumps({'phase':'rejected','reason':str(error) if isinstance(error,ValueError) else type(error).__name__,'executed':False,'stable_release_accepted':False}));return 1
if __name__=='__main__':raise SystemExit(main())
