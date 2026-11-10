#!/usr/bin/env python3
"""Verify and select the pinned published preview executable, without rebuilding it.

Acceptance fixture only. Downloaded checksums are checked against a separately
reviewed contract, not used as their own trust root. No archive paths are extracted.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import tarfile

VERSION = 'v0.1.0-rc.3-preview.1'
SOURCE = '7638ee9f871287d1056e267034e0c4e46903b66e'
PACKAGE = '73bf2aaf38dfd92757cd58e610d4e49debc56b1f'
TAG_OBJECT = '54cd5c74852aa680c9779783328bfeaebf5e8744'
SUMS_SHA256 = '6d810ca571c4a2d0ae9f9b47a1f924dff1e87de6b78d99e2f5394b33b1480ae1'
ARTIFACTS = {
    'amd64': {'id': 730823163, 'size': 1708379, 'machine': 62,
              'archive': '65ad8e81d85249e7d4f96d216eaed8cc09b6e03b41d3b65342da9d62b6c9c45f',
              'binary': 'f07973272313db26d359797dda4665145f7dd6490bac2a55f9084bd367faf361'},
    'arm64': {'id': 730823217, 'size': 1553342, 'machine': 183,
              'archive': '3e650f035bb87411821e429b611c39e3e42860ddfe78c722555c4de981a0c89a',
              'binary': 'c20a9ea5b070ea1039f1dcdc8cbba867eda58eb016c1c4cd8aceec28a8151463'},
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(folder, arch):
    expected = ARTIFACTS[arch]
    name = f'containerresourceguard-{VERSION}-linux-{arch}.tar.gz'
    release = json.loads((folder / 'release.json').read_text(encoding='utf-8'))
    tag = json.loads((folder / 'tag.json').read_text(encoding='utf-8'))
    annotated = json.loads((folder / 'tag-object.json').read_text(encoding='utf-8'))
    require(release['id'] == 440151208 and release['tag_name'] == VERSION and
            release['draft'] is False and release['prerelease'] is True, 'release identity differs')
    require(tag['ref'] == 'refs/tags/' + VERSION and tag['object']['type'] == 'tag' and
            tag['object']['sha'] == TAG_OBJECT and annotated['sha'] == TAG_OBJECT and
            annotated['tag'] == VERSION and annotated['object']['type'] == 'commit' and
            annotated['object']['sha'] == PACKAGE, 'published annotated tag no longer matches package revision')
    assets = [a for a in release['assets'] if a['name'] == name]
    require(len(assets) == 1 and assets[0]['id'] == expected['id'] and
            assets[0]['size'] == expected['size'] and
            assets[0]['digest'] == 'sha256:' + expected['archive'], 'release asset identity differs')
    sums = (folder / 'SHA256SUMS').read_bytes()
    require(hashlib.sha256(sums).hexdigest() == SUMS_SHA256, 'downloaded checksum file differs')
    entries = [line.split() for line in sums.decode('ascii').splitlines()]
    require(len(entries) == 2 and len({e[1] for e in entries}) == 2 and
            all(len(e) == 2 and e[1] == f'containerresourceguard-{VERSION}-linux-{a}.tar.gz' and
                e[0] == ARTIFACTS[a]['archive'] for e, a in zip(entries, ['amd64', 'arm64'])),
            'checksum inventory differs')
    archive = folder / name
    require(archive.stat().st_size == expected['size'] and
            hashlib.sha256(archive.read_bytes()).hexdigest() == expected['archive'], 'archive digest differs')
    with tarfile.open(archive, 'r:gz') as bundle:
        members = bundle.getmembers()
        names = [m.name for m in members]
        require(len(names) == len(set(names)) and sum(m.size for m in members) <= 64 * 1024**2,
                'duplicate or oversized archive')
        require(all(not PurePosixPath(m.name).is_absolute() and '..' not in PurePosixPath(m.name).parts
                    and '\\' not in m.name and (m.isfile() or m.isdir()) for m in members),
                'unsafe archive member')
        binary_member = bundle.getmember('crg')
        require(binary_member.isfile() and binary_member.mode & 0o111, 'executable missing')
        binary = bundle.extractfile(binary_member).read()
        metadata = json.loads(bundle.extractfile('BUILD.json').read())
    require(metadata == {'product': 'ContainerResourceGuard', 'version': VERSION,
                         'source_revision': SOURCE, 'package_revision': PACKAGE,
                         'os': 'linux', 'arch': arch, 'binary_sha256': expected['binary']},
            'package metadata differs')
    require(hashlib.sha256(binary).hexdigest() == expected['binary'], 'published executable differs')
    require(binary[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<H', binary, 18)[0] == expected['machine'],
            'native ELF target differs')
    offset = struct.unpack_from('<Q', binary, 32)[0]
    size, count = struct.unpack_from('<HH', binary, 54)
    require(size >= 56 and offset + size * count <= len(binary) and
            all(struct.unpack_from('<I', binary, offset + size * n)[0] != 3 for n in range(count)),
            'invalid ELF or dynamic interpreter')
    return binary, {'version': VERSION, 'source_revision': SOURCE, 'package_revision': PACKAGE, 'tag_object': TAG_OBJECT,
                    'architecture': arch, 'asset_id': expected['id'], 'archive_sha256': expected['archive'],
                    'binary_sha256': expected['binary'], 'checksum_file_sha256': SUMS_SHA256,
                    'scope': 'published bytes selected; not yet execution or controller acceptance'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--arch', choices=ARTIFACTS, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    binary, receipt = verify(args.directory, args.arch)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'crg').write_bytes(binary)
    (args.output / 'crg').chmod(0o755)
    (args.output / 'verification.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
