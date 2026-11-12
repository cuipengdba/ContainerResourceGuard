from pathlib import Path
import datetime,hashlib,json,os,resource,signal,subprocess,time,traceback

w=Path(__file__).parent;sha=lambda raw:hashlib.sha256(raw).hexdigest()
f=json.loads((w/'manifest.json').read_text());report={'schema':'crg-compact-report-output-qualification-v1','phase':'running','checks':[],'source_sha256':f['source_sha256'],'product_or_BPF_execution':False}
def identity(pid):
 fields=Path('/proc',str(pid),'stat').read_bytes().rsplit(b')',1)[1].split()
 return {'pid':pid,'start_ticks':int(fields[19]),'parent_pid':int(fields[1])}
(w/'worker.json').write_text(json.dumps(identity(os.getpid())))
def check(name,passed,**extra):
 report['checks'].append({'name':name,'passed':bool(passed),**extra})
 if not passed:raise AssertionError(name)
def invoke(args,label,preexec=None):
 p=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'CRG_DIRECT_BPF':''},preexec_fn=preexec)
 row={'identity':identity(p.pid),'entry':args[0]};report.setdefault('children',{})[label]=row
 out,err=p.communicate(timeout=45);row.update(exit=p.returncode,stdout=out.decode(),stderr=err.decode())
 return row
try:
 for name,want in f['source_sha256'].items():assert sha((w/name).read_bytes())==want
 check('all-frozen-source-and-ELF-hashes-match',True)
 unit=invoke([str(w/'pairing.test'),'-test.v','-test.run','TestReport'],'go-unit')
 report['unit']=unit
 check('Linux-unit-compact-exact-bound-overflow-and-all-output-failures',unit['exit']==0 and not unit['stderr'] and unit['stdout'].endswith('PASS\n') and all(name in unit['stdout'] for name in ['TestReportCompactEncodingRetainsEveryFieldAndRecord','TestReportExact32MiBBoundAndOneByteOverflow','TestReportAllOutputFailuresAreExplicitAndCloseKeepsFirstError']))
 for label in ['cli-rejection','cli-file-size-failure']:
  output=w/(label+'.json')
  def small_file_limit():
   signal.signal(signal.SIGXFSZ,signal.SIG_IGN);resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
  row=invoke([str(w/'direct-bpf'),'--plan',str(w/'not-a-plan.json'),'--output',str(output),'--execute'],label,small_file_limit if label.endswith('failure') else None)
  lines=[json.loads(line) for line in row['stdout'].splitlines()];terminal=lines[-1];raw=output.read_bytes();report.setdefault('output_files',{})[label]={'path':str(output),'sha256':sha(raw),'bytes':len(raw),'terminal':terminal}
  if label=='cli-rejection':
   r=json.loads(raw)
   check('actual-CLI-rejection-writes-complete-compact-report-before-finished',row['exit']==1 and not row['stderr'] and r['phase']=='rejected' and r['reason']=='EXPLICIT_LAB_MARKER' and not r.get('program_ids') and not r.get('map_ids') and terminal['phase']=='finished' and terminal['complete_report_written'] and terminal['intended_report_bytes']==len(raw) and terminal['report_limit_bytes']==33554432 and len(raw.splitlines())==1)
  else:
   check('actual-CLI-write-failure-is-nonzero-and-explicit-not-finished',row['exit']==1 and not row['stderr'] and len(raw)==0 and terminal['phase']=='failed' and terminal['reason']=='REPORT_WRITE' and terminal['complete_report_written'] is False)
 for row in report['children'].values():
  p=Path('/proc',str(row['identity']['pid']))
  assert not p.exists() or int((p/'stat').read_bytes().rsplit(b')',1)[1].split()[19])!=row['identity']['start_ticks']
 check('all-three-executed-children-reaped-and-no-BPF-load-attempt',len(report['children'])==3)
 report['phase']='passed'
except BaseException as exc:report.update(phase='failed',error_class=type(exc).__name__,error=str(exc),traceback=traceback.format_exc())
finally:
 report['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();(w/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');(w/'exit.json').write_text(json.dumps({'exit':0 if report['phase']=='passed' else 1}));print(json.dumps({'phase':report['phase'],'checks':len(report['checks']),'error':report.get('error')}))
