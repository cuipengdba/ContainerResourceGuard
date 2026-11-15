"""Isolated fixed-source CLI contract; no multi-container product controller."""
from pathlib import Path
import copy,datetime,hashlib,json,math,os,re,time

sha=lambda raw:hashlib.sha256(raw).hexdigest()
NAMES=['initial-manual-status-human-JSON','percent50-upper-constraints','independent-percent25-29-80','invalid101-retains-generation-policy','malformed-JSON-retains-generation-policy','whitespace-explicit-reload-same-generation','missing-profile-readonly-coverage','wrong-identity-profile-readonly-coverage','uncovered-path-readonly-coverage','original-manual-effective-policy-restored','external-CPU-original-value-detected','external-CPU-value-retained-next-cycle','conflict-disable-restores-runtime-empty-journal','enable-final-single-writer-original-policy']

def keyed(rows):return {(v['file'],v.get('device','')):v for v in rows}
def cpus(text):return sum(int(v.split('-')[1])-int(v.split('-')[0])+1 if '-' in v else 1 for v in text.split(','))
def number(value):return math.inf if value=='max' else int(value)
def cpu(value):
 a,b=value.split();return math.inf if a=='max' else int(a)/int(b)
def controls(group,names):return {f:(group/f).read_text().strip() for f in names}
def equal(a,b):return a==b

class Checks:
 def __init__(self,c):
  self.c=c;self.plan=c['plan'];self.role=c['role'];self.folder=c['folder'];self.group=c['group'];self.item=c['item'];self.path=c['config_path'];self.original=c['original_config'];self.contract=c['contract'];self.runtime={k:v.strip() for k,v in self.contract.runtime.items()};self.initial={k:v.strip() for k,v in self.contract.controls.items()};self.rows=self.item.setdefault('output_matrix_checks',[]);self.views=self.item.setdefault('output_matrix_views',[]);self.commands=self.item.setdefault('output_matrix_commands',[]);self.expected=copy.deepcopy(self.initial);self.cfgstate='accepted';self.generation=1;self.phase='online';self.prepared=False;self.initial_agent=self.agents();assert len(self.initial_agent)==1
  self.source=Path(self.plan['tools'])/'tests/output-profile.json';self.profile_raw=self.source.read_bytes();assert sha(self.profile_raw)==self.plan['output_contract']['profile_sha256'];self.profile=json.loads(self.profile_raw);self.dev=self.profile['devices'][0];self.device=self.dev['device'];self.profile_path=self.path.with_name('io-profile.json');assert not self.profile_path.exists();self.reference=self.item['old_doctor']['environment'];self.basis=self.read_basis();self.item['output_independent_basis']=self.basis
  self.accepted_hash=json.loads((self.folder/'resource-state/status.json').read_bytes())['configuration']['accepted_hash'];self.initial_config_hash=self.accepted_hash;self.policy=None
 def save(self):self.c['save']()
 def agents(self):
  found=[]
  for value in (self.group/'cgroup.procs').read_text().splitlines():
   p=Path('/proc',value)
   try:
    args=(p/'cmdline').read_bytes().split(bytes([0]))
    if len(args)>1 and Path(os.fsdecode(args[0])).name=='crg' and args[1]==b'run':found.append({'pid':int(value),'start_ticks':int((p/'stat').read_bytes().rsplit(b')',1)[1].split()[19]),'sha256':sha((p/'exe').read_bytes())})
   except (FileNotFoundError,ProcessLookupError):pass
  return found
 def invariant(self,agent=True):
  assert self.c['measurement_active']();self.c['reserve']();assert self.c['ex'](self.role,'cat','/proc/1/stat').stdout.split()[21]==self.c['pid1'];assert all(int(Path('/proc',str(p),'stat').read_bytes().rsplit(b')',1)[1].split()[19])==ticks for p,ticks in self.c['cache_identity']);assert json.loads((self.folder/'cache-state/status.json').read_bytes())['action']=='enforce';assert int(dict(v.split() for v in (self.group/'memory.events').read_text().splitlines())['oom_kill'])==self.c['oom'];assert all((self.group/k).read_text().strip()==self.runtime[k] for k in self.runtime if k not in ['cpu.max','memory.high','io.max'])
  if agent:assert self.agents()==self.initial_agent
  if self.profile_path.exists():assert self.profile_path.read_bytes()==self.profile_raw and self.profile_path.stat().st_mtime_ns==self.profile_mtime
 def read_basis(self):
  online=Path('/sys/devices/system/cpu/online').read_text().strip();memory=int(next(v.split()[1] for v in Path('/proc/meminfo').read_text().splitlines() if v.startswith('MemTotal:')))*1024;assert cpus(online)==self.reference['host_online_cpus']==24 and memory==self.reference['host_memory_bytes']==66673278976;rows=[];directory=self.group
  while True:
   row={'path':str(directory)}
   for f in ['cpu.max','memory.max','memory.high','cpuset.cpus.effective']:
    p=directory/f
    if p.exists():row[f]=self.runtime[f] if directory==self.group and f in self.runtime else p.read_text().strip()
   rows.append(row)
   if directory==Path('/sys/fs/cgroup'):break
   assert Path('/sys/fs/cgroup') in directory.parents;directory=directory.parent
  return {'online':online,'host_online_cpus':cpus(online),'host_memory_bytes':memory,'page_bytes':os.sysconf('SC_PAGE_SIZE'),'ancestors_leaf_uses_predeclared_runtime':rows,'effective_cpuset':self.reference.get('effective_cpuset','')}
 def expected_percent(self,p):
  b=self.basis;desired_cpu=b['host_online_cpus']*p['cpu_percent']/100;desired_mem=int(b['host_memory_bytes']*p['memory_percent']/100)//b['page_bytes']*b['page_bytes'];n=desired_cpu;m=desired_mem
  for row in b['ancestors_leaf_uses_predeclared_runtime']:
   if 'cpu.max' in row:n=min(n,cpu(row['cpu.max']))
   for f in ['memory.max','memory.high']:
    if f in row:m=min(m,number(row[f]))
  if b['effective_cpuset']:n=min(n,cpus(b['effective_cpuset']))
  wanted=dict(self.initial);wanted.update({'cpu.max':str(int(n*100000))+' 100000','memory.high':str(int(m)),'io.max':self.device+' rbps='+str(int(self.dev['read_bps']*p['io_percent']/100))+' wbps='+str(int(self.dev['write_bps']*p['io_percent']/100))+' riops=max wiops=max'});return wanted,{'CPU':n<desired_cpu,'memory':m<desired_mem}
 def invoke(self,command,*args,config='/etc/crg/config.json'):
  self.invariant(agent=command not in ['enable','status']);began=time.time();options=['--state-dir','/tmp/containerresourceguard'] if command=='status' else ['--config',config];r=self.c['ex'](self.role,'/staging/crg',command,*options,*args,check=False,timeout=30);end=time.time();value=None
  try:value=json.loads(r.stdout)
  except ValueError:pass
  self.commands.append({'phase':self.phase,'command':command,'args':list(args),'config':None if command=='status' else config,'config_or_state_options':options,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'response':value,'started_epoch':began,'ended_epoch':end});self.save();assert r.returncode==0,(command,r.stderr);assert self.c['measurement_active']();return r,value
 def check(self,name):self.invariant();self.rows.append({'name':name,'passed':True,'phase':self.phase,'epoch':time.time()});self.save()
 def human_plan(self,p,text):
  env=p['environment'];assert env['identity']==self.reference['identity'] and env['cgroup']==str(self.group);assert 'Cgroup: '+str(self.group) in text and 'Host: '+str(env['host_online_cpus'])+' online CPUs, '+str(env['host_memory_bytes'])+' bytes memory' in text
  if p['resource_mode']=='manual':assert 'Requested: manual CPU / memory / per-device IO; omitted dimensions unmanaged' in text
  else:
   x=p['percentages'];assert ('Requested: CPU '+format(x['cpu_percent'],'.4g')+'%; memory '+format(x['memory_percent'],'.4g')+'%; calibrated read/write bandwidth '+format(x['io_percent'],'.4g')+'% (IOPS baseline retained)') in text
  for s in p['settings']:assert 'Target '+s['file']+' '+s.get('device','')+': '+s['value'] in text
  for w in p.get('warnings',[]):assert 'Warning: '+w in text
  for d in p.get('io_devices',[]):assert 'IO device '+d['profile_device']+' -> '+d.get('resolved_device','')+': '+d['state']+' ('+d['detail']+')' in text
  for d in p.get('data_paths',[]):assert 'Data path '+d['path']+' device '+d.get('device','')+': '+d['state']+' ('+d['detail']+')' in text
 def observe(self,label,conflict=False):
  persisted=self.folder/'resource-state/status.json';raw=persisted.read_bytes();mtime=persisted.stat().st_mtime_ns;_,v=self.invoke('status','--format','json');h,_=self.invoke('status','--format','human');assert raw==persisted.read_bytes() and mtime==persisted.stat().st_mtime_ns;self.human_plan(v['plan'],h.stdout);cfg=v['configuration'];assert cfg['state']==self.cfgstate and cfg['generation']==self.generation and cfg['accepted_hash']==self.accepted_hash
  assert cfg['source']=='/etc/crg/config.json' and v['writer_lock_held'] and not v.get('lock_check_error');line=re.search(r'^State: (.*?); mode: (.*?); snapshot age: (-?[0-9]+)s; writer lock held: (true|false)$',h.stdout,re.M);assert line and line[1]==v['state'] and line[2]==v['mode'] and line[4]=='true' and abs(int(line[3])-v['snapshot_age_seconds'])<=5
  assert v['state']==('degraded' if conflict or self.cfgstate=='rejected' or v['plan'].get('warnings') else 'managed');stamp=datetime.datetime.fromisoformat(v['time_utc'].replace('Z','+00:00')).timestamp();assert -2<=time.time()-stamp-v['snapshot_age_seconds']<=5;expected_items=keyed(v['plan']['settings']);assert {k[0] for k in expected_items}=={'cpu.max','memory.high','io.max'};actual=keyed(v['actual']);assert set(actual)==set(expected_items)
  for key,s in expected_items.items():
   assert s['value']==(self.initial['cpu.max'] if conflict and key[0]=='cpu.max' else self.expected[key[0]].removeprefix(self.device+' ') if key[0]=='io.max' else self.expected[key[0]]);a=actual[key];assert a['state']=='read' and a['value']==(self.expected[key[0]].removeprefix(self.device+' ') if key[0]=='io.max' else self.expected[key[0]]) and 'Actual '+key[0]+' '+key[1]+': '+a['value']+' ' in h.stdout
  for row in v['items']:assert 'Result '+row['file']+' '+row.get('device','')+': '+row['state']+' ['+row.get('reason_code','')+'] ('+row.get('detail','')+')' in h.stdout
  if conflict:assert any(x['file']=='cpu.max' and x['state']=='conflict' and x['reason_code']=='external_conflict' for x in v['items'])
  if self.cfgstate=='rejected':assert cfg.get('error')
  self.views.append({'label':label,'epoch':time.time(),'json':v,'human_stdout':h.stdout,'persisted_status_sha256':sha(raw),'persisted_status_mtime_ns':mtime,'actual_controls':controls(self.group,self.runtime),'expected_controls':copy.deepcopy(self.expected),'same_Agent':self.agents()==self.initial_agent,'field_contract':'configuration generation/hash/state/request_id/error are JSON-only; human summarizes effective plan/results, same meaning on shared fields'});self.save();return v
 def write(self,raw):
  temp=self.path.with_name('output1615.next');assert not temp.exists()
  with temp.open('xb') as stream:os.chmod(temp,0o600);stream.write(raw);stream.flush();os.fsync(stream.fileno())
  temp.replace(self.path)
 def transition(self,label,raw,expected,generation,state='accepted',policy=None):
  oldhash=self.accepted_hash;previous=json.loads((self.folder/'resource-state/status.json').read_bytes());began=time.time();self.write(raw);_,ack=self.invoke('reload');assert ack['state']=='requested';deadline=time.monotonic()+60
  while time.monotonic()<deadline:
   self.invariant();v=json.loads((self.folder/'resource-state/status.json').read_bytes());cfg=v['configuration'];actual=controls(self.group,self.runtime)
   if cfg.get('request_id')==ack['request_id'] and cfg['state']==state and cfg['generation']==generation and equal(actual,expected) and all(x['state']=='applied' and x['reason_code']=='unchanged' for x in v['items']):break
   time.sleep(.25)
  else:raise RuntimeError('original60s transition deadline: '+label)
  if generation==self.generation:assert cfg['accepted_hash']==oldhash
  else:assert generation==self.generation+1 and cfg['accepted_hash']!=oldhash
  if state=='rejected':assert v['plan']==previous['plan'] and cfg.get('error')
  self.expected=copy.deepcopy(expected);self.generation=generation;self.cfgstate=state;self.accepted_hash=cfg['accepted_hash'];self.policy=policy;self.item.setdefault('output_transitions',[]).append({'label':label,'began_epoch':began,'ended_epoch':time.time(),'request_id':ack['request_id'],'configuration':cfg,'expected_controls':copy.deepcopy(expected),'raw_config_sha256':sha(raw)});self.save();return self.observe(label)
 def config(self,p):return json.dumps(dict(p,interval_seconds=1,data_paths=['/opt/postgresql']),sort_keys=True).encode()
 def readonly(self,label,change):
  directory=self.folder/'recovery/output1615';directory.mkdir(mode=0o700,exist_ok=True);value=dict(self.policy,interval_seconds=1,data_paths=['/opt/postgresql']);value.update(change);raw=json.dumps(value).encode();p=directory/(label+'.json');p.write_bytes(raw);p.chmod(0o600);journal=self.c['statefile'].read_bytes();actual=controls(self.group,self.runtime);active=self.path.read_bytes();results=[]
  for cmd in ['doctor','preflight']:
   _,v=self.invoke(cmd,'--format','json',config='/recovery/output1615/'+p.name);h,_=self.invoke(cmd,'--format','human',config='/recovery/output1615/'+p.name);self.human_plan(v,h.stdout);results.append(v)
  assert journal==self.c['statefile'].read_bytes() and actual==controls(self.group,self.runtime) and active==self.path.read_bytes();self.item.setdefault('output_readonly_plans',[]).append({'label':label,'epoch':time.time(),'config':value,'results':results,'active_config_journal_controls_unchanged':True});self.save();return results
 def online(self):
  assert self.plan['output_contract']['cases']==NAMES;self.observe(NAMES[0]);self.check(NAMES[0])
  with self.profile_path.open('xb') as stream:os.chmod(self.profile_path,0o600);stream.write(self.profile_raw);stream.flush();os.fsync(stream.fileno())
  self.profile_mtime=self.profile_path.stat().st_mtime_ns
  p={'cpu_percent':50,'memory_percent':50,'io_percent':100};target,clamped=self.expected_percent(p);assert all(clamped.values());v=self.transition(NAMES[1],self.config(p),target,2,policy=p);assert 'CPU constrained by existing limits/cpuset' in v['plan']['warnings'] and 'memory constrained by existing limits' in v['plan']['warnings'] and v['plan']['percentages']==p;self.check(NAMES[1])
  p={'cpu_percent':25,'memory_percent':29,'io_percent':80};target,_=self.expected_percent(p);v=self.transition(NAMES[2],self.config(p),target,3,policy=p);assert v['plan']['percentages']==p;self.check(NAMES[2])
  self.transition(NAMES[3],b'{"io_percent":101}',target,3,'rejected',p);self.check(NAMES[3]);self.transition(NAMES[4],b'{',target,3,'rejected',p);self.check(NAMES[4]);self.transition(NAMES[5],b' \n'+self.config(p)+b'\n ',target,3,policy=p);self.check(NAMES[5])
  missing=self.readonly(NAMES[6],{'io_profile':'/recovery/output1615/no-profile.json','io_calibration':'off'});assert all(not any(v['file']=='io.max' for v in x['settings']) and any('IO unmanaged: profile unavailable:' in w for w in x['warnings']) for x in missing);self.check(NAMES[6])
  bad=copy.deepcopy(self.profile);bad['devices'][0]['identity']='0'*64;badpath=self.folder/'recovery/output1615/wrong-profile.json';badpath.write_bytes(json.dumps(bad).encode());badpath.chmod(0o600);badplans=self.readonly(NAMES[7],{'io_profile':'/recovery/output1615/wrong-profile.json','io_calibration':'off'});assert all(not any(v['file']=='io.max' for v in x['settings']) and any(v['state']=='unavailable' for v in x['io_devices']) for x in badplans);self.check(NAMES[7])
  uncovered=self.readonly(NAMES[8],{'data_paths':['/proc']});assert all(len(x['data_paths'])==1 and x['data_paths'][0]['path']=='/proc' and x['data_paths'][0]['state']=='unmanaged' for x in uncovered);self.check(NAMES[8]);self.transition(NAMES[9],self.original,self.initial,4);assert self.c['same']();self.check(NAMES[9])
  self.invariant();before=self.c['statefile'].read_bytes();self.item['output_external_CPU']={'predeclared_original':self.runtime['cpu.max'],'last_owned':self.initial['cpu.max'],'injected':self.runtime['cpu.max'],'journal_before_sha256':sha(before),'started_epoch':time.time()};self.save();(self.group/'cpu.max').write_text(self.runtime['cpu.max']+'\n');self.expected['cpu.max']=self.runtime['cpu.max'];deadline=time.monotonic()+60
  while time.monotonic()<deadline:
   self.invariant();v=json.loads((self.folder/'resource-state/status.json').read_bytes())
   if any(x['file']=='cpu.max' and x['reason_code']=='external_conflict' for x in v['items']):break
   time.sleep(.25)
  else:raise RuntimeError('external CPU conflict original60s deadline')
  assert controls(self.group,self.runtime)==self.expected;self.observe(NAMES[10],True);self.check(NAMES[10]);time.sleep(2);self.observe(NAMES[11],True);self.check(NAMES[11]);self.item['output_external_CPU']['ended_epoch']=time.time();self.item['output_external_CPU']['journal_after']=json.loads(self.c['statefile'].read_bytes());self.save()
  _,disabled=self.invoke('disable');assert disabled['state']=='restored' and controls(self.group,self.runtime)==self.runtime and json.loads(self.c['statefile'].read_bytes())==self.contract.empty_journal;self.rows.append({'name':NAMES[12],'passed':True,'phase':'online','epoch':time.time()});self.save();self.invoke('enable');assert self.c['wait_guard'](self.plan['programs']['candidate']['binary_sha256']);self.initial_agent=self.agents();assert len(self.initial_agent)==1 and self.c['same']();self.generation=1;self.cfgstate='accepted';self.expected=copy.deepcopy(self.initial);deadline=time.monotonic()+60
  while time.monotonic()<deadline:
   self.invariant();v=json.loads((self.folder/'resource-state/status.json').read_bytes())
   if v['configuration']['generation']==1 and all(x['reason_code']=='unchanged' for x in v['items']):break
   time.sleep(.25)
  else:raise RuntimeError('resumed Agent settled original60s deadline')
  self.accepted_hash=v['configuration']['accepted_hash'];assert self.accepted_hash==self.initial_config_hash;self.observe(NAMES[13]);self.check(NAMES[13]);assert [v['name'] for v in self.rows]==NAMES;self.prepared=True
 def after_disable(self):
  assert self.prepared and controls(self.group,self.runtime)==self.runtime and json.loads(self.c['statefile'].read_bytes())==self.contract.empty_journal and self.path.read_bytes()==self.original and self.profile_path.read_bytes()==self.profile_raw and self.profile_path.stat().st_mtime_ns==self.profile_mtime;self.item['output_final_restored']=True;self.save()
