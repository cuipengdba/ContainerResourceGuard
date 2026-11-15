"""Replay a dated startup snapshot; never accept long duration from startup."""
from pathlib import Path
import argparse,base64,gzip,hashlib,json

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();raw=a.evidence.read_bytes();assert len(raw)<1024**2
 with gzip.GzipFile(fileobj=a.evidence.open('rb')) as f:body=f.read(2*1024**2+1)
 assert len(body)<=2*1024**2;v=json.loads(body);files={}
 assert len(v['files'])==8 and not v['long_duration_accepted'] and not v['runtime_inherited'] and v['identities_alive_and_entry_matches'] and v['frozen_source_members_verified']==16
 for n,item in v['files'].items():
  assert not n.startswith('/') and '..' not in Path(n).parts
  b=base64.b64decode(item['base64'],validate=True);assert len(b)==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256'];files[n]=b
 assert hashlib.sha256(files['tools/plan.json']).hexdigest()=='ea19e85c8e8690845449ce36b9e3be8266282015cb8e8ba8ed6eec207187370c'
 plan=json.loads(files['tools/plan.json']);launch=json.loads(files['tools/launch.json']);worker=json.loads(files['tools/worker.json']);observer=json.loads(files['tools/observer-launch.json']);r=json.loads(files['results/report.json']);c=json.loads(files['results/campaign-baseline/report.json'])
 assert launch['single_launch_guard'] and launch['job_sha256']==r['job_sha256']==plan['job_sha256'] and launch['plan_sha256']==r['plan_sha256']==hashlib.sha256(files['tools/plan.json']).hexdigest()
 assert launch['node_admission']['admitted'] and launch['admission']['phase']=='ready' and not launch['admission']['blocking_pods'] and not launch['admission']['business_fixture_created'] and not launch['admission']['long_measurement_started']
 assert observer['read_only_Kubernetes_queries'] and not observer['product_or_business_signals']
 assert len({(v['pid'],v['start_ticks']) for v in [launch,worker,observer]})==3
 assert r['phase']=='measuring-baseline' and not r['runtime_inherited'] and not r['stable_release_accepted'] and len(r['tests'])==12 and all(t['passed'] for t in r['tests'])
 assert len(r['roles'])==2
 for row in r['roles'].values():
  assert row['phase']=='ready-for-baseline' and row['original_start_script_unmodified'] and row['same_container_mount_paths'] and row['actual_controls']==row['original_controls']
  assert set(row['fixed_processes'])=={'PID1','Agent','cache'}
 assert c['phase']=='measuring' and c['both_workers_started_epoch'] and set(c['roles'])=={'dbs','hisdbs'}
 assert [(s['phase'],s['seconds'],s['cycles']) for s in plan['stages']]==[('baseline',86400,4),('enforce',86400,4),('acceptance',604800,28)] and plan['minimum_duration_seconds']==777600
 query=r['last_exclusivity_observation'];assert query['read_only'] and not query['blocked'] and query['elapsed_seconds']<15 and query['budget_seconds']==15
 for node in v['node_conditions']:
  state={c['type']:c['status'] for c in node};assert state['Ready']=='True' and all(state[k]=='False' for k in ['MemoryPressure','DiskPressure','PIDPressure'])
 assert not v['private_command_receipts']['raw_outputs_published']
 print(json.dumps({'schema':'crg-long1728-initial-offline-review-v1','phase':'startup-snapshot-verified','observed_utc':v['observed_utc'],'archive_sha256':hashlib.sha256(raw).hexdigest(),'members_verified':8,'startup_checks':12,'native_phase_at_snapshot':'measuring-baseline','launch_utc':launch['node_utc'],'both_native_started_epoch':c['both_workers_started_epoch'],'original_processes':{k:{f:row[f] for f in ['pid','start_ticks','entry']} for k,row in [('runner',launch),('worker',worker),('readonly_recorder',observer)]},'source_sha256':launch['source_sha256'],'same_original_start_and_observe_controls':True,'runtime_inherited':False,'stable_release_accepted':False,'long_duration_accepted':False,'boundary':'Dated native snapshot only; no continuous-duration or future process-health acceptance'},indent=2))

if __name__=='__main__':main()
