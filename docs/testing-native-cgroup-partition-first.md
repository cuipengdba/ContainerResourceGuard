# 原生控制器首轮：分区IO未通过

[运行前冻结计划](test-plan-native-cgroup-ci.json)首次执行两线、两种原生架构，共四格均未通过；[完整失败与原生程序摘要](test-results-native-cgroup-partition-first.json)保留。主线f2555b0及组合a0050c1实际均为Linux7.0.0-1017-azure、Docker28.0.4，各自本机原生编译执行，非模拟器。

每格前三项源码/本机ELF、本地Docker和scratch镜像检查通过，第四项真实三资源回读失败：CPU已为50000/100000、memory.max134217728B，io.max为空，状态degraded。数据目录实际是可见块设备上的分区，其自身dm/uuid、device/wwid、wwid均不存在；产品明确记录“无稳定UUID/WWID”，未伪造profile或把IO报告成功。其余五控制值保留。

此后CPU/IO负载、内存分配、崩溃重启、disable、新ID/自动标定复用及只读权限场景均未执行。四格的占位容器/cgroup、私有镜像与目录已正常清理并独立核对，不接触原业务节点或原24h基线。

[内核sysfs规则](https://docs.kernel.org/7.0/admin-guide/sysfs-rules.html)要求区分分区与磁盘、按实际设备树核实父级，不能按名称猜测。[内核块cgroup源码](https://github.com/torvalds/linux/blob/v6.19/block/blk-cgroup.c)中的blkg_conf_open_bdev还会拒绝partition设备号。只给分区补一个身份仍不能完成正确的控制设备映射，因此本次没有提交未完整验证的运行时代码。后续P04/P06需同时设计分区稳定身份、整盘控制目标、同盘多分区合并及祖先/现有profile冲突，然后另起实测；当前不宣称该组合支持分区IO。

下一轮拟用临时VM内独立新建、真实dm UUID的可丢弃文件系统验证控制器，先单独冻结夹具源摘要和清理条件。它不是本轮分区通过，也不代表物理多设备、ARM厂商业务或Linux6.x验收。原生基础race/helper/CLI与普通包CI的成功单独保留，不能替代本轮失败。
