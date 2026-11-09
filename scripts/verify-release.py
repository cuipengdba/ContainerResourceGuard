#!/usr/bin/env python3
"""Offline integrity verification against an EXTERNALLY TRUSTED package digest.

Does not extract or execute the archive. Source authenticity requires an
independently trusted expected hash or verified build attestation, not a sibling
SHA256SUMS downloaded through the same untrusted channel.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import struct
import stat
import tarfile
import tempfile

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('archive',type=Path)
p.add_argument('--sha256',required=True)
p.add_argument('--source-revision',required=True)
p.add_argument('--arch',choices=['amd64','arm64'],required=True)
a=p.parse_args()
if not re.fullmatch('[0-9a-f]{64}',a.sha256) or not re.fullmatch('[0-9a-f]{40}',a.source_revision):p.error('explicit lowercase trusted digest and full source revision required')
def require(condition,message):
    if not condition:raise ValueError(message)
def digest(stream):
    h=hashlib.sha256()
    while True:
        part=stream.read(32768)
        if not part:return h.hexdigest()
        h.update(part)
def verified_snapshot():
    snapshot=tempfile.TemporaryFile()
    try:
        total=0;h=hashlib.sha256()
        fd=os.open(a.archive,os.O_RDONLY|getattr(os,'O_NONBLOCK',0))
        with os.fdopen(fd,'rb') as source:
            require(stat.S_ISREG(os.fstat(source.fileno()).st_mode),'archive must be a regular file')
            while True:
                part=source.read(32768)
                if not part:break
                total+=len(part)
                require(total<=256*1024**2,'compressed archive exceeds 256MiB')
                h.update(part);snapshot.write(part)
        require(h.hexdigest()==a.sha256,'trusted package SHA256 mismatch')
        snapshot.seek(0)
        return snapshot
    except BaseException:
        snapshot.close();raise
try:
    require(a.archive.stat().st_size<=256*1024**2,'compressed archive exceeds 256MiB')
    seen=set();total=0;metadata=None;sbom=None;binary_sha=None
    # Parse the exact private compressed snapshot whose digest was verified,
    # rather than reopening a caller-writable path after verification.
    with verified_snapshot() as snapshot,tarfile.open(fileobj=snapshot,mode='r:gz') as t:
        for index,m in enumerate(t):
            require(index<4096 and m.name not in seen,'too many or duplicate members')
            seen.add(m.name)
            require(not m.name.startswith('/') and '..' not in PurePosixPath(m.name).parts and PurePosixPath(m.name).as_posix()==m.name.rstrip('/'),'unsafe member name')
            require(m.isfile() or m.isdir(),'links/special members not supported')
            total+=m.size
            require(0<=m.size<=(64*1024**2 if m.name=='crg' else 2*1024**2) and total<=128*1024**2,'expanded archive exceeds bounds')
            if m.name in ['BUILD.json','SBOM.cdx.json']:
                raw=t.extractfile(m).read(2*1024**2+1)
                if m.name=='BUILD.json':metadata=json.loads(raw)
                else:sbom=json.loads(raw);sbom_sha=hashlib.sha256(raw).hexdigest()
            elif m.name=='crg':
                with t.extractfile(m) as f:
                    header=f.read(64)
                    require(len(header)==64 and header[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',header,18)[0]=={'amd64':62,'arm64':183}[a.arch],'ELF target mismatch')
                    h=hashlib.sha256(header)
                    while True:
                        part=f.read(32768)
                        if not part:break
                        h.update(part)
                    binary_sha=h.hexdigest()
                require(m.mode&0o111,'binary not executable')
    require(metadata is not None and sbom is not None and binary_sha is not None,'missing build metadata, SBOM or binary')
    require(metadata['source_revision']==a.source_revision and metadata['arch']==a.arch and metadata['os']=='linux' and metadata['product']=='ContainerResourceGuard','source/target/product mismatch')
    require(metadata['binary_sha256']==binary_sha and metadata['sbom_sha256']==sbom_sha,'inner artifact digest mismatch')
    require(sbom['bomFormat']=='CycloneDX' and sbom['specVersion']=='1.6' and {'alg':'SHA-256','content':binary_sha} in sbom['metadata']['component']['hashes'],'SBOM binary binding mismatch')
    print(json.dumps({'state':'verified','archive_sha256':a.sha256,'source_revision':a.source_revision,'arch':a.arch,'binary_sha256':binary_sha,'go_version':metadata['go_version'],'executed':False,'extracted':False,'trust':'caller-supplied expected digest; verify attestation separately'}))
except (ValueError,KeyError,TypeError,EOFError,OSError,tarfile.TarError) as error:
    p.exit(1,json.dumps({'state':'rejected','error':str(error)})+'\n')
