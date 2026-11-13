from pathlib import Path
import copy,hashlib,importlib.util,io,json,sys,tempfile

path=Path(sys.argv[1]);spec=importlib.util.spec_from_file_location('artifacts820',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);cases=[]
class Remote:
 def __init__(self,values):self.values=values
 def open(self,path,mode):assert mode=='rb' and path.startswith(m.ROOT+'/');return io.BytesIO(self.values[path[len(m.ROOT)+1:]])
data=(b'bounded-original-event-integers\n'*700000) # >16MiB, transferred in bounded chunks.
name='dbs-full600-bpf.json';index={'schema':'crg-full-pressure-artifact-index-v1','root':m.ROOT,'artifacts':[{'filename':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}],'total_bytes':len(data),'complete':True}
scratch=Path(tempfile.gettempdir()).resolve()
with tempfile.TemporaryDirectory(prefix='crg-artifact820-unit-') as directory:
 root=Path(directory);assert root.resolve().parent==scratch and root.name.startswith('crg-artifact820-unit-')
 for variant in ['exact-large','truncated','trailing','tampered','path-traversal','absolute-path','duplicate','wrong-root','invalid-hash','incomplete-index','too-many','total-overflow']:
  current=copy.deepcopy(index);content=data
  if variant=='truncated':content=data[:-1]
  elif variant=='trailing':content=data+b'x'
  elif variant=='tampered':content=b'x'+data[1:]
  elif variant=='path-traversal':current['artifacts'][0]['filename']='../outside.json'
  elif variant=='absolute-path':current['artifacts'][0]['filename']='C:/outside.json'
  elif variant=='duplicate':current['artifacts']*=2;current['total_bytes']*=2
  elif variant=='wrong-root':current['root']='/another/container'
  elif variant=='invalid-hash':current['artifacts'][0]['sha256']='unknown'
  elif variant=='incomplete-index':current['complete']=False
  elif variant=='too-many':current['artifacts']=[dict(index['artifacts'][0],filename='artifact%d.json'%i,bytes=0) for i in range(65)];current['total_bytes']=0
  elif variant=='total-overflow':current['artifacts']=[dict(index['artifacts'][0],filename='artifact%d.json'%i,bytes=m.MAX_FILE) for i in range(9)];current['total_bytes']=9*m.MAX_FILE
  target=root/variant;caught=None
  try:result=m.download_verified(Remote({name:content}),current,target)
  except m.Rejected as exc:caught=exc
  if variant=='exact-large':
   assert caught is None and result['original_bytes_preserved'] and result['total_bytes']==len(data)>16*1024*1024 and (target/name).read_bytes()==data
  else:
   assert caught is not None and not (target/name).exists()
   if variant in ['truncated','trailing','tampered']:assert (target/(name+'.part')).exists()
  cases.append({'variant':variant,'accepted':caught is None,'failure_class':None if caught is None else str(caught)})
result={'schema':'crg-bounded-artifact-transfer-unit-v1','phase':'passed','source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'large_exact_bytes':len(data),'chunk_bytes':m.CHUNK,'maximum_file_bytes':m.MAX_FILE,'maximum_total_bytes':m.MAX_TOTAL,'cases':cases,'synthetic_only_not_full_vendor_pressure':True}
print(json.dumps(result))
