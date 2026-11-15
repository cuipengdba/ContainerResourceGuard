# 固定最终ELF三场景30分钟开销

P07.4/P09.4的准确最终候选补验，三场景已各完成实际1800秒测量和181份样本，原门槛通过，独立复算及完整清理已确认，见[终态报告](testing-final-v1-overhead-terminal.md)。下列启动快照按历史时点保留。源码`ced461705ebc27315a59aefe463f9b4af47130a3`，嵌入v1.0.0，ELF`9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8`。与旧preview.4/旧硬上限策略的开销结果分开记录，不继承其运行时间。

三份独立占位PID1容器：正常、metrics/events持续指向受保护marker的符号链接故障、真正只读cgroup挂载。每容器一份最终Agent，原厂镜像只作shell运行时，不启动DBS/HISDBS或缓存业务。测试使用已验证supervisor/helper，原业务与旧七天进程/控制不操作。

保持既有原门槛：预热45秒，连续测量1800秒，每10秒采样；15秒协调周期，单核CPU平均≤0.1%，RSS采样最大≤20MiB，稳定状态写入最小间隔≥299秒，正常Agent写入≤8MiB、故障≤16MiB，零新增OOM kill，PID1/Agent身份及八项实际控制全程保持。手动0.25核、memory.high128MiB、读写64KiB/s与手动8IOPS；运行时memory.max256MiB保持。只读场景IO约束由测试夹具只向其自有叶组设置，不是Agent成功写入。

节点保留8GiB可用内存和20GiB磁盘，真实低IO/输出失败、daily0600/v2/high日志及marker不变均须接受。结束还需独立复算原始样本、确认runner/worker与全部登记PID/start和namespace/父叶cgroup消失。CPU/RSS/写入只计Agent，不代表整个节点或采样器成本。

本轮在共享amd64/Linux5.14/单设备节点进行，旧版七天任务继续；不称独占、不作为业务性能、默认20%通过、24h+24h或七天验收。固定最终ELF284原生控制资格先决已核对。执行器仅替换固定身份/当前先决条件、增加UID清理与进程登记，测量主体和所有判定门槛保持。[准确计划](test-plan-final-v1-overhead.json)、[只读预检查及可逆适配清单](test-results-final-v1-overhead-preflight.json)、[非二进制准确执行文件](../tests/final-v1-overhead-frozen/README.md)。

首个实际快照中runner/worker命令与PID/start匹配，三份PID1/Agent均存在、程序摘要准确且八项控制符合计划，各只有1份初始样本，不能算开销通过。[启动身份](test-start-final-v1-overhead.json)与[准确原件](test-evidence-final-v1-overhead-start.json.gz)保留。首个外部启动器因换行转义在Python解析阶段失败，未创建launch记录；缺失记录的只读观察也保留。修正启动器并逐项确认无guard/log/worker/output及无对应活进程后，才唯一启动实际runner。测试程序、计划、二进制和全部门槛未变，没有发生第二次测量。
