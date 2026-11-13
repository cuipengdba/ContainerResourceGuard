from pathlib import Path
import copy,hashlib,importlib.util,io,json,os,sys,tempfile

source=Path(sys.argv[1]);spec=importlib.util.spec_from_file_location('annotation_export',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);cases=[];sha=lambda raw:hashlib.sha256(raw).hexdigest()
class Remote:
 def __init__(self,files):self.files=files;self.read_sizes=[]
 def open(self,path,mode):
  assert mode=='rb' and path.startswith(m.ROOT+'/');raw=self.files[path[len(m.ROOT)+1:]];parent=self
  class Stream(io.BytesIO):
   def read(self,size=-1):assert 0<size<=m.CHUNK;parent.read_sizes.append(size);return super().read(size)
  return Stream(raw)
data=b'CRG_TRANSPORT_V1 {"run_id":"202611139430","kind":"unit"}\n'
with tempfile.TemporaryDirectory(prefix='crg-annotations943-') as directory:
 root=Path(directory)
 for role in ['dbs','hisdbs']:
  name=role+'-transport-annotations.jsonl'
  for variant in ['exact','truncated','trailing','tampered','oversized']:
   index={'schema':'crg-full-pressure-artifact-index-v1','root':m.ROOT,'artifacts':[{'filename':name,'bytes':len(data),'sha256':sha(data)}],'total_bytes':len(data),'complete':True};content=data
   if variant=='truncated':content=data[:-1]
   if variant=='trailing':content=data+b'x'
   if variant=='tampered':content=b'x'+data[1:]
   if variant=='oversized':index['artifacts'][0]['bytes']=m.ANNOTATION_MAX_FILE+1;index['total_bytes']=m.ANNOTATION_MAX_FILE+1
   target=root/(role+'-'+variant);remote=Remote({name:content});error=None;result=None
   try:result=m.download_verified(remote,index,target)
   except m.Rejected as e:error=str(e)
   if variant=='exact':assert error is None and result['original_bytes_preserved'] and (target/name).read_bytes()==data
   else:assert error is not None and not (target/name).exists()
   cases.append({'variant':role+'-'+variant,'passed':True,'accepted':error is None,'error':error,'read_sizes':remote.read_sizes})
 for name in ['other-transport-annotations.jsonl','DBS-transport-annotations.jsonl','../dbs-transport-annotations.jsonl']:
  index={'schema':'crg-full-pressure-artifact-index-v1','root':m.ROOT,'artifacts':[{'filename':name,'bytes':len(data),'sha256':sha(data)}],'total_bytes':len(data),'complete':True};error=None
  try:m.validate_index(index)
  except m.Rejected as e:error=str(e)
  assert error=='ARTIFACT_FILENAME';cases.append({'variant':'exact-filename-rejection-'+name,'passed':True,'error':error})
 saved_root=m.ROOT;saved_os=m.os
 try:
  for variant in ['exact-two','symlink','hardlink','fifo','oversized','replaced-at-open']:
   own=root/('index-'+variant);own.mkdir();m.ROOT=str(own);path=own/'dbs-transport-annotations.jsonl';other=root/('outside-'+variant);other.write_bytes(data);path.write_bytes(data)
   if variant=='exact-two':(own/'hisdbs-transport-annotations.jsonl').write_bytes(data);(own/'unrelated.jsonl').write_bytes(b'not-exported')
   if variant in ['symlink','hardlink','fifo']:path.unlink()
   if variant=='symlink':path.symlink_to(other)
   if variant=='hardlink':os.link(other,path)
   if variant=='fifo':os.mkfifo(path,0o600)
   if variant=='oversized':path.write_bytes(b'x'*(m.ANNOTATION_MAX_FILE+1))
   if variant=='replaced-at-open':
    class OSProxy:
     def __getattr__(self,key):return getattr(saved_os,key)
     def open(self,name,*args,**kwargs):
      assert Path(name)==path;path.rename(own/'previous-file');path.write_bytes(data);return saved_os.open(name,*args,**kwargs)
    m.os=OSProxy()
   error=None;index=None
   try:index=m.index_directory('0'*64,'1'*64)
   except m.Rejected as e:error=str(e)
   finally:m.os=saved_os
   if variant=='exact-two':assert error is None and {v['filename'] for v in index['artifacts']}==set(m.ANNOTATION_FILES) and index['total_bytes']==len(data)*2
   else:assert error==('ARTIFACT_OPEN_IDENTITY' if variant=='replaced-at-open' else 'ARTIFACT_SHAPE')
   cases.append({'variant':'actual-index-'+variant,'passed':True,'error':error})
 finally:m.ROOT=saved_root;m.os=saved_os
assert len(cases)==19 and all(v['passed'] for v in cases)
print(json.dumps({'schema':'crg-two-exact-JSONL-export-unit-v1','phase':'passed','source_sha256':sha(source.read_bytes()),'annotation_byte_bound':m.ANNOTATION_MAX_FILE,'original_file_bound':m.MAX_FILE,'original_total_bound':m.MAX_TOTAL,'original_count_bound':m.MAX_FILES,'cases':cases,'synthetic_remote_and_actual_private_filesystem_only':True}))
