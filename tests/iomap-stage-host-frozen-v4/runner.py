from pathlib import Path
import json,os,signal,subprocess,sys
w=Path(__file__).parent
with (w/'checks.log').open('xb') as out:
 p=subprocess.Popen([sys.executable,str(w/'checks.py')],stdin=subprocess.DEVNULL,stdout=out,stderr=out,start_new_session=True)
 fields=Path('/proc',str(p.pid),'stat').read_bytes().rsplit(b')',1)[1].split();(w/'worker.json').write_text(json.dumps({'pid':p.pid,'start_ticks':int(fields[19]),'entry':str(w/'checks.py')}))
 timed=False
 try:rc=p.wait(timeout=130)
 except subprocess.TimeoutExpired:
  timed=True;os.killpg(p.pid,signal.SIGTERM)
  try:rc=p.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait(timeout=2)
 (w/'exit.json').write_text(json.dumps({'exit':rc,'timed_out':timed}))
