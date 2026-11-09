"""Package already built artifacts; never include private profiles or test data."""
import argparse
import hashlib
import gzip
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
    info.mtime=epoch
    info.uname=info.gname=''
    info.mode=0o755 if info.isdir() or info.name=='crg' or info.name.endswith('.sh') else 0o644
    return info
outputs=[]
package_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
revision=args.source_revision or package_revision
if not re.fullmatch(r'[0-9a-f]{40}',revision):parser.error('source-revision must be a full Git SHA')
epoch=int(subprocess.check_output(['git','show','-s','--format=%ct',package_revision],cwd=root,text=True).strip())
manifest=json.loads((dist/'build-manifest.json').read_text(encoding='utf-8'))
if manifest['source_revision']!=revision or manifest['version']!=args.version:parser.error('build manifest revision/version mismatch')
# Only committed, allowlisted public blobs enter the package. Working-tree or
# untracked files can never silently become release documentation or scripts.
snapshot=subprocess.check_output(['git','archive','--format=tar',package_revision],cwd=root)
public={}
with tarfile.open(fileobj=io.BytesIO(snapshot),mode='r:') as source:
    for member in source:
        name=member.name
        selected=name in ('README.md','LICENSE','THIRD_PARTY_NOTICES.md','CHANGELOG.md','SECURITY.md','tests/README.md') or name.startswith(('docs/','examples/','scripts/'))
        if not selected:continue
        if member.isdir():public[name]=None
        elif member.isfile():public[name]=source.extractfile(member).read()
        else:raise SystemExit('release source contains unsupported link/special file')
for arch in ('amd64','arm64'):
    binary=dist/f'crg-linux-{arch}'
    if not binary.is_file():raise SystemExit(f'missing {binary}')
    artifact=dist/f'containerresourceguard-{args.version}-linux-{arch}.tar.gz'
    digest=hashlib.sha256(binary.read_bytes()).hexdigest()
    build=next(x for x in manifest['artifacts'] if x['arch']==arch)
    if build['binary_sha256']!=digest:raise SystemExit('binary differs from build manifest')
    sbom=(dist/f'sbom-linux-{arch}.cdx.json').read_bytes()
    metadata=json.dumps({'product':'ContainerResourceGuard','version':args.version,'source_revision':revision,'package_revision':package_revision,'os':'linux','arch':arch,'binary_sha256':digest,'go_version':manifest['go_version'],'sbom_sha256':hashlib.sha256(sbom).hexdigest(),'source_date_epoch':manifest['source_date_epoch']},indent=2,sort_keys=True).encode()+b'\n'
    entries=dict(public,**{'crg':binary.read_bytes(),'BUILD.json':metadata,'SBOM.cdx.json':sbom})
    with artifact.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as compressed,tarfile.open(fileobj=compressed,mode='w',format=tarfile.PAX_FORMAT) as archive:
        for name,data in sorted(entries.items()):
            info=tarfile.TarInfo(name)
            if data is None:info.type=tarfile.DIRTYPE
            else:info.size=len(data)
            info=normalize(info)
            archive.addfile(info,None if data is None else io.BytesIO(data))
    outputs.append(artifact)
(dist/'SHA256SUMS').write_bytes(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in outputs).encode('utf-8'))
for p in outputs:print(p)
