"""Actual Linux pressure-helper lease checks; no allocation or cgroup writes."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time

here=Path(__file__).parent
if os.environ.get('CRG_PRESSURE_LEASE_CHECKS')!='authorized-disposable-test-node-only':
    raise SystemExit('explicit isolated test marker required')
output=Path(sys.argv[1]);output.mkdir(mode=0o700,exist_ok=False)
helper=here/'vendor-memory-pressure-worker-v2.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='741a1aaaecef91bb54a06bdd6af3bf76f5f8e1ad17c25bbdee4c868fddd3daff'
spec=importlib.util.spec_from_file_location('lease',here/'vendor-pressure-sql-lease.py')
lease=importlib.util.module_from_spec(spec);spec.loader.exec_module(lease)
report={'phase':'running','checks':[],'cases':{},'maximum_allocated_bytes':0,
        'helper_sha256':hashlib.sha256(helper.read_bytes()).hexdigest(),
        'lease_module_sha256':hashlib.sha256((here/'vendor-pressure-sql-lease.py').read_bytes()).hexdigest()}
children=[]
def save(): (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
def check(name,condition):
    report['checks'].append({'name':name,'passed':bool(condition)});save()
    assert condition,name
def start(name):
    env=os.environ.copy();env['CRG_MEMORY_PRESSURE_TEST']='authorized-disposable-loopback-only'
    log=(output/(name+'.stderr')).open('x')
    p=subprocess.Popen([sys.executable,'-u',str(helper)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,bufsize=1,env=env)
    children.append((p,log))
    hello=receive(p)
    check(name+'-unchanged-ready-lease-and-zero-allocation',hello['phase']=='ready' and hello['lease_seconds']==10 and hello['lifetime_seconds']==240 and hello['maximum_bytes']==12<<30)
    return p,log,hello
def receive(p):
    ready,_,_=select.select([p.stdout],[],[],5);assert ready,'bounded helper response'
    line=p.stdout.readline(4097);assert line.endswith('\n') and len(line)<=4096
    return json.loads(line)
def ping(p):
    p.stdin.write('{"op":"ping"}\n');p.stdin.flush();reply=receive(p)
    assert reply['phase']=='ack' and reply['op']=='ping' and reply['allocated_bytes']==0
def finish(name,p,log):
    if p.poll() is None:p.stdin.close()
    try:p.wait(timeout=15)
    except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5);raise
    tail=p.stdout.read(8193);assert len(tail)<=8192
    lines=[json.loads(x) for x in tail.splitlines()]
    log.close();assert not (output/(name+'.stderr')).read_bytes()
    record={'exit':p.returncode,'terminal_stdout':tail,'terminal':lines,'pid':p.pid,'process_gone':not Path('/proc',str(p.pid)).exists()}
    report['cases'].setdefault(name,{}).update(record);save();return record

try:
    # Reproduce the unchanged helper's original lease expiry, keeping stdin open.
    p,log,hello=start('unleased')
    time.sleep(11)
    r=finish('unleased',p,log)
    check('unleased-exits-and-retains-real-alarm-release-reason',r['exit']==1 and r['process_gone'] and len(r['terminal'])==1 and r['terminal'][0]['phase']=='released' and r['terminal'][0]['allocated_bytes']==0 and 'lease-or-signal-14' in r['terminal'][0]['reason'])

    p,log,hello=start('leased15')
    record={};report['cases']['leased15']={'wrapper':record}
    def slow_probe():time.sleep(15);return 'same-primary'
    value=lease.call_with_lease(slow_probe,lambda:ping(p),record)
    check('leased-probe-longer-than-ten-seconds-keeps-same-helper',value=='same-primary' and p.poll() is None and record['elapsed_seconds']>=15 and record['pulse_count']>=10 and record['original_SQL_call_finished'] and not record['SQL_thread_alive_at_return'])
    r=finish('leased15',p,log)
    check('leased-EOF-releases-without-signals-or-allocation',r['exit']==0 and r['process_gone'] and r['terminal'][0]['reason']=='EOF' and r['terminal'][0]['allocated_bytes']==0)

    sql_error=RuntimeError('own synthetic SQL error');pulse_error=OSError('own synthetic pulse error')
    def failed_probe():time.sleep(.7);raise sql_error
    def failed_pulse():raise pulse_error
    record={}
    try:lease.call_with_lease(failed_probe,failed_pulse,record)
    except BaseException as actual:check('SQL-error-object-keeps-precedence-over-pulse-failure',actual is sql_error and record['pulse_error_class']=='OSError' and record['original_SQL_call_finished'] and not record['SQL_thread_alive_at_return'])
    else:raise AssertionError('original SQL failure lost')
    def good_probe():time.sleep(.7);return 'done'
    record={}
    try:lease.call_with_lease(good_probe,failed_pulse,record)
    except BaseException as actual:check('pulse-error-remains-visible-after-successful-SQL',actual is pulse_error and record['original_SQL_call_finished'] and not record['SQL_thread_alive_at_return'])
    else:raise AssertionError('pulse failure hidden')
    record={}
    try:lease.call_with_lease(lambda:subprocess.run([sys.executable,'-c','import time;time.sleep(3)'],capture_output=True,timeout=.3),lambda:None,record)
    except subprocess.TimeoutExpired:check('original-real-subprocess-timeout-is-not-retried-or-extended',record['original_SQL_call_finished'] and not record['SQL_thread_alive_at_return'] and record['elapsed_seconds']<2 and record['SQL_retries']==0)
    else:raise AssertionError('source timeout lost')
    record={}
    check('immediate-return-does-not-add-a-pulse',lease.call_with_lease(lambda:'ready',lambda:None,record)=='ready' and record['pulse_count']==0 and record['original_SQL_call_finished'])
    report['phase']='passed'
except BaseException as error:
    report.update(phase='failed',error_class=type(error).__name__,error=str(error));raise
finally:
    forced=False
    for p,log in children:
        if p.poll() is None:
            if not p.stdin.closed:p.stdin.close()
            try:p.wait(timeout=15)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5);forced=True
        if not log.closed:log.close()
    report['all_owned_helpers_gone']=all(p.poll() is not None for p,log in children)
    report['forced_own_helper_cleanup']=forced
    if forced or not report['all_owned_helpers_gone']:report['phase']='failed'
    save()
print(json.dumps({'phase':report['phase'],'checks':len(report['checks']),'helper_allocated_bytes':0}))
