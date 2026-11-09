"""Package already built artifacts; never include private profiles or test data."""
import argparse
import hashlib
from pathlib import Path
import re
import tarfile

parser=argparse.ArgumentParser()
parser.add_argument('version')
args=parser.parse_args()
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',args.version):parser.error('invalid version')
root=Path(__file__).resolve().parents[1]
dist=root/'dist'
def normalize(info):
    info.uid=info.gid=0
    info.uname=info.gname=''
    info.mode=0o755 if info.isdir() or info.name=='crg' or info.name.endswith('.sh') else 0o644
    return info
outputs=[]
for arch in ('amd64','arm64'):
    binary=dist/f'crg-linux-{arch}'
    if not binary.is_file():raise SystemExit(f'missing {binary}')
    artifact=dist/f'containerresourceguard-{args.version}-linux-{arch}.tar.gz'
    with tarfile.open(artifact,'w:gz') as archive:
        archive.add(binary,arcname='crg',filter=normalize)
        for name in ('README.md','LICENSE','CHANGELOG.md','SECURITY.md','docs','examples'):
            archive.add(root/name,arcname=name,filter=normalize)
    outputs.append(artifact)
(dist/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in outputs),encoding='utf-8')
for p in outputs:print(p)
