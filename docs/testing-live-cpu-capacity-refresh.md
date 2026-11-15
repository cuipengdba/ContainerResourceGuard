# 在线CPU容量刷新：对照、修复和重新验收

当前结论：新生产源37ca44e0e24a0eaa14e52b5c8bbbda54c76364b0已在ARM64/Linux7完成56/56原生CPU热插拔检查，已合入release/integration-v1。main、compatibility和partition分支本次只同步证据/任务，未替换其旧运行时代码或发布包。完整新候选业务、原生矩阵与长期验收仍待，稳定1.0.0未发布。

## 需求与修复

一个容器一份Agent，按自己的动态cgroup身份工作。CPU、内存、IO分别百分比，默认各20%；新内存策略用memory.high，IO百分比按标定读写带宽，IOPS只留手动模式；不增加其它资源。辅助失败不阻断原业务，v1/混合/未知跳过写入，日志按天、保留30天且总量1GiB。

原循环虽重新发现环境检查身份，却丢弃新容量。旧候选ced4617在4核减为3核时20%仍维持0.8核，fresh doctor正确为0.6核。修复保留同身份/同目标的新环境，并同时更新Plan/Engine；容量来源失去信任时不沿用旧可信总数；身份变化仍终止写入。[实现与需求记录](development-live-capacity-refresh.zh.md)、[新构建身份](build-identity-live-capacity-fixed.json)。单元测试go test ./...通过；两架构静态ELF分别重复构建逐字相同。此CPU测试不能证明内存热插拔。

## 冻结对照与原始证据

驱动SHA256 dfcb84e1c01538c6b2efded31bffcdb162df3b4ad80cce465e2d6bb4dfe1ec44。旧、新候选使用同一驱动、两种外部上限、相同56项条件和10秒观测界限。运行期间Agent和PID1不重启。4次真实下线及4次上线，每次按实际在线CPU核数独立计算；紧外部0.1核上限始终保留，其它七项控制不改。两实例均检查八项原值恢复、没有OOM kill、归属进程/leaf清理及CPU掩码恢复。

| 运行 | 结果 | 边界 |
| --- | --- | --- |
| [旧版43759787440](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/43759787440) | 50/56，六项真实容量/配额失败；清理通过 | 旧ELF缺陷对照 |
| [修复43760116572](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/43760116572) | 56/56；全部归属清理通过 | ARM64，Linux7.0.0-1017-azure临时VM，非厂商业务 |
| AMD64旧版43758489795 | CPU sysfs下线返回EBUSY；8项启动/清理通过 | 无成功下线；原因未知，不计热插拔覆盖 |

[新计划](test-plan-final-v1-live-cpu-capacity.json)、[新结果](test-results-live-cpu-capacity-fixed.json)、[新准确ZIP及API摘要](test-evidence-live-cpu-capacity-fixed.json.gz)、[旧准确对照](test-evidence-live-cpu-capacity-v3-old.json.gz)。[驱动](../tests/live-cpu-capacity-v1/driver.py)只准独占临时GitHub VM，禁止在SSH业务节点下线CPU；[独立离线复核](../tests/live-cpu-capacity-v1/review.py)对提取出的原ZIP执行 --zip，旧版增加 --expect-failure。

首轮夹具错误调用不存在的plan命令，实际没有下线；[原件保留](test-evidence-live-cpu-capacity-first-fixture-error.json.gz)。第二轮ARM64已复现六项缺陷，但无写入的tight场景错误读取不存在的journal，导致清理中断；[AMD64/ARM64失败原件保留](test-evidence-live-cpu-capacity-v2-failures.json.gz)。v3仅允许五次样本均无journal、八项原值逐次不变的tight场景证明无操作；有写入场景仍须空journal。不得将v2整体说成通过。

## 旧长测已明确停止

原1728使用旧ced4617 ELF。确认新缺陷并独立验证修复后，于原节点UTC 2026-11-15T20:45:24Z向已核对PID/start_ticks/入口的原worker发SIGTERM，由原finally执行隔离夹具清理，未修改18项冻结输入；这不是未知原因自然失败。原任务正式记录failed/exit1，不能改写成成功。12项启动通过，约3107秒baseline负载内SQL/API均0错误，仅一周期，未达到任何完整24h、enforce或七天标准；结果不转移给新ELF。

[原生终态](test-results-final-v1-long1728-terminal.json)、[13项原终态文件、完整只读记录、冻结输入及独立清理证据](test-evidence-final-v1-long1728-terminal.json.gz)。原namespace、两leaf/父组和全部登记进程均独立确认消失，三协调进程也已结束。原1396及旧78失败历史保持。

## 继续任务

[新候选重新验收方案](testing-capacity-refresh-requalification.md)、[原生矩阵冻结计划](test-plan-capacity-refresh-native-CI.json)已单独冻结并派发，保持原284项及四环境条件。DBS/HISDBS原start路径、SQL、/test、备份/同步/独立恢复和短负载需用新ELF复验；之后再从零执行24h observe、同容器24h enforce、新七天及老化后验收。不能把本次56项或旧来源通过概括为上述全部通过。

原52项定义与18项既有范围完成声明不变，P06.3/P06.4/P10.3及长期门槛仍开放；无可用厂商ARM或独立多物理盘的边界保持。
