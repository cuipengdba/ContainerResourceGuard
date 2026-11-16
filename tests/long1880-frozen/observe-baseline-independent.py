from pathlib import Path
import datetime,hashlib,json,time
w=Path('/var/tmp/crg-final1880-tools-20261116');root=Path('/var/tmp/crg-final1880-results-20261116');raw=(w/'plan.json').read_bytes();assert hashlib.sha256(raw).hexdigest()=='0b98d3c5cba9e2375cb19d0357a1376dd7dffdda96f616a1297d181c7dacbdae';plan=json.loads(raw)
for n,h in plan['source_sha256'].items():assert hashlib.sha256((w/n).read_bytes()).hexdigest()==h
def read(path,bound=32*1024*1024):
 for attempt in range(20):
  raw=path.read_bytes();assert len(raw)<=bound
  try:return json.loads(raw),hashlib.sha256(raw).hexdigest()
  except json.JSONDecodeError:
   if attempt==19:raise
   time.sleep(.05)
def process(identity):
 try:
  p=Path('/proc',str(identity['pid']));fields=(p/'stat').read_bytes().rsplit(b')',1)[1].split();original=int(fields[19])==identity['start_ticks'] and fields[0]!=b'Z';return dict(identity,original_alive=original,expected_entry_matches=not original or identity['entry'].encode() in (p/'cmdline').read_bytes().split(b'\0'))
 except (FileNotFoundError,ProcessLookupError):return dict(identity,original_alive=False)
out={'read_only':True,'node_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'processes':{},'phase':'not-created','long_duration_accepted':False}
for key,name in [('runner','launch.json'),('worker','worker.json'),('readonly_recorder','observer-launch.json')]:
 if (w/name).exists():out['processes'][key]=process(read(w/name)[0])
if (root/'report.json').exists():
 report,h=read(root/'report.json');out.update(phase=report['phase'],main_report_sha256=h,main_checks=len(report['tests']),main_passed=sum(v['passed'] for v in report['tests']),stages=report['phases'],error=report.get('error'),roles={r:{k:v.get(k) for k in ['phase','fixed_processes','original_start_script_unmodified','same_container_mount_paths','actual_three_controls','original_controls','fixed_controls','fixture_identity']} for r,v in report['roles'].items()})
 out['campaigns']={}
 for stage in plan['stages']:
  path=root/('campaign-'+stage['phase'])/'report.json'
  if not path.exists():continue
  c,h=read(path);out['campaigns'][stage['phase']]={'phase':c['phase'],'report_sha256':h,'cycles':len(c['backups']),'last_cycle':c['backups'][-1] if c['backups'] else None,'both_workers_started_epoch':c.get('both_workers_started_epoch'),'roles':{r:{'host_samples':len(v.get('samples',[])),'last_sample':v.get('samples',[])[-1] if v.get('samples') else None,'workload':v.get('workload')} for r,v in c['roles'].items()}}
if (w/'exit.json').exists():out['exit']=read(w/'exit.json')[0]
directory=w/'readonly-observation';daily=sorted(directory.glob('*.jsonl')) if directory.exists() else []
if daily:
 with daily[-1].open('rb') as stream:
  stream.seek(max(0,daily[-1].stat().st_size-131072));tail=stream.read();lines=tail.rsplit(b'\n',1)[0].splitlines() if b'\n' in tail else []
  if lines:out['readonly_recorder_latest']=json.loads(lines[-1])
if (directory/'exit.json').exists():out['readonly_recorder_exit']=read(directory/'exit.json')[0]
out['independent_baseline_guards']={}
if out['phase']=='measuring-baseline':
 for key,row in report['roles'].items():
  group=Path(row['fixture_identity']['group']);assert group.resolve()==group and group.is_dir();actual={n:(group/n).read_text().strip() for n in plan['control_files']};assert actual==row['original_controls'];bound={}
  for name,identity in row['fixed_processes'].items():
   fields=Path('/proc',str(identity['pid']),'stat').read_bytes().rsplit(b')',1)[1].split();assert int(fields[19])==identity['start_ticks'] and fields[0]!=b'Z';membership=next(x.split('::',1)[1].lstrip('/') for x in Path('/proc',str(identity['pid']),'cgroup').read_text().splitlines() if x.startswith('0::'));assert membership==str(group.relative_to('/sys/fs/cgroup'));bound[name]={'pid':identity['pid'],'start_ticks':identity['start_ticks'],'original_alive':True,'own_group':True}
  assert hashlib.sha256(Path('/proc',str(row['fixed_processes']['Agent']['pid']),'exe').read_bytes()).hexdigest()==plan['binary_sha256'];out['independent_baseline_guards'][key]={'eight_controls_unchanged':True,'fixed_three_processes':bound,'actual_controls':actual,'actual_running_ELF_matches_frozen':True}
out['summary']={'phase':out['phase'],'node_utc':out['node_utc'],'processes':{k:{j:v.get(j) for j in ['pid','start_ticks','original_alive','expected_entry_matches']} for k,v in out['processes'].items()},'main_checks':out.get('main_checks'),'main_passed':out.get('main_passed'),'independent_baseline_guard_roles':len(out['independent_baseline_guards']),'campaigns':{k:{j:v.get(j) for j in ['phase','cycles','both_workers_started_epoch']} for k,v in out.get('campaigns',{}).items()},'long_duration_accepted':False,'terminal':out.get('exit'),'recorder_sample_utc':out.get('readonly_recorder_latest',{}).get('utc')};print(json.dumps(out))
