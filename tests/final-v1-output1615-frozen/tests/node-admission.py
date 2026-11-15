"""Read-only admission for disposable vendor tests; never installed as CRG."""
from pathlib import Path
import datetime,json,shutil,subprocess,sys

def evaluate(nodes,images,expected,disk,expected_tags=None):
 issues=[]
 if len(nodes)!=1:issues.append('requires exact single test node')
 for node in nodes:
  states={v['type']:v['status'] for v in node['status']['conditions']}
  if states.get('Ready')!='True':issues.append('node is not Ready')
  for name in ['DiskPressure','MemoryPressure','PIDPressure']:
   if states.get(name)!='False':issues.append('node '+name+' is not False')
 threshold=max(20*1024**3,(disk['total']*15+99)//100)
 if disk['free']<threshold:issues.append('free disk below max(20GiB,15% filesystem)')
 identities={v['id'].removeprefix('sha256:') for v in images}
 for role,h in expected.items():
  if h not in identities:issues.append(role+' original config digest is absent in CRI image store')
  if expected_tags:
   tag=expected_tags[role].removeprefix('docker.io/')
   if not any(v['id'].removeprefix('sha256:')==h and tag in [s.removeprefix('docker.io/') for s in v.get('repoTags',[])] for v in images):issues.append(role+' original tag does not resolve to expected config digest')
 return {'admitted':not issues,'issues':issues,'minimum_free_bytes':threshold,'actual_free_bytes':disk['free'],'filesystem_bytes':disk['total'],'expected_original_images':expected}

def main():
 def read(args):
  p=subprocess.run(args,capture_output=True,text=True,timeout=12,check=True)
  if p.stderr:raise RuntimeError('unexpected diagnostic stderr')
  return json.loads(p.stdout)
 plan=json.loads(Path(sys.argv[1] if len(sys.argv)>1 else '/var/tmp/crg-final1571-tools-20261115/plan.json').read_bytes());metadata=json.loads(Path('/var/tmp/crg-business-20261110/vendor-import.json').read_bytes());nodes=read(['kubectl','get','nodes','-o','json','--request-timeout=8s'])['items'];images=read(['crictl','images','-o','json'])['images'];result=evaluate(nodes,images,plan['expected_original_image_sha256'],shutil.disk_usage('/var/tmp')._asdict(),{role:v['tag'] for role,v in metadata['images'].items()});result.update(schema='crg-disposable-test-node-admission-v1',node_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),read_only=True,fixtures_created=False,product_controls_changed=False);print(json.dumps(result))
if __name__=='__main__':main()
