#!/usr/bin/env python3
"""Bounded directory-depth reproduction/regression; disposable GitHub VM only."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import tarfile
import tempfile

p = argparse.ArgumentParser(description=__doc__)
for n in ['candidate', 'stager', 'baseline', 'plan', 'output']:
    p.add_argument('--' + n, type=Path, required=True)
p.add_argument('--arch', choices=['amd64', 'arm64'], required=True)
a = p.parse_args()
if (sys.platform != 'linux' or os.environ.get('GITHUB_ACTIONS') != 'true'
        or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted'):
    p.error('disposable GitHub-hosted Linux VM required')
sha = lambda raw: hashlib.sha256(raw).hexdigest()
plan = json.loads(a.plan.read_bytes())
assert sha(a.baseline.read_bytes()) == '1d8faf3c88948cf946559878a4f279e4f68f7ab6ecabaeea5b27f52e02fbd952'
assert sha(a.candidate.read_bytes()) == plan['artifacts'][a.arch]['candidate_sha256']
a.output.mkdir(parents=True, exist_ok=False)
root = Path(tempfile.mkdtemp(prefix='crg-depth-CI-'))
root.chmod(0o700)
report = {'schema': 'crg-staging-depth-v1', 'arch': a.arch, 'kernel': platform.release(),
          'python': platform.python_version(), 'baseline_sha256': sha(a.baseline.read_bytes()),
          'stager_sha256': sha(a.stager.read_bytes()), 'plan_sha256': sha(a.plan.read_bytes()),
          'candidate_sha256': sha(a.candidate.read_bytes()), 'cases': [], 'phase': 'running',
          'package_code_executed': False, 'cgroups_changed': False}


def save():
    (a.output / 'depth-report.json').write_text(json.dumps(report, indent=2) + '\n')


def entries(path):
    """Iterative bounded walk: intentionally avoids Python recursive cleanup."""
    found, pending = [], [(path, 0)]
    while pending:
        current, depth = pending.pop()
        assert depth <= 1105 and len(found) < 1200
        st = current.lstat()
        found.append((current, depth, stat.S_ISDIR(st.st_mode)))
        if stat.S_ISDIR(st.st_mode):
            with os.scandir(current) as children:
                for child in children:
                    pending.append((Path(child.path), depth + 1))
    return found


def clean(path):
    for item, depth, directory in reversed(entries(path)):
        if directory:
            item.rmdir()
        else:
            item.unlink()


def fixture(name, depth, directory, late):
    target = root / (name + '.tar.gz')
    with tarfile.open(a.candidate, 'r:gz') as original, tarfile.open(target, 'w:gz') as out:
        required = ['BUILD.json', 'SBOM.cdx.json', 'crg']
        def add_deep():
            info = tarfile.TarInfo('/'.join(['d'] * depth))
            info.type = tarfile.DIRTYPE if directory else tarfile.REGTYPE
            out.addfile(info, None if directory else io.BytesIO(b''))
        if not late:
            add_deep()
        for member in required:
            info = original.getmember(member)
            out.addfile(info, io.BytesIO(original.extractfile(info).read()))
        if late:
            add_deep()
    return target


def case(name, tool, depth, directory=True, late=True, expected='rejected'):
    archive = fixture(name, depth, directory, late)
    destination = root / name
    command = [sys.executable, '-I', str(tool), str(archive), '--destination', str(destination),
               '--sha256', sha(archive.read_bytes()), '--source-revision', plan['source_revision'],
               '--package-revision', plan['candidate_package_revision'], '--arch', a.arch]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    (a.output / (name + '.stdout')).write_text(result.stdout)
    (a.output / (name + '.stderr')).write_text(result.stderr)
    try:
        value = json.loads(result.stdout)
    except ValueError:
        value = None
    residue = list(root.glob('.crg-stage-*'))
    count = sum(len(entries(path)) for path in residue)
    row = {'name': name, 'depth': depth, 'directory': directory, 'late': late, 'exit': result.returncode,
           'result': value, 'stderr_sha256': sha(result.stderr.encode()),
           'unhandled_recursion_error': 'RecursionError' in result.stderr,
           'destination_present': destination.exists(), 'private_residue_directories': len(residue),
           'private_residue_entries': count}
    report['cases'].append(row)
    save()
    if expected == 'baseline-defect':
        row['passed'] = (result.returncode != 0 and not destination.exists() and len(residue) == 1
                         and count >= 1000 and (row['unhandled_recursion_error']
                                               or bool(value and value.get('cleanup_error'))))
    elif expected == 'staged':
        row['passed'] = (result.returncode == 0 and value and value['state'] == 'staged'
                         and destination.is_dir() and not residue
                         and sha((destination / 'crg').read_bytes()) == plan['artifacts'][a.arch]['candidate_binary_sha256'])
    else:
        row['passed'] = (result.returncode != 0 and value and value['state'] == 'rejected'
                         and not value['published'] and not destination.exists() and not residue
                         and not value.get('cleanup_error') and value['private_files_written'] == 0
                         and 'depth exceeds64' in value['error'])
    for path in residue:
        clean(path)
    if destination.exists():
        clean(destination)
    archive.unlink()
    row['owned_cleanup_verified'] = not list(root.glob('.crg-stage-*')) and not destination.exists()
    save()
    assert row['passed'] and row['owned_cleanup_verified'], name


try:
    case('old-1100-directory', a.baseline, 1100, expected='baseline-defect')
    case('boundary-64-directory', a.stager, 64, expected='staged')
    case('boundary-64-file', a.stager, 64, False, expected='staged')
    case('reject-65-directory', a.stager, 65)
    case('reject-65-file', a.stager, 65, False)
    case('reject-1100-directory-late', a.stager, 1100)
    case('reject-1100-directory-first', a.stager, 1100, late=False)
    report['phase'] = 'passed'
finally:
    report['root_empty_before_cleanup'] = not list(root.iterdir())
    if report['root_empty_before_cleanup']:
        root.rmdir()
    report['owned_root_removed'] = not root.exists()
    save()
