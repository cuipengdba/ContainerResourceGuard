from pathlib import Path
import copy,hashlib,importlib.util,json,os,selectors,shutil,subprocess,sys,time,traceback
w=Path(__file__).resolve().parent;root=w/'result';ns='crg-vendor-lab-port1312-20261115';report={'phase':'preparing','scope':'Live isolated original-image Pod diagnostic admission/ownership only; no CRG or business started. Fault tests explicitly injected.','tests':[],'roles':{},'source_sha256':{},'business_SLA_accepted':False};created=False;namespace_uid=None
def run(argv,timeout=20,check=True,data=None):
 q=subprocess.run(argv,input=data,capture_output=True,text=True,timeout=timeout)
 if check and q.returncode:raise RuntimeError('qualification command failed exit='+str(q.returncode))
 return q
def get(kind,name):return json.loads(run(['kubectl','get',kind,name,'--request-timeout=3s','-o','json']+(['-n',ns] if kind=='pod' else [])).stdout)
def create(value):run(['kubectl','create','-f','-'],data=json.dumps(value))
def save():(root/'report.json').write_text(json.dumps(report,indent=2)+'\n')
def record(name,condition):
 report['tests'].append({'name':name,'passed':bool(condition)});save();assert condition,name
def identity(pid):
 try:return int(Path('/proc',str(pid),'stat').read_bytes().rsplit(b')',1)[1].split()[19])
 except (FileNotFoundError,ProcessLookupError):return None
def load(name):
 spec=importlib.util.spec_from_file_location(name.replace('-','_'),w/(name+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
assert os.geteuid()==0 and os.environ.get('CRG_PORT1312_QUALIFICATION')=='authorized-isolated-test-node-only' and not root.exists();root.mkdir(mode=0o700)
try:
 for name,h in json.loads((w/'source-map.json').read_bytes()).items():
  assert hashlib.sha256((w/name).read_bytes()).hexdigest()==h;report['source_sha256'][name]=h
 # Confirm the preceding exact migration remains terminal and all its fixtures
 # gone before creating this entirely separate diagnostic fixture.
 prior=Path('/var/tmp/crg-percent1287-results-20261115/report.json');raw=prior.read_bytes();assert hashlib.sha256(raw).hexdigest()=='8252c7adc5e803cd476774ab323fe73506b2b4b67e5c59b218e97ede6d08a716';previous=json.loads(raw);assert previous['phase']=='passed'
 for row in previous['roles'].values():
  assert identity(row['driver']['pid'])!=row['driver']['start_ticks']
  for rec in row['cleanup']:
   v=rec['identity'];assert not Path(v['group']).exists() and not Path(v['pod_parent']).exists() and all(identity(p['pid'])!=p['start_ticks'] for p in v['processes'])
 for oldns in ['crg-vendor-lab-percent1287-dbs-20261115','crg-vendor-lab-percent1287-hisdbs-20261115',ns]:assert not run(['kubectl','get','namespace',oldns,'--ignore-not-found','--request-timeout=3s','-o','json']).stdout.strip()
 mem=int(next(v.split()[1] for v in Path('/proc/meminfo').read_text().splitlines() if v.startswith('MemAvailable:')))*1024;assert mem>=8*1024**3 and shutil.disk_usage(w).free>=20*1024**3;report['available_memory_before_bytes']=mem
 structural=load('port-integration-checks').qualify(w);assert structural['phase']=='passed' and structural['count']==28;report['structural_qualification']=structural;save()
 module=load('vendor-port-diagnostics');create({'apiVersion':'v1','kind':'Namespace','metadata':{'name':ns,'labels':{'managed-by':'crg-vendor-test'}}});created=True;namespace_uid=get('namespace',ns)['metadata']['uid'];report['namespace_uid']=namespace_uid
 create({'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'deny-all','namespace':ns},'spec':{'podSelector':{},'policyTypes':['Ingress','Egress']}})
 images=json.loads(Path('/var/tmp/crg-business-20261110/vendor-import.json').read_bytes())['images'];expected_images={'dbs':'25825bc9f1e9635075f97bedcee37bebb409821cc3c0084ec8ee2a07588cd3b5','hisdbs':'b772e2bcd0c9d5b8b0896c6efe972d92e76280c0c183d317ebca75df2ca8c39f'}
 for role in ['dbs','hisdbs']:
  item={'phase':'preparing','snapshots':[]};report['roles'][role]=item;save();pod_created=False;owner=None;init=None;group=None;pod_uid=None
  try:
   pod={'apiVersion':'v1','kind':'Pod','metadata':{'name':role+'-business','namespace':ns,'labels':{'managed-by':'crg-vendor-test'}},'spec':{'restartPolicy':'Never','automountServiceAccountToken':False,'enableServiceLinks':False,'containers':[{'name':role,'image':images[role]['tag'],'imagePullPolicy':'Never','command':['/bin/sh','-c','exec sleep 600'],'resources':{'requests':{'cpu':'10m','memory':'32Mi'},'limits':{'cpu':'1','memory':'256Mi'}}}]}}
   create(pod);pod_created=True;run(['kubectl','wait','-n',ns,'--for=condition=Ready','pod/'+role+'-business','--timeout=90s'],timeout=100);meta=get('pod',role+'-business');pod_uid=meta['metadata']['uid'];status=next(v for v in meta['status']['containerStatuses'] if v['name']==role);assert status['imageID'].rsplit('sha256:',1)[-1]==expected_images[role];cid=status['containerID'].split('://')[1];pid=json.loads(run(['crictl','inspect',cid]).stdout)['info']['pid'];init={'pid':pid,'start_ticks':identity(pid)};group=Path('/sys/fs/cgroup')/next(v.split('::',1)[1].lstrip('/') for v in Path('/proc',str(pid),'cgroup').read_text().splitlines() if v.startswith('0::'));item.update(init=init,group=str(group),pod_parent=str(group.parent),pod_uid=pod_uid,container_id=cid,original_image_id=status['imageID']);save()
   assert group.name=='cri-containerd-'+cid+'.scope' and '/kubepods.slice/' in str(group)
   run(['nsenter','-t',str(pid),'-n','--','ip','link','set','dev','eth0','down']);assert 'state DOWN' in run(['nsenter','-t',str(pid),'-n','--','ip','-o','link','show','dev','eth0']).stdout
   session=module.begin(ns,role,meta);record(role+'-actual-isolated-runtime-admission',isinstance(session,module.Session) and session.target['pid']==pid and session.target['start_ticks']==init['start_ticks'])
   before=session.snapshot('before-qualification-listener');item['snapshots'].append(before);record(role+'-before-start-recorded-with-stable-target',before.get('sample',{}).get('target_identity_stable') and not before['sample']['listeners'])
   code="import json,os,socket,sys\na=socket.socket();a.bind(('127.0.0.1',55432));a.listen(1)\nu=socket.socket(socket.AF_UNIX);u.bind('/tmp/.s.PGSQL.55432');u.listen(1)\nsys.stdout.write(json.dumps({'pid':os.getpid()})+'\\n');sys.stdout.flush();sys.stdin.readline();a.close();u.close();os.unlink('/tmp/.s.PGSQL.55432')\n"
   owner=subprocess.Popen(['kubectl','exec','-i','-n',ns,role+'-business','-c',role,'--','python','-u','-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);item['owner_exec']={'pid':owner.pid,'start_ticks':identity(owner.pid)};save()
   with selectors.DefaultSelector() as sel:
    sel.register(owner.stdout,selectors.EVENT_READ);assert sel.select(10),'listener fixture output timeout';child=json.loads(owner.stdout.readline())
   held=session.snapshot('listener-held');item['snapshots'].append(held);rows=held.get('sample',{}).get('listeners',[]);owners=[p for v in rows for p in v['owners']];item['socket_owner_instances']=[{'pid':p['pid'],'start_ticks':p['start_ticks']} for p in owners];save();record(role+'-actual-TCP-and-Unix-owner-observed',{'tcp','unix'}<=set(v['table'] for v in rows) and bool(owners) and all(p['same_cgroup'] and p['cgroup_membership']==session.target['cgroup_membership'] and int(next(v.split()[-1] for v in Path('/proc',str(p['pid']),'status').read_text().splitlines() if v.startswith('NSpid:')))==child['pid'] for p in owners))
   runtime=session._runtime_pid;session._runtime_pid=lambda:pid+1
   try:changed=session.snapshot('injected-runtime-change')
   finally:session._runtime_pid=runtime
   item['snapshots'].append(changed);record(role+'-injected-runtime-change-does-not-scan',changed['phase']=='partial' and changed['issues']==['fixture-identity-changed-no-scan'] and 'sample' not in changed)
   getter=module._get
   def changed_get(kind,name,namespace=None):
    value=getter(kind,name,namespace)
    if kind=='pod':value=copy.deepcopy(value);value['metadata']['uid']='87654321-4321-4321-4321-cba987654321'
    return value
   module._get=changed_get
   try:changed=session.snapshot('injected-Pod-UID-change')
   finally:module._get=getter
   item['snapshots'].append(changed);record(role+'-injected-Pod-UID-change-does-not-scan',changed['phase']=='partial' and changed['issues']==['fixture-identity-changed-no-scan'] and 'sample' not in changed)
   stdout,stderr=owner.communicate('\n',timeout=15);assert owner.returncode==0,(stdout,stderr);after=session.snapshot('after-qualification-owner-stop');item['snapshots'].append(after);record(role+'-own-EOF-listener-stop-and-stable-init',after.get('sample',{}).get('target_identity_stable') and not after['sample']['listeners'] and identity(init['pid'])==init['start_ticks']);item['phase']='passed';save()
  except BaseException as error:item.update(phase='failed',error_class=type(error).__name__,traceback=traceback.format_exc());save();raise
  finally:
   if owner is not None and owner.poll() is None:
    try:owner.communicate('\n',timeout=15)
    except subprocess.TimeoutExpired:item['owner_exec_pending_Pod_cleanup']=True
   if pod_created:
    meta=get('pod',role+'-business');assert meta['metadata']['uid']==pod_uid and meta['metadata']['labels']['managed-by']=='crg-vendor-test';run(['kubectl','delete','pod','-n',ns,role+'-business','--wait=true','--timeout=90s'],timeout=100)
   if group is not None:
    item['cleanup']={'leaf_absent':not group.exists(),'parent_absent':not group.parent.exists(),'init_original_absent':identity(init['pid'])!=init['start_ticks'],'socket_owner_instances_absent':all(identity(v['pid'])!=v['start_ticks'] for v in item.get('socket_owner_instances',[])),'owner_exec_original_absent':not item.get('owner_exec') or identity(item['owner_exec']['pid'])!=item['owner_exec']['start_ticks']};record(role+'-own-Pod-parent-leaf-and-registered-processes-absent',all(item['cleanup'].values()))
   save()
 report['phase']='passed' if len(report['tests'])==14 and all(v['passed'] for v in report['tests']) and len(report['roles'])==2 and all(v['phase']=='passed' for v in report['roles'].values()) else 'failed'
except BaseException as error:report.update(phase='failed',error_class=type(error).__name__,traceback=traceback.format_exc())
finally:
 if created:
  meta=get('namespace',ns);assert meta['metadata']['uid']==namespace_uid and meta['metadata']['labels']['managed-by']=='crg-vendor-test';run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=120s'],timeout=130)
 report['namespace_absent']=not run(['kubectl','get','namespace',ns,'--ignore-not-found','--request-timeout=3s','-o','json']).stdout.strip();save()
exit_code=0 if report['phase']=='passed' and report['namespace_absent'] else 1;(w/'exit.json').write_text(json.dumps({'exit':exit_code,'phase':report['phase'],'namespace_absent':report['namespace_absent'],'report_sha256':hashlib.sha256((root/'report.json').read_bytes()).hexdigest()}));print(json.dumps({'phase':report['phase'],'checks':len(report['tests'])}));raise SystemExit(exit_code)
