"""Python 2/3 check inside an isolated, read-only original vendor image.

Never runs worker main, starts PostgreSQL, or touches a business database.
The sole libpq connection targets this new Pod's empty numeric loopback:5432.
"""
from __future__ import print_function, division
import ast
import ctypes
import datetime
import hashlib
import json
import os
import select
import sys
import threading
import time

root=sys.argv[1]
raw=open(root+'/worker.py','rb').read()
old=open(root+'/original.py','rb').read()
adapter=json.load(open(root+'/adapter.json'))
assert hashlib.sha256(raw).hexdigest()==adapter['new_worker_sha256']
assert hashlib.sha256(old).hexdigest()==adapter['old_worker_sha256']
assert open('/proc/self/cgroup').read()==open('/proc/1/cgroup').read()
tree=ast.parse(raw)
compile(tree,'worker.py','exec')
passed=[]
passed.append('original-image-python-compiles-full-worker-without-executing-main')

def functions(t):
    return dict((n.name,ast.dump(n)) for n in t.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)))
before,after=functions(ast.parse(old)),functions(tree)
assert sorted(k for k in before if before[k]!=after[k])==['api_load','sample','sql_load']
passed.append('original-image-python-AST-retains-all-other-functions')
ns={'ctypes':ctypes,'datetime':datetime,'json':json,'select':select,'threading':threading,
    'time':time,'lock':threading.Lock(),'bounds':[.001,.005,.01,.02,.05,.1,.25,.5,1,2,5]}
names=['stats','failure_event','sample','ready','connect','Connection']
nodes=[]
for n in tree.body:
    if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names:
        nodes.append(n)
    elif isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id.startswith('DIAGNOSTIC_') for t in n.targets):
        nodes.append(n)
module=ast.Module(body=nodes)
if sys.version_info[0]>=3:module.type_ignores=[]
exec(compile(module,'selected-worker-functions','exec'),ns)
ns['report']={'sql':ns['stats'](),'api':ns['stats']()}
for n in tree.body:
    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id=='report' for t in n.targets):
        m=ast.Module(body=[n])
        if sys.version_info[0]>=3:m.type_ignores=[]
        exec(compile(m,'diagnostic-initialization','exec'),ns)

# Use Linux monotonic on the image's older Python as the actual worker does.
if hasattr(time,'monotonic'):
    clock=time.monotonic
else:
    class Timespec(ctypes.Structure):
        _fields_=[('seconds',ctypes.c_long),('nanoseconds',ctypes.c_long)]
    libc=ctypes.CDLL(None,use_errno=True)
    def clock():
        value=Timespec()
        assert libc.clock_gettime(1,ctypes.byref(value))==0
        return value.seconds+value.nanoseconds/1e9
ns['monotonic']=clock
ns['sample']('sql',clock(),False,'sql_query',RuntimeError('bounded SQL readiness deadline'))
event=ns['report']['failure_diagnostics']['events'][-1]
assert event['reason']=='sql_readiness_deadline' and event['stage']=='sql_query'
assert ns['report']['sql']['errors']==1
passed.append('fixed-SQL-deadline-is-recorded-in-original-image-Python')

class Hostile(Exception):
    def __str__(self):raise AssertionError('do not inspect private exception')
    def __repr__(self):raise AssertionError('do not inspect private exception')
ns['sample']('api',clock(),False,'api_request',Hostile('private'))
assert 'private' not in json.dumps(ns['report']['failure_diagnostics'])
passed.append('hostile-exception-payload-never-serialized')

# Real vendor libpq binding, same functions/prototypes and numeric loopback.
pq=ctypes.CDLL('/opt/postgresql/pgsql/lib/libpq.so.5')
ns.update(pq=pq,pointer=ctypes.c_void_p,integer=ctypes.c_int,string=ctypes.c_char_p)
for name,returns,parameters in [
        ('PQconnectStartParams',ctypes.c_void_p,[ctypes.POINTER(ctypes.c_char_p),ctypes.POINTER(ctypes.c_char_p),ctypes.c_int]),
        ('PQconnectPoll',ctypes.c_int,[ctypes.c_void_p]),('PQsocket',ctypes.c_int,[ctypes.c_void_p]),
        ('PQsetnonblocking',ctypes.c_int,[ctypes.c_void_p,ctypes.c_int]),('PQfinish',None,[ctypes.c_void_p])]:
    function=getattr(pq,name);function.restype=returns;function.argtypes=parameters
started=clock();caught=None
try:
    connection=ns['connect']()
    connection.close()
    raise AssertionError('unexpected PostgreSQL listener in isolated image-check Pod')
except RuntimeError as error:
    caught=error
assert caught is not None and clock()-started<6
ns['sample']('sql',started,False,'sql_connect',caught)
event=ns['report']['failure_diagnostics']['events'][-1]
assert event['exception_class']=='RuntimeError' and event['reason'] in ['sql_connection_polling','sql_socket_deadline','sql_readiness_deadline']
passed.append('actual-vendor-libpq-empty-loopback-failure-is-bounded-and-classified')

for i in range(512):ns['sample']('sql',clock(),False,'sql_query',RuntimeError('SQL input failed'))
d=ns['report']['failure_diagnostics']
assert len(d['events'])==128 and d['dropped_events']==387 and d['retained_event_bytes']<=65536
assert ns['report']['sql']['errors']==514 and ns['report']['api']['errors']==1
passed.append('original-image-Python-event-cap-and-total-error-counters')
print(json.dumps({'schema':'crg-diagnostic-original-image-compatibility-v1','phase':'passed',
    'python':sys.version.split()[0],'worker_sha256':hashlib.sha256(raw).hexdigest(),
    'checks':passed,'passed_checks':len(passed),'libpq_failure':event,
    'business_database_access':False,'worker_main_executed':False,'only_empty_new_Pod_loopback_attempt':True,
    'product_or_original_startup_performance_accepted':False},sort_keys=True))
