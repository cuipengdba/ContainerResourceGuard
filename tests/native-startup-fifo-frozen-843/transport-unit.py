from __future__ import print_function
import errno,fcntl,hashlib,json,os,sys,threading,time,types

path=sys.argv[1];namespace={'__file__':path,'__name__':'transport_unit_module'}
raw=open(path,'rb').read();exec(compile(raw,path,'exec'),namespace)
assert not namespace['ACTIVATED'];cases=[]
class Sock(object):
    def getsockname(self):return ('127.0.0.1',34567)
    def getpeername(self):return ('127.0.0.1',8090)
class Request(object):
    data=b'{}'
    def __init__(self,url):self.url=url
    def get_full_url(self):return self.url
for variant in ['success','urlopen-error','body-error-after-headers','sink-error','clock-error','non-target-URL','non-target-URL-error','connection-metadata-error']:
    rows=[];calls=[];primary=ValueError('original-urlopen');body_error=ValueError('original-body');sentinel=object()
    class Response(object):
        def read(self):
            if variant=='body-error-after-headers':raise body_error
            return b'{"Result":"000"}'
    response=Response()
    class HTTP(object):
        def connect(self,*args,**kwargs):
            calls.append(('connect',args,kwargs));self.sock=Sock()
            if variant=='connection-metadata-error':self.sock=sentinel
            return sentinel
    def original(request,*args,**kwargs):
        calls.append(('urlopen',request,args,kwargs));assert HTTP().connect() is sentinel
        if variant in ['urlopen-error','non-target-URL-error']:raise primary
        return response
    module=types.ModuleType('url_module');module.urlopen=original
    def clock():
        if variant=='clock-error':raise OSError('clock unavailable')
        return 123.0+len(rows)*.01
    def sink(row):
        if variant=='sink-error':raise OSError('annotation unavailable')
        rows.append(dict(row))
    uninstall=namespace['install'](HTTP,module,clock,sink,'202611120001')
    request=Request('http://example.invalid/' if variant.startswith('non-target-URL') else namespace['URL']);caught=None;result=None
    try:result=module.urlopen(request,timeout=4)
    except BaseException as exc:caught=exc
    assert len([v for v in calls if v[0]=='urlopen'])==1
    assert calls[0][1] is request and calls[0][3]=={'timeout':4} and request.data==b'{}'
    if variant in ['urlopen-error','non-target-URL-error']:
        assert caught is primary
        if variant=='urlopen-error':assert rows[0]['original_exception_class']=='ValueError' and not rows[0]['headers_returned']
    else:assert caught is None and result is response
    if variant=='body-error-after-headers':
        try:result.read()
        except Exception as exc:assert exc is body_error
        else:raise AssertionError('body failure lost')
        assert rows[0]['headers_returned'] and 'success' not in rows[0]
    if variant not in ['sink-error','clock-error','non-target-URL','non-target-URL-error']:
        assert len(rows)==1 and rows[0]['iteration']==0 and rows[0]['socket_timeout_seconds']==4
        if variant!='connection-metadata-error':assert rows[0]['local_port']==34567 and rows[0]['server_port']==8090
        else:assert 'local_port' not in rows[0]
    else:assert not rows
    uninstall();assert module.urlopen is original
    cases.append({'variant':variant,'original_call_return_or_exact_exception_preserved':True,'payload_and_four_second_timeout_unchanged':True})

read_fd,write_fd=os.pipe();before=fcntl.fcntl(write_fd,fcntl.F_GETFL)
emit,close=namespace['nonblocking_pipe_sink'](write_fd)
try:
    assert fcntl.fcntl(write_fd,fcntl.F_GETFL)==before
    assert emit({'iteration':0})
    line=os.read(read_fd,512);assert line.startswith(namespace['PREFIX']) and json.loads(line[len(namespace['PREFIX']):])=={'iteration':0}
    # Fill via a separate nonblocking description; the annotation must drop promptly.
    filling=os.open('/proc/self/fd/'+str(write_fd),os.O_WRONLY|os.O_NONBLOCK)
    try:
        while True:
            try:os.write(filling,b'x'*4096)
            except OSError as exc:
                assert exc.errno in [errno.EAGAIN,errno.EWOULDBLOCK];break
        started=time.time();assert emit({'iteration':1}) is False;assert time.time()-started<1
    finally:os.close(filling)
    assert fcntl.fcntl(write_fd,fcntl.F_GETFL)==before
finally:close();os.close(read_fd);os.close(write_fd)
cases.append({'variant':'full-pipe-drops-annotation-without-blocking-or-changing-stdout-flags','passed':True})
result={'schema':'crg-native-transport-shim-unit-v1','phase':'passed','Python':sys.version.split()[0],'source_sha256':hashlib.sha256(raw).hexdigest(),'cases':cases,'synthetic_only_not_original_full_pressure':True,'headers_return_not_business_success':True,'native_worker_source_unchanged':True}
print(json.dumps(result,sort_keys=True))
