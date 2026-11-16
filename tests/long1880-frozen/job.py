"""Disposable acceptance coordinator; never a product agent."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,os,pathlib,re,shutil,signal,subprocess,sys,time,traceback,uuid
candidates=Path('/var/tmp/crg-final1880-tools-20261116');plan_raw=(candidates/'plan.json').read_bytes();plan=json.loads(plan_raw)
root=Path(plan['output']);source=Path('/var/tmp/crg-business-20261110');ns=plan['namespace'];created=False;namespace_uid=None;campaign_job=None
sha=lambda raw:hashlib.sha256(raw).hexdigest()
report={'schema':'crg-final-24h-24h-seven-day-v1','phase':'not-started','sources':{'candidate1':{'revision':plan['source_revision'],'binary_sha256':plan['binary_sha256']}},'version':'v1.0.0','job_sha256':plan['job_sha256'],'plan_sha256':sha(plan_raw),'namespace':ns,'roles':{},'tests':[],'phases':{},'stable_release_accepted':False,'runtime_inherited':False}

probe_path=candidates/'tests/coordinator-probe-v1/probe.py'
probe_spec=importlib.util.spec_from_file_location('frozen_coordinator_probe',probe_path)
probe=importlib.util.module_from_spec(probe_spec);probe_spec.loader.exec_module(probe)
receipts=candidates/'private-command-receipts'

def run(a,check=True,timeout=60,**kw):
 return probe.recorded_run(a,receipts,check=check,timeout=timeout,**kw)
def create(o):
 # One mutation attempt; never retry create/delete/exec/nsenter automatically.
 return run(['kubectl','create','-f','-'],input=json.dumps(o),timeout=30)
def ex(role,*a,**kw):return run(['kubectl','exec','-n',ns,role+'-business','-c',role,'--',*a],**kw)
def save():
 raw=(json.dumps(report,indent=2)+'\n').encode();p=root/'report.candidate';p.write_bytes(raw);p.chmod(0o600);p.replace(root/'report.json')
def record(name,passed,**extra):
 report['tests'].append(dict(name=name,passed=bool(passed),**extra));save()
 if not passed:raise AssertionError(name)
def reserve(minimum=8):
 available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 if available<minimum*1024**3 or shutil.disk_usage('/var/tmp').free<20*1024**3:raise RuntimeError('node reserve threshold reached')
 return available
def absent(v):
 try:return int(Path('/proc',str(v['pid']),'stat').read_bytes().rsplit(b')',1)[1].split()[19])!=v['start_ticks']
 except (FileNotFoundError,ProcessLookupError):return True
def controls(group):return {n:(group/n).read_text().strip() for n in plan['control_files']}
def identity(pid):
 p=Path('/proc',str(pid));fields=(p/'stat').read_bytes().rsplit(b')',1)[1].split();return {'pid':int(pid),'start_ticks':int(fields[19])}
def exclusive():
 blocked,observation=probe.exclusive(ns,receipts,budget_seconds=15,max_attempts=3)
 report['last_exclusivity_observation']=observation
 if root.exists():save()
 return blocked
def admission():
 assert os.geteuid()==0 and os.uname().machine=='x86_64' and hasattr(os,'pidfd_open') and os.environ.get('CRG_FINAL1880_LONG')=='authorized-disposable-test-node-only'
 assert root==Path('/var/tmp/crg-final1880-results-20261116') and ns=='crg-vendor-lab-final1880-20261116' and not root.exists()
 assert sha(Path(__file__).read_bytes())==plan['job_sha256']
 for name,h in plan['source_sha256'].items():assert sha((candidates/name).read_bytes())==h,name
 for name,h in plan['private_fixture_sha256'].items():assert sha((source/name).read_bytes())==h,name
 info=json.loads(run([str(candidates/'binaries/crg-linux-amd64'),'build-info']).stdout)
 assert info['version']=='v1.0.0' and info['revision']==plan['source_revision'] and info['arch']=='amd64' and info['memory_policy'].startswith('high-reclaim-throttle') and info['io_percent_policy']=='calibrated-read-write-bandwidth; IOPS manual only; external IOPS retained'
 q=json.loads((candidates/'business-qualification.json').read_bytes());ci=json.loads((candidates/'CI-qualification.json').read_bytes());assert q['phase']=='passed' and q['passed_checks']==18 and q['source_commit']==plan['source_revision'] and ci['phase']=='passed' and ci['actual_total_checks']==284 and ci['source_revision']==plan['source_revision'] and ci['all_actual_controller_programs_match_frozen_final_ELFs']
 previous=plan['business_prerequisite'];raw=(Path(previous['output'])/'report.json').read_bytes();assert sha(raw)==q['coordinator_report_sha256']==previous['report_sha256'];old=json.loads(raw);assert old['phase']=='passed' and json.loads((Path(previous['tools'])/'exit.json').read_bytes())['exit']==0 and absent(json.loads((Path(previous['tools'])/'launch.json').read_bytes()))
 for row in old['roles'].values():
  assert row['phase']=='passed' and absent(row['driver'])
  for clean in row['cleanup']:
   v=clean['identity'];assert not Path(v['group']).exists() and not Path(v['pod_parent']).exists() and all(absent(p) for p in v['processes']+clean['additional_processes'])
 oldtools=Path('/var/tmp/crg-final1396-tools-20261115');oldraw=Path('/var/tmp/crg-final1396-results-20261115/report.json').read_bytes()
 assert sha(oldraw)=='03a11a35b1a6aaa371c85107c7e9e97e4500ed0228aca23bbcd059f3a096e287';oldterminal=json.loads(oldraw)
 assert oldterminal['phase']=='failed' and oldterminal['namespace_absent'] and not oldterminal.get('cleanup_errors')
 oldexit=json.loads((oldtools/'exit.json').read_bytes());assert oldexit['exit']==1 and oldexit['job_sha256']=='4b2789bca4a30bbf0e2181f74422825a31896384fe6e6f546c2ea240a1a759ac' and oldexit['plan_sha256']=='9018ae5400591afd4ce04b5fd379be59e892172cb193cf5a06fe9995d5d800a4'
 for name in ['launch.json','worker.json','observer-launch.json']:assert absent(json.loads((oldtools/name).read_bytes()))
 for key,row in oldterminal['roles'].items():
  assert not Path(row['fixture_identity']['group']).exists() and not Path(row['fixture_identity']['pod_parent']).exists()
  assert all(absent(p) for p in oldterminal['cleanup'][key]['registered_processes'])
 assert not run(['kubectl','get','namespace',oldterminal['namespace'],'--ignore-not-found','-o','json','--request-timeout=5s'],timeout=10).stdout.strip()
 oldtools=Path('/var/tmp/crg-final1728-tools-20261116');oldraw=Path('/var/tmp/crg-final1728-results-20261116/report.json').read_bytes();assert sha(oldraw)=='7adb3ba40455282f546aa90f727f1a13476f097f989f2f786a761f76bc40c733';oldterminal=json.loads(oldraw)
 assert oldterminal['phase']=='failed' and oldterminal['error']=='explicit long-test stop requested' and oldterminal['namespace_absent'] and not oldterminal.get('cleanup_errors')
 oldplan=json.loads((oldtools/'plan.json').read_bytes());assert sha((oldtools/'plan.json').read_bytes())=='ea19e85c8e8690845449ce36b9e3be8266282015cb8e8ba8ed6eec207187370c' and all(sha((oldtools/n).read_bytes())==h for n,h in oldplan['source_sha256'].items())
 assert json.loads((oldtools/'exit.json').read_bytes())['exit']==1
 for name in ['launch.json','worker.json','observer-launch.json']:assert absent(json.loads((oldtools/name).read_bytes()))
 for role,row in oldterminal['roles'].items():
  assert not Path(row['fixture_identity']['group']).exists() and not Path(row['fixture_identity']['pod_parent']).exists() and all(absent(p) for p in oldterminal['cleanup'][role]['registered_processes'])
 assert not run(['kubectl','get','namespace',oldterminal['namespace'],'--ignore-not-found','-o','json','--request-timeout=5s'],timeout=10).stdout.strip()
 assert q['auxiliary_checks_passed']==4 and q['native_whole600_each_role'] and q['all22_and_cleanup_qualified'] and q['original_check_names_equal_previously_frozen9_each_role']
 assert q['independent_qualification_sha256']==sha((candidates/'formal18-independent.json').read_bytes())
 available=reserve(28);blocked=exclusive();assert not json.loads(run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json','--request-timeout=5s'],timeout=10).stdout or '{}')
 return {'phase':'ready' if not blocked else 'waiting-existing-fixtures','node_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'build_info':info,'all_frozen_inputs_verified':len(plan['source_sha256']),'business18_and_native284_verified':True,'available_memory_bytes':available,'free_disk_bytes':shutil.disk_usage('/var/tmp').free,'blocking_pods':blocked,'business_fixture_created':False,'long_measurement_started':False}
def processes(row):
 group=Path(row['fixture_identity']['group']);return [identity(v) for v in (group/'cgroup.procs').read_text().split() if Path('/proc',v).exists()]
def guard_snapshot(row,expected):
 group=Path(row['fixture_identity']['group']);fixed=row['fixed_processes'];assert all(not absent(v) for v in fixed.values())
 for v in fixed.values():assert next(x.split('::',1)[1].lstrip('/') for x in Path('/proc',str(v['pid']),'cgroup').read_text().splitlines() if x.startswith('0::'))==str(group.relative_to('/sys/fs/cgroup'))
 assert controls(group)==expected
 state=json.loads((root/'fixture'/(row['role']+'-business')/'resource-state/status.json').read_bytes());return {'fixed_processes':fixed,'controls':controls(group),'state':state['state'],'configuration':state.get('configuration'),'status_time':state.get('time_utc')}
def capture_before_phase():
 for row in report['roles'].values():
  row.setdefault('registered_processes',[]).extend(processes(row))
def run_campaign(stage):
 global campaign_job
 phase=stage['phase'];path=root/('campaign-'+phase);args=['python3',str(candidates/'campaign-wrapper.py'),'--namespace',ns,'--fixture-root',str(root/'fixture'),'--work-dir',str(path),'--run-id',stage['run_id'],'--test-phase',phase,'--seconds',str(stage['seconds']),'--agent-sha256',plan['binary_sha256'],'--cache-sha256',plan['private_fixture_sha256']['fixture/containercacheguard']]
 if stage.get('source_run_id'):args+=['--source-run-id',stage['source_run_id']]
 row={'phase':'starting','run_id':stage['run_id'],'requested_seconds':stage['seconds'],'source_run_id':stage.get('source_run_id'),'output':str(path),'native_accepted':False};report['phases'][phase]=row;report['phase']='measuring-'+phase;save();capture_before_phase()
 with (root/(phase+'-campaign.log')).open('xb') as log:
  campaign_job=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=log,stderr=log);row['campaign_identity']=dict(identity(campaign_job.pid),entry=str(candidates/'campaign-wrapper.py'));save();checked=0
  while campaign_job.poll() is None:
   reserve()
   if time.monotonic()-checked>=60:
    assert not exclusive(),'OTHER_DISPOSABLE_BUSINESS_FIXTURE_APPEARED';checked=time.monotonic()
   time.sleep(5)
 row['exit']=campaign_job.returncode;row['campaign_original_absent']=absent(row['campaign_identity']);raw=(path/'report.json').read_bytes();result=json.loads(raw);row.update(phase=result['phase'],report_sha256=sha(raw),actual_cycles=len(result['backups']),failure=result.get('failure'));save()
 # The unchanged, source-pinned auditor independently recomputes all original
 # native counters, criteria, identities, cycles and temporal containment.
 spec=importlib.util.spec_from_file_location('frozen_soak_auditor',candidates/'tests/soak-report-audit.py');auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor);audit=auditor.audit(result,phase,plan['campaign_pins'],stage.get('source_run_id'));row['audit']=audit
 assert campaign_job.returncode==0 and row['campaign_original_absent'] and audit['phase']=='passed' and audit['continuous_report_accepted'] and audit['accepted_engine_cycles']==stage['cycles'];row['native_accepted']=True
 for role,value in result['roles'].items():
  native=value['workload'];row.setdefault('native',{})[role]={k:native[k] for k in ['phase','elapsed_seconds','sql','api','initial_checksum','final_checksum','primary_start_time_initial','primary_start_time_final']}
  registered=report['roles']['candidate1-'+role+'-bw64']['registered_processes']
  for engine in sorted(path.glob('backup-*/business-backup.json')):
   er=json.loads(engine.read_bytes())['roles'][role]
   for event in er.get('port_diagnostics',[]):
    for listener in event.get('sample',{}).get('listeners',[]):
     registered.extend({k:p[k] for k in ['pid','start_ticks']} for p in listener['owners'] if p['same_cgroup'])
 record(phase+'-both-native-full-duration-and-all-cycles',True,requested_seconds=stage['seconds'],accepted_cycles=stage['cycles']);save()
def switch_enforce():
 baseline=report['phases']['baseline'];assert baseline['native_accepted'] and baseline['audit']['requested_seconds']==86400
 # Keep both actual baseline output and same container workload lineage. No
 # business or guard process restart, quota relaxation or fixture data reset.
 for row in report['roles'].values():
  role=row['role'];folder=root/'fixture'/(role+'-business');before=guard_snapshot(row,row['original_controls']);raw=plan['enforce_configuration_exact_utf8'].encode();config=folder/'crg-config/config.json';assert config.read_bytes()==plan['baseline_configuration_exact_utf8'].encode();(folder/'baseline-config-preserved.json').write_bytes(config.read_bytes())
  temporary=folder/'crg-config/config.candidate'
  with temporary.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
  temporary.chmod(0o600);temporary.replace(config);fd=os.open(str(config.parent),os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(fd)
  finally:os.close(fd)
  ack=json.loads(ex(role,'/opt/crg/crg','reload','--config','/etc/crg/config.json').stdout);assert ack['state']=='requested';deadline=time.monotonic()+300
  while time.monotonic()<deadline:
   reserve();state=json.loads((folder/'resource-state/status.json').read_bytes())
   if state.get('mode')=='enforce' and state.get('state')=='managed' and len(state.get('items',[]))==3 and all(v['state']=='applied' for v in state['items']):break
   time.sleep(3)
  else:raise RuntimeError('baseline-to-enforce did not reach exact fixed budget within300s')
  group=Path(row['fixture_identity']['group']);journal=json.loads((folder/'resource-state/journal.json').read_bytes());assert controls(group)==row['enforce_controls'] and journal==row['enforce_journal'];after=guard_snapshot(row,row['enforce_controls']);row['enforce_transition']={'before':before,'after':after,'reload_ack':ack,'exact_journal':journal,'same_fixed_processes':before['fixed_processes']==after['fixed_processes']};save()
 record('same-container-and-guards-observe-to-enforce-exact-budget',True)
def cleanup():
 global campaign_job
 if campaign_job is not None and campaign_job.poll() is None:
  # Wrapper turns TERM into an exception and runs original campaign cleanup.
  campaign_job.terminate()
  try:campaign_job.wait(timeout=210)
  except subprocess.TimeoutExpired:report.setdefault('cleanup_errors',[]).append('campaign did not finish210s cleanup; own Pod deletion remains scoped')
 if created:
  meta=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout);assert meta['metadata']['uid']==namespace_uid and meta['metadata']['labels'].get('managed-by')=='crg-vendor-test'
  for row in report['roles'].values():
   if row.get('fixture_identity') and Path(row['fixture_identity']['group']).exists():row.setdefault('registered_processes',[]).extend(processes(row))
  save();r=run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=150s'],check=False,timeout=160);report['namespace_delete_exit']=r.returncode;report['namespace_absent']=not run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json']).stdout.strip()
  report['cleanup']={}
  for key,row in report['roles'].items():
   v=row.get('fixture_identity',{});registered=row.get('registered_processes',[])+v.get('processes',[]);report['cleanup'][key]={'leaf_absent':'group' in v and not Path(v['group']).exists(),'parent_absent':'pod_parent' in v and not Path(v['pod_parent']).exists(),'registered_processes':registered,'all_registered_absent':bool(registered) and all(absent(p) for p in registered)}
  if r.returncode or not report['namespace_absent'] or len(report['cleanup'])!=2 or not all(v['leaf_absent'] and v['parent_absent'] and v['all_registered_absent'] for v in report['cleanup'].values()):report.setdefault('cleanup_errors',[]).append('owned fixture cleanup incomplete')
 if report.get('cleanup_errors'):report['phase']='failed'

# create_business() is appended from the qualified original-image setup, with
# explicit archived adaptations to observe mode and exact candidate identity.

def create_business():
 global created,namespace_uid,item
 (root/'tools').mkdir(mode=0o700)
 for name in ['vendor-soak-load.py','vendor-soak-campaign.py','vendor-engine-smoke.py','vendor-port-diagnostics.py','port-owner-observer.py','own-pg-startup-log.py']:shutil.copyfile(candidates/'tests'/name,root/'tools'/name)
 report['phase']='preparing';save()
 gates=root/'gates';gates.mkdir(mode=0o700)
 aux=root/'aux';aux.mkdir(mode=0o700);shutil.copyfile('/usr/bin/etcd',aux/'etcd');(aux/'etcd').chmod(0o755)
 if run(['kubectl','get','namespace',ns],False).returncode==0:raise RuntimeError('namespace already exists')
 create({'apiVersion':'v1','kind':'Namespace','metadata':{'name':ns,'labels':{'managed-by':'crg-vendor-test'}}});created=True;namespace_uid=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout)['metadata']['uid'];report['namespace_uid']=namespace_uid;save()
 create({'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'deny-all','namespace':ns},'spec':{'podSelector':{},'policyTypes':['Ingress','Egress']}})
 images=json.loads((source/'vendor-import.json').read_text())['images']
 for index,(candidate,role,bandwidth) in enumerate([('candidate1','dbs',64),('candidate1','hisdbs',64)]):
  key=candidate+'-'+role+'-bw'+str(bandwidth);pod_created=False;campaign_job=None;item={'phase':'preparing','candidate_branch':candidate,'role':role,'declared_read_write_bps':bandwidth*1024**2};report['roles'][key]=item;save()
  try:
   available=reserve(28);case_root=root/'fixture';case_root.mkdir(mode=0o700,exist_ok=True);folder=case_root/(role+'-business');folder.mkdir(mode=0o700)
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
   (folder/'crg-config/config.json').write_text(plan['baseline_configuration_exact_utf8'])
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
   actual_image=next(v['imageID'] for v in meta['status']['containerStatuses'] if v['name']==role);assert actual_image.rsplit('sha256:',1)[-1]==plan['expected_original_image_sha256'][role]
   assert meta['metadata']['namespace']==ns and meta['metadata']['labels'].get('managed-by')=='crg-vendor-test' and not any(meta['spec'].get(k,False) for k in ['hostNetwork','hostPID','hostIPC'])
   assert pid>1 and all(Path('/proc',str(pid),'ns',kind).stat().st_ino!=Path('/proc/1/ns',kind).stat().st_ino for kind in ['net','pid','mnt'])
   extra_files=['pids.max','cpu.weight','io.weight','memory.max','memory.swap.max'];extra_original={f:(group/f).read_text().strip() for f in extra_files}
   run(['nsenter','-t',str(pid),'-n','--','ip','link','set','dev','eth0','down'])
   if 'state DOWN' not in run(['nsenter','-t',str(pid),'-n','--','ip','-o','link','show','dev','eth0']).stdout:raise RuntimeError('network gate not isolated')
   initial={f:(group/f).read_text().strip() for f in ['cpu.max','memory.max','io.max','pids.max','cpu.weight','io.weight','memory.high','memory.swap.max']}
   doctor=json.loads(ex(role,'/opt/crg/crg','doctor','--config','/etc/crg/config.json').stdout)
   envinfo=doctor['environment'];settings=doctor['settings']
   if envinfo['cgroup']!=str(group) or envinfo.get('cgroup_version')!='v2' or doctor.get('memory_policy')!='high-reclaim-throttle' or doctor.get('warnings') or len(settings)!=3 or {x['file'] for x in settings}!={'cpu.max','memory.high','io.max'}:raise RuntimeError('pre-gate own high doctor plan differs')
   if initial['cpu.max']!='800000 100000' or initial['memory.max']!='21474836480' or initial['memory.high']!='max' or initial['io.max']!='':raise RuntimeError('pre-gate original runtime differs')
   wanted=dict(initial);mutations={}
   for setting in settings:
    file=setting['file'];value=setting['value'];device=setting.get('device','');mutation=dict(setting)
    if file=='cpu.max' and value!='720000 100000' or file=='memory.high' and value!='20001980416' or file=='io.max' and (value!='rbps=67108864 wbps=67108864 riops=4096 wiops=4096' or not re.fullmatch('[0-9]+:[0-9]+',device) or not re.fullmatch('[0-9a-f]{64}',setting.get('device_identity',''))):raise RuntimeError('pre-gate manual budget differs')
    wanted[file]=(device+' ' if file=='io.max' else '')+value
    mutation.update(original='rbps=max wbps=max riops=max wiops=max' if file=='io.max' else initial[file],applied=value);mutations[file+':'+device]=mutation
   expected_journal={'version':1,'identity':envinfo['identity'],'target':str(group),'mutations':mutations}
   fixture_identity={'pod_uid':meta['metadata']['uid'],'container_id':cid,'init_pid':pid,'init_start_ticks':identity(pid)['start_ticks'],'group':str(group),'pod_parent':str(group.parent),'processes':[]}
   started=time.monotonic();(gates/meta['metadata']['uid']).write_text('isolated\n');item={'phase':'booting','resource_mode':'manual','candidate_branch':candidate,'memory_reserve_before_bytes':available,'declared_read_write_bps':bandwidth*1024**2,'original_start_script_unmodified':True,'same_container_mount_paths':True,'original_ccg_readonly':True};report['roles'][key]=item;report['phase']='testing-'+key;save()
   item.update(fixture_identity=fixture_identity,original_controls=initial,predeclared_controls=initial,enforce_controls=wanted,enforce_journal=expected_journal,role=role,original_image_id=actual_image);save()
   deadline=time.monotonic()+300
   while time.monotonic()<deadline:
    reserve()
    try:
     q=ex(role,'su','-','postgres','-c','/opt/postgresql/pgsql/bin/pg_isready -h 127.0.0.1 -p 5432 -t 2',check=False,timeout=max(0.01,min(15,deadline-time.monotonic())))
     item['last_readiness_probe']={'exit':q.returncode,'output':(q.stdout+q.stderr)[-1500:]};save()
     status=folder/'resource-state/status.json'
     if q.returncode==0 and status.exists() and json.loads(status.read_text()).get('state')=='observe' and time.monotonic()<deadline:
      api="import urllib2,json; r=urllib2.urlopen(urllib2.Request('http://127.0.0.1:8090/test',data='{}',headers={'Content-Type':'application/json'}),timeout=3); assert r.getcode()==200; assert json.loads(r.read(1024))['Result']=='000'"
      a=ex(role,'python','-c',api,check=False,timeout=max(0.01,min(10,deadline-time.monotonic())))
      item['last_api_probe']={'exit':a.returncode};save()
      if a.returncode==0 and time.monotonic()<deadline:break
    except subprocess.TimeoutExpired:
     item['readiness_observation_timeouts']=item.get('readiness_observation_timeouts',0)+1;save()
    time.sleep(max(0,min(3,deadline-time.monotonic())))
   else:raise RuntimeError(role+' original PG/API readiness/observe budget not met within declared 300s')
   item['ready_and_managed_seconds']=time.monotonic()-started;state=json.loads(status.read_text());item['automatic_io']=state.get('automatic_io');save()
   record(key+'-real-path-original-startup-observe-without-resource-writes',state['state']=='observe' and state.get('automatic_io') is None and not (folder/'crg-config/io-profile.json').exists())
   mountinfo=ex(role,'findmnt','-n','-o','OPTIONS','/opt/ccg').stdout.strip();record(key+'-original-CCG-mount-stays-readonly','ro' in mountinfo.split(','))
   cachefile=folder/'cache-state/status.json';cache_started=time.monotonic();cache_deadline=min(started+300,cache_started+45)
   while time.monotonic()<cache_deadline:
    if cachefile.exists() and json.loads(cachefile.read_text()).get('action')=='enforce':break
    time.sleep(min(1,max(0,cache_deadline-time.monotonic())))
   item['cache_enforce_observation_seconds']=time.monotonic()-cache_started
   record(key+'-original-cache-independent-enforce',cachefile.exists() and json.loads(cachefile.read_text()).get('action')=='enforce' and time.monotonic()<=started+300)
   actual_active={f:(group/f).read_text().strip() for f in ['cpu.max','memory.high','io.max']}
   io_settings=[x for x in state['plan']['settings'] if x['file']=='io.max']
   expected_active={'cpu.max':'720000 100000','memory.high':'20001980416','io.max':io_settings[0]['device']+' rbps=67108864 wbps=67108864 riops=4096 wiops=4096'} if len(io_settings)==1 else {}
   item['actual_active_controls']=actual_active;item['expected_active_controls']=expected_active
   record(key+'-observe-three-planned-controls-and-all-eight-originals-preserved',set(x['file'] for x in state['items'])=={'cpu.max','memory.high','io.max'} and len(state['items'])==3 and not state['plan'].get('warnings') and all(x['state']=='observe' for x in state['items']) and actual_active=={f:initial[f] for f in actual_active} and all((group/f).read_text().strip()==v for f,v in extra_original.items()))
   item['actual_controls']={f:(group/f).read_text().strip() for f in initial};item['actual_journal']=json.loads((folder/'resource-state/journal.json').read_text()) if (folder/'resource-state/journal.json').exists() else None
   if item['actual_controls']!=initial or item['actual_journal'] is not None and item['actual_journal'].get('mutations'):raise RuntimeError('observe changed original controls or created owned mutations')
   for member in (group/'cgroup.procs').read_text().splitlines():
    proc=pathlib.Path('/proc',member)
    try:
     raw=(proc/'stat').read_text();fields=raw[raw.rfind(')')+2:].split();fixture_identity['processes'].append({'pid':int(member),'start_ticks':int(fields[19]),'program':pathlib.Path(os.readlink(proc/'exe')).name})
    except FileNotFoundError:pass
   save()
   daily=list((folder/'log/crg').glob('crg-*.log'));events=[json.loads(x) for file in daily for x in file.read_text().splitlines()]
   record(key+'-daily-logs-report-v2-before-business-campaign',bool(daily) and all(file.stat().st_mode&0o777==0o600 for file in daily) and any(x['event']=='cgroup_detected' and x.get('fields',{}).get('check',{}).get('cgroup_version')=='v2' for x in events))
   fixed={'PID1':identity(pid)}
   for name,expected_exe,expected_sha in [('Agent','/opt/crg/crg',plan['binary_sha256']),('cache','/opt/ccg/bin/containercacheguard',plan['private_fixture_sha256']['fixture/containercacheguard'])]:
    matches=[]
    for member in (group/'cgroup.procs').read_text().split():
     try:
      proc=Path('/proc',member)
      if os.readlink(proc/'exe')==expected_exe:
       assert sha((proc/'exe').read_bytes())==expected_sha;matches.append(identity(member))
     except (FileNotFoundError,ProcessLookupError):pass
    assert len(matches)==1;fixed[name]=matches[0]
   item['fixed_processes']=fixed;item['registered_processes']=list(fixture_identity['processes']);item['primary_start']=ex(role,'su','-','postgres','-c',"/opt/postgresql/pgsql/bin/psql -XAtw -h127.0.0.1 -p5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c 'SELECT pg_postmaster_start_time();'").stdout.strip().splitlines()[-1]
   record(key+'-one-exact-Agent-cache-and-initial-primary',True)
   item['phase']='ready-for-baseline';save()
  except Exception as error:
   item.update(phase='failed',error=str(error),traceback=traceback.format_exc());save();raise

def main():
 global campaign_job
 gate=admission()
 if '--preflight' in sys.argv:
  print(json.dumps(gate));return 0 if gate['phase']=='ready' else 2
 if gate['phase']!='ready':
  print(json.dumps(gate));return 2
 os.umask(0o077);root.mkdir(mode=0o700);report['admission']=gate;report['build_info']=gate['build_info'];report['started_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
 def stopped(signum,frame):raise RuntimeError('explicit long-test stop requested')
 signal.signal(signal.SIGTERM,stopped)
 try:
  create_business();assert len(report['roles'])==2 and all(v['phase']=='ready-for-baseline' for v in report['roles'].values())
  for stage in plan['stages']:
   if stage['phase']=='enforce':switch_enforce()
   for row in report['roles'].values():
    guard_snapshot(row,row['original_controls'] if stage['phase']=='baseline' else row['enforce_controls'])
    assert ex(row['role'],'su','-','postgres','-c',"/opt/postgresql/pgsql/bin/psql -XAtw -h127.0.0.1 -p5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c 'SELECT pg_postmaster_start_time();'").stdout.strip().splitlines()[-1]==row['primary_start']
   run_campaign(stage)
   for row in report['roles'].values():guard_snapshot(row,row['original_controls'] if stage['phase']=='baseline' else row['enforce_controls'])
  report.update(phase='passed',aged_fixture_retained=True,postflight_required=True)
 except BaseException as error:report.update(phase='failed',failure_class=type(error).__name__,error=str(error),traceback=traceback.format_exc())
 finally:
  try:cleanup()
  except BaseException as error:report.update(phase='failed');report.setdefault('cleanup_errors',[]).append(type(error).__name__+': '+str(error))
  report['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
 print(json.dumps({'phase':report['phase'],'checks':len(report['tests']),'stable_release_accepted':False}));return 0 if report['phase']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())
