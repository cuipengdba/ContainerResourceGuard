"""Manual restoration of a verified private retired-test archive; never auto-run."""
from pathlib import Path
import base64,gzip,hashlib,json,os,stat,sys
home=Path(sys.argv[1]).resolve();assert home==Path('/var/tmp/crg-retired-pg-archive1889-20261116');v=json.loads((home/'report.json').read_bytes());assert v['phase']=='passed-lossless-archive-only';os.umask(0o077)
for r in v['files']:
 p=Path(r['original']);assert any(str(p).startswith(t+'/') for t in v['targets']) and p.parent.resolve()==p.parent and not p.is_symlink();source=home/r['archive'];assert source.resolve()==source and home in source.parents and hashlib.sha256(source.read_bytes()).hexdigest()==r['gzip_sha256']
 if p.exists():
  assert p.is_file() and p.stat().st_size==r['bytes'];h=hashlib.sha256()
  with p.open('rb') as s:
   for block in iter(lambda:s.read(1048576),b''):h.update(block)
  assert h.hexdigest()==r['sha256'];continue
 temporary=p.with_name(p.name+'.crg1889-restore');h=hashlib.sha256();length=0
 with gzip.open(source,'rb') as s,temporary.open('xb') as d:
  for block in iter(lambda:s.read(1048576),b''):h.update(block);length+=len(block);d.write(block)
  d.flush();os.fsync(d.fileno())
 assert h.hexdigest()==r['sha256'] and length==r['bytes'];os.chown(temporary,r['uid'],r['gid']);os.chmod(temporary,r['mode'])
 for name,value in r['xattrs_base64'].items():os.setxattr(temporary,name,base64.b64decode(value))
 os.utime(temporary,ns=(r['atime_ns'],r['mtime_ns']));os.link(temporary,p);temporary.unlink()
print('Exact retired payloads restored; original private gzip evidence retained.')
