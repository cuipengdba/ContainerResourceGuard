from pathlib import Path
import datetime,hashlib,json,os,subprocess,traceback
w=Path(__file__).parent;f=json.loads((w/'manifest.json').read_text());report={'schema':'crg-actual-factory-start-host-unit-v1','phase':'running','source_sha256':f['source_sha256'],'actual_vendor_business_or_BPF_executed':False}
fields=Path('/proc',str(os.getpid()),'stat').read_bytes().rsplit(b')',1)[1].split();(w/'worker.json').write_text(json.dumps({'pid':os.getpid(),'start_ticks':int(fields[19])}))
try:
 for name,want in f['source_sha256'].items():assert hashlib.sha256((w/name).read_bytes()).hexdigest()==want
 child=subprocess.run(['python3',str(w/'unit.py'),str(w/'factory.py'),str(w/'hook.py'),str(w/'receiver.py'),str(w/'sitecustomize.py')],capture_output=True,timeout=30);assert len(child.stdout)<=65536 and len(child.stderr)<=65536;report.update(child_exit=child.returncode,stdout_utf8=child.stdout.decode(),stderr_utf8=child.stderr.decode())
 if child.returncode==0 and not child.stderr:
  report['unit']=json.loads(child.stdout);report['phase']='passed' if report['unit']['phase']=='passed' and len(report['unit']['cases'])==9 else 'failed'
 else:report['phase']='failed'
except BaseException as error:report.update(phase='failed',error_class=type(error).__name__,error=str(error),traceback=traceback.format_exc())
finally:
 report['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();(w/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');(w/'exit.json').write_text(json.dumps({'exit':0 if report['phase']=='passed' else 1}));print(json.dumps({'phase':report['phase']}))
