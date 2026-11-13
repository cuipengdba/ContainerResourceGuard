from pathlib import Path
import hashlib,json,os,sys,time

w=Path(__file__).parent;run_id='2026111288200';path=sys.argv[1];raw=(w/'sitecustomize.py').read_bytes();module={'__name__':'long_receiver_synthetic_writer','__file__':str(w/'sitecustomize.py')};exec(compile(raw,str(w/'sitecustomize.py'),'exec'),module);assert not module['ACTIVATED']
emit,close=module['nonblocking_fifo_sink'](path);expected=[];began=time.monotonic();cpu=time.process_time();fields=Path('/proc',str(os.getpid()),'stat').read_bytes().rsplit(b')',1)[1].split()
print(json.dumps({'phase':'ready','pid':os.getpid(),'start_ticks':int(fields[19]),'run_id':run_id,'source_sha256':hashlib.sha256(raw).hexdigest(),'synthetic_receiver_records_only_no_HTTP':True}),flush=True)
try:
    for index in range(121):
        deadline=began+index*5
        while time.monotonic()<deadline:time.sleep(min(.2,deadline-time.monotonic()))
        row={'run_id':run_id,'kind':'urlopen-headers','iteration':index,'synthetic_receiver_probe':True};assert emit(row)
        expected.append(module['PREFIX']+json.dumps(row,sort_keys=True,separators=(',',':')).encode('ascii')+b'\n')
finally:close()
raw=b''.join(expected);print(json.dumps({'phase':'finished','records':len(expected),'elapsed_seconds':time.monotonic()-began,'writer_process_CPU_seconds':time.process_time()-cpu,'exact_expected_bytes':len(raw),'exact_expected_sha256':hashlib.sha256(raw).hexdigest(),'synthetic_receiver_records_only_no_HTTP':True}),flush=True)
