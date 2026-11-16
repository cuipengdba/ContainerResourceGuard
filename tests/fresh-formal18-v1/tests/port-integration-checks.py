"""Fault/AST qualification; does not claim a live vendor-Pod engine cycle."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import shlex
import types


def qualify(folder):
    folder=Path(folder);spec=importlib.util.spec_from_file_location('port_diagnostics',folder/'vendor-port-diagnostics.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);checks=[]
    def check(name,ok):
        assert ok,name
        checks.append({'name':name,'passed':True})
    meta={'metadata':{'namespace':'crg-vendor-lab-qualification','name':'dbs-business','uid':'12345678-1234-1234-1234-123456789abc','labels':{'managed-by':'crg-vendor-test'}},'spec':{},'status':{'containerStatuses':[{'name':'dbs','containerID':'containerd://'+'a'*64,'state':{'running':{'startedAt':'irrelevant'}}}]}}
    expected={'pod_uid':meta['metadata']['uid'],'container_id':'a'*64};check('admit-explicit-isolated-Pod-metadata',module._pod_identity(meta,'crg-vendor-lab-qualification','dbs')==expected)
    for name,edit in [('wrong-namespace',lambda m:m['metadata'].update(namespace='other')),('wrong-name',lambda m:m['metadata'].update(name='other')),('wrong-label',lambda m:m['metadata']['labels'].update({'managed-by':'other'})),('host-net',lambda m:m['spec'].update(hostNetwork=True)),('host-pid',lambda m:m['spec'].update(hostPID=True)),('host-ipc',lambda m:m['spec'].update(hostIPC=True)),('bad-UID',lambda m:m['metadata'].update(uid='missing')),('bad-runtime',lambda m:m['status']['containerStatuses'][0].update(containerID='docker://'+'a'*64)),('not-running',lambda m:m['status']['containerStatuses'][0].update(state={'terminated':{}})),('duplicate-role',lambda m:m['status']['containerStatuses'].append(copy.deepcopy(m['status']['containerStatuses'][0])))]:
        value=copy.deepcopy(meta);edit(value)
        try:module._pod_identity(value,'crg-vendor-lab-qualification','dbs')
        except ValueError:check('deny-'+name,True)
        else:raise AssertionError(name)
    engine=ast.parse((folder/'vendor-engine-smoke.py').read_bytes());nodes=[n for n in engine.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in ['EngineInterrupted','prepare_port_capture']];assert len(nodes)==2
    testmodule=types.ModuleType('qualified_engine_diagnostic_mock');testmodule.begin=lambda *a:types.SimpleNamespace(snapshot=lambda stage:{'stage':stage,'phase':'complete','issues':[]});loader=types.SimpleNamespace(exec_module=lambda module:None);fakeutil=types.SimpleNamespace(spec_from_file_location=lambda *a:types.SimpleNamespace(loader=loader),module_from_spec=lambda spec:testmodule);saved=[]
    env={'pathlib':__import__('pathlib'),'importlib':types.SimpleNamespace(util=fakeutil),'__file__':str(folder/'vendor-engine-smoke.py'),'ns':'crg-vendor-lab-qualification','save':lambda:saved.append(True)};exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual-engine-helpers','exec'),env);Interrupted=env['EngineInterrupted']
    session=module.Session.__new__(module.Session);session.fixture=expected;session.namespace='crg-vendor-lab-qualification';session.role='dbs';session.namespace_uid='known';session.target={'pid':123};called=[];session.collector=types.SimpleNamespace(collect=lambda *a:called.append(a) or {'phase':'complete','listeners':[],'issues':[]});session._matches=lambda:False
    value=session.snapshot('guard-test');check('changed-fixture-never-scans-processes',value['phase']=='partial' and not called and value['issues']==['fixture-identity-changed-no-scan'])
    session._matches=lambda:True;value=session.snapshot('known-test');check('matching-fixture-uses-only-temporary-PG-ports',value['phase']=='complete' and called==[(session.target,[55432,55433])])
    def fail(error):raise error
    session._matches=lambda:fail(TimeoutError('private-error-detail-must-not-leak'));value=session.snapshot('timeout-test');check('ordinary-diagnostic-timeout-retains-partial-without-error-message',value['phase']=='partial' and value['issues']==['diagnostic-unavailable-TimeoutError'] and 'private-error-detail' not in json.dumps(value))
    interrupted=Interrupted('engine fixture interrupted; attempting temporary-instance cleanup');session._matches=lambda:fail(interrupted)
    try:session.snapshot('signal-test')
    except Interrupted as error:check('snapshot-propagates-exact-engine-stop-request',error is interrupted)
    else:raise AssertionError('stop swallowed')
    original=module.Session
    for error,title in [(TimeoutError('private-detail'),'ordinary-admission-failure'),(interrupted,'stop-during-admission')]:
        module.Session=lambda *a:fail(error)
        try:
            try:value=module.begin('unused','unused',{})
            except Interrupted as actual:check(title+'-propagates',actual is interrupted)
            else:check(title+'-becomes-unavailable',value.snapshot('start')['phase']=='partial' and 'private-detail' not in json.dumps(value.snapshot('start')))
        finally:module.Session=original
    item={};capture=env['prepare_port_capture']('dbs',meta,item);capture('normal');check('actual-engine-helper-appends-event-and-saves',item['port_diagnostics']==[{'stage':'normal','phase':'complete','issues':[]}] and bool(saved))
    testmodule.begin=lambda *a:fail(OSError('private-detail'));item={};capture=env['prepare_port_capture']('dbs',meta,item);capture('load-fault');check('engine-module-or-admission-fault-does-not-gate-business',item['port_diagnostics'][0]['phase']=='partial' and 'private-detail' not in json.dumps(item))
    testmodule.begin=lambda *a:types.SimpleNamespace(snapshot=lambda stage:fail(RuntimeError('private-detail')));item={};capture=env['prepare_port_capture']('dbs',meta,item);capture('read-fault');check('engine-capture-fault-does-not-gate-business',item['port_diagnostics'][0]['phase']=='partial' and 'private-detail' not in json.dumps(item))
    env['save']=lambda:fail(OSError('read-only-report'));capture('save-fault');check('diagnostic-save-failure-retains-original-execution',item['port_diagnostic_save_unavailable']);env['save']=lambda:None
    testmodule.begin=lambda *a:types.SimpleNamespace(snapshot=lambda stage:fail(interrupted));capture=env['prepare_port_capture']('dbs',meta,{})
    try:capture('stop-during-capture')
    except Interrupted as actual:check('actual-engine-capture-propagates-exact-stop',actual is interrupted)
    else:raise AssertionError('helper swallowed stop')
    # Execute the actual inserted before/try/after nodes, not a replacement
    # implementation; the business command is intentionally a fault stub.
    for which in ['standby','restore']:
        selected=[]
        for parent in ast.walk(engine):
            for field in ['body','orelse','finalbody']:
                body=getattr(parent,field,None)
                if not isinstance(body,list):continue
                for index,node in enumerate(body):
                    if isinstance(node,ast.Try) and len(node.body)==1 and isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Call):
                        call=node.body[0].value
                        if isinstance(call.func,ast.Name) and call.func.id=='ex' and any(k.arg=='log' and isinstance(k.value,ast.Constant) and k.value.value==which+'-start.txt' for k in call.keywords):selected.append(body[index-1:index+2])
        assert len(selected)==1
        program=compile(ast.Module(body=selected[0],type_ignores=[]),'actual-'+which+'-start','exec');business_error=RuntimeError('original-business-start-failure');commands=[]
        for diagnostic_fails in [False,True]:
            testmodule.begin=lambda *a:types.SimpleNamespace(snapshot=lambda stage:fail(TimeoutError('diagnostic-detail')) if diagnostic_fails else {'stage':stage,'phase':'complete','issues':[]});item={};capture=env['prepare_port_capture']('dbs',meta,item)
            def ex(*a,**k):commands.append((a,k));raise business_error
            scope=dict(ex=ex,capture_ports=capture,role='dbs',bin='/bin/',root='/qualified/root',standby='/qualified/standby',restore='/qualified/restore',opts='unchanged',shlex=shlex)
            try:exec(program,scope)
            except RuntimeError as actual:check(which+'-original-error-preserved-with-diagnostic-'+('failure' if diagnostic_fails else 'success'),actual is business_error and [v['stage'] for v in item['port_diagnostics']]==['before-'+which+'-start',which+'-start-failed'])
            else:raise AssertionError('business error swallowed')
        check(which+'-unchanged-pgctl-start-timeout',all(k['timeout']==90 and '-w -t 60 start' in a[1] for a,k in commands))
    return {'schema':'crg-vendor-port-integration-fault-qualification-v1','phase':'passed','checks':checks,'count':len(checks),'scope':'Pure metadata, injected faults and execution of actual engine AST nodes on Linux host; no live vendor Pod or business cycle claimed.','live_vendor_engine_accepted':False,'new_long_test_launched':False}


if __name__=='__main__':
    import sys
    print(json.dumps(qualify(sys.argv[1])))
