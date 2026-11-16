from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
T=Path(__file__).parent;B=T.parent;enc=lambda v:(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode();sha=lambda b:hashlib.sha256(b).hexdigest()
f=json.loads((T/'crg-r1880-long-frozen.json').read_bytes());freeze=T/f['freeze'];expected=f['uploaded_sha256'];assert len(expected)==19
assert all(sha((freeze/n).read_bytes())==h for n,h in expected.items())
pre=json.loads((T/'crg-r1881-upload-long-preflight.json').read_bytes());v=json.loads(pre['stdout']);admission=json.loads(v['stdout']);assert pre['exit']==v['exit']==0 and admission['phase']=='ready' and not admission['long_measurement_started'] and not v['business_created']
old=(T/'crg-r1731-launch-long97.py').read_text();tree=ast.parse(old);node=next(n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='expected' for t in n.targets));lines=old.splitlines(keepends=True);offset=sum(len(x) for x in lines[:node.value.lineno-1])+node.value.col_offset;end=sum(len(x) for x in lines[:node.value.end_lineno-1])+node.value.end_col_offset
launcher=(old[:offset]+repr(expected)+old[end:]).replace('final1728','final1880').replace('FINAL1728','FINAL1880').replace('formal1728','formal1880').replace('fabfb66930dcf8d415e7771c1f487d619017ed03bdb5cbd8220000ddde4da6d4',expected['observer-readonly.py']);ast.parse(launcher)
assert 'node-admission.py' in launcher and '0f5cfbd1866947a9c13db2a930b3ecc89a4702651857ce1f3abd7fb218082868' in launcher and 'os.O_EXCL' in launcher
lp=T/'crg-r1883-launch-long97.py';assert not lp.exists();lp.write_bytes(launcher.encode())
observe=(T/'crg-r1732-observe-long97.py').read_text().replace('final1728','final1880').replace('ea19e85c8e8690845449ce36b9e3be8266282015cb8e8ba8ed6eec207187370c',f['plan_sha256']);ast.parse(observe);(T/'crg-r1884-observe-long97.py').write_bytes(observe.encode())
S=T/'crg-r1882-prepared';S.mkdir(exist_ok=False);files={}
def keep(n,raw):
 p=S/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);files[n]=sha(raw)
for n,h in expected.items():
 if n.startswith('binaries/'):continue
 keep('tests/long1880-frozen/'+n,(freeze/n).read_bytes())
keep('tests/long1880-frozen/launch-once.py',lp.read_bytes());keep('tests/long1880-frozen/observe-readonly.py',observe.encode());keep('tests/long1880-frozen/prepare-publication.py',Path(__file__).read_bytes())
keep('docs/test-plan-new-long1880.json',enc(f));keep('docs/test-results-new-long1880-admission.json',enc({'schema':'crg-long1880-prelaunch-native-admission-v1','admission':admission,'source_members_verified':19,'launcher_sha256':sha(lp.read_bytes()),'launch_not_executed':True,'product_source_revision':f['source_revision'],'stable_release_accepted':False}))
status={'phase':'frozen-ready-not-launched','plan':'test-plan-new-long1880.json','guide':'development-new-long1880.zh.md','source_revision':f['source_revision'],'job_sha256':f['job_sha256'],'plan_sha256':f['plan_sha256'],'new_clock':True,'inherited_seconds':0,'fresh_formal18_accepted':True,'auxiliary4_accepted':True,'native284_accepted':True,'stages_seconds':[86400,86400,604800],'long_duration_accepted':False,'stable_release_accepted':False}
guide='''# 新候选从零开始的长稳测试

CRG 源 37ca44e0 的独立 DBS/HISDBS 原18项和另4项辅助检查已经按原600秒完成并接受，原件和旧元数据边界见[正式复验](development-fresh-formal18.zh.md)。原四组对照44/44与Linux 6.8/7、AMD64/ARM64原生284项分别归档，不能互相代替。产品仍仅CPU、内存、IO独立百分比默认20；memory.high、百分比IO只限标定带宽、手动IOPS、纯v2设置/v1跳过、每容器一对一、辅助失败不阻断原启动、每日30天/1GiB日志均保留。

本轮是新命名空间、新工具目录、新准确源码和从零时钟。先24小时observe基线，再在同一容器24小时enforce，最后新的七天验收，共九天。各阶段原周期数4/4/28、SQL/API零错误/max5秒/p95桶1秒/98%覆盖、备份/同步/独立恢复、原start.sh与缓存enforce、父叶归属与原始审计器全部保留。既有人工参考预算和外部上限不变；这不是任意20%配置的性能保证。之后仍须原老化后故障/恢复/升级及发布门槛。

[19输入准确摘要和完整计划](test-plan-new-long1880.json)、[实际只读准入](test-results-new-long1880-admission.json)、[冻结文本和唯一启动程序](../tests/long1880-frozen/)、[原18项独立前置](test-results-fresh-formal18-v1-terminal.json)可审核。准确ELF由同源构建摘要绑定，文本归档不重复嵌入二进制。发布这些文件时尚未启动；只有实际唯一启动回执才代表开始。

唯一启动程序在启动前再次核对全部19输入、节点准入、正式复验准确报告/清理和native284，原独立前驱终态也必须保持。O_EXCL启动守卫和准确PID/start绑定防止重复；连接异常只读确认，不重启、不自动重试变更。独立只读记录器不写cgroup、不改变业务或中止业务。协调探针沿用相同字节的24例/114原件资格：仅失败的只读Pod清单最多三次，共15秒；无效清单和变更命令不重试。有限量私有故障输出不作为公开业务环境文件导出。

旧1396失败和1728因源码修复停止的结果完整保留，不继承时间、数据或源码资格；旧1761 DBS错误原因仍unknown。新观察器是附加信息，不授予原时长资格。缺失PSI不能冒充压力验证；没有独立物理双盘/厂商ARM节点的覆盖仍缺失。52项原定义/18项既有范围声明不改；当前无长稳完成结论，无稳定1.0发布。
''';keep('docs/development-new-long1880.zh.md',guide.encode())
spec=importlib.util.spec_from_file_location('render',B/'ContainerResourceGuard-integration/scripts/render-task-audit.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);plan={'common_files':files,'branches':{}}
for name,branch in [('ContainerResourceGuard-integration','release/integration-v1'),('ContainerResourceGuard-v10','next/compatibility-contract'),('ContainerResourceGuard-partition','next/partition-io'),('ContainerResourceGuard','main')]:
 repo=B/name;out=S/'branch-specific'/name/'docs';out.mkdir(parents=True);reg=json.loads((repo/'docs/current-task-registry.json').read_bytes());audit=json.loads((repo/'docs/current-52-task-audit.json').read_bytes());reg['new_long1880']=status;audit['new_long1880']=status
 for task in reg['tasks']:
  if task['id'] not in ['P02.1','P02.2','P06.3','P10.2','P10.3']:continue
  task['before_new_long1880']=dict(task['current_acceptance']);a=dict(task['current_acceptance']);a['verified_scope']+=' 新候选19输入/从零24h-24h-7d计划及唯一启动程序已冻结，当前只读准入ready，尚未启动。';a['remaining_or_boundary']+=' 各阶段必须原时长/原周期实际接受，禁止继承旧长测时钟或以快照替代。';a['evidence']='development-new-long1880.zh.md';task['current_acceptance']=a;task['new_long1880']=status;row=next(v for v in audit['tasks'] if v['id']==task['id']);row['new_long1880']=status
  for k in ['verified_scope','remaining_or_boundary','evidence']:row[k]=a[k]
 for n,val in [('current-task-registry.json',reg),('current-52-task-audit.json',audit)]:(out/n).write_bytes(enc(val))
 for task in audit['tasks']:
  target=out/task['evidence']
  if not target.exists():
   src=S/'docs'/task['evidence'] if (S/'docs'/task['evidence']).exists() else repo/'docs'/task['evidence'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(src.read_bytes())
 (out/'current-52-task-audit.md').write_bytes(m.render(out));names=['current-task-registry.json','current-52-task-audit.json','current-52-task-audit.md'];plan['branches'][name]={'branch':branch,'parent':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),'files':{'docs/'+n:sha((out/n).read_bytes()) for n in names}}
(T/'crg-r1882-prepared.json').write_bytes(enc(plan));(T/'crg-r1882-launcher-frozen.json').write_bytes(enc({'file':lp.name,'sha256':sha(lp.read_bytes()),'plan_sha256':f['plan_sha256'],'inputs':expected,'launched':False}));s=(T/'crg-r1850-publish.py').read_text().replace('crg-r1850','crg-r1882').replace('test: freeze original600 four-cell comparison before sole launch [skip ci]','test: freeze source37 zero-clock long plan and sole launch [skip ci]');(T/'crg-r1882-publish.py').write_bytes(s.encode());print(json.dumps({'common_files':len(files),'phase':status['phase'],'launcher_sha256':sha(lp.read_bytes())}))
