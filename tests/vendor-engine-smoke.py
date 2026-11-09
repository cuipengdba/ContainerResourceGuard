import argparse,json,pathlib,subprocess,time,traceback,shlex,threading,re,sys
parser=argparse.ArgumentParser(description="Engine smoke in disposable original-vendor Pods; never use a business namespace")
parser.add_argument("--namespace",required=True)
parser.add_argument("--work-dir",required=True)
parser.add_argument("--run-id",default=time.strftime("%Y%m%d%H%M%S",time.gmtime()))
args=parser.parse_args()
if not re.fullmatch(r"[0-9]{8,14}",args.run_id):parser.error("run-id must contain 8..14 digits")
if not args.namespace.startswith("crg-vendor-lab-"):parser.error("only disposable crg-vendor-lab-* namespaces are accepted")
p=pathlib.Path(args.work_dir);ns=args.namespace
p.mkdir(mode=0o700,parents=True,exist_ok=True)
report={'phase':'running','started':time.time(),'roles':{},'scope':'isolated original vendor primary plus engine backup/streaming/independent restore; does not verify undocumented vendor backup/sync APIs','criteria':{'rows':16384,'payload_bytes_per_row':4096,'phase_deadline_seconds':300,'api_max_seconds':5,'sql_max_seconds':5,'expected_api_result':'000','stream_catchup_seconds':60}}
bin='/opt/postgresql/pgsql/bin/';schema='crg_acceptance_'+args.run_id;reportfile=p/'business-backup.json'
def save():reportfile.write_text(json.dumps(report,indent=2))
def ex(role,cmd,timeout=300,check=True,log=None):
    r=subprocess.run(['kubectl','exec','-n',ns,role+'-business','-c',role,'--','su','-','postgres','-c',cmd],capture_output=True,text=True,timeout=timeout)
    if log:(p/(role+'-business')/log).write_text(r.stdout+r.stderr)
    if check and r.returncode:raise RuntimeError('command failed exit=%s log=%s detail=%s'%(r.returncode,log,(r.stderr+r.stdout)[-1000:]))
    return r
def sql(role,q,port=5432):
    cmd=bin+'psql -XAtw -h 127.0.0.1 -p '+str(port)+' -U postgres -d postgres -v ON_ERROR_STOP=1 -c '+shlex.quote(q)
    return ex(role,cmd,timeout=300).stdout.strip().splitlines()[-1]
def check(item,name,condition,detail=None):
    item['checks'].append({'name':name,'passed':bool(condition),'detail':detail});save()
    if not condition:raise RuntimeError(name+' failed')
def summary(role,port=5432):return sql(role,"SELECT count(*),sum(id),sum(octet_length(payload)),md5(string_agg(md5(payload),'' ORDER BY id)) FROM "+schema+'.fixture;',port)
save()
try:
  for role in ['dbs','hisdbs']:
    meta=json.loads(subprocess.check_output(['kubectl','get','pod','-n',ns,role+'-business','-o','json'],text=True,timeout=30))
    if meta['metadata'].get('labels',{}).get('managed-by')!='crg-vendor-test' or meta['spec'].get('hostNetwork') or meta['spec'].get('hostPID'):
      raise RuntimeError('refusing Pod without disposable fixture label or with host namespaces')
    (p/(role+'-business')).mkdir(mode=0o700,exist_ok=True)
    item={'checks':[],'phase':'preparing','probes':[]};report['roles'][role]=item
    item['primary_start_time_before']=sql(role,'SELECT pg_postmaster_start_time();');save()
    root='/opt/postgresql/basebackup/crg-acceptance-'+args.run_id;base=root+'/snapshot';standby=root+'/standby';restore=root+'/restore'
    ex(role,'test ! -e '+shlex.quote(root)+' && mkdir -m 700 '+shlex.quote(root),log='backup-root.txt')
    stop=threading.Event()
    def probe():
      while not stop.is_set():
        sample={'time':time.time()}
        for k,command in [('api',"python -c \"import urllib2,json; r=urllib2.urlopen(urllib2.Request('http://127.0.0.1:8090/test',data='{}',headers={'Content-Type':'application/json'}),timeout=5); assert r.getcode()==200; assert json.loads(r.read(1024))['Result']=='000'\""),('sql',bin+"psql -XAtw -h127.0.0.1 -p5432 -U postgres -d postgres -c 'SELECT 1' -v ON_ERROR_STOP=1")]:
          t=time.monotonic()
          try:r=ex(role,command,timeout=10,check=False);sample[k+'_ok']=r.returncode==0
          except Exception:sample[k+'_ok']=False
          sample[k+'_seconds']=time.monotonic()-t
        item['probes'].append(sample);stop.wait(1)
    monitor=threading.Thread(target=probe,daemon=True);monitor.start()
    try:
      t=time.monotonic()
      q='CREATE SCHEMA '+schema+'; CREATE TABLE '+schema+'.fixture(id bigint PRIMARY KEY,payload text NOT NULL); ALTER TABLE '+schema+'.fixture ALTER COLUMN payload SET STORAGE EXTERNAL; INSERT INTO '+schema+".fixture SELECT g,repeat(md5(g::text),128) FROM generate_series(1,16384) g; CHECKPOINT;"
      sql(role,q);item['load_seconds']=time.monotonic()-t;item['primary_before']=summary(role)
      check(item,'fixture_initial_rows',item['primary_before'].startswith('16384|'),item['primary_before'])
      t=time.monotonic();ex(role,bin+'pg_dump -w -h127.0.0.1 -p5432 -U postgres -Fc --schema='+schema+' -f '+root+'/logical.dump postgres',log='logical-backup.txt');item['logical_backup_seconds']=time.monotonic()-t
      t=time.monotonic();ex(role,bin+'pg_basebackup -w -h127.0.0.1 -p5432 -U postgres -D '+base+' -R -X stream --checkpoint=fast',log='physical-backup.txt');item['physical_backup_seconds']=time.monotonic()-t
      check(item,'physical_backup_finished',True)
      ex(role,'cp -a --reflink=auto '+base+' '+standby+' && cp -a --reflink=auto '+base+' '+restore+' && rm -- '+restore+'/standby.signal',log='backup-copies.txt')
      opts='-p 55432 -h 127.0.0.1 -k /tmp -c shared_buffers=128MB'
      ex(role,bin+'pg_ctl -D '+standby+' -o '+shlex.quote(opts)+' -l '+root+'/standby.log -w -t 60 start',log='standby-start.txt',timeout=90)
      item['phase']='streaming';save()
      sql(role,'INSERT INTO '+schema+".fixture SELECT g,repeat(md5(g::text),128) FROM generate_series(16385,18432) g;")
      expected=summary(role);item['primary_after']=expected;deadline=time.monotonic()+60;matched=False
      while time.monotonic()<deadline:
        if summary(role,55432)==expected:matched=True;break
        time.sleep(1)
      check(item,'streaming_new_rows_and_checksum',matched,expected)
      check(item,'standby_in_recovery',sql(role,'SELECT pg_is_in_recovery();',55432)=='t')
      opts='-p 55433 -h 127.0.0.1 -k /tmp -c shared_buffers=128MB'
      ex(role,bin+'pg_ctl -D '+restore+' -o '+shlex.quote(opts)+' -l '+root+'/restore.log -w -t 60 start',log='restore-start.txt',timeout=90)
      check(item,'independent_restore_initial_checksum',summary(role,55433)==item['primary_before'])
      check(item,'independent_restore_is_writable',sql(role,'SELECT pg_is_in_recovery();',55433)=='f')
      sql(role,'INSERT INTO '+schema+".fixture VALUES(999999,repeat('r',4096));",55433)
      check(item,'independent_restore_does_not_modify_primary',summary(role)==expected)
      sql(role,'CREATE DATABASE crg_acceptance_restore_'+args.run_id+';')
      ex(role,bin+'pg_restore -w -h127.0.0.1 -p5432 -U postgres -d crg_acceptance_restore_'+args.run_id+' --exit-on-error '+root+'/logical.dump',log='logical-restore.txt')
      r=ex(role,bin+'psql -XAtw -h127.0.0.1 -p5432 -U postgres -d crg_acceptance_restore_'+args.run_id+' -v ON_ERROR_STOP=1 -c '+shlex.quote('SELECT count(*) FROM '+schema+'.fixture;'))
      check(item,'logical_restore_initial_rows',r.stdout.strip().splitlines()[-1]=='16384')
      for directory in [standby,restore]:ex(role,bin+'pg_ctl -D '+directory+' -m fast -w -t 30 stop',log='stop-'+directory.rsplit('/',1)[-1]+'.txt',timeout=45)
      item['phase']='checked'
    finally:
      # Stop only the two temporary data directories created by this run. Keep
      # failed snapshots/logs for diagnosis; never stop the original primary.
      for directory in [standby,restore]:
        try:
          cleanup=ex(role,'if test -s '+directory+'/postmaster.pid; then '+bin+'pg_ctl -D '+directory+' -m fast -w -t 30 stop; fi',timeout=45,check=False)
          if cleanup.returncode:item.setdefault('cleanup_errors',[]).append({'temporary_engine':directory.rsplit('/',1)[-1],'kind':'nonzero-exit'})
        except Exception as error:
          # Retain the original phase failure; still attempt the other temporary
          # engine and stop the monitor. No implicit quota relaxation here.
          item.setdefault('cleanup_errors',[]).append({'temporary_engine':directory.rsplit('/',1)[-1],'kind':type(error).__name__})
      stop.set();monitor.join(timeout=25)
      item['probe_monitor_stopped']=not monitor.is_alive()
    item['primary_start_time_after']=sql(role,'SELECT pg_postmaster_start_time();')
    check(item,'primary_did_not_restart',item['primary_start_time_before']==item['primary_start_time_after'])
    check(item,'business_probes_during_backup_sync_restore',len(item['probes'])>=1 and all(x['api_ok'] and x['sql_ok'] and x['api_seconds']<=5 and x['sql_seconds']<=5 for x in item['probes']),{'samples':len(item['probes']),'api_max':max(x['api_seconds'] for x in item['probes']),'sql_max':max(x['sql_seconds'] for x in item['probes'])})
    ex(role,'test ! -f '+standby+'/postmaster.pid && test ! -f '+restore+'/postmaster.pid && rm -rf -- '+standby+' '+restore,log='temporary-servers-cleanup.txt')
    item['temporary_servers_stopped_and_copies_removed']=True;save()
  report['phase']='passed'
except Exception as e:
  report['phase']='failed';report['error']=str(e);report['traceback']=traceback.format_exc()
report['ended']=time.time();save();print(json.dumps({'phase':report['phase'],'roles':{k:{'phase':v['phase'],'checks':len(v['checks'])} for k,v in report['roles'].items()}}))
sys.exit(0 if report['phase']=='passed' else 1)
