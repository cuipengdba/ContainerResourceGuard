from __future__ import print_function
import errno,fcntl,hashlib,json,os,shutil,stat,sys,tempfile,time

path=sys.argv[1];raw=open(path,'rb').read();module={'__file__':path,'__name__':'fifo_unit'};exec(compile(raw,path,'exec'),module);assert not module['ACTIVATED']
root=tempfile.mkdtemp(prefix='crg-fifo-unit-');cases=[]
def check(name,test):
    test();cases.append({'variant':name,'passed':True})
def channel(index):
    folder=root+'/crg-transport-'+str(2026111284600+index);os.mkdir(folder,0o700);p=folder+'/annotations.fifo';os.mkfifo(p,0o600);return p
def rejected(p,allowed):
    try:
        emit,close=module['nonblocking_fifo_sink'](p);close()
    except Exception as error:
        assert isinstance(error,allowed),type(error).__name__;return
    raise AssertionError('unsafe channel accepted')
try:
    def success():
        p=channel(0);reader=os.open(p,os.O_RDONLY|os.O_NONBLOCK);emit,close=module['nonblocking_fifo_sink'](p)
        try:
            assert emit({'iteration':0});line=os.read(reader,512);assert line.startswith(module['PREFIX']) and len(line)<=512 and json.loads(line[len(module['PREFIX']):])=={'iteration':0}
        finally:close();os.close(reader)
    check('private-FIFO-atomic-record-roundtrip',success)
    def absent_reader():
        p=channel(1);started=time.time()
        try:module['nonblocking_fifo_sink'](p)
        except OSError as error:assert error.errno==errno.ENXIO
        else:raise AssertionError('reader absent should fail')
        assert time.time()-started<1
    check('missing-reader-fails-immediately',absent_reader)
    def full():
        p=channel(2);reader=os.open(p,os.O_RDONLY|os.O_NONBLOCK);emit,close=module['nonblocking_fifo_sink'](p);filling=os.open(p,os.O_WRONLY|os.O_NONBLOCK)
        try:
            while True:
                try:os.write(filling,b'x'*4096)
                except OSError as error:assert error.errno in [errno.EAGAIN,errno.EWOULDBLOCK];break
            started=time.time();assert not emit({'iteration':0}) and time.time()-started<1
        finally:close();os.close(filling);os.close(reader)
    check('full-FIFO-drops-without-blocking',full)
    def directory_mode():
        p=channel(3);os.chmod(os.path.dirname(p),0o755);rejected(p,(ValueError,))
    check('public-directory-rejected',directory_mode)
    def fifo_mode():
        p=channel(4);os.chmod(p,0o644);rejected(p,(ValueError,))
    check('public-FIFO-rejected',fifo_mode)
    def regular():
        p=channel(5);os.unlink(p);fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd);rejected(p,(ValueError,))
    check('regular-file-rejected',regular)
    def symlink():
        p=channel(6);os.rename(p,p+'.real');os.symlink(p+'.real',p);rejected(p,(ValueError,))
    check('FIFO-symlink-rejected',symlink)
    def dirlink():
        p=channel(7);folder=os.path.dirname(p);os.rename(folder,folder+'.real');os.symlink(folder+'.real',folder);rejected(p,(ValueError,))
    check('directory-symlink-rejected',dirlink)
    check('wrong-basename-rejected',lambda:rejected(root+'/wrong',(ValueError,)))
    def oversize():
        p=channel(8);reader=os.open(p,os.O_RDONLY|os.O_NONBLOCK);emit,close=module['nonblocking_fifo_sink'](p)
        try:
            assert not emit({'value':'z'*1024})
            try:assert not os.read(reader,2048)
            except OSError as error:assert error.errno in [errno.EAGAIN,errno.EWOULDBLOCK]
        finally:close();os.close(reader)
    check('oversize-record-dropped-without-prefix-fragment',oversize)
    def limit():
        p=channel(9);reader=os.open(p,os.O_RDONLY|os.O_NONBLOCK);emit,close=module['nonblocking_fifo_sink'](p)
        try:
            for index in range(1024):assert emit({'iteration':index});assert os.read(reader,512)
            assert not emit({'iteration':1024})
        finally:close();os.close(reader)
    check('1024-record-upper-bound',limit)
    def stdout():
        before=fcntl.fcntl(1,fcntl.F_GETFL);p=channel(10);reader=os.open(p,os.O_RDONLY|os.O_NONBLOCK);emit,close=module['nonblocking_fifo_sink'](p)
        try:assert emit({'iteration':0}) and before==fcntl.fcntl(1,fcntl.F_GETFL)
        finally:close();os.close(reader)
    check('business-stdout-flags-unchanged',stdout)
    def unicode_path():
        p=channel(11);reader=os.open(p,os.O_RDONLY|os.O_NONBLOCK)
        try:
            try:text_type=unicode
            except NameError:text_type=str
            emit,close=module['nonblocking_fifo_sink'](text_type(p))
            try:assert emit({'iteration':0}) and os.read(reader,512).startswith(module['PREFIX'])
            finally:close()
        finally:os.close(reader)
    check('Python2-unicode-path-from-decoded-proc-argv',unicode_path)
finally:shutil.rmtree(root)
print(json.dumps({'schema':'crg-private-fifo-unit-v1','phase':'passed','Python':sys.version.split()[0],'source_sha256':hashlib.sha256(raw).hexdigest(),'cases':cases,'private-unit-files-cleaned':not os.path.exists(root),'synthetic_only_no_vendor_business':True}))
