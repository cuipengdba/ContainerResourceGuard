from pathlib import Path
import hashlib,json,os,subprocess,sys,time
w=Path('/var/tmp/crg-final1404-tools-20261115');p=json.loads((w/'overhead-plan.json').read_bytes())
assert hashlib.sha256((w/'overhead-job.py').read_bytes()).hexdigest()==p['job_sha256']
child=subprocess.Popen([sys.executable,'-B',str(w/'overhead-job.py')],stdin=subprocess.DEVNULL,env=dict(os.environ,CRG_FINAL1404_OVERHEAD='authorized-disposable-test-node-only'))
fields=Path('/proc',str(child.pid),'stat').read_bytes().rsplit(b')',1)[1].split();(w/'worker.json').write_text(json.dumps({'pid':child.pid,'start_ticks':int(fields[19]),'entry':str(w/'overhead-job.py')})+'\n');rc=child.wait()
(w/'exit.json').write_text(json.dumps({'exit':rc,'job_sha256':p['job_sha256'],'ended_epoch':time.time()})+'\n');raise SystemExit(rc)
