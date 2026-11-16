from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
w=Path('/var/tmp/crg-final1880-tools-20261116');expected={'binaries/crg-linux-amd64': 'ee4f0a140dd7fc1b0435298cd7ee673eedb0eaea6be9f79971d565f5f181308c', 'examples/optional-agent.sh': 'f7e7208f58bac7066d75d49cb17199b720e3d05bb5953e2a7a7800f881b54b79', 'tests/own-pg-startup-log.py': 'd067cde7ccbc2f7e8330409607a21ebda03ea6788ae86215904fa988aa5aac8f', 'tests/port-integration-checks.py': '4a07d6ad84ea77d13e6d789882dd382c871d8efbd63ee56d4b06d9c3ab565c77', 'tests/port-owner-observer.py': 'fb82be5e05e69d4667620228f3e14995764a03c7a7626d73f8ed8b65f38ea4d0', 'tests/vendor-engine-smoke.py': '1a4317e3f9ce8ccde4a22c89893780b3c7121afd2cfc2be4a52e23258244c30a', 'tests/vendor-port-diagnostics.py': 'c8fbc334aa68721f571cf49b2d5d4b65114213091ab1596480ba16bb969ffb2a', 'tests/vendor-soak-campaign.py': 'a89ed2e32fe02876c39a240f8368eecb964ff7bce02235072ab417760fe282ce', 'tests/vendor-soak-load.py': '52517a96032305ff3cbcd9f58be8dd8331d9975037ee81f7380400ed370275be', 'tests/soak-report-audit.py': '4feb3e7fad630e37245c837fc85e90dec4e10a086e5fe96a4bc299f4ad481eb8', 'business-qualification.json': '7bfae4f21f26c441e01e216f24f5af51a38bd67915d85c50651239b186f8ef38', 'CI-qualification.json': 'a7079fac3267b55edbd819221aed2a9d6d647e3a112641efc3d71189b606e9bf', 'job.py': '9e04850b4da072071feaf73cf395da3b505e8d4d5e90d9c738da39d9774d0972', 'campaign-wrapper.py': '15eec0f922ac7bce86af9dbc4cc474342dbb4eba5d1e50f4a61a2fa623a1d994', 'runner.py': '62e12f33d4761e9275099525bf6a9a047f6177f110d1f8881f752f58b8adc975', 'tests/coordinator-probe-v1/probe.py': '8bbffbf5615800cc53dbfb3ee04f7294cb2121f5de43f0af44aa6b54df211f9e', 'formal18-independent.json': '8cb2f74b08271b155105ddb024492816b43b157dba1bebd359810a74a11d0aec', 'plan.json': '0b98d3c5cba9e2375cb19d0357a1376dd7dffdda96f616a1297d181c7dacbdae', 'observer-readonly.py': 'fae5d64cd612fb0361081daa04741e4cc41a21a771448a4065b8ee592775c3f0'};plan=json.loads((w/'plan.json').read_bytes());assert not (w/'launch.json').exists() and not (w/'launch.guard').exists() and not Path(plan['output']).exists()
for n,h in expected.items():assert hashlib.sha256((w/n).read_bytes()).hexdigest()==h
node_tools=Path('/var/tmp/crg-final1615-tools-20261115');assert hashlib.sha256((node_tools/'plan.json').read_bytes()).hexdigest()=='6b49b1f71108a10b3793afc628dc7b727b2246fdcfdd2cadba287bcc272d12aa' and hashlib.sha256((node_tools/'tests/node-admission.py').read_bytes()).hexdigest()=='dc1c21210b2fe023cfa75c02b283a792212a80ab9948236aea40447d50c87ab6'
q=subprocess.run([sys.executable,str(Path('/var/tmp/crg-final1615-tools-20261115/tests/node-admission.py')),'/var/tmp/crg-final1615-tools-20261115/plan.json'],capture_output=True,text=True,check=True,timeout=40);assert not q.stderr;node_admission=json.loads(q.stdout)
q=subprocess.run([sys.executable,'-B',str(w/'job.py'),'--preflight'],env=dict(os.environ,CRG_FINAL1880_LONG='authorized-disposable-test-node-only'),capture_output=True,text=True,timeout=45);assert q.returncode in [0,2] and not q.stderr;admission=json.loads(q.stdout);assert not admission['business_fixture_created'] and not admission['long_measurement_started'] and not Path(plan['output']).exists()
# Only the exact independently qualified predecessor permits the formal clock.
previous_tools=Path('/var/tmp/crg-final1615-tools-20261115');previous_raw=Path('/var/tmp/crg-final1615-results-20261115/report.json').read_bytes();assert hashlib.sha256(previous_raw).hexdigest()=='0f5cfbd1866947a9c13db2a930b3ecc89a4702651857ce1f3abd7fb218082868';previous_output_passed=json.loads(previous_raw);previous_exit=json.loads((previous_tools/'exit.json').read_bytes());assert previous_output_passed['phase']==previous_exit['phase']=='passed' and previous_exit['exit']==0 and previous_exit['artifact_index_complete']
def original_absent(row):
 try:
  fields=Path('/proc',str(row['pid']),'stat').read_bytes().rsplit(b')',1)[1].split();return fields[0]==b'Z' or int(fields[19])!=row['start_ticks']
 except (FileNotFoundError,ProcessLookupError):return True
assert original_absent(json.loads((previous_tools/'launch.json').read_bytes()))
for row in previous_output_passed['roles'].values():
 assert row['phase']=='passed' and row['recorded_checks']==row['passed_checks']==13 and original_absent(row['driver'])
 for clean in row['cleanup']:
  identity=clean['identity'];assert not Path(identity['group']).exists() and not Path(identity['pod_parent']).exists() and all(original_absent(v) for v in identity['processes'])
assert node_admission['admitted'] and q.returncode==0 and admission['phase']=='ready' and not admission['blocking_pods']
guard=os.open(str(w/'launch.guard'),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(guard,'w') as stream:stream.write('sole fresh formal1880 launch\n');stream.flush();os.fsync(stream.fileno())
with (w/'runner.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-B',str(w/'runner.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True);fields=Path('/proc',str(child.pid),'stat').read_bytes().rsplit(b')',1)[1].split();assert fields[0]!=b'Z';out={'pid':child.pid,'start_ticks':int(fields[19]),'entry':str(w/'runner.py'),'job_sha256':plan['job_sha256'],'plan_sha256':hashlib.sha256((w/'plan.json').read_bytes()).hexdigest(),'node_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'single_launch_guard':True,'source_sha256':expected,'node_admission':node_admission,'admission':admission}
 with (w/'launch.json').open('x') as stream:json.dump(out,stream,indent=2);stream.flush();os.fsync(stream.fileno())
# Supplemental observer is source-pinned but never gates or signals business.
try:
 observer_path=w/'observer-readonly.py';assert hashlib.sha256(observer_path.read_bytes()).hexdigest()=='fae5d64cd612fb0361081daa04741e4cc41a21a771448a4065b8ee592775c3f0'
 with (w/'observer.log').open('xb') as log:
  observer=subprocess.Popen([sys.executable,'-B',str(observer_path)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True);fields=Path('/proc',str(observer.pid),'stat').read_bytes().rsplit(b')',1)[1].split();assert fields[0]!=b'Z';observer_identity={'pid':observer.pid,'start_ticks':int(fields[19]),'entry':str(observer_path),'source_sha256':'fae5d64cd612fb0361081daa04741e4cc41a21a771448a4065b8ee592775c3f0','read_only_Kubernetes_queries':True,'product_or_business_signals':False}
 with (w/'observer-launch.json').open('x') as stream:json.dump(observer_identity,stream,indent=2);stream.flush();os.fsync(stream.fileno())
 out['observer']=observer_identity
except Exception as error:
 out['observer_launch_error']=type(error).__name__+': '+str(error)
 with (w/'observer-launch-error.json').open('x') as stream:json.dump({'error':out['observer_launch_error'],'formal_job_not_stopped_or_restarted':True},stream)
print(json.dumps({'summary':out}))
