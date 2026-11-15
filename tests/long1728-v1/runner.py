from pathlib import Path
import hashlib,json,os,subprocess,sys,time
w=Path('/var/tmp/crg-final1728-tools-20261116');raw=(w/'plan.json').read_bytes();p=json.loads(raw)
assert hashlib.sha256((w/'job.py').read_bytes()).hexdigest()==p['job_sha256']
env=dict(os.environ,CRG_FINAL1728_LONG='authorized-disposable-test-node-only');child=subprocess.Popen([sys.executable,'-B',str(w/'job.py')],stdin=subprocess.DEVNULL,env=env)
fields=Path('/proc',str(child.pid),'stat').read_bytes().rsplit(b')',1)[1].split();(w/'worker.json').write_text(json.dumps({'pid':child.pid,'start_ticks':int(fields[19]),'entry':str(w/'job.py')})+'\n');rc=child.wait();(w/'exit.json').write_text(json.dumps({'exit':rc,'job_sha256':p['job_sha256'],'plan_sha256':hashlib.sha256(raw).hexdigest(),'ended_epoch':time.time()})+'\n');raise SystemExit(rc)
