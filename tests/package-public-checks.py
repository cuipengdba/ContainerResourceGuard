"""Check committed-only document closure, immutable evidence links and bounds."""
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import subprocess
import tarfile

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('package_public',root/'scripts/package_public.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
revision='a'*40;checks=[]

def snapshot(files,symlink=None):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w') as archive:
        for name,data in files.items():
            info=tarfile.TarInfo(name)
            if data is None:info.type=tarfile.DIRTYPE;archive.addfile(info)
            else:info.size=len(data);archive.addfile(info,io.BytesIO(data))
        if symlink:
            info=tarfile.TarInfo(symlink);info.type=tarfile.SYMTYPE;info.linkname='/private/file';archive.addfile(info)
    return stream.getvalue()

def check(name,condition):
    assert condition,name;checks.append(name)

files={'README.md':b'[test](tests/frozen/README.md)\n','tests/frozen/README.md':b'[helper](helper.py#entry)\n','tests/frozen/helper.py':b'print("committed")\n','tests/unreferenced-private-fixture.json':b'not selected'}
public=m.collect_public(snapshot(files),revision)
check('transitive-committed-source-and-fragment',all(public[name]==files[name] for name in files if 'unreferenced' not in name))
check('unreferenced-test-data-excluded','tests/unreferenced-private-fixture.json' not in public)
directory_files={'README.md':b'[tests](tests)\n','tests':None,'tests/README.md':b'tests\n','tests/linked.py':b'committed\n'}
check('directory-link-expands-already-present-parent','tests/linked.py' in m.collect_public(snapshot(directory_files),revision))
big=b' '*(m.MAX_FILE+1);files={'README.md':b'[result](docs/large.json#details)\n','docs/large.json':big}
public=m.collect_public(snapshot(files),revision);notice=json.loads(public[m.NOTICE]);url='https://github.com/cuipengdba/ContainerResourceGuard/blob/'+revision+'/docs/large.json'
check('oversized-evidence-external-at-exact-commit',public['README.md']==('[result]('+url+'#details)\n').encode() and 'docs/large.json' not in public)
check('original-evidence-digest-and-transformation-recorded',notice['omitted_evidence']['docs/large.json']['sha256']==hashlib.sha256(big).hexdigest() and notice['rewritten_markdown']['README.md']['source_sha256']==hashlib.sha256(files['README.md']).hexdigest())
check('deterministic-rendering',public==m.collect_public(snapshot(files),revision))
for name,data,link in [('missing-source',{'README.md':b'[missing](tests/not-committed.py)\n'},None),('parent-escape',{'README.md':b'[bad](../private)\n'},None),('backslash',{'README.md':b'[bad](tests\\private)\n'},None),('symlink',{'README.md':b'[bad](tests/link)\n'},'tests/link'),('oversized-required-script',{'scripts/required.py':big},None),('bytecode',{'README.md':b'[bad](tests/a.pyc)\n','tests/a.pyc':b'bytecode'},None)]:
    try:m.collect_public(snapshot(data,link),revision)
    except ValueError:check('reject-'+name,True)
    else:raise AssertionError(name)
# Exercise the actual committed docs, including all prior evidence references.
current=subprocess.check_output(['git','archive','--format=tar','HEAD'],cwd=root)
public=m.collect_public(current,subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip())
check('current-committed-document-closure-and-bounds',sum(len(v) for v in public.values() if v is not None)<=m.MAX_PUBLIC_BYTES and len(public)<=m.MAX_PUBLIC_MEMBERS)
print(json.dumps({'checks':checks,'count':len(checks),'actual_committed_public_members':len(public),'actual_committed_public_bytes':sum(len(v) for v in public.values() if v is not None)}))
