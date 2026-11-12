from pathlib import Path
import json,os,signal,subprocess,sys
w=Path(__file__).parent
with (w/'fixture.log').open('xb') as out:
 p=subprocess.Popen([sys.executable,str(w/'fixture.py')],stdin=subprocess.DEVNULL,stdout=out,stderr=out,start_new_session=True)
 f=Path('/proc',str(p.pid),'stat').read_bytes().rsplit(b')',1)[1].split();(w/'worker.json').write_text(json.dumps({'pid':p.pid,'start_ticks':int(f[19]),'entry':str(w/'fixture.py')}))
 timed=False
 try:rc=p.wait(timeout=1500)
 except subprocess.TimeoutExpired:
  timed=True;os.kill(p.pid,signal.SIGTERM)
  try:rc=p.wait(timeout=180)
  except subprocess.TimeoutExpired:rc=None
 (w/'exit.json').write_text(json.dumps({'exit':rc,'timed_out':timed}))
