from pathlib import Path
import datetime,hashlib,json,os,shutil,signal,subprocess,sys
w=Path('/var/tmp/crg-final1525-tools-20261115');expected={'maintenance-business.py': 'd89b41e3646832724c0007cff6a3ac8055bd244356b79d56557b2fd6b79b06c0', 'runner.py': '811d391a42149830a3f01516d0baebdd486c49c11fbac1bfef5ed89e7c19187d', 'artifact-transfer.py': '8a89dc7df6af1286c4b9b6c7837fdc969b9c746063c877403d716bbe4496bfb8', 'tests/manual-maintenance-contract.py': '42edbdfb1b727f02c70a8e45d362748d78aeb3bc43f586263bd811660b743985', 'binaries/candidate': '9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8', 'tests/vendor-soak-load.py': 'ba87ef2d646b723eb8419de25ffcd736f7a5b0925716f4b638761dff70bb2461', 'tests/vendor-soak-campaign.py': 'b49d5a73654c5cf7c93b04851f3409eea318b3a9c71c0e8f601f252a3dda07ea', 'tests/vendor-engine-smoke.py': 'b0d4fe313156743ff1424b46eb58c5ab5b8e1f2c91851420023f5f018dd08e5c', 'examples/optional-agent.sh': 'f7e7208f58bac7066d75d49cb17199b720e3d05bb5953e2a7a7800f881b54b79', 'tests/cli-supervisor-checks.py': '0e27567c2c5a8b96664c36176d60d73a9ae2660306e03b8c8c4a1c7b6df1edc9', 'plan.json': '6b2a9f475eb68f1d8f64e6a949e96fa489ee7293029863c35d9fbbf8dae52759'};sha=lambda raw:hashlib.sha256(raw).hexdigest();plan=json.loads((w/'plan.json').read_bytes());assert not (w/'launch.json').exists() and not Path(plan['output']).exists()
for name,h in expected.items():
 raw=(w/name).read_bytes();assert sha(raw)==h
 if name.endswith('.py'):compile(raw.decode(),name,'exec')
assert not Path('/var/tmp/crg-final1523-tools-20261115').exists() and not Path('/var/tmp/crg-final1523-results-20261115').exists()
assert os.geteuid()==0 and os.uname().machine=='x86_64' and hasattr(os,'pidfd_open') and hasattr(signal,'pidfd_send_signal')
runner=(w/'runner.py').read_text();marker='root.mkdir(mode=0o700);out=';assert runner.count(marker)==1;prefix=runner.split(marker)[0];gate={};exec(compile(prefix,'exact-coordinator-read-only-prefix','exec'),gate);assert gate['registered']==71 and gate['maintenance_registered']==64 and not Path(plan['output']).exists()
scope={};exec(compile((w/'artifact-transfer.py').read_bytes(),'own-frozen-transfer-source','exec'),scope);assert scope['ROOT']==plan['output']+'/export'
for ns in plan['namespaces'].values():
 q=subprocess.run(['kubectl','get','namespace',ns,'--ignore-not-found','--request-timeout=8s','-o','json'],capture_output=True,text=True,timeout=12,check=True);assert not q.stdout.strip() and not q.stderr
infos={}
for name,bound in plan['programs'].items():
 q=subprocess.run([str(w/'binaries'/name),'build-info'],capture_output=True,text=True,timeout=10,check=True);assert not q.stderr;info=json.loads(q.stdout);assert info['revision']==bound['source_revision'] and info['version']==bound['embedded_version'] and info['memory_policy']=='high-reclaim-throttle; percentages may be exceeded; external hard limits retained' and info['lock_protocol']=='cgroup-inode-flock+state-agent-lock-v1' and 1 in info['journal_versions'];infos[name]=info
assert infos['candidate']['io_percent_policy']=='calibrated-read-write-bandwidth; IOPS manual only; external IOPS retained'
for name,h in plan['private_fixture_sha256'].items():assert sha((Path('/var/tmp/crg-business-20261110')/name).read_bytes())==h
assert not os.listxattr(w/'tests/cli-supervisor-checks.py')
for template in plan['supervisor_templates'].values():
 raw=template['exact_utf8'].encode();assert sha(raw)==template['sha256'];q=subprocess.run(['/bin/bash','--noprofile','--norc','-n'],input=raw,capture_output=True,timeout=5,check=True);assert not q.stdout and not q.stderr
compile((w/'tests/cli-supervisor-checks.py').read_bytes(),'fixed-cli-checks-native-python','exec')
available=int(next(v.split()[1] for v in Path('/proc/meminfo').read_text().splitlines() if v.startswith('MemAvailable:')))*1024;free=shutil.disk_usage('/var/tmp').free;assert available>=28*1024**3 and free>=20*1024**3

assert not any((w/name).exists() for name in ['launch.guard','runner.log','exit.json','artifact-index.json'])
os.umask(0o077)
value={'entry':str(w/'runner.py'),'job_sha256':plan['job_sha256'],'plan_sha256':sha((w/'plan.json').read_bytes()),'predecessor_diagnostic_registered_instances_absent':gate['registered'],'predecessor_binary_maintenance_registered_instances_absent':gate['maintenance_registered'],'single_launch_guard':True}
assert value['predecessor_diagnostic_registered_instances_absent']==71 and value['predecessor_binary_maintenance_registered_instances_absent']==64
own_args=Path('/proc/self/cmdline').read_bytes().split(bytes([0]));value['launcher_source_sha256']=sha(own_args[own_args.index(b'-c')+1])
guard=os.open(str(w/'launch.guard'),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(guard,'wb') as stream:
 stream.write((datetime.datetime.now(datetime.timezone.utc).isoformat()+'\n').encode());stream.flush();os.fsync(stream.fileno())
with (w/'runner.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-B',str(w/'runner.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
 fields=Path('/proc',str(child.pid),'stat').read_bytes().rsplit(b')',1)[1].split();assert fields[0]!=b'Z' and str(w/'runner.py').encode() in Path('/proc',str(child.pid),'cmdline').read_bytes().split(bytes([0]));value.update(pid=child.pid,start_ticks=int(fields[19]),node_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
 with (w/'launch.json').open('x') as stream:
  stream.write(json.dumps(value)+'\n');stream.flush();os.fsync(stream.fileno())
print(json.dumps(value))
