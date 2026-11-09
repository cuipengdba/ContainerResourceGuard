#!/usr/bin/env python3
"""Generate deterministic package-level SBOM from the actual pinned Go build."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import uuid

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('version')
a = p.parse_args()
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', a.version):
    p.error('invalid version')
root = Path(__file__).resolve().parents[1]
pin = json.loads((root / 'scripts/toolchain.json').read_text())['version']
env = dict(os.environ, GOTOOLCHAIN='local', GOENV='off', GOWORK='off', GOPROXY='off', GOSUMDB='off', GOFLAGS='', GOEXPERIMENT='', CGO_ENABLED='0', GOOS='linux', GOAMD64='v1', GOARM64='v8.0')
def command(*args):
    return subprocess.check_output(args, cwd=root, env=env, text=True).strip()
if command('go', 'env', 'GOVERSION') != pin:
    raise SystemExit('pinned Go toolchain required')
if command('git', 'status', '--porcelain', '--untracked-files=no'):
    raise SystemExit('source must be committed before release metadata')
revision = command('git', 'rev-parse', 'HEAD')
epoch = int(command('git', 'show', '-s', '--format=%ct', revision))
stamp = datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
manifest = {'schema': 'crg-build-v1', 'version': a.version, 'source_revision': revision, 'source_date_epoch': epoch, 'go_version': pin, 'artifacts': []}
for arch in ['amd64', 'arm64']:
    env['GOARCH'] = arch
    binary = root / 'dist' / ('crg-linux-' + arch)
    info = json.loads(command('go', 'version', '-m', '-json', str(binary)))
    settings = {item['Key']: item['Value'] for item in info['Settings']}
    if info['GoVersion'] != pin or info['Main']['Path'] != 'github.com/cuipengdba/ContainerResourceGuard' or info.get('Deps') or any(settings.get(k) != v for k, v in {'GOOS': 'linux', 'GOARCH': arch, 'CGO_ENABLED': '0', '-trimpath': 'true'}.items()):
        raise SystemExit('binary metadata differs from the pinned dependency/target contract')
    # List the packages selected by the SAME target/toolchain/source, including
    # vendored standard-library packages. This is build dependency inventory,
    # not a claim that every source function survives the linker.
    deps = command('go', 'list', '-deps', '-f', '{{if .Standard}}S {{.ImportPath}}{{else}}M {{.ImportPath}}{{end}}', './cmd/crg').splitlines()
    if any(line.startswith('M ') and not line.startswith('M github.com/cuipengdba/ContainerResourceGuard/') for line in deps):
        raise SystemExit('new external dependency requires explicit SBOM/license support')
    names = sorted(set(line[2:] for line in deps if line.startswith('S ')))
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    item = {'arch': arch, 'binary_sha256': digest, 'go_build_info': info, 'standard_package_count': len(names)}
    manifest['artifacts'].append(item)
    app = {'type': 'application', 'bom-ref': 'crg', 'name': 'ContainerResourceGuard', 'version': a.version, 'hashes': [{'alg': 'SHA-256', 'content': digest}], 'licenses': [{'license': {'id': 'MIT'}}], 'properties': [{'name': 'crg:source_revision', 'value': revision}, {'name': 'crg:target', 'value': 'linux/' + arch}]}
    components = [{'type': 'library', 'bom-ref': 'stdlib:' + name, 'name': name, 'version': pin, 'scope': 'required', 'properties': [{'name': 'crg:inventory_level', 'value': 'Go standard build dependency'}]} for name in names]
    serial='urn:uuid:'+str(uuid.uuid5(uuid.NAMESPACE_URL,'https://github.com/cuipengdba/ContainerResourceGuard/SBOM/'+arch+'/'+digest))
    sbom = {'bomFormat': 'CycloneDX', 'specVersion': '1.6', 'serialNumber':serial, 'version': 1, 'metadata': {'timestamp': stamp, 'component': app, 'tools': {'components': [{'type': 'framework', 'name': 'Go toolchain', 'version': pin, 'licenses': [{'license': {'id': 'BSD-3-Clause'}}]}]}, 'properties': [{'name': 'crg:timestamp_semantics', 'value': 'source commit time, not wall-clock build time'}, {'name': 'crg:coverage', 'value': 'application and target-specific standard package build dependencies; compiler listed as tool; excludes vendor databases and programs not distributed here'}]}, 'components': components, 'dependencies': [{'ref': 'crg', 'dependsOn': [c['bom-ref'] for c in components]}]}
    (root / 'dist' / ('sbom-linux-' + arch + '.cdx.json')).write_text(json.dumps(sbom, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
(root / 'dist/build-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
print(json.dumps({'go_version': pin, 'source_revision': revision, 'architectures': ['amd64', 'arm64'], 'SBOM': 'package-level build dependencies'}))
