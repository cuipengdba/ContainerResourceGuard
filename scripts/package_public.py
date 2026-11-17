"""Build bounded deployment documentation from a committed Git archive only."""
import hashlib
import io
import json
import posixpath
import re
import tarfile

MAX_FILE = 2 * 1024**2
MAX_PUBLIC_BYTES = 60 * 1024**2
MAX_PUBLIC_MEMBERS = 4000
ROOT_FILES = {'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'CHANGELOG.md',
              'SECURITY.md', 'tests/README.md', 'tests/vendor-engine-smoke.py',
              'tests/vendor-soak-load.py', 'tests/vendor-soak-campaign.py'}
NOTICE = 'PACKAGE-DOCUMENTATION.json'


def collect_public(snapshot, revision):
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('documentation revision must be a full Git SHA')
    public, originals, omitted, rewrites, expanded_directories = {}, {}, {}, [], set()
    with tarfile.open(fileobj=io.BytesIO(snapshot), mode='r:') as archive:
        members = {}
        for member in archive:
            name = member.name
            if (name.startswith('/') or '\\' in name or ':' in name or
                    posixpath.normpath(name) != name or '..' in name.split('/') or name in members):
                raise ValueError('noncanonical or duplicate committed archive path')
            members[name] = member
        if NOTICE in members:
            raise ValueError('generated documentation manifest collides with source')

        def remote(name):
            return 'https://github.com/cuipengdba/ContainerResourceGuard/blob/' + revision + '/' + name

        def add(name):
            if name in omitted or (name in public and (not members[name].isdir() or name in expanded_directories)):
                return
            if name not in members:
                raise ValueError('documentation target is absent from committed source: ' + name)
            member = members[name]
            if not member.isfile() and not member.isdir():
                raise ValueError('documentation references a link or special member: ' + name)
            if '__pycache__' in name.split('/') or name.endswith('.pyc'):
                raise ValueError('documentation references excluded bytecode: ' + name)
            if member.isdir():
                expanded_directories.add(name)
                public[name] = None
                for child in members:
                    if child.startswith(name + '/'):
                        add(child)
            else:
                data = archive.extractfile(member).read()
                if len(data) != member.size:
                    raise ValueError('truncated committed source member')
                if len(data) > MAX_FILE:
                    if not name.startswith('docs/') or not name.endswith(('.json', '.json.gz')):
                        raise ValueError('required public file exceeds offline verifier bound: ' + name)
                    omitted[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                                     'url': remote(name)}
                    return
                public[name] = originals[name] = data
            parent = posixpath.dirname(name)
            while parent:
                if parent in members and members[parent].isdir():
                    public[parent] = None
                parent = posixpath.dirname(parent)

        # Select files, not whole directories: historical evidence can be large.
        for name, member in members.items():
            if member.isdir():
                continue
            if name in ROOT_FILES or name.startswith(('docs/', 'examples/', 'scripts/')):
                add(name)
        visited = set()
        while True:
            pending = [name for name, data in public.items()
                       if data is not None and name.endswith('.md') and name not in visited]
            if not pending:
                break
            for name in sorted(pending):
                visited.add(name)

                def link(match):
                    href = match[1]
                    if href.startswith(('https:', 'http:', '#', 'mailto:')):
                        return match[0]
                    target, separator, fragment = href.partition('#')
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
                    if target.startswith(('/', '../')) or target == '..' or '\\' in target or ':' in target:
                        raise ValueError('documentation link leaves committed archive')
                    add(target)
                    if target not in omitted:
                        return match[0]
                    replacement = remote(target) + (separator + fragment if separator else '')
                    rewrites.append({'document': name, 'original_link': href, 'packaged_link': replacement})
                    return '](' + replacement + ')'

                public[name] = re.sub(r'\]\(([^)]+)\)', link, originals[name].decode('utf-8')).encode('utf-8')
    notice = {'schema': 'crg-packaged-documentation-v1', 'package_revision': revision,
              'scope': 'deployment documentation; oversized historical evidence remains at the exact committed revision',
              'offline_verifier_bounds_unchanged': True,
              'full_evidence_replay_requires_matching_repository_checkout': True,
              'omitted_evidence': omitted, 'rewritten_links': rewrites,
              'rewritten_markdown': {name: {'source_sha256': hashlib.sha256(originals[name]).hexdigest(),
                                           'packaged_sha256': hashlib.sha256(data).hexdigest()}
                                     for name, data in public.items()
                                     if data is not None and name.endswith('.md') and data != originals[name]}}
    public[NOTICE] = (json.dumps(notice, indent=2, sort_keys=True) + '\n').encode('utf-8')
    if (len(public) > MAX_PUBLIC_MEMBERS or any(len(data) > MAX_FILE for data in public.values() if data is not None)
            or sum(len(data) for data in public.values() if data is not None) > MAX_PUBLIC_BYTES):
        raise ValueError('deployment documentation exceeds unchanged release verification reserve')
    return public
