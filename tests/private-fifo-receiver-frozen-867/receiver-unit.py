from pathlib import Path
import errno,fcntl,hashlib,importlib.util,json,os,sys,tempfile,time

source=Path(sys.argv[1]);shim=Path(sys.argv[2]).read_bytes();spec=importlib.util.spec_from_file_location('receiver_under_test',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);cases=[]
def check(name,work):work();cases.append({'variant':name,'passed':True})
def reject(work,code):
    try:work()
    except m.Rejected as error:assert str(error)==code;return
    raise AssertionError('expected '+code)
def record(run_id,index=0):return m.PREFIX+json.dumps({'run_id':run_id,'kind':'urlopen-headers','iteration':index},separators=(',',':')).encode()+b'\n'
with tempfile.TemporaryDirectory(prefix='crg-receiver863-unit-') as tmp:
    root=Path(tmp);serial=[2026111286300]
    def channel(guard=lambda:True):
        serial[0]+=1;c=m.Channel(root,str(serial[0]),os.geteuid(),os.getegid(),shim,guard);c.prepare();return c
    def dispose(c):c.stop();c.cleanup();assert c.status()['cleaned'] and c.status()['reader_closed']
    def send(c,raw):
        fd=os.open(str(root/c.name/'annotations.fifo'),os.O_WRONLY|os.O_NONBLOCK)
        try:assert os.write(fd,raw)==len(raw)
        finally:os.close(fd)
    def normal():
        c=channel();before=fcntl.fcntl(1,fcntl.F_GETFL);c.start();raw=record(c.run_id);send(c,raw);c.stop();assert c.raw()==raw and len(c.annotations())==1 and not c.status()['incomplete'] and before==fcntl.fcntl(1,fcntl.F_GETFL);c.cleanup();assert not (root/c.name).exists()
    check('actual-private-FIFO-thread-exact-record-and-cleanup',normal)
    def no_reader():
        c=channel()
        try:
            try:os.open(str(root/c.name/'annotations.fifo'),os.O_WRONLY|os.O_NONBLOCK)
            except OSError as error:assert error.errno==errno.ENXIO
            else:raise AssertionError('unexpected reader')
        finally:dispose(c)
    check('prepared-without-reader-never-blocks-writer-open',no_reader)
    def close_before():
        c=channel();c.start();c.stop();assert c.status()['reader_closed']
        try:os.open(str(root/c.name/'annotations.fifo'),os.O_WRONLY|os.O_NONBLOCK)
        except OSError as error:assert error.errno==errno.ENXIO
        else:raise AssertionError('reader leaked')
        c.cleanup()
    check('stopped-reader-is-really-closed-before-worker',close_before)
    def no_writer():
        c=channel();c.start();time.sleep(.05);assert c.thread.is_alive();c.stop();assert c.raw()==b'' and c.annotations()==[];c.cleanup()
    check('no-writer-EOF-keeps-ready-until-bounded-stop',no_writer)
    def malformed():
        c=channel();c.start();send(c,b'not-a-record\n');c.stop();reject(c.annotations,'ANNOTATION_RECORD_BOUND_OR_PREFIX');assert c.raw()==b'not-a-record\n';c.cleanup()
    check('malformed-prefix-retains-raw-and-rejects-acceptance',malformed)
    def partial():
        c=channel();c.start();send(c,record(c.run_id)[:-1]);c.stop();reject(c.annotations,'PARTIAL_ANNOTATION_RECORD');c.cleanup()
    check('partial-last-line-rejected',partial)
    def wrong_run():
        c=channel();c.start();send(c,record('2026111200000'));c.stop();reject(c.annotations,'ANNOTATION_SCOPE');c.cleanup()
    check('foreign-run-id-rejected',wrong_run)
    def oversize():
        c=channel();c.start();send(c,m.PREFIX+b'x'*512+b'\n');c.stop();reject(c.annotations,'ANNOTATION_RECORD_BOUND_OR_PREFIX');c.cleanup()
    check('513-plus-byte-record-rejected-with-raw-retained',oversize)
    def count_limit():
        c=channel();c.start();fd=os.open(str(root/c.name/'annotations.fifo'),os.O_WRONLY|os.O_NONBLOCK)
        try:
            for index in range(1025):
                raw=record(c.run_id,index);deadline=time.monotonic()+3
                while True:
                    try:assert os.write(fd,raw)==len(raw);break
                    except BlockingIOError:assert time.monotonic()<deadline;time.sleep(.002)
        finally:os.close(fd)
        c.stop();reject(c.annotations,'ANNOTATION_RECORD_BOUND_OR_PREFIX');assert c.raw().count(b'\n')==1025;c.cleanup()
    check('1025-record-stream-rejected-not-silently-truncated',count_limit)
    def overflow():
        c=channel();c.start();fd=os.open(str(root/c.name/'annotations.fifo'),os.O_WRONLY|os.O_NONBLOCK);deadline=time.monotonic()+5;written=0
        try:
            while c.thread.is_alive():
                assert time.monotonic()<deadline
                try:written+=os.write(fd,b'x'*4096)
                except BlockingIOError:time.sleep(.001)
                except BrokenPipeError:break
        finally:os.close(fd)
        c.stop();status=c.status();assert status['incomplete'] and status['errors']==['RECEIVER_BYTE_BOUND'] and len(c.raw())==1048576 and status['observed_bytes']==1048577;reject(c.annotations,'INCOMPLETE_RECEIVER');c.cleanup()
    check('actual-byte-flood-closes-reader-at1MiB-plus1-and-marks-incomplete',overflow)
    def identity_start():
        allow=[True];c=channel(lambda:allow[0]);allow[0]=False;reject(c.start,'CONTAINER_IDENTITY_CHANGED');allow[0]=True;dispose(c)
    check('PID1-root-identity-change-before-start-rejected',identity_start)
    def replaced_fifo():
        c=channel();p=root/c.name/'annotations.fifo';p.rename(p.with_name('held-original'));os.mkfifo(p,0o600);reject(c.start,'CHANNEL_FILE_REPLACED');reject(c.cleanup,'UNEXPECTED_CHANNEL_CONTENTS');assert p.exists() and p.with_name('held-original').exists();p.unlink();p.with_name('held-original').unlink();(root/c.name/'sitecustomize.py').unlink();(root/c.name).rmdir()
    check('replaced-FIFO-not-opened-or-deleted-by-cleanup',replaced_fifo)
    def foreign_content():
        c=channel();p=root/c.name/'foreign';p.write_bytes(b'keep');reject(c.cleanup,'UNEXPECTED_CHANNEL_CONTENTS');assert p.read_bytes()==b'keep';p.unlink();(root/c.name/'sitecustomize.py').unlink();(root/c.name/'annotations.fifo').unlink();(root/c.name).rmdir()
    check('unexpected-file-prevents-channel-deletion',foreign_content)
    def mkdir_collision():
        serial[0]+=1;runid=str(serial[0]);p=root/('crg-transport-'+runid);p.mkdir();keep=p/'keep';keep.write_bytes(b'keep');c=m.Channel(root,runid,os.geteuid(),os.getegid(),shim,lambda:True)
        try:c.prepare()
        except FileExistsError:pass
        else:raise AssertionError('directory collision accepted')
        c.stop();c.cleanup();assert keep.read_bytes()==b'keep';keep.unlink();p.rmdir()
    check('existing-directory-never-adopted-or-removed',mkdir_collision)
    def preparation_failure():
        serial[0]+=1;c=m.Channel(root,str(serial[0]),os.geteuid(),os.getegid(),shim,lambda:True);original=m.os.mkfifo;primary=PermissionError('denied')
        def denied(*a,**kw):raise primary
        m.os.mkfifo=denied
        try:
            try:c.prepare()
            except Exception as error:assert error is primary
            else:raise AssertionError('fault absent')
        finally:m.os.mkfifo=original
        dispose(c);assert not (root/c.name).exists()
    check('partial-prepare-permission-failure-cleaned-and-exact-error-kept',preparation_failure)
    def live_cleanup():
        c=channel();c.start();reject(c.cleanup,'CLEANUP_WITH_LIVE_READER');dispose(c)
    check('live-reader-must-stop-before-cleanup',live_cleanup)
    def closed_handles():
        c=channel();c.start();fds=[c.parent_fd,c.directory_fd,c.reader_fd];dispose(c)
        for fd in fds:
            try:os.fstat(fd)
            except OSError as error:assert error.errno==errno.EBADF
            else:raise AssertionError('descriptor leaked')
    check('all-owned-real-descriptors-closed',closed_handles)
    def broken_reader():
        path=Path(sys.argv[2]);module={'__file__':str(path),'__name__':'private_receiver_broken_pipe_unit'};exec(compile(shim,str(path),'exec'),module);assert not module['ACTIVATED']
        c=channel();c.start();emit,close=module['nonblocking_fifo_sink'](str(root/c.name/'annotations.fifo'));c.stop();began=time.monotonic()
        try:assert emit({'run_id':c.run_id,'kind':'urlopen-headers'}) is False and time.monotonic()-began<1
        finally:close();c.cleanup()
    check('real-reader-loss-EPIPE-drops-annotation-without-blocking',broken_reader)
    assert not list(root.iterdir())
print(json.dumps({'schema':'crg-private-fifo-host-receiver-unit-v1','phase':'passed','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'shim_sha256':hashlib.sha256(shim).hexdigest(),'cases':cases,'real_FIFO_thread_and_flood':True,'container_business_not_qualified':True,'own_temporary_files_cleaned':True}))
