# memory.high 当前操作文档核对

2026-11-13核对发现：main的配置页仍称三项百分比不写memory.high、使用memory.max下调规则；三分支运维页也没有区分high回收目标与历史硬限额下调预检。它们与已发布preview.4及用户明确要求不一致，本次修正文案。

README、配置页和运维页现在明确：memory_percent以及手动limits.memory_high使用memory.high；触达时进入回收/节流，可超目标。CRG不新增memory.max，保留外部/Kubernetes/祖先硬限额。high不直接触发OOM killer，但外部硬限额或宿主内存耗尽仍可OOM；不能任意释放活跃数据库内存。旧max别名和已拥有旧硬限额的恢复遵循[策略文档](memory-reclaim-policy.md)，不能把memory.max一律设成max。

配置页的默认自动标定、已发布版本表述也改为preview.4，手动模式继续不标定。main源码尚未回移，文档明确面向下载的preview.4；main内历史源码/配置示例通过不可变的已发布源码示例链接区分。历史测试结果、原52项、默认IO四轴语义和正在运行的手动对照均不改写。本次没有程序、发布附件或环境部署变更。

依据：[Linux内核cgroup v2 memory.high/memory.max接口](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory-interface-files)。本次只做文档一致性和链接/包校验；不能计作新的业务、回收压力或长期验证通过。
