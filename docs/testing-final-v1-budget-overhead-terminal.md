# 固定最终ELF：不同实际额度开销终态

两份新增独立容器完成45秒预热及实际1800秒，各181样本。全部新测Agent/PID1身份、实际控制及ELF在独立初始观察中确认，并与终态相同；没有重建产物或继承旧计时。

| 来源/额度 | 测量秒数 | 单核CPU平均% | RSS最大MiB | 写入KiB | 状态最小写入间隔秒 |
| --- | --- | --- | --- | --- | --- |
| healthy-low | 1800.008 | 0.022778 | 9.750 | 152.000 | 300.001 |
| healthy-half | 1800.009 | 0.023333 | 9.848 | 156.000 | 300.001 |
| healthy-threequarters | 1800.009 | 0.023333 | 9.527 | 152.000 | 300.000 |

healthy-low是既有最终1404健康档的准确复算引用，不是第三份新测：0.25CPU/high128MiB/BPS64KiB/手动8IOPS。两份新测为0.5CPU/high192MiB/BPS128KiB/16IOPS及0.75CPU/high224MiB/BPS1MiB/128IOPS。运行时1CPU/memory.max256MiB保留，产品不新增memory.max。

每份新样本实际控制保持，metrics/events为ready且文件有内容；原15秒周期、单核CPU≤0.1%、RSS≤20MiB、稳定状态写入间隔≥299秒、健康写入≤8MiB与OOM0均逐项复算。全部runner/worker、四个原始PID/start、两对父叶cgroup和namespace独立确认消失。必要日志/journal未为达标省略。

与既有最终1404真实低IO、持续导出失败、实际只读挂载1800秒原件共同形成不同有效额度和异常开销证据。共享节点、占位PID1与Agent自身计数，不是排除系统干扰的因果性能比较、厂商业务或七天老化证明。

[计划](testing-final-v1-budget-overhead.md)、[独立复算JSON](test-results-final-v1-budget-overhead-terminal.json)、[原始终态/初始实际ELF及样本](test-evidence-final-v1-budget-overhead-terminal.json.gz)、[既有低IO/持续异常终态](testing-final-v1-overhead-terminal.md)。稳定1.0尚未接受。
