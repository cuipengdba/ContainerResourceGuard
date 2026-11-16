"""Prepare a separate formal18 +4 auxiliary run only AFTER comparison closure.

Does not connect, upload, launch or re-use any measured time or data.
"""
from pathlib import Path
import hashlib,json
T=Path(__file__).parent;sha=lambda b:hashlib.sha256(b).hexdigest();enc=lambda v:(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
qpath=T/'crg-r1853-independent-qualification.json'
assert qpath.exists(),'comparison terminal selected originals must first be independently qualified'
q=json.loads(qpath.read_bytes());assert q['phase']=='passed-comparison-only' and q['cleanup_independent'] and len(q['cells'])==4 and q['recorded_checks']==q['passed_checks']==44
assert all(v['full600_completed'] and v['normal_business_passed'] and v['auxiliary_diagnostics_passed'] for v in q['cells'].values())
d=json.loads((T/'crg-r1853-comparison-download.json').read_bytes());D=T/d['destination'];coraw=(D/'coordinator-report.json').read_bytes();co=json.loads(coraw);assert co['phase']=='passed'
for r in d['result']['files']:assert sha((D/r['filename']).read_bytes())==r['sha256']==r['download_sha256']
old=json.loads((T/'crg-r1843-comparison-frozen.json').read_bytes());F=T/old['freeze'];target=T/'crg-r1856-formal-business-freeze';assert not target.exists() and not (T/'crg-r1856-business-frozen.json').exists()
inputs={}
for n,h in old['uploaded_sha256'].items():
 raw=(F/n).read_bytes();assert sha(raw)==h
 if n=='plan.json':continue
 inputs[n]=raw.replace(b'compare1843',b'business1856').replace(b'COMPARE1843',b'BUSINESS1856') if n in ['business-driver.py','runner.py','artifact-transfer.py'] else raw
s=inputs['runner.py'].decode();needle='root.mkdir(mode=0o700);out='
prereq="""p=plan['fixed_comparison_prerequisite'];pr=Path(p['tools']);priorraw=(Path(p['output'])/'report.json').read_bytes();assert sha(priorraw)==p['report_sha256'] and sha((pr/'plan.json').read_bytes())==p['plan_sha256'];prior=json.loads(priorraw);oldplan=json.loads((pr/'plan.json').read_bytes());assert prior['phase']=='passed' and json.loads((pr/'exit.json').read_bytes())['exit']==0 and absent(json.loads((pr/'launch.json').read_bytes()))
assert len(prior['roles'])==4 and all(sha((pr/n).read_bytes())==h for n,h in oldplan['source_sha256'].items())
for row in prior['roles'].values():
 assert row['recorded_checks']==row['passed_checks']==11 and absent(row['driver']) and row['namespace_absent']
 for c in row['cleanup']:
  identity=c['identity'];assert not Path(identity['group']).exists() and not Path(identity['pod_parent']).exists() and all(absent(v) for v in identity['processes']+c['additional_processes'])
assert all(ns_absent(n) for arm in oldplan['namespaces'].values() for n in arm.values())
"""
assert s.count(needle)==1;s=s.replace(needle,prereq+needle).replace("for arm in ['observe','enforce']:","for arm in ['enforce']:").replace("len(out['roles'])==4","len(out['roles'])==2").replace('crg-fixed-observe-enforce-original600-coordinator-v1','crg-fresh-formal18-plus4-auxiliary-original600-v1').replace('fixed one-pair observe/enforce,4 original600 windows plus own wait diagnostics; not formal original18 acceptance','fresh enforce DBS/HISDBS, each original600, original18 checks plus4 auxiliary checks, independently verified before any long start')
inputs['runner.py']=s.encode();p=json.loads((F/'plan.json').read_bytes());p.update(schema='crg-fresh-formal18-plus4-auxiliary-original600-plan-v1',phase='frozen-before-readonly-admission-publication-sole-launch',tools='/var/tmp/crg-business1856-tools-20261116',output='/var/tmp/crg-business1856-results-20261116',matrix=[{'role':r,'mode':'enforce','seconds':600,'repeats':1} for r in ['dbs','hisdbs']],qualification_scope='fresh formal18 original checks plus4 separately counted auxiliary diagnostics; no comparison clock/data transfer')
p['fixed_comparison_prerequisite']={'tools':old['plan']['tools'],'output':old['plan']['output'],'plan_sha256':old['plan_sha256'],'report_sha256':sha(coraw),'independent_qualification_sha256':sha(qpath.read_bytes()),'selected_originals':len(d['result']['files']),'selected_bytes':d['result']['total_bytes']}
p['namespaces']={'enforce':{r:'crg-vendor-lab-business1856-enforce-'+r+'-20261116' for r in ['dbs','hisdbs']}};p['run_ids']={'enforce':{'dbs':'202611161856','hisdbs':'202611161857'}};p['planned_checks']={'enforce_each_role':11,'original_business_total':18,'auxiliary_total':4,'total':22};p['criteria']['original18_accepted_by_this_comparison']=False;p['criteria']['formal_original_checks_separate']=18;p['criteria']['auxiliary_checks_separate']=4
p['source_sha256']={n:sha(raw) for n,raw in inputs.items()};p['job_sha256']=sha(inputs['business-driver.py']);p['final_ELF_identity']['actual_new_binary_business_accepted']=False
for n,raw in inputs.items():
 dest=target/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
raw=enc(p);(target/'plan.json').write_bytes(raw);inputs['plan.json']=raw
f={'schema':'crg-fresh-formal18-plus4-frozen-v1','phase':'frozen-not-uploaded-not-launched','freeze':target.name,'source_commit':old['source_commit'],'job_sha256':p['job_sha256'],'plan_sha256':sha(raw),'plan':p,'uploaded_sha256':{n:sha(raw) for n,raw in inputs.items()},'source_worker_and_timeline_exact':True,'formal_original18_accepted':False,'new_long_started':False,'stable_release_accepted':False}
(T/'crg-r1856-business-frozen.json').write_bytes(enc(f));print(json.dumps({'phase':f['phase'],'inputs':len(inputs),'planned_original_checks':18,'planned_auxiliary_checks':4}))
