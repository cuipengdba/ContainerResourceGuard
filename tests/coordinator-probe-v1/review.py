"""Bounded offline replay of original Linux coordinator-probe evidence."""
from pathlib import Path
import argparse,base64,gzip,hashlib,json

EXPECTED={
 'healthy-list','healthy-podlist','other-running','other-pending','other-succeeded','other-failed',
 'one-error-then-success','two-errors-then-success','three-errors-closed','invalid-json','wrong-kind',
 'missing-items','missing-UID','non-pod','bad-UTF8','original15s-hang','shrinking-deadline',
 'budget-over15-rejected','budget-over15-rejected-exact','oversize-success-closed',
 'generic-no-mutation-retry-exact-nonUTF8','launch-error-recorded',
 'unsafe-and-symlink-directory-rejected','receipt-capacity-closed-originals-preserved'}

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
 raw=args.evidence.read_bytes();assert len(raw)<1024**2
 with gzip.GzipFile(fileobj=args.evidence.open('rb')) as stream:body=stream.read(8*1024**2+1)
 assert len(body)<=8*1024**2;value=json.loads(body);files={}
 assert len(value['files'])==114
 for name,item in value['files'].items():
  assert not name.startswith('/') and '..' not in Path(name).parts
  data=base64.b64decode(item['base64'],validate=True);assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'];files[name]=data
 manifest=value['frozen']
 for name,item in manifest['files'].items():assert hashlib.sha256(files['source/'+name]).hexdigest()==item['sha256'] and len(files['source/'+name])==item['bytes']
 r=json.loads(files['native/report.json']);cases={v['name']:v for v in r['cases']};assert len(cases)==24 and set(cases)==EXPECTED and r['phase']=='passed' and r['passed_checks']==24 and all(v['passed'] for v in cases.values())
 assert not r['kubernetes_mutations'] and not r['CRG_executed'] and r['all_fake_processes_absent']
 assert r['module_sha256']==manifest['files']['probe.py']['sha256'] and r['driver_sha256']==manifest['files']['native.py']['sha256']
 for name,row in cases.items():
  for receipt in row.get('receipts',[]):
   assert receipt['elapsed_seconds']>=0 and receipt['reason'] in ['nonzero-exit','invalid-inventory','timeout']
   for axis,item in receipt['outputs'].items():
    data=files['native/'+name+'/receipts/'+item['file']];assert len(data)==item['retained_bytes'] and hashlib.sha256(data).hexdigest()==item['retained_sha256'] and item['truncated']==(item['original_bytes']>item['retained_bytes'])
  if 'calls' not in row:continue
  original=[json.loads(x) for x in files['native/'+name+'/calls.jsonl'].splitlines()] if row['calls'] else []
  assert original==row['calls']
  assert len(original)<=3 and all(v['argv'][:5]==['get','pods','-A','-o','json'] for v in original)
  if row['query']:
   q=row['query'];assert q['budget_seconds']==15 and q['elapsed_seconds']<15 and q['read_only'] and len(q['attempts'])==len(original)
 for name in ['one-error-then-success','two-errors-then-success','three-errors-closed']:
  row=cases[name];assert len(row['receipts'])==int(name=='one-error-then-success')+2*int(name=='two-errors-then-success')+3*int(name=='three-errors-closed')
  assert bool(row['error'])==(name=='three-errors-closed')
 for name in ['other-running','other-pending','other-succeeded','other-failed']:assert len(cases[name]['calls'])==1 and len(cases[name]['query']['blocked'])==1
 for name in ['invalid-json','wrong-kind','missing-items','missing-UID','non-pod','bad-UTF8']:assert len(cases[name]['calls'])==1 and cases[name]['error'] and cases[name]['receipts'][0]['reason']=='invalid-inventory'
 row=cases['original15s-hang'];assert 14.5<=row['elapsed_seconds']<15.8 and len(row['calls'])==1 and row['receipts'][0]['reason']=='timeout'
 for axis,data in [('stdout',b'partial-out\n'),('stderr',b'partial-error\n')]:assert files['native/original15s-hang/receipts/'+row['receipts'][0]['outputs'][axis]['file']]==data
 row=cases['shrinking-deadline'];assert row['calls'][0]['argv'][-1]=='--request-timeout=10000ms' and int(row['calls'][1]['argv'][-1].split('=')[1][:-2])<4800 and row['elapsed_seconds']<15
 row=cases['oversize-success-closed']['receipts'][0]['outputs']['stdout'];assert row['original_bytes']==4194305 and row['retained_bytes']==4194304 and row['truncated']
 row=cases['generic-no-mutation-retry-exact-nonUTF8']['receipt'];assert row['exit']==7
 for axis,data in [('stdout',b'\xff\x00A'),('stderr',b'\xfe\x00B')]:assert files['native/generic/receipts/'+row['outputs'][axis]['file']]==data
 calls=[json.loads(x) for x in files['native/generic/calls.jsonl'].splitlines()];assert len(calls)==1 and calls[0]['argv']==['create','fake-only']
 assert not r['actual_cluster_readonly']['blocked'] and r['actual_cluster_readonly']['read_only'] and r['actual_cluster_readonly']['elapsed_seconds']<15
 print(json.dumps({'schema':'crg-coordinator-probe-offline-review-v1','phase':'passed','passed_native_cases':24,'members_verified':len(files),'archive_sha256':hashlib.sha256(raw).hexdigest(),'module_sha256':r['module_sha256'],'driver_sha256':r['driver_sha256'],'read_only_observation_total_budget_seconds':15,'max_readonly_attempts':3,'mutating_retries':0,'actual_cluster_readonly':True,'product_changed':False,'old_API_failure_cause_known':False,'business_long_duration_accepted':False},indent=2))

if __name__=='__main__':main()
