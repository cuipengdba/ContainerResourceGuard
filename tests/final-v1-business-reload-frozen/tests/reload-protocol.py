"""Frozen isolated business reload protocol; imported only by this test campaign."""
from pathlib import Path
import hashlib,json,os,time

TOOLS=Path('/var/tmp/crg-final1425-tools-20261115')
PROFILE_SHA='00e35e91594ed0ad1075a196c20bd8f4c6628c346c4bd6e901ac05d4cc90ef6b'
FIELDS=['cpu.max','memory.max','io.max','cpu.weight','pids.max','memory.high','memory.swap.max','io.weight']
NAMES=['manual-to-percent30','independent-percent25-29-80','invalid-IO101','truncated-JSON','duplicate-key','temporarily-missing','FIFO-without-writer','atomic-ConfigMap-link-recovery','whitespace-same-policy','manual-CPU-only-removes-owned-high-IO','manual-all-three','manual-to-percent-again','return-original-manual']

def digest(raw):return hashlib.sha256(raw).hexdigest()
def getjson(path):return json.loads(path.read_bytes())
def io_fields(text,device):
 rows={}
 for line in text.splitlines():
  f=line.split();assert f[0] not in rows;rows[f[0]]=dict(v.split('=',1) for v in f[1:])
 own=rows.pop(device,{});return {'rbps':'max','wbps':'max','riops':'max','wiops':'max',**own},rows

class Protocol:
 def __init__(self,context):
  self.c=context;self.started=False;self.step=0;self.finished=False;self.rows=[]
  self.plan=getjson(TOOLS/'plan.json');assert self.plan['reload_contract']['cases']==NAMES
  raw=(TOOLS/'tests/reload-profile.json').read_bytes();assert digest(raw)==PROFILE_SHA;self.profile=raw;self.profile_value=json.loads(raw);assert self.profile_value['version']==2 and len(self.profile_value['devices'])==1
  self.dev=self.profile_value['devices'][0];self.device=self.dev['device'];assert self.device=='253:0'
  self.manual=self.plan['configuration'];self.policies=[{'cpu_percent':30,'memory_percent':30,'io_percent':100},{'cpu_percent':25,'memory_percent':29,'io_percent':80}]
  self.configs=[self.policies[0],self.policies[1],{'io_percent':101},b'{',b'{"cpu_percent":20,"cpu_percent":30}',None,'FIFO',self.policies[1],self.policies[1],{'resource_mode':'manual','limits':{'cpu_cores':7.2}},self.manual,self.policies[0],self.manual]
  self.generations=[2,3,3,3,3,3,3,3,3,4,5,6,7]
  self.c['report']['reload_contract']={'cases':NAMES,'source_profile_sha256':PROFILE_SHA,'actual_observations':self.rows,'passed':False}

 def start(self):
  assert len(self.c['roles'])==1;self.role,self.own=next(iter(self.c['roles'].items()));self.folder=self.own['state'].parent.parent;self.path=self.folder/'crg-config/config.json';self.profile_path=self.path.with_name('io-profile.json');assert not self.profile_path.exists()
  self.initial=dict(self.own['controls']);assert set(self.initial)==set(FIELDS);self.expected=dict(self.initial);self.original={'cpu.max':'800000 100000','memory.high':'max','io.max':''}
  self.config_state='accepted';self.generation=1;self.current_hash=getjson(self.own['state'])['configuration']['accepted_hash'];self.last_good=self.policies[1]
  journal=getjson(self.folder/'resource-state/journal.json')['mutations'];assert journal['cpu.max:']['original']==self.original['cpu.max'] and journal['memory.high:']['original']=='max' and journal['io.max:'+self.device]['original']=='rbps=max wbps=max riops=max wiops=max'
  with self.profile_path.open('xb') as f:os.chmod(self.profile_path,0o600);f.write(self.profile);f.flush();os.fsync(f.fileno())
  self.profile_mtime=self.profile_path.stat().st_mtime_ns;self.started=True

 def expected_policy(self,value):
  expected=dict(self.initial)
  if 'cpu_percent' in value:
   mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:')))*1024;online=Path('/sys/devices/system/cpu/online').read_text().strip();assert online=='0-23' and mem==66673278976
   page=os.sysconf('SC_PAGE_SIZE');expected['cpu.max']=str(int(24*value['cpu_percent']/100*100000))+' 100000';expected['memory.high']=str(int(mem*value['memory_percent']/100)//page*page)
   expected['io.max']=self.device+' rbps='+str(int(self.dev['read_bps']*value['io_percent']/100))+' wbps='+str(int(self.dev['write_bps']*value['io_percent']/100))+' riops=max wiops=max'
  elif len(value['limits'])==1:expected.update(self.original);expected['cpu.max']='720000 100000'
  return expected

 def controls_equal(self,actual,expected):
  return all(actual[k]==expected[k] for k in FIELDS if k!='io.max') and io_fields(actual['io.max'],self.device)==io_fields(expected['io.max'],self.device)

 def same(self):
  self.c['guards']()
  for identity in [self.own['main'],self.own['agent'],self.own['cache']]:self.c['verify_process'](self.role,identity)
  assert self.c['find_guard'](self.own['group'],'crg',self.c['args'].agent_sha256)==self.own['agent'] and self.c['find_guard'](self.own['group'],'containercacheguard',self.c['args'].cache_sha256)==self.own['cache']
  assert getjson(self.own['cache_state'])['action']=='enforce' and int(dict(x.split() for x in (self.own['group']/'memory.events').read_text().splitlines())['oom_kill'])==self.own['oom_kills']

 def validate_sample_state(self,state):
  cfg=state['configuration'];assert cfg['state']==self.config_state and cfg['generation']==self.generation and cfg['accepted_hash']==self.current_hash
  assert state['state']==('degraded' if self.config_state=='rejected' else 'managed') and all(v['state']=='applied' for v in state['items'])

 def write_config(self,index,value):
  path=self.path;temp=path.with_name('reload1425.next');assert not temp.exists() and not temp.is_symlink()
  if index==5:path.replace(path.with_name('reload1425.saved'));return
  if index==6:
   assert not path.exists();os.mkfifo(path,0o600);return
  if path.exists() and not path.is_file() and not path.is_symlink():path.unlink()
  raw=value if isinstance(value,bytes) else json.dumps(dict(value,interval_seconds=1,data_paths=['/opt/postgresql']),sort_keys=True).encode()
  if index==8:raw=b' \n'+raw+b'\n  '
  target=path.with_name('reload1425.target.json') if index==7 else temp
  with target.open('xb') as f:os.chmod(target,0o600);f.write(raw);f.flush();os.fsync(f.fileno())
  if index==7:temp.symlink_to(target.name)
  temp.replace(path)

 def tick(self,elapsed,backup):
  if not self.started:self.start()
  if self.step>=len(NAMES):return
  if elapsed<31+self.step*30:return
  index=self.step;name=NAMES[index];assert self.c['jobs'][0][1].poll() is None and elapsed<self.c['args'].seconds
  if index==0:assert backup is not None and backup.poll() is None,'first effective reload must overlap original engine'
  previous=getjson(self.own['state']);self.validate_sample_state(previous);old_hash=self.current_hash;old_controls=dict(self.expected);rejected=2<=index<=6;value=self.configs[index];candidate=old_controls if rejected else self.expected_policy(value);mark=time.time_ns();began=time.time();self.write_config(index,value);deadline=time.monotonic()+60
  while time.monotonic()<deadline:
   self.same();assert self.c['jobs'][0][1].poll() is None
   actual=self.c['controls'](self.own['group'])
   for key in FIELDS:
    if key not in ['cpu.max','memory.high','io.max']:assert actual[key]==self.initial[key]
   if rejected:assert self.controls_equal(actual,old_controls)
   state=getjson(self.own['state']);cfg=state['configuration'];target_state='rejected' if rejected else 'accepted'
   if self.own['state'].stat().st_mtime_ns>=mark and cfg['state']==target_state and cfg['generation']==self.generations[index] and self.controls_equal(actual,candidate):break
   time.sleep(.25)
  else:raise RuntimeError('reload original60s deadline: '+name)
  assert state['state']==('degraded' if rejected else 'managed') and all(v['state']=='applied' for v in state['items'])
  if rejected or index in [7,8]:assert cfg['accepted_hash']==old_hash
  else:assert cfg['accepted_hash']!=old_hash
  if rejected:assert state['plan']==previous['plan'] and cfg.get('error')
  else:
   expected_files={'cpu.max'} if index==9 else {'cpu.max','memory.high','io.max'};assert {v['file'] for v in state['items']}==expected_files
   if 'cpu_percent' in value:assert state['plan']['percentages']==value and state['plan']['resource_mode']=='percent'
   else:assert state['plan']['resource_mode']=='manual'
   journal=getjson(self.folder/'resource-state/journal.json');assert {v['file'] for v in journal['mutations'].values()}==expected_files
  assert self.profile_path.read_bytes()==self.profile and self.profile_path.stat().st_mtime_ns==self.profile_mtime
  self.expected=candidate;self.own['controls']=actual;self.config_state=target_state;self.generation=cfg['generation'];self.current_hash=cfg['accepted_hash'];self.same();self.validate_sample_state(state)
  self.rows.append({'case':name,'passed':True,'began_epoch':began,'ended_epoch':time.time(),'generation':cfg['generation'],'configuration_state':cfg['state'],'accepted_hash':cfg['accepted_hash'],'actual_controls':actual,'expected_controls':candidate,'same_Agent_PID1_cache':True,'profile_unchanged':True,'engine_alive_at_first_reload':index==0 and backup is not None and backup.poll() is None,'state':state['state'],'error':cfg.get('error'),'declared_numeric':state['plan'].get('percentages')});self.step+=1;self.c['save']()
  if self.step==len(NAMES):self.finished=True;self.c['report']['reload_contract']['passed']=True;self.c['save']()

 def finish(self):
  assert self.finished and len(self.rows)==13 and self.config_state=='accepted' and self.generation==7 and self.controls_equal(self.c['controls'](self.own['group']),self.initial)
  assert self.profile_path.read_bytes()==self.profile and self.profile_path.stat().st_mtime_ns==self.profile_mtime
