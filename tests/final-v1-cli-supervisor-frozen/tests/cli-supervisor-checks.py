"""Frozen-test candidate: actual final CLI on private vendor-container copies.

Never execute a copied supervisor. The real business/cache startup is untouched.
"""
from pathlib import Path
import datetime,hashlib,json,os,re,stat,time

sha=lambda raw:hashlib.sha256(raw).hexdigest()

class Checks:
 def __init__(self,context):
  self.c=context;self.item=context['item'];self.folder=context['folder'];self.role=context['role'];self.plan=context['plan'];self.rows=self.item.setdefault('cli_supervisor_checks',[]);self.commands=self.item.setdefault('cli_supervisor_commands',[]);self.installed=[];self.expected_config=(self.folder/'crg-config/config.json').read_bytes();self.expected_held=context['statefile'].read_bytes();self.module_started=time.time();self.save=context['save'];self.prepared=False
 def check(self,name,ok,**detail):
  self.rows.append(dict(name=name,passed=bool(ok),phase=self.phase,epoch=time.time(),**detail));self.save()
  if not ok:raise AssertionError(name)
 def invoke(self,command,*args,refuse=False,reason=None):
  if self.phase=='online' and not self.c['measurement_active']():raise RuntimeError('CLI action outside original active600s')
  started=time.time();result=self.c['ex'](self.role,'/staging/crg',command,'--config','/etc/crg/config.json',*args,check=False,timeout=45);ended=time.time();assert len(result.stdout.encode())<=262144 and len(result.stderr.encode())<=65536;response=None
  if result.stdout.strip():
   try:response=json.loads(result.stdout)
   except ValueError:pass
  self.commands.append({'command':command,'args':list(args),'phase':self.phase,'expected_refusal':refuse,'started_epoch':started,'ended_epoch':ended,'exit':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'response':response});self.save()
  if refuse:
   assert result.returncode!=0,'expected refusal: '+command
   if reason:assert reason in result.stdout+result.stderr,'refusal reason missing: '+reason
  else:assert result.returncode==0,'CLI failed: '+command
  if self.phase=='online' and not self.c['measurement_active']():raise RuntimeError('CLI action did not fit wholly inside original600s')
  return result,response
 def protected(self):
  return self.c['same']() and self.c['statefile'].read_bytes()==self.expected_held and (self.folder/'crg-config/config.json').read_bytes()==self.expected_config and not (self.folder/'crg-config/io-profile.json').exists() and sha((self.folder/'ccg/scripts/business-supervisor.sh').read_bytes())==self.plan['private_fixture_sha256']['fixture/'+self.role+'/supervisor.sh']
 def agents(self):
  rows=[]
  for pid in (self.c['group']/'cgroup.procs').read_text().splitlines():
   p=Path('/proc',pid)
   try:
    args=(p/'cmdline').read_bytes().split(bytes([0]))
    if len(args)>1 and Path(os.fsdecode(args[0])).name=='crg' and args[1]==b'run':
     fields=(p/'stat').read_bytes().rsplit(b')',1)[1].split();rows.append({'pid':int(pid),'start_ticks':int(fields[19]),'sha256':sha((p/'exe').read_bytes()),'state':fields[0].decode()})
   except (FileNotFoundError,ProcessLookupError):pass
  return rows
 def writer_unlocked(self):
  import fcntl
  fd=os.open(str(self.c['group']),os.O_RDONLY|os.O_DIRECTORY)
  try:
   try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:return False
   fcntl.flock(fd,fcntl.LOCK_UN);return True
  finally:os.close(fd)
 def readonly_status(self,label,lock,minimum_age=0):
  path=self.folder/'resource-state/status.json';before=path.read_bytes();before_meta=path.stat();_,view=self.invoke('status','--format','json');human,_=self.invoke('status','--format','human');after=path.read_bytes();match=re.search(r'^State: (.*?); mode: (.*?); snapshot age: (-?[0-9]+)s; writer lock held: (true|false)$',human.stdout,re.M);assert match and view['writer_lock_held']==lock and not view.get('lock_check_error') and view['snapshot_age_seconds']>=minimum_age and (match[1],match[2],match[4])==(view['state'],view['mode'],str(lock).lower()) and abs(int(match[3])-view['snapshot_age_seconds'])<=5
  self.c['contract'].status(view);env=view['plan']['environment'];assert env['cgroup']==str(self.c['group']) and 'Cgroup: '+env['cgroup'] in human.stdout and 'Host: '+str(env['host_online_cpus'])+' online CPUs, '+str(env['host_memory_bytes'])+' bytes memory' in human.stdout and 'Requested: manual CPU / memory / per-device IO; omitted dimensions unmanaged' in human.stdout
  settings={(v['file'],v.get('device','')):v for v in view['plan']['settings']};actual={(v['file'],v.get('device','')):v for v in view['actual']};assert set(settings)==set(actual)
  for key,wanted in settings.items():
   got=actual[key];assert got['state']=='read' and got['value']==wanted['value'] and 'Actual '+key[0]+' '+key[1]+': '+got['value']+' ' in human.stdout
  stamp=datetime.datetime.fromisoformat(view['time_utc'].replace('Z','+00:00')).timestamp();assert -2<=time.time()-stamp-view['snapshot_age_seconds']<=5;assert before==after and path.stat().st_mtime_ns==before_meta.st_mtime_ns and self.protected();self.item.setdefault('cli_status_observations',[]).append({'label':label,'phase':self.phase,'epoch':time.time(),'json':view,'human_stdout':human.stdout,'persisted_status_sha256':sha(before),'persisted_status_mtime_ns':before_meta.st_mtime_ns,'actual_agents':self.agents()});self.save();return view
 def plan_views(self):
  for command in ['doctor','preflight']:
   before=self.c['statefile'].read_bytes();_,value=self.invoke(command,'--format','json');human,_=self.invoke(command,'--format','human');p=value;assert p['resource_mode']=='manual' and p['environment']['cgroup']==str(self.c['group']) and 'Requested: manual CPU / memory / per-device IO; omitted dimensions unmanaged' in human.stdout
   for v in p['settings']:assert 'Target '+v['file']+' '+v.get('device','')+': '+v['value'] in human.stdout
   if command=='preflight':assert 'Disabled: false' in human.stdout and all(v['open_writable'] for v in value['checks'])
   assert before==self.c['statefile'].read_bytes() and self.protected();self.check(command+'-JSON-human-own-plan-readonly',True)
 def create_source(self,name,raw,mode=0o750):
  directory=self.folder/'recovery'/name;directory.mkdir(mode=0o700);path=directory/'supervisor.sh';path.write_bytes(raw);path.chmod(mode);assert not os.listxattr(path),'scratch source has metadata unsupported by product installer';return {'name':name,'host':path,'inside':'/recovery/'+name+'/supervisor.sh','raw':raw,'sha256':sha(raw),'mode':mode,'backup_host':directory/'backup','backup':'/recovery/'+name+'/backup'}
 def options(self,row):return ['--supervisor',row['inside'],'--supervisor-sha256',row['sha256'],'--helper','/opt/crg/optional-agent.sh','--helper-sha256',self.plan['source_sha256']['examples/optional-agent.sh'],'--agent-binary','/opt/crg/crg','--agent-sha256',self.plan['programs']['candidate']['binary_sha256']]
 def preview(self,row):
  before=row['host'].read_bytes();_,value=self.invoke('supervisor-plan',*self.options(row));p=value['plan'];assert value['business_action']==value['limits_action']=='none' and p['state']=='preview' and p['source_sha256']==row['sha256'] and p['helper_sha256']==self.plan['source_sha256']['examples/optional-agent.sh'] and p['binary_sha256']==self.plan['programs']['candidate']['binary_sha256'] and p['config_sha256']==sha(self.expected_config) and re.fullmatch('[0-9a-f]{64}',p['proposed_sha256']) and row['host'].read_bytes()==before and not row['backup_host'].exists() and self.protected();return p
 def install(self,row,preview):
  _,value=self.invoke('supervisor-install',*self.options(row),'--backup-dir',row['backup']);assert value['plan']['state']=='installed' and value['plan']['proposed_sha256']==preview['proposed_sha256'];body=row['host'].read_bytes();assert sha(body)==preview['proposed_sha256'] and stat.S_IMODE(row['host'].stat().st_mode)==row['mode'] and (row['backup_host']/'supervisor.original').read_bytes()==row['raw'] and (row['backup_host']/'supervisor.proposed.sh').read_bytes()==body
  for name in ['supervisor.original','supervisor.proposed.sh','config.json','optional-agent.sh','plan.json','receipt.json']:assert stat.S_IMODE((row['backup_host']/name).stat().st_mode)==0o600
  assert (row['backup_host']/'config.json').read_bytes()==self.expected_config and (row['backup_host']/'optional-agent.sh').read_bytes()==(self.folder/'crg/optional-agent.sh').read_bytes();receipt=json.loads((row['backup_host']/'receipt.json').read_bytes());assert receipt['state']=='installed' and receipt['source_sha256']==row['sha256'] and receipt['proposed_sha256']==preview['proposed_sha256'] and receipt['source_mode']==row['mode'];self.installed.append(row);self.item.setdefault('supervisor_copies',[]).append({'name':row['name'],'source_sha256':row['sha256'],'proposed_sha256':sha(body),'source_mode':row['mode'],'private_source_bytes_exported':False});assert self.protected();return body
 def online(self):
  self.phase='online';self.check('initial-actual-status-JSON-human-lock-and-age',self.readonly_status('initial-managed',True)['state']=='managed');self.plan_views();templates=[]
  for name,value in self.plan['supervisor_templates'].items():
   raw=value['exact_utf8'].encode();assert sha(raw)==value['sha256'];row=self.create_source('template-'+name,raw);row['preview']=self.preview(row);templates.append(row);self.check(name+'-trusted-template-plan-readonly',True)
  row=templates[0];before=row['host'].read_bytes();self.invoke('supervisor-install',*self.options(row),'--backup-dir',row['backup'],refuse=True,reason='quiesce the resource Agent');self.check('active-Agent-lock-refuses-install-before-backup',row['host'].read_bytes()==before and not row['backup_host'].exists() and self.protected())
  for flag,reason in [('--supervisor-sha256','trusted source SHA256 mismatch'),('--helper-sha256','helper SHA256 mismatch'),('--agent-sha256','binary mode or trusted SHA256 mismatch')]:
   options=self.options(row);options[options.index(flag)+1]='0'*64;self.invoke('supervisor-plan',*options,refuse=True,reason=reason);self.check(flag[2:]+'-wrong-trusted-hash-refused',row['host'].read_bytes()==before and not row['backup_host'].exists() and self.protected())
  unknown=self.create_source('unknown-layout',b'#!/bin/bash\nexit 0\n');self.invoke('supervisor-plan',*self.options(unknown),refuse=True,reason='unsupported supervisor shutdown');self.check('unknown-layout-refused-with-source-byte-unchanged',unknown['host'].read_bytes()==unknown['raw'] and not unknown['backup_host'].exists() and self.protected())
  alias=row['host'].parent/'alias.sh';alias.symlink_to(row['host'].name);opts=self.options(row);opts[opts.index('--supervisor')+1]='/recovery/'+row['name']+'/alias.sh';self.invoke('supervisor-plan',*opts,refuse=True);self.check('symlink-source-refused-without-target-change',row['host'].read_bytes()==before and alias.is_symlink() and self.protected())
  self.invoke('quiesce');self.check('quiesced-writer-unlocked-original-policy-and-business-retained',self.writer_unlocked() and self.protected());self.item['natural_age_wait']={'started_epoch':time.time(),'snapshot_time_utc':json.loads((self.folder/'resource-state/status.json').read_bytes())['time_utc']};self.save();self.check('quiesced-JSON-human-reports-unlocked',not self.readonly_status('quiesced',False)['writer_lock_held'])
  for row in templates:
   body=self.install(row,row['preview']);text=body.decode();self.check(row['name']+'-install-private-copy-preserves-template-anchors-and-mode',text.count('# CRG OPTIONAL BEGIN')==1 and '"$BUSINESS_START" &\nbusiness_pid=$!\nstart_guard\n# CRG OPTIONAL BEGIN' in text and 'wait "$business_pid"\nstatus=$?' in text and '"$CCG_BIN" &\n  guard_pid=$!' in text)
   self.invoke('supervisor-plan',*self.options(row),refuse=True,reason='trusted source SHA256 mismatch');self.check(row['name']+'-repeated-original-receipt-source-refused',row['host'].read_bytes()==body and self.protected())
   self.invoke('supervisor-uninstall','--supervisor',row['inside'],'--backup-dir',row['backup'],refuse=True,reason='unresolved resource journal');self.check(row['name']+'-uninstall-owned-journal-refused',row['host'].read_bytes()==body and self.protected())
  private_raw=(self.folder/'ccg/scripts/business-supervisor.sh').read_bytes();private=self.create_source('private-vendor-copy',private_raw);prefix='  [[ -z "$guard_pid" ]] || kill -TERM "$guard_pid" 2>/dev/null || ';text=private_raw.decode();supported=(text.startswith(('#!/usr/bin/env bash\n','#!/bin/bash\n')) and not any(x in text for x in ['\r','\x00','CRG OPTIONAL']) and text.count('business_pid=\nguard_pid=\nstopping=0\n')==1 and text.count('"$BUSINESS_START" &\nbusiness_pid=$!\nstart_guard\n')==1 and sum(text.count(prefix+v) for v in [':\n','true\n'])==1)
  self.item['private_vendor_template_supported']=supported
  if supported:self.install(private,self.preview(private))
  else:self.invoke('supervisor-plan',*self.options(private),refuse=True)
  self.check('known-private-vendor-copy-plan-and-supported-install-or-safe-refusal',private_raw==private['raw'] and sha(private_raw)==self.plan['private_fixture_sha256']['fixture/'+self.role+'/supervisor.sh'] and self.protected())
  stamp=datetime.datetime.fromisoformat(self.item['natural_age_wait']['snapshot_time_utc'].replace('Z','+00:00')).timestamp();held_status=(self.folder/'resource-state/status.json').read_bytes();deadline=time.monotonic()+320
  while time.time()-stamp<305:
   assert time.monotonic()<deadline and self.c['measurement_active']() and self.writer_unlocked() and self.protected() and (self.folder/'resource-state/status.json').read_bytes()==held_status;self.c['reserve']();time.sleep(min(3,max(.01,305-(time.time()-stamp))))
  view=self.readonly_status('naturally-aged-quiesced',False,305);self.item['natural_age_wait'].update(ended_epoch=time.time(),observed_age_seconds=view['snapshot_age_seconds']);self.check('naturally-aged-over305s-no-timestamp-or-mtime-edits',self.writer_unlocked() and held_status==(self.folder/'resource-state/status.json').read_bytes());self.invoke('enable');assert self.c['wait_guard'](self.plan['programs']['candidate']['binary_sha256']);fresh_deadline=time.monotonic()+30
  while json.loads((self.folder/'resource-state/status.json').read_bytes())['time_utc']==self.item['natural_age_wait']['snapshot_time_utc']:
   assert time.monotonic()<fresh_deadline and self.c['measurement_active']();time.sleep(.2)
  view=self.readonly_status('resumed-final-single-writer',True);agents=self.agents();self.check('resumed-same-final-ELF-new-snapshot-one-writer',len(agents)==1 and agents[0]['sha256']==self.plan['programs']['candidate']['binary_sha256'] and view['snapshot_age_seconds']<120 and view['time_utc']!=self.item['natural_age_wait']['snapshot_time_utc']);assert [r['name'] for r in self.rows if r['phase']=='online']==self.plan['cli_supervisor_online_checks'];self.prepared=True
 def after_disable(self):
  self.phase='post600';assert self.prepared and self.writer_unlocked() and json.loads(self.c['statefile'].read_bytes())==self.c['contract'].empty_journal and {f:(self.c['group']/f).read_text() for f in self.c['policy_contract'].FILES}==self.c['contract'].runtime
  for row in self.installed:
   _,value=self.invoke('supervisor-uninstall','--supervisor',row['inside'],'--backup-dir',row['backup']);assert value['plan']['state']=='uninstalled' and row['host'].read_bytes()==row['raw'] and stat.S_IMODE(row['host'].stat().st_mode)==row['mode'] and json.loads((row['backup_host']/'receipt.json').read_bytes())['state']=='uninstalled'
  self.check('all-installed-private-copies-uninstall-byte-and-mode-restored',len(self.installed)==2+int(self.item['private_vendor_template_supported']));self.check('post-uninstall-original-runtime-journal-business-and-cache-unchanged',json.loads(self.c['statefile'].read_bytes())==self.c['contract'].empty_journal and {f:(self.c['group']/f).read_text() for f in self.c['policy_contract'].FILES}==self.c['contract'].runtime and (self.folder/'crg-config/config.json').read_bytes()==self.expected_config and sha((self.folder/'ccg/scripts/business-supervisor.sh').read_bytes())==self.plan['private_fixture_sha256']['fixture/'+self.role+'/supervisor.sh']);assert [r['name'] for r in self.rows if r['phase']=='post600']==self.plan['cli_supervisor_post600_checks']
