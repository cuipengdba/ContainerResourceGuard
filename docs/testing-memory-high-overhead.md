# memory.high 发布程序的稳定开销验证

按[冻结计划](test-plan-memory-high-overhead.json)，先接受 preview.4 的四组原生 88 项与八文件构建一致性，再在测试节点创建三个私有占位 PID1 容器：健康、指标与事件持续写入失败、真实只读 cgroup。每容器一个 Agent，每组预热 45 秒后实测 1800 秒，10 秒采样；单核 CPU ≤0.1%、RSS ≤20MiB、稳定状态写入间隔 ≥299 秒，健康写入 ≤8MiB、故障写入 ≤16MiB，零 OOM kill，进程身份和全部八项实际控制不漂移。宿主内存 8GiB、磁盘 20GiB 保留门槛保持。

内存按新要求设 memory.high=128MiB，运行时 memory.max=256MiB 保持；CPU=0.25 核，读写各 64KiB/s 和 8IOPS。只读场景的外部 IO 预算由私有测试夹具设置，不能称为 Agent 成功写入。每日 0600 日志需记录 v2 和 high-reclaim-throttle。

本次计划和程序摘要单独归档，旧硬内存策略的 1800 秒不计入。此项不包含 DBS/HISDBS 业务、标定成本或长期接受，结束还需独立核对清理。当前已冻结、尚未启动。

第一次准备在创建 Pod 前失败，原始[结果](test-results-memory-high-overhead-v1.json)保留：驱动误把 build-info 的完整说明值与短策略名比较，实际程序策略正确。第二次按四格 CI 所记录的完整值作精确比较，其他标准保持，见[新冻结计划](test-plan-memory-high-overhead-v2.json)；使用独立目录和命名空间，尚未启动。

第二次已启动并进入实际采样，固定程序摘要6088721c；仍须完整1800秒终态、exit0和独立清理后才能接受。

第二次已终态通过，见[完整结果及独立清理](test-results-memory-high-overhead-v2.json)：实测1800.0305秒，每场景181次采样；健康/导出失败/只读的单核CPU平均分别0.02389%、0.02278%、0.03111%，RSS最高分别10174464/10027008/10240000字节。状态写入最短间隔均≥300秒，写入量均低于原门槛，零OOM kill。只读场景保持降级，外部IO夹具不计为Agent成功。namespace、自有3个Pod父cgroup、3个叶cgroup及6个原PID1/Agent进程均经独立观察确认消失；runner已退出、exit0。业务等待门槛已解除，DBS启动中，不把本项当作业务或长期接受。
