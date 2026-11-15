# 原路径SQL等待诊断：两次失败与第三版冻结

## 当前结果

第二版1824已失败终止并独立复核清理，两角色各9项记录/8通过/1失败/4未执行。观察器在原DBS/HISDBS启动路径采到了实际Lock/relation及阻塞PID，也记录到注入8秒锁区间的SQL deadline；但psql调用未取到持锁PID，无法进行“准确holder=实际blocker”验收，不能算诊断通过。负载因检查失败在约19秒停止，未完成120秒，更不替代原18项/600秒。

[第二版终态及独立复算](test-results-controlled-sql-wait-v2-terminal.json)、[24个准确索引原件215628字节](test-evidence-controlled-sql-wait-v2-terminal.json.gz)、[第二版冻结计划](test-plan-controlled-sql-wait-v2.json)。两namespace/父叶cgroup及58条登记进程实例均独立复核消失；观察器与负载已为不同PID。正常停止标记未到达，两个缺失文件如实登记，观察器由本轮准确身份pidfd在紧急清理中停止，没有改业务PID1/Agent/cache。PSI六项全部明确unavailable，不能声称测得压力或压力因果。

第一版1816各7项启动通过，但观察器header后退出、0样本、未注入锁/未完成120秒；12项诊断未执行。其任意argv匹配和normal导出错误已在第二版修复。原14索引文件与10只读补取原件保留，重复辅助身份不冒充独立PID；[第一版终态](test-results-controlled-sql-wait-v1-terminal.json)与[原件](test-evidence-controlled-sql-wait-v1-terminal.json.gz)不删除。宿主PSI缺失不是已终止第一版容器确切异常的证明，旧观察器没有写出异常阶段/类别，原因边界仍保留。[第一版历史说明](development-controlled-sql-wait-frozen-v1.zh.md)、[第二版历史说明](development-controlled-sql-wait-frozen-v2.zh.md)中的未启动状态只表示当时。

## 第三版修复与启动前计划

第二版把SELECT pg_backend_pid、BEGIN/LOCK/pg_sleep/ROLLBACK放在一个psql -c字符串，只得到末条SQL的结果；[PostgreSQL14官方说明](https://www.postgresql.org/docs/14/app-psql.html)明确该行为。第三版改为同一psql连接连续两个-c：先独立输出pg_backend_pid，再运行原事务和8秒锁；仍只有一个持锁连接、一次8秒锁、原超时选项。必须得到一个数值PID且与等待时间线真实blocker相等，不能仅凭“看到锁”等价通过。

[第三版15项冻结计划](test-plan-controlled-sql-wait-v3.json)、[全部文本输入](../tests/controlled-sql-wait-v3/)、[准入结果](test-results-controlled-sql-wait-v3-preflight.json)、[原生24项故障检查](test-results-own-wait-pressure-faults-v3.json)、[原件](test-evidence-own-wait-pressure-faults-v3.json.gz)。Windows23通过、1项Linux专用符号链接检查跳过。准入重新核对两次失败的计划/全部来源/终态/归属清理及原前置业务记录；全新工具和输出身份，当前第三版尚未启动，发布后只启动一次，不自动重复到通过。

第三版观察器与第二版准确字节相同：必需CPU节流、内存计数和IO计数；PSI仅ENOENT记录unavailable，不填零，权限/格式错误或能力变化失败。2秒一条固定只读PG等待查询及本容器计数，PID1 start/成员摘要/组inode/device前后核对；固定异常阶段/类别/errno，不导出任意SQL/异常/连接/环境。900样本、16KiB行、4MiB总量、2KiB终态预留；私有目录0700/文件0600；正常停止为当前身份/单调时钟绑定标记，紧急信号只针对准确自有辅助入口。

原镜像、start.sh、软件/数据/缓存路径与7项启动检查不变，手动7.2核、memory.high20001980416、64MiB/s读写及手动4096IOPS、外部8核/20GiB不变。完整120秒负向窗口、运行10秒后唯一8秒合成表锁、SQL/API/超时/2秒与5秒采样/零错误/max5秒/p95桶1秒/98%覆盖、解锁后计数/API/OOM、辅助停止及八控制值检查都不变。负载应如实failed；六项诊断通过只证明受控错误可定位，不能抵销原1761 DBS错误。

## 发布门槛与归档

CRG产品源37ca44e0及候选ELF不变；仅CPU/IO/memory.high、各自百分比默认20、v1跳过/v2设置、无权限不阻断、每容器一对一、日志30天/1GiB保持。所有改动属于隔离辅助程序，preview.5资产不变，稳定1.0尚未接受。

原52定义/18既有范围声明保留，本轮归入P02.1/P02.2/P06.3/P10.2/P10.3。受控诊断后仍需预先冻结observe/enforce对照及新的原18项/各600秒，然后从零完成24h observe、同容器24h enforce、新七天、原老化后故障/恢复/升级/稳定包门槛。旧故障、旧源及旧时钟不转移。只读观察有额外查询和输出开销，不能声称零开销或只凭相关性推出历史故障原因。
