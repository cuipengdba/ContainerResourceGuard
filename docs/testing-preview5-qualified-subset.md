# preview.5 工程预发布的已验证范围

发布类型为工程预发布，准确程序源码ced461705ebc27315a59aefe463f9b4af47130a3、内置版本v1.0.0-preview.5；amd64字节与正在运行的真实业务矩阵相同。CPU/内存/IO各默认20，memory.high、带宽百分比和手动可选IOPS按最新用户选择；[策略](io-bandwidth-policy.md)、[版本说明](releases/v1.0.0-preview.5.md)及[准确工程CI](test-results-IO-bandwidth-CI.json)分别记录。

| 当前完成范围 | 结果 |
| --- | --- |
| 原生两架构实际Cgroup / Linux6.8及7.0同盘双分区 | 52 / 180项通过 |
| 原生ARM64测试事件 | 240项通过，原生ELF183 |
| 新程序、原DBS镜像/路径、空配置20% | 完整36项通过，三次受控就绪58.60/85.87/83.43秒 |
| 三次重建ID、自动profile复用、单Agent、原探针 | 全部通过；原300秒、缓存45秒及原删除门槛保持 |
| 64MiB数据/128标记、逻辑备份、独立数据库恢复 | 全部通过；不冒充物理备份/同步 |
| disable及自身隔离清理 | 八项原值恢复；namespace、三组父叶及95个登记进程实例独立确认消失 |
| 四组144项完整矩阵 | 仍运行；HIS20首启已就绪，其余依赖步骤未接受 |
| 两架构交付程序 | 固定Go1.27.3独立重复构建逐字节一致；本地构建不宣称GitHub签名证明 |

节点2026-11-13T15:24:52.434826+00:00的[逐项分析](test-results-preview5-qualified-subset.json)及[精确原件](test-evidence-preview5-qualified-subset.json.gz)包含五份134329字节的DBS报告、驱动日志、空配置、IO profile与逐日日志、读取脚本及独立清理。三个新ID的原始journal只新增cpu.max/memory.high/io.max；IO仅读8408293/写7905573Bps，IOPS保持max，外部20GiB memory.max不变。profile三样本中位数和各次主机CPU/MemTotal换算已独立复算，profile摘要跨重建相同。实际标定离散度警告保留，不把共享设备测量当成保证吞吐。

## 归档工具缺陷与补充

冻结1129驱动实际目录为preview5-role-percentN-startup，原runner导出仍引用preview4-role-N-startup。因此原runner的导出会缺少profile/配置/逐日日志；原17项结构检查没有覆盖目录映射。保留冻结源与原索引，不修改或重启测试。独立[只读补充读取器](../tests/bandwidth-percent-supplemental-reader.py)及[已完成组读取器](../tests/bandwidth-percent-completed-case-reader.py)仅访问固定四组已终结的实际私有测试目录，绑定原报告摘要、进程身份和文件原字节；本轮先读取已完成DBS20。10项[本地边界检查](test-results-bandwidth-supplemental-reader.json)通过，包括目录映射、非终态/摘要/越界/超大/多链接/非UTF8拒绝。未声称这些本地检查已在Linux运行；实际DBS读取与95进程清理已在测试节点完成。

后续四组终态时另外导出完整实际证据，原runner的缺项继续保留，不能把取证补充说成业务重跑或降低144项门槛。本次先以已完成工程和DBS20范围提供preview.5，其它三组及原完整业务/物理备份/同步/600秒/正式迁移/独占24h+24h/七天老化/硬件门槛继续，不将旧源码时间转给新源码。原52项完成声明和全部历史失败保持，稳定1.0未接受。
