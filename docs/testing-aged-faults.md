# 实际保留数据上的辅助故障执行器

[执行器源码](https://github.com/cuipengdba/ContainerResourceGuard/blob/ddad4be878f1e2a88a5de222a7d3396a61ce4bf8/tests/vendor-aged-faults.py)已实现，按[七天后计划](test-plan-aged-faults.json)等待原七天组件及其实际[恢复/重建/维护后置](testing-aged-postflight-execution.md)终态通过并清理后，再在同一数据目录上验证辅助故障。默认调用只读，不创建报告、锁或工作目录；真实七天仍运行时，即使传--execute也返回pending/退出2，不能提前执行。

另有明确分开的[短演练计划](test-plan-aged-faults-rehearsal.json)：使用已完成R51业务、R60恢复/重建/维护的实际64MiB保留目录，未创建空数据库替代。该短演练已启动，首个[固定观察](test-progress-aged-faults-rehearsal-start.json)仍在运行；20场景/152项是完整计划数量，尚未作为通过成绩。它不接受七天组件，也不关闭P10或稳定发布。

## 执行内容

DBS/HISDBS分别验证缺失、无效、崩溃、卡住、忽略TERM、原supervisor回退、cgroup只读、profile只读、state只读和真实标定取消，共20场景。沿用PG/API90秒、缓存45秒、TERM12秒及标定FD/程序/cgroup/pidfd身份条件。每个场景再核对原64MiB全量校验和与最终counter、PG未中途重启；缓存必须有本次新状态及唯一正确程序，旧status文件不算就绪。

原PG目录、原镜像/start.sh、PG参数/凭据、原缓存和真实容器路径继续使用；只复制小型辅助程序、配置和resource-state到本场景私有挂载。旧journal和disabled标记原样复制，覆盖新ID处理；原程序/配置/source journal保持以便最后逐项核对。state只读场景验证复制后的既有状态完全未改，不能因原有旧journal存在就误判失败或先删除旧状态。回退场景只替换私有CCG副本中的supervisor，原CCG仍只读并保留。

不复制/格式化原PG数据库，不改业务节点；结束按实际Pod/namespace UID清理隔离资源并保留数据。每天0600日志保留旧前缀并验证追加或新增文件；既有30日/总1GB规则不变。资源配置仅三个独立30%用于故障隔离，不能证明该比例或默认20%的持续业务性能。

## 门禁与验证

执行前核对冻结计划/执行器摘要、原七天实际进程与终态、后置36项和两次新ID/600秒、原目录inode/输入摘要/日志前缀、剩余空间/内存及无并发数据使用。所有Pod均检查，直接挂载该数据或其子目录、可写或有提权条件的父目录挂载拒绝；通用只读父目录监控要求只读、不可提权、非privileged、drop ALL且无SYS_ADMIN/ALL、不双向传播，不使用Pod名称白名单。

首次只读预检将节点只读根目录监控误判为数据使用者，已保留该拒绝记录并修正判定，未启动任何故障场景。修正后8项Linux自检全部通过；真实长门禁及提前--execute均pending且没有工作目录/namespace，短演练前置通过。合成测试覆盖报告缺项/重复/错误、新ID、模式混用、并发挂载、源文件复制/符号链接、辅助挂载隔离和提前执行，无一项替代真实七天终态。

实际执行需Linux root与CRG_AGED_FAULTS=authorized-disposable-test-node-only，--execute前再次只读校验并独占创建新工作目录。这是授权测试节点的验收驱动；产品仍严格一容器一Agent，不管理其他容器，不依赖Kubernetes API。
