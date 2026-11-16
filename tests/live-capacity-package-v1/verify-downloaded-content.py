from pathlib import Path
import hashlib,json,os,subprocess,sys
T=Path(__file__).parent;R=T.parent/'ContainerResourceGuard-integration';dist=T/'crg-r1920-package-artifacts'
plan=json.loads((T/'crg-r1918-package-dispatch-intent.json').read_bytes());download=json.loads((T/'crg-r1920-package-download.json').read_bytes())
sha=lambda b:hashlib.sha256(b).hexdigest()
for n,h in plan['recipe_sha256'].items():assert sha((R/n).read_bytes())==h and sha(subprocess.check_output(['git','show',plan['packaging_revision']+':'+n],cwd=R))==h
env=os.environ.copy();env['PYTHONPATH']=str(T/'sbom-schema-deps')
checks=[]
for arch in ['amd64','arm64']:
 n=f'containerresourceguard-v1.0.0-linux-{arch}.tar.gz'
 assert sha((dist/n).read_bytes())==download['files'][n]['sha256']
 cases=[('offline-downloaded-'+arch,[str(R/'scripts/verify-release.py'),str(dist/n),'--sha256',download['files'][n]['sha256'],'--source-revision',plan['program_source_revision'],'--arch',arch]),('schema-downloaded-'+arch,[str(R/'scripts/validate-sbom.py'),str(dist/f'sbom-linux-{arch}.cdx.json'),'--schema-directory',str(T/'sbom-schemas')])]
 for name,args in cases:
  r=subprocess.run([sys.executable,*args],env=env,capture_output=True,timeout=55);assert r.returncode==0,(name,r.stderr.decode())
  result=json.loads(r.stdout);assert result.get('state')=='verified' or result.get('schema_valid') is True
  checks.append({'name':name,'exit':0,'result':result})
out={'schema':'crg-source37-package-content-independent-v1','package_revision':plan['packaging_revision'],'program_source_revision':plan['program_source_revision'],'run_id':download['run_id'],'phase':'passed','checks':checks,'stable_release_accepted':False}
(T/'crg-r1921-independent-package-content.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(out))
