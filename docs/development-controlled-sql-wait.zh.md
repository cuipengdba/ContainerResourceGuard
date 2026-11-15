# 原路径受控SQL锁超时与只读压力时间线

## 冻结状态及要求归档

已实现每次隔离测试只观察一个容器的有界时间线，辅助程序不是CRG产品Agent。CRG生产源仍37ca44e0e24a0eaa14e52b5c8bbbda54c76364b0，准确AMD64候选ELF摘要ee4f0a140dd7fc1b0435298cd7ee673eedb0eaea6be9f79971d565f5f181308c；三资源、外部硬上限、每容器一对一与无权限不阻断业务要求不变。原1761 DBS失败仍未知，未因开发诊断而撤销。

[冻结计划](test-plan-controlled-sql-wait.json)、[驱动/协调器及全部文本输入](../tests/controlled-sql-wait-v1/)、[原生准入](test-results-controlled-sql-wait-preflight.json)、[故障验证结果](test-results-own-wait-pressure-faults.json)、[原件](test-evidence-own-wait-pressure-faults.json.gz)。15输入已在新测试工具目录逐摘要校验；原1728显式停止及1761整体失败/归属清理重新验证，节点Ready且无Memory/Disk/PIDPressure、无冲突夹具。当前尚未启动本轮Pod/业务测试，以下为冻结前记录。

Windows最终17通过、1项Linux O_NOFOLLOW符号链接停止文件检查跳过；原生amd64/Linux5.14最终18/18通过。更早16项是加入停止标记前的旧来源，不当作新18项叠加。验证覆盖计数/PSI/IO格式及边界、未知字段隐私、后端PID与阻塞数组、PID1重用/成员迁移/cgroup inode变化拒绝、根组及外容器拒绝、源摘要先验、文件长度及符号链接拒绝、行/总量/终态预留、停止标记身份和当前时钟窗口。

## 时间线实现

在原镜像Python2/3中只加载准确工作线程的libpq客户端四个函数，不执行其main或任何工作负载SQL。每2秒读取本容器CPU节流、memory.current/events/stat、IO字节/次数及CPU/内存/IO PSI；宿主PSI和少量vmstat明确作为共享节点指标。固定只读pg_stat_activity/pg_blocking_pids查询仅选本轮两合成应用，排除观察器自身；保存数值PID、查询年龄、固定状态/等待标签与阻塞PID，不导出SQL文本、连接/HTTP内容、凭据、环境或任意异常文本。

每个样本前后复核PID1 start、成员原件摘要和自身目标inode/device；拒绝根组、混合/v1、外容器或身份变化。只观察自己的CRI叶组，绝不写cgroup。查询1秒、连接沿用原5秒；最多900样本、每行16KiB、文件4MiB，并预留终态。新私有输出目录0700、文件0600；未知等待标签转other，不宣称覆盖所有PG等待分类。

正常结束使用新私有目录中的原子停止标记，绑定run-id、PID1 start、成员摘要及本轮单调时钟窗口；避免信号中断正在进行的观测查询。紧急清理仅对本轮明确entry/PID/start/组成员核对后的pidfd发信号，绝不向业务PID1、Agent或缓存程序发信号。只读观察仍有额外查询/读取/输出开销，样本不是原子快照，不能据此宣称零开销或单靠相关性判断旧故障原因。PG官方也提示频繁pg_blocking_pids调用会短暂影响锁管理器：[PG14动态统计](https://www.postgresql.org/docs/14/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW)、[阻塞PID函数](https://www.postgresql.org/docs/14/functions-info.html)、[cgroup v2接口](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)。

## 本轮负向真机计划：不替代原600秒

在两个新namespace依次创建DBS/HISDBS原镜像，沿用原start.sh/软件与数据挂载路径、只读原缓存程序、手动7.2核、memory.high20001980416B、读写64MiB/s和手动4096IOPS，以及外部8核/20GiB硬上限。每角色原7项启动/资源/日志/单实例门槛原样保留。

随后运行相同失败诊断工作线程，另开120秒负向窗口，不运行物理备份周期，不是将原600秒缩短。原SQL、2秒/5秒采样、零错误/max5秒/p95桶1秒/98%覆盖及数据校验方程一字未改；本轮要求原生负载如实报告failed。运行10秒后，唯一新连接仅对本轮crg_soak_<runid>.fixture持有一次8秒ACCESS EXCLUSIVE锁（申请锁2秒、该会话语句15秒、exec22秒）。不改业务PG配置、资源或原表。

每角色增加6项诊断检查：自身观察器/负载归属；唯一8秒锁会话结束；完整120秒原负载保留failed并记录重叠注入窗口的SQL deadline；事件区间内真实Lock/relation与准确holder PID匹配；解锁后SQL计数继续增加/API原标准/OOM不变；有界时间线按归属标记退出且原PID1/Agent/cache和八控制值不变。任何额外未知SQL失败、API错误、观察缺口或清理不明保持失败，不自动重跑到绿灯。

两角色各13项（7启动+6诊断）即使全通过，也只是预期失败的诊断资格，不能代替原18项/两角色各完整600秒；不宣称1761底层原因已知。每角色结束后独立检查Pod/namespace/父叶cgroup和登记进程实例消失，再进行下一角色，全部原件按索引导出、核对和归档。

## 原任务与后续

本轮归入原P02.1/P02.2/P06.3/P10.2/P10.3子任务，保留全部52项定义及18项既有范围完成声明。下一步实际执行并独立复算本轮受控负向试验；随后预先冻结observe/enforce固定次数对照与正常业务时间线，定位原问题，再进行原18项/各600秒。正常业务门槛关闭后从零执行24h observe、同容器24h enforce、新七天及原老化后故障/恢复/升级/稳定包门槛。旧失败或旧源时钟不能继承，稳定1.0尚未接受，preview.5资产不变。
