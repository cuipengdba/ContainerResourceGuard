"""Supplemental test observer only; never shipped or installed as the CRG Agent."""
from pathlib import Path
import datetime,hashlib,json,os,re,shutil,subprocess,time,traceback

w=Path('/var/tmp/crg-final1728-tools-20261116');ns='crg-vendor-lab-final1728-20261116';out=w/'readonly-observation';os.umask(0o077);out.mkdir(mode=0o700)
expected_plan='ea19e85c8e8690845449ce36b9e3be8266282015cb8e8ba8ed6eec207187370c';assert hashlib.sha256((w/'plan.json').read_bytes()).hexdigest()==expected_plan
started=time.monotonic();seen={};samples=0;errors=0
def safe(value):
 value=str(value)
 if re.search(r'password|secret|token|postgresql://|env:',value,re.I):return '[withheld]'
 return re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b','[address]',value)[:2048]
def query(args):
 r=subprocess.run(args+['--request-timeout=8s'],capture_output=True,text=True,timeout=12)
 if r.returncode:
  return {'query_error':r.returncode,'diagnostic':safe(r.stderr),'namespace_not_created_or_already_removed':'NotFound' in r.stderr}
 assert not r.stderr and len(r.stdout)<=4*1024*1024;return json.loads(r.stdout)
def absent(identity):
 try:
  fields=Path('/proc',str(identity['pid']),'stat').read_bytes().rsplit(b')',1)[1].split();return fields[0]==b'Z' or int(fields[19])!=identity['start_ticks']
 except (FileNotFoundError,ProcessLookupError):return True
try:
 while True:
  sample={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-started,'disk':shutil.disk_usage('/var/tmp')._asdict()}
  try:
   nodes=query(['kubectl','get','nodes','-o','json']);sample['nodes']=[{'conditions':[{k:v[k] for k in ['type','status','lastTransitionTime','reason'] if k in v} for v in n['status']['conditions']]} for n in nodes.get('items',[])];sample['node_query_error']=nodes.get('query_error')
   pods=query(['kubectl','get','pods','-n',ns,'-o','json']);sample['pods']=[];sample['pod_query_error']=pods.get('query_error')
   for p in pods.get('items',[]):
    status=p.get('status',{});sample['pods'].append({'name':p['metadata']['name'],'UID':p['metadata']['uid'],'resourceVersion':p['metadata']['resourceVersion'],'deletionTimestamp':p['metadata'].get('deletionTimestamp'),'phase':status.get('phase'),'reason':status.get('reason'),'message':safe(status.get('message','')),'containers':[{'name':c['name'],'containerID':c.get('containerID'),'restartCount':c['restartCount'],'ready':c['ready'],'state':{k:{f:safe(v) if f=='message' else v for f,v in row.items() if f in ['exitCode','reason','message','startedAt','finishedAt','signal']} for k,row in c.get('state',{}).items()}} for c in status.get('containerStatuses',[])]})
   events=query(['kubectl','get','events','-n',ns,'-o','json']);sample['events']=[];sample['event_query_error']=events.get('query_error')
   for event in events.get('items',[]):
    uid=event['metadata']['uid'];version=event['metadata']['resourceVersion']
    if seen.get(uid)==version:continue
    seen[uid]=version;obj=event.get('involvedObject',{});sample['events'].append({'UID':uid,'resourceVersion':version,'type':event.get('type'),'reason':event.get('reason'),'message':safe(event.get('message','')),'count':event.get('count'),'firstTimestamp':event.get('firstTimestamp'),'lastTimestamp':event.get('lastTimestamp'),'eventTime':event.get('eventTime'),'object':{k:obj.get(k) for k in ['kind','name','uid']}})
   if len(seen)>10000:raise RuntimeError('event inventory bound exceeded')
  except Exception as error:errors+=1;sample['observer_error']=safe(type(error).__name__+': '+str(error))
  day=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d');daily=out/(day+'.jsonl')
  assert sum(p.stat().st_size for p in out.glob('*.jsonl'))<64*1024*1024
  with daily.open('a',encoding='utf-8') as stream:stream.write(json.dumps(sample,ensure_ascii=False)+'\n');stream.flush();os.fsync(stream.fileno())
  samples+=1
  if (w/'exit.json').exists() and (w/'launch.json').exists():
   original=json.loads((w/'launch.json').read_bytes());worker=json.loads((w/'worker.json').read_bytes()) if (w/'worker.json').exists() else None
   if absent(original) and (worker is None or absent(worker)):break
  if time.monotonic()-started>12*86400:raise RuntimeError('observer twelve-day safety deadline; no test process signaled')
  time.sleep(60)
 terminal={'phase':'captured-terminal','samples':samples,'query_errors':errors}
except BaseException as error:terminal={'phase':'observer-failed','samples':samples,'query_errors':errors,'error':safe(type(error).__name__+': '+str(error)),'traceback':safe(traceback.format_exc())}
terminal.update(ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),product_or_business_signaled=False,read_only_kubernetes_queries=True)
with (out/'exit.json').open('x') as stream:json.dump(terminal,stream,indent=2)
