from pathlib import Path
import datetime,hashlib,importlib.util,json,os,shlex,stat,subprocess,tempfile,time,traceback

w=Path(__file__).parent;ns='crg-vendor-lab-bytecode943-20261113';sha=lambda raw:hashlib.sha256(raw).hexdigest();f=json.loads((w/'manifest.json').read_text());created=False;namespace_uid=None
report={'schema':'crg-private-bytecode-and-export-qualification-v1','phase':'running','checks':[],'roles':{},'host_Python3':{},'source_sha256':f['source_sha256'],'namespace':ns,'original_vendor_services_or_full600_started':False,'BPF_hooks_or_maps_created':False}
pins={'dbs':'sha256:25825bc9f1e9635075f97bedcee37bebb409821cc3c0084ec8ee2a07588cd3b5','hisdbs':'sha256:b772e2bcd0c9d5b8b0896c6efe972d92e76280c0c183d317ebca75df2ca8c39f'}
def ident(pid):
 fields=Path('/proc',str(pid),'stat').read_bytes().rsplit(b')',1)[1].split();return {'pid':pid,'start_ticks':int(fields[19])}
(w/'worker.json').write_text(json.dumps(ident(os.getpid())))
def save():(w/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
def check(name,passed,strict=True):
 report['checks'].append({'name':name,'passed':bool(passed)});save()
 if strict and not passed:raise AssertionError(name)
def run(args,data=None,timeout=30):
 v=subprocess.run(args,input=data,capture_output=True,timeout=timeout);assert len(v.stdout)<=65536 and len(v.stderr)<=65536
 if v.returncode:
  report['failed_command']={'args':args,'exit':v.returncode,'stdout_utf8':v.stdout.decode(),'stderr_utf8':v.stderr.decode()};save();raise RuntimeError('owned qualification command exit='+str(v.returncode))
 return v
def create(value):run(['kubectl','create','-f','-'],json.dumps(value).encode())
def absent(value):
 try:return ident(value['pid'])['start_ticks']!=value['start_ticks']
 except (FileNotFoundError,ProcessLookupError):return True
def load(name):
 spec=importlib.util.spec_from_file_location(name.replace('-','_'),w/(name+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
try:
 for name,want in f['source_sha256'].items():assert sha((w/name).read_bytes())==want
 assert (w/'factory-old.py').read_text().replace("result[-1]='CRG_VENDOR_TRANSPORT=","result[-1]='PYTHONDONTWRITEBYTECODE=1 CRG_VENDOR_TRANSPORT=")==(w/'factory.py').read_text()
 check('all-frozen-SHAs-and-factory-one-environment-assignment-only',True)
 previous=Path('/var/tmp/crg-high930-pressure-20261113/report.json').read_bytes();old=json.loads(previous)
 check('previous-full930-business-pass-and-private-cleanup-failure-retained',sha(previous)==f['previous_full930_report_sha256'] and old['phase']=='passed' and len(old['tests'])==32 and all(v['passed'] for v in old['tests']) and len(old['roles'])==2 and all(any(v['name']=='private-transport-channel-bounded-cleaned-and-original-native-exited' and not v['passed'] for v in row['full_BPF_diagnostic']['checks']) for row in old['roles'].values()) and not run(['kubectl','get','namespace','crg-vendor-lab-high930-20261113','--ignore-not-found','-o','json']).stdout.strip())
 units=[('original-factory17',['factory-old-unit.py','factory.py','hook.py','original-core.py','actual-null-preflight.json'],17),('real-private-factory9',['factory-private-unit.py','factory.py','hook.py','receiver.py','sitecustomize.py'],9),('unchanged-host-receiver18',['receiver-unit.py','receiver.py','sitecustomize.py'],18),('original-export12',['artifact-transfer-old-unit.py','artifact-transfer.py'],12),('exact-annotation-export19',['artifact-annotations-unit.py','artifact-transfer.py'],19)]
 report['host_units']={}
 for name,names,count in units:
  result=run(['python3',*[str(w/file) for file in names]],timeout=45);assert not result.stderr;value=json.loads(result.stdout);report['host_units'][name]=value;check(name,value['phase']=='passed' and len(value['cases'])==count)
 receiver=load('receiver');factory=load('factory');old_factory=load('factory-old')
 for number,mode in enumerate(['default','disabled']):
  with tempfile.TemporaryDirectory(prefix='crg-bytecode943-host-') as directory:
   root=Path(directory);c=receiver.Channel(root,'202611139439'+str(number),os.geteuid(),os.getegid(),(w/'sitecustomize.py').read_bytes(),lambda:True);c.prepare();c.start();env=dict(os.environ,PYTHONPATH=str(root/c.name));env.pop('PYTHONDONTWRITEBYTECODE',None)
   if mode=='disabled':env['PYTHONDONTWRITEBYTECODE']='1'
   v=subprocess.run(['python3','-c','import sys; print(sys.version.split()[0])'],capture_output=True,env=env,timeout=15);assert v.returncode==0 and not v.stderr and len(v.stdout)<128
   before=sorted(p.name for p in (root/c.name).iterdir());c.stop();error=None
   try:c.cleanup()
   except receiver.Rejected as e:error=str(e)
   status=c.status();ok=status['stopped'] and status['reader_closed'] and not status['thread_alive'] and status['directory_fd_closed'] and status['parent_fd_closed']
   if mode=='default':ok=ok and '__pycache__' in before and error=='UNEXPECTED_CHANNEL_CONTENTS' and not status['cleaned'] and (root/c.name/'__pycache__').is_dir()
   else:ok=ok and set(before)==set(c.owned) and error is None and status['cleaned'] and not (root/c.name).exists()
   report['host_Python3'][mode]={'Python':v.stdout.decode().strip(),'entries_before_cleanup':before,'cleanup_error':error,'channel':status,'negative_unregistered_cache_removed_only_by_fixture_temp_root_teardown':mode=='default'};check('actual-host-Python3-'+mode+'-bytecode-and-strict-cleanup',ok)
 assert not run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json']).stdout.strip()
 create({'apiVersion':'v1','kind':'Namespace','metadata':{'name':ns,'labels':{'managed-by':'crg-vendor-test','crg-unit-run':'bytecode943'}}});created=True;namespace_uid=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout)['metadata']['uid'];report['namespace_uid']=namespace_uid
 images=json.loads(Path('/var/tmp/crg-business-20261110/vendor-import.json').read_text())['images']
 for role_index,role in enumerate(['dbs','hisdbs']):
  image=images[role]['tag'];image_id=json.loads(run(['crictl','inspecti',image]).stdout)['status']['id'];check(role+'-original-image-pin-no-pull',image_id==pins[role]);pod=role+'-bytecode-unit'
  create({'apiVersion':'v1','kind':'Pod','metadata':{'name':pod,'namespace':ns,'labels':{'managed-by':'crg-vendor-test','crg-unit-run':'bytecode943'}},'spec':{'restartPolicy':'Never','terminationGracePeriodSeconds':2,'containers':[{'name':role,'image':image,'imagePullPolicy':'Never','command':['/bin/sh','-c','exec sleep 300'],'resources':{'limits':{'cpu':'500m','memory':'256Mi'}},'securityContext':{'runAsUser':0,'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL'],'add':['SETUID','SETGID']}}}]}})
  run(['kubectl','wait','-n',ns,'--for=condition=Ready','pod/'+pod,'--timeout=90s'],timeout=100)
  meta=json.loads(run(['kubectl','get','pod',pod,'-n',ns,'-o','json']).stdout);cid=meta['status']['containerStatuses'][0]['containerID'].split('://')[1];pid=json.loads(run(['crictl','inspect',cid]).stdout)['info']['pid'];identity=ident(pid);cgroup_raw=Path('/proc',str(pid),'cgroup').read_bytes();group=Path('/sys/fs/cgroup')/cgroup_raw.decode().strip()[3:].lstrip('/');assert group.name=='cri-containerd-'+cid+'.scope'
  uid=int(run(['kubectl','exec','-n',ns,pod,'-c',role,'--','id','-u','postgres']).stdout);gid=int(run(['kubectl','exec','-n',ns,pod,'-c',role,'--','id','-g','postgres']).stdout);assert uid==999
  row={'image_id':image_id,'pod_uid':meta['metadata']['uid'],'container_id':cid,'init':identity,'group':str(group),'pod_parent':str(group.parent),'postgres_uid':uid,'postgres_gid':gid,'cases':[]};report['roles'][role]=row;save()
  for name in ['bytecode-PG-harness.py','bytecode-usercustomize.py','frozen-native.py']:
   code="import os,sys;fd=os.open('/tmp/"+name+"',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o444);s=os.fdopen(fd,'wb');s.write(sys.stdin.read());s.close()";run(['kubectl','exec','-i','-n',ns,pod,'-c',role,'--','python','-c',code],(w/name).read_bytes())
  def same_container():return not absent(identity) and Path('/proc',str(pid),'cgroup').read_bytes()==cgroup_raw and group.exists()
  for index,(mode,variant) in enumerate([('default','normal'),('disabled','normal'),('disabled','no-reader'),('disabled','stopped-reader')]):
   run_id='20261113943'+str(role_index)+str(index);c=receiver.Channel(Path('/proc',str(pid),'root/tmp'),run_id,uid,gid,(w/'sitecustomize.py').read_bytes(),same_container);case={'mode':mode,'variant':variant,'run_id':run_id};row['cases'].append(case);accepted=False
   try:
    c.prepare()
    if variant!='no-reader':c.start()
    if variant=='stopped-reader':c.stop()
    module=old_factory if mode=='default' else factory;command=['kubectl','exec','-n',ns,role+'-business','-c',role,'--','su','-','postgres','-c',module.native_command(role,run_id)];augmented,matched=module.augment_native_call(command,ns,role,run_id,c.container_directory);assert matched and augmented[:-1]==command[:-1] and augmented[-1].endswith(command[-1]);prefix=augmented[-1][:-len(command[-1])];assert ('PYTHONDONTWRITEBYTECODE=1 ' in prefix)==(mode=='disabled')
    unit_command=prefix+'python /tmp/bytecode-PG-harness.py '+run_id+' '+variant+' '+mode
    result=subprocess.run(['kubectl','exec','-n',ns,pod,'-c',role,'--','su','-','postgres','-c',unit_command],capture_output=True,timeout=30);assert len(result.stdout)<=65536 and len(result.stderr)<=65536;case.update(exec_exit=result.returncode,stdout_utf8=result.stdout.decode(),stderr_utf8=result.stderr.decode(),factory_derived_environment_prefix=prefix);marker=b'CRG_RECEIVER_HARNESS ';found=[json.loads(line[len(marker):]) for line in result.stdout.splitlines() if line.startswith(marker)];case['startup']=found[0] if len(found)==1 else None;c.stop();raw=c.raw();case['annotation_utf8']=raw.decode();case['annotation_sha256']=sha(raw);case['annotations']=c.annotations();before=[]
    for name in sorted(os.listdir(c.directory_fd)):
     st=os.stat(name,dir_fd=c.directory_fd,follow_symlinks=False);before.append({'name':name,'bytes':st.st_size,'type':stat.S_IFMT(st.st_mode),'owned_by_receiver':name in c.owned})
    case['entries_before_cleanup']=before;error=None
    try:c.cleanup()
    except receiver.Rejected as e:error=str(e)
    case['cleanup_error']=error;status=c.status();case['channel']=status
    accepted=result.returncode==0 and not result.stderr and len(found)==1 and found[0]['phase']=='passed' and found[0]['Python']=='2.7.5' and found[0]['status']['source_sha256']==f['source_sha256']['sitecustomize.py'] and found[0]['private_unit_folder_cleaned'] and found[0]['original_native_SHA_unchanged'] and found[0]['status']['dont_write_bytecode']==(mode=='disabled') and len(case['annotations'])==(1 if variant=='normal' else 0) and status['stopped'] and status['reader_closed'] and not status['thread_alive'] and status['directory_fd_closed'] and status['parent_fd_closed'] and not status['incomplete']
    if mode=='default':accepted=accepted and error=='UNEXPECTED_CHANNEL_CONTENTS' and not status['cleaned'] and any(v['name']=='sitecustomize.pyc' and not v['owned_by_receiver'] for v in before);case['negative_unregistered_pyc_left_for_disposable_pod_teardown']=True
    else:accepted=accepted and error is None and status['cleaned'] and {v['name'] for v in before}==set(c.owned)
    if variant=='normal':a=case['annotations'][0];accepted=accepted and a['run_id']==run_id and a['iteration']==0 and a['local_port']>0 and a['server_port']==8090 and a['headers_returned'] and a['socket_timeout_seconds']==4 and 'success' not in a
   except Exception as e:case.update(error_class=type(e).__name__,error=str(e),traceback=traceback.format_exc())
   finally:
    try:
     c.stop()
     if c.directory_fd is not None:c.cleanup()
    except Exception as e:case.update(final_cleanup_error=str(e));accepted=False
    case['passed']=bool(accepted);case['final_channel']=c.status();save()
   check(role+'-'+mode+'-'+variant+'-actual-Python2-startup-and-strict-cleanup',accepted,strict=False)
  run(['kubectl','delete','pod',pod,'-n',ns,'--wait=true','--timeout=45s'],timeout=50);deadline=time.monotonic()+5
  while time.monotonic()<deadline and (not absent(identity) or group.exists() or group.parent.exists()):time.sleep(.1)
  row.update(init_absent=absent(identity),own_leaf_absent=not group.exists(),own_parent_absent=not group.parent.exists());check(role+'-original-PID1-and-leaf-parent-gone',row['init_absent'] and row['own_leaf_absent'] and row['own_parent_absent'])
 report['phase']='passed' if all(v['passed'] for v in report['checks']) else 'failed'
except BaseException as e:report.update(phase='failed',error_class=type(e).__name__,error=str(e),traceback=traceback.format_exc())
finally:
 try:
  if created:
   meta=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout);assert meta['metadata']['uid']==namespace_uid and meta['metadata']['labels']['managed-by']=='crg-vendor-test' and meta['metadata']['labels']['crg-unit-run']=='bytecode943';run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=90s'],timeout=100);report['namespace_absent']=not run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json']).stdout.strip();check('own-namespace-gone',report['namespace_absent'])
 except BaseException as e:report.update(phase='failed',cleanup_error_class=type(e).__name__,cleanup_error=str(e))
 report['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();(w/'exit.json').write_text(json.dumps({'exit':0 if report['phase']=='passed' else 1}));print(json.dumps({'phase':report['phase'],'checks':len(report['checks']),'error':report.get('error')}))
