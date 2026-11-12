"""Pure assertions: no container, cgroup, database or original data access."""
import copy,importlib.util,json,pathlib
p=pathlib.Path(__file__).with_name('vendor-memory-policy-maintenance-contract.py')
spec=importlib.util.spec_from_file_location('policy_contract',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
runtime={'cpu.max':'800000 100000\n','memory.max':m.HARD+'\n','io.max':'','pids.max':'max\n','cpu.weight':'100\n','io.weight':'default 100\n','memory.high':'max\n','memory.swap.max':'0\n'}
env={'identity':'a'*64,'cgroup':'/sys/fs/cgroup/own-fixture.scope','cgroup_version':'v2'}
io={'file':'io.max','device':'253:0','device_identity':'b'*64,'value':m.IO}
old={'environment':dict(env),'settings':[{'file':'cpu.max','value':m.CPU},{'file':'memory.max','value':m.TARGET},io]}
new=copy.deepcopy(old);new['settings'][1]['file']='memory.high';new['warnings']=[m.ALIAS];new['memory_policy']='high-reclaim-throttle'
c=m.Contract(runtime,old,new);checks=[]
def record(name):checks.append({'name':name,'passed':True})
def rejects(name,operation):
    try:operation()
    except AssertionError:record(name);return
    raise AssertionError('accepted tampering: '+name)
for policy in ['hard','high']:
    c.verify(policy,c.controls[policy],c.journals[policy]);record('predeclared-valid-'+policy)
    value={'state':'managed' if policy=='hard' else 'degraded','plan':copy.deepcopy(old if policy=='hard' else new),'configuration':{'state':'accepted'},'items':[dict(v,state='applied') for v in c.settings[policy].values()]}
    c.status(policy,value);record('predeclared-status-'+policy)
    for field,replacement in [('identity','foreign'),('target','/other'),('version',2)]:
        bad=copy.deepcopy(c.journals[policy]);bad[field]=replacement;rejects(policy+'-foreign-'+field,lambda:c.verify(policy,c.controls[policy],bad))
    for field,replacement in [('original','max'),('applied','1 100000'),('pending','1 100000'),('conflict',True)]:
        bad=copy.deepcopy(c.journals[policy]);bad['mutations']['cpu.max:'][field]=replacement;rejects(policy+'-journal-'+field,lambda:c.verify(policy,c.controls[policy],bad))
    bad=copy.deepcopy(c.journals[policy]);bad['mutations']['pids.max:']={'file':'pids.max','value':'5','applied':'5','original':'max'};rejects(policy+'-extra-resource',lambda:c.verify(policy,c.controls[policy],bad))
    for file in ['cpu.weight','memory.max','memory.high','io.max']:
        bad=dict(c.controls[policy]);bad[file]='different\n';rejects(policy+'-changed-'+file,lambda:c.verify(policy,bad,c.journals[policy]))
    bad=copy.deepcopy(value);bad['plan']['warnings']=['unrelated failure'];rejects(policy+'-unknown-warning',lambda:c.status(policy,bad))
    bad=copy.deepcopy(value);bad['items'][0]['state']='skipped';rejects(policy+'-partial-dimension',lambda:c.status(policy,bad))
rejects('stale-hard-journal-with-high-controls',lambda:c.verify('high',c.controls['high'],c.journals['hard']))
bad=copy.deepcopy(runtime);bad['memory.high']='1024\n';rejects('unreviewed-existing-high',lambda:m.Contract(bad,old,new))
bad=copy.deepcopy(new);bad['settings'].append(dict(io));rejects('duplicate-settings',lambda:m.Contract(runtime,old,bad))
print(json.dumps({'phase':'passed','checks':checks,'count':len(checks),'scope':'pure policy migration contract; no runtime acceptance'}))
