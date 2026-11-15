"""Linux-only fake-CLI faults plus one actual read-only cluster inventory.

Never creates Pods, runs CRG or alters cgroups. An explicit unique work directory
retains the original fake-command outputs and process identities for review.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,stat,subprocess,sys,time

FAKE = r'''#!/usr/bin/env python3
from pathlib import Path
import json,os,sys,time
w=Path(__file__).parent
p=w/'calls.jsonl'
fields=Path('/proc/self/stat').read_bytes().rsplit(b')',1)[1].split()
prior=p.read_text().splitlines() if p.exists() else []
with p.open('a') as f:f.write(json.dumps({'pid':os.getpid(),'start_ticks':int(fields[19]),'argv':sys.argv[1:]})+'\n')
options=json.loads((w/'options.json').read_bytes());step=options['steps'][min(len(prior),len(options['steps'])-1)]
os.write(1,step.get('stdout','').encode()+bytes.fromhex(step.get('stdout_hex','')))
os.write(2,step.get('stderr','').encode()+bytes.fromhex(step.get('stderr_hex','')))
if step.get('flood'):os.write(1,b'x'*step['flood'])
time.sleep(step.get('sleep',0))
raise SystemExit(step.get('exit',0))
'''

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--work',required=True);args=parser.parse_args()
 work=Path(args.work);assert work.is_absolute() and str(work).startswith('/var/tmp/crg-probe1726-') and not work.exists()
 os.umask(0o077);work.mkdir(mode=0o700)
 source=Path(__file__).with_name('probe.py');spec=importlib.util.spec_from_file_location('probe',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 report={'schema':'crg-coordinator-probe-native-v1','phase':'running','module_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'work':str(work),'cases':[],'scope':'Actual Linux fake CLI failures; one real read-only inventory; no original API failure recreation or vendor business qualification','kubernetes_mutations':False,'CRG_executed':False}
 pod=lambda ns,name='p':{'apiVersion':'v1','kind':'Pod','metadata':{'namespace':ns,'name':name,'uid':'fake-'+ns},'status':{'phase':'Running'}}
 listing=lambda items,kind='List':json.dumps({'apiVersion':'v1','kind':kind,'items':items})
 own='crg-vendor-lab-probe1726';valid=listing([pod(own),pod('ordinary')])
 all_identities=[]
 def case(name,steps,expected_calls,expect_failure=False,expected_blocked=0,budget=15,**kw):
  directory=work/name;directory.mkdir();receipt=directory/'receipts';fake=directory/'kubectl';fake.write_text(FAKE);fake.chmod(0o700);(directory/'options.json').write_text(json.dumps({'steps':steps}))
  start=time.monotonic();error=None;summary=None;blocked=None
  try:blocked,summary=m.exclusive(own,receipt,kubectl=str(fake),budget_seconds=budget,**kw)
  except (RuntimeError,ValueError) as e:error=type(e).__name__+': '+str(e)
  elapsed=time.monotonic()-start;calls=[json.loads(x) for x in (directory/'calls.jsonl').read_text().splitlines()] if (directory/'calls.jsonl').exists() else []
  assert len(calls)==expected_calls,(name,calls,error)
  assert bool(error)==expect_failure,(name,error)
  if not expect_failure:assert len(blocked)==expected_blocked
  assert elapsed<budget+.8,(name,elapsed)
  for call in calls:assert call['argv'][:5]==['get','pods','-A','-o','json']
  metas=[json.loads(p.read_bytes()) for p in receipt.glob('*.json')]
  for meta in metas:
   for output in meta['outputs'].values():
    p=receipt/output['file'];raw=p.read_bytes();assert len(raw)==output['retained_bytes'] and hashlib.sha256(raw).hexdigest()==output['retained_sha256'] and stat.S_IMODE(p.stat().st_mode)==0o600
  row={'name':name,'passed':True,'elapsed_seconds':elapsed,'calls':calls,'error':error,'query':summary,'receipts':metas};report['cases'].append(row);all_identities.extend(calls)
  return row,directory
 case('healthy-list',[{'stdout':valid}],1)
 case('healthy-podlist',[{'stdout':listing([],kind='PodList')}],1)
 for phase in ['Running','Pending','Succeeded','Failed']:
  other=pod('crg-vendor-lab-other');other['status']['phase']=phase
  case('other-'+phase.lower(),[{'stdout':listing([other])},{'stdout':valid}],1,expected_blocked=1)
 case('one-error-then-success',[{'stderr':'EOF from fake server\n','exit':1},{'stdout':valid}],2)
 case('two-errors-then-success',[{'stderr':'fake unavailable\n','exit':1},{'stderr':'fake timeout\n','exit':1},{'stdout':valid}],3)
 case('three-errors-closed',[{'stderr':'fake unavailable\n','exit':1}],3,True)
 for name,output in [('invalid-json','{'),('wrong-kind',listing([],kind='SecretList')),('missing-items','{"apiVersion":"v1","kind":"List"}'),('missing-UID',listing([{'apiVersion':'v1','kind':'Pod','metadata':{'namespace':'ordinary','name':'p'}}])),('non-pod',listing([{'kind':'Secret','apiVersion':'v1'}])),('bad-UTF8','')]:
  step={'stdout':output}
  if name=='bad-UTF8':step['stdout_hex']='fffe'
  case(name,[step,{'stdout':valid}],1,True)
 row,directory=case('original15s-hang',[{'stdout':'partial-out\n','stderr':'partial-error\n','sleep':25}],1,True)
 assert 14.5<=row['elapsed_seconds']<15.8
 receipt=row['receipts'][0];assert receipt['reason']=='timeout' and (directory/'receipts'/receipt['outputs']['stdout']['file']).read_bytes()==b'partial-out\n' and (directory/'receipts'/receipt['outputs']['stderr']['file']).read_bytes()==b'partial-error\n'
 row,_=case('shrinking-deadline',[{'stderr':'slow-fake-error\n','sleep':10.2,'exit':1},{'stdout':valid}],2)
 assert row['calls'][0]['argv'][-1]=='--request-timeout=10000ms'
 assert int(row['calls'][1]['argv'][-1].split('=')[1][:-2])<4800
 case('budget-over15-rejected',[{'stdout':valid}],0,True,budget=15,max_attempts=4)
 try:m.exclusive(own,work/'bad-budget',budget_seconds=15.01)
 except ValueError:report['cases'].append({'name':'budget-over15-rejected-exact','passed':True})
 else:raise AssertionError('widened deadline accepted')
 row,directory=case('oversize-success-closed',[{'flood':m.STDOUT_LIMIT+1}],1,True)
 assert row['receipts'][0]['outputs']['stdout']['truncated'] and row['receipts'][0]['outputs']['stdout']['original_bytes']==m.STDOUT_LIMIT+1
 directory=work/'generic';directory.mkdir();fake=directory/'kubectl';fake.write_text(FAKE);fake.chmod(0o700);(directory/'options.json').write_text(json.dumps({'steps':[{'stdout_hex':'ff0041','stderr_hex':'fe0042','exit':7}]}));receipts=directory/'receipts'
 result=m.recorded_run([str(fake),'create','fake-only'],receipts,check=False)
 assert result.returncode==7 and len((directory/'calls.jsonl').read_text().splitlines())==1
 meta=json.loads(result.failure_receipt.read_bytes());assert (receipts/meta['outputs']['stdout']['file']).read_bytes()==b'\xff\x00A' and (receipts/meta['outputs']['stderr']['file']).read_bytes()==b'\xfe\x00B'
 report['cases'].append({'name':'generic-no-mutation-retry-exact-nonUTF8','passed':True,'receipt':meta});all_identities.extend(json.loads(x) for x in (directory/'calls.jsonl').read_text().splitlines())
 missing=work/'missing-executable-receipts'
 try:m.recorded_run(['/nonexistent/crg-probe1726'],missing)
 except m.CommandFailure as e:assert json.loads(e.receipt.read_bytes())['reason']=='launch-error'
 else:raise AssertionError('missing executable accepted')
 report['cases'].append({'name':'launch-error-recorded','passed':True})
 unsafe=work/'unsafe';unsafe.mkdir();unsafe.chmod(0o755)
 link=work/'symlink';link.symlink_to(unsafe)
 for path in [unsafe,link]:
  try:m.private_directory(path)
  except RuntimeError:pass
  else:raise AssertionError('unsafe receipt directory accepted')
 report['cases'].append({'name':'unsafe-and-symlink-directory-rejected','passed':True})
 full=work/'full';full.mkdir();p=full/'sentinel';p.write_bytes(b'preserve');p2=full/'sparse';p2.touch();p2.open('r+b').truncate(m.STORE_LIMIT)
 try:m.failure_receipt(full,['fake'],b'',b'','fake',0)
 except RuntimeError:assert p.read_bytes()==b'preserve' and len(list(full.iterdir()))==2
 else:raise AssertionError('full receipt budget accepted')
 report['cases'].append({'name':'receipt-capacity-closed-originals-preserved','passed':True});p2.unlink()
 blocked,actual=m.exclusive(own,work/'actual-readonly');assert not blocked
 report['actual_cluster_readonly']=actual
 def absent(identity):
  try:
   v=Path('/proc',str(identity['pid']),'stat').read_bytes().rsplit(b')',1)[1].split();return v[0]==b'Z' or int(v[19])!=identity['start_ticks']
  except FileNotFoundError:return True
 assert all(absent(p) for p in all_identities)
 report.update(phase='passed',passed_checks=len(report['cases']),all_fake_processes_absent=True,process_identities=all_identities)
 (work/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'summary':{'phase':'passed','passed_checks':report['passed_checks'],'module_sha256':report['module_sha256'],'driver_sha256':report['driver_sha256'],'all_fake_processes_absent':True,'work':str(work),'actual_cluster_readonly':True}}))

if __name__=='__main__':main()
