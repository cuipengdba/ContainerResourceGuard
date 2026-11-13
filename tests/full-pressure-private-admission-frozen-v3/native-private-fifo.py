"""Bounded host receiver for one disposable container's diagnostic-only FIFO.

No production resource control, worker source edits, child signals, stdout flag
changes, retries, or cross-container supervision belong in this module.
"""
from pathlib import Path
import errno,hashlib,json,os,re,stat,threading,time

PREFIX=b'CRG_TRANSPORT_V1 '
MAX_BYTES=1048576
MAX_RECORD=512
MAX_RECORDS=1024
SHIM_SHA='92d7f4352d0f413efbed0e49495d4ad0ff36f74f617a2291173a7e36e28b06b2'

class Rejected(Exception):pass

def require(value,reason):
    if not value:raise Rejected(reason)

def file_identity(value):return (value.st_dev,value.st_ino,stat.S_IFMT(value.st_mode))

class Channel:
    def __init__(self,tmp_root,run_id,uid,gid,shim,verify_identity):
        require(isinstance(run_id,str) and re.fullmatch(r'[0-9]{8,14}',run_id) is not None,'RUN_ID')
        require(type(uid) is int and type(gid) is int and 0<=uid<2147483648 and 0<=gid<2147483648,'OWNER_ID')
        require(type(shim) is bytes and len(shim)<=65536 and hashlib.sha256(shim).hexdigest()==SHIM_SHA,'FROZEN_SHIM')
        require(Path(tmp_root).is_absolute() and callable(verify_identity),'BOUND_CONTAINER_ROOT')
        self.tmp_root=Path(tmp_root);self.run_id=run_id;self.uid=uid;self.gid=gid;self.shim=shim;self.verify_identity=verify_identity
        self.name='crg-transport-'+run_id;self.container_directory='/tmp/'+self.name;self.container_FIFO=self.container_directory+'/annotations.fifo'
        self.parent_fd=None;self.directory_fd=None;self.directory_identity=None;self.owned={};self.reader_fd=None;self.thread=None
        self.buffer=bytearray();self.observed_bytes=0;self.errors=[];self.stop_requested=threading.Event();self.started=False;self.stopped=False;self.cleaned=False;self.reader_closed=True;self.created=False
    def guard(self):require(self.verify_identity() is True,'CONTAINER_IDENTITY_CHANGED')
    def prepare(self):
        require(not self.created and self.parent_fd is None,'DUPLICATE_PREPARE');self.guard()
        self.parent_fd=os.open(str(self.tmp_root),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
        try:
            os.mkdir(self.name,0o700,dir_fd=self.parent_fd);self.created=True
            self.directory_fd=os.open(self.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=self.parent_fd)
            self.directory_identity=file_identity(os.fstat(self.directory_fd))
            fd=os.open('sitecustomize.py',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o444,dir_fd=self.directory_fd)
            try:
                self.owned['sitecustomize.py']=file_identity(os.fstat(fd));at=0
                while at<len(self.shim):
                    written=os.write(fd,self.shim[at:]);require(written>0,'SHIM_SHORT_WRITE');at+=written
                os.fchmod(fd,0o444);os.fchown(fd,self.uid,self.gid)
            finally:os.close(fd)
            os.mkfifo('annotations.fifo',0o600,dir_fd=self.directory_fd)
            self.owned['annotations.fifo']=file_identity(os.stat('annotations.fifo',dir_fd=self.directory_fd,follow_symlinks=False))
            os.chmod('annotations.fifo',0o600,dir_fd=self.directory_fd,follow_symlinks=False)
            os.chown('annotations.fifo',self.uid,self.gid,dir_fd=self.directory_fd,follow_symlinks=False)
            os.fchmod(self.directory_fd,0o700);os.fchown(self.directory_fd,self.uid,self.gid);self.guard()
            self.validate_directory();return self.status()
        except BaseException:
            # The owner invokes cleanup even when prepare fails. Preserve its
            # original exception; cleanup must never erase the business error.
            raise
    def validate_directory(self):
        require(self.parent_fd is not None and self.directory_fd is not None and self.created,'NOT_PREPARED')
        require(file_identity(os.stat(self.name,dir_fd=self.parent_fd,follow_symlinks=False))==self.directory_identity,'DIRECTORY_REPLACED')
        directory=os.fstat(self.directory_fd);require(stat.S_IMODE(directory.st_mode)==0o700 and directory.st_uid==self.uid and directory.st_gid==self.gid,'DIRECTORY_OWNER_OR_MODE')
        for name,expected in self.owned.items():
            current=os.stat(name,dir_fd=self.directory_fd,follow_symlinks=False)
            require(file_identity(current)==expected and current.st_nlink==1 and current.st_uid==self.uid and current.st_gid==self.gid,'CHANNEL_FILE_REPLACED')
        fifo=os.stat('annotations.fifo',dir_fd=self.directory_fd,follow_symlinks=False)
        require(stat.S_ISFIFO(fifo.st_mode) and stat.S_IMODE(fifo.st_mode)==0o600,'FIFO_MODE')
    def start(self):
        require(not self.started and self.thread is None and not self.stopped,'DUPLICATE_START');self.guard();self.validate_directory()
        fd=os.open('annotations.fifo',os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=self.directory_fd)
        try:require(file_identity(os.fstat(fd))==self.owned['annotations.fifo'],'READER_IDENTITY')
        except BaseException:os.close(fd);raise
        self.reader_fd=fd;self.reader_closed=False
        def receive():
            deadline=None
            try:
                while True:
                    if self.stop_requested.is_set() and deadline is None:deadline=time.monotonic()+1
                    if deadline is not None and time.monotonic()>=deadline:self.errors.append('DRAIN_DEADLINE');break
                    try:part=os.read(fd,min(4096,MAX_BYTES+1-len(self.buffer)))
                    except OSError as error:
                        if error.errno not in [errno.EAGAIN,errno.EWOULDBLOCK]:raise
                        part=None
                    if part:
                        self.observed_bytes+=len(part);remaining=MAX_BYTES-len(self.buffer);self.buffer.extend(part[:remaining])
                        if len(part)>remaining:self.errors.append('RECEIVER_BYTE_BOUND');break
                    else:
                        if self.stop_requested.is_set():break
                        self.stop_requested.wait(.02)
            except Exception as error:self.errors.append('READER_'+type(error).__name__)
            finally:
                os.close(fd);self.reader_closed=True
        self.thread=threading.Thread(target=receive,name='crg-diagnostic-fifo-'+self.run_id,daemon=True)
        try:self.thread.start();self.started=True
        except BaseException:
            os.close(fd);self.reader_closed=True;self.thread=None;raise
        return self.status()
    def stop(self):
        self.stop_requested.set()
        if self.thread is not None:
            self.thread.join(timeout=2);require(not self.thread.is_alive(),'RECEIVER_THREAD_STOP_TIMEOUT')
        self.stopped=True;return self.status()
    def raw(self):
        require(self.stopped and (self.thread is None or not self.thread.is_alive()),'RECEIVER_NOT_STOPPED')
        return bytes(self.buffer)
    def annotations(self):
        raw=self.raw();require(not self.errors,'INCOMPLETE_RECEIVER');require(not raw or raw.endswith(b'\n'),'PARTIAL_ANNOTATION_RECORD');rows=[]
        for line in raw.splitlines():
            require(line.startswith(PREFIX) and len(line)+1<=MAX_RECORD and len(rows)<MAX_RECORDS,'ANNOTATION_RECORD_BOUND_OR_PREFIX')
            value=json.loads(line[len(PREFIX):]);require(type(value) is dict and value.get('run_id')==self.run_id and value.get('kind')=='urlopen-headers','ANNOTATION_SCOPE');rows.append(value)
        return rows
    def status(self):
        return {'run_id':self.run_id,'container_directory':self.container_directory,'container_FIFO':self.container_FIFO,'directory_identity':self.directory_identity,'owned_identities':dict(self.owned),'owner_uid':self.uid,'owner_gid':self.gid,'byte_bound':MAX_BYTES,'record_bound':MAX_RECORD,'record_count_bound':MAX_RECORDS,'retained_bytes':len(self.buffer),'observed_bytes':self.observed_bytes,'errors':list(self.errors),'started':self.started,'stopped':self.stopped,'reader_closed':self.reader_closed,'thread_alive':self.thread.is_alive() if self.thread else False,'cleaned':self.cleaned,'directory_fd_closed':self.directory_fd is None,'parent_fd_closed':self.parent_fd is None,'incomplete':bool(self.errors)}
    def cleanup(self):
        require(self.thread is None or not self.thread.is_alive(),'CLEANUP_WITH_LIVE_READER')
        try:
            if self.created:
                self.guard()
                require(self.directory_fd is not None and self.parent_fd is not None,'MISSING_OWN_DIRECTORY_HANDLE')
                require(file_identity(os.stat(self.name,dir_fd=self.parent_fd,follow_symlinks=False))==self.directory_identity,'CLEANUP_DIRECTORY_REPLACED')
                require(set(os.listdir(self.directory_fd))==set(self.owned),'UNEXPECTED_CHANNEL_CONTENTS')
                for name,expected in self.owned.items():require(file_identity(os.stat(name,dir_fd=self.directory_fd,follow_symlinks=False))==expected,'CLEANUP_FILE_REPLACED')
                for name in self.owned:os.unlink(name,dir_fd=self.directory_fd)
                require(file_identity(os.stat(self.name,dir_fd=self.parent_fd,follow_symlinks=False))==self.directory_identity,'CLEANUP_DIRECTORY_REPLACED')
                os.rmdir(self.name,dir_fd=self.parent_fd);self.cleaned=True
            else:self.cleaned=True
        finally:
            if self.directory_fd is not None:os.close(self.directory_fd);self.directory_fd=None
            if self.parent_fd is not None:os.close(self.parent_fd);self.parent_fd=None
        return self.status()
