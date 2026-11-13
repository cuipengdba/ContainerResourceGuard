#!/usr/bin/env python3
"""Rebuild a committed revision in a fresh local clone and compare exact bytes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zlib

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('version')
a=p.parse_args()
root=Path(__file__).resolve().parents[1]
revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
names=['crg-linux-'+arch for arch in ['amd64','arm64']]+['containerresourceguard-'+a.version+'-linux-'+arch+'.tar.gz' for arch in ['amd64','arm64']]+['sbom-linux-'+arch+'.cdx.json' for arch in ['amd64','arm64']]+['build-manifest.json','SHA256SUMS']
expected={name:hashlib.sha256((root/'dist'/name).read_bytes()).hexdigest() for name in names}
bash=os.environ.get('CRG_BASH') or ('C:/Program Files/Git/bin/bash.exe' if os.name=='nt' and Path('C:/Program Files/Git/bin/bash.exe').exists() else shutil.which('bash'))
if not bash:p.error('bash required for the published build recipe')
env=dict(os.environ,CRG_PYTHON=sys.executable.replace('\\','/'))
with tempfile.TemporaryDirectory(prefix='crg-reproduce-') as temporary:
    clone=Path(temporary)/'different-absolute-source-directory'
    subprocess.run(['git','clone','--no-hardlinks','--quiet','--no-checkout',str(root),str(clone)],check=True)
    subprocess.run(['git','checkout','--quiet','--detach',revision],cwd=clone,check=True)
    subprocess.run([bash,'scripts/build.sh',a.version],cwd=clone,env=env,check=True)
    subprocess.run([sys.executable,'scripts/package.py',a.version],cwd=clone,env=env,check=True)
    actual={name:hashlib.sha256((clone/'dist'/name).read_bytes()).hexdigest() for name in names}
    if actual!=expected:raise SystemExit('reproducibility mismatch: '+','.join(name for name in names if actual[name]!=expected[name]))
result={'source_revision':revision,'same_toolchain':True,'different_absolute_checkout':True,'byte_equal':True,'packager_environment':{'python':sys.version.split()[0],'zlib_runtime':zlib.ZLIB_RUNTIME_VERSION,'platform':sys.platform},'artifacts':expected,'limits':'same host/toolchain recipe; independent platform and third-party reproduction are separate evidence'}
(root/'dist/reproducibility-check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
