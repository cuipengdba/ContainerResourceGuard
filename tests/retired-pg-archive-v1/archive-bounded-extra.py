"""Losslessly archive only unmounted retired test PG regular files; no production paths."""
from pathlib import Path
import base64,datetime,gzip,hashlib,json,os,shutil,stat,subprocess,sys
home=Path('/var/tmp/crg-retired-pg-archive1900-20261116');assert home.resolve()==home and home.is_dir() and not home.is_symlink();os.umask(0o077)
roots=[Path('/var/tmp/crg-seven-day78-20261111')]
targets=[roots[0]/'fixture/dbs-business/postgresql']
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for b in iter(lambda:stream.read(1048576),b''):h.update(b)
 return h.hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def under(value,path):return value==str(path) or value.startswith(str(path)+'/')
def quiescent():
 p=subprocess.run(['kubectl','get','pods','-A','-o','json','--request-timeout=8s'],capture_output=True,text=True,timeout=12,check=True);assert not p.stderr
 for pod in json.loads(p.stdout)['items']:
  for volume in pod['spec'].get('volumes',[]):
   value=volume.get('hostPath',{}).get('path','')
   if value:assert not any(under(value,t) or under(str(t),Path(value)) for t in targets),(pod['metadata']['name'],value)
 for line in Path('/proc/self/mountinfo').read_text().splitlines():
  fields=line.split();assert not any(under(fields[i],t) for i in [3,4] for t in targets)
 for directory in Path('/proc').glob('[0-9]*'):
  for link in [directory/'cwd',directory/'exe',*list((directory/'fd').glob('*'))]:
   try:value=os.readlink(link)
   except OSError:continue
   assert not any(under(value,t) for t in targets),(str(link),value)
for root in roots:assert root.resolve()==root and root.is_dir() and not root.is_symlink()
for target in targets:assert target.resolve()==target and target.is_dir() and not target.is_symlink() and any(root in target.parents for root in roots)
failed=roots[0]/'campaign-acceptance/backup-2026111107818/business-backup.json';assert json.loads(failed.read_bytes())['phase']=='failed';reports={str(failed):sha(failed)}
p=subprocess.run(['kubectl','get','namespace','crg-vendor-lab-acceptance78-20261111','--ignore-not-found','-o','name','--request-timeout=8s'],capture_output=True,text=True,timeout=12,check=True);assert not p.stdout.strip() and not p.stderr
quiescent();candidates=[]
for target in targets:
 for p in target.rglob('*'):
  if sum(item.st_size for _,item in candidates)>=6*1024**3:break
  s=p.lstat()
  if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_size<8*1024**2:continue
  assert p.resolve()==p and not p.is_symlink() and s.st_dev==target.stat().st_dev;candidates.append((p,s))
assert candidates and sum(s.st_size for _,s in candidates)<=7*1024**3
out={'schema':'crg-lossless-retired-PG-archive-bounded-extra-v2','phase':'archiving','started_utc':now(),'targets':[str(p) for p in targets],'candidate_files':len(candidates),'candidate_bytes':sum(s.st_size for _,s in candidates),'before_free_bytes':shutil.disk_usage('/var/tmp').free,'retained_report_sha256':reports,'files':[],'business_started':False,'product_or_original_business_changed':False}
def save():
 p=home/'report.candidate';p.write_text(json.dumps(out,indent=2)+'\n');p.chmod(0o600);p.replace(home/'report.json')
save()
try:
 for p,s in candidates:
  dest=home/'files'/p.relative_to('/var/tmp');dest=dest.with_name(dest.name+'.gz');dest.parent.mkdir(parents=True,exist_ok=True,mode=0o700);assert not dest.exists();h=hashlib.sha256();attrs={n:base64.b64encode(os.getxattr(p,n)).decode() for n in os.listxattr(p)}
  with p.open('rb') as source,dest.open('xb') as compressed:
   with gzip.GzipFile(filename='',mode='wb',fileobj=compressed,compresslevel=1,mtime=0) as z:
    for block in iter(lambda:source.read(1048576),b''):h.update(block);z.write(block)
   compressed.flush();os.fsync(compressed.fileno())
  verify=hashlib.sha256();length=0
  with gzip.open(dest,'rb') as stream:
   for block in iter(lambda:stream.read(1048576),b''):verify.update(block);length+=len(block)
  assert h.digest()==verify.digest() and length==s.st_size
  fresh=p.stat();assert (fresh.st_dev,fresh.st_ino,fresh.st_size,fresh.st_mtime_ns,fresh.st_ctime_ns)==(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns) and p.resolve()==p
  row={'original':str(p),'archive':str(dest.relative_to(home)),'sha256':h.hexdigest(),'bytes':length,'gzip_sha256':sha(dest),'gzip_bytes':dest.stat().st_size,'uid':s.st_uid,'gid':s.st_gid,'mode':stat.S_IMODE(s.st_mode),'atime_ns':s.st_atime_ns,'mtime_ns':s.st_mtime_ns,'xattrs_base64':attrs,'exact_decompressed_content_verified':True,'original_removed':False};out['files'].append(row);save();p.unlink();row['original_removed']=True;out['last_progress_utc']=now();save()
 assert all(sha(Path(p))==h for p,h in reports.items());out.update(phase='passed-lossless-archive-only',ended_utc=now(),after_free_bytes=shutil.disk_usage('/var/tmp').free,retained_reports_unchanged=True);out['actual_free_increase_bytes']=out['after_free_bytes']-out['before_free_bytes'];save()
except BaseException as e:
 out.update(phase='failed-preserve-partial-archive',error=type(e).__name__+': '+str(e),ended_utc=now());save();raise
