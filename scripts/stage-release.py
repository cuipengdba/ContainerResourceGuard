#!/usr/bin/env python3
"""Verify an offline release snapshot and atomically publish a NEW private directory.

Run this script and its sibling verify-release.py from a pre-trusted checkout.
Never executes package contents, replaces an installed Agent, or changes cgroups.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import subprocess
import sys
import tarfile
import tempfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(st):
    return st.st_dev, st.st_ino


def private_parent(path):
    require(path.is_absolute() and str(path) == os.path.abspath(path),
            'destination must have a clean absolute parent')
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        require(stat.S_ISDIR(os.lstat(current).st_mode), 'parent ancestors must be real directories')
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        st = os.fstat(fd)
        require(st.st_uid == os.geteuid() and stat.S_IMODE(st.st_mode) == 0o700,
                'destination parent must be owned by the current user with mode0700')
        require(identity(st) == identity(os.stat(path, follow_symlinks=False)), 'parent identity changed')
        return fd
    except BaseException:
        os.close(fd)
        raise


def remove_owned(parent, name, expected):
    st = os.stat(name, dir_fd=parent, follow_symlinks=False)
    require(identity(st) == expected and stat.S_ISDIR(st.st_mode), 'temporary directory ownership changed')
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    try:
        require(identity(os.fstat(fd)) == expected, 'temporary directory changed while opening')
        for child in os.listdir(fd):
            value = os.stat(child, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(value.st_mode):
                remove_owned(fd, child, identity(value))
            else:
                os.unlink(child, dir_fd=fd)
    finally:
        os.close(fd)
    require(identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) == expected,
            'temporary directory changed before removal')
    os.rmdir(name, dir_fd=parent)


def parent_of(root, parts):
    fd = os.dup(root)
    try:
        for part in parts:
            try:
                os.mkdir(part, 0o700, dir_fd=fd)
            except FileExistsError:
                pass
            nextfd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nextfd
        return fd
    except BaseException:
        os.close(fd)
        raise


def sync_tree(fd):
    for name in os.listdir(fd):
        st = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if stat.S_ISDIR(st.st_mode):
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                sync_tree(child)
            finally:
                os.close(child)
    os.fsync(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--source-revision', required=True)
    parser.add_argument('--package-revision', required=True)
    parser.add_argument('--arch', choices=['amd64', 'arm64'], required=True)
    a = parser.parse_args()
    parent = stage = None
    temporary = expected = None
    published = False
    files_written = 0
    result = None
    cleanup_error = None
    try:
        require(sys.platform == 'linux' and sys.version_info >= (3, 8), 'Linux with Python3.8+ is required')
        for value, count in [(a.sha256, 64), (a.source_revision, 40), (a.package_revision, 40)]:
            require(re.fullmatch('[0-9a-f]{' + str(count) + '}', value),
                    'trusted lowercase SHA256 and full source/package revisions are required')
        require(a.destination.is_absolute() and str(a.destination) == os.path.abspath(a.destination)
                and a.destination.name not in ['', '.', '..'], 'destination must be a clean absolute new directory')
        libc = ctypes.CDLL(None, use_errno=True)
        rename = getattr(libc, 'renameat2', None)
        require(rename is not None, 'libc renameat2 is required; no replacement fallback')
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        parent = private_parent(a.destination.parent)
        try:
            os.stat(a.destination.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise ValueError('destination already exists; it will not be replaced')
        temporary = '.crg-stage-' + secrets.token_hex(16)
        os.mkdir(temporary, 0o700, dir_fd=parent)
        stage = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        expected = identity(os.fstat(stage))
        verifier = Path(__file__).resolve().with_name('verify-release.py')
        require(verifier.is_file(), 'trusted sibling verify-release.py is missing')
        with tempfile.TemporaryFile(dir='/proc/self/fd/' + str(stage)) as snapshot:
            sourcefd = os.open(a.archive, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(sourcefd, 'rb') as source:
                require(stat.S_ISREG(os.fstat(source.fileno()).st_mode), 'archive must be a regular non-symlink file')
                total, digest = 0, hashlib.sha256()
                while True:
                    part = source.read(32768)
                    if not part:
                        break
                    total += len(part)
                    require(total <= 256 * 1024**2, 'compressed archive exceeds256MiB')
                    digest.update(part)
                    snapshot.write(part)
            require(digest.hexdigest() == a.sha256, 'trusted package SHA256 mismatch')
            snapshot.flush()
            snapshot.seek(0)
            verified = subprocess.run(
                [sys.executable, '-I', str(verifier), '/proc/self/fd/' + str(snapshot.fileno()),
                 '--sha256', a.sha256, '--source-revision', a.source_revision, '--arch', a.arch],
                pass_fds=(snapshot.fileno(),), capture_output=True, timeout=120)
            require(verified.returncode == 0, 'trusted verifier rejected package integrity/source/target')
            verified_info = json.loads(verified.stdout)
            require(verified_info['state'] == 'verified', 'trusted verifier returned unexpected state')
            snapshot.seek(0)
            with tarfile.open(fileobj=snapshot, mode='r:gz') as archive:
                metadata = json.load(archive.extractfile('BUILD.json'))
                require(metadata['package_revision'] == a.package_revision, 'trusted package revision mismatch')
                require('STAGING-VERIFICATION.json' not in archive.getnames(), 'reserved receipt name in package')
                for member in archive:
                    name = member.name.rstrip('/') if member.isdir() else member.name
                    require(name not in ['', '.'] and PurePosixPath(name).as_posix() == name
                            and not name.startswith('/') and '..' not in PurePosixPath(name).parts
                            and not re.search(r'(^[A-Za-z]:|\\)', name), 'unsafe staging member name')
                    require(member.isfile() or member.isdir(), 'links and special files cannot be staged')
                    parts = PurePosixPath(name).parts
                    directory = parent_of(stage, parts if member.isdir() else parts[:-1])
                    try:
                        if member.isdir():
                            continue
                        fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                     0o700 if member.mode & 0o100 else 0o600, dir_fd=directory)
                        with os.fdopen(fd, 'wb') as output, archive.extractfile(member) as source:
                            left = member.size
                            while left:
                                part = source.read(min(left, 32768))
                                require(part, 'truncated archive member')
                                output.write(part)
                                left -= len(part)
                            output.flush()
                            os.fsync(output.fileno())
                        files_written += 1
                    finally:
                        os.close(directory)
            receipt = {'schema': 'crg-verified-staging-v1', 'state': 'verified-before-publication',
                       'archive_sha256': a.sha256, 'source_revision': a.source_revision,
                       'package_revision': a.package_revision, 'arch': a.arch,
                       'binary_sha256': verified_info['binary_sha256'], 'files': files_written,
                       'verifier_sha256': hashlib.sha256(verifier.read_bytes()).hexdigest(),
                       'stager_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                       'package_code_executed': False, 'trust': 'caller-supplied independent expected digest and revisions'}
            fd = os.open('STAGING-VERIFICATION.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=stage)
            with os.fdopen(fd, 'wb') as output:
                output.write((json.dumps(receipt, indent=2) + '\n').encode())
                output.flush()
                os.fsync(output.fileno())
        sync_tree(stage)
        require(identity(os.stat(a.destination.parent, follow_symlinks=False)) == identity(os.fstat(parent)),
                'destination parent identity changed before publication')
        require(identity(os.stat(temporary, dir_fd=parent, follow_symlinks=False)) == expected,
                'temporary directory identity changed before publication')
        # Linux RENAME_NOREPLACE: an existing file, directory or symlink always wins.
        if rename(parent, os.fsencode(temporary), parent, os.fsencode(a.destination.name), 1) != 0:
            number = ctypes.get_errno()
            raise OSError(number, os.strerror(number))
        published = True
        require(identity(os.stat(a.destination.name, dir_fd=parent, follow_symlinks=False)) == expected,
                'published directory identity differs')
        os.fsync(parent)
        result = {**receipt, 'state': 'staged', 'published': True, 'destination': str(a.destination),
                  'installed_agent_replaced': False, 'cgroups_changed': False}
    except (ValueError, KeyError, TypeError, OSError, EOFError, tarfile.TarError,
            subprocess.SubprocessError) as error:
        result = {'state': 'published-unconfirmed' if published else 'rejected',
                  'error': str(error), 'published': published, 'private_files_written': files_written,
                  'package_code_executed': False, 'installed_agent_replaced': False, 'cgroups_changed': False}
    finally:
        if stage is not None:
            os.close(stage)
        if parent is not None:
            if temporary is not None and expected is not None and not published:
                try:
                    remove_owned(parent, temporary, expected)
                except (ValueError, OSError) as error:
                    cleanup_error = str(error)
            os.close(parent)
    if cleanup_error:
        result['cleanup_error'] = cleanup_error
        result['retained_private_temporary_name'] = temporary
    print(json.dumps(result))
    return 0 if result['state'] == 'staged' else 1


if __name__ == '__main__':
    raise SystemExit(main())
