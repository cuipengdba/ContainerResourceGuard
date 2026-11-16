from pathlib import Path
import datetime,hashlib,json,shutil,stat
w=Path('/var/tmp/crg-retired-pg-archive1889-20261116');raw=(w/'report.json').read_bytes();v=json.loads(raw);launch=json.loads((w/'launch.json').read_bytes());assert v['phase']=='passed-lossless-archive-only' and v['candidate_files']==len(v['files']) and all(r['original_removed'] and r['exact_decompressed_content_verified'] for r in v['files']);assert hashlib.sha256((w/'job.py').read_bytes()).hexdigest()==launch['source_sha256']=='0730f26b095c5e4a1c14ef2d18d561272298d82ffc311290b64f539194955560'
try:
 fields=Path('/proc',str(launch['pid']),'stat').read_bytes().rsplit(b')',1)[1].split();assert int(fields[19])!=launch['start_ticks'] or fields[0]==b'Z'
except (FileNotFoundError,ProcessLookupError):pass
assert stat.S_IMODE(w.stat().st_mode)==0o700
for r in v['files']:
 p=w/r['archive'];assert p.resolve()==p and w in p.parents and not Path(r['original']).exists() and p.stat().st_size==r['gzip_bytes'] and stat.S_IMODE(p.stat().st_mode)==0o600 and hashlib.sha256(p.read_bytes()).hexdigest()==r['gzip_sha256']
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in v['retained_report_sha256'].items())
out={k:x for k,x in v.items() if k!='files'};out.update(read_only=True,observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),report_sha256=hashlib.sha256(raw).hexdigest(),files_verified=len(v['files']),all_gzip_hashes_and_original_absence_independently_verified=True,all_file_contents_previously_fully_decompressed_verified=True,archive_private_0700_files0600=True,archiver_original_absent=True,current_free_bytes=shutil.disk_usage('/var/tmp').free,total_gzip_bytes=sum(r['gzip_bytes'] for r in v['files']),original_report_states_preserved={'realpaths64':'passed','high557':'failed'},stable_release_accepted=False)
print(json.dumps(out))
