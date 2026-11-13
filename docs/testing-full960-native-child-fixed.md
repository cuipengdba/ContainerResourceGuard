# 子进程句柄修复后的完整终态

内存百分比继续只写`memory.high`；外部`memory.max`保持。CPU、内存、IO独立百分比及各默认20%、v1跳过、权限不足继续原业务、单容器单Agent和每日/30天/1GB日志策略保持。[preview.4](releases/v1.0.0-preview.4.md)八份下载附件、标签、发布内容与生产程序未变。

[宿主14个真实子进程/15用例及原工厂17项](testing-native-child-lifecycle.md)通过后，新隔离任务按原业务core/native worker准确字节、全部driver函数AST与原32项标准执行。原两角色各600秒、11区间、原配额、SQL5秒/API4秒socket、零错误、覆盖、引擎内容及清理条件均未放宽。此次只修正诊断器对实际原业务子进程句柄的保留和查询，不修改业务成功标记。

## 结果：业务失败，BPF与私有通道诊断通过

计划32项，实际记录29项，29项通过；DBS原native退出1导致三项后置业务检查未执行，不能将29/29称为32项通过。DBS实际600.353925秒，SQL5次错误、API0错，SQL覆盖率0.976667也低于原0.98；HISDBS实际600.232693秒，SQL/API0错。两角色均完成11区间。本轮整体业务失败，不能用前一轮通过结果覆盖。

| 角色 | 原业务秒 | SQL错 | API错 | 原角色阶段 | BPF诊断通过 |
| --- | ---: | ---: | ---: | --- | --- |
| v10-dbs-bw64 | 600.353925 | 5 | 0 | failed | True |
| v10-hisdbs-bw64 | 600.232693 | 0 | 0 | short-acceptance-passed | True |

两角色捕获的原业务子进程各恰好一次、实际已退出，分别保留退出码1/0，原工厂全部诊断检查通过；独立30项也通过。修复没有把DBS失败转换成成功。私有FIFO读取线程、FD和目录严格清理，正式导出两份JSONL；原始流与已准入流无丢失/incomplete，边界原样保留，40个挂接程序、1个关闭控制程序及7个map、一秒准入排空/150ms perf排空、原事件/报告/映射预算均保持。新的固定作用域ELF重新编译，不称与旧ELF字节相同。

## SQL失败的现有证据

五次错误均为原`sql-readiness-deadline`，原5秒时间窗保留。首个失败窗口内，五个同backend采样为`LWLock/WALWrite`；后四窗口各五个同backend采样为`LWLock/BufferContent`。它们与真实high30→20压力、释放及返回30区间有时间重叠，但单靠重叠不能证明资源限额或某次日志write是原因。原采样没有测得blocking_pids，SQL和/proc分别读取非原子；内核栈实际EACCES不可读，不推断具体写回栈或完整阻塞链。

原native诊断另记录`diagnostic_complete=false`、`pg_wait_errors=5`，没有丢弃请求或PG样本；这一不完整状态原样保留。BPF/私有通道的30项通过不等于所有原生等待诊断完整，也不等于业务通过。后续应先按同一请求/后端和压力窗口核对原件，区分已观测等待、缺失数据与因果结论；不盲目重跑、增加超时或放宽资源预算。

## 原件与清理

[完整结果JSON](test-results-full960-native-child-fixed.json)、[全部原件](test-evidence/full960-native-child-fixed.json.gz)及[冻结接线源码](../tests/full-pressure-native-child-fixed-frozen-v5/full-pressure-integration.py)公开。正式清单35份原件，共49549278字节，按长度、EOF、SHA256逐份实际下载；原始业务报告、原native请求/PG样本、全部BPF流/summary、注解、观察、冻结源码/manifest和离线分析均保留。三个ELF仅公开长度与摘要。任务自然退出1，无热改或重启；59个注册进程实例、96个BPF对象、namespace和叶/父cgroup独立确认消失。

前一篇[运行中快照](testing-native-child-lifecycle.md)只代表其观察时点，不作为当前通过声明。[950的业务32通过但原工厂判定失败](testing-full950-bytecode-export-fixed.md)、[930清理失败](testing-full930-private-admission.md)、831和更早超时/丢失原件不重评。实际OS线程号复用、默认20%业务、正式24小时、七天604800秒/28周期与老化、环境和实际已发布次版本迁移等原条件继续。原52项定义与未完成声明保持，稳定1.0未接受。
