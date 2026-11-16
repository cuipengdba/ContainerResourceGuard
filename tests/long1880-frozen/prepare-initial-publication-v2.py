from pathlib import Path
import hashlib,importlib.util,json,subprocess
T=Path(__file__).parent;B=T.parent;sha=lambda b:hashlib.sha256(b).hexdigest();enc=lambda v:(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode();O=T/'crg-r344-observations'
def latest(stem,predicate):
 for p in sorted(O.glob('*-'+stem+'.json'),reverse=True):
  receipt=json.loads(p.read_bytes())
  if receipt['exit']!=0:continue
  value=json.loads(receipt['stdout'])
  if predicate(value):return p,receipt,value
 raise AssertionError('missing qualifying actual receipt '+stem)
ap,ar,a=latest('crg-r1894-verify-retired-archive97',lambda v:v['phase']=='passed-lossless-archive-only');bp,br,b=latest('crg-r1903-verify-retired-archive97',lambda v:v['phase']=='passed-lossless-archive-only');lp,lr,l=latest('crg-r1883-launch-long97',lambda v:'summary' in v);launch=l['summary'];sp,sr,o=latest('crg-r1905-observe-long97',lambda v:v['phase']=='measuring-baseline' and v.get('main_checks')==v.get('main_passed')==12 and len(v.get('independent_baseline_guards',{}))==2)
assert all(v['all_gzip_hashes_and_original_absence_independently_verified'] and v['all_file_contents_previously_fully_decompressed_verified'] and v['retained_reports_unchanged'] and v['archiver_original_absent'] for v in [a,b]);assert all(v['original_alive'] and v.get('expected_entry_matches',True) for v in o['processes'].values());assert o['campaigns']['baseline']['both_workers_started_epoch']
f=json.loads((T/'crg-r1880-long-frozen.json').read_bytes());assert launch['job_sha256']==f['job_sha256'] and launch['plan_sha256']==f['plan_sha256'] and launch['source_sha256']==f['uploaded_sha256'] and launch['node_admission']['admitted'] and launch['admission']['phase']=='ready'
S=T/'crg-r1895-prepared';S.mkdir(exist_ok=False);files={}
def keep(n,raw):
 p=S/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);files[n]=sha(raw)
archives={'schema':'crg-retired-PG-two-private-archives-independent-v1','runs':[a,b],'total_verified_files':a['files_verified']+b['files_verified'],'old_failed_reports_preserved':True,'product_or_original_business_changed':False,'raw_database_gzip_and_restore_metadata_remain_private':True,'new_long_duration_accepted':False};keep('docs/test-results-retired-pg-archive-v1.json',enc(archives))
for n,local in [('archive-bounded-extra.py','crg-r1900-retired-pg-archive-job.py'),('restore-bounded-extra.py','crg-r1902-restore-retired-pg.py'),('verify-archive-v1.py','crg-r1894-verify-retired-archive97.py'),('verify-archive-extra-v2.py','crg-r1903-verify-retired-archive97.py')]:keep('tests/retired-pg-archive-v1/'+n,(T/local).read_bytes())
snapshot={k:o[k] for k in ['node_utc','processes','phase','main_checks','main_passed','stages','roles','summary','main_report_sha256','independent_baseline_guards']};snapshot.update(schema='crg-new-long1880-initial-readonly-v1',launch_identity={k:launch[k] for k in ['pid','start_ticks','entry','job_sha256','plan_sha256','node_utc','single_launch_guard']},source_revision=f['source_revision'],all19_source_sha256=f['uploaded_sha256'],node_admission=launch['node_admission'],launch_admission=launch['admission'],fresh_formal18_accepted=True,auxiliary4_accepted=True,first_pre_guard_disk_rejection_retained=True,new_clock=True,inherited_seconds=0,long_duration_accepted=False,stable_release_accepted=False)
snapshot['campaigns']={}
for stage,c in o['campaigns'].items():
 last=c.get('last_cycle');snapshot['campaigns'][stage]={'phase':c['phase'],'cycles_recorded':c['cycles'],'both_workers_started_epoch':c['both_workers_started_epoch'],'roles':{r:{'host_samples':v['host_samples'],'terminal_workload_summary_available':v.get('workload') is not None,'campaign_reports_both_native_workers_started':c['both_workers_started_epoch'] is not None} for r,v in c['roles'].items()},'last_cycle':{k:last[k] for k in ['phase','content_phase','content_started_epoch','content_ended_epoch','native_workload_validation'] if k in last} if last else None,'whole_native_duration_and_cycles_accepted':False}
keep('docs/test-results-new-long1880-initial.json',enc(snapshot));keep('tests/long1880-frozen/prepare-initial-publication.py',Path(__file__).read_bytes());keep('tests/long1880-frozen/observe-baseline-independent.py',(T/'crg-r1905-observe-long97.py').read_bytes())
guide=(B/'ContainerResourceGuard-integration/docs/development-new-long1880.zh.md').read_text()+'''
## 实际唯一启动与初期快照

第一次准入被拒后没有创建守卫或业务。首批725个文件逐个完整解压校验、私有压缩件和旧报告独立复查完成，但实际可用空间仍低于原预留线；第二批只归档旧78已停用DBS测试PG副本的至少8MiB普通文件，选择至6GiB、总量不得超过7GiB，同样检查旧namespace/挂载/进程不引用、全部内容和私有压缩件摘要，并保留旧失败周期原件。两份私有恢复清单和[各自恢复工具](../tests/retired-pg-archive-v1/)保留，原failed不改成passed。[两批归档核验](test-results-retired-pg-archive-v1.json)记录实际文件数、源/结果摘要与权限；这些是空间回收结果，不是业务或长稳资格。

完成后重新通过原15%/20GiB节点门槛及新job全部前置，才执行同一冻结程序的唯一实际启动；不是连接异常后盲目重启。实际PID/start、原生UTC、job/plan/19输入及节点准入在[初期快照](test-results-new-long1880-initial.json)绑定。两角色各6项原启动检查共12/12，通过原启动链、缓存独立enforce、observe仅三项计划且八原控制不写、v2日志权限和准确一对一Agent/初始主进程检查；两原生工作线程已开始24h基线。快照内备份周期只记当时进度，整段原生时长/全部周期尚未完成，不能提前认定业务周期或长稳接受。

当前是新的24h observe基线运行中；之后同容器24h enforce和新七天，以及老化后原故障/恢复/维护/升级/稳定发布门槛仍全部待验收。之前各历史段落是带日期的准入/准备状态，不抹去被拒、换行校验失败或旧长测失败。源37、精确ELF、19输入与原各阶段参数/时长/检查未变。preview.5未改，稳定1.0尚未发布。
''';keep('docs/development-new-long1880.zh.md',guide.encode());spec=importlib.util.spec_from_file_location('render',B/'ContainerResourceGuard-integration/scripts/render-task-audit.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);plan={'common_files':files,'branches':{}}
for name,branch in [('ContainerResourceGuard-integration','release/integration-v1'),('ContainerResourceGuard-v10','next/compatibility-contract'),('ContainerResourceGuard-partition','next/partition-io'),('ContainerResourceGuard','main')]:
 repo=B/name;out=S/'branch-specific'/name/'docs';out.mkdir(parents=True);reg=json.loads((repo/'docs/current-task-registry.json').read_bytes());audit=json.loads((repo/'docs/current-52-task-audit.json').read_bytes());status=dict(reg['new_long1880'],phase='running-baseline-not-duration-accepted',actual_launch_guard_created=True,lossless_retired_archive='two-completed-independently-verified',launch_utc=launch['node_utc'],last_snapshot_utc=o['node_utc'],initial_original_startup_checks=12,initial_startup_passed=12,first_pre_guard_rejection_preserved=True);reg['new_long1880']=status;audit['new_long1880']=status
 reg['latest_requirements']+=' New1880 zero-clock long has sole actual start after unchanged15percent-disk guard and verified reversible retired-PG archival; baseline24h active/initial startup12 passed only, then same-container24h/new7d and original post-aging/release gates remain. No elapsed-time acceptance.'
 for task in reg['tasks']:
  if task['id'] not in ['P02.1','P02.2','P06.3','P10.2','P10.3']:continue
  aa=dict(task['before_new_long1880']);aa['verified_scope']+=' 新候选19输入/从零24h-24h-7d冻结，原磁盘预留拒绝与可逆归档完整保留；再次准入通过后的唯一实际启动，初期原启动12/12及两原生工作线程运行。';aa['remaining_or_boundary']+=' 基线24h进行中，不授予原时长/周期资格；同容器24h/新七天及原老化后/稳定门槛全部保留。';aa['evidence']='development-new-long1880.zh.md';task['current_acceptance']=aa;task['new_long1880']=status;row=next(v for v in audit['tasks'] if v['id']==task['id']);row['new_long1880']=status
  for k in ['verified_scope','remaining_or_boundary','evidence']:row[k]=aa[k]
 for n,val in [('current-task-registry.json',reg),('current-52-task-audit.json',audit)]:(out/n).write_bytes(enc(val))
 for task in audit['tasks']:
  target=out/task['evidence']
  if not target.exists():
   src=S/'docs'/task['evidence'] if (S/'docs'/task['evidence']).exists() else repo/'docs'/task['evidence'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(src.read_bytes())
 (out/'current-52-task-audit.md').write_bytes(m.render(out));plan['branches'][name]={'branch':branch,'parent':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),'files':{'docs/'+n:sha((out/n).read_bytes()) for n in ['current-task-registry.json','current-52-task-audit.json','current-52-task-audit.md']}}
(T/'crg-r1895-prepared.json').write_bytes(enc(plan));s=(T/'crg-r1850-publish.py').read_text().replace('crg-r1850','crg-r1895').replace('test: freeze original600 four-cell comparison before sole launch [skip ci]','test: archive fresh formal gates and sole zero-clock long initial observation [skip ci]');(T/'crg-r1895-publish.py').write_bytes(s.encode());print(json.dumps({'files':len(files),'phase':status['phase'],'snapshot_utc':o['node_utc'],'cycles':snapshot['campaigns']['baseline']['cycles_recorded']}))
