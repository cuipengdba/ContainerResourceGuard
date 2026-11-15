# DBS/HISDBS原路径受控SQL等待诊断完成

## 已验证的结果

第三版1830按启动前发布的冻结计划各执行一次，DBS/HISDBS各13/13通过（各7项原启动+6项新增诊断）。各完成独立120秒负向窗口，唯一8秒合成表锁实际造成SQL deadline；原负载正确保持failed。观察器真实Lock/relation中的阻塞PID与同连接psql准确持锁PID一致，事件时间区间重叠，解锁后SQL计数继续、API满足原标准、无新增OOM。不是正常业务18项通过，也不是原1761错误原因已经查明。

|角色|检查|原负载实际秒|预期SQL错误|持锁PID|时间线样本|API错误|API最大秒|锁前计数|解锁后计数|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|dbs|13/13|120.192|1|1745|65|0|0.008|96|176|
|hisdbs|13/13|120.155|1|1766|64|0|0.009|96|176|

[独立逐原件复算结果](test-results-controlled-sql-wait-v3-terminal.json)、[准确原件和原生终态](test-evidence-controlled-sql-wait-v3-terminal.json.gz)、[启动前15项冻结计划](test-plan-controlled-sql-wait-v3.json)、[准确文本来源](../tests/controlled-sql-wait-v3/)、[独立复算程序](../tests/controlled-sql-wait-v3/qualify-selected-originals.py)。全部选定索引原件26个/441991字节逐长度/摘要核验，source-map无缺失；两namespace/Pod/父叶cgroup及55条登记进程实例消失另行复核。准确主入口、PID/start、成员摘要和自身目标inode绑定，观察器与负载为不同PID。观察器按身份/时钟绑定停止标记正常退出，未向原PID1/Agent/cache发停止信号，八个控制值前后完全一致。

## 实现和适用边界

CRG生产源37ca44e0及AMD64候选ee4f0a14未改；原镜像、start.sh、软件/数据/只读CCG路径和业务配置保持。手动7.2核、memory.high20001980416、64MiB/s读写、手动4096IOPS，外部8核/20GiB保持；本试验不改变百分比模式的BPS-only定义。负载SQL/API/超时/采样/零错误/max5秒/p95桶1秒/98%覆盖与原数据校验方程不变，注入锁时预期failed不能被改成正常passed。

观察器每2秒读取自身CPU节流、内存及IO计数、固定只读PG等待查询；源字节与第二版相同。实际六项PSI全部unavailable（ENOENT），明确没有压力测量资格，不填零、不宣称无压力。必需计数和PG查询完整，查询错误0；最多900样本、16KiB行、4MiB总量/2KiB终态预留，目录0700/文件0600，固定异常阶段/类别/errno，未知字段不导出任意SQL/异常/连接串/环境。数据有采样与额外查询开销，非原子，不能仅凭相关性判断旧故障原因。

第三版同一psql连接先-c SELECT pg_backend_pid，再-c原BEGIN/LOCK/pg_sleep(8)/ROLLBACK，仍一个锁连接一次8秒锁；[PG14 psql说明](https://www.postgresql.org/docs/14/app-psql.html)解释单个-c多SQL只输出最后结果。原生24项辅助故障检查通过，Windows23通过/1项Linux专用符号链接检查跳过。它们是辅助程序检查，不增加原任务的完成声明。

## 全部失败仍保留

第一版1816观察器header后退出、0样本、未注入锁/未完成120秒，各原7启动通过、12诊断未执行。任意argv匹配误把--worker参数作为入口、normal导出分支错位的问题已修复；原14索引与10只读补取文件分别保留，重复辅助登记不冒充独立身份。旧观察器没写异常阶段/类别，后来宿主PSI缺失不等于确知旧容器异常原因。[第一版终态](test-results-controlled-sql-wait-v1-terminal.json)、[原件](test-evidence-controlled-sql-wait-v1-terminal.json.gz)。

第二版1824已采到锁等待/SQL deadline，但单个psql -c未输出前置持锁PID，各9项记录/8通过/1失败/4未执行；约19秒中断，未完成120秒，不接受精确holder归属。24原件与58登记进程归属清理独立核对，缺失停止标记如实列出。[第二版终态](test-results-controlled-sql-wait-v2-terminal.json)、[原件](test-evidence-controlled-sql-wait-v2-terminal.json.gz)。[第一版](development-controlled-sql-wait-frozen-v1.zh.md)、[第二版](development-controlled-sql-wait-frozen-v2.zh.md)、[第三版启动前](development-controlled-sql-wait-frozen-v3.zh.md)历史冻结说明中的“未启动”仅表示当时状态。

## 下一步与稳定发布

[固定次数observe/enforce业务对照设计](development-next-business-comparison.zh.md)已归档：DBS/HISDBS各observe/enforce一次、各原600秒，唯一CRG模式变量，缓存/外部限制/SQL/API/备份恢复不变。该文件只是待实现设计，未生成可执行冻结来源、未启动。对照不能冒充原18项正式复验；随后还要新原18项/各600秒，从零24h observe、同容器24h enforce、新七天及原老化后故障/恢复/升级/稳定包门槛。

原1761 DBS完整600秒失败、HISDBS9/9和DBS原因unknown不改变，不凭已知注入锁反推旧故障。全部52项定义/18项既有范围声明保留，本轮属于P02.1/P02.2/P06.3/P10.2/P10.3辅助诊断子任务。仅CPU/IO/memory.high、各自百分比默认20、v1跳过/v2设置、每容器一对一、无权限不阻断原启动、每日日志30天/1GiB要求保持。preview.5资产未改，稳定1.0尚未接受。
