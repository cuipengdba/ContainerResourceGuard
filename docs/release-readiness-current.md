# 当前交付与待办：2026-11-16

当前18/52项按各自原定义范围完成，稳定1.0尚未接受。公开下载仍为[v1.0.0-preview.5](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v1.0.0-preview.5)，八附件和标签不变；固定最终候选的产品实现尚未合入main。[完整任务](current-task-registry.json)及[逐项审核](current-52-task-audit.md)保持全部原定义、失败和具体待办。

## 当前功能

每容器一份Agent，只控制自身CPU/内存/IO；重建后重新发现cgroup。三个百分比各自默认20%，保留手动额度模式。CPU用cpu.max，内存用memory.high回收/节流并保留外部硬上限，IO百分比用自动最大合格本地分区标定的读写BPS，IOPS只在手动模式设置。只在纯v2写入，v1/混合/未知/权限不足明确日志降级；辅助故障不阻断业务。日志一天一文件、30日/1GB清理。memory.high允许短时超目标，不能承诺系统绝无OOM。

[使用与配置](../README.md)、[逐容器升级](upgrade-preview4-preview5.zh.md)、[运维与恢复](operations-release-policy.md)。

## 已完成的固定候选验证

| 范围 | 实际结果 |
| --- | --- |
| [原路径业务](testing-final-v1-full600-terminal.md) | DBS/HISDBS各原600秒、18/18，SQL/API及物理备份/同步/独立恢复和清理 |
| [原生架构/内核](testing-final-v1-native-CI-terminal.md) | amd64/ARM64、Linux6/7四VM组合284/284；不是厂商ARM或独立物理多盘证明 |
| [热重载](testing-final-v1-business-reload-terminal.md) | 18主/26观察，各600秒，拒绝坏配置并保留策略 |
| [诊断](testing-final-v1-diagnostics-counter-fixed-terminal.md) | 20主/38诊断，各600秒；缺失计数如实表示 |
| [维护](testing-final-v1-binary-maintenance-terminal.md) | 40/40，两角色各600秒、单写者及显式回退/原值恢复 |
| [CLI与可选启动](testing-final-v1-cli-supervisor-terminal.md) | 26主/48子，各600秒、自然老化/锁及两种支持模板安装卸载；未知私有布局安全拒绝 |
| [完整输出1615](testing-final-v1-output1615-terminal.md) | 26主/28输出，各600秒，补齐P07.1并独立复算清理 |
| [开销](testing-final-v1-budget-overhead-terminal.md) | 多档实际限额及健康/导出失败/只读各1800秒；Agent自身计数，不冒充厂商因果性能或七天 |
| [解析器](testing-final-v1-parser-fuzz.md) | 准确源码两目标各300秒、418输入保持；非真实掉电证明 |
| [候选打包与来源](final-v1-package-rehearsal.md) | 实际Linux两架构包、14项离线检查、重复构建打包及10项独立签名正常/拒绝；本地SBOM schema通过，尚非稳定附件/安装验收 |
| [历史硬内存恢复并发](testing-final-v1-legacy-restore-pressure.md) | 相同最终ELF、amd64/ARM64与Linux6.8/7.0四VM，116/116及16夹具清理；模拟旧journal，不代替真实旧版本迁移或厂商老化验收 |
| [安全暂存与准确包维护](verified-release-staging.md) | 两架构150/150及52暂存场景，实际候选包升级/回退/禁用；原失败保留，非稳定身份或厂商/老化验收 |
| [安全暂存深度修复](verified-release-staging-depth.md) | 旧缺陷两架构复现保留；新工具整树预检/64层上限，原150项及12个深度场景通过；未改变长期门槛 |

## 正在进行与待办

[正式1396长期试验](testing-final-v1-long-node-admission.md)已独立准入并唯一启动baseline observe。原16输入、最终ELF和原SLA保持，另有只读Pod/事件记录器。协议是同容器24h observe→24h enforce→新七天，至少777600秒；启动/首周期不计时长通过。旧78已失败、不足七天，不继承其时长。当前不启动其他一次性厂商业务夹具干扰独占测量。

后续需完成长期及老化后故障/维护验收、各项剩余压力/所有权/状态场景，以及最终稳定打包、安装/回退和发布实际下载。每项边界见逐项审核。用户暂无额外厂商ARM和独立物理多盘节点，保留未验证范围；[环境矩阵](tested-environment-matrix.md)不扩大支持。

## 保留失败与历史

默认三项20%完整业务曾发生SQL/API和停库超时，manual参考通过不能证明任意数据库20%性能。[1551输出失败](testing-final-v1-output-matrix-failed.md)、[1571镜像/Ready前失败和旧78终态](testing-output1571-old78-node-admission.md)、[容量/原镜像恢复](testing-capacity-recovery-output1615.md)保留原件；旧78主库fast shutdown来源仍未确认。既有诊断/维护执行器错误及观察竞态也保留对应原件，不改判原失败。

[本次整理前交付页](release-readiness-before-package-rehearsal.md)保留此前时点的17项/未启动等原始记录；当前状态以上述摘要及明确日期的实际收据为准。
