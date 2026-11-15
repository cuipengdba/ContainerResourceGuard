"""Read-only assertions for the fixed default20 public4/5 migration fixture.

No writes, calibration or process management. Does not infer expected quotas from
the program's plan. Scope: one confirmed device, known 8CPU/20GiB runtime with
unconstrained ancestors; the native driver must establish these prerequisites.
"""
import math,re,statistics
FILES=('cpu.max','memory.max','memory.high','io.max','pids.max','cpu.weight','io.weight','memory.swap.max')
AXES=('rbps','wbps','riops','wiops')
def need(ok,reason):
 if not ok:raise AssertionError(reason)
def axes(text,device=None):
 lines=[v.split() for v in text.splitlines() if v.strip()]
 if device is not None:
  need(all(re.fullmatch(r'\d+:\d+',v[0]) for v in lines),'io-device-lines');lines=[v[1:] for v in lines if v[0]==device]
 need(len(lines)<=1,'duplicate-io-line');result={k:'max' for k in AXES}
 if lines:
  seen=set()
  for token in lines[0]:
   k,sep,v=token.partition('=');need(sep and k in AXES and k not in seen and (v=='max' or v.isdigit() and int(v)>0),'valid-unique-io-axes');seen.add(k);result[k]=v
 return result
def settings(plan):
 out={}
 for row in plan['settings']:
  need(row['file'] not in out,'duplicate-resource-setting');out[row['file']]=row
 need(set(out)=={'cpu.max','memory.high','io.max'},'exactly-three-resources');return out
class Contract:
 def __init__(self,runtime,profile,host_cpus,host_mem,page):
  need(set(runtime)==set(FILES),'eight-runtime-controls');self.runtime={k:v.strip() for k,v in runtime.items()}
  need(self.runtime['cpu.max']=='800000 100000' and self.runtime['memory.max']=='21474836480' and self.runtime['memory.high']=='max','declared-runtime-budget')
  need(isinstance(host_cpus,int) and host_cpus>0 and isinstance(host_mem,int) and host_mem>0 and page>=4096 and page&(page-1)==0,'trusted-host-capacity-and-page')
  need(profile['version']==2 and len(profile['devices'])==1,'single-real-v2-profile');d=profile['devices'][0];self.device=d['device'];self.device_identity=d['identity'];need(re.fullmatch(r'\d+:\d+',self.device) and re.fullmatch('[0-9a-f]{64}',self.device_identity),'known-device-identity')
  need(len(d['measurements'])==3,'three-real-samples')
  for key in ['read_bps','write_bps','read_iops','write_iops']:
   values=[v[key] for v in d['measurements']];need(all(type(v) is int and v>0 for v in values) and d[key]==statistics.median(values),'positive-median-'+key)
  self.baseline=axes(self.runtime['io.max'],self.device);need(all(self.baseline[k]=='max' for k in ['rbps','wbps']),'fixture-unlimited-baseline-bandwidth')
  self.cpu=str(int(min(host_cpus*.2,8)*100000))+' 100000';self.high=str(min(math.floor(host_mem*.2)//page*page,21474836480));self.old_io={axis:str(math.floor(d[key]*.2)) for axis,key in zip(AXES,['read_bps','write_bps','read_iops','write_iops'])};need(all(int(v)>0 for v in self.old_io.values()),'old-four-axis-profile-eligible')
  self.new_io=dict(self.old_io,riops=self.baseline['riops'],wiops=self.baseline['wiops'])
 def controls(self,version):
  io=self.old_io if version==4 else self.new_io;need(version in [4,5],'published-policy-version');out=dict(self.runtime);out.update({'cpu.max':self.cpu,'memory.high':self.high,'io.max':self.device+' '+' '.join(k+'='+io[k] for k in AXES)});return out
 def verify(self,status,actual,journal,version):
  need(status['state']=='managed' and not status.get('error'),'managed-status');p=status['plan'];env=p['environment'];need(env['cgroup_version']=='v2' and re.fullmatch('[0-9a-f]{64}',env['identity']),'own-v2-identity');need(p['resource_mode']=='percent' and p['percentages']=={'cpu_percent':20,'memory_percent':20,'io_percent':20} and p['memory_policy']=='high-reclaim-throttle','three-default-percentages')
  expected=self.controls(version);normal={k:v.strip() for k,v in actual.items()};need(set(normal)==set(FILES),'eight-actual-controls');need(all(normal[k]==expected[k] for k in FILES if k!='io.max') and axes(normal['io.max'],self.device)==axes(expected['io.max'],self.device),'independent-quota-readback')
  s=settings(p);need(s['cpu.max']['value']==self.cpu and s['memory.high']['value']==self.high and s['io.max']['device']==self.device and s['io.max']['device_identity']==self.device_identity and axes(s['io.max']['value'])==(self.old_io if version==4 else self.new_io),'independent-plan')
  need(journal['version']==1 and journal['identity']==env['identity'] and journal['target']==env['cgroup'],'same-owned-journal-identity');m=journal['mutations'];need(set(m)=={'cpu.max:','memory.high:','io.max:'+self.device},'three-owned-mutations')
  for key,original in [('cpu.max:',self.runtime['cpu.max']),('memory.high:',self.runtime['memory.high'])]:need(m[key]['original']==original and m[key]['applied']==s[m[key]['file']]['value'] and not m[key].get('pending'),'owned-original-'+key)
  row=m['io.max:'+self.device];need(row['device_identity']==self.device_identity and axes(row['original'])==self.baseline and axes(row['applied'])==(self.old_io if version==4 else self.new_io) and not row.get('pending'),'owned-device-original-and-applied')
  if version==5:need(p['io_policy'].startswith('calibrated-bandwidth'),'bandwidth-only-policy')
