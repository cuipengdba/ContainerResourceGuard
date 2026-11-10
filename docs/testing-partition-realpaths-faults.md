# 分区组合候选：真实路径辅助故障终态

当前未发布组合d3706f3、AMD64程序3a1ce7dbf5630f8f1c823005ceb4958653c6c235b2ba5026956ca6597f1926f9，按[冻结计划](test-plan-partition-realpaths-faults.json)完成DBS/HISDBS各10场景，共20场景、108项检查通过。运行器退出0，全部测试Pod与namespace独立确认清理。[逐场景结果](test-results-partition-realpaths-faults.json)保留程序来源、就绪/TERM时间和降级原因。

覆盖程序缺失、无效配置、崩溃、挂起、忽略TERM、原supervisor回退、cgroup只读、profile只读、state只读和实际标定取消。保持原镜像/start.sh/数据库参数/容器路径及只读原缓存挂载；测试目录、数据、凭据和网络独立。只有当前同程序两格600秒业务通过并清理后才创建本轮Pod；正式基线及固定d6候选保持原状态。

PG/API总90秒、缓存就绪后45秒、TERM从请求起12秒的原条件保持，SQL、原ls探针、PID1与OOM检查通过。cgroup只读记录真实degraded并保持全部原控制；profile只读确认输出不可写，不测速；state只读拒绝建原值状态和测速/控制写入。实际取消在观察到Agent持有自有标定临时文件且程序摘要匹配后通过pidfd发送TERM，核对原控制/profile未写，并使下次配置无效以防重试。cgroup只读仍可能先测速，不能描述成所有无权限都在测速前退出。

本轮仅使用三个独立30%参数做辅助隔离短测，不能证明自动30%持续业务或默认20%性能。默认20%失败、旧7638/d6的40场景216项、当前d370手动64预算各600秒、旧fc2正式observe和固定d6后续enforce分别归档。真实v1硬件、ARM厂商业务、独立物理多盘、24h+24h与至少7天条件继续保留。

[先前9场景49项中间观察](test-progress-partition-realpaths-faults.json)保留其时刻，不作为最终结果。当前故障终态和清理满足后，方可按[独立维护计划](test-plan-partition-realpaths-maintenance.json)执行升级/回退；维护结果另判，当前组合尚未正式发布。
