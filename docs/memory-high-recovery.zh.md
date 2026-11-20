# 自动恢复 memory.high

每个容器通过自己的配置显式开启 `memory_high_recovery`。沿用 `interval_seconds`，设为 `60` 时每分钟检查一次。省略开关或设为 `false` 时沿用原冲突处理。采用原配置加载和热重载方式。

下例是 171 的 DBS 验收参数。HISDBS 的相应值为 `15GiB`。两个值都从配置读取。示例使用手动模式单独管理内存。如果容器已有 CPU 或 IO 策略，将恢复开关与间隔合并到现有配置。

```json
{
  "mode": "enforce",
  "resource_mode": "manual",
  "limits": {"memory_high": "30GiB"},
  "interval_seconds": 60,
  "memory_high_recovery": true,
  "memory_high_recovery_paused": false,
  "events_enabled": true
}
```

维护前将 `memory_high_recovery_paused` 设为 `true`，原子替换配置并执行 `crg reload --config /etc/crg/config.json`。用 `crg status --config /etc/crg/config.json` 核对 reload 的请求 ID 和接受代次后再维护。正在进行的恢复需要等写入和回读结束后才会接受新配置。维护结束将暂停字段设回 `false` 并热重载。暂停时遇到原有限值漂移到 `max` 会保留暂停状态和原所有权，可以在恢复启用后继续处理。正常热重载仍可在所有权有效时应用新值。

使用自定义 `state_dir` 时，`reload` 需要传入相同目录的 `--state-dir`。恢复开启后的 journal 可包含新字段。旧版严格读取配置和 journal，回退前用目标程序做兼容性检查，保留原状态备份并按已有恢复流程处理受控迁移。详见 [安装与回退](installation.md)。

恢复只处理当前已校验策略中同一个、曾经由 CRG 应用并回读的有限值变成 `max`。新值须先经正常流程应用并回读，才成为可恢复目标。仅在现值仍匹配此前已完成且改变过内核值的所有权记录时，才能从旧 journal 建立验证记录。较严的外部有限值、无法验证的父级限制、身份变化和未决写入均触发保护。CRG 在现有 writer 锁保护下持久化 intent，复查身份、接受的配置来源、父级限制和内核实际值，随后只对锁定的本容器 cgroup 打开的 `memory.high` 写入并回读。

单次恢复在独立任务上运行。旧内核可能在写入时同步回收，任务未完成时检查循环仍更新状态并接收控制请求，同一 writer 的其它写入和接受配置变更等待该任务提交。新配置文件或停用标记可取消尚未开始的写入。内核读写接口没有原子比较交换，写后回读会识别该窗口中仍可观察到的覆盖。持久状态保留原值、有限目标和最近 16 条恢复事件。同一目标一次恢复尝试后 10 分钟内又漂移会保留冲突并停止自动写入，需按现有 journal 冲突流程人工核查。写入或回读失败也会保留故障和未决 intent。成功应用并验证一个新的配置目标后使用该目标的退避记录。

日文件和状态中的事件包括 `memory_high_recovery_started`、`memory_high_recovered`、`memory_high_recovery_paused`、`memory_high_recovery_backoff`、`memory_high_recovery_blocked` 和 `memory_high_recovery_failed`。开启 `events_enabled` 还会在 `state_dir/events.jsonl` 导出摘要。验收以 `crg status` 中 `actual` 的内核回读或本容器 `memory.high` 的直接读取为准。高于软阈值时还应核对 `memory.current`、`memory.events` 的 `high` 与 `oom_kill`、内存 PSI 和实际业务延迟。内核支持用量暂时高于软阈值。参考 [Linux cgroup v2 内存控制器](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory-interface-files)。

隔离 Linux 验证入口为 [native-memory-high-recovery.py](../tests/native-memory-high-recovery.py)。覆盖 60 秒间隔、DBS 30 GiB、HISDBS 15 GiB、热重载、暂停、容器更换和 journal 隔离、重复覆盖、未开启时的旧冲突行为，以及恢复 96 MiB 阈值时的 PostgreSQL 查询延迟和内核压力。开发验证使用临时测试容器。

## 隔离 Linux 验证结果

2026-11-20，Linux AMD64 `7.0.0-1017-azure`、PostgreSQL 16.16。受测提交为 `5a3628a57d7545a6401a1367ff823f8f29f9bb3e`。原始报告包含内核回读、journal、事件日志和清理结果。[实测报告](test-results-memory-high-recovery.json) · [Linux 实测](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/44692261670) · [项目 CI](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/44692261480)

| 测试 | 结果 |
| --- | --- |
| DBS，60 秒检查周期 | 在下一轮恢复为 32,212,254,720 字节（30 GiB），从测试写入到观测回读约 60.001 秒。journal 最初值 38 GiB，其他控制值核对一致。 |
| HISDBS，热重载与暂停 | 热重载从 12 GiB 改为 15 GiB。暂停后确保 `max` 持续 5 秒，恢复启用后回读为 16,106,127,360 字节。 |
| 重复覆盖 | 同一目标的再次覆盖写入 `max` 后进入退避冲突；经过后续检查仍回读为 `max`，journal 和日志记录 `memory_high_recovery_backoff`。 |
| 容器更换与旧配置 | 新容器的 ID、cgroup inode 和 journal 身份变更。旧 journal 归档。未配置开关的实例遇到 `max` 后保留原冲突行为。 |
| 写入和恢复保护 | Linux Go race 测试覆盖未决 intent、写入异常、身份或实际值变化、更新配置导致旧任务取消，以及阻塞写入期间检查仍可运行。 |

压力用例在用量约 **226.8 MiB** 时恢复到 **96 MiB**，随后 `memory.current` 约 **189.5 MiB**。内核 `high` 事件增加 **326** 次，`pgscan` 增加 **11,119**，`oom_kill` 增量为 **0**。两次 6 秒 pgbench 查询均零失败，平均延迟分别为 **0.303 ms** 和 **0.284 ms**，吞吐分别为 **35.01 TPS** 和 **20.55 TPS**。用量和吞吐仍受压力影响，这组数据只覆盖隔离的短查询负载。早期同负载下新启动的容器内清理命令超过 30 秒，最终用例在记录内核与 SQL 结果后由测试宿主清理该临时文件，再等待 journal 确认回读后注入第二次覆盖。[清理超时记录](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/44681552990) · [重复漂移前等待回读的修正记录](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/44687972301)

首次验证的 reload 命令漏传测试实例的自定义状态目录，后续按现有命令参数重试。项目 CI 中的旧厂商阶段自检改为读取与原摘要匹配的冻结夹具，保留原摘要和检查条件。所有临时测试容器及各自 cgroup 均已移除。本轮未在 171 部署。[首次验证记录](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/44680128956)
