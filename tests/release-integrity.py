#!/usr/bin/env python3
"""Exercise offline verifier against real packages and malicious archive forms."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

p=argparse.ArgumentParser();p.add_argument('version');a=p.parse_args()
root=Path(__file__).resolve().parents[1]
revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
checks=[]
def check(name,archive,expected,arch='amd64',source=revision,success=False):
    result=subprocess.run([sys.executable,str(root/'scripts/verify-release.py'),str(archive),'--sha256',expected,'--source-revision',source,'--arch',arch],capture_output=True,text=True,timeout=30)
    if (result.returncode==0)!=success:raise AssertionError(name+': '+result.stdout+result.stderr)
    checks.append({'name':name,'passed':True})
for arch in ['amd64','arm64']:
    archive=root/'dist'/('containerresourceguard-'+a.version+'-linux-'+arch+'.tar.gz')
    check('valid-'+arch,archive,hashlib.sha256(archive.read_bytes()).hexdigest(),arch=arch,success=True)
archive=root/'dist'/('containerresourceguard-'+a.version+'-linux-amd64.tar.gz');original=archive.read_bytes();sha=hashlib.sha256(original).hexdigest()
check('wrong-external-digest',archive,'0'*64)
check('wrong-architecture',archive,sha,arch='arm64')
check('wrong-source-revision',archive,sha,source='0'*40)
with tempfile.TemporaryDirectory(prefix='crg-integrity-') as temporary:
    directory=Path(temporary)
    bad=directory/'truncated.tar.gz';bad.write_bytes(original[:len(original)//2]);check('truncated-archive',bad,hashlib.sha256(bad.read_bytes()).hexdigest())
    for name,member in [('traversal','../escape'),('absolute','/escape'),('windows-drive','C:/escape'),('backslash','..\\escape'),('symlink','link'),('duplicate','same')]:
        bad=directory/(name+'.tar.gz')
        with tarfile.open(bad,'w:gz') as t:
            info=tarfile.TarInfo(member)
            if name=='symlink':info.type=tarfile.SYMTYPE;info.linkname='/etc/passwd'
            t.addfile(info)
            if name=='duplicate':t.addfile(info)
        check(name,bad,hashlib.sha256(bad.read_bytes()).hexdigest())
    bad=directory/'changed-binary.tar.gz'
    with tarfile.open(archive,'r:gz') as source,tarfile.open(bad,'w:gz') as target:
        for info in source:
            if info.isfile():
                data=source.extractfile(info).read()
                if info.name=='crg':data=data[:-1]+bytes([data[-1]^1])
                target.addfile(info,io.BytesIO(data))
            else:target.addfile(info)
    check('inner-binary-binding',bad,hashlib.sha256(bad.read_bytes()).hexdigest())
    check('changed-package-cannot-use-old-trusted-digest',bad,sha)
result={'checks':checks,'count':len(checks),'scope':'offline integrity and parser bounds; signature identity verified separately'}
(root/'dist/integrity-check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
