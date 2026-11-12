from pathlib import Path
import datetime,hashlib,json,os,subprocess,time,traceback

w=Path(__file__).parent;ns='crg-vendor-lab-transport855-20261112';sha=lambda raw:hashlib.sha256(raw).hexdigest();created=False;namespace_uid=None;pods={}
pins={'dbs':'sha256:25825bc9f1e9635075f97bedcee37bebb409821cc3c0084ec8ee2a07588cd3b5','hisdbs':'sha256:b772e2bcd0c9d5b8b0896c6efe972d92e76280c0c183d317ebca75df2ca8c39f'}
f=json.loads((w/'manifest.json').read_text());report={'schema':'crg-private-fifo-startup-qualification-v1','phase':'running','checks':[],'roles':{},'source_sha256':f['source_sha256'],'original_vendor_services_or_workload_started':False,'namespace':ns}
def ident(pid):
 fields=Path('/proc',str(pid),'stat').read_bytes().rsplit(b')',1)[1].split();return {'pid':pid,'start_ticks':int(fields[19])}
(w/'worker.json').write_text(json.dumps(ident(os.getpid())))
def run(args,data=None,timeout=30):
 r=subprocess.run(args,input=data,capture_output=True,timeout=timeout)
 if r.returncode:raise RuntimeError('owned unit command failed exit='+str(r.returncode))
 assert len(r.stdout)<=65536 and len(r.stderr)<=65536
 return r
def create(value):run(['kubectl','create','-f','-'],json.dumps(value).encode())
def check(name,passed):
 report['checks'].append({'name':name,'passed':bool(passed)})
 if not passed:raise AssertionError(name)
def save():(w/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
def absent(v):
 try:return ident(v['pid'])['start_ticks']!=v['start_ticks']
 except (FileNotFoundError,ProcessLookupError):return True
try:
 for name,want in f['source_sha256'].items():assert sha((w/name).read_bytes())==want
 check('all-frozen-Python-sources-match',True)
 result=run(['python3',str(w/'transport-unit.py'),str(w/'sitecustomize.py')]);assert not result.stderr;report['host_unit']=json.loads(result.stdout)
 check('host-nine-units-include-full-pipe-and-exact-business-exceptions',report['host_unit']['phase']=='passed' and len(report['host_unit']['cases'])==9)
 result=run(['python3',str(w/'proc-activation-unit.py'),str(w/'sitecustomize.py')]);assert not result.stderr;report['host_proc_unit']=json.loads(result.stdout)
 check('host-self-proc-launch-parser19',report['host_proc_unit']['phase']=='passed' and len(report['host_proc_unit']['cases'])==19)
 result=run(['python3',str(w/'fifo-unit.py'),str(w/'sitecustomize.py')]);assert not result.stderr;report['host_fifo_unit']=json.loads(result.stdout)
 check('host-private-FIFO13',report['host_fifo_unit']['phase']=='passed' and len(report['host_fifo_unit']['cases'])==13)
 current=run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json']);assert not current.stdout.strip()
 create({'apiVersion':'v1','kind':'Namespace','metadata':{'name':ns,'labels':{'managed-by':'crg-vendor-test','crg-unit-run':'transport855'}}});created=True
 namespace_uid=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout)['metadata']['uid'];report['namespace_uid']=namespace_uid
 images=json.loads(Path('/var/tmp/crg-business-20261110/vendor-import.json').read_text())['images']
 for role in ['dbs','hisdbs']:
  image=images[role]['tag'];inspected=json.loads(run(['crictl','inspecti',image]).stdout);image_id=inspected['status']['id']
  check(role+'-uses-existing-original-image-without-pull',image_id==pins[role])
  pod=role+'-transport-unit';create({'apiVersion':'v1','kind':'Pod','metadata':{'name':pod,'namespace':ns,'labels':{'managed-by':'crg-vendor-test','crg-unit-run':'transport855'}},'spec':{'restartPolicy':'Never','terminationGracePeriodSeconds':2,'containers':[{'name':role,'image':image,'imagePullPolicy':'Never','command':['/bin/sh','-c','exec sleep 180'],'securityContext':{'runAsUser':0,'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL'],'add':['SETUID','SETGID']}}}]}})
  run(['kubectl','wait','-n',ns,'--for=condition=Ready','pod/'+pod,'--timeout=90s'],timeout=100)
  meta=json.loads(run(['kubectl','get','pod',pod,'-n',ns,'-o','json']).stdout);cid=meta['status']['containerStatuses'][0]['containerID'].split('://')[1];init=json.loads(run(['crictl','inspect',cid]).stdout)['info']['pid'];group=Path('/sys/fs/cgroup')/Path('/proc',str(init),'cgroup').read_text().strip()[3:].lstrip('/')
  assert group.name=='cri-containerd-'+cid+'.scope';row={'image_id':image_id,'pod_uid':meta['metadata']['uid'],'container_id':cid,'init':ident(init),'group':str(group)};pods[role]=row;report['roles'][role]=row;save()
  for name in ['sitecustomize.py','transport-unit.py','proc-activation-unit.py','startup-harness.py','old-transport.py','new-transport.py','frozen-native.py','fifo-transport.py','fifo-unit.py','fifo-startup-wrapper.py','fifo-startup-harness.py']:
   data=(w/name).read_bytes();code="import os,sys;p='/tmp/"+name+"';f=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o444);s=os.fdopen(f,'wb');s.write(sys.stdin.read());s.close()"
   run(['kubectl','exec','-i','-n',ns,pod,'-c',role,'--','python','-c',code],data)
  result=run(['kubectl','exec','-n',ns,pod,'-c',role,'--','python','/tmp/transport-unit.py','/tmp/sitecustomize.py']);assert not result.stderr;row['unit']=json.loads(result.stdout)
  check(role+'-original-Python27-nine-units-retain-payload-timeout-and-body-error',row['unit']['phase']=='passed' and row['unit']['Python']=='2.7.5' and len(row['unit']['cases'])==9 and row['unit']['source_sha256']==f['source_sha256']['sitecustomize.py'] and row['unit']['headers_return_not_business_success'])
  result=run(['kubectl','exec','-n',ns,pod,'-c',role,'--','python','/tmp/proc-activation-unit.py','/tmp/sitecustomize.py']);assert not result.stderr;row['proc_unit']=json.loads(result.stdout)
  check(role+'-original-Python27-self-proc-parser19',row['proc_unit']['phase']=='passed' and len(row['proc_unit']['cases'])==19)
  result=run(['kubectl','exec','-n',ns,pod,'-c',role,'--','python','/tmp/startup-harness.py']);row['startup']=json.loads(result.stdout);row['startup_stderr_utf8']=result.stderr.decode();save()
  original_cases=row['startup']['cases'];check(role+'-prior-two-startup-failures-reproduced-not-regraded',row['startup']['phase']=='failed' and original_cases[0]['status']['activation_error_class']=='AttributeError' and original_cases[1]['status']['activation_errno']==13 and all(v['child_exit']==0 for v in original_cases))
  result=run(['kubectl','exec','-n',ns,pod,'-c',role,'--','su','-','postgres','-c','PYTHONDONTWRITEBYTECODE=1 python /tmp/fifo-unit.py /tmp/fifo-transport.py']);assert not result.stderr;row['fifo_unit']=json.loads(result.stdout)
  check(role+'-original-Python27-postgres-private-FIFO13',row['fifo_unit']['phase']=='passed' and len(row['fifo_unit']['cases'])==13 and row['fifo_unit']['Python']=='2.7.5')
  result=subprocess.run(['kubectl','exec','-n',ns,pod,'-c',role,'--','su','-','postgres','-c','PYTHONDONTWRITEBYTECODE=1 python /tmp/fifo-startup-harness.py'],capture_output=True,timeout=30);assert len(result.stdout)<=65536 and len(result.stderr)<=65536;row['fifo_startup_exit']=result.returncode;row['fifo_startup_stdout_utf8']=result.stdout.decode();row['fifo_startup_stderr_utf8']=result.stderr.decode();save()
  marker=b'CRG_FIFO_HARNESS ';found=[json.loads(line[len(marker):]) for line in result.stdout.splitlines() if line.startswith(marker)];row['fifo_startup']=found[0] if len(found)==1 else None
  accepted=result.returncode==0 and not result.stderr and len(found)==1 and found[0]['phase']=='passed' and len(found[0]['cases'])==4 and all(v['passed'] for v in found[0]['cases'])
  report['checks'].append({'name':role+'-four-actual-postgres-startups-with-real-own-HTTP-and-faults','passed':bool(accepted)});save()
  run(['kubectl','delete','pod',pod,'-n',ns,'--wait=true','--timeout=45s'],timeout=50)
  row['init_absent']=absent(row['init']);row['own_leaf_absent']=not group.exists();check(role+'-own-unit-PID1-and-leaf-independently-gone',row['init_absent'] and row['own_leaf_absent']);save()
 report['phase']='passed' if all(v['passed'] for v in report['checks']) else 'failed'
except BaseException as exc:report.update(phase='failed',error_class=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
finally:
 try:
  if created:
   meta=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout);assert meta['metadata']['uid']==namespace_uid and meta['metadata']['labels']['managed-by']=='crg-vendor-test' and meta['metadata']['labels']['crg-unit-run']=='transport855'
   run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=90s'],timeout=100)
   report['namespace_absent']=not run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json']).stdout.strip();check('own-namespace-independently-gone',report['namespace_absent'])
 except BaseException as exc:report.update(phase='failed',cleanup_error_class=type(exc).__name__)
 report['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();(w/'exit.json').write_text(json.dumps({'exit':0 if report['phase']=='passed' else 1}));print(json.dumps({'phase':report['phase'],'checks':len(report['checks']),'error':report.get('error')}))
