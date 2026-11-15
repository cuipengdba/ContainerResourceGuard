# 原路径SQL等待诊断：失败记录与第二版冻结

## 当前结果

第一版1816实际失败，已终止并独立复核清理：DBS/HISDBS各原7项启动检查通过，12项新增诊断检查均未执行，观察器各写入header后以bounded_observer_failure退出，样本为0。未执行锁注入，也未完成120秒负载，不能算受控锁验证通过。原1761 DBS完整600秒SQL超时原因仍未知，稳定1.0未获接受。

[终态资格](test-results-controlled-sql-wait-v1-terminal.json)、[索引原件与只读补取原件](test-evidence-controlled-sql-wait-v1-terminal.json.gz)、[第一版启动前原始说明](development-controlled-sql-wait-frozen-v1.zh.md)、[第一版冻结计划](test-plan-controlled-sql-wait.json)。原14个索引文件120067字节均逐字节/摘要核对；旧协调器把诊断导出放在conflict分支，实际normal分支未执行，不能称完整计划证据已导出。另只读补取10个原始诊断文件16860字节，原索引/源/终态全部保留。两namespace、父叶cgroup和55条登记进程记录独立检查消失；DBS辅助登记含重复身份，55条不是55个独立有效辅助实例，Pod父组清理另有核验。

## 修复与边界

1. [后续宿主只读检查](test-results-kernel-numeric-wait-probe.json)观察到PSI文件不存在，已有CPU/memory.stat/IO/vmstat解析通过。宿主根组没有memory.events不等于业务叶组缺失。第一版未记异常阶段/类别，不能把宿主PSI缺失冒充旧容器确切失败原因。第二版对PSI仅ENOENT记unavailable及errno，不填0、不算测得压力；其它权限/格式错误、期间能力变化仍失败。CPU/内存/IO必需计数与实际PG锁归属仍为必需。新计划明确缺少PSI时压力归因未验证，不算旧强制PSI计划通过。
2. 原按任意argv出现脚本路径识别进程，观察器的--worker参数可能被当作负载主入口。第二版只接受Python argv[1]准确脚本，停止时同样复核；观察器与负载PID必须不同。回归检查覆盖这次误选及伪Python名称。
3. 第二版normal分支导出准确受控结果、原负载、时间线、停止标记与两个日志；故障检查明确验证分支和六个文件路径。缺少文件仍如实列出。
4. 观察失败追加固定阶段/类别/理由/数值errno，不导出任意异常、SQL、连接串、环境或凭据。每2秒一条本容器计数/固定PG等待信息；PID1 start、成员原件摘要和组inode/device前后核对。最多900样本、单行16KiB、总4MiB、终态预留2KiB，私有目录0700/文件0600。

CRG产品源37ca44e0及准确候选ELF未变。程序仅CPU/IO/memory.high、各自百分比默认20、v1跳过/v2设置、无权限不阻断、每容器一对一及日志30天/1GiB要求不变。全部改动属于隔离验收辅助代码。

## 第二版启动前冻结

[15项冻结输入/计划](test-plan-controlled-sql-wait-v2.json)、[完整文本来源](../tests/controlled-sql-wait-v2/)、[只读准入](test-results-controlled-sql-wait-v2-preflight.json)、[23项故障检查](test-results-own-wait-pressure-faults-v2.json)、[原件](test-evidence-own-wait-pressure-faults-v2.json.gz)。原生amd64/Linux5.14为23/23，Windows22通过、1项Linux符号链接检查跳过。已逐摘要上传到全新工具路径，准入保留原任务及前次失败终态/清理复核。当前第二版尚未启动，计划发布在先，之后至多启动一次；不自动重跑到通过。

原DBS/HISDBS镜像、start.sh、软件/数据/缓存路径和7项启动检查不变；手动7.2核、memory.high20001980416、读写64MiB/s、手动4096IOPS及外部8核/20GiB限制不变。原SQL/API/超时/采样/零错误/max5秒/p95桶1秒/98%覆盖不变。另开完整120秒负向窗口，在本轮合成表恰好一次持有8秒ACCESS EXCLUSIVE锁，预期原负载保持failed。六项新增诊断要求：独立辅助身份；真实锁会话；完整120秒按原标准失败且SQL事件重叠注入；PG实际Lock/relation与准确holder PID匹配；解锁后计数继续、API达原标准且无新增OOM；时间线按归属停止且PID1/Agent/cache及八控制值不变。

各角色13项即使通过，也仅是预期失败的诊断试验，不替代原18项/各600秒。不改变旧失败事实或原门槛。结束后逐字节取回选定原件，独立复算锁归属、资源值和清理。随后冻结observe/enforce对照及正常完整600秒，再从零进行24h observe、同容器24h enforce、新七天及原老化后故障/恢复/升级/稳定包门槛，旧源旧时钟不能继承。

本轮归入原P02.1/P02.2/P06.3/P10.2/P10.3子任务；52定义/18既有范围完成声明保持。历史冻结说明中的“尚未启动”只描述当时状态，本页为当前状态。PostgreSQL固定只读等待查询仍增加负担，不能宣称零开销；[PG统计](https://www.postgresql.org/docs/14/monitoring-stats.html)、[pg_blocking_pids](https://www.postgresql.org/docs/14/functions-info.html)及[cgroup v2](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)为接口依据。
