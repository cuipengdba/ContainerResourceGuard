# 固定最终ELF三场景30分钟开销终态

固定v1.0.0最终候选、产品源码`ced461705ebc27315a59aefe463f9b4af47130a3`，二进制`9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8`。原门槛未改，正常、持续导出失败、只读cgroup三场景均完成45秒预热后实际1800秒测量，各181份样本，runner退出0。独立按准确样本复算：

| 场景 | 测量秒数 | 平均CPU（单核%） | RSS最大MiB | Agent写入KiB | 状态最小写入间隔秒 | OOM新增 |
| --- | --- | --- | --- | --- | --- | --- |
| healthy | 1800.008 | 0.022778 | 9.750 | 152.000 | 300.001 | 0 |
| export-failure | 1800.008 | 0.022778 | 9.875 | 44.000 | 300.000 | 0 |
| readonly | 1800.008 | 0.031111 | 9.445 | 1112.000 | 300.066 | 0 |

各场景均符合单核CPU平均≤0.1%、RSS采样最大≤20MiB、状态稳定写入间隔≥299秒，正常写入≤8MiB、故障≤16MiB。每份样本的Agent身份、PID1/Agent归属和八项控制保持；结束后独立观察确认runner/worker、六个原始PID/start、三个父叶cgroup对及namespace全部消失。

持续故障场景的metrics/events全程unavailable，受保护marker和符号链接保留；只读场景全程degraded，IO上限由夹具仅向自有叶组外部设置，不能算Agent写入成功。终态每日0600日志含v2检测和high策略，journal/status保留。日志、事件与必要journal未为达标省略。

预算为manual 0.25CPU、memory.high128MiB、读写64KiB/s和手动8IOPS，运行时memory.max256MiB不变。三份独立占位PID1使用原厂镜像shell，没有启动DBS/HISDBS与缓存业务；共享amd64/Linux5.14单设备节点。CPU、RSS及写入统计仅计Agent。未继承旧版本计时，也不是默认20%业务性能、不同有效限额全部覆盖、独占长期或稳定发布证明。

[独立复算与完整清理结果](test-results-final-v1-overhead-terminal.json)、[准确原始终态及样本](test-evidence-final-v1-overhead-terminal.json.gz)、[唯一启动与冻结计划](testing-final-v1-overhead.md)、[环境矩阵](tested-environment-matrix.md)。旧版开销结果与本轮分开归档。
