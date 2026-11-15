"""Private independent replay, no candidate execution or host changes."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,zipfile
P=argparse.ArgumentParser();P.add_argument('--zip',type=Path,required=True);P.add_argument('--expect-failure',action='store_true');A=P.parse_args();sha=lambda b:hashlib.sha256(b).hexdigest()
raw=A.zip.read_bytes();assert len(raw)<4*1024**2
with zipfile.ZipFile(A.zip) as z:
 infos=z.infolist();assert len(infos)==len(set(i.filename for i in infos))<=150 and sum(i.file_size for i in infos)<=16*1024**2
 files={}
 for i in infos:
  p=PurePosixPath(i.filename);assert not p.is_absolute() and '..' not in p.parts and '\\' not in i.filename and i.file_size<=2*1024**2
  if not i.is_dir():files[i.filename]=z.read(i)
plan=json.loads(files['plan.json']);r=json.loads(files['results/report.json']);env=json.loads(files['environment.json']);assert sha(files['driver.py'])==r['driver_sha256']==plan['test_inputs_sha256']['tests/live-cpu-capacity-v1/driver.py'] and sha(files['main.go'])==plan['test_inputs_sha256']['tests/native-holder/main.go'] and r['plan_sha256']==sha(files['plan.json']) and env['source50_verified']
assert r['source_revision']==plan['source_revision'] and r['binary_sha256']==plan['binary_sha256'][r['arch']] and r['kernel']==env['kernel'] and r['arch']==env['machine'].replace('x86_64','amd64').replace('aarch64','arm64')
assert len(r['tests'])==plan['expected_checks']==56 and len(r['cases'])==2 and not r.get('error')
assert not r['cleanup']['errors'] and r['cleanup']['original_online_mask_restored'] and r['cleanup']['all_owned_containers_removed']
numbers=lambda value:{n for part in value.split(',') for n in range(int(part.split('-')[0]),int(part.split('-')[-1])+1)}
original=numbers(r['initial_online_mask']);cpu=r['selected_CPU']['number'];assert len(original)>=2 and cpu in original and cpu!=0 and len(r['hotplug_events'])==9
events=r['hotplug_events'];assert sum(not e['online'] for e in events)==4
for e in events:
 assert e['actual_sysfs_write'] and e['cpu']==cpu
 assert numbers(e['after'])==(original if e['online'] else original-{cpu})
assert numbers(events[-1]['after'])==original
actual_failures=[]
for case in r['cases']:
 assert case['name'] in ['uncapped-percent','external-cap'] and len(case['samples'])==5 and len(case['registered_agents'])==1
 assert case['configuration']['cpu_percent']==case['configuration']['memory_percent']==case['configuration']['io_percent']==20 and case['configuration']['io_calibration']=='off' and case['configuration']['interval_seconds']==1
 assert case['tight_external_cap']==(case['name']=='external-cap')
 for sample,label in zip(case['samples'],['initial','offline-0','online-0','offline-1','online-1']):
  assert sample['label']==label and sample['agent']==case['registered_agents'] and sample['online_count']==len(numbers(sample['online_mask']))
  cpus=original-{cpu} if label.startswith('offline') else original;assert numbers(sample['online_mask'])==cpus
  expected=('10000' if case['tight_external_cap'] else str(len(cpus)*20000))+' 100000';assert sample['expected_cpu_max']==expected
  statusraw=files['results/'+case['name']+'/'+label+'-status.json'];freshraw=files['results/'+case['name']+'/'+label+'-fresh-plan.json'];assert sha(statusraw)==sample['status_sha256'] and sha(freshraw)==sample['fresh_plan_sha256'];status=json.loads(statusraw);fresh=json.loads(freshraw)
  assert fresh['environment']['host_online_cpus']==sample['fresh_cli_online_cpus']==len(cpus)
  assert next(s['value'] for s in fresh['settings'] if s['file']=='cpu.max')==expected
  assert status['plan']['environment']['host_online_cpus']==sample['reported_online_cpus']
  assert all(v==case['original_controls'][k] for k,v in sample['actual_controls'].items() if k!='cpu.max')
  actual=sample['actual_controls']['cpu.max'].split();before=case['original_controls']['cpu.max'].split();assert int(actual[0])*int(before[1])<=int(before[0])*int(actual[1])
  for suffix,passed in [('same-single-Agent-and-PID1',True),('current-host-capacity-in-live-status',sample['reported_online_cpus']==len(cpus)),('live-percent-kernel-quota',sample['actual_controls']['cpu.max']==expected),('fresh-CLI-agrees-with-independent-host',True),('other-seven-controls-retained',True)]:
   name=case['name']+':'+label+':'+suffix;rows=[t for t in r['tests'] if t['name']==name];assert len(rows)==1 and rows[0]['passed']==passed
   if not passed:actual_failures.append(name)
 restore=json.loads(files['results/'+case['name']+'/restore.json']);assert restore['state']=='restored'
 journal_name='results/'+case['name']+'/journal.json'
 if journal_name in files:assert not json.loads(files[journal_name])['mutations']
 else:assert case['tight_external_cap'] and all(not sample['journal_present'] and sample['actual_controls']==case['original_controls'] for sample in case['samples'])
 for suffix in ['restore-original-eight-controls','no-OOM-kill','owned-container-leaf-and-processes-absent']:
  rows=[t for t in r['tests'] if t['name']==case['name']+':'+suffix];assert len(rows)==1 and rows[0]['passed']
assert len(actual_failures)==sum(not t['passed'] for t in r['tests'])
if A.expect_failure:
 assert r['phase']=='failed' and len(actual_failures)==6
 assert all(':offline-' in name and ('current-host-capacity' in name or (name.startswith('uncapped-percent') and 'live-percent-kernel-quota' in name)) for name in actual_failures)
else:assert r['phase']=='passed' and not actual_failures
print(json.dumps({'schema':'crg-live-cpu-capacity-replay-v1','phase':'confirmed-old-live-capacity-defect' if A.expect_failure else 'passed','native_phase':r['phase'],'source_revision':r['source_revision'],'binary_sha256':r['binary_sha256'],'driver_sha256':r['driver_sha256'],'archive_sha256':sha(raw),'members':len(files),'kernel':r['kernel'],'arch':r['arch'],'checks':56,'passed_checks':56-len(actual_failures),'failure_names':actual_failures,'real_cpu_offline_events':4,'original_host_CPU_mask_restored':True,'own_container_process_control_cleanup_verified':True,'fresh_CLI_correct_while_old_running_Agent_stale':A.expect_failure,'vendor_business_qualification':False,'whole_P06_4_complete':False},indent=2))
