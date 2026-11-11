#!/usr/bin/env python3
"""Linux checks for the pressure fixture's bounded protocol and cleanup paths."""
import importlib.util,json,os,pathlib,select,signal,subprocess,sys,time
sys.dont_write_bytecode=True
p=pathlib.Path(__file__).with_name('vendor-memory-pressure-worker.py')
spec=importlib.util.spec_from_file_location('pressure_fixture',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def line(process,timeout=5):
    ready,_,_=select.select([process.stdout],[],[],timeout)
    if not ready:raise AssertionError('worker response deadline')
    raw=process.stdout.readline();assert raw,'worker closed without its release record'
    return json.loads(raw)

def launch(marker=True):
    env=os.environ.copy();env.pop('CRG_MEMORY_PRESSURE_TEST',None)
    if marker:env['CRG_MEMORY_PRESSURE_TEST']=module.MARKER
    return subprocess.Popen([sys.executable,'-u',str(p)],env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)

def send(process,value):
    process.stdin.write(json.dumps(value).encode()+b'\n');process.stdin.flush();return line(process)

def run():
    assert sys.platform=='linux','Linux selftest only'
    checks=[]
    # Pure validation rejects a request above the cap without allocating it.
    for command,allocated in [({'op':'allocate'},module.MAXIMUM),({'op':'allocate','bytes':1<<40},0),({'op':'unknown'},0)]:
        try:module.permitted(command,allocated)
        except ValueError:pass
        else:raise AssertionError('unsafe command accepted')
    checks.append('invalid commands and fixed cap rejected without allocation')
    process=launch(False)
    try:assert line(process)['phase']=='rejected' and process.wait(5)==1
    finally:
        if process.poll() is None:process.kill();process.wait(5)
    checks.append('missing marker rejects before allocation')
    for case in ['normal','EOF','invalid-after-allocation','TERM','idle-lease']:
        process=launch()
        try:
            ready=line(process);assert ready['phase']=='ready' and ready['maximum_bytes']==12<<30 and ready['lease_seconds']==10
            ack=send(process,{'op':'allocate'});assert ack['allocated_bytes']==64<<20
            if case=='normal':
                assert send(process,{'op':'ping'})['allocated_bytes']==64<<20
                assert send(process,{'op':'release'})['allocated_bytes']==0
                assert send(process,{'op':'exit'})['allocated_bytes']==0
            elif case=='EOF':process.stdin.close()
            elif case=='invalid-after-allocation':
                process.stdin.write(b'{"op":"allocate","bytes":1099511627776}\n');process.stdin.flush()
            elif case=='TERM':process.send_signal(signal.SIGTERM)
            last=line(process,timeout=13 if case=='idle-lease' else 5)
            assert last['phase']=='released' and last['allocated_bytes']==0
            assert process.wait(5)==(0 if case in ['normal','EOF'] else 1)
        finally:
            if process.poll() is None:process.kill();process.wait(5)
        checks.append(case+' exits and emits release')
    print(json.dumps({'phase':'passed','checks':checks,'maximum_actual_allocation_each_process':64<<20,'product_or_cgroup_writes':False}))

if __name__=='__main__':run()
