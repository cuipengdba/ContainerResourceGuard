# 当前交付与待办：2026-11-16

> 正式v1.0.0已发布：八项公开附件完整下载/摘要及两架构离线验包通过，[实际发布收据](publication-v1.0.0.zh.md)。长稳、老化后与真实回退验收继续，不因发布改为已通过。

> 2026-11-17用户明确要求现在正式发布v1.0.0，本次按此要求提前发布；该发布决策优先于下文此前“未达全部稳定条件仅预发布”的项目流程。已发布版本身份与完整稳定性资格分别记录，未完成的限制24h、新七天、老化后和真实回退不改为通过，52任务/18原完成声明保持，测试继续。[正式版说明](releases/v1.0.0.md)与[决策记录](release-decision-v1.0.0.json)。以下保留历史时点及原验收条件。

> 更新：原1880的24h基线已独立接受，DBS/HISDBS各完整86400秒、SQL/API零错误、4轮备份恢复通过；目前同容器24h enforce，原八项控制/进程/ELF复核通过，新七天未开始。回退准备Linux13组保护通过，真实仍pending。详见[本轮真机与回退输入](development-source37-aged-input-prepare.zh.md)。以下此前时点记录保留，不能作当前阶段状态；整体长稳与稳定1.0仍未接受。

集成候选源`37ca44e0`已独立完成新一轮DBS/HISDBS各原600秒，**原18项业务检查与另4项辅助检查全部接受**；固定四组对照44/44和同源四格原生284/284分别归档。新19输入长稳已唯一实际启动，当前24h observe基线运行中，初期原启动12/12、首周期内容通过但原生整段验证仍pending；同容器24h enforce、新七天和原老化后/发布门槛尚未接受。公开preview.5未改，稳定1.0未发布。

本页核对到测试节点原生UTC `2026-11-16T02:37:27.650400+00:00`；准确PID/start的runner、worker、只读记录器均仍在运行，两角色八项原控制和实际Agent ELF独立复核保持。日期是该节点时钟，时长验收依原程序单调计时；快照不替代原24h/24h/7d。

## 当前候选的独立证据

|范围|已核实结果|仍未证明的范围|
|---|---|---|
|[新原18项正式复验](development-fresh-formal18.zh.md)|两角色各原600秒；原9项×2与辅助2项×2分开接受；30准确原件1646028字节、独立归属清理|不替代长稳或任意百分比业务性能|
|[固定四组原600秒对照](development-original600-comparison.zh.md)|DBS/HISDBS各observe/enforce，44/44，56准确原件3274433字节；原生SQL/API零错误|两条单独exec原5秒标志仍false，不宣称全部请求低于5秒或确定CRG因果|
|[CPU修复与新原生矩阵](testing-live-capacity-native-and-business-current.md)|ARM64实际CPU下线/上线56/56；AMD64/ARM64、Linux6.8/7完整59绑定下284/284|AMD64热插拔EBUSY、厂商ARM业务、独立物理多盘仍缺；不是内存热插拔证明|
|[新长稳1880](development-new-long1880.zh.md)|19输入冻结、原磁盘准入拒绝及可逆归档保留，再次完整准入后唯一实际启动；原启动12/12|24h基线仍运行，首周期content-passed-native-pending，不授予完整时长/周期资格|
|[源37打包/SBOM/来源](live-capacity-package-rehearsal.zh.md)|准确9deb打包，两架构/14完整性/8输出重建通过；完整ZIP、4客户端内容与10签名条件独立接受|仅候选演练，最终稳定身份附件、实际安装/回退与发布下载仍待|

|[源37老化只读门禁](development-source37-aged-reader-v2.zh.md)|两平台各13组合成故障及真机baseline pending/提前采集拒绝通过，19输入保持|此条记录发布时无执行器；现有新执行器保护检查见下一行，真实seal/老化仍待|
|[源37老化执行器保护](development-source37-aged-executor-v1.zh.md)|两平台各12组合成保护、实际default/execute均pending；原标准保留，旧max版本拒绝|代码可用但真实seal/authority/老化执行均待，high预览回退目标未验；旧max历史未通过保留，当前按用户决定拒绝|
|[老化v2原始证据与独立审核](development-source37-aged-evidence-v2.zh.md)|Linux14+16组、Windows14+15通过/1跳过，实际3入口pending；high-only范围用户已确认|真实seal/回执/老化仍待，旧max版按要求拒绝；其它原门槛保持|
|[七天采集入口修复](development-source37-capture-v3.zh.md)|Linux8组、Windows6通过/2跳过，旧两处采集缺陷明确复现；实际pending/提前拒绝通过|真实七天seal仍待；采集须用capture-v3，原源/时长不改|
|[老化单次执行包装器](development-source37-aged-runner-v2.zh.md)|Linux11组/Windows4通过7跳过；真实默认/执行均pending|仍待真实一次性启动、authority、退出回执和独立审核，原长测不改|
|[老化单次执行包装器](development-source37-aged-runner-v3.zh.md)|Linux13组/Windows4通过9跳过；真实默认/执行均pending|仍待真实一次性启动、authority、退出回执和独立审核，原长测不改|
|[单次七天身份保存](development-source37-capture-save.zh.md)|Linux13组/Windows5通过8跳过；真实默认/保存均pending|必须在真实新七天窗口采集；未生成实际seal，不代表时长或发布接受|
|[单次后台验收启动](development-source37-detached-launch.zh.md)|Linux12组/Windows4通过8跳过；真实默认/启动均pending|具备后台交接工具，实际启动/退出/恢复和发布审核仍待|

原18项与辅助4项的整体接受来自新正式计划/coordinator及准确原9名称/辅助标签核对；复用per-role原件中的旧comparison scope和raw formal=false仍保留，不能通过改标签冒充接受。受控120秒负向诊断只证明已知注入锁的观察能力，PSI不可用不算零压力。

本表只归属于源37ca44e及对应准确ELF/输入。其它分支保留其各自产品源，旧ced候选的热重载、维护、开销、打包和长期证据仍各归原来源，不能转移为新源通过。固定手动参考为外部8核/20GiB下7.2核、memory.high20001980416、读写64MiB/s及手动4096IOPS，未放宽原SLA，不能据此保证默认20%业务性能。

## 用户要求与当前功能

每容器一份Agent，只控制自身CPU/内存/IO，重建后重新发现并复核cgroup。三项独立百分比各默认20%，保留手动模式；CPU用cpu.max，内存用memory.high回收/节流并保留外部硬上限，IO百分比仅自动标定读写带宽，IOPS只在手动模式。默认自动选最大合格本地可写文件系统并复用profile；纯v2才设置，v1/混合/未知或权限不足跳过并记录。辅助故障不阻断原业务；每日一份日志、保留30天/1GiB。memory.high允许超过目标，不能保证系统绝无OOM。其它资源限制不加入当前范围。

[使用配置](../README.md)、[完整需求档案](requirements.md)、[十版原规划](roadmap.md)、[当前逐项任务审核](current-52-task-audit.md)、[机器登记](current-task-registry.json)、[发布和恢复策略](operations-release-policy.md)。52项原定义及18项既有任务完成声明保持；业务原18项是另一个独立验收范围，不能混用计数。

## 仍须完成

1. 新24h observe完整时长/原周期及审计接受后，在同一容器24h enforce，再完成新七天及原业务全部标准；不继承旧1396/1728/78时间。
2. 原老化后故障、恢复、状态/所有权、镜像持久化、维护/升级等剩余组合。旧源结果只保留原资格；缺少的厂商ARM和两块独立物理设备覆盖明确未验。
3. 最终源/准确包身份下的可重复构建、SBOM/来源与离线校验、安装/回退和发布实际下载核验，产品实现合入main及正式稳定发布。源37本轮演练只绑定准确9deb候选包，后续稳定附件须按最终打包提交重验；安装/回退和发布实际下载仍待。

当前公开下载仍为[v1.0.0-preview.5](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v1.0.0-preview.5)，原八资产、正文和tag不变；[草稿PR](https://github.com/cuipengdba/ContainerResourceGuard/pull/1)尚未合并，稳定v1.0.0尚未接受。

## 历史原件与来源边界

[此前交付页完整原文](release-readiness-before-fresh18-long1880.md)保留旧候选各热重载/诊断/维护/打包/持久化测试入口及当时的“待终态/未启动”状态；这些是历史时点，当前以本页和准确日期的独立证据为准。[旧1761失败完整原文](live-capacity-before-fresh18-long1880.md)及[原600秒失败原件](test-results-live-capacity-business600-terminal.json)仍为failed/exit1：DBS SQL一次错误/max5.004658635秒，原因unknown，不被新通过覆盖。旧1396协调器失败、1728为换缺陷源码而停止、旧78失败及默认20%业务失败都保留；不放宽标准、不反复跑到绿灯，也不把可逆PG归档视为业务或掉电持久化验收。
