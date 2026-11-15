from pathlib import Path
import datetime,hashlib,json,os
w=Path('/var/tmp/crg-final1501-tools-20261115');root=Path('/var/tmp/crg-final1501-results-20261115');sha=lambda raw:hashlib.sha256(raw).hexdigest();plan=json.loads((w/'plan.json').read_bytes());report=json.loads((root/'report.json').read_bytes());assert report['job_sha256']==plan['job_sha256'] and report['plan_sha256']==sha((w/'plan.json').read_bytes()) and report['started_epoch']==1794740769.7306628 and not (w/'launch.json').exists() and (w/'launch.guard').exists()
pid=4139156;start=168071232;p=Path('/proc',str(pid));fields=(p/'stat').read_bytes().rsplit(b')',1)[1].split();assert int(fields[19])==start and fields[0]!=b'Z' and str(w/'runner.py').encode() in (p/'cmdline').read_bytes().split(bytes([0]))
for name,h in plan['source_sha256'].items():assert sha((w/name).read_bytes())==h
value={'pid':pid,'start_ticks':start,'entry':str(w/'runner.py'),'job_sha256':plan['job_sha256'],'plan_sha256':sha((w/'plan.json').read_bytes()),'node_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actual_coordinator_started_epoch':report['started_epoch'],'launch_guard_utc':(w/'launch.guard').read_text().strip(),'launcher_source_sha256':'c82d146371be5682e89dc40c342362e179ae2c152f5150a4f8055f03e2f9625f','single_launch_guard':True,'record_reconstructed_after_launcher_NameError':True,'reconstruction_scope':'Only missing launch identity record; existing runner PID/start/entry and frozen source checked. No process start, signal, configuration, quota or report changes.'}
os.umask(0o077)
with (w/'launch.json').open('x') as stream:stream.write(json.dumps(value)+'\n');stream.flush();os.fsync(stream.fileno())
print(json.dumps(value))
