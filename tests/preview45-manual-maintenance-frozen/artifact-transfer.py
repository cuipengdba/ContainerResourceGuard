"""Bounded exact-byte artifact export for the single full-pressure fixture."""
from pathlib import Path,PurePosixPath
import hashlib,json,os,re,stat

ROOT='/var/tmp/crg-public1261-results-20261114/export'
MAX_FILE=32*1024*1024
MAX_TOTAL=256*1024*1024
MAX_FILES=64
CHUNK=1024*1024
ANNOTATION_FILES=('dbs-transport-annotations.jsonl','hisdbs-transport-annotations.jsonl')
ANNOTATION_MAX_FILE=1024*1024

def file_limit(name):return ANNOTATION_MAX_FILE if name in ANNOTATION_FILES else MAX_FILE

class Rejected(Exception):pass
def require(ok,reason):
    if not ok:raise Rejected(reason)
def filename_ok(name):
    return isinstance(name,str) and bool(re.fullmatch(r'[A-Za-z0-9_.-]+\.(?:json|log)',name) or re.fullmatch(r'(?:dbs|hisdbs)-engine/business-backup\.json',name) or name in ANNOTATION_FILES) and '..' not in PurePosixPath(name).parts
def validate_index(value):
    require(value['schema']=='crg-full-pressure-artifact-index-v1' and value['root']==ROOT,'FIXED_ARTIFACT_ROOT')
    rows=value['artifacts'];require(type(rows) is list and 0<len(rows)<=MAX_FILES,'ARTIFACT_COUNT')
    names=set();total=0
    for row in rows:
        name=row['filename'];require(filename_ok(name) and name not in names,'ARTIFACT_FILENAME');names.add(name)
        require(type(row['bytes']) is int and 0<=row['bytes']<=file_limit(name),'ARTIFACT_SIZE')
        require(isinstance(row['sha256'],str) and re.fullmatch(r'[0-9a-f]{64}',row['sha256']) is not None,'ARTIFACT_SHA256')
        total+=row['bytes'];require(total<=MAX_TOTAL,'ARTIFACT_TOTAL')
    require(value['total_bytes']==total and value['complete'] is True,'INCOMPLETE_ARTIFACT_INDEX')
    return rows
def index_directory(job_sha256,plan_sha256):
    root=Path(ROOT);require(root.is_dir() and not root.is_symlink(),'OWN_ARTIFACT_DIRECTORY')
    paths=sorted([*root.glob('*.json'),*root.glob('*.log'),*(root/name for name in ANNOTATION_FILES if (root/name).exists() or (root/name).is_symlink()),*(root/name/'business-backup.json' for name in ['dbs-engine','hisdbs-engine'] if (root/name/'business-backup.json').exists())])
    rows=[]
    for path in paths:
        relative=path.relative_to(root).as_posix();require(filename_ok(relative),'ARTIFACT_FILENAME')
        before=path.lstat();require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=file_limit(relative),'ARTIFACT_SHAPE')
        fd=os.open(str(path),os.O_RDONLY|getattr(os,'O_NOFOLLOW',0));digest=hashlib.sha256();size=0
        with os.fdopen(fd,'rb') as stream:
            opened=os.fstat(stream.fileno());require((opened.st_dev,opened.st_ino)==(before.st_dev,before.st_ino),'ARTIFACT_OPEN_IDENTITY')
            while True:
                block=stream.read(min(CHUNK,file_limit(relative)+1-size))
                if not block:break
                size+=len(block);require(size<=file_limit(relative),'ARTIFACT_READ_BOUND');digest.update(block)
        after=path.lstat();require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) and size==before.st_size,'ARTIFACT_CHANGED')
        rows.append({'filename':relative,'bytes':size,'sha256':digest.hexdigest()})
    result={'schema':'crg-full-pressure-artifact-index-v1','root':ROOT,'job_sha256':job_sha256,'plan_sha256':plan_sha256,'artifacts':rows,'total_bytes':sum(v['bytes'] for v in rows),'complete':True}
    validate_index(result);return result
def download_verified(sftp,index,destination):
    rows=validate_index(index);destination=Path(destination)
    require(not destination.exists() and not destination.is_symlink(),'FRESH_DOWNLOAD_DIRECTORY')
    destination.mkdir(mode=0o700);base=destination.resolve();receipts=[]
    for row in rows:
        relative=PurePosixPath(row['filename']);final=destination.joinpath(*relative.parts)
        final.parent.mkdir(parents=True,exist_ok=True);require(final.parent.resolve().is_relative_to(base),'LOCAL_ARTIFACT_PARENT')
        partial=final.with_name(final.name+'.part');require(not final.exists() and not final.is_symlink(),'FRESH_LOCAL_ARTIFACT')
        digest=hashlib.sha256();total=0
        with sftp.open(ROOT+'/'+row['filename'],'rb') as remote,partial.open('xb') as local:
            os.chmod(partial,0o600)
            while total<row['bytes']:
                maximum=min(CHUNK,row['bytes']-total);block=remote.read(maximum)
                require(isinstance(block,bytes) and 0<len(block)<=maximum,'ARTIFACT_TRUNCATED_OR_OVERSIZED_READ')
                total+=len(block);digest.update(block);local.write(block)
            require(remote.read(1)==b'','ARTIFACT_TRAILING_BYTES')
            require(total==row['bytes'] and digest.hexdigest()==row['sha256'],'ARTIFACT_HASH_MISMATCH')
            local.flush();os.fsync(local.fileno())
        require(not final.exists() and not final.is_symlink() and final.parent.resolve().is_relative_to(base),'FRESH_LOCAL_ARTIFACT')
        partial.replace(final);receipts.append(dict(row,download_sha256=digest.hexdigest(),download_bytes=total))
    return {'schema':'crg-full-pressure-exact-download-v1','phase':'passed','files':receipts,'total_bytes':sum(v['download_bytes'] for v in receipts),'original_bytes_preserved':True}
