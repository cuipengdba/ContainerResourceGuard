# Agent 活动对照的生命周期资格

本轮已实现并实测仅供隔离测试使用的暂停/恢复工具。宿主机真实子进程资格 27 项通过；随后在原 DBS、HISDBS 镜像与路径各完成 16 项，共 32 项。原运行器、worker、六个 watchdog 均独立确认退出，两个 Pod 的叶组、父 cgroup 和 namespace 均已消失。[证据索引](test-results-agent-activity-qualification.json)及[独立重放结果](test-analysis-agent-activity-qualification.json)保留来源与清理检查。

这项结果使[固定 IO 限额下的 Agent 活动对照](plan-agent-fixed-io-comparison.md)具备生命周期工具前置条件。四臂 A1/B1/B2/A2 的完整业务执行器和测量尚未完成；本轮没有执行原生 600 秒性能验收、备份/同步十项内容或原 32 项重载压力矩阵，也没有证明 Agent 导致或排除了既有超时。产品程序和已发布包没有修改。

## 工具边界

工具默认 CLI 不执行信号。实际操作要求显式测试环境标记、Linux root、自己的 0700 根目录与 0600 所有权证明、容器内匹配标记、精确 namespace/Pod UID/容器 ID/cgroup，以及实际 Agent 的 argv、ELF 和 PID/start_ticks。目标必须是本轮容器 PID1 的子孙、独立于 PID1、数据库和缓存；每容器仍只有一份 Agent。

STOP/CONT 使用已固定实例的 pidfd；每次核对身份，暂停后检查全部线程状态和实际八项内核值。正常结束和异常退出均恢复同一 Agent。独立有界 watchdog 在控制方管道关闭或租约到期时恢复仍匹配的目标；它不是产品容器管理功能。宿主机演练实际强杀的是自己创建的测试控制子进程，没有强杀厂商业务进程。恢复边界不包括 watchdog 与控制方同时被强杀，任何四臂测量中租约恢复或提前结束都应判为不完整。

pidfd 的实例固定与避免 PID 复用语义参考 [Linux pidfd_send_signal(2)](https://man7.org/linux/man-pages/man2/pidfd_send_signal.2.html)。当前 5.14 测试使用 flags=0，没有使用较新内核的线程范围标志。

## 实际测量范围

| 阶段 | 实际覆盖 | 限制 |
|---|---|---|
| 宿主机 27 项 | 默认惰性、无权限标记与身份拒绝、正常/异常恢复、目标退出、控制值变化识别、租约恢复、控制方 SIGKILL 后恢复与清理 | 控制文件是私有普通文件，仅进程与 pidfd 生命周期是真实操作 |
| DBS/HISDBS 各 16 项 | 原业务启动、只读 CCG 挂载、独立缓存、七类目标拒绝、活动/暂停/异常三种 Session、SQL/API 与 PG/缓存身份、恢复原值 | 实际自有容器 cgroup；短生命周期资格，不是 600 秒性能样本 |
| 离线重放 | 冻结源码/计划/报告摘要、32 项精确名称、实际暂停样本和信号计数、watchdog、控制值及独立清理 | 不能替代真实四臂对照或扩大到未测环境 |

厂商资格使用原已通过的手动启动预算：CPU 7.2 核、内存 20001980416 字节、读写各 64MiB/s 与 4096 IOPS。活动与暂停之间八项内核值一致；最后由匹配产品程序 disable 回到运行时原 CPU 8 核、内存 20GiB、空 io.max，其他五项保持。此预算没有代替后续四臂所要求的 64700080/37470104 BPS、83/135 IOPS，后续不得改用本轮较高 IO 预算宣称正式对照通过。

## 保留的首轮失败

首轮在两镜像中各完成三项启动/缓存检查后，root 直接执行 psql 均返回 127；此时尚未打开任何活动 Session，也没有发出 STOP。首轮程序、计划和完整终态保留在索引中。修订仅将 SQL 检查改为原引擎验收使用的 `su - postgres` 登录环境；追加 root `psql --version` 诊断，实际确认两镜像均因找不到 `libpq.so.5` 失败。没有修改数据库参数、资源限额或业务 SLA。

修订终态的两个原始进程为 runner 812438/start_ticks 137520314、worker 812439/137520317。独立观察确认原实例消失、退出码 0，32 项全部通过；首轮也确认原进程退出、退出码 1 和自有容器清理。没有因观察超时重启同一轮任务。

## 复核入口

从完整源码仓库执行：

```bash
python3 tests/analyze-agent-activity-qualification.py
```

核验器拒绝“源码改变但沿用摘要”和“32 项摘要全通过但删除 HISDBS 实际暂停样本，即使重算所有外层摘要”两种合成负例。它只读证据，不连接节点或发送信号。安装包不包含 tests，使用[核验源码](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/analyze-agent-activity-qualification.py)、[Session 源码](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-agent-activity-session.py)、[首轮执行器](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-agent-activity-qualification.py)和[修订执行器](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-agent-activity-qualification-v2.py)时应检出完整仓库。

原 52 项任务、仅三资源独立百分比默认 20%、v1 跳过/v2 校验、日志保留、一容器一 Agent 和辅助故障不阻断原业务的要求保持。全部历史失败、原七天句柄及后置、正式 24h 对照、未测硬件和稳定版发布条件继续。
