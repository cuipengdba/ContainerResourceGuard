"""Read-only predeclared manual-high invariants for actual preview4/5 programs."""
import copy,json,re
FILES=('cpu.max','memory.max','io.max','pids.max','cpu.weight','io.weight','memory.high','memory.swap.max')
CPU='720000 100000';HIGH='20001980416';HARD='21474836480';IO='rbps=67108864 wbps=67108864 riops=4096 wiops=4096'
def need(value,reason):
 if not value:raise AssertionError(reason)
def keyed(rows):
 result={}
 for row in rows:
  key=(row['file'],row.get('device',''));need(key not in result,'duplicate-setting');result[key]=row
 return result
class Contract:
 def __init__(self,runtime,old,new):
  need(set(runtime)==set(FILES),'eight-runtime-controls');need(runtime['cpu.max']=='800000 100000\n' and runtime['memory.max']==HARD+'\n' and runtime['memory.high']=='max\n' and runtime['io.max'].strip()=='','known-original-runtime')
  a,z=old['environment'],new['environment'];need(a['identity']==z['identity'] and a['cgroup']==z['cgroup'] and a['cgroup_version']==z['cgroup_version']=='v2' and re.fullmatch('[0-9a-f]{64}',z['identity']),'same-own-v2-identity')
  o,n=keyed(old['settings']),keyed(new['settings']);ios=[v for k,v in o.items() if k[0]=='io.max'];need(len(ios)==1,'one-device');io=ios[0];dev=io.get('device','');need(re.fullmatch('[0-9]+:[0-9]+',dev) and re.fullmatch('[0-9a-f]{64}',io.get('device_identity','')) and io['value']==IO,'same-known-device-budget')
  self.settings=keyed([{'file':'cpu.max','value':CPU},{'file':'memory.high','value':HIGH},dict(io)]);need(o==n==self.settings,'both-published-programs-same-three-manual-high-settings')
  for p in [old,new]:need(p['resource_mode']=='manual' and p['memory_policy']=='high-reclaim-throttle' and not p.get('warnings'),'canonical-manual-without-alias-warning')
  self.runtime=copy.deepcopy(runtime);self.controls=copy.deepcopy(runtime);self.controls.update({'cpu.max':CPU+'\n','memory.high':HIGH+'\n','io.max':dev+' '+IO+'\n'})
  metadata={'version':1,'identity':z['identity'],'target':z['cgroup']};mutations={}
  for row in self.settings.values():
   v=copy.deepcopy(row);file=v['file'];key=file+':'+v.get('device','');original='rbps=max wbps=max riops=max wiops=max' if file=='io.max' else runtime[file].strip();v.update(original=original,applied=v['value']);mutations[key]=v
  self.journal=dict(metadata,mutations=mutations);self.empty_journal=dict(metadata,mutations={})
 def verify(self,controls,journal):
  if not isinstance(journal,dict):journal=json.loads(journal)
  need(controls==self.controls,'exact-eight-active-controls');need(journal==self.journal,'exact-predeclared-journal-and-originals');return journal
 def status(self,status):
  need(status['state']=='managed' and not status.get('error') and status['configuration']['state']=='accepted' and status.get('automatic_io') is None,'managed-canonical-manual')
  plan=status['plan'];need(keyed(plan['settings'])==self.settings and plan['resource_mode']=='manual' and plan['memory_policy']=='high-reclaim-throttle' and not plan.get('warnings'),'same-three-high-plan')
  need(plan['environment']['identity']==self.journal['identity'] and plan['environment']['cgroup']==self.journal['target'],'same-status-identity');need(len(status['items'])==3 and keyed([{k:v for k,v in row.items() if k in ['file','value','device','device_identity']} for row in status['items']])==self.settings and all(row['state']=='applied' for row in status['items']),'three-applied-controls')
