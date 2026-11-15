from pathlib import Path
import datetime,hashlib,json,os,subprocess,time

w=Path('/var/tmp/crg-final1461-tools-20261115');out=Path('/var/tmp/crg-final1461-overhead-20261115');p=json.loads((w/'overhead-plan.json').read_bytes());sha=lambda v:hashlib.sha256(v).hexdigest()
def process(v,entry=None):
 try:
  proc=Path('/proc',str(v['pid']));fields=(proc/'stat').read_bytes().rsplit(b')',1)[1].split();args=(proc/'cmdline').read_bytes().split(b'\0');actual=int(fields[19]);value={'pid':v['pid'],'expected_start_ticks':v['start_ticks'],'actual_start_ticks':actual,'original_absent':actual!=v['start_ticks'],'state':fields[0].decode()}
  if entry:value['expected_entry_matches']=entry.encode() in args
  if actual==v['start_ticks']:
   value['cgroup']=(proc/'cgroup').read_text();value['children']=[int(v) for v in (proc/'task'/str(v['pid'])/'children').read_text().split()]
  return value
 except (FileNotFoundError,ProcessLookupError):return {'pid':v['pid'],'expected_start_ticks':v['start_ticks'],'original_absent':True}
def command(args):return subprocess.run(args,capture_output=True,text=True,timeout=15)
launch=json.loads((w/'launch.json').read_bytes());result={'phase':'read-only-final-overhead-observation','node_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'job_sha256':sha((w/'overhead-job.py').read_bytes()),'plan_sha256':sha((w/'overhead-plan.json').read_bytes()),'launch':launch,'processes':{'runner':process(launch,launch['entry'])},'new_long_started':Path('/var/tmp/crg-final1396-results-20261115').exists(),'stable_release_accepted':False}
assert result['job_sha256']==p['job_sha256'] and result['plan_sha256']==launch['plan_sha256']
if (w/'worker.json').exists():
 worker=json.loads((w/'worker.json').read_bytes());result['worker']=worker;result['processes']['worker']=process(worker,worker['entry'])
if (w/'exit.json').exists():result['exit']=json.loads((w/'exit.json').read_bytes())
if (out/'report.json').exists():
 raw=(out/'report.json').read_bytes();assert len(raw)<4*1024**2;report=json.loads(raw);result.update(report=report,report_sha256=sha(raw),report_exact_utf8=raw.decode(),fixture_processes={})
 for name,row in report['cases'].items():
  fixture=row.get('fixture_identity')
  if not fixture:continue
  group=Path(fixture['group']);result['fixture_processes'][name]={'identity':fixture,'main':process(fixture['main']),'Agent':process(fixture['Agent']),'leaf_absent':not group.exists(),'parent_absent':not Path(fixture['pod_parent']).exists()}
  if group.exists():
   value=result['fixture_processes'][name];value['current_controls']={n:(group/n).read_text().strip() for n in ['cpu.max','memory.max','io.max','pids.max','cpu.weight','io.weight','memory.high','memory.swap.max']};value['expected_controls_match']=value['current_controls']==row['actual_controls'];value['Agent_binary_sha256']=sha(Path('/proc',str(fixture['Agent']['pid']),'exe').read_bytes()) if not value['Agent']['original_absent'] else None
 ns=command(['kubectl','get','namespace',p['namespace'],'--ignore-not-found','-o','json','--request-timeout=5s']);assert ns.returncode==0;result['namespace_absent']=not ns.stdout.strip()
 result['namespace_UID_matches']=None if result['namespace_absent'] else json.loads(ns.stdout)['metadata']['uid']==report.get('namespace_uid')
 summary={'node_utc':result['node_utc'],'phase':report['phase'],'error':report.get('error'),'runner':result['processes']['runner'],'worker':result['processes'].get('worker'),'exit':result.get('exit'),'cases':{name:{'samples':len(v['samples']),'last_elapsed_seconds':v['samples'][-1]['elapsed_seconds'] if v['samples'] else None,'passed':v.get('passed'),'result':v.get('result')} for name,v in report['cases'].items()},'namespace_absent':result['namespace_absent'],'new_long_started':result['new_long_started'],'stable_release_accepted':False}
else:summary={'node_utc':result['node_utc'],'phase':'report-not-created','processes':result['processes'],'exit':result.get('exit')}
result['summary']=summary
result['frozen_inputs_actual_sha256']={name:sha((w/name).read_bytes()) for name in p['source_sha256']}
result['terminal_files']={}
if result.get('report',{}).get('phase') in ['passed','failed']:
 for name in result['report']['cases']:
  state=out/name;logs=[]
  for path in sorted((state/'logs').glob('crg-*.log')):
   raw=path.read_bytes();assert len(raw)<16*1024**2
   events=[json.loads(v) for v in raw.splitlines() if v.strip()]
   logs.append({'filename':path.name,'bytes':len(raw),'mode':oct(path.stat().st_mode&0o777),'sha256':sha(raw),'has_v2_detection':any(v.get('event')=='cgroup_detected' and v.get('fields',{}).get('check',{}).get('cgroup_version')=='v2' for v in events),'has_high_policy':any(v.get('event')=='resource_status' and v.get('fields',{}).get('memory_policy')=='high-reclaim-throttle' for v in events)})
  marker=state/'marker';result['terminal_files'][name]={'logs':logs,'marker':marker.read_text() if marker.exists() else None,'metrics_symlink':(state/'metrics.prom').is_symlink(),'events_symlink':(state/'events.jsonl').is_symlink(),'journal_sha256':sha((state/'journal.json').read_bytes()),'status_sha256':sha((state/'status.json').read_bytes())}
print(json.dumps(result))
