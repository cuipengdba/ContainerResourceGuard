from __future__ import print_function
import errno,hashlib,json,os,shutil,stat,subprocess,sys,time

assert os.geteuid()!=0
root='/tmp/crg-fifo-startup847';os.mkdir(root,0o700)
native=open('/tmp/frozen-native.py','rb').read();native_sha='bbb86c6af6c472674ebf108686052d5676207b8470b69dbf34fdeb5197cff29b';assert hashlib.sha256(native).hexdigest()==native_sha
wrapper=open('/tmp/fifo-startup-wrapper.py','rb').read();cases=[]
for index,variant in enumerate(['success','no-reader','full-pipe','no-channel']):
    runid=str(2026111284700+index);entry='/tmp/crg-business-reload-'+runid+'.py';fd=os.open(entry,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o444)
    with os.fdopen(fd,'wb') as stream:stream.write(native)
    folder=root+'/'+variant;os.mkdir(folder,0o700)
    with open(folder+'/sitecustomize.py','wb') as stream:stream.write(wrapper)
    channel_dir='/tmp/crg-transport-'+runid;os.mkdir(channel_dir,0o700);channel=channel_dir+'/annotations.fifo';os.mkfifo(channel,0o600)
    reader=None;filler=None
    if variant!='no-reader':reader=os.open(channel,os.O_RDONLY|os.O_NONBLOCK)
    if variant=='full-pipe':
        filler=os.open(channel,os.O_WRONLY|os.O_NONBLOCK)
        while True:
            try:os.write(filler,b'x'*4096)
            except OSError as error:assert error.errno in [errno.EAGAIN,errno.EWOULDBLOCK];break
    status_path=folder+'/status.json'
    env=dict(os.environ);env.update(CRG_VENDOR_TRANSPORT='qualified-disposable-loopback-only',CRG_VENDOR_SOAK_TEST='disposable-loopback-only',CRG_VENDOR_NATIVE_DIAGNOSTICS='qualified-disposable-loopback-only',PYTHONPATH=folder,PYTHONDONTWRITEBYTECODE='1',CRG_FIFO_UNIT_STATUS=status_path,CRG_FIFO_UNIT_VARIANT=variant)
    env.pop('CRG_VENDOR_TRANSPORT_FIFO',None)
    if variant!='no-channel':env['CRG_VENDOR_TRANSPORT_FIFO']=channel
    started=time.time()
    # Inherit su's root-owned stdout; do not create a replacement stdout pipe.
    child=subprocess.Popen(['python',entry,'--run-id',runid,'--seconds','1','--help'],env=env,stdout=sys.stdout,stderr=sys.stderr,close_fds=True);code=child.wait();elapsed=time.time()-started
    status_raw=open(status_path,'rb').read(8193);assert len(status_raw)<=8192;status=json.loads(status_raw)
    content=b''
    if reader is not None:
        while True:
            try:block=os.read(reader,4096)
            except OSError as error:assert error.errno in [errno.EAGAIN,errno.EWOULDBLOCK];break
            if not block:break
            content+=block;assert len(content)<=1048576
    if filler is not None:os.close(filler)
    if reader is not None:os.close(reader)
    annotations=[]
    if variant=='success':
        for line in content.splitlines():
            assert line.startswith(b'CRG_TRANSPORT_V1 ') and len(line)+1<=512
            annotations.append(json.loads(line[len(b'CRG_TRANSPORT_V1 '):]))
        assert len(annotations)==1
        row=annotations[0];assert row['run_id']==runid and row['iteration']==0 and row['local_port']>0 and row['server_port']==8090 and row['headers_returned'] and row['socket_timeout_seconds']==4 and 'success' not in row
    elif variant=='full-pipe':assert content and content==b'x'*len(content)
    else:assert not content
    expected=variant in ['success','full-pipe'];passed=code==0 and elapsed<15 and status['activated']==expected and not status['has_sys_argv_during_site'] and not status['main_monotonic_defined_during_site'] and status['stdout_is_FIFO'] and status['stdout_owner_uid']==0 and status['euid']!=0 and status['stdout_flags_before']==status['stdout_flags_after'] and status['own_HTTP_payload_unchanged'] and status['own_HTTP_thread_stopped']
    if variant=='no-reader':passed=passed and status['activation_errno']==errno.ENXIO
    assert hashlib.sha256(open(entry,'rb').read()).hexdigest()==native_sha
    os.unlink(entry);os.unlink(channel);os.rmdir(channel_dir)
    cases.append({'variant':variant,'passed':bool(passed),'status':status,'child_exit':code,'elapsed_seconds':elapsed,'annotations':annotations,'FIFO_bytes_read':len(content),'private_channel_cleaned':not os.path.lexists(channel_dir),'original_native_SHA_unchanged':True,'only_own_HTTP_and_original_argparse_help_no_vendor_DB_or_native600':True})
shutil.rmtree(root)
print('CRG_FIFO_HARNESS '+json.dumps({'schema':'crg-private-fifo-real-python-startup-v1','phase':'passed' if all(v['passed'] for v in cases) else 'failed','Python':sys.version.split()[0],'cases':cases,'private_files_cleaned':not os.path.exists(root),'original_native_SHA_unchanged':True,'vendor_database_or_native600_started':False}))
