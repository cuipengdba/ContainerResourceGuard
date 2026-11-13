from pathlib import Path
import hashlib,importlib.util,json,os,re,subprocess,time,traceback

os.umask(0o077);w=Path('/var/tmp/crg-high950-tools-20261113');raw=(w/'plan.json').read_bytes();plan=json.loads(raw);plan_sha=hashlib.sha256(raw).hexdigest();assert plan_sha=='6328a1c4e3e6df1723a0d46b7f32db15f1ab277d4ac68287004d551d8ac302ab'
def identity(pid,entry):
 fields=Path('/proc',str(pid),'stat').read_bytes().rsplit(b')',1)[1].split();return {'pid':pid,'start_ticks':int(fields[19]),'entry':entry}
preflight={'phase':'running','units':{},'business_started':False};exit_value={'exit':1,'job_sha256':plan['job_sha256'],'plan_sha256':plan_sha,'started_epoch':time.time()}
try:
 for name,digest in plan['source_sha256'].items():assert hashlib.sha256((w/name).read_bytes()).hexdigest()==digest
 commands={'Go-pairing-output-duration-and-fixed-vendor-scope':[str(w/'pairing.test'),'-test.v'],'full-factory17':['python3',str(w/'full-pressure-factory-unit.py'),str(w/'full-pressure-integration.py'),str(w/'full-pressure-hook.py'),str(w/'vendor-memory-high-pressure-core.py'),str(w/'actual-null-preflight.json')],'artifact-transfer12':['python3',str(w/'artifact-transfer-unit.py'),str(w/'artifact-transfer.py')],'private-factory9':['python3',str(w/'private-factory-start-unit.py'),str(w/'full-pressure-integration.py'),str(w/'full-pressure-hook.py'),str(w/'native-private-fifo.py'),str(w/'sitecustomize.py')],'annotation-export19':['python3',str(w/'artifact-annotations-unit.py'),str(w/'artifact-transfer.py')]}
 for name,args in commands.items():
  v=subprocess.run(args,capture_output=True,timeout=45);assert len(v.stdout)<=65536 and not v.stderr
  preflight['units'][name]={'exit':v.returncode,'stdout':v.stdout.decode()};assert v.returncode==0
  if name!='Go-pairing-output-duration-and-fixed-vendor-scope':
   value=json.loads(v.stdout);assert value['phase']=='passed' and len(value['cases'])=={'full-factory17':17,'artifact-transfer12':12,'private-factory9':9,'annotation-export19':19}[name];preflight['units'][name]['result']=value
  else:assert len(re.findall(r'^--- PASS: ',v.stdout.decode(),re.M))==14
 preflight['phase']='passed';(w/'preflight.json').write_text(json.dumps(preflight,indent=2)+'\n')
 env=dict(os.environ,CRG_HIGH950_PRESSURE='authorized-disposable-test-node-only')
 with (w/'business.log').open('xb') as log:
  p=subprocess.Popen(['python3',str(w/'vendor-memory-high-business-pressure.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=env);(w/'worker.json').write_text(json.dumps(identity(p.pid,str(w/'vendor-memory-high-business-pressure.py'))));preflight['business_started']=True;(w/'preflight.json').write_text(json.dumps(preflight,indent=2)+'\n');code=p.wait()
 exit_value['exit']=code
 if Path(plan['output']).exists():
  spec=importlib.util.spec_from_file_location('full_artifact_transfer',w/'artifact-transfer.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  try:
   index=module.index_directory(plan['job_sha256'],plan_sha);(w/'artifact-index.json').write_text(json.dumps(index,indent=2)+'\n');exit_value['artifact_index_complete']=True
  except Exception as exc:exit_value.update(artifact_index_complete=False,artifact_index_error_class=type(exc).__name__)
except BaseException as exc:
 preflight.update(phase='failed',error_class=type(exc).__name__,traceback=traceback.format_exc());(w/'preflight.json').write_text(json.dumps(preflight,indent=2)+'\n');exit_value.update(exit=1,runner_error_class=type(exc).__name__)
finally:
 exit_value['ended_epoch']=time.time();(w/'exit.json').write_text(json.dumps(exit_value,indent=2)+'\n')
raise SystemExit(exit_value['exit'])
