"""Predeclared read-only assertions for one disposable policy migration.

Expected control values and journal originals come from the runtime before the
business gate, never from values observed after an upgrade. No kernel writes.
"""
import copy,json,re

FILES=('cpu.max','memory.max','io.max','pids.max','cpu.weight','io.weight','memory.high','memory.swap.max')
CPU='720000 100000'
TARGET='20001980416'
HARD='21474836480'
IO='rbps=67108864 wbps=67108864 riops=4096 wiops=4096'
UNLIMITED_IO='rbps=max wbps=max riops=max wiops=max'
ALIAS='legacy limits.memory_max is interpreted as a memory.high target; use limits.memory_high; no new memory.max hard limit'

def need(value,reason):
    if not value:raise AssertionError(reason)

def keyed(settings):
    result={}
    for row in settings:
        key=(row['file'],row.get('device',''));need(key not in result,'duplicate-setting');result[key]=row
    return result

class Contract:
    def __init__(self,runtime,old_plan,new_plan):
        need(set(runtime)==set(FILES),'runtime-eight-controls')
        need(runtime['cpu.max']=='800000 100000\n' and runtime['memory.max']==HARD+'\n'
             and runtime['memory.high']=='max\n' and runtime['io.max'].strip()=='','runtime-original-known-budget')
        old_env,new_env=old_plan['environment'],new_plan['environment']
        need(old_env['identity']==new_env['identity'] and old_env['cgroup']==new_env['cgroup']
             and new_env.get('cgroup_version')=='v2' and re.fullmatch('[0-9a-f]{64}',new_env['identity']), 'same-own-v2-identity')
        old,new=keyed(old_plan['settings']),keyed(new_plan['settings'])
        io=[v for k,v in old.items() if k[0]=='io.max'];need(len(io)==1,'one-resolved-device');io=io[0]
        dev=io.get('device','');need(re.fullmatch('[0-9]+:[0-9]+',dev) and re.fullmatch('[0-9a-f]{64}',io.get('device_identity','')),'stable-IO-identity')
        base={'cpu.max:':{'file':'cpu.max','value':CPU},'io.max:'+dev:dict(io)}
        need(io['value']==IO,'original-IO-budget')
        self.settings={}
        for policy,plans in [('hard',old),('high',new)]:
            file='memory.max' if policy=='hard' else 'memory.high'
            expected=[{'file':'cpu.max','value':CPU},{'file':file,'value':TARGET},dict(io)]
            need(plans==keyed(expected),'predeclared-three-settings-'+policy);self.settings[policy]=keyed(expected)
        need(not old_plan.get('warnings') and new_plan.get('warnings')==[ALIAS]
             and new_plan.get('memory_policy')=='high-reclaim-throttle','only-legacy-alias-warning')
        self.runtime=copy.deepcopy(runtime);self.controls={'original':copy.deepcopy(runtime)};self.journals={}
        metadata={'version':1,'identity':new_env['identity'],'target':new_env['cgroup']}
        for policy in ['hard','high']:
            control=copy.deepcopy(runtime);control['cpu.max']=CPU+'\n';control['io.max']=dev+' '+IO+'\n'
            file='memory.max' if policy=='hard' else 'memory.high';control[file]=TARGET+'\n';self.controls[policy]=control
            mutations=copy.deepcopy(base)
            mutations['cpu.max:'].update(original=runtime['cpu.max'].strip(),applied=CPU)
            mutations['io.max:'+dev].update(original=UNLIMITED_IO,applied=IO)
            mutations[file+':']={'file':file,'value':TARGET,'original':runtime[file].strip(),'applied':TARGET}
            self.journals[policy]=dict(metadata,mutations=mutations)
        self.empty_journal=dict(metadata,mutations={})

    def verify(self,policy,controls,journal):
        need(policy in self.journals,'known-policy')
        if not isinstance(journal,dict):journal=json.loads(journal)
        need(controls==self.controls[policy],'exact-eight-controls-'+policy)
        need(journal==self.journals[policy],'exact-journal-originals-and-ownership-'+policy)
        return journal

    def status(self,policy,value):
        need(value.get('state')==('managed' if policy=='hard' else 'degraded') and not value.get('error'),'expected-resource-state')
        plan=value['plan'];need(keyed(plan['settings'])==self.settings[policy],'status-three-settings')
        need(plan['environment']['identity']==self.journals[policy]['identity'] and plan['environment']['cgroup']==self.journals[policy]['target'],'status-own-identity')
        need(value.get('configuration',{}).get('state')=='accepted','accepted-config')
        need(plan.get('warnings',[])==([] if policy=='hard' else [ALIAS]),'only-expected-warning')
        if policy=='high':need(plan.get('memory_policy')=='high-reclaim-throttle','high-policy')
        wanted={row['file'] for row in self.settings[policy].values()};seen=set()
        for row in value['items']:
            if row['file'] in wanted:
                need(row['state']=='applied' and row['file'] not in seen,'applied-unique-dimension');seen.add(row['file'])
            else:
                need(row['file']==('memory.high' if policy=='hard' else 'memory.max') and row['state']=='restored','only-policy-transition-restoration')
        need(seen==wanted,'all-three-dimensions-applied')
