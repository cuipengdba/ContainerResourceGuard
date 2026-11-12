from __future__ import print_function
import hashlib,json,sys

path=sys.argv[1];raw=open(path,'rb').read();ns={'__name__':'proc_activation_unit','__file__':path};exec(compile(raw,path,'exec'),ns);assert not ns['ACTIVATED'];parse=ns['frozen_worker_launch'];runid=b'2026111284300';entry=b'/tmp/crg-business-reload-'+runid+b'.py';base=[b'/usr/bin/python2.7',entry,b'--run-id',runid,b'--seconds',b'1',b'--help']
def cmd(parts):return b'\x00'.join(parts)+b'\x00'
variants=[('valid-python27',cmd(base),True),('valid-python3',cmd([b'/usr/bin/python3.12']+base[1:]),True),('valid-python-relative',cmd([b'python']+base[1:]),True),('wrong-executable',cmd([b'/bin/bash']+base[1:]),False),('interpreter-option-before-entry',cmd([b'python',b'-c']+base[1:]),False),('wrong-script-directory',cmd([base[0],entry.replace(b'/tmp/',b'/opt/production/')]+base[2:]),False),('short-script-ID',cmd([base[0],b'/tmp/crg-business-reload-1234567.py']+base[2:]),False),('long-script-ID',cmd([base[0],b'/tmp/crg-business-reload-123456789012345.py']+base[2:]),False),('missing-run-id',cmd([base[0],entry,b'--seconds',b'1']),False),('missing-run-id-value',cmd([base[0],entry,b'--run-id']),False),('non-numeric-run-id',cmd(base[:3]+[b'not-a-run']+base[4:]),False),('duplicate-run-id',cmd(base+[b'--run-id',runid]),False),('entry-run-id-mismatch',cmd(base[:3]+[b'2026111284301']+base[4:]),False),('missing-final-NUL',cmd(base)[:-1],False),('embedded-empty-field',cmd(base[:1]+[b'']+base[1:]),False),('non-ASCII-field',cmd(base+[b'\xff']),False),('oversized-cmdline',cmd(base+[b'x'*4096]),False),('wrong-object-type',None,False),('empty-cmdline',b'',False)]
cases=[]
for name,value,want in variants:
 result=parse(value);assert bool(result)==want,name
 if want:assert result=={'entry':entry.decode('ascii'),'run_id':runid.decode('ascii')}
 cases.append({'variant':name,'passed':True})
print(json.dumps({'schema':'crg-self-proc-activation-unit-v1','phase':'passed','Python':sys.version.split()[0],'source_sha256':hashlib.sha256(raw).hexdigest(),'cases':cases,'pure_launch_parser_only_not_actual_startup_or_native_workload':True}))
