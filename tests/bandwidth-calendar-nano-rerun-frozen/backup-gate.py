"""Read-only terminal check for old576; its failed elapsed time is not accepted."""
from pathlib import Path
import hashlib,json,subprocess,time
def snapshot(plan):
 g=plan['old576_terminal'];w=Path(g['tools']);root=Path(g['output']);raw=(root/'report.json').read_bytes();r=json.loads(raw);end=json.loads((w/'acceptance.exit.json').read_bytes());assert hashlib.sha256(raw).hexdigest()==g['report_sha256'] and hashlib.sha256((root/'campaign-acceptance/report.json').read_bytes()).hexdigest()==g['campaign_report_sha256'] and hashlib.sha256((w/'acceptance-job.py').read_bytes()).hexdigest()==g['job_sha256'] and end['exit']==1 and end['job_sha256']==g['job_sha256'] and r['phase']=='failed'
 def absent(p):
  try:return int(Path('/proc',str(p['pid']),'stat').read_bytes().rsplit(b')',1)[1].split()[19])!=p['start_ticks']
  except (FileNotFoundError,ProcessLookupError):return True
 assert all(absent(p) for p in [json.loads((w/'launch.json').read_bytes()),json.loads((w/'worker.json').read_bytes()),r['campaign_identity']]);count=0
 for role in r['roles'].values():
  own=role['fixture_identity'];assert not Path(own['group']).exists() and not Path(own['pod_parent']).exists() and all(absent(p) for p in own['processes']);count+=len(own['processes'])
 q=subprocess.run(['kubectl','get','namespace',g['namespace'],'--ignore-not-found','--request-timeout=8s','-o','json'],capture_output=True,text=True,timeout=12,check=True);assert not q.stdout.strip() and not q.stderr and count==51
 return {'node_epoch':time.time(),'gate_passed':True,'old576_phase':'failed','old576_registered_initial_instances_absent':count,'not_seven_day_acceptance':True,'no_elapsed_transfer':True}
