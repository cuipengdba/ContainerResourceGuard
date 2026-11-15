# 正式版本号候选：原路径业务终态

固定v1.0.0候选、产品源码ced4617，实际执行18/18通过。两个全新DBS/HISDBS原厂镜像克隆分别完成原生600秒、SQL/API零错误及原延迟/覆盖标准，实际物理备份、同步和独立恢复十项与PG端口拥有者八阶段均保持。此处是新ELF的实际结果，没有继承preview.5运行时间。

| 角色 | 通过/记录 | 原生实际秒数 | SQL次数/错误 | API次数/错误 |
| --- | --- | --- | --- | --- |
| normal-dbs | 9/9 | 600.263 | 301/0 | 121/0 |
| normal-hisdbs | 9/9 | 600.194 | 300/0 | 120/0 |

预算仍为原manual参考7.2CPU、memory.high=20001980416字节、读写64MiB/s和手动IOPS4096，外部8CPU/20GiB保持；没有新增memory.max。原镜像、启动链、真实挂载、原缓存程序、每容器一份Agent和原PG命令/超时均保持。控制值、journal仅三项所有权、实际嵌入版本/修订/二进制摘要独立核对。

22份白名单原件、353830字节逐项核对，独立复算23项证据断言；74条登记记录（58个唯一PID/start实例）、runner/两个driver、两个namespace及父叶cgroup均确认消失。端口扫描的原始partial状态保留，限定PG拥有者断言不能被解释为所有扫描完整。具体指标及每项真假见[机器终态](test-results-final-v1-full600-terminal.json)，[准确原件和独立终态观察](test-evidence-final-v1-full600-terminal.json.gz)，[冻结计划和执行器](testing-final-v1-full600.md)。

这是共享amd64/Linux5.14/单设备manual参考预算业务验收。默认20%完整业务失败继续保留，不能用本轮覆盖。另见[同一固定ELF原生284项结果](testing-final-v1-native-CI-terminal.md)。新产物独占24h基线+24h限额、至少七天及逐项发布审核仍待完成；稳定1.0尚未接受或发布。
