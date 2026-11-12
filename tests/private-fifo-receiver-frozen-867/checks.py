from pathlib import Path
import datetime,hashlib,importlib.util,json,os,subprocess,traceback

w=Path(__file__).parent;ns='crg-vendor-lab-transport867-20261112';sha=lambda raw:hashlib.sha256(raw).hexdigest();created=False;namespace_uid=None
f=json.loads((w/'manifest.json').read_text());report={'schema':'crg-private-fifo-host-receiver-qualification-v1','phase':'running','checks':[],'roles':{},'source_sha256':f['source_sha256'],'original_vendor_services_or_workload_started':False,'BPF_hooks_or_maps_created':False,'namespace':ns}
pins={'dbs':'sha256:25825bc9f1e9635075f97bedcee37bebb409821cc3c0084ec8ee2a07588cd3b5','hisdbs':'sha256:b772e2bcd0c9d5b8b0896c6efe972d92e76280c0c183d317ebca75df2ca8c39f'}
def ident(pid):
    fields=Path('/proc',str(pid),'stat').read_bytes().rsplit(b')',1)[1].split();return {'pid':pid,'start_ticks':int(fields[19])}
(w/'worker.json').write_text(json.dumps(ident(os.getpid())))
def save():(w/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
def run(args,data=None,timeout=30):
    result=subprocess.run(args,input=data,capture_output=True,timeout=timeout);assert len(result.stdout)<=65536 and len(result.stderr)<=65536
    if result.returncode:
        report['failed_command']={'args':args,'exit':result.returncode,'stdout_utf8':result.stdout.decode(),'stderr_utf8':result.stderr.decode()};save();raise RuntimeError('owned qualification command exit='+str(result.returncode))
    return result
def create(value):run(['kubectl','create','-f','-'],json.dumps(value).encode())
def check(name,passed,strict=True):
    report['checks'].append({'name':name,'passed':bool(passed)});save()
    if strict and not passed:raise AssertionError(name)
def absent(value):
    try:return ident(value['pid'])['start_ticks']!=value['start_ticks']
    except (FileNotFoundError,ProcessLookupError):return True
try:
    for name,want in f['source_sha256'].items():assert sha((w/name).read_bytes())==want
    check('all-frozen-source-SHAs-match',True)
    units=[('original-factory17',['factory-old-unit.py','factory.py','hook.py','original-core.py','actual-null-preflight.json'],17),('real-host-receiver18',['receiver-unit.py','receiver.py','sitecustomize.py'],18),('real-channel-factory-fault8',['factory-fault-unit.py','factory.py','hook.py','receiver.py','sitecustomize.py'],8)]
    report['host_units']={}
    for name,files,count in units:
        result=run(['python3',*[str(w/file) for file in files]]);assert not result.stderr;unit=json.loads(result.stdout);report['host_units'][name]=unit;check(name,unit['phase']=='passed' and len(unit['cases'])==count)
    spec=importlib.util.spec_from_file_location('receiver_runtime',w/'receiver.py');receiver=importlib.util.module_from_spec(spec);spec.loader.exec_module(receiver)
    assert not run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json']).stdout.strip()
    create({'apiVersion':'v1','kind':'Namespace','metadata':{'name':ns,'labels':{'managed-by':'crg-vendor-test','crg-unit-run':'transport867'}}});created=True
    namespace_uid=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout)['metadata']['uid'];report['namespace_uid']=namespace_uid
    images=json.loads(Path('/var/tmp/crg-business-20261110/vendor-import.json').read_text())['images']
    for role_index,role in enumerate(['dbs','hisdbs']):
        image=images[role]['tag'];image_id=json.loads(run(['crictl','inspecti',image]).stdout)['status']['id'];check(role+'-original-image-pin-without-pull',image_id==pins[role]);pod=role+'-receiver-unit'
        create({'apiVersion':'v1','kind':'Pod','metadata':{'name':pod,'namespace':ns,'labels':{'managed-by':'crg-vendor-test','crg-unit-run':'transport867'}},'spec':{'restartPolicy':'Never','terminationGracePeriodSeconds':2,'containers':[{'name':role,'image':image,'imagePullPolicy':'Never','command':['/bin/sh','-c','exec sleep 180'],'securityContext':{'runAsUser':0,'allowPrivilegeEscalation':False,'capabilities':{'drop':['ALL'],'add':['SETUID','SETGID']}}}]}})
        run(['kubectl','wait','-n',ns,'--for=condition=Ready','pod/'+pod,'--timeout=90s'],timeout=100)
        meta=json.loads(run(['kubectl','get','pod',pod,'-n',ns,'-o','json']).stdout);cid=meta['status']['containerStatuses'][0]['containerID'].split('://')[1];pid=json.loads(run(['crictl','inspect',cid]).stdout)['info']['pid'];identity=ident(pid);cgroup_raw=Path('/proc',str(pid),'cgroup').read_bytes();group=Path('/sys/fs/cgroup')/cgroup_raw.decode().strip()[3:].lstrip('/');assert group.name=='cri-containerd-'+cid+'.scope'
        uid=int(run(['kubectl','exec','-n',ns,pod,'-c',role,'--','id','-u','postgres']).stdout);gid=int(run(['kubectl','exec','-n',ns,pod,'-c',role,'--','id','-g','postgres']).stdout);assert uid==999
        row={'image_id':image_id,'pod_uid':meta['metadata']['uid'],'container_id':cid,'init':identity,'group':str(group),'postgres_uid':uid,'postgres_gid':gid,'cases':[]};report['roles'][role]=row;save()
        for name in ['receiver-PG-harness.py','receiver-usercustomize.py','frozen-native.py']:
            code="import os,sys;fd=os.open('/tmp/"+name+"',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o444);s=os.fdopen(fd,'wb');s.write(sys.stdin.read());s.close()";run(['kubectl','exec','-i','-n',ns,pod,'-c',role,'--','python','-c',code],(w/name).read_bytes())
        def same_container():return not absent(identity) and Path('/proc',str(pid),'cgroup').read_bytes()==cgroup_raw and group.exists()
        for case_index,variant in enumerate(['normal','no-reader','stopped-reader']):
            run_id=str(2026111286700+role_index*10+case_index);c=receiver.Channel(Path('/proc',str(pid),'root/tmp'),run_id,uid,gid,(w/'sitecustomize.py').read_bytes(),same_container);case={'variant':variant,'run_id':run_id};row['cases'].append(case);accepted=False
            try:
                c.prepare()
                if variant!='no-reader':c.start()
                if variant=='stopped-reader':c.stop()
                command='PYTHONDONTWRITEBYTECODE=1 python /tmp/receiver-PG-harness.py '+run_id+' '+variant
                result=subprocess.run(['kubectl','exec','-n',ns,pod,'-c',role,'--','su','-','postgres','-c',command],capture_output=True,timeout=30);assert len(result.stdout)<=65536 and len(result.stderr)<=65536;case.update(exec_exit=result.returncode,stdout_utf8=result.stdout.decode(),stderr_utf8=result.stderr.decode());save()
                marker=b'CRG_RECEIVER_HARNESS ';found=[json.loads(line[len(marker):]) for line in result.stdout.splitlines() if line.startswith(marker)];case['startup']=found[0] if len(found)==1 else None
                c.stop();raw=c.raw();case['annotation_utf8']=raw.decode();case['annotation_sha256']=sha(raw);case['annotations']=c.annotations()
                accepted=result.returncode==0 and not result.stderr and len(found)==1 and found[0]['phase']=='passed' and found[0]['Python']=='2.7.5' and found[0]['status']['source_sha256']==f['source_sha256']['sitecustomize.py'] and found[0]['private_unit_folder_cleaned'] and found[0]['original_native_SHA_unchanged'] and len(case['annotations'])==(1 if variant=='normal' else 0)
                if variant=='normal':
                    a=case['annotations'][0];accepted=accepted and a['run_id']==run_id and a['iteration']==0 and a['local_port']>0 and a['server_port']==8090 and a['headers_returned'] and a['socket_timeout_seconds']==4 and 'success' not in a
            except Exception as error:case.update(error_class=type(error).__name__,error=str(error),traceback=traceback.format_exc())
            finally:
                try:c.stop();c.cleanup()
                except Exception as error:case.update(cleanup_error_class=type(error).__name__,cleanup_error=str(error));accepted=False
                case['host_channel']=c.status();status=case['host_channel'];accepted=accepted and status['cleaned'] and status['stopped'] and status['reader_closed'] and not status['thread_alive'] and status['directory_fd_closed'] and status['parent_fd_closed'] and not status['incomplete'];case['passed']=bool(accepted);save()
            check(role+'-'+variant+'-real-host-receiver-original-postgres-startup-and-cleanup',accepted,strict=False)
        run(['kubectl','delete','pod',pod,'-n',ns,'--wait=true','--timeout=45s'],timeout=50);row['init_absent']=absent(identity);row['own_leaf_absent']=not group.exists();check(role+'-original-PID1-and-leaf-gone',row['init_absent'] and row['own_leaf_absent'])
    report['phase']='passed' if all(v['passed'] for v in report['checks']) else 'failed'
except BaseException as error:report.update(phase='failed',error_class=type(error).__name__,error=str(error),traceback=traceback.format_exc())
finally:
    try:
        if created:
            meta=json.loads(run(['kubectl','get','namespace',ns,'-o','json']).stdout);assert meta['metadata']['uid']==namespace_uid and meta['metadata']['labels']['managed-by']=='crg-vendor-test' and meta['metadata']['labels']['crg-unit-run']=='transport867'
            run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=90s'],timeout=100);report['namespace_absent']=not run(['kubectl','get','namespace',ns,'--ignore-not-found','-o','json']).stdout.strip();check('own-namespace-gone',report['namespace_absent'])
    except BaseException as error:report.update(phase='failed',cleanup_error_class=type(error).__name__,cleanup_error=str(error))
    report['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();(w/'exit.json').write_text(json.dumps({'exit':0 if report['phase']=='passed' else 1}));print(json.dumps({'phase':report['phase'],'checks':len(report['checks']),'error':report.get('error')}))
