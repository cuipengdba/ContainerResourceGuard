from pathlib import Path
import datetime,hashlib,json,shutil
w=Path('/var/tmp/crg-retired-pg-archive1889-20261116');launch=json.loads((w/'launch.json').read_bytes());out={'read_only':True,'node_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'launch':launch,'free_bytes':shutil.disk_usage('/var/tmp').free}
try:
 fields=Path('/proc',str(launch['pid']),'stat').read_bytes().rsplit(b')',1)[1].split();out['original_alive']=int(fields[19])==launch['start_ticks'] and fields[0]!=b'Z'
except (FileNotFoundError,ProcessLookupError):out['original_alive']=False
if (w/'report.json').exists():
 v=json.loads((w/'report.json').read_bytes());out.update({k:r for k,r in v.items() if k!='files'});out['files_recorded']=len(v['files']);out['files_removed']=sum(r['original_removed'] for r in v['files']);out['original_bytes_archived']=sum(r['bytes'] for r in v['files'] if r['original_removed']);out['gzip_bytes']=sum(r['gzip_bytes'] for r in v['files']);out['all_content_verified']=all(r['exact_decompressed_content_verified'] for r in v['files']);out['report_sha256']=hashlib.sha256((w/'report.json').read_bytes()).hexdigest()
if not out['original_alive']:out['log_tail']=(w/'job.log').read_text()[-4096:]
print(json.dumps(out))
