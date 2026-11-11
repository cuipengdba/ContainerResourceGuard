import datetime,hashlib,json,os,pathlib,subprocess,tarfile,time
os.umask(0o077)
base=pathlib.Path('/var/tmp/crg-memory167-tools-20261111');root=pathlib.Path('/var/tmp/crg-native185-qualification-20261111');tools=pathlib.Path('/var/tmp/crg-native185-tools-20261111');ns='crg-vendor-lab-native185-20261111'
assert os.environ.get('CRG_NATIVE_QUALIFICATION')=='authorized-disposable-test-node-only'
frozen={'payload_sha256': 'ac936cd8f116c56bb7c699027a3423f9e0f2a9ead77416002e4c7fe13fdee108', 'files': {'vendor-native-diagnostics.py': '83b3f8894eea96af9dfc2c789ee54b63cd5803e9dd2218a74f6bc100934c31ab', 'vendor-native-diagnostics-checks.py': '38106a8c5f13f34e873d65f08f0c813da799e593339cc5c860c7961b3ee4ed42', 'vendor-soak-load-diagnostics.py': '50ea0454d17d5412a9d4085472ed89831e4408f60aa0fa0ca2dfd905a2bacb1f', 'vendor-soak-load.py': 'ba87ef2d646b723eb8419de25ffcd736f7a5b0925716f4b638761dff70bb2461'}}
payload=base/'native185-payload.tar'
assert not root.exists() and not tools.exists() and hashlib.sha256(payload.read_bytes()).hexdigest()==frozen['payload_sha256']
root.mkdir(mode=0o700);tools.mkdir(mode=0o700)
with tarfile.open(payload) as archive:
 members=archive.getmembers();assert len(members)==len(frozen['files']) and {m.name for m in members}==set(frozen['files'])
 for member in members:
  assert member.isfile() and '/' not in member.name and 0<member.size<65536
  raw=archive.extractfile(member).read();assert hashlib.sha256(raw).hexdigest()==frozen['files'][member.name]
  p=tools/member.name;p.write_bytes(raw);p.chmod(0o600);compile(raw,str(p),'exec')
report={'schema':'crg-native-diagnostic-runtime-qualification-v1','phase':'running','source_sha256':frozen['files'],'roles':{},'started_node_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'mock callback selftest and CLI guards in Linux3.9 and both cached Python2 images; real PG activity/wait/native execution not yet qualified; no product or original input changes'}
uid=None
def save():
 p=root/'report.candidate';p.write_text(json.dumps(report,indent=2)+'\n');p.chmod(0o600);p.replace(root/'report.json')
def run(args,data=None,timeout=30,check=True):
 p=subprocess.run(args,input=data,capture_output=True,text=True,timeout=timeout)
 if check:assert p.returncode==0,(args[:5],p.returncode,p.stderr[-800:])
 return p
def get(kind,name):
 p=run(['kubectl','get',kind,name,'-n',ns,'--ignore-not-found','-o','json']);return json.loads(p.stdout) if p.stdout.strip() else None
def create(value):run(['kubectl','create','-f','-'],data=json.dumps(value))
def ex(role,*args,**kwargs):return run(['kubectl','exec','-i','-n',ns,role+'-runtime','-c',role,'--',*args],**kwargs)
try:
 p=run(['env','CRG_NATIVE_DIAGNOSTICS_SELFTEST=authorized-disposable-test-node-only','python3',str(tools/'vendor-native-diagnostics-checks.py'),'--work-dir',str(root/'host-checks')],timeout=30,check=False)
 report['host_selftest']={'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'result':json.loads((root/'host-checks/checks-result.json').read_text())};save();assert p.returncode==0 and len(report['host_selftest']['result']['checks'])==23
 assert get('namespace',ns) is None
 create({'apiVersion':'v1','kind':'Namespace','metadata':{'name':ns,'labels':{'managed-by':'crg-vendor-test'}}});uid=get('namespace',ns)['metadata']['uid']
 report['namespace_uid']=uid
 create({'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'deny-all','namespace':ns},'spec':{'podSelector':{},'policyTypes':['Ingress','Egress']}})
 for role in ['dbs','hisdbs']:
  original=json.loads(run(['kubectl','get','pod',role+'-business','-n','crg-vendor-lab-acceptance78-20261111','-o','json']).stdout)
  assert original['metadata']['labels'].get('managed-by')=='crg-vendor-test'
  image=next(c['image'] for c in original['spec']['containers'] if c['name']==role)
  imageid=next(c['imageID'] for c in original['status']['containerStatuses'] if c['name']==role)
  obj={'apiVersion':'v1','kind':'Pod','metadata':{'name':role+'-runtime','namespace':ns,'labels':{'managed-by':'crg-vendor-test'}},
   'spec':{'nodeName':original['spec']['nodeName'],'restartPolicy':'Never','automountServiceAccountToken':False,
    'containers':[{'name':role,'image':image,'imagePullPolicy':'Never','command':['/bin/sh','-c','exec sleep 240'],
     'resources':{'requests':{'cpu':'1','memory':'256Mi'},'limits':{'cpu':'1','memory':'256Mi'}},
     'securityContext':{'readOnlyRootFilesystem':True,'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL']}},
     'volumeMounts':[{'name':'tmp','mountPath':'/tmp'}]}],'volumes':[{'name':'tmp','emptyDir':{'sizeLimit':'64Mi'}}]}}
  create(obj);pod=get('pod',role+'-runtime');poduid=pod['metadata']['uid']
  run(['kubectl','wait','-n',ns,'--for=condition=Ready','pod/'+role+'-runtime','--timeout=60s'],timeout=70)
  ex(role,'python','-c',"import os;os.mkdir('/tmp/crg-native185-tools',0o700)")
  for filename,want in frozen['files'].items():
   raw=(tools/filename).read_text();code="import hashlib,os,sys;raw=sys.stdin.read();assert hashlib.sha256(raw.encode('utf-8')).hexdigest()==sys.argv[2];p='/tmp/crg-native185-tools/'+sys.argv[1];f=open(p,'wb');f.write(raw.encode('utf-8'));f.close();os.chmod(p,0o400)"
   ex(role,'python','-c',code,filename,want,data=raw)
  info="import ctypes,json,os,pwd,sys;lib=ctypes.CDLL('/opt/postgresql/pgsql/lib/libpq.so.5');lib.PQlibVersion.restype=ctypes.c_int;u=pwd.getpwnam('postgres');p='/tmp/crg-native185-tools/vendor-soak-load-diagnostics.py';compile(open(p,'rb').read(),p,'exec');print(json.dumps({'python':sys.version.split()[0],'platform':sys.platform,'postgres_uid':u.pw_uid,'postgres_gid':u.pw_gid,'libpq_version':lib.PQlibVersion(),'PQbackendPID_available':hasattr(lib,'PQbackendPID'),'initdb_available':os.path.isfile('/opt/postgresql/pgsql/bin/initdb')}))"
  runtime=json.loads(ex(role,'python','-c',info).stdout);assert runtime['python']=='2.7.5' and runtime['PQbackendPID_available'] and runtime['initdb_available']
  item={'runtime':runtime,'pod_uid':poduid,'image_id':imageid,'no_host_or_business_data_mounts':True,'checks':[]};report['roles'][role]=item;save()
  result=ex(role,'env','CRG_NATIVE_DIAGNOSTICS_SELFTEST=authorized-disposable-test-node-only','python','/tmp/crg-native185-tools/vendor-native-diagnostics-checks.py','--work-dir','/tmp/crg-native185-checks',timeout=30,check=False)
  value=json.loads(ex(role,'cat','/tmp/crg-native185-checks/checks-result.json').stdout)
  item['selftest']={'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'result':value};save();assert result.returncode==0 and len(value['checks'])==23 and all(c['passed'] for c in value['checks'])
  for index,case in enumerate(['missing-diagnostic-marker','over900seconds']):
   runid='20261111185'+('0' if role=='dbs' else '1')+str(index)
   cmd=['env','-u','CRG_VENDOR_NATIVE_DIAGNOSTICS','CRG_VENDOR_SOAK_TEST=disposable-loopback-only']
   if case!='missing-diagnostic-marker':cmd+=['CRG_VENDOR_NATIVE_DIAGNOSTICS=qualified-disposable-loopback-only']
   p=ex(role,*cmd,'python','/tmp/crg-native185-tools/vendor-soak-load-diagnostics.py','--run-id',runid,'--seconds','901' if case=='over900seconds' else '15',timeout=10,check=False)
   absent=ex(role,'python','-c',"import os,sys;assert not os.path.exists('/opt/postgresql/basebackup/crg-soak-'+sys.argv[1])",runid).returncode==0
   assert p.returncode==2 and absent
   item['checks'].append({'case':case,'passed':True,'exit':p.returncode,'own_workload_output_absent':True,'stderr':p.stderr[-400:]});save()
  current=get('pod',role+'-runtime');assert current['metadata']['uid']==poduid
  status=next(c for c in current['status']['containerStatuses'] if c['name']==role);assert status['restartCount']==0 and status['imageID']==imageid
  run(['kubectl','delete','pod',role+'-runtime','-n',ns,'--wait=true','--timeout=45s'],timeout=55);assert get('pod',role+'-runtime') is None
 report['phase']='passed'
except BaseException as error:report.update(phase='failed',reason=type(error).__name__+':'+str(error)[:1200])
finally:
 if uid is not None:
  try:
   current=get('namespace',ns);assert current['metadata']['uid']==uid and current['metadata']['labels'].get('managed-by')=='crg-vendor-test'
   run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=90s'],timeout=100);assert get('namespace',ns) is None;report['namespace_absent']=True
  except BaseException as error:report.update(phase='failed',cleanup_error=type(error).__name__)
 report['ended_node_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
print(json.dumps({'phase':report['phase'],'host_checks':len(report.get('host_selftest',{}).get('result',{}).get('checks',[])),'roles':{role:{'unit_checks':len(item.get('selftest',{}).get('result',{}).get('checks',[])),'gates':len(item['checks'])} for role,item in report['roles'].items()},'reason':report.get('reason'),'namespace_absent':report.get('namespace_absent')}))
raise SystemExit(0 if report['phase']=='passed' else 1)
