import hashlib,json,os,pathlib,subprocess,time
os.umask(0o077);w=pathlib.Path('/var/tmp/crg-high618-tools-20261112');planraw=(w/'plan.json').read_bytes();plan=json.loads(planraw)
assert hashlib.sha256(planraw).hexdigest()=='f88c03697d12fc188997e3766122bc74e019d613d37cc00dc2426c1a503bef34'
assert hashlib.sha256((w/'vendor-memory-high-business-pressure.py').read_bytes()).hexdigest()==plan['job_sha256']
env=os.environ.copy();env['CRG_HIGH618_PRESSURE']='authorized-disposable-test-node-only';began=time.time()
with (w/'business.log').open('xb') as out:
 p=subprocess.Popen(['python3',str(w/'vendor-memory-high-business-pressure.py')],env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=out)
 fields=pathlib.Path('/proc',str(p.pid),'stat').read_bytes().rsplit(b')',1)[1].split()
 with (w/'worker.json').open('x') as stream:json.dump({'pid':p.pid,'start_ticks':int(fields[19]),'entry':str(w/'vendor-memory-high-business-pressure.py')},stream)
 code=p.wait()
with (w/'exit.json').open('x') as stream:json.dump({'exit':code,'job_sha256':plan['job_sha256'],'plan_sha256':'f88c03697d12fc188997e3766122bc74e019d613d37cc00dc2426c1a503bef34','started_epoch':began,'ended_epoch':time.time()},stream)
raise SystemExit(code)
