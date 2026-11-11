import datetime,hashlib,json,os,pathlib,subprocess,tarfile,time
os.umask(0o077)
assert os.environ.get('CRG_NATIVE_QUALIFICATION')=='authorized-disposable-test-node-only'
base=pathlib.Path('/var/tmp/crg-memory167-tools-20261111');root=pathlib.Path('/var/tmp/crg-native194-qualification-20261111');tools=pathlib.Path('/var/tmp/crg-native194-tools-20261111');ns='crg-vendor-lab-native194-20261111'
frozen={'payload_sha256': 'a32b8f5d2b4f733675b315a8b288c81cb6a43eaf3f666dbe6a16087a295e9022', 'files': {'vendor-native-diagnostics.py': '83b3f8894eea96af9dfc2c789ee54b63cd5803e9dd2218a74f6bc100934c31ab', 'vendor-native-diagnostics-checks.py': '38106a8c5f13f34e873d65f08f0c813da799e593339cc5c860c7961b3ee4ed42', 'vendor-soak-load-diagnostics.py': '50ea0454d17d5412a9d4085472ed89831e4408f60aa0fa0ca2dfd905a2bacb1f', 'vendor-soak-load.py': 'ba87ef2d646b723eb8419de25ffcd736f7a5b0925716f4b638761dff70bb2461', 'vendor-native-diagnostics-runtime.py': 'ed4040a1864efec8631cc70013da5628a66c76c76cea76104b31d02b7bad2f2d'}}
payload=base/'native194-payload.tar'
assert not root.exists() and not tools.exists() and hashlib.sha256(payload.read_bytes()).hexdigest()==frozen['payload_sha256']
root.mkdir(mode=0o700);tools.mkdir(mode=0o700)
with tarfile.open(payload) as archive:
 members=archive.getmembers();assert len(members)==len(frozen['files']) and {m.name for m in members}==set(frozen['files'])
 for member in members:
  assert member.isfile() and '/' not in member.name and 0<member.size<65536
  raw=archive.extractfile(member).read();assert hashlib.sha256(raw).hexdigest()==frozen['files'][member.name]
  p=tools/member.name;p.write_bytes(raw);p.chmod(0o600);compile(raw,str(p),'exec')
old_report=pathlib.Path('/var/tmp/crg-native185-qualification-20261111/report.json');prior=json.loads(old_report.read_bytes())
assert prior['phase']=='failed' and prior['host_selftest']['result']['phase']=='passed' and len(prior['host_selftest']['result']['checks'])==23
report={'schema':'crg-native-diagnostic-runtime-qualification-v2','phase':'running','source_sha256':frozen['files'],'roles':{},'started_node_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'prior_qualification':{'path':str(old_report),'sha256':hashlib.sha256(old_report.read_bytes()).hexdigest(),'phase':prior['phase'],'host_checks':23,'retained_reason':prior['reason']},
 'scope':'real Python2 image units and fresh emptyDir PG normal/controlled-lock; no original PG data/config or vendor business startup; original seven-day processes unchanged'}
mount_failure=pathlib.Path('/var/tmp/crg-native188-qualification-20261111/report.json');mount_prior=json.loads(mount_failure.read_bytes());assert mount_prior['phase']=='failed' and 'Permission denied' in mount_prior['reason'];report['prior_root_mount_failure']={'path':str(mount_failure),'sha256':hashlib.sha256(mount_failure.read_bytes()).hexdigest(),'reason':mount_prior['reason']}
uid=None
pins={'bin/postgres':'20af592a38cf5d950a0e28bf0e2fd4e807fd5bd1dd895a9d9b4b5a6151e37bcb','bin/initdb':'c235346ef1d2f14fa4964407965522ea0cdce51fe5428f067b0e75ceaf3db194','bin/pg_ctl':'d1e8bb6e1979fc5b01d9f1aa9f7b7f06e12ff8ef6e865562ac21d777c0a3fe57','bin/psql':'c2d5b1cf6eaa9835b7d1cd21f9d78edf08e17982b0c01880c088356c53e4455a','lib/libpq.so.5':'a0f6cc8fb39a6f84a150c2b423cc17da8766c06923b1722fbea224579c11fd89'}

def save():
 p=root/'report.candidate';p.write_text(json.dumps(report,indent=2)+'\n');p.chmod(0o600);p.replace(root/'report.json')

def run(args,data=None,timeout=30,check=True):
 p=subprocess.run(args,input=data,capture_output=True,text=True,timeout=timeout)
 if check:assert p.returncode==0,(args[:5],p.returncode,p.stderr[-1200:])
 return p

def get(kind,name):
 p=run(['kubectl','get',kind,name,'-n',ns,'--ignore-not-found','-o','json']);return json.loads(p.stdout) if p.stdout.strip() else None

def create(value):run(['kubectl','create','-f','-'],data=json.dumps(value))

def ex(role,*args,**kwargs):return run(['kubectl','exec','-i','-n',ns,role+'-runtime','-c',role,'--',*args],**kwargs)

def component_state(role):
 src=pathlib.Path('/var/tmp/crg-realpaths64-20261111/v10-'+role+'-bw64/'+role+'-business/postgresql/pgsql');out={}
 for name in ['bin','lib','share/postgresql']:
  path=src/name;assert (path.stat().st_uid,path.stat().st_gid)==(999,998) and (path.stat().st_mode & 0o777)==0o700;assert path.is_dir() and not path.is_symlink() and str(path.resolve()).startswith(str(src)+'/')
 for name,want in pins.items():
  p=src/name;assert p.is_file() and str(p.resolve()).startswith(str(src)+'/');actual=hashlib.sha256(p.read_bytes()).hexdigest();assert actual==want;out[name]=actual
 out['share/postgresql/postgres.bki']=hashlib.sha256((src/'share/postgresql/postgres.bki').read_bytes()).hexdigest()
 return out

def pod(role,original,image,userid=None):
 mounts=[{'name':'tmp','mountPath':'/tmp'}];volumes=[{'name':'tmp','emptyDir':{'sizeLimit':'1Gi'}}]
 src='/var/tmp/crg-realpaths64-20261111/v10-'+role+'-bw64/'+role+'-business/postgresql/pgsql/'
 for name,suffix in [('pgbin','bin'),('pglib','lib'),('pgshare','share/postgresql')]:
  mounts.append({'name':name,'mountPath':'/opt/postgresql/pgsql/'+suffix,'readOnly':True});volumes.append({'name':name,'hostPath':{'path':src+suffix,'type':'Directory'}})
 security={}
 if userid is not None:
  security={'runAsUser':userid[0],'runAsGroup':userid[1],'fsGroup':userid[1],'runAsNonRoot':True}
  mounts.append({'name':'output','mountPath':'/opt/postgresql/basebackup'});volumes.append({'name':'output','emptyDir':{'sizeLimit':'64Mi'}})
 obj={'apiVersion':'v1','kind':'Pod','metadata':{'name':role+'-runtime','namespace':ns,'labels':{'managed-by':'crg-vendor-test'}},
  'spec':{'nodeName':original['spec']['nodeName'],'restartPolicy':'Never','automountServiceAccountToken':False,'activeDeadlineSeconds':600,'securityContext':security,
   'containers':[{'name':role,'image':image,'imagePullPolicy':'Never','command':['/bin/sh','-c','exec sleep 540'],
    'env':[{'name':'LD_LIBRARY_PATH','value':'/opt/postgresql/pgsql/lib:/usr/local/lib:/usr/lib64'}],
    'resources':{'requests':{'cpu':'1','memory':'512Mi'},'limits':{'cpu':'1','memory':'512Mi'}},
    'securityContext':{'readOnlyRootFilesystem':True,'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']}},'volumeMounts':mounts}], 'volumes':volumes}}
 create(obj);created=get('pod',role+'-runtime');poduid=created['metadata']['uid']
 run(['kubectl','wait','-n',ns,'--for=condition=Ready','pod/'+role+'-runtime','--timeout=60s'],timeout=70)
 current=get('pod',role+'-runtime');status=next(c for c in current['status']['containerStatuses'] if c['name']==role)
 assert current['metadata']['uid']==poduid and status['restartCount']==0
 ex(role,'python','-c',"import os;os.mkdir('/tmp/crg-native194-tools',0o700)")
 for filename,want in frozen['files'].items():
  raw=(tools/filename).read_text();code="import hashlib,os,sys;raw=sys.stdin.read();assert hashlib.sha256(raw.encode('utf-8')).hexdigest()==sys.argv[2];p='/tmp/crg-native194-tools/'+sys.argv[1];f=open(p,'wb');f.write(raw.encode('utf-8'));f.close();os.chmod(p,0o400)"
  ex(role,'python','-c',code,filename,want,data=raw)
 return {'pod_uid':poduid,'image_id':status['imageID'],'security_context':security,'volume_mounts':mounts}

def deletepod(role,poduid):
 current=get('pod',role+'-runtime');assert current['metadata']['uid']==poduid
 run(['kubectl','delete','pod',role+'-runtime','-n',ns,'--wait=true','--timeout=45s'],timeout=55);assert get('pod',role+'-runtime') is None

try:
 assert get('namespace',ns) is None
 create({'apiVersion':'v1','kind':'Namespace','metadata':{'name':ns,'labels':{'managed-by':'crg-vendor-test'}}});uid=get('namespace',ns)['metadata']['uid'];report['namespace_uid']=uid;save()
 create({'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'deny-all','namespace':ns},'spec':{'podSelector':{},'policyTypes':['Ingress','Egress']}})
 for role in ['dbs','hisdbs']:
  original=json.loads(run(['kubectl','get','pod',role+'-business','-n','crg-vendor-lab-acceptance78-20261111','-o','json']).stdout)
  assert original['metadata']['labels'].get('managed-by')=='crg-vendor-test'
  image=next(c['image'] for c in original['spec']['containers'] if c['name']==role);imageid=next(c['imageID'] for c in original['status']['containerStatuses'] if c['name']==role)
  item={'components_before':component_state(role),'source_image_id':imageid,'checks':[]};report['roles'][role]=item;save()
  item['unit_pod']=pod(role,original,image,(999,998));assert item['unit_pod']['image_id']==imageid
  info="import ctypes,json,os,pwd,sys;lib=ctypes.CDLL('/opt/postgresql/pgsql/lib/libpq.so.5');lib.PQlibVersion.restype=ctypes.c_int;u=pwd.getpwnam('postgres');p='/tmp/crg-native194-tools/vendor-soak-load-diagnostics.py';compile(open(p,'rb').read(),p,'exec');q='/tmp/crg-native194-tools/vendor-native-diagnostics-runtime.py';compile(open(q,'rb').read(),q,'exec');print(json.dumps({'python':sys.version.split()[0],'platform':sys.platform,'postgres_uid':u.pw_uid,'postgres_gid':u.pw_gid,'libpq_version':lib.PQlibVersion(),'PQbackendPID_available':hasattr(lib,'PQbackendPID')}))"
  runtime=json.loads(ex(role,'python','-c',info).stdout);item['runtime']=runtime;save();assert runtime['python']=='2.7.5' and runtime['PQbackendPID_available'] and (runtime['postgres_uid'],runtime['postgres_gid'])==(999,998)
  p=ex(role,'env','CRG_NATIVE_DIAGNOSTICS_SELFTEST=authorized-disposable-test-node-only','python','/tmp/crg-native194-tools/vendor-native-diagnostics-checks.py','--work-dir','/tmp/crg-native194-checks',timeout=30,check=False)
  value=json.loads(ex(role,'cat','/tmp/crg-native194-checks/checks-result.json').stdout);item['selftest']={'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'result':value};save();assert p.returncode==0 and value['phase']=='passed' and len(value['checks'])==23
  for index,case in enumerate(['missing-diagnostic-marker','over900seconds','tampered-helper']):
   runid='20261111188'+('0' if role=='dbs' else '1')+str(index+2);path='/tmp/crg-native194-tools/vendor-soak-load-diagnostics.py'
   cmd=['env','-u','CRG_VENDOR_NATIVE_DIAGNOSTICS','CRG_VENDOR_SOAK_TEST=disposable-loopback-only']
   if case!='missing-diagnostic-marker':cmd+=['CRG_VENDOR_NATIVE_DIAGNOSTICS=qualified-disposable-loopback-only']
   if case=='tampered-helper':
    ex(role,'python','-c',"import os,shutil;d='/tmp/crg-native194-tampered';os.mkdir(d,0o700);shutil.copyfile('/tmp/crg-native194-tools/vendor-soak-load-diagnostics.py',d+'/vendor-soak-load-diagnostics.py');open(d+'/vendor-native-diagnostics.py','wb').write(b'# altered helper\\n')")
    path='/tmp/crg-native194-tampered/vendor-soak-load-diagnostics.py'
   p=ex(role,*cmd,'python',path,'--run-id',runid,'--seconds','901' if case=='over900seconds' else '12',timeout=10,check=False)
   ex(role,'python','-c',"import os,sys;assert not os.path.exists('/opt/postgresql/basebackup/crg-soak-'+sys.argv[1])",runid)
   assert p.returncode==2;item['checks'].append({'case':case,'passed':True,'exit':p.returncode,'own_workload_output_absent':True,'stderr':p.stderr[-400:]});save()
  deletepod(role,item['unit_pod']['pod_uid']);item['unit_pod']['deleted']=True;save()
  item['pg_pod']=pod(role,original,image,(runtime['postgres_uid'],runtime['postgres_gid']));assert item['pg_pod']['image_id']==imageid;save()
  p=ex(role,'env','CRG_NATIVE_RUNTIME_QUALIFICATION=new-emptydir-postgres-only','python','/tmp/crg-native194-tools/vendor-native-diagnostics-runtime.py',role,timeout=400,check=False)
  item['real_pg_process']={'exit':p.returncode,'stdout':p.stdout[-2000:],'stderr':p.stderr[-2000:]}
  save();raw=ex(role,'cat','/tmp/crg-native188-runtime/report.json').stdout;value=json.loads(raw);item['real_pg']=value;item['real_pg_report_sha256']=hashlib.sha256(raw.encode()).hexdigest();save()
  if p.returncode!=0:
   logs=ex(role,'python','-c',"import glob,json,os;d='/tmp/crg-native188-runtime';print(json.dumps({os.path.basename(p):open(p,'rb').read()[-3000:].decode('utf-8','replace') for p in glob.glob(d+'/*.log')}))",check=False)
   item['failure_log_tails']=logs.stdout;save()
  assert p.returncode==0 and value['phase']=='passed' and value['own_postgres_stopped']
  deletepod(role,item['pg_pod']['pod_uid']);item['pg_pod']['deleted']=True
  item['components_after']=component_state(role);assert item['components_after']==item['components_before'];save()
 report['phase']='passed'
except BaseException as error:report.update(phase='failed',reason=type(error).__name__+':'+str(error)[:1800])
finally:
 if uid is not None:
  try:
   current=get('namespace',ns);assert current['metadata']['uid']==uid and current['metadata']['labels'].get('managed-by')=='crg-vendor-test'
   run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=90s'],timeout=100);assert get('namespace',ns) is None;report['namespace_absent']=True
  except BaseException as error:report.update(phase='failed',cleanup_error=type(error).__name__)
 report['ended_node_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
print(json.dumps({'phase':report['phase'],'roles':{r:{'unit_checks':len(v.get('selftest',{}).get('result',{}).get('checks',[])),'real_pg_checks':len(v.get('real_pg',{}).get('checks',[]))} for r,v in report['roles'].items()},'reason':report.get('reason'),'namespace_absent':report.get('namespace_absent')}))
raise SystemExit(0 if report['phase']=='passed' else 1)
