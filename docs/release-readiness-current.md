# 当前交付与待办：2026-11-15

最新实测：[输出1615完整终态](testing-final-v1-output1615-terminal.md)。两原厂角色各原600秒、26主/28输出通过，数值/代次/共享human与JSON/profile覆盖/外部冲突、原值恢复和活动资源清理独立复核。结合1525完成原P07.1，当前18/52；其余定义与失败保持。最终ELF及preview.5不变，稳定1.0与长期门槛未完成。

最新进展：[测试容量恢复及输出1615](testing-capacity-recovery-output1615.md)。退役数据按守卫回收约94.09GiB并保留报告；原厂镜像已同摘要恢复。新13输入协议绑定只读节点准入，19项本地及原生前缀通过，待唯一启动，未计业务通过。旧78主库收到fast shutdown，但来源未确认；原活动资源消失已独立核对。17/52、最终ELF及preview.5保持，正式1396与稳定验收未完成。

最新节点终态：[1571/旧78/存储准入](testing-output1571-old78-node-admission.md)。1571因原镜像缺失在Ready前失败，未运行产品或600秒；旧78在第19周期自行failed/exit1，不足七天，不再在线。八份退役冷副本载荷已按守卫清理，实际约4.7GiB；报告/原件保留。节点压力恢复False但可用空间与原镜像尚未满足新准入，正式1396未启动。17/52保持，稳定版未接受。

当前可下载 [v1.0.0-preview.5](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v1.0.0-preview.5)。固定 v1.0.0 候选尚未发布，main 产品实现尚未合入；公开八项附件及标签保持。产品源码为 ced461705ebc27315a59aefe463f9b4af47130a3，最终两架构 ELF 见[候选身份](final-v1-candidate-identity.json)。

## 已交付功能

- DBS/HISDBS 每容器一份 Agent，仅控制自身 cgroup，容器或 Pod ID 改变后重新发现。
- 仅 CPU、内存、IO；cpu_percent、memory_percent、io_percent 独立设置，省略各自默认20%，保留手动绝对额度模式。
- 内存使用 memory.high 回收/节流，保留外部硬上限；百分比可短时超过，不能保证系统绝无 OOM。
- IO 自动选择容量最大的合格可写本地文件系统进行标定/复用；默认百分比仅限制读写 BPS，IOPS 仅手动配置，外部 IOPS 保留。
- 仅纯 cgroup v2 校验后写入，v1/混合/未知或权限不足明确日志降级；辅助失败放行业务。
- 日志每天一文件，保留30天及总量1GB清理；日志故障不阻断业务。

[接入说明](../README.md)、[配置](configuration.md)、[升级](upgrade-preview4-preview5.zh.md)、[运行和恢复策略](operations-release-policy.md)。

## 固定最终候选的已完成验证

| 范围 | 实际结果 |
| --- | --- |
| [原路径业务](testing-final-v1-full600-terminal.md) | DBS/HISDBS 各600秒，18/18主检查，SQL/API零错误，真实物理备份、同步、独立恢复及清理 |
| [原生控制/分区](testing-final-v1-native-CI-terminal.md) | amd64/ARM64、Linux6/7四个实际VM组合284/284；非厂商ARM或独立物理多盘证明 |
| [同Agent热重载](testing-final-v1-business-reload-terminal.md) | 18/18主检查、26/26配置观察，各600秒，坏配置拒绝保留策略和业务完整验收 |
| [诊断/内存统计](testing-final-v1-diagnostics-counter-fixed-terminal.md) | 修订1465新测20/20主检查、38/38诊断，各600秒；PSI/HugeTLB缺失如实表示 |
| [自身开销](testing-final-v1-budget-overhead-terminal.md) | 健康/持续导出失败/实际只读及三档实际限额各自1800秒，181样本；Agent自身计数，非厂商因果性能或七天老化 |
| [源码解析器](testing-final-v1-parser-fuzz.md) | Windows amd64 两目标各配置300秒、实际301.02秒，418份输入前后不变；非Linux持久化故障证明 |

## 当前进行与待办

[最终二进制升级/回滚通过](testing-final-v1-binary-maintenance-terminal.md)：40/40，两角色各新600秒SQL/API零错误，单写者/相同配额/回执保护、显式回退和最终原值恢复及全部自有对象清理通过。启动记录错误和一次观察读写竞态均保留准确原件，原进程未重跑。

[CLI状态与可选启动安装通过](testing-final-v1-cli-supervisor-terminal.md)：26/26主检查、48/48子检查，两角色各新600秒SQL/API零错误；自然快照老化305秒、写锁/单Agent恢复、两种已知模板副本安装与拒绝保护、原值恢复及卸载和独立清理通过。P08.1按已验证模板范围完成；真实私有厂商脚本布局不支持时安全拒绝。P07.1其余逐字段组合仍待，不提前全项接受。

[P07.1完整输出组合1551失败](testing-final-v1-output-matrix-failed.md)：两角色均在首次50%约束状态上触发测试预期错误；三控制正确applied，既有约束警告使聚合状态为degraded。16主/2输出检查通过、其余10主/26输出未执行，另有2次未汇总断言失败。原600秒未通过，56登记实例及全部自有对象清理确认，17/52保持。下一步按准确源码修订测试语义并另行冻结新测，不改原件或SLA。

[修订输出1571](testing-final-v1-output1571.md)已冻结12输入、22项本地及原生只读准入通过，未启动。仅修正已知约束警告的聚合状态预期，保留三控制应用/读回及原600秒SLA；新56失败前置清理门槛，17/52保持。

[52项原任务审核](current-52-task-audit.md)当前17项按定义范围完成；[完整任务与历史](current-task-registry.json)保留原定义和失败。CLI其余状态组合、未来格式、镜像持久化、故障压力及其余具体待办按各项继续，不能用二进制维护代替。

[固定最终产物长期执行器](testing-final-v1-long.md)已冻结，24h observe → 同容器24h enforce → 七天新计时尚未开始。既有旧源码七天任务继续运行，其时长不能转记最终候选。未取得新候选长期及老化后验证，稳定发布尚未接受。

[环境矩阵](tested-environment-matrix.md)按实际报告声明；用户暂无额外厂商ARM和独立物理多盘节点，这些范围保留未验证。

## 保留的失败与边界

默认三项20%完整业务测试仍有SQL/API及停库超时；手动参考配额通过不能证明任意数据库20%负载性能。preview.4旧长期端口冲突失败、1448诊断执行器末尾旧计数导致 failed/exit1 均保持原件和失败判定；修订1465是独立新测通过。1498维护初稿在上传前发现导出目录错误，被拒绝且未运行，1501另行冻结修订。旧preview.4→5维护40/40及迁移48/48保留来源，不作为最终ELF新测结果。
