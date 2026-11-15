# 原1448诊断任务：汇总计数错误终态

原协调器及两个driver均按失败退出1，原phase保留failed，不重标。实际20项主检查均通过；失败来自新增第10项后末尾仍用旧9项总数。全部原件、源码摘要和独立清理已核对，准确计数与整体phase分别保留。

| 角色 | 主检查 | 诊断子检查 | 原生秒数 | SQL次数/错误 | API次数/错误 |
| --- | --- | --- | --- | --- | --- |
| normal-dbs | 10/10 | 19/19 | 600.367 | 299/0 | 120/0 |
| normal-hisdbs | 10/10 | 19/19 | 600.311 | 301/0 | 121/0 |

诊断标准输出及0600本地文件、白名单/敏感标记排除、已有文件/链接/状态/profile拒绝覆盖、全部8实际控制与journal/Agent/PID1/缓存/PG保持均由原module执行并在准确报告中保留。内核memory.pressure与memory.stat.hugetlb缺失明确不可用；gauge分时变化不强求相等，不造重叠总量。实际业务均通过原600秒SQL/API零错误、最大5秒/p95桶上界1秒/覆盖98%、真实备份/同步/独立恢复、PG未重启与端口拥有者核对。

22份准确原件共419288字节。独立观察确认runner、两个driver、71条登记进程记录（55个唯一PID/start实例）、两个namespace及父叶cgroup消失。协调报告摘要 86ac9a71e30459bf74abdb6a848eb4c65be19388986a8601ac133a425a5e55c8。诊断子检查与嵌套引擎内容检查不重复累计到主检查。

修订1465只更改末尾汇总从旧常量9改为冻结计划计数，并增加原失败终态/20项实际通过和完整清理守卫；新ELF、诊断模块、worker/engine、额度和全部业务标准不变。原任务原件归档且新原生只读准入通过，尚未启动修订轮业务；必须新跑完整600秒及清理，不能继承本轮计时。P05.1/P07.2仍等待新轮终态。

[原计划](testing-final-v1-diagnostics.md)、[失败终态复算](test-results-final-v1-diagnostics-counter-failure-terminal.json)、[准确原件](test-evidence-final-v1-diagnostics-counter-failure-terminal.json.gz)、[根因及修订](testing-final-v1-diagnostics-counter-fixed.md)、[新准入](test-results-final-v1-diagnostics-counter-fixed-preflight.json)。稳定1.0仍未接受。
