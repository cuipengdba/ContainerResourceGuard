#!/usr/bin/env python3
"""Validate checksums, static ELF targets, bundled binary equality and doc links."""
import argparse
import hashlib
import json
from pathlib import Path
import posixpath
import re
import struct
import tarfile

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('version')
a=p.parse_args()
root=Path(__file__).resolve().parents[1]
results=[]
sums={name:sha for sha,name in (line.split() for line in (root/'dist/SHA256SUMS').read_text().splitlines())}
for arch,machine in [('amd64',62),('arm64',183)]:
    artifact=root/'dist'/f'containerresourceguard-{a.version}-linux-{arch}.tar.gz'
    assert hashlib.sha256(artifact.read_bytes()).hexdigest()==sums[artifact.name], 'checksum mismatch'
    with tarfile.open(artifact) as t:
        members={m.name:m for m in t.getmembers()}
        assert all(not m.issym() and not m.islnk() and not m.name.startswith('/') and '..' not in m.name.split('/') for m in members.values())
        data=t.extractfile('crg').read()
        metadata=json.loads(t.extractfile('BUILD.json').read())
        assert metadata['version']==a.version and metadata['arch']==arch and metadata['binary_sha256']==hashlib.sha256(data).hexdigest()
        assert data[:4]==b'\x7fELF' and struct.unpack_from('<H',data,18)[0]==machine
        assert members['crg'].mode&0o111
        assert data==(root/'dist'/f'crg-linux-{arch}').read_bytes(), 'packaged binary differs'
        phoff=struct.unpack_from('<Q',data,32)[0]
        phentsize,phnum=struct.unpack_from('<HH',data,54)
        assert all(struct.unpack_from('<I',data,phoff+i*phentsize)[0]!=3 for i in range(phnum)), 'dynamic interpreter'
        bad=[]
        for name,m in members.items():
            if not name.endswith('.md') or not m.isfile():continue
            for link in re.findall(r'\]\(([^)]+)\)',t.extractfile(m).read().decode()):
                if link.startswith(('https:','http:','#')):continue
                target=posixpath.normpath(posixpath.join(posixpath.dirname(name),link.split('#')[0]))
                if target not in members:bad.append((name,link))
        assert not bad,bad
        results.append({'arch':arch,'static_elf':True,'markdown_links_valid':True,'binary_sha256':hashlib.sha256(data).hexdigest()})
(root/'dist/package-check.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
