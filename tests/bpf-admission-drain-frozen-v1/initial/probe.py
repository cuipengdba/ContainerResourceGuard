from pathlib import Path
import fcntl, json, os, sys, threading, time

root=Path(__file__).parent
path=root/('write-'+str(os.getpid())+'.data'); fd=os.open(str(path),os.O_CREAT|os.O_EXCL|os.O_RDWR,0o600)
pr,pw=os.pipe(); fcntl.fcntl(pw,fcntl.F_SETFL,os.O_NONBLOCK); filled=0
while True:
    try:filled+=os.write(pw,b'p'*4096)
    except BlockingIOError:break
fcntl.fcntl(pw,fcntl.F_SETFL,0)
stat=os.fstat(fd)
def emit(row):print(json.dumps(row),flush=True)
emit({'phase':'ready','pid':os.getpid(),'tid':threading.get_native_id(),'regular_fd':fd,'inode':stat.st_ino,'device':stat.st_dev,'mode':stat.st_mode,'pipe_write_fd':pw,'pipe_capacity_filled':filled})
try:
    while True:
        command=sys.stdin.readline().strip()
        if command=='finish':break
        if command=='burst':
            calls=[]; begin=time.monotonic_ns()
            for index in range(32):
                start=time.monotonic_ns(); n=os.write(fd,b'x'*143); end=time.monotonic_ns(); assert n==143
                calls.append({'iteration':index,'begin_ns':start,'end_ns':end,'bytes':n})
            emit({'phase':'burst-finished','begin_ns':begin,'end_ns':time.monotonic_ns(),'tid':threading.get_native_id(),'fd':fd,'calls':calls})
        elif command=='block':
            def release():
                release_command=sys.stdin.readline().strip()
                assert release_command in ['release','burst-then-release']
                if release_command=='burst-then-release':
                    calls=[]; start=time.monotonic_ns()
                    for index in range(32):
                        begin=time.monotonic_ns(); n=os.write(fd,b'y'*143); end=time.monotonic_ns(); assert n==143
                        calls.append({'iteration':index,'begin_ns':begin,'end_ns':end,'bytes':n})
                    emit({'phase':'closing-regular-burst-finished','begin_ns':start,'end_ns':time.monotonic_ns(),'tid':threading.get_native_id(),'fd':fd,'calls':calls})
                assert len(os.read(pr,4096))==4096
            helper=threading.Thread(target=release); helper.start()
            emit({'phase':'about-to-block','tid':threading.get_native_id(),'fd':pw,'count':4096})
            begin=time.monotonic_ns(); n=os.write(pw,b'b'*4096); end=time.monotonic_ns(); assert n==4096
            helper.join(timeout=3); assert not helper.is_alive()
            emit({'phase':'blocked-write-finished','begin_ns':begin,'end_ns':end,'tid':threading.get_native_id(),'fd':pw,'bytes':n})
        else:raise AssertionError('unexpected own probe command')
finally:
    os.close(fd); os.close(pr); os.close(pw); path.unlink()
