from __future__ import print_function
import fcntl,hashlib,imp,json,os,stat,sys,threading,time

before=fcntl.fcntl(1,fcntl.F_GETFL);stdout_info=os.fstat(1);has_argv=hasattr(sys,'argv');had_clock=hasattr(sys.modules['__main__'],'monotonic')
import sitecustomize as transport
error_class=None;error_errno=None
if not transport.ACTIVATED:
    try:transport.activate()
    except Exception as error:error_class=type(error).__name__;error_errno=getattr(error,'errno',None)
try:
    import BaseHTTPServer as server_module
    import urllib2 as url_module
except ImportError:
    import http.server as server_module
    import urllib.request as url_module
requests=[]
class Handler(server_module.BaseHTTPRequestHandler):
    def do_POST(self):
        length=int(self.headers.get('Content-Length','0'));assert 0<=length<=64
        body=self.rfile.read(length);requests.append({'path':self.path,'payload':body.decode('ascii')})
        reply=b'{"Result":"000"}';self.send_response(200);self.send_header('Content-Length',str(len(reply)));self.end_headers();self.wfile.write(reply)
    def log_message(self,*args):pass
server=server_module.HTTPServer(('127.0.0.1',8090),Handler);server.timeout=4
thread=threading.Thread(target=server.handle_request);thread.daemon=True;thread.start()
# This is a unit-only clock for one synthetic HTTP request before argparse --help.
# The unchanged native worker defines its own clock once its module executes.
main=sys.modules['__main__'];main.monotonic=lambda:time.time()
request=url_module.Request('http://127.0.0.1:8090/test',data=b'{}')
response=url_module.urlopen(request,timeout=4);body=response.read();response.close();thread.join(5);server.server_close()
assert not thread.is_alive() and body==b'{"Result":"000"}' and requests==[{'path':'/test','payload':'{}'}]
del main.monotonic
status={'variant':os.environ['CRG_FIFO_UNIT_VARIANT'],'activated':bool(transport.ACTIVATED),'activation_error_class':error_class,'activation_errno':error_errno,'has_sys_argv_during_site':has_argv,'main_monotonic_defined_during_site':had_clock,'stdout_is_FIFO':stat.S_ISFIFO(stdout_info.st_mode),'stdout_owner_uid':stdout_info.st_uid,'euid':os.geteuid(),'stdout_flags_before':before,'stdout_flags_after':fcntl.fcntl(1,fcntl.F_GETFL),'own_HTTP_payload_unchanged':True,'own_HTTP_complete_response':body.decode('ascii'),'own_HTTP_timeout_seconds':4,'own_HTTP_thread_stopped':True,'unit_clock_only_not_native_workload':True,'source_sha256':hashlib.sha256(open(transport.__file__.replace('.pyc','.py'),'rb').read()).hexdigest()}
raw=json.dumps(status,sort_keys=True).encode('ascii');assert len(raw)<=8192
fd=os.open(os.environ['CRG_FIFO_UNIT_STATUS'],os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'wb') as stream:stream.write(raw)
