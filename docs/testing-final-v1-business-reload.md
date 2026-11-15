# 固定最终候选：同一Agent业务热重载补验

准确最终v1.0.0、源码`ced461705ebc27315a59aefe463f9b4af47130a3`、AMD64二进制`9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8`。协议及全部输入先冻结，原生只读准入已通过，尚未启动本轮业务或取得终态。覆盖P03.1/2/3/5相关当前候选证据缺口，不转记旧d370/d6或preview的运行结果。

沿用已通过最终候选18项的两角色原镜像、真实路径、原start/supervisor和独立CCG；各建立独立namespace顺序执行。先以既有manual参考7.2CPU、memory.high20001980416字节、读写64MiB/s和手动IOPS4096启动。Kubernetes8CPU/20GiB、另外五项控制保持。仅配置协调周期由默认15秒改为1秒用于原60秒重载观察；不是CPU开销回归。

原实际600秒SQL/API零错误、最大5秒、p95桶上界1秒、覆盖98%、64MiB数据、PG不重启，以及实际逻辑/物理备份、同步、独立恢复10项和8阶段PG拥有者诊断全部保留。worker、engine、端口诊断源码和原300/45秒启动、600秒、PG/停库超时不改。共享节点28GiB创建余量、8GiB运行余量及20GiB磁盘保持。旧七天任务不操作。

首版1425输入已冻结并保留在[原始执行输入](../tests/final-v1-business-reload-frozen/README.md)，但从未启动业务。执行前静态复核发现等价空白配置可能因状态去重不立即写文件；本修订仅在空白场景发出`crg reload`并要求request_id准确确认、hash/generation不变。资源移除等待restored结果进入稳定applied快照，仍在原60秒观察内；不把正确的日志去重或恢复中间态误判产品失败。新工具/输出/namespace均使用1429，原15项输入保持字节不变。

每角色13个观察：manual转CPU/内存/IO百分比30/30/100；三项分别25/29/80；IO101拒绝；半截JSON；重复键；临时缺文件；无writer的FIFO；ConfigMap式原子符号链接恢复；同策略空白变化；manual仅CPU移除自有high/IO；manual三项；再转百分比；回原manual。开始约31秒，此后每30秒触发，逐项最长观察60秒，不缩短完整600秒。第一有效切换必须与原30秒调度的备份引擎实际运行重叠。

IO100是原真实三次标定基准，非物理设备全速承诺：64700080/37470104 B/s；IO80为51760064/29976083 B/s。两次有效百分比CPU/内存分别为720000/600000（100000周期）及20001980416/19335249920字节。百分比只限BPS，移除原自有IOPS恢复真实原值，不按83/135 IOPS百分比设置。使用同节点同设备原实测v2 profile准确字节；仅复制复用，不造标定值，不在业务阶段再测速。持续核对字节与mtime。

每次核对全部8项实际控制、generation、accepted_hash、上一整份plan、journal所有权及同一Agent/PID1/CCG。无效配置保留上一份完整策略，明确degraded/rejected；FIFO不得阻塞读文件。IO空文本和全max行仅按四轴无限额的同一内核语义比较，其他设备行也必须完全相等，不能忽略额外限额。最终必须回原manual、Agent/业务未重启、原生业务及引擎通过，再独立检查登记PID/start、父叶cgroup及namespace清理。

CLI优先由准确源码原生unit/race另证；本轮沿原业务helper以文件配置启动，不伪称厂商CLI覆盖实测。无并发disable/物理掉电/CPU热插拔或老化后故障资格声明；这些仍按原任务保留。默认20%完整业务历史失败不改判；任何本轮失败原样归档，不自动重跑、加配额或放宽业务标准。

[固定计划](test-plan-final-v1-business-reload.json)、[原生准入](test-results-final-v1-business-reload-preflight.json)、[非二进制准确输入](../tests/final-v1-business-reload-frozen-v2/README.md)、[原最终候选600秒结果](testing-final-v1-full600-terminal.md)、[原52项](current-52-task-audit.md)。稳定1.0尚未接受，本轮计时不替代24h+24h/七天。
