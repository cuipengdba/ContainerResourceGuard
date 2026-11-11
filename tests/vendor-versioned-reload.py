#!/usr/bin/env python3
"""Explicit disposable-node exact-candidate controller reload checks; not vendor business acceptance."""
import pathlib,json,subprocess,time,traceback,hashlib,os,shutil,datetime,sys,argparse,signal

REVISION='d3706f3ea7ad279fea818e5ad1aa62ac5d3f8710'
BINARY_SHA='dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8'
PROFILE_SHA='00e35e91594ed0ad1075a196c20bd8f4c6628c346c4bd6e901ac05d4cc90ef6b'
REFERENCE_SHA='c96f2edad86977624996006857f1dd55e4535d1672065e79e301982aae1aefeb'
FIXED={'schema':'crg-versioned-reload-plan-v1','source_revision':REVISION,'binary_sha256':BINARY_SHA,
 'profile_sha256':PROFILE_SHA,'reference_template_sha256':REFERENCE_SHA,
 'binary_path':'/var/tmp/crg-realpaths64-20261111/v10-dbs-bw64/dbs-business/crg/crg',
 'profile_path':'/var/tmp/crg-r30-20261110/actual/v10/config/io-profile.json',
 'work_root':'/var/tmp/crg-versioned-reload87-20261111','namespace':'crg-versioned-reload87-20261111',
 'criteria':{'checks':15,'reload_wait_seconds':60,'interval_seconds':1,'cpu_outer_cores':8,'memory_outer_bytes':20*1024**3,
             'host_available_min_bytes':8*1024**3,'disk_free_min_bytes':20*1024**3},
 'scope':'continuous one-Agent original-image placeholder PID1; not vendor business or percentage performance acceptance'}

def initial_gate():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',required=True,type=pathlib.Path);p.add_argument('--plan-sha256',required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
 try:
  assert sys.platform=='linux' and os.geteuid()==0,'LINUX_ROOT_REQUIRED'
  assert a.plan.is_file() and not a.plan.is_symlink() and a.plan.stat().st_size<65536,'PLAN_FILE'
  raw=a.plan.read_bytes();assert hashlib.sha256(raw).hexdigest()==a.plan_sha256,'PLAN_DIGEST'
  plan=json.loads(raw);assert set(plan)==set(FIXED)|{'executor_sha256'},'PLAN_FIELDS'
  assert all(json.dumps(plan[k],sort_keys=True)==json.dumps(v,sort_keys=True) for k,v in FIXED.items()),'PLAN_CONTRACT'
  assert hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()==plan['executor_sha256'],'EXECUTOR_SOURCE'
  for key,want in [('binary_path',BINARY_SHA),('profile_path',PROFILE_SHA)]:
   source=pathlib.Path(plan[key]);assert source.is_file() and not source.is_symlink() and hashlib.sha256(source.read_bytes()).hexdigest()==want,'SOURCE_DIGEST'
  info=subprocess.run([plan['binary_path'],'build-info'],capture_output=True,text=True,timeout=15);assert info.returncode==0,'BUILD_INFO_EXIT'
  info=json.loads(info.stdout);assert info['version']=='v1.0.0' and info['revision']==REVISION and info['arch']=='amd64','BUILD_IDENTITY'
  root=pathlib.Path(FIXED['work_root']);assert not root.exists() and not root.is_symlink(),'TARGET_NOT_FRESH'
  result=subprocess.run(['kubectl','get','namespace',FIXED['namespace'],'--ignore-not-found','-o','json'],capture_output=True,text=True,timeout=30)
  assert result.returncode==0 and not result.stdout.strip(),'NAMESPACE_NOT_FRESH'
  available=next(int(x.split()[1])*1024 for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
  assert available>=FIXED['criteria']['host_available_min_bytes'] and shutil.disk_usage('/var/tmp').free>=FIXED['criteria']['disk_free_min_bytes'],'HOST_RESERVE'
  if a.execute:assert os.environ.get('CRG_VERSIONED_RELOAD')=='authorized-disposable-test-node-only','EXPLICIT_LAB_MARKER'
  else:
   print(json.dumps({'phase':'ready','execution_allowed':True,'executed':False,'target_root_absent':True,'namespace_absent':True,'release_accepted':False}));raise SystemExit(0)
  return plan,a.plan_sha256,info
 except (AssertionError,OSError,KeyError,TypeError,ValueError,subprocess.SubprocessError) as error:
  print(json.dumps({'phase':'rejected','reason':str(error) if isinstance(error,AssertionError) else type(error).__name__,'executed':False,'release_accepted':False}));raise SystemExit(1)

plan,plan_sha,build_info=initial_gate()
def interrupted(signum,frame):raise KeyboardInterrupt()
signal.signal(signal.SIGTERM,interrupted)
os.umask(0o077)
work=pathlib.Path(FIXED['work_root']);out=work/'actual';ns=FIXED['namespace'];created=False;namespace_uid=None;pod_uid=None;group=None
report={'schema':'crg-versioned-reload-report-v1','phase':'preparing','scope':FIXED['scope'],'tests':[],
 'sources':{'v10':{'revision':REVISION,'binary_sha256':BINARY_SHA}},'version':'v1.0.0','build_info':build_info,
 'executor_sha256':plan['executor_sha256'],'plan_sha256':plan_sha,'reference_template_sha256':REFERENCE_SHA,'profile_sha256':PROFILE_SHA,
 'started_epoch':time.time(),'criteria':FIXED['criteria'],'P10_complete':False,'release_accepted':False}

def run(a,check=True,timeout=240):
 r=subprocess.run(a,capture_output=True,text=True,timeout=timeout)
 if check and r.returncode:raise RuntimeError('test command failed: '+r.stderr[-1500:]+r.stdout[-1000:])
 return r
def create(o):
 r=subprocess.run(['kubectl','create','-f','-','-o','json'],input=json.dumps(o),capture_output=True,text=True,timeout=30)
 if r.returncode:raise RuntimeError('fixture create failed')
 return json.loads(r.stdout)
def ex(*a,**kw):return run(['kubectl','exec','-n',ns,'self','--',*a],**kw)
def call(*a,**kw):return ex('/opt/crg/crg-linux-amd64',*a,**kw)
def save():
 p=out/'report.candidate';p.write_text(json.dumps(report,indent=2));p.chmod(0o600);p.replace(out/'report.json')
def record(name,passed,**extra):
 report['tests'].append(dict(name=name,passed=bool(passed),**extra));save()
 if not passed:raise AssertionError(name)
def launch(root,branch):
 global pod_uid
 mounts=[{'name':n,'mountPath':m,'readOnly':ro} for n,m,ro in [('tools','/opt/crg',True),('config','/etc/crg',False),('data','/opt/postgresql',False),('state','/tmp/containerresourceguard',False),('logs','/var/log/crg',False)]]
 vols=[{'name':n,'hostPath':{'path':str(p),'type':'Directory'}} for n,p in [('tools',work/'binaries'/branch),('config',root/'config'),('data',root/'data'),('state',root/'state'),('logs',root/'logs')]]
 meta_created=create({'apiVersion':'v1','kind':'Pod','metadata':{'name':'self','namespace':ns,'labels':{'managed-by':'crg-auto-test'}},'spec':{'automountServiceAccountToken':False,'enableServiceLinks':False,'restartPolicy':'Never','terminationGracePeriodSeconds':5,'containers':[{'name':'self','image':'db_puc/dbs:V7.0.12.001.02.56','imagePullPolicy':'Never','command':['/bin/bash','-c','while :; do sleep 1; done'],'securityContext':{'privileged':True},'resources':{'requests':{'cpu':'10m','memory':'16Mi'},'limits':{'cpu':'8','memory':'20Gi'}},'volumeMounts':mounts}],'volumes':vols}})
 pod_uid=meta_created['metadata']['uid']
 run(['kubectl','wait','-n',ns,'--for=condition=Ready','pod/self','--timeout=90s'],timeout=100)
 meta=json.loads(run(['kubectl','get','pod','-n',ns,'self','-o','json']).stdout);cid=meta['status']['containerStatuses'][0]['containerID'].split('://')[1];pid=json.loads(run(['crictl','inspect',cid]).stdout)['info']['pid']
 if os.readlink('/proc/%s/ns/mnt'%pid)==os.readlink('/proc/self/ns/mnt'):raise RuntimeError('private mount namespace required')
 group=pathlib.Path('/sys/fs/cgroup')/next(x.split('::',1)[1].lstrip('/') for x in pathlib.Path('/proc/%s/cgroup'%pid).read_text().splitlines() if x.startswith('0::'))
 if group.name!='cri-containerd-'+cid+'.scope':raise RuntimeError('own cgroup leaf mismatch')
 if meta['metadata']['uid']!=pod_uid or not str(group).startswith('/sys/fs/cgroup/kubepods.slice/'):raise RuntimeError('own Pod scope mismatch')
 for namespace in ['pid','net']:
  if os.readlink('/proc/%s/ns/%s'%(pid,namespace))==os.readlink('/proc/self/ns/'+namespace):raise RuntimeError('private namespace required')
 run(['nsenter','-t',str(pid),'-n','ip','link','set','eth0','down'],timeout=15)
 links=json.loads(run(['nsenter','-t',str(pid),'-n','ip','-j','link','show'],timeout=15).stdout)
 if any('UP' in v.get('flags',[]) for v in links if v['ifname']!='lo'):raise RuntimeError('non-loopback interface active')
 report['own_container']={'pod_uid':pod_uid,'container_id':cid,'cgroup':str(group),'network_isolated_before_Agent':True,'namespace_uid':namespace_uid,'image_id':meta['status']['containerStatuses'][0].get('imageID')}
 return cid,group,ex('cat','/proc/1/stat').stdout.split()[21]
def controls(group):return {n:(group/n).read_text().strip() for n in ['cpu.max','memory.max','io.max','cpu.weight','io.weight','memory.high','memory.swap.max','pids.max']}
job=None;cid=None
def write_config(value):
 p=root/'config/config.json';temp=p.with_name('next.json');temp.write_text(json.dumps(value));temp.chmod(0o600);os.replace(temp,p)
def state():
 p=root/'state/status.json'
 try:return json.loads(p.read_text())
 except (FileNotFoundError,json.JSONDecodeError):return {}
def wait_for(predicate,description,seconds=60):
 deadline=time.monotonic()+seconds
 while time.monotonic()<deadline:
  d=state()
  if predicate(d):return d
  if job is not None and job.poll() is not None:raise RuntimeError('Agent stopped before '+description)
  time.sleep(.25)
 raise RuntimeError('reload observation deadline: '+description)
def percentages(d):return d.get('plan',{}).get('percentages',{})
def unchanged_extras():return all(controls(group)[k]==original[k] for k in extra_files)
def start_agent(args):
 global job,stdout,stderr
 stdout=(root/('agent-'+str(len(report['tests']))+'.stdout')).open('xb');stderr=(root/('agent-'+str(len(report['tests']))+'.stderr')).open('xb')
 job=subprocess.Popen(['kubectl','exec','-n',ns,'self','--','/opt/crg/crg-linux-amd64','run','--config','/etc/crg/config.json',*args],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr)
def stop_agent():
 global job
 result=call('disable','--config','/etc/crg/config.json',check=False,timeout=60)
 if job is not None:job.wait(timeout=30);stdout.close();stderr.close();job=None
 return result
try:
 work.mkdir(mode=0o700,exist_ok=False);out.mkdir(mode=0o700);save()
 (work/'binaries/v10').mkdir(mode=0o700,parents=True)
 binary=pathlib.Path(FIXED['binary_path'])
 if hashlib.sha256(binary.read_bytes()).hexdigest()!=report['sources']['v10']['binary_sha256']:raise RuntimeError('source digest mismatch')
 shutil.copyfile(binary,work/'binaries/v10/crg-linux-amd64');(work/'binaries/v10/crg-linux-amd64').chmod(0o755)
 if run(['kubectl','get','namespace',ns],False).returncode==0:raise RuntimeError('namespace exists')
 meta_created=create({'apiVersion':'v1','kind':'Namespace','metadata':{'name':ns,'labels':{'managed-by':'crg-auto-test'}}});namespace_uid=meta_created['metadata']['uid'];created=True
 create({'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'deny-all','namespace':ns},'spec':{'podSelector':{},'policyTypes':['Ingress','Egress']}})
 root=out/'v10';root.mkdir(mode=0o700)
 for n in ['config','data','state','logs']:(root/n).mkdir(mode=0o700)
 profile_source=pathlib.Path(FIXED['profile_path']);cached=profile_source.read_bytes();shutil.copyfile(profile_source,root/'config/io-profile.json')
 (root/'config/io-profile.json').chmod(0o600);profile=root/'config/io-profile.json';profile_mtime=profile.stat().st_mtime_ns
 write_config({'cpu_percent':10,'memory_percent':20,'io_percent':30,'interval_seconds':1,'log_dir':'/var/log/crg/file-v1'})
 cid,group,pid1=launch(root,'v10');original=controls(group);extra_files=['pids.max','cpu.weight','io.weight','memory.high','memory.swap.max']
 report['phase']='testing-live-independent-percentages';save();start_agent(['--cpu-percent','25','--log-dir','/var/log/crg/cli'])
 d=wait_for(lambda x:x.get('state')=='managed' and percentages(x)=={'cpu_percent':25,'memory_percent':20,'io_percent':30},'initial managed')
 record('live-initial-independent-percentages-and-CLI-CPU25',d['configuration']['generation']==1 and unchanged_extras())
 current_pid=next(int(p) for p in (group/'cgroup.procs').read_text().split() if pathlib.Path('/proc',p,'cmdline').read_bytes().split(bytes([0]))[0]==b'/opt/crg/crg-linux-amd64' and hashlib.sha256(pathlib.Path('/proc',p,'exe').read_bytes()).hexdigest()==report['sources']['v10']['binary_sha256'])
 starttime=pathlib.Path('/proc',str(current_pid),'stat').read_text().split()[21]
 write_config({'cpu_percent':35,'memory_percent':25,'io_percent':40,'interval_seconds':1,'log_dir':'/var/log/crg/file-v2'})
 d=wait_for(lambda x:x.get('state')=='managed' and percentages(x)=={'cpu_percent':25,'memory_percent':25,'io_percent':40},'change memory and IO with sticky CLI')
 record('live-reload-two-dimensions-and-sticky-CLI',d['configuration']['generation']==2 and unchanged_extras())
 before=controls(group);write_config({'io_percent':101,'interval_seconds':1})
 d=wait_for(lambda x:x.get('configuration',{}).get('state')=='rejected','reject invalid percentage')
 record('bad-config-retains-entire-last-good-policy-and-kernel-values',d['state']=='degraded' and percentages(d)=={'cpu_percent':25,'memory_percent':25,'io_percent':40} and controls(group)==before and d['configuration']['generation']==2)
 write_config({'io_percent':50,'interval_seconds':1,'log_dir':'/var/log/crg/file-v3'})
 d=wait_for(lambda x:x.get('state')=='managed' and percentages(x)=={'cpu_percent':25,'memory_percent':20,'io_percent':50},'recovery and omitted memory default20')
 record('good-config-recovers-and-omitted-dimension-defaults20',d['configuration']['generation']==3 and unchanged_extras())
 write_config({'interval_seconds':1})
 d=wait_for(lambda x:x.get('state')=='managed' and percentages(x)=={'cpu_percent':25,'memory_percent':20,'io_percent':20},'all omitted except sticky CLI')
 record('empty-resource-config-defaults-memory-and-IO-independently',d['configuration']['generation']==4 and unchanged_extras())
 record('same-Agent-and-PID1-through-live-reloads',pathlib.Path('/proc',str(current_pid),'stat').read_text().split()[21]==starttime and ex('cat','/proc/1/stat').stdout.split()[21]==pid1)
 record('CLI-log-directory-kept-across-file-log-changes',bool(list((root/'logs/cli').glob('crg-*.log'))) and not any((root/'logs'/n).exists() for n in ['file-v1','file-v2','file-v3']))
 record('live-reload-reuses-device-profile-without-recalibration',profile.read_bytes()==cached and profile.stat().st_mtime_ns==profile_mtime)
 r=stop_agent();record('continuous-agent-disable-restores-three-originals',r.returncode==0 and controls(group)==original)
 write_config({'resource_mode':'manual','limits':{'cpu_cores':1,'memory_max':'1GiB'},'interval_seconds':1})
 call('enable','--config','/etc/crg/config.json');start_agent([])
 d=wait_for(lambda x:x.get('state')=='managed' and x.get('plan',{}).get('resource_mode')=='manual','manual restart')
 record('manual-start-manages-only-explicit-core-dimensions',set(i['file'] for i in d['items'])=={'cpu.max','memory.max'} and unchanged_extras())
 write_config({'cpu_percent':20,'memory_percent':20,'io_percent':20,'interval_seconds':1})
 d=wait_for(lambda x:x.get('state')=='managed' and percentages(x)=={'cpu_percent':20,'memory_percent':20,'io_percent':20},'manual-to-percent with existing stable profile')
 record('manual-to-three-percent-reload-adds-calibrated-IO',set(i['file'] for i in d['items'])=={'cpu.max','memory.max','io.max'} and unchanged_extras())
 write_config({'resource_mode':'manual','limits':{'cpu_cores':1},'interval_seconds':1})
 d=wait_for(lambda x:x.get('state')=='managed' and x.get('plan',{}).get('resource_mode')=='manual' and len(x['plan']['settings'])==1,'remove memory and IO')
 record('manual-removal-restores-owned-memory-and-IO',controls(group)['memory.max']==original['memory.max'] and controls(group)['io.max']==original['io.max'] and unchanged_extras())
 (group/'cpu.max').write_text('50000 100000')
 d=wait_for(lambda x:any(i['file']=='cpu.max' and i['state']=='conflict' for i in x.get('items',[])),'external CPU conflict')
 record('external-CPU-change-is-not-overwritten',controls(group)['cpu.max']=='50000 100000' and unchanged_extras())
 r=stop_agent();record('disable-reports-conflict-and-retains-external-CPU',r.returncode!=0 and controls(group)['cpu.max']=='50000 100000' and controls(group)['memory.max']==original['memory.max'] and unchanged_extras())
 record('all-reloads-preserve-PID1-and-zero-OOM',ex('cat','/proc/1/stat').stdout.split()[21]==pid1 and 'oom_kill 0' in (group/'memory.events').read_text())
 assert len(report['tests'])==15 and len({x['name'] for x in report['tests']})==15 and all(x['passed'] for x in report['tests'])
 report['runtime_original_controls']=original;report['runtime_final_controls']=controls(group);report['phase']='passed'
except BaseException as e:report.update(phase='failed',error=str(e),traceback=traceback.format_exc())
finally:
 try:
  if created:
   if job is not None and job.poll() is None:
    try:stop_agent()
    except Exception:pass
   meta=run(['kubectl','get','pod','-n',ns,'self','--ignore-not-found','-o','json'],timeout=30)
   if meta.stdout.strip():
    current=json.loads(meta.stdout)
    if current['metadata']['uid']!=pod_uid or current['metadata']['labels'].get('managed-by')!='crg-auto-test':raise RuntimeError('cleanup Pod UID mismatch')
    run(['kubectl','delete','pod','-n',ns,'self','--wait=true','--timeout=90s'],timeout=100)
   if job is not None:
    try:job.wait(timeout=15)
    except subprocess.TimeoutExpired:job.terminate();job.wait(timeout=15)
   current=json.loads(run(['kubectl','get','namespace',ns,'-o','json'],timeout=30).stdout)
   if current['metadata']['uid']!=namespace_uid or current['metadata']['labels'].get('managed-by')!='crg-auto-test':raise RuntimeError('cleanup namespace UID mismatch')
   run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=150s'],timeout=160)
   absent=run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json'],timeout=30)
   report['namespace_absent']=not absent.stdout.strip()
   if group is not None:
    report['own_cgroup_and_all_Pod_scopes_absent']=not group.exists() and not list(group.parent.glob('cri-containerd-*.scope'))
   if not report['namespace_absent'] or not report.get('own_cgroup_and_all_Pod_scopes_absent'):raise RuntimeError('cleanup not complete')
 except Exception as error:report.update(phase='failed',cleanup_error=type(error).__name__)
 if out.exists():report['ended_epoch']=time.time();save()
print(json.dumps({'phase':report['phase'],'checks':len(report['tests']),'namespace_absent':report.get('namespace_absent'),'error_class':type(report.get('error')).__name__ if report.get('error') else None,'release_accepted':False}))
raise SystemExit(0 if report['phase']=='passed' and report.get('namespace_absent') and report.get('own_cgroup_and_all_Pod_scopes_absent') else 1)
