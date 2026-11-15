"""Read-only diagnostic qualification in this run's original-path vendor fixture."""
from pathlib import Path
import hashlib,json,os,stat,time

MEMORY_FIELDS=['anon','file','kernel','kernel_stack','pagetables','sec_pagetables','percpu','sock','vmalloc','shmem','file_mapped','file_dirty','file_writeback','anon_thp','file_thp','shmem_thp','inactive_anon','active_anon','inactive_file','active_file','slab_reclaimable','slab_unreclaimable','slab','hugetlb']
EVENT_FIELDS=['low','high','max','oom','oom_kill','oom_group_kill','sock_throttled']
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def qualify(ex,folder,group,item,plan):
 started=time.time();rows=[]
 def check(name,value):
  rows.append({'name':name,'passed':bool(value)});assert value,name
 def controls():return {name:(group/name).read_text().strip() for name in item['initial_controls']}
 def kernel_sample():
  result={}
  for name in ['memory.current','memory.swap.current','memory.stat','memory.events','memory.pressure']:
   p=group/name;result[name]={'available':True,'exact_utf8':p.read_text()} if p.exists() else {'available':False}
  return result
 def pg_start():return ex('su','-','postgres','-c',"/opt/postgresql/pgsql/bin/psql -XAtw -h127.0.0.1 -p5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c 'SELECT pg_postmaster_start_time();'").stdout.strip().splitlines()[-1]
 def identities():
  return {str(pid):int((Path('/proc')/str(pid)/'stat').read_bytes().rsplit(b')',1)[1].split()[19]) for pid in [item['fixture_identity']['init_pid'],*[x['pid'] for x in item['fixture_identity']['processes'] if x['executable'] in ['/opt/crg/crg','/opt/ccg/bin/containercacheguard']]]}
 before_controls=controls();before_ids=identities();before_pg=pg_start();before_journal=sha((folder/'resource-state/journal.json').read_bytes());before=kernel_sample()
 command=['env','CRG_DIAGNOSTIC_PRIVATE_SENTINEL=not-a-real-password','/opt/crg/crg','diagnose','--config','/etc/crg/config.json']
 stdout=ex(*command).stdout;raw=stdout.encode();bundle=json.loads(raw);after=kernel_sample()
 allowed={'schema','created_utc','included','os','arch','status_available','snapshot_age_seconds','writer_lock_held','state','mode','resource_mode','percent','percentages','host_cpus','host_memory_bytes','controls','omitted_controls','memory'}
 check('runtime-strict-root-allowlist-and-size',set(bundle)<=allowed and bundle['schema']=='crg-diagnostics-v1' and 0<len(raw)<=65536 and bundle['included']==['platform','verified_host_totals','bounded_controller_results','live_memory_counters'])
 check('runtime-no-config-path-identity-journal-env-or-private-marker',not any(v in raw for v in [b'CRG_DIAGNOSTIC_PRIVATE_SENTINEL',b'not-a-real-password',b'/etc/crg',b'/opt/postgresql',str(group).encode(),item['fixture_identity']['container_id'].encode(),item['fixture_identity']['pod_uid'].encode(),b'accepted_hash',b'original_value',b'cmdline',b'password']))
 check('runtime-current-own-status-and-verified-basis',bundle['os']=='linux' and bundle['arch']=='amd64' and bundle['status_available'] and bundle['writer_lock_held'] and bundle['state']=='managed' and bundle['mode']=='enforce' and bundle['resource_mode']=='manual' and bundle['host_cpus']==24 and bundle['host_memory_bytes']==66673278976)
 controls_out=bundle['controls'];check('runtime-bounded-three-controller-results',len(controls_out)==3 and {x['file'] for x in controls_out}=={'cpu.max','memory.high','io.max'} and all(set(x)<={'file','device','value','state'} and len(x.get('value',''))<=256 and x['state']=='read' for x in controls_out))
 m=bundle['memory'];check('runtime-memory-schema-no-overlapping-sum',set(m)<={'sampled_utc','current_bytes','swap_current_bytes','stat_bytes','events','pressure','unavailable'} and set(m['stat_bytes'])<=set(MEMORY_FIELDS) and set(m['events'])<=set(EVENT_FIELDS) and all(type(x) is int and x>=0 for x in [*m['stat_bytes'].values(),*m['events'].values()]))
 missing=[];stable_numeric={}
 for filename,key in [('memory.current','current_bytes'),('memory.swap.current','swap_current_bytes')]:
  if before[filename]['available']:
   check('runtime-'+filename+'-available-value',type(m[key]) is int and m[key]>=0)
  else:missing.append(filename);check('runtime-'+filename+'-missing-is-null',m[key] is None)
 for filename,key,fields in [('memory.stat','stat_bytes',MEMORY_FIELDS),('memory.events','events',EVENT_FIELDS)]:
  if before[filename]['available']:
   a={k:int(v) for k,v in (x.split() for x in before[filename]['exact_utf8'].splitlines()) if k in fields};z={k:int(v) for k,v in (x.split() for x in after[filename]['exact_utf8'].splitlines()) if k in fields};check('runtime-'+filename+'-available-key-coverage',set(m[key])==set(a)==set(z))
   if key=='events':check('runtime-events-monotonic-bracket',all(a[k]<=v<=z[k] for k,v in m[key].items()))
   stable_numeric[key]={k:{'both_endpoint_values':v,'sample_value':m[key][k],'sample_matches_endpoints':m[key][k]==v} for k,v in a.items() if z[k]==v}
  else:missing.append(filename);check('runtime-'+filename+'-missing-is-empty',m[key]=={})
 for name in ['anon','file','kernel','hugetlb']:
  if name not in m['stat_bytes']:missing.append('memory.stat.'+name)
 if before['memory.pressure']['available']:
  pressures={x.split()[0] for x in before['memory.pressure']['exact_utf8'].splitlines() if x.split()[0] in ['some','full']};check('runtime-pressure-available-keys',set(m['pressure'])==pressures)
  for v in m['pressure'].values():check('runtime-pressure-units-and-values',set(v)=={'avg10_percent','avg60_percent','avg300_percent','total_microseconds'} and all(0<=v[k]<=100 for k in ['avg10_percent','avg60_percent','avg300_percent']) and type(v['total_microseconds']) is int and v['total_microseconds']>=0)
 else:missing.append('memory.pressure');check('runtime-pressure-missing-is-empty',m['pressure']=={})
 check('runtime-exact-unavailable-not-fake-zero',set(m.get('unavailable',[]))==set(missing))
 output='/etc/crg/diagnostic1448.json';p=folder/'crg-config/diagnostic1448.json';link=folder/'crg-config/diagnostic1448-link.json';assert not p.exists() and not link.exists();ack=json.loads(ex(*command,'--output',output).stdout);written=p.read_bytes();written_bundle=json.loads(written)
 check('runtime-private-local-new-file-and-declared-contents',ack['state']=='written' and ack['bytes']==len(written) and ack['maximum_bytes']==65536 and len(written)<=65536 and stat.S_IMODE(p.stat().st_mode)==0o600 and set(written_bundle)<=allowed and written_bundle['included']==bundle['included'])
 written_hash=sha(written);again=ex(*command,'--output',output,check=False);check('runtime-existing-output-refused-not-overwritten',again.returncode!=0 and sha(p.read_bytes())==written_hash)
 link.symlink_to(p.name);linked=ex(*command,'--output','/etc/crg/'+link.name,check=False);check('runtime-symlink-output-refused-not-followed',linked.returncode!=0 and link.is_symlink() and sha(p.read_bytes())==written_hash)
 for dest in ['/tmp/containerresourceguard/status.json','/etc/crg/io-profile.json']:
  result=ex(*command,'--output',dest,check=False);check('runtime-protected-output-refused-'+Path(dest).name,result.returncode!=0)
 check('runtime-no-automatic-profile-or-resource-mutation',not (folder/'crg-config/io-profile.json').exists() and controls()==before_controls and sha((folder/'resource-state/journal.json').read_bytes())==before_journal)
 check('runtime-Agent-PID1-cache-PG-not-restarted',identities()==before_ids and pg_start()==before_pg)
 return {'phase':'passed','began_epoch':started,'ended_epoch':time.time(),'checks':rows,'stdout_exact_utf8':stdout,'stdout_sha256':sha(raw),'local_file_exact_utf8':written.decode(),'local_file_sha256':written_hash,'local_file_bytes':len(written),'local_file_mode':'0600','local_write_acknowledgement':ack,'kernel_before':before,'kernel_after':after,'stable_numeric_fields_independently_compared':stable_numeric,'actual_missing_fields':missing,'original_controls_unchanged':True,'original_journal_unchanged':True,'same_Agent_PID1_cache_PG':True,'counters_not_an_atomic_snapshot':'Stable bracket values and monotonic events are compared; changing gauges remain sampled values, no sum or atomic-read claim.'}
