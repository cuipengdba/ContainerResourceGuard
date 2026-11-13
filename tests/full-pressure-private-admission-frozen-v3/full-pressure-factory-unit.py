from pathlib import Path
import hashlib,importlib.util,json,sys,tempfile,types

def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
source=Path(sys.argv[1]);hook_source=Path(sys.argv[2]);core_source=Path(sys.argv[3]);null_source=Path(sys.argv[4]);m=load(source,'full_pressure817');hook=load(hook_source,'full_pressure_hook');cases=[]
assert hashlib.sha256(core_source.read_bytes()).hexdigest()==m.CORE_SHA
cases.append({'variant':'original-full-pressure-core-bytes-retained','passed':True})
for variant in ['matched-success','matched-Popen-error','unmatched-Popen-error','annotation-preparation-error']:
 primary=ValueError('original Popen');calls=[];record={}
 class Delegate:
  def Popen(self,args,*rest,**kwargs):
   calls.append((args,rest,kwargs))
   if variant in ['matched-Popen-error','unmatched-Popen-error']:raise primary
   return 'original-child'
 original=['kubectl','exec','-n',m.NAMESPACE,'dbs-business','-c','dbs','--','su','-','postgres','-c',m.native_command('dbs',m.RUN_ID+'0')]
 args=original if variant!='unmatched-Popen-error' else ['ordinary-original-command']
 owner=types.SimpleNamespace(execution=types.SimpleNamespace(ns=m.NAMESPACE),role='dbs',run_id=m.RUN_ID+'0',shim_directory='/tmp/crg-transport-'+m.RUN_ID+'0',record=record)
 if variant=='annotation-preparation-error':owner.shim_directory='/wrong-private-shim'
 proxy=m.ProcessProxy(Delegate(),owner);caught=None
 try:result=proxy.Popen(args,stdin='original-input',stdout='original-output')
 except BaseException as exc:caught=exc
 assert len(calls)==1 and calls[0][2]=={'stdin':'original-input','stdout':'original-output'}
 assert original[-1]==m.native_command('dbs',m.RUN_ID+'0')
 if variant in ['matched-success','matched-Popen-error']:
  assert calls[0][0] is not original and calls[0][0][:-1]==original[:-1] and calls[0][0][-1].endswith(original[-1]) and record['native_launch_count']==1
 else:assert calls[0][0] is args
 if variant in ['matched-Popen-error','unmatched-Popen-error']:assert caught is primary
 else:assert caught is None and result=='original-child'
 if variant=='annotation-preparation-error':assert record['diagnostic_failed'] and record['diagnostic_errors'][0]['action']=='native-command-annotation'
 cases.append({'variant':variant,'single_original_launch_and_exception_identity_preserved':True})
for variant in ['success','body-error-after-headers','missing-annotation','header-outside-native-window','duplicate-annotation']:
 native={'kind':'api','iteration':0,'started_monotonic':10.0,'ended_monotonic':12.0,'success':variant!='body-error-after-headers'}
 annotation={'run_id':'202611128170','kind':'urlopen-headers','iteration':0,'socket_timeout_seconds':4,'local_port':34567,'server_port':8090,'started_monotonic_ns':10500000000,'finished_monotonic_ns':11000000000,'headers_returned':True}
 def pair(call,stamp):return {'entry':{'call':call,'monotonic_ns':stamp,'fd_metadata':{'source':'event-time-safe-kernel-metadata','remote_port':34567,'local_port':8090}},'exit':{'return':3}}
 stream={'pairs':[pair('recvfrom',10600000000),pair('sendto',11500000000),pair('sendto',14000000000)]}
 rows=[] if variant=='missing-annotation' else [annotation]
 if variant=='header-outside-native-window':annotation['finished_monotonic_ns']=13000000000
 if variant=='duplicate-annotation':rows.append(dict(annotation))
 try:result=m.associate_requests(stream,[native],rows,'202611128170')
 except m.Rejected:
  assert variant=='duplicate-annotation';result=None
 if variant!='duplicate-annotation':
  row=result['requests'][0];assert row['native_request'] is native and row['business_success']==native['success'] and row['full_original_request_ended_ns']==12000000000
  if variant in ['missing-annotation','header-outside-native-window']:assert not result['every_API_has_one_complete_annotation'] and row['receive_pairs_within_original_request']==row['send_pairs_within_original_request']==0
  else:assert result['every_API_has_one_complete_annotation'] and row['receive_pairs_within_original_request']==row['send_pairs_within_original_request']==1
  if variant=='body-error-after-headers':assert not row['business_success'] and row['transport']['headers_returned'] and len(row['same_ports_after_original_end'])==1 and row['same_ports_after_original_end'][0]['entry']['monotonic_ns']==14000000000
 cases.append({'variant':variant,'original_full_request_window_success_and_late_failure_evidence_retained':True})
with tempfile.TemporaryDirectory(prefix='crg-full817-unit-') as directory:
 assert Path(directory).resolve().parent==Path(tempfile.gettempdir()).resolve() and Path(directory).name.startswith('crg-full817-unit-')
 path=Path(directory)/'exact.json';value={'all_events':[{'integer':1},{'integer':2}]};descriptor=m.private_json(path,value)
 assert json.loads(path.read_bytes())==value and descriptor['sha256']==hashlib.sha256(path.read_bytes()).hexdigest() and descriptor['bytes']==len(path.read_bytes())
 try:m.artifact(path,descriptor['bytes']-1)
 except m.Rejected:pass
 else:raise AssertionError('oversized artifact accepted')
 cases.append({'variant':'raw-artifact-exact-bytes-and-bound','passed':True})
for variant in ['helper-start-permission','helper-save-permission','helper-start-and-business-error','collector-stop-error']:
 primary=ValueError('original-business');cleanup=OSError('collector cleanup');work=[];saved=[];record={};delegate=object()
 class Execution:
  ns=m.NAMESPACE;root=m.ROOT;plan={'run_id':m.RUN_ID}
  def save(self):
   if variant=='helper-save-permission':raise OSError('optional save denied')
   saved.append(True)
  def identity(self,role):raise PermissionError('optional diagnostic denied')
  def business_native(self,*args):
   work.append(True)
   if variant=='helper-start-and-business-error':raise primary
   return 'original-business-result'
 core=types.SimpleNamespace(PressureExecution=Execution,subprocess=delegate)
 if variant=='collector-stop-error':
  observer=m.Observer(core,None,Execution(),'dbs','own-folder','own-group',{},record)
  class FailingSession:
   child=None
   def finish(self):raise cleanup
  session=FailingSession();observer.sessions=[session];observer.collector=session;observer.delegate=delegate;observer.proxy=m.ProcessProxy(delegate,observer);core.subprocess=observer.proxy
  caught=None
  try:observer.finish()
  except Exception as exc:caught=exc
  assert caught is cleanup and core.subprocess is delegate and record['diagnostic_errors'][0]['action']=='collector-stop'
 else:
  def factory(execution,role,folder,group,row,detail):return m.Observer(core,None,execution,role,folder,group,row,detail)
  hook.install(core,factory);row={};caught=None
  try:returned=Execution().business_native('dbs','own-folder','own-group',row)
  except BaseException as exc:caught=exc
  assert len(work)==1 and row['full_BPF_diagnostic']['diagnostic_failed']
  if variant=='helper-start-and-business-error':assert caught is primary
  else:assert caught is None and returned=='original-business-result'
 cases.append({'variant':variant,'ordinary_diagnostic_failure_does_not_skip_original_business_or_replace_exception':True})
class CheckExecution:
 ns=m.NAMESPACE;root=m.ROOT;plan={'run_id':m.RUN_ID}
 def save(self):pass
 def business_native(self,*args):return 'original-business-result'
core=types.SimpleNamespace(PressureExecution=CheckExecution)
def check_factory(execution,role,folder,group,row,record):
 observer=m.Observer(core,None,execution,role,folder,group,row,record)
 observer.start=lambda:None
 observer.finish=lambda:observer.diagnostic_check('synthetic-incomplete-stream',False)
 return observer
hook.install(core,check_factory);row={};assert CheckExecution().business_native('dbs','own-folder','own-group',row)=='original-business-result' and row['full_BPF_diagnostic']['diagnostic_failed'] and not row['full_BPF_diagnostic']['checks'][0]['passed']
cases.append({'variant':'failed-diagnostic-check-stays-failed-after-wrapper-finally','passed':True})
actual_raw=null_source.read_bytes();assert hashlib.sha256(actual_raw).hexdigest()=='765e9a891d3e7eced53d02a5bf6596079a9989c4b79145e418f9b35cec14e751';actual=json.loads(actual_raw);assert actual['function_pairs'] is None and actual['phase']=='preflight-readonly'
with tempfile.TemporaryDirectory(prefix='crg-null817-unit-') as directory:
 root=Path(directory);assert root.resolve().parent==Path(tempfile.gettempdir()).resolve() and root.name.startswith('crg-null817-unit-');path=root/'dbs-readonly-bpf.json';path.write_bytes(actual_raw);saved=[];record={}
 execution=types.SimpleNamespace(root=root,plan={'run_id':m.RUN_ID},save=lambda:saved.append(True));observer=m.Observer(None,None,execution,'dbs',root/'folder',root/'group',{},record);observer.capture['BPF_sessions']['readonly']={'report':actual};observer.save()
 summary=record['sessions']['readonly'];assert saved==[True] and summary['summary']['function_pairs']==0 and summary['summary']['events']==summary['summary']['syscall_pairs']==0 and summary['summary']['hook_count']==40 and summary['report_artifact']['sha256']==hashlib.sha256(actual_raw).hexdigest() and path.read_bytes()==actual_raw
cases.append({'variant':'actual-null-preflight-projection-retains-exact-raw-artifact','passed':True})
result={'schema':'crg-full-pressure-factory-unit-v1','phase':'passed','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'hook_sha256':hashlib.sha256(hook_source.read_bytes()).hexdigest(),'original_core_sha256':hashlib.sha256(core_source.read_bytes()).hexdigest(),'actual_null_preflight_sha256':hashlib.sha256(actual_raw).hexdigest(),'cases':cases,'synthetic_only_not_vendor_runtime_qualification':True,'original_full600_and11_intervals_not_executed':True}
print(json.dumps(result))
