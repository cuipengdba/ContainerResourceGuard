from __future__ import print_function
"""Diagnostic-only loader for the original bounded vendor smoke workload.

Keeps its SQL, payload, periods, deadlines and error counting. Adds integer
metadata for the client's own HTTP connection, never response/request content.
"""
import hashlib,os,sys
path='/tmp/crg-bpf710-original.py'
with open(path,'rb') as stream:source=stream.read(65537)
assert hashlib.sha256(source).hexdigest()=='ba87ef2d646b723eb8419de25ffcd736f7a5b0925716f4b638761dff70bb2461'
if not isinstance(source,str):source=source.decode('utf-8')
inject=r'''
# Transport annotation belongs only to this disposable diagnostic worker.
try:
    import http.client as _transport_http
except ImportError:
    import httplib as _transport_http
_transport_tls=threading.local()
_transport_connect_original=_transport_http.HTTPConnection.connect
_transport_urlopen_original=urlopen
def _transport_connect(self,*a,**kw):
    result=_transport_connect_original(self,*a,**kw)
    if getattr(_transport_tls,'active',False):
        try:
            local=self.sock.getsockname();remote=self.sock.getpeername()
            if local[0]=='127.0.0.1' and remote[0]=='127.0.0.1' and remote[1]==8090:
                _transport_tls.value.update(local_port=local[1],server_port=remote[1])
        except Exception:
            _transport_tls.value['endpoint_unknown']=True
    return result
def _transport_urlopen(*a,**kw):
    _transport_tls.active=True
    _transport_tls.value={'kind':'api','socket_timeout_seconds':kw.get('timeout')}
    try:return _transport_urlopen_original(*a,**kw)
    except Exception as e:
        _transport_tls.value['error_class']=type(e).__name__
        raise
    finally:_transport_tls.active=False
def _transport_finish(started,success):
    value=dict(getattr(_transport_tls,'value',{}))
    value.update(started_monotonic_ns=int(started*1000000000),finished_monotonic_ns=int(monotonic()*1000000000),success=bool(success))
    # Output failure never replaces the original API success/error sample.
    try:
        line=json.dumps(value,sort_keys=True)+chr(10)
        target=root+'/transport-events.jsonl'
        if not hasattr(_transport_tls,'file'):
            fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            _transport_tls.file=os.fdopen(fd,'w')
        _transport_tls.file.write(line);_transport_tls.file.flush()
    except Exception:pass
_transport_http.HTTPConnection.connect=_transport_connect
urlopen=_transport_urlopen
'''
assert source.count('def api_load():')==1
needle="sample('api', started, success)";assert source.count(needle)==1
source=source.replace('def api_load():',inject+'\ndef api_load():').replace(needle,needle+'; _transport_finish(started,success)')
exec(compile(source,path,'exec'),{'__name__':'__main__','__file__':path})
