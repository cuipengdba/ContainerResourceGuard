# 版本化候选的稳定开销终态

v1.0.0候选AMD64程序dbc48aa5，按[冻结计划](test-plan-versioned-candidate-overhead.json)完成45秒预热后的实际1800.030404秒测量，三场景全部通过；运行器退出0，namespace独立确认不存在。[逐场景结果](test-results-versioned-candidate-overhead.json)固定实际程序、来源、阈值与范围。此前[固定早期观察](test-progress-versioned-candidate-start.json)保留，不替代本终态。

| 场景 | 样本数 | 单核平均CPU | 最大RSS | Agent写入增量 | 状态最短写入间隔 |
|---|---:|---:|---:|---:|---:|
| healthy | 181 | 0.021667% | 9592832B | 155648B | 300.000s |
| export-failure | 181 | 0.022222% | 10477568B | 45056B | 300.000s |
| readonly | 181 | 0.032222% | 9830400B | 1138688B | 301.037s |

全部样本核对唯一Agent/PID1身份、进程cgroup关系及8项实际控制；只有CPU/内存/IO接管，另5项原值保持。每日0600日志必须记录v2；导出失败持续unavailable且不破坏标记，实际只读cgroup持续degraded，无新增OOM。原CPU≤0.1%、RSS≤20MiB、健康写入≤8MiB/故障≤16MiB、状态写入间隔≥299秒等门槛保持。

只读夹具CPU1核/内存256MiB为外部原值，host夹具只对自身叶子设置双向64KiB/s、各8IOPS；不能写为Agent设置成功。其他两组CPU0.25核/内存128MiB及相同IO。此为占位PID1、手动固定预算，不含首次标定、真实数据库业务或宿主采集器/全部运行时日志成本。

本次时长属于新ELF dbc48aa5，开发版3a1ce7db结果独立保留。后续[真实路径业务](testing-versioned-candidate-business.md)及[辅助故障](testing-versioned-candidate-faults.md)需自身完整终态；已完成的旧observe24h、现有d370七天与新v1.0.0长期资格互不替换。尚未发布稳定版。
