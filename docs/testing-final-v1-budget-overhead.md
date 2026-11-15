# 最终ELF不同有效限额开销补验

固定源码ced4617、v1.0.0 ELF 9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8。7项输入冻结，原生只读准入通过，尚未创建夹具或启动计时。P09.4仍待实际终态。

每容器单独Agent、独立父叶cgroup，两个占位PID1夹具：CPU0.5/high192MiB/双向128KiB每秒/手动16IOPS，以及CPU0.75/high224MiB/双向1MiB每秒/手动128IOPS。外部1CPU/memory.max256MiB由夹具设置，CRG不新增memory.max。两档均正常开启本地metrics/events，与已完成最终1404低IO健康档0.25CPU/high128MiB/64KiB每秒/8IOPS保持相同导出配置；不能把故障标签算作不同预算。

保持原15秒周期、45秒预热、至少1800秒稳定测量、每10秒采样，工程阈值单核CPU≤0.1%、RSS≤20MiB、状态持久化间隔≥299秒、健康写入≤8MiB、OOM增量0。原300秒状态去重调度保留299秒观测容差，不能为了过关省略必要日志。持续核对一对一Agent/PID1身份和全部8项实际值。共享节点可用内存8GiB、磁盘20GiB保护不变。既有1404低IO和持续导出失败/实际只读挂载各1800秒原件保持，不继承其计时。

只读准入可在当前诊断业务运行时完成；实际启动必须等诊断任务终态归档、登记进程/namespace/父叶cgroup清理，且没有下一组诊断业务正在运行，避免这组新测试与该业务互相干扰。旧七天任务不修改。数据只代表共享节点Agent自身CPU/RSS/写入；不能声称排除系统干扰的因果性能对比、厂商业务性能、长期老化或默认20%任意负载保证。完整新1800秒、两组真实控制、独立重新计算及进程/cgroup/namespace清理通过后再判断本项。

[计划](test-plan-final-v1-budget-overhead.json)、[原生准入](test-results-final-v1-budget-overhead-preflight.json)、[可逆适配](test-adapter-final-v1-budget-overhead.json)、[准确输入](../tests/final-v1-budget-overhead-frozen/README.md)、[已有低IO/持续异常终态](testing-final-v1-overhead-terminal.md)。当前未启动，稳定1.0未接受。

不同有效额度开销补验于节点2026-11-15T10:04:27.183865+00:00通过原1448失败原件/清理、新1465通过/清理及原1404准确报告守卫后唯一启动。独立活体快照确认两档各自原Agent/PID1、实际三项额度及同一最终ELF；45秒预热后新计1800秒，尚未接受。额外[启动守卫](../tests/final-v1-budget-overhead-launch.py)及[观察器](../tests/final-v1-budget-overhead-observe.py)不替换7份冻结测量输入。[启动快照](test-start-final-v1-budget-overhead.json)、[准确原件](test-evidence-final-v1-budget-overhead-start.json.gz)。已完成14/52项及稳定发布未接受保持。
