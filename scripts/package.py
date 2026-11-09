"""Package already built artifacts; never include private profiles or test data."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import subprocess

parser=argparse.ArgumentParser()
parser.add_argument('version')
parser.add_argument('--source-revision',help='revision embedded in the tested binary; defaults to current HEAD')
args=parser.parse_args()
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',args.version):parser.error('invalid version')
root=Path(__file__).resolve().parents[1]
dist=root/'dist'
def normalize(info):
    if '__pycache__' in info.name.split('/') or info.name.endswith('.pyc'):return None
    info.uid=info.gid=0
    info.uname=info.gname=''
    info.mode=0o755 if info.isdir() or info.name=='crg' or info.name.endswith('.sh') else 0o644
    return info
outputs=[]
package_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
revision=args.source_revision or package_revision
if not re.fullmatch(r'[0-9a-f]{40}',revision):parser.error('source-revision must be a full Git SHA')
for arch in ('amd64','arm64'):
    binary=dist/f'crg-linux-{arch}'
    if not binary.is_file():raise SystemExit(f'missing {binary}')
    artifact=dist/f'containerresourceguard-{args.version}-linux-{arch}.tar.gz'
    with tarfile.open(artifact,'w:gz') as archive:
        archive.add(binary,arcname='crg',filter=normalize)
        metadata=json.dumps({'product':'ContainerResourceGuard','version':args.version,'source_revision':revision,'package_revision':package_revision,'os':'linux','arch':arch,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()},indent=2).encode()+b'\n'
        entry=tarfile.TarInfo('BUILD.json');entry.size=len(metadata);entry.mode=0o644
        archive.addfile(entry,io.BytesIO(metadata))
        for name in ('README.md','LICENSE','CHANGELOG.md','SECURITY.md','docs','examples','scripts'):
            archive.add(root/name,arcname=name,filter=normalize)
        archive.add(root/'tests/README.md',arcname='tests/README.md',filter=normalize)
    outputs.append(artifact)
(dist/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in outputs),encoding='utf-8')
for p in outputs:print(p)
