# 最终候选长期测试的独立准入与事件记录

> 当前终态：原1396已在baseline失败结束，未达到24h/七天。[原始终态与后续任务](testing-final-v1-long1396-terminal.md)。以下内容保留原冻结/启动时点。


状态：原16项冻结输入及最终ELF保持；原生只读preflight=ready、无其他一次性业务Pod，其后已唯一启动并进入baseline observe，尚未达到长期门槛。当前18/52、稳定1.0未接受，公开preview.5不变。

沿用[原24小时+24小时+新七天协议](testing-final-v1-long.md)，同一正式1396目录、namespace、准确16项源摘要和600/长测原标准；不重建/重新上传候选或改写旧78。准入包装器验证原16项、精确已通过1615主报告SHA、原runner/driver/登记进程退出及父/叶不存在，再执行原预检与独立节点准入。只接受单节点Ready、三种压力False、空闲至少max(20GiB,文件系统15%)、两原厂镜像的精确digest与原tag；帮助程序及其已核对镜像计划也SHA绑定。唯一O_EXCL launch.guard保护，原runner PID/start和准确启动源另行记账；观察超时不允许重启原任务。

旧20261110基线与旧78已在本次查询前消失，独立CRI/cgroup/proc核对通过；未向其发信号或执行删除，源fixture、镜像tar和报告保留。当前就绪不代表未来压力不会发生；缺空间、镜像变化、其他业务夹具再出现等仍会被实际入口拒绝。

为避免故障后丢失事件，另加隔离测试专用只读记录器，与正式runner分别登记PID/start。每60秒查询本namespace Pod/事件及单节点条件，记录磁盘余量、容器退出原因/时间；事件按UID/resourceVersion去重，敏感字段过滤，日志UTC每日文件、累计64MiB和12天安全边界。它只向自有观察目录写日志，不控制cgroup、部署业务Pod、发信号或恢复服务；观察器故障不停止/重启正式业务。它属于额外测试证据工具，原16输入业务程序不变，独立源SHA公开；不是产品中的多容器管理器，CRG仍每容器独立一Agent。

长期阶段严格为baseline observe86400秒/4周期→同容器enforce86400秒/4周期→新acceptance604800秒/28周期，至少777600秒。各阶段仍须零错误、最大5秒、p95桶上界1秒、98%计划覆盖、内容完整及原进程身份，原审计器独立复算；启动及运行中快照不计时长通过。旧source/memory.max的78任务时长不继承，当前memory.high不承诺全系统绝不OOM，外部硬上限保持。

[准入就绪原件](test-results-final-v1-long-ready-node-admission.json)、[精确绑定](test-binding-final-v1-long-launch.json)、[唯一启动包装器](../tests/final-v1-long-admitted-launch.py)、[只读记录器](../tests/final-v1-long-readonly-recorder.py)、[独立观察器](../tests/final-v1-long-readonly-observer.py)、[1615准确终态](testing-final-v1-output1615-terminal.md)、[唯一启动](test-results-final-v1-long-admitted-launch.json)、[首份baseline快照](test-results-final-v1-long-first-baseline-observation.json)。
