from pathlib import Path
import fcntl,json,os,resource,socket,sys,threading,time

def emit(value):print(json.dumps(value),flush=True)
root=Path(__file__).parent
server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1)
pr,pw=os.pipe();os.set_blocking(pw,False)
while True:
    try:os.write(pw,b'x'*4096)
    except BlockingIOError:break
emit({'phase':'ready','pid':os.getpid(),'tid':threading.get_native_id(),'port':server.getsockname()[1],'pipe_write_fd':pw})
fd=None;path=None
try:
    command=input()
    if command=='long':
        path=root/('own-long-'+str(os.getpid())+'.bin')
        fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_APPEND,0o600);st=os.fstat(fd)
        info={'path':str(path),'fd':fd,'inode':st.st_ino,'major':os.major(st.st_dev),'minor':os.minor(st.st_dev),'mode':st.st_mode,'flags':fcntl.fcntl(fd,fcntl.F_GETFL)}
        cpu=resource.getrusage(resource.RUSAGE_SELF);cpu_start=cpu.ru_utime+cpu.ru_stime
        began=time.monotonic_ns();until=time.monotonic()+600;calls=[]
        emit({'phase':'long-started','started_ns':began,'file':info})
        while time.monotonic()<until:
            server.settimeout(min(.5,max(.001,until-time.monotonic())))
            try:connection,address=server.accept()
            except socket.timeout:continue
            with connection:
                connection.settimeout(4);data=connection.recv(4096)
                assert data==b'GET /test HTTP/1.0\r\n\r\n'
                before=time.monotonic_ns();count=os.write(fd,b'x'*143);after=time.monotonic_ns();assert count==143
                calls.append({'count':143,'return':count,'started_ns':before,'finished_ns':after,'tid':threading.get_native_id()})
                connection.sendall(b'HTTP/1.0 200 OK\r\nContent-Length: 3\r\n\r\n000')
        ended=time.monotonic_ns();cpu=resource.getrusage(resource.RUSAGE_SELF)
        emit({'phase':'long-finished','started_ns':began,'finished_ns':ended,'elapsed_seconds':(ended-began)/1e9,'file':info,'calls':calls,'bytes_written':len(calls)*143,'measured_target_cpu_seconds':cpu.ru_utime+cpu.ru_stime-cpu_start,'target_maxrss_kB_observed_before_final_report':cpu.ru_maxrss})
    elif command=='flood':
        fd=os.open('/dev/null',os.O_WRONLY);began=time.monotonic_ns()
        for index in range(100000):assert os.write(fd,b'x')==1
        os.close(fd);fd=None
        emit({'phase':'flood-finished','actual_calls':100000,'started_ns':began,'finished_ns':time.monotonic_ns()})
    else:raise AssertionError('unexpected own command')
    assert input()=='finish'
finally:
    if fd is not None:
        assert path is not None and os.fstat(fd).st_ino==path.stat().st_ino
        os.close(fd)
        assert not path.is_symlink();path.unlink()
    server.close();os.close(pr);os.close(pw)
