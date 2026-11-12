from __future__ import print_function
import hashlib,json,os,shutil,subprocess,sys,time

assert os.geteuid()!=0;runid=sys.argv[1];variant=sys.argv[2];assert runid.isdigit() and 8<=len(runid)<=14 and variant in ['normal','no-reader','stopped-reader']
native=open('/tmp/frozen-native.py','rb').read();native_sha='bbb86c6af6c472674ebf108686052d5676207b8470b69dbf34fdeb5197cff29b';assert hashlib.sha256(native).hexdigest()==native_sha
entry='/tmp/crg-business-reload-'+runid+'.py';fd=os.open(entry,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o444)
with os.fdopen(fd,'wb') as stream:stream.write(native)
folder='/tmp/crg-receiver867-'+runid;os.mkdir(folder,0o700)
with open(folder+'/usercustomize.py','wb') as stream:stream.write(open('/tmp/receiver-usercustomize.py','rb').read())
channel='/tmp/crg-transport-'+runid;status_path=folder+'/status.json';env=dict(os.environ);env.update(CRG_VENDOR_TRANSPORT='qualified-disposable-loopback-only',CRG_VENDOR_SOAK_TEST='disposable-loopback-only',CRG_VENDOR_NATIVE_DIAGNOSTICS='qualified-disposable-loopback-only',CRG_VENDOR_TRANSPORT_FIFO=channel+'/annotations.fifo',PYTHONPATH=channel+':'+folder,PYTHONDONTWRITEBYTECODE='1',CRG_FIFO_UNIT_STATUS=status_path,CRG_FIFO_UNIT_VARIANT=variant)
began=time.time();child=subprocess.Popen(['python',entry,'--run-id',runid,'--seconds','1','--help'],env=env,stdout=sys.stdout,stderr=sys.stderr,close_fds=True);code=child.wait();elapsed=time.time()-began
raw=open(status_path,'rb').read(8193);assert len(raw)<=8192;status=json.loads(raw)
passed=code==0 and elapsed<15 and status['activated']==(variant=='normal') and not status['has_sys_argv_during_site'] and not status['main_monotonic_defined_during_site'] and status['stdout_is_FIFO'] and status['stdout_owner_uid']==0 and status['euid']==999 and status['stdout_flags_before']==status['stdout_flags_after'] and status['own_HTTP_payload_unchanged'] and status['own_HTTP_timeout_seconds']==4 and status['own_HTTP_thread_stopped']
if variant!='normal':passed=passed and status['activation_errno']==6
assert hashlib.sha256(open(entry,'rb').read()).hexdigest()==native_sha
os.unlink(entry);shutil.rmtree(folder)
print('CRG_RECEIVER_HARNESS '+json.dumps({'schema':'crg-real-original-image-host-receiver-startup-v1','phase':'passed' if passed else 'failed','Python':sys.version.split()[0],'variant':variant,'run_id':runid,'status':status,'child_exit':code,'elapsed_seconds':elapsed,'private_unit_folder_cleaned':not os.path.exists(folder),'original_native_SHA_unchanged':True,'only_own_HTTP_and_original_help_no_vendor_DB600':True}))
