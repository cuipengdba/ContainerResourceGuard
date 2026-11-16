"""Prepare a zero-clock long run only after fresh original18+4 are qualified.

No SSH, fixture creation, test launch, original output editing or clock reuse.
"""
from pathlib import Path
import ast,base64,gzip,hashlib,json
T=Path(__file__).parent;B=T.parent;sha=lambda b:hashlib.sha256(b).hexdigest();enc=lambda v:(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
qpath=T/'crg-r1871-independent-qualification.json';assert qpath.exists(),'fresh formal18 plus4 must first complete independent exact verification'
qraw=qpath.read_bytes();q=json.loads(qraw);assert q['phase']=='passed-formal18-plus4-only' and q['formal_original18_accepted'] and q['cleanup_independent'] and q['recorded_checks']==q['passed_checks']==22
assert q['original_business_checks']==18 and q['auxiliary_checks']==4 and len(q['cells'])==2 and all(v['full600_completed'] and v['normal_business_passed'] and v['auxiliary_diagnostics_passed'] for v in q['cells'].values())
d=json.loads((T/'crg-r1871-formal-download.json').read_bytes());D=T/d['destination'];formal=json.loads((T/'crg-r1856-business-frozen.json').read_bytes());FF=T/formal['freeze'];coraw=(D/'coordinator-report.json').read_bytes();co=json.loads(coraw);assert co['phase']=='passed'
for r in d['result']['files']:assert sha((D/r['filename']).read_bytes())==r['sha256']==r['download_sha256']
for role in ['dbs','hisdbs']:
 report=json.loads((D/('enforce-'+role+'-report.json')).read_bytes());reference=json.loads((T/'crg-r1853-comparison-exact'/('enforce-'+role+'-report.json')).read_bytes())
 assert len(report['tests'])==11 and all(v['passed'] for v in report['tests'])
 assert [v['name'] for v in report['tests'][:9]]==[v['name'] for v in reference['tests'][:9]] and all(v.get('scope')!='auxiliary-diagnostic' for v in report['tests'][:9]) and all(v.get('scope')=='auxiliary-diagnostic' for v in report['tests'][9:])
old=json.loads((T/'crg-r1728-long-frozen.json').read_bytes());OF=T/old['freeze'];N=T/'crg-r1880-long-freeze';assert not N.exists() and not (T/'crg-r1880-long-frozen.json').exists()
assert all(sha((OF/n).read_bytes())==h for n,h in old['uploaded_sha256'].items())
inputs={n:(OF/n).read_bytes() for n in old['plan']['source_sha256']}
for n in ['binaries/crg-linux-amd64','tests/vendor-soak-campaign.py','tests/vendor-soak-load.py']:
 inputs[n]=(FF/n).read_bytes();assert sha(inputs[n])==formal['uploaded_sha256'][n]
ci=(B/'ContainerResourceGuard-integration/docs/test-results-live-capacity-native-CI-v2.json').read_bytes();civ=json.loads(ci);assert civ['phase']=='passed' and civ['source_revision']==formal['source_commit'] and civ['actual_total_checks']==284 and civ['all_actual_controller_programs_match_frozen_final_ELFs'];inputs['CI-qualification.json']=ci
projection={'schema':'crg-fresh-formal18-original-checks-projection-v1','phase':'passed','source_commit':formal['source_commit'],'job_sha256':formal['job_sha256'],'plan_sha256':formal['plan_sha256'],'coordinator_report_sha256':sha(coraw),'planned_checks':18,'recorded_checks':18,'passed_checks':18,'auxiliary_checks_passed':4,'native_whole600_each_role':True,'independent_qualification_sha256':sha(qraw),'original_check_names_equal_previously_frozen9_each_role':True,'all22_and_cleanup_qualified':True,'no_time_data_or_source_transfer':True,'formal_original18_accepted':True,'stable_release_accepted':False};inputs['business-qualification.json']=enc(projection);inputs['formal18-independent.json']=qraw
oldterminal=json.loads(gzip.decompress((B/'ContainerResourceGuard-integration/docs/test-evidence-final-v1-long1728-terminal.json.gz').read_bytes()));record=next(v for v in oldterminal['files'] if v['name']=='results/report.json');oldraw=base64.b64decode(record['base64']);assert sha(oldraw)==record['sha256']=='7adb3ba40455282f546aa90f727f1a13476f097f989f2f786a761f76bc40c733';ended=json.loads(oldraw);assert ended['phase']=='failed' and ended['error']=='explicit long-test stop requested' and ended['namespace_absent'] and not ended.get('cleanup_errors')
s=inputs['job.py'].decode().replace('crg-final1728','crg-final1880').replace('crg-vendor-lab-final1728','crg-vendor-lab-final1880').replace('CRG_FINAL1728_LONG','CRG_FINAL1880_LONG')
gate=""" oldtools=Path('/var/tmp/crg-final1728-tools-20261116');oldraw=Path('/var/tmp/crg-final1728-results-20261116/report.json').read_bytes();assert sha(oldraw)=='7adb3ba40455282f546aa90f727f1a13476f097f989f2f786a761f76bc40c733';oldterminal=json.loads(oldraw)
 assert oldterminal['phase']=='failed' and oldterminal['error']=='explicit long-test stop requested' and oldterminal['namespace_absent'] and not oldterminal.get('cleanup_errors')
 oldplan=json.loads((oldtools/'plan.json').read_bytes());assert sha((oldtools/'plan.json').read_bytes())=='ea19e85c8e8690845449ce36b9e3be8266282015cb8e8ba8ed6eec207187370c' and all(sha((oldtools/n).read_bytes())==h for n,h in oldplan['source_sha256'].items())
 assert json.loads((oldtools/'exit.json').read_bytes())['exit']==1
 for name in ['launch.json','worker.json','observer-launch.json']:assert absent(json.loads((oldtools/name).read_bytes()))
 for role,row in oldterminal['roles'].items():
  assert not Path(row['fixture_identity']['group']).exists() and not Path(row['fixture_identity']['pod_parent']).exists() and all(absent(p) for p in oldterminal['cleanup'][role]['registered_processes'])
 assert not run(['kubectl','get','namespace',oldterminal['namespace'],'--ignore-not-found','-o','json','--request-timeout=5s'],timeout=10).stdout.strip()
 assert q['auxiliary_checks_passed']==4 and q['native_whole600_each_role'] and q['all22_and_cleanup_qualified'] and q['original_check_names_equal_previously_frozen9_each_role']
 assert q['independent_qualification_sha256']==sha((candidates/'formal18-independent.json').read_bytes())
"""
needle=' available=reserve(28);blocked=exclusive();';assert s.count(needle)==1;s=s.replace(needle,gate+needle);ast.parse(s);inputs['job.py']=s.encode()
def functions(raw):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
normalized_old=(OF/'job.py').read_bytes().replace(b'crg-final1728',b'crg-final1880').replace(b'crg-vendor-lab-final1728',b'crg-vendor-lab-final1880').replace(b'CRG_FINAL1728_LONG',b'CRG_FINAL1880_LONG')
before,after=functions(normalized_old),functions(inputs['job.py']);assert {n for n,v in before.items() if after.get(n)!=v}=={'admission'} and set(before)==set(after)
inputs['runner.py']=inputs['runner.py'].replace(b'crg-final1728',b'crg-final1880').replace(b'CRG_FINAL1728_LONG',b'CRG_FINAL1880_LONG')
inputs['campaign-wrapper.py']=inputs['campaign-wrapper.py'].replace(old['plan']['campaign_pins']['campaign_script_sha256'].encode(),sha(inputs['tests/vendor-soak-campaign.py']).encode())
p=json.loads((OF/'plan.json').read_bytes());p.update(schema='crg-new-source37-zero-clock-24h-24h-seven-day-plan-v1',phase='fresh-zero-time-frozen-before-native-preflight-publication-sole-launch',tools='/var/tmp/crg-final1880-tools-20261116',output='/var/tmp/crg-final1880-results-20261116',namespace='crg-vendor-lab-final1880-20261116',source_revision=formal['source_commit'],binary_sha256=sha(inputs['binaries/crg-linux-amd64']),job_sha256=sha(inputs['job.py']))
p['business_prerequisite']={'tools':formal['plan']['tools'],'output':formal['plan']['output'],'report_sha256':sha(coraw),'original_checks':18,'separately_qualified_auxiliary_checks':4,'exact_independent_qualification_sha256':sha(qraw)}
for stage in p['stages']:
 stage['run_id']={'baseline':'202611161880','enforce':'202611161881','acceptance':'202611161882'}[stage['phase']]
 if stage.get('source_run_id'):stage['source_run_id']='202611161880'
for n,k in [('agent_sha256','binaries/crg-linux-amd64'),('worker_sha256','tests/vendor-soak-load.py'),('campaign_script_sha256','tests/vendor-soak-campaign.py'),('engine_script_sha256','tests/vendor-engine-smoke.py')]:p['campaign_pins'][n]=sha(inputs[k])
p['source_sha256']={n:sha(raw) for n,raw in inputs.items()};p['policy']=p['policy'].replace('Fresh1728','Fresh1880')+' Old1728 explicitly stopped for the CPU-capacity source fix remains failed, all cleanup and exact inputs are rechecked; its clocks never transfer. Only qualified formal1856 original18 plus4 and source37 native284 qualify this new run. Diagnostic worker retains bounded original-request failure metadata; original long sampling/SQL/API/latency/coverage/auditor unchanged. No600 wait observer is enabled for long phases.'
p['old1728_terminal_report_sha256']=record['sha256'];p['fresh_formal18_projection']=projection;p['source_worker_diagnostics_sha256']=sha(inputs['tests/vendor-soak-load.py'])
oldp=old['plan']
for key in ['baseline_configuration','baseline_configuration_exact_utf8','enforce_configuration','enforce_configuration_exact_utf8','private_fixture_sha256','expected_original_image_sha256','minimum_duration_seconds','control_files','scope','coordinator_observation_contract']:assert p[key]==oldp[key]
assert [(s['phase'],s['seconds'],s['cycles']) for s in p['stages']]==[(s['phase'],s['seconds'],s['cycles']) for s in oldp['stages']]
inputs['plan.json']=enc(p);observer=(OF/'observer-readonly.py').read_bytes().replace(b'crg-final1728',b'crg-final1880').replace(b'crg-vendor-lab-final1728',b'crg-vendor-lab-final1880').replace(old['plan_sha256'].encode(),sha(inputs['plan.json']).encode());ast.parse(observer);inputs['observer-readonly.py']=observer
for n,raw in inputs.items():
 if n.endswith('.py'):ast.parse(raw)
 dest=N/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
f={'schema':'crg-new-source37-fresh1880-long-frozen-v1','phase':'frozen-not-uploaded-not-launched','freeze':N.name,'job_sha256':p['job_sha256'],'plan_sha256':sha(inputs['plan.json']),'uploaded_sha256':{n:sha(raw) for n,raw in inputs.items()},'plan':p,'all_original_durations_SLA_budgets_cache_and_auditor_unchanged':True,'old1396_1728_inputs_untouched':True,'new_clock':True,'inherited_seconds':0,'source_revision':formal['source_commit'],'formal_original18_and_aux4_accepted':True,'new_long_started':False,'stable_release_accepted':False};(T/'crg-r1880-long-frozen.json').write_bytes(enc(f));print(json.dumps({'phase':f['phase'],'inputs':len(inputs),'minimum_duration_seconds':p['minimum_duration_seconds'],'source_revision':p['source_revision'],'long_started':False}))
