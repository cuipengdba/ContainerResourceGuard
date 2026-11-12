from __future__ import print_function
"""Optional sitecustomize for one frozen disposable native worker, Python 2/3.

Records HTTP connection integers only. The record covers urlopen through headers;
the original native diagnostic remains authoritative for full request completion.
"""
import atexit,hashlib,json,os,re,stat,sys,threading

PREFIX=b'CRG_TRANSPORT_V1 '
WORKER_SHA='bbb86c6af6c472674ebf108686052d5676207b8470b69dbf34fdeb5197cff29b'
MAX_RECORD=512
MAX_RECORDS=1024
URL='http://127.0.0.1:8090/test'

def nonblocking_pipe_sink(source_fd=1):
    """Open a distinct pipe description; never alter original stdout flags."""
    import fcntl
    fd=os.open('/proc/self/fd/'+str(source_fd),os.O_WRONLY|os.O_NONBLOCK|getattr(os,'O_CLOEXEC',0))
    try:
        if not stat.S_ISFIFO(os.fstat(fd).st_mode) or os.fpathconf(fd,'PC_PIPE_BUF')<MAX_RECORD:
            raise ValueError('annotation requires an atomic nonblocking pipe')
        fcntl.fcntl(fd,fcntl.F_SETFD,fcntl.fcntl(fd,fcntl.F_GETFD)|fcntl.FD_CLOEXEC)
    except Exception:
        os.close(fd);raise
    count=[0]
    def emit(row):
        if count[0]>=MAX_RECORDS:return False
        count[0]+=1
        try:
            raw=PREFIX+json.dumps(row,sort_keys=True,separators=(',',':')).encode('ascii')+b'\n'
            if len(raw)>MAX_RECORD:return False
            return os.write(fd,raw)==len(raw)
        except Exception:return False
    def close():
        try:os.close(fd)
        except Exception:pass
    return emit,close

def install(http_class,url_module,clock,sink,run_id):
    if getattr(url_module,'_crg_transport_installed',False):raise ValueError('duplicate transport installation')
    original_connect=http_class.connect;original_urlopen=url_module.urlopen;tls=threading.local()
    def connect(self,*args,**kwargs):
        result=original_connect(self,*args,**kwargs)
        if getattr(tls,'active',False):
            try:
                local=self.sock.getsockname();remote=self.sock.getpeername()
                if local[0]=='127.0.0.1' and remote[0]=='127.0.0.1' and remote[1]==8090:
                    tls.row.update(local_port=int(local[1]),server_port=int(remote[1]))
            except Exception:pass
        return result
    def urlopen(*args,**kwargs):
        try:
            request=args[0];url=request.get_full_url() if hasattr(request,'get_full_url') else request
            row=None
            if url==URL:
                iteration=getattr(tls,'iteration',0);tls.iteration=iteration+1
                row={'run_id':run_id,'iteration':iteration,'kind':'urlopen-headers','socket_timeout_seconds':kwargs.get('timeout'),'started_monotonic_ns':int(clock()*1000000000),'headers_returned':False}
        except Exception:row=None
        if row is None:return original_urlopen(*args,**kwargs)
        tls.row=row;tls.active=True
        try:
            result=original_urlopen(*args,**kwargs);row['headers_returned']=True;return result
        except BaseException as exc:
            row['original_exception_class']=type(exc).__name__;raise
        finally:
            tls.active=False
            try:
                row['finished_monotonic_ns']=int(clock()*1000000000);sink(row)
            except Exception:pass
    http_class.connect=connect;url_module.urlopen=urlopen;url_module._crg_transport_installed=True
    def uninstall():
        http_class.connect=original_connect;url_module.urlopen=original_urlopen;del url_module._crg_transport_installed
    return uninstall

def frozen_worker_launch(raw):
    """Inspect this process's kernel argv; Python2 site runs before sys.argv."""
    if not isinstance(raw,bytes) or not 0<len(raw)<=4096 or not raw.endswith(b'\x00'):return None
    fields=raw[:-1].split(b'\x00')
    if len(fields)<4 or not re.match(br'^python(?:[23](?:\.[0-9]+)?)?\Z',fields[0].rsplit(b'/',1)[-1]):return None
    try:args=[v.decode('ascii') for v in fields[1:]]
    except (UnicodeError,AttributeError):return None
    if not re.match(r'^/tmp/crg-business-reload-[0-9]{8,14}\.py\Z',args[0]) or args.count('--run-id')!=1:return None
    at=args.index('--run-id')
    if at+1>=len(args) or not re.match(r'^[0-9]{8,14}\Z',args[at+1]):return None
    if args[0]!='/tmp/crg-business-reload-'+args[at+1]+'.py':return None
    return {'entry':args[0],'run_id':args[at+1]}


def activate():
    if os.environ.get('CRG_VENDOR_TRANSPORT')!='qualified-disposable-loopback-only' or os.environ.get('CRG_VENDOR_SOAK_TEST')!='disposable-loopback-only' or os.environ.get('CRG_VENDOR_NATIVE_DIAGNOSTICS')!='qualified-disposable-loopback-only':return False
    with open('/proc/self/cmdline','rb') as stream:launch=frozen_worker_launch(stream.read(4097))
    if launch is None:return False
    run_id=launch['run_id']
    with open(launch['entry'],'rb') as stream:raw=stream.read(65537)
    if len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=WORKER_SHA:return False
    if open('/proc/self/cgroup').read()!=open('/proc/1/cgroup').read():return False
    try:
        import http.client as http
        import urllib.request as url_module
    except ImportError:
        import httplib as http
        import urllib2 as url_module
    sink,close=nonblocking_pipe_sink()
    try:install(http.HTTPConnection,url_module,lambda:sys.modules['__main__'].monotonic(),sink,run_id)
    except Exception:close();raise
    atexit.register(close);return True

try:ACTIVATED=activate()
except Exception:ACTIVATED=False
