from pathlib import Path
import concurrent.futures,hashlib,json,os,subprocess,urllib.request,datetime
t=Path(__file__).parent;dist=t/'crg-r1641-package-artifacts';out=t/'crg-r1642-package-attestations';out.mkdir(mode=0o700,exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
repo='cuipengdba/ContainerResourceGuard';revision='576e6070b09804017ececf3f82fb2f6517c18316';ref='refs/heads/release/integration-v1';workflow=repo+'/.github/workflows/final-package.yml';run=43729111057
assert (t/'crg-r1641-package-download.json').is_file()
env=os.environ.copy()
for scheme,value in urllib.request.getproxies().items():
 if scheme in ['http','https']:env[scheme.upper()+'_PROXY']=value
base=['--repo',repo,'--signer-workflow',workflow,'--source-digest',revision,'--signer-digest',revision,'--source-ref',ref,'--deny-self-hosted-runners','--format','json']
tasks=[(f'online-{kind}-{arch}',dist/(f'containerresourceguard-v1.0.0-linux-{arch}.tar.gz' if kind=='provenance' else f'crg-linux-{arch}'), 'https://slsa.dev/provenance/v1' if kind=='provenance' else 'https://cyclonedx.org/bom') for arch in ['amd64','arm64'] for kind in ['provenance','SBOM']]
plan={'schema':'crg-fixed-final-package-attestation-v1','phase':'frozen-before-verification','package_revision':revision,'program_source_revision':'ced461705ebc27315a59aefe463f9b4af47130a3','repo':repo,'workflow':workflow,'ref':ref,'run_id':run,'online_positive_cases':4,'offline_positive_cases':3,'offline_negative_cases':['wrong-source','wrong-workflow','changed-package'],'artifacts':{p.name:sha(p) for _,p,_ in tasks},'script_sha256':sha(Path(__file__))}
(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
def command(name,args,environment=env):
 r=subprocess.run([str(t/'github-cli/bin/gh.exe'),*args],env=environment,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
 (out/(name+'.stdout.json')).write_text(r.stdout,encoding='utf-8');(out/(name+'.stderr.txt')).write_text(r.stderr,encoding='utf-8');return r
def identity(values,path,predicate):
 assert isinstance(values,list) and values
 for item in values:
  v=item['verificationResult'];c=v['signature']['certificate'];s=v['statement']
  assert c['sourceRepositoryDigest']==revision and c['sourceRepositoryURI']=='https://github.com/'+repo and c['sourceRepositoryRef']==ref
  assert c['sourceRepositoryIdentifier']=='1451211647' and c['sourceRepositoryOwnerIdentifier']=='17305257'
  assert c['buildSignerDigest']==revision and c['issuer']=='https://token.actions.githubusercontent.com'
  assert c['subjectAlternativeName']=='https://github.com/'+workflow+'@'+ref and c['runnerEnvironment']=='github-hosted'
  assert c['runInvocationURI']==f'https://github.com/{repo}/actions/runs/{run}/attempts/1'
  assert s['predicateType']==predicate and any(x.get('digest',{}).get('sha256')==sha(path) for x in s['subject'])
 return values
def online(task):
 name,path,predicate=task;r=command(name,['attestation','verify',str(path),*base,'--predicate-type',predicate]);assert r.returncode==0,name
 selected=identity(json.loads(r.stdout),path,predicate)
 (out/(name+'.bundle.jsonl')).write_text(''.join(json.dumps(x['attestation']['bundle'])+'\n' for x in selected),encoding='utf-8')
 return {'name':name,'exit':0,'passed':True,'artifact_sha256':sha(path),'matching_attestations':len(selected),'exact_certificate_and_subject':True}
checks=[]
try:
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for row in pool.map(online,tasks):checks.append(row);print(json.dumps(row),flush=True)
 r=command('trusted-root',['attestation','trusted-root']);assert r.returncode==0
 trust=out/'trusted-root.jsonl';trust.write_text(r.stdout,encoding='utf-8');assert all(json.loads(x) for x in r.stdout.splitlines() if x.strip())
 offline=dict(env)
 for k in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy']:offline[k]='http://127.0.0.1:9'
 offline['NO_PROXY']='';offline['no_proxy']=''
 def off(name,path,args,positive):
  r=command(name,['attestation','verify',str(path),*args],offline)
  assert (r.returncode==0)==positive,name
  if positive:identity(json.loads(r.stdout),path,'https://slsa.dev/provenance/v1')
  else:
   assert not any(x in r.stderr.lower() for x in ['connection refused','proxyconnect','timeout','no such host','http 404','http 500','http 502','http 503','none of the others can be','unknown flag','requires an argument','usage:']),name+' invalid trial'
   if name=='offline-wrong-source':assert 'expected SourceRepositoryDigest to be '+'0'*40+', got '+revision in r.stderr
  checks.append({'name':name,'exit':r.returncode,'passed':True,'expected_success':positive,'stdout_sha256':sha(out/(name+'.stdout.json')),'stderr_sha256':sha(out/(name+'.stderr.txt'))});print(json.dumps(checks[-1]),flush=True)
 for arch in ['amd64','arm64']:
  package=dist/f'containerresourceguard-v1.0.0-linux-{arch}.tar.gz';args=[*base,'--bundle',str(out/f'online-provenance-{arch}.bundle.jsonl'),'--custom-trusted-root',str(trust)]
  off('offline-positive-'+arch,package,args,True)
 package=dist/'containerresourceguard-v1.0.0-linux-amd64.tar.gz';args=[*base,'--bundle',str(out/'online-provenance-amd64.bundle.jsonl'),'--custom-trusted-root',str(trust)]
 wrong=list(args);wrong[wrong.index('--source-digest')+1]='0'*40;off('offline-wrong-source',package,wrong,False)
 wrong=list(args);wrong[wrong.index('--signer-workflow')+1]=repo+'/.github/workflows/ci.yml';off('offline-wrong-workflow',package,wrong,False)
 changed=out/'changed.tar.gz';changed.write_bytes(package.read_bytes()+b'CRG-tampered-test');off('offline-changed-package',changed,args,False)
 off('offline-positive-after',package,args,True)
 result={**plan,'phase':'passed','checks':checks,'trusted_root_sha256':sha(trust),'raw_receipts':{p.name:sha(p) for p in out.iterdir() if p.name.endswith(('.stdout.json','.stderr.txt','.bundle.jsonl'))},'network_condition':'offline HTTP/HTTPS/ALL proxies point to closed loopback and empty NO_PROXY; not OS firewall isolation','trust_bootstrap':'existing GitHub CLI 2.103.3 and TUF bootstrap fetched trust root before offline checks; bundle extracted only from successful online verification','stable_release_accepted':False,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
except Exception as e:result={**plan,'phase':'failed','checks':checks,'error':str(e)}
(out/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'phase':result['phase'],'accepted_checks':len(checks),'error':result.get('error')}),flush=True)
raise SystemExit(0 if result['phase']=='passed' else 1)
