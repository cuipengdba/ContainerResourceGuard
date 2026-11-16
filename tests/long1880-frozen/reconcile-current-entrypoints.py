from pathlib import Path
import hashlib,importlib.util,json,subprocess
T=Path(__file__).parent;B=T.parent;repo=B/'ContainerResourceGuard-integration';enc=lambda v:(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode();sha=lambda b:hashlib.sha256(b).hexdigest();S=T/'crg-r1912-prepared';S.mkdir(exist_ok=False);files={}
verified=json.loads((T/'crg-r1910-final-verification.json').read_bytes());prior=json.loads((T/'crg-r1911-turn-state.json').read_bytes());receipt=json.loads((T/'crg-r344-observations/638-crg-r1905-observe-long97.json').read_bytes());native=json.loads(receipt['stdout']);assert receipt['exit']==0 and native['phase']=='measuring-baseline' and native['main_checks']==native['main_passed']==12 and len(native['independent_baseline_guards'])==2 and all(v['original_alive'] and v['expected_entry_matches'] for v in native['processes'].values());assert verified['formal_original18_accepted'] and verified['new_long_started'] and not verified['long_duration_accepted']
def keep(n,raw):
 p=S/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);files[n]=sha(raw)
oldoverview=(repo/'docs/release-readiness-current.md').read_bytes();oldbusiness=(repo/'docs/testing-live-capacity-native-and-business-current.md').read_bytes();keep('docs/release-readiness-before-fresh18-long1880.md',oldoverview);keep('docs/live-capacity-before-fresh18-long1880.md',oldbusiness)
summary='集成候选源`37ca44e0`已独立完成新一轮DBS/HISDBS各原600秒，**原18项业务检查与另4项辅助检查全部接受**；固定四组对照44/44和同源四格原生284/284分别归档。新19输入长稳已唯一实际启动，当前24h observe基线运行中，初期原启动12/12、首周期内容通过但原生整段验证仍pending；同容器24h enforce、新七天和原老化后/发布门槛尚未接受。公开preview.5未改，稳定1.0未发布。'
live='本页核对到测试节点原生UTC `'+native['node_utc']+'`；准确PID/start的runner、worker、只读记录器均仍在运行，两角色八项原控制和实际Agent ELF独立复核保持。日期是该节点时钟，时长验收依原程序单调计时；快照不替代原24h/24h/7d。'
overview='''# 当前交付与待办：2026-11-16

'''+summary+'\n\n'+live+'''

## 当前候选的独立证据

|范围|已核实结果|仍未证明的范围|
|---|---|---|
|[新原18项正式复验](development-fresh-formal18.zh.md)|两角色各原600秒；原9项×2与辅助2项×2分开接受；30准确原件1646028字节、独立归属清理|不替代长稳或任意百分比业务性能|
|[固定四组原600秒对照](development-original600-comparison.zh.md)|DBS/HISDBS各observe/enforce，44/44，56准确原件3274433字节；原生SQL/API零错误|两条单独exec原5秒标志仍false，不宣称全部请求低于5秒或确定CRG因果|
|[CPU修复与新原生矩阵](testing-live-capacity-native-and-business-current.md)|ARM64实际CPU下线/上线56/56；AMD64/ARM64、Linux6.8/7完整59绑定下284/284|AMD64热插拔EBUSY、厂商ARM业务、独立物理多盘仍缺；不是内存热插拔证明|
|[新长稳1880](development-new-long1880.zh.md)|19输入冻结、原磁盘准入拒绝及可逆归档保留，再次完整准入后唯一实际启动；原启动12/12|24h基线仍运行，首周期content-passed-native-pending，不授予完整时长/周期资格|

原18项与辅助4项的整体接受来自新正式计划/coordinator及准确原9名称/辅助标签核对；复用per-role原件中的旧comparison scope和raw formal=false仍保留，不能通过改标签冒充接受。受控120秒负向诊断只证明已知注入锁的观察能力，PSI不可用不算零压力。

本表只归属于源37ca44e及对应准确ELF/输入。其它分支保留其各自产品源，旧ced候选的热重载、维护、开销、打包和长期证据仍各归原来源，不能转移为新源通过。固定手动参考为外部8核/20GiB下7.2核、memory.high20001980416、读写64MiB/s及手动4096IOPS，未放宽原SLA，不能据此保证默认20%业务性能。

## 用户要求与当前功能

每容器一份Agent，只控制自身CPU/内存/IO，重建后重新发现并复核cgroup。三项独立百分比各默认20%，保留手动模式；CPU用cpu.max，内存用memory.high回收/节流并保留外部硬上限，IO百分比仅自动标定读写带宽，IOPS只在手动模式。默认自动选最大合格本地可写文件系统并复用profile；纯v2才设置，v1/混合/未知或权限不足跳过并记录。辅助故障不阻断原业务；每日一份日志、保留30天/1GiB。memory.high允许超过目标，不能保证系统绝无OOM。其它资源限制不加入当前范围。

[使用配置](../README.md)、[完整需求档案](requirements.md)、[十版原规划](roadmap.md)、[当前逐项任务审核](current-52-task-audit.md)、[机器登记](current-task-registry.json)、[发布和恢复策略](operations-release-policy.md)。52项原定义及18项既有任务完成声明保持；业务原18项是另一个独立验收范围，不能混用计数。

## 仍须完成

1. 新24h observe完整时长/原周期及审计接受后，在同一容器24h enforce，再完成新七天及原业务全部标准；不继承旧1396/1728/78时间。
2. 原老化后故障、恢复、状态/所有权、镜像持久化、维护/升级等剩余组合。旧源结果只保留原资格；缺少的厂商ARM和两块独立物理设备覆盖明确未验。
3. 最终源/准确包身份下的可重复构建、SBOM/来源与离线校验、安装/回退和发布实际下载核验，产品实现合入main及正式稳定发布。已有打包演练不等于新候选或稳定附件验收。

当前公开下载仍为[v1.0.0-preview.5](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v1.0.0-preview.5)，原八资产、正文和tag不变；[草稿PR](https://github.com/cuipengdba/ContainerResourceGuard/pull/1)尚未合并，稳定v1.0.0尚未接受。

## 历史原件与来源边界

[此前交付页完整原文](release-readiness-before-fresh18-long1880.md)保留旧候选各热重载/诊断/维护/打包/持久化测试入口及当时的“待终态/未启动”状态；这些是历史时点，当前以本页和准确日期的独立证据为准。[旧1761失败完整原文](live-capacity-before-fresh18-long1880.md)及[原600秒失败原件](test-results-live-capacity-business600-terminal.json)仍为failed/exit1：DBS SQL一次错误/max5.004658635秒，原因unknown，不被新通过覆盖。旧1396协调器失败、1728为换缺陷源码而停止、旧78失败及默认20%业务失败都保留；不放宽标准、不反复跑到绿灯，也不把可逆PG归档视为业务或掉电持久化验收。
''';keep('docs/release-readiness-current.md',overview.encode())
business='''# 新容量候选：当前证据与历史失败

'''+summary+'\n\n'+live+'''

当前产品源37ca44e0e24a0eaa14e52b5c8bbbda54c76364b0在集成分支；各项资格按准确来源区分，main及其它分支未因此自动换产品源。

## 原生与CPU容量刷新

同一Agent/PID1在四次实际CPU下线/上线后重算20%配额，4核0.8→3核0.6→4核0.8；ARM64/Linux7的56项、原8控制/CPU掩码和归属清理接受，旧版六项失败保留。AMD64下线EBUSY原因未知不算覆盖。完整59来源绑定下，AMD64/ARM64与Linux6.8/7四格原生284/284接受，见[CPU证据](testing-live-cpu-capacity-refresh.md)、[准确计划](test-plan-capacity-refresh-native-CI-v2.json)、[独立结论](test-results-live-capacity-native-CI-v2.json)及[32准确成员](test-evidence-live-capacity-native-CI-v2.json.gz)。首轮50绑定缺9项的门禁缺口仍保留，不改写成完整通过；不代表厂商ARM、内存热插拔或独立物理双盘。

## 新一轮原18项正式验收与长稳

[新正式复验](development-fresh-formal18.zh.md)在四组原600秒对照之后另行冻结、唯一执行；两角色各原600秒、原18项与4辅助分别全部接受，原生SQL/API零错误、完整备份/同步/独立恢复、原启动/缓存/八控制和准确归属清理保持。30准确原件与旧scope/raw false元数据边界已独立复算，不能把先前对照或改标签当正式接受。

[固定四组对照](development-original600-comparison.zh.md)44/44及56原件分别归档；DBS-enforce API5.3326秒和HISDBS-observe SQL8.2149秒两个单独exec原标志仍false。原native-campaign规则以完整成功原生窗口包含内容周期，标准未改；不是所有请求低于5秒或CRG因果证明。

[新长稳1880](development-new-long1880.zh.md)以源37和19准确输入从零开始，原24h observe→同容器24h enforce→新七天及全部原指标不变。原启动12项与当前只读身份/原控制核对通过；首周期内容通过但整段原生资格pending，当前没有24h或长期接受。后续老化后/维护/发布条件仍待。

## 旧1761失败继续保留

旧轮DBS完整600.336702秒，SQL299次1错误/max5.004658635秒，角色7通过/1失败/1未执行；HISDBS600.367087秒、9/9通过，整体17项记录16通过，原计划18项未接受。[完整原文](live-capacity-before-fresh18-long1880.md)、[独立失败复算](test-results-live-capacity-business600-terminal.json)、[22准确原件](test-evidence-live-capacity-business600-terminal.json.gz)保持failed/exit1和独立清理结论。旧工作线程未保存异常明细，丢失信息无法事后恢复，原因仍unknown，不能认定CRG或此CPU修复导致，也不被新成功抵消。

为后续请求增加的[有界错误诊断](development-sql-failure-diagnostics.zh.md)已完成两平台26项及两个准确原镜像各6项兼容性，后续[受控120秒锁负向诊断](development-controlled-sql-wait.zh.md)各13/13，前两次夹具失败保留。该已知注入锁不能解释旧未知原因，PSI六项实际不可用也不能冒充压力验证。

原52项定义及18项既有任务范围声明不改。所有预算保持原固定手动参考，不能证明任意默认20%业务性能；旧ced/1396/1728/78的来源和时钟不继承。其它压力/状态/权限切换、节点/镜像重建、老化后故障/恢复/升级、稳定源打包和实际安装/发布下载等剩余项见[当前逐项审核](current-52-task-audit.md)。
''';keep('docs/testing-live-capacity-native-and-business-current.md',business.encode())
banner=summary+' [当前交付与剩余工作](release-readiness-current.md)、[新正式18项/4辅助](development-fresh-formal18.zh.md)、[新长稳计划与实际状态](development-new-long1880.zh.md)。\n\n以下为此前各时点记录，保留原文及原验收要求；其中“当前/未启动/待终态”仅适用于对应历史来源，不覆盖上面的当前结论。\n\n## 历史更新与原计划（原文保留）\n\n'
for path in ['docs/next-version.md','docs/requirements.md','docs/roadmap.md']:
 raw=(repo/path).read_text();first,body=raw.split('\n',1);keep(path,(first+'\n\n'+banner+body.lstrip('\n')).encode())
path='docs/development-sql-failure-diagnostics.zh.md';raw=(repo/path).read_text();first,body=raw.split('\n',1);body=body.replace('## 当前结论','## 诊断工具阶段结论（先于新正式业务复验）',1);keep(path,(first+'\n\n'+banner+body.lstrip('\n')).encode())
keep('docs/development-next-business-comparison.zh.md',('''# 固定对照、另行正式复验与后续长稳

[固定四组原600秒对照](development-original600-comparison.zh.md)已终止，44/44及独立清理接受；它本身不授予原18项正式资格。随后[另行冻结的新正式两角色复验](development-fresh-formal18.zh.md)各原600秒，原18项及4辅助分别全部接受；来源和原件独立，不借用对照。当前[新19输入长稳](development-new-long1880.zh.md)已从零启动，24h基线运行中，尚无24h/24h/7d或稳定发布接受。旧失败及unknown原因保持，两个对照exec超5秒标志仍false。完整当前范围见[交付页](release-readiness-current.md)。
''').encode())
record={'schema':'crg-current-entrypoint-reconciliation-v1','native_snapshot_utc':native['node_utc'],'live_runner':{k:native['processes']['runner'][k] for k in ['pid','start_ticks','original_alive','expected_entry_matches']},'phase':native['phase'],'source_revision':prior['source_revision'],'formal_original18_accepted':True,'separately_qualified_auxiliary4':True,'fixed_comparison_passed':44,'native_controller_checks_passed':284,'startup_passed':12,'cycles_recorded':1,'last_cycle_phase':native['campaigns']['baseline']['last_cycle']['phase'],'long_duration_accepted':False,'stable_release_accepted':False,'old1761_cause':'unknown','criteria_or_frozen_sources_changed':False,'all52_definitions_and18_task_claims_unchanged':True,'old_entrypoint_archive_sha256':{'release-readiness-before-fresh18-long1880.md':sha(oldoverview),'live-capacity-before-fresh18-long1880.md':sha(oldbusiness)}};keep('docs/test-results-current-entrypoint-reconciliation.json',enc(record));keep('tests/long1880-frozen/reconcile-current-entrypoints.py',Path(__file__).read_bytes())
spec=importlib.util.spec_from_file_location('render',repo/'scripts/render-task-audit.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);plan={'common_files':files,'branches':{}}
scope='集成候选37ca44e/准确ELF的新正式两角色各原600秒，原18项及独立4辅助全部接受；四组对照44/44与完整59绑定四格原生284/284分别归档，ARM64 CPU实际热插拔56/56。新1880源37/19冻结输入已唯一实际启动，24h基线测量中，原启动12/12及两角色八原控制/准确三进程/实际Agent ELF独立核对保持；首周期仅content-passed-native-pending。其它分支保留各自产品源，既有旧源资格不转移。'
remaining={
 'P02.1':'当前新24h observe完整时长/原周期/审计尚待；随后同容器24h enforce、新七天及原老化后故障/恢复/维护/升级和稳定发布门槛不变。旧1396/1728/78来源/时钟不继承，旧1761失败原因unknown，不放宽原SLA或用快照代替接受。',
 'P02.2':'原SQL/API零错误、max5秒、p95桶1秒、98%覆盖、完整备份/同步/恢复/包含关系和控制/清理须在各完整长期窗口实际接受。两条对照exec超5秒仍false；PSI不可用不算零压力，不能证明任意20%业务性能。',
 'P06.3':'连续权限撤销/恢复、私有namespace/systemd/祖先与可信宿主基数等剩余原生/厂商组合须逐项终态；现有284或短业务不能替代长期/老化。AMD64 CPU下线EBUSY、内存热插拔和厂商ARM业务未覆盖，未知统计不冒充已测。',
 'P06.4':'连续重建/路径复用/只读权限切换与节点重启等剩余原组合待验，AMD64 CPU下线EBUSY未覆盖；不能以ARM64热插拔56项代替全部组合，不重启共享测试节点干扰本轮长稳。旧1761失败及unknown原因保留。',
 'P10.2':'新七天尚未开始，必须在原24h基线和同容器24h限制接受后完成原全部周期、冷启动/重建/恢复/升级/故障及长于七天关键周期补充。首周期内容通过和旧约4.5天/4.23小时/3107秒历史均不计长期接受。',
 'P10.3':'新候选完整长期/老化后隔离、权限降级、外部冲突、脱敏、恢复所有权及最终准确包/稳定发布身份仍须闭环；旧源维护/打包/压力/持久化资格不转移。旧失败未知原因明确保留，缺厂商ARM/独立物理多盘不冒充支持。'}
for name,row in verified['branches'].items():
 r=B/name;out=S/'branch-specific'/name;out.mkdir(parents=True);reg=json.loads((r/'docs/current-task-registry.json').read_bytes());audit=json.loads((r/'docs/current-52-task-audit.json').read_bytes());parent=subprocess.check_output(['git','-C',str(r),'rev-parse','HEAD'],text=True).strip();assert parent==row['commit'];reg['current_entrypoint_reconciliation']=record;audit['current_entrypoint_reconciliation']=record
 for task in reg['tasks']:
  if task['id'] not in remaining:continue
  a=dict(task['current_acceptance']);a.update(verified_scope=scope,remaining_or_boundary=remaining[task['id']],evidence='release-readiness-current.md');task['current_acceptance']=a;task['current_acceptance_previous_exact_parent']={'commit':parent,'path':'docs/current-task-registry.json','task_id':task['id']};arow=next(v for v in audit['tasks'] if v['id']==task['id'])
  for k in ['verified_scope','remaining_or_boundary','evidence']:arow[k]=a[k]
 reg['latest_requirements']='CPU/memory/IO only, independent percentages each default20; memory.high reclaim/throttle retaining external hard caps; calibrated read/write BPS percentage, IOPS manual only. Purev2 writes; v1/hybrid/unknown or inadequate permission skips/logs. Automatic largest qualified local writable filesystem calibration/profile reuse; strict per-container1:1; helper failure never gates original business. Daily files30days/1GiB. Integration source37 has separate fresh formal18+4 accepted, fixed comparison44 and native284; new1880 baseline24h active/startup12 only, no duration acceptance. Same-container24h/new7d and original post-aging, final source/package/install/release gates pending. Old failures/unknown causes and old-source qualifications retained without transfer. Other branches keep own production source; preview5 unchanged/stable not accepted.'
 for n,v in [('current-task-registry.json',reg),('current-52-task-audit.json',audit)]:p=out/'docs'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(enc(v))
 for task in audit['tasks']:
  target=out/'docs'/task['evidence']
  if not target.exists():
   source=S/'docs'/task['evidence'] if (S/'docs'/task['evidence']).exists() else r/'docs'/task['evidence'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
 (out/'docs/current-52-task-audit.md').write_bytes(m.render(out/'docs'));readme=(r/'README.md').read_text();first,body=readme.split('\n',1);paragraph=body.lstrip('\n').split('\n\n',1)[0];assert paragraph.startswith('当前18/52项');body=body.replace(paragraph,summary+' [当前交付与待办](docs/release-readiness-current.md)、[准确新正式复验](docs/development-fresh-formal18.zh.md)、[新长稳状态](docs/development-new-long1880.zh.md)。',1);(out/'README.md').write_bytes((first+'\n'+body).encode());names=['docs/current-task-registry.json','docs/current-52-task-audit.json','docs/current-52-task-audit.md','README.md'];plan['branches'][name]={'branch':row['branch'],'parent':parent,'files':{n:sha((out/n).read_bytes()) for n in names}}
(T/'crg-r1912-prepared.json').write_bytes(enc(plan));s=(T/'crg-r1850-publish.py').read_text().replace('crg-r1850','crg-r1912').replace('test: freeze original600 four-cell comparison before sole launch [skip ci]','docs: reconcile current release entrypoints with fresh formal and live long evidence [skip ci]');(T/'crg-r1912-publish.py').write_bytes(s.encode());print(json.dumps({'files':len(files),'phase':native['phase'],'current_task_scopes_reconciled':len(remaining),'source_or_criteria_changed':False}))
