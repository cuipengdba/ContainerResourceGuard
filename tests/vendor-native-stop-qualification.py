"""Host pidfd final flush against both original Python2 vendor images.

Only fresh emptyDir PG and mock HTTP fixtures, not original vendor business.
"""
import ast
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pathlib
import subprocess
import sys
import tarfile
import time

sys.dont_write_bytecode=True
os.umask(0o077)
assert os.environ.get('CRG_NATIVE_STOP_QUALIFICATION')=='authorized-disposable-test-node-only'
base=Path('/var/tmp/crg-memory167-tools-20261111')
root=Path('/var/tmp/crg-native220-qualification-20261111')
tools=Path('/var/tmp/crg-native220-tools-20261111')
ns='crg-vendor-lab-native220-20261111'
frozen={'payload_sha256': 'cd968467721c5a83fa9ae5ed2d293f87fb9a6901b5d7953dc9bea1bf108ead9f', 'files': {'vendor-native-session.py': 'ae53be88970f343624882cd7a11ffc5945bae469a7ad005b4c760592b08aec63', 'vendor-thread-session.py': '35f65518ce56f5b889c82041a1c45c87d9f3284ab6bd59cc39752bf78fdc8bce', 'vendor-native-diagnostics-qualification.py': 'b12a8b5ae1f0f2b105fd4c9a53cc3231a006e3ad1fe0eb1e7cfd1299c49b8e80', 'vendor-native-diagnostics-runtime.py': 'ed4040a1864efec8631cc70013da5628a66c76c76cea76104b31d02b7bad2f2d', 'vendor-soak-load-diagnostics.py': '50ea0454d17d5412a9d4085472ed89831e4408f60aa0fa0ca2dfd905a2bacb1f', 'vendor-native-diagnostics.py': '83b3f8894eea96af9dfc2c789ee54b63cd5803e9dd2218a74f6bc100934c31ab', 'vendor-native-stop-runtime.py': 'ea05714bd766eace4f938f53bd1500d5aded906489e48df07fa80aadf5866916'}}
payload=base/'native220-payload.tar'
assert not root.exists() and not tools.exists() and hashlib.sha256(payload.read_bytes()).hexdigest()==frozen['payload_sha256']
root.mkdir(mode=0o700);tools.mkdir(mode=0o700)
with tarfile.open(payload) as archive:
    members=archive.getmembers();assert len(members)==len(frozen['files']) and {m.name for m in members}==set(frozen['files'])
    for member in members:
        assert member.isfile() and '/' not in member.name and 0<member.size<65536
        raw=archive.extractfile(member).read();assert hashlib.sha256(raw).hexdigest()==frozen['files'][member.name]
        p=tools/member.name;p.write_bytes(raw);p.chmod(0o400);compile(raw,str(p),'exec')
def module(name):
    spec=importlib.util.spec_from_file_location(name,tools/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
session=module('vendor-native-session');precedence=module('vendor-thread-session')
legacy=tools/'vendor-native-diagnostics-qualification.py'
assert hashlib.sha256(legacy.read_bytes()).hexdigest()=='b12a8b5ae1f0f2b105fd4c9a53cc3231a006e3ad1fe0eb1e7cfd1299c49b8e80'
tree=ast.parse(legacy.read_bytes())
wanted=['save','run','get','create','ex','component_state','pod','deletepod']
tree.body=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in wanted
           or isinstance(node,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='pins' for v in node.targets)]
assert len(tree.body)==len(wanted)+1
exec(compile(tree,'frozen-vendor-pod-functions','exec'),globals(),globals())
prior_path=Path('/var/tmp/crg-native194-qualification-20261111/report.json')
assert hashlib.sha256(prior_path.read_bytes()).hexdigest()=='bc9897ed00032b6a6f33fb20e4631b9ba5dda3a144d9c5d5da775e3a210e4c41'
prior=json.loads(prior_path.read_bytes());assert prior['phase']=='passed' and prior['namespace_absent']
unit_path=Path('/var/tmp/crg-native219-session-checks-20261111/checks-result.json')
unit=json.loads(unit_path.read_bytes());assert unit['phase']=='passed' and len(unit['checks'])==18 and unit['selftest_only_children_all_reaped'] and unit['original_controls_unchanged']
assert unit['source_sha256']['vendor-native-session.py']==frozen['files']['vendor-native-session.py']
report={'schema':'crg-native-stop-qualification-v1','phase':'running','roles':{},'source_sha256':frozen['files'],
        'started_node_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'original_runtime_qualification_sha256':hashlib.sha256(prior_path.read_bytes()).hexdigest(),
        'host_lifecycle_qualification_sha256':hashlib.sha256(unit_path.read_bytes()).hexdigest(),
        'full600s_accepted':False,'historical_pressure_failure_resolved':False,
        'scope':'one exact native worker per fresh PG/mock HTTP pod; synthetic external failure only; not vendor business acceptance'}
uid=None;client=None;log=None;owned_groups=[]
def controls(group):
    return {name:(group/name).read_text() for name in ['cpu.max','memory.max','io.max']}
try:
    assert get('namespace',ns) is None
    create({'apiVersion':'v1','kind':'Namespace','metadata':{'name':ns,'labels':{'managed-by':'crg-vendor-test'}}})
    uid=get('namespace',ns)['metadata']['uid'];report['namespace_uid']=uid;save()
    create({'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'deny-all','namespace':ns},'spec':{'podSelector':{},'policyTypes':['Ingress','Egress']}})
    for role in ['dbs','hisdbs']:
        original=json.loads(run(['kubectl','get','pod',role+'-business','-n','crg-vendor-lab-acceptance78-20261111','-o','json']).stdout)
        assert original['metadata']['labels'].get('managed-by')=='crg-vendor-test'
        image=next(c['image'] for c in original['spec']['containers'] if c['name']==role)
        item={'components_before':component_state(role)};report['roles'][role]=item;save()
        item['pod']=pod(role,original,image,(999,998));assert item['pod']['image_id']==prior['roles'][role]['source_image_id'];save()
        current=get('pod',role+'-runtime');status=next(c for c in current['status']['containerStatuses'] if c['name']==role)
        cid=status['containerID'].split('://',1)[1];pid=json.loads(run(['crictl','inspect',cid]).stdout)['info']['pid']
        membership=Path('/proc',str(pid),'cgroup').read_text().strip();assert membership.startswith('0::/') and len(membership.splitlines())==1
        group=Path('/sys/fs/cgroup')/membership[3:].lstrip('/');assert cid in str(group) and uid!=item['pod']['pod_uid']
        owned_groups.append(group);item['cgroup']=str(group);item['controls_before']=controls(group)
        log=(root/(role+'-runtime.log')).open('xb')
        client=subprocess.Popen(['kubectl','exec','-n',ns,role+'-runtime','-c',role,'--','env','CRG_NATIVE_STOP_RUNTIME=new-emptydir-postgres-only','python','/tmp/crg-native194-tools/vendor-native-stop-runtime.py',role],stdin=subprocess.DEVNULL,stdout=log,stderr=log)
        item['runtime_client']={'pid':client.pid,'start_ticks':int(Path('/proc',str(client.pid),'stat').read_text().rsplit(')',1)[1].split()[19])};save()
        deadline=time.monotonic()+140;ready=None
        while time.monotonic()<deadline:
            assert client.poll() is None,'runtime exited before host handshake'
            p=ex(role,'cat','/tmp/crg-native220-runtime/report.json',timeout=10,check=False)
            if p.returncode==0:
                ready=json.loads(p.stdout)
                if ready['phase']=='waiting-for-host-cleanup':break
                assert ready['phase']!='failed'
            time.sleep(.25)
        assert ready and ready['phase']=='waiting-for-host-cleanup'
        record={};item['native_session']=record
        s=session.Session(group,'/tmp/crg-native194-tools/vendor-soak-load-diagnostics.py',ready['run_id'],600,frozen['files']['vendor-soak-load-diagnostics.py'],record)
        try:
            identity=s.attach();save()
            # Six measured seconds guarantee multiple actual PG/API/SQL samples.
            # This remains partial and is deliberately NOT 600s acceptance.
            time.sleep(6)
            original_error=RuntimeError('qualification-external-business-failure')
            errors=[]
            def work():raise original_error
            def finish():s.finish_after_failure(original_error,120)
            try:precedence.preserve_business_error(work,finish,lambda error:errors.append(type(error).__name__))
            except RuntimeError as error:
                assert error is original_error and not errors
                item['original_business_error_object_preserved']=True
            else:raise AssertionError('original error was hidden')
        finally:s.close();save()
        client.wait(timeout=140);item['runtime_exit']=client.returncode;client=None;log.close();log=None;save()
        value=json.loads(ex(role,'cat','/tmp/crg-native220-runtime/report.json').stdout);item['runtime']=value
        assert item['runtime_exit']==0 and value['phase']=='passed' and len(value['checks'])==8 and all(v['passed'] for v in value['checks']) and value['own_postgres_stopped'] and not value.get('fixture_emergency_kill')
        assert record['signals_sent']==1 and record['phase']=='worker-exited' and record['original_worker_exited'] and not record['forced_kill'] and not record['complete600s_accepted']
        nativepid=identity['pid'];assert not Path('/proc',str(nativepid)).exists()
        item['controls_after']=controls(group);assert item['controls_after']==item['controls_before'];save()
        deletepod(role,item['pod']['pod_uid']);item['pod']['deleted']=True
        item['components_after']=component_state(role);assert item['components_after']==item['components_before'];save()
    report['phase']='passed'
except BaseException as error:
    report.update(phase='failed',reason=type(error).__name__+':'+str(error)[:1400])
finally:
    if uid is not None:
        try:
            current=get('namespace',ns);assert current['metadata']['uid']==uid and current['metadata']['labels'].get('managed-by')=='crg-vendor-test'
            run(['kubectl','delete','namespace',ns,'--wait=true','--timeout=90s'],timeout=100)
            assert get('namespace',ns) is None;report['namespace_absent']=True
        except BaseException as error:report.update(phase='failed',cleanup_error=type(error).__name__)
    if client is not None:
        try:client.wait(timeout=10)
        except subprocess.TimeoutExpired:report.update(phase='failed',runtime_client_pending=True)
    if log is not None:log.close()
    deadline=time.monotonic()+30
    while any(p.exists() for p in owned_groups) and time.monotonic()<deadline:time.sleep(.1)
    report['all_owned_cgroups_absent']=all(not p.exists() for p in owned_groups)
    if not report['all_owned_cgroups_absent']:report['phase']='failed'
    report['ended_node_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
print(json.dumps({'phase':report['phase'],'roles':{role:{'runtime_checks':len(item.get('runtime',{}).get('checks',[])),'signals_sent':item.get('native_session',{}).get('signals_sent')} for role,item in report['roles'].items()},'reason':report.get('reason'),'namespace_absent':report.get('namespace_absent')}))
raise SystemExit(0 if report['phase']=='passed' else 1)
