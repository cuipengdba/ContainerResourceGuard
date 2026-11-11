# 版本化候选辅助故障终态

真实v1.0.0候选程序dbc48aa5，按[冻结计划](test-plan-versioned-candidate-faults.json)完成DBS/HISDBS各10场景，共20场景、108项检查通过。运行器退出0，Pod已删除，namespace独立确认不存在。[逐场景结果](test-results-versioned-candidate-faults.json)保留实际就绪和TERM时间、降级原因及来源。

覆盖程序缺失、无效配置、崩溃、卡住、忽略TERM、原supervisor回退、cgroup只读、profile只读、state只读、真实标定取消。原PG/API90秒、缓存45秒、TERM12秒，SQL/原ls探针、PID1及OOM检查未放宽。实际取消观察自有临时文件FD并核对程序和cgroup身份，经pidfd发送TERM后确认原控制和profile未写。profile只读不测速；cgroup只读仍可能先测速，不能声称所有权限失败都在测速之前退出。

本轮只在新程序自身[1800秒开销](testing-versioned-candidate-overhead.md)与[两角色各600秒业务](testing-versioned-candidate-business.md)通过并独立清理后创建Pod，旧开发版3a1的结果单独保留。原镜像、start.sh、PG参数、CCG只读挂载及真实路径保持，数据/配置/凭据/DCS使用独立测试背板。单独30%配置仅证明辅助隔离，未追认默认20%或自动30%持续性能。

本结果不替代实际老化数据故障、24h+24h、至少七天、两个已发布次版本维护及未测硬件条件。稳定1.0尚未发布。
