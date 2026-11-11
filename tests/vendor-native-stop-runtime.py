from __future__ import division, print_function
"""Fresh PG fixture: the host signals only its exact 600s native test worker.

An interrupted partial report must remain failed. No vendor business acceptance.
"""
import ast
import ctypes
import hashlib
import json
import os
import select
import subprocess
import sys
import threading
import time
try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

assert os.environ.get('CRG_NATIVE_STOP_RUNTIME')=='new-emptydir-postgres-only'
assert sys.platform.startswith('linux') and os.geteuid()!=0
assert len(sys.argv)==2 and sys.argv[1] in ['dbs','hisdbs']
role=sys.argv[1];root='/tmp/crg-native220-runtime'
assert not os.path.lexists(root);os.mkdir(root,0o700)
pgdata=root+'/pgdata';bin_dir='/opt/postgresql/pgsql/bin/'
source_dir=os.path.dirname(os.path.abspath(__file__))
worker=source_dir+'/vendor-soak-load-diagnostics.py'
report={'schema':'crg-native-stop-real-pg-v1','phase':'preparing','role':role,'checks':[],
        'full600s_accepted':False,'scope':'fresh PG and mock HTTP; host-initiated native final flush only'}
with open(source_dir+'/vendor-native-diagnostics-runtime.py','rb') as stream:
    raw=stream.read()
assert hashlib.sha256(raw).hexdigest()=='ed4040a1864efec8631cc70013da5628a66c76c76cea76104b31d02b7bad2f2d'
tree=ast.parse(raw);wanted=['save','check','command','connection_functions','MockAPI']
tree.body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in wanted]
assert len(tree.body)==len(wanted)
eval(compile(tree,'frozen-native-runtime-functions','exec'),globals(),globals())
server=None;pg_started=False;process=None;stream=None
try:
    check('new-nonroot-empty-PG-and-output',not os.path.exists(pgdata) and not os.listdir('/opt/postgresql/basebackup'))
    command([bin_dir+'initdb','-D',pgdata,'-L','/opt/postgresql/pgsql/share/postgresql','-A','trust','-U','postgres','--no-locale','-E','UTF8'])
    command([bin_dir+'pg_ctl','-D',pgdata,'-l',root+'/postgres.log','-o','-h 127.0.0.1 -p 5432 -k '+root+' -c shared_buffers=32MB -c max_connections=20','-w','-t','30','start'],40)
    pg_started=True
    server=HTTPServer(('127.0.0.1',8090),MockAPI)
    thread=threading.Thread(target=server.serve_forever);thread.daemon=True;thread.start()
    run_id='20261111220'+('0' if role=='dbs' else '1')
    output='/opt/postgresql/basebackup/crg-soak-'+run_id
    env=dict(os.environ,CRG_VENDOR_SOAK_TEST='disposable-loopback-only',CRG_VENDOR_NATIVE_DIAGNOSTICS='qualified-disposable-loopback-only')
    stream=open(root+'/native.log','wb')
    process=subprocess.Popen(['python',worker,'--run-id',run_id,'--seconds','600','--test-phase','smoke'],env=env,stdout=stream,stderr=stream)
    began=time.time();value=None
    while process.poll() is None and time.time()-began<120:
        if os.path.exists(output+'/load.json'):
            with open(output+'/load.json') as saved:value=json.load(saved)
            if value['phase']=='running':break
        time.sleep(.05)
    assert value and value['phase']=='running'
    report.update(phase='waiting-for-host-cleanup',run_id=run_id,worker_pid=process.pid,native_started_utc=value['started_utc'])
    save()
    while process.poll() is None and time.time()-began<180:time.sleep(.05)
    assert process.poll() is not None,'host did not finalize its own native worker within fixture bound'
    stream.close()
    with open(output+'/load.json','rb') as saved:load_raw=saved.read()
    with open(output+'/native-diagnostics.json','rb') as saved:diag_raw=saved.read()
    native,diagnostic=json.loads(load_raw),json.loads(diag_raw);summary=native['native_diagnostics']
    report.update(native_exit=process.returncode,native=native,native_sha256=hashlib.sha256(load_raw).hexdigest(),
                  diagnostic=diagnostic,diagnostic_sha256=hashlib.sha256(diag_raw).hexdigest())
    check('host-TERM-keeps-interrupted-partial-native-failed',process.returncode==1 and native['phase']=='failed' and native['interrupted'] and native['requested_duration_seconds']==600 and 5<=native['elapsed_seconds']<600)
    check('actual-final-native-and-PG-files-identity-linked',summary['diagnostic_complete'] and summary['probe_thread_stopped'] and summary['report_sha256']==report['diagnostic_sha256'] and summary['report_bytes']==len(diag_raw)<=8388608 and diagnostic['run_id']==run_id and diagnostic['worker_sha256']==hashlib.sha256(open(worker,'rb').read()).hexdigest())
    check('actual-partial-SQL-API-counts-match',summary['request_count']==len(diagnostic['requests'])==native['sql']['attempts']+native['api']['attempts'] and summary['request_errors']==native['sql']['errors']+native['api']['errors'])
    check('actual-partial-PG-samples-are-available-and-bounded',4<=len(diagnostic['pg_samples'])<588 and all(v['available'] and not v['truncated'] and len(v['rows'])<=16 for v in diagnostic['pg_samples']))
    check('payload-primary-and-workload-threads-preserved',native['payload_integrity'] and native['primary_not_restarted'] and native['threads_stopped'])
    check('original600s-coverage-not-relaxed',native['sql']['sample_coverage']<.98 and native['api']['sample_coverage']<.98 and native['criteria']['maximum_errors']==0 and native['criteria']['maximum_seconds']==5 and native['phase']=='failed')
    check('no-dropped-request-or-PG-diagnostics',all(summary[k]==0 for k in ['dropped_requests','dropped_pg_samples','pg_errors','recorder_internal_errors','pg_truncated_samples']))
    report['phase']='passed'
except BaseException as error:
    report.update(phase='failed',reason=type(error).__name__+':'+str(error)[:800])
finally:
    if process is not None and process.poll() is None:
        process.kill();process.wait();report['fixture_emergency_kill']=True
    if stream is not None:stream.close()
    if server is not None:server.shutdown();server.server_close()
    if pg_started:
        try:
            command([bin_dir+'pg_ctl','-D',pgdata,'-m','fast','-w','-t','30','stop'],40)
            report['own_postgres_stopped']=True
        except BaseException as error:report.update(phase='failed',cleanup_error=type(error).__name__)
    save()
print(json.dumps({'phase':report['phase'],'checks':len(report['checks']),'reason':report.get('reason')}))
raise SystemExit(0 if report['phase']=='passed' else 1)
