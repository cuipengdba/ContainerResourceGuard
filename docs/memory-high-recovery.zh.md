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

恢复只处理当前已校验策略中同一个、曾经由 CRG 应用并回读的有限值变成 `max`。新值须先经正常流程应用并回读，才成为可恢复目标。仅在现值仍匹配此前已完成且改变过内核值的所有权记录时，才能从旧 journal 建立验证记录。较严的外部有限值、无法验证的父级限制、身份变化和未决写入均触发保护。CRG 在现有 writer 锁保护下持久化 intent，复查身份、接受的配置来源、父级限制和内核实际值，随后只对锁定的本容器 cgroup 打开的 `memory.high` 写入并回读。

单次恢复在独立任务上运行。旧内核可能在写入时同步回收，任务未完成时检查循环仍更新状态并接收控制请求，同一 writer 的其它写入和接受配置变更等待该任务提交。新配置文件或停用标记可取消尚未开始的写入。内核读写接口没有原子比较交换，写后回读会识别该窗口中仍可观察到的覆盖。持久状态保留原值、有限目标和最近 16 条恢复事件。同一目标一次恢复尝试后 10 分钟内又漂移会保留冲突并停止自动写入，需按现有 journal 冲突流程人工核查。写入或回读失败也会保留故障和未决 intent。成功应用并验证一个新的配置目标后使用该目标的退避记录。

日文件和状态中的事件包括 `memory_high_recovery_started`、`memory_high_recovered`、`memory_high_recovery_paused`、`memory_high_recovery_backoff`、`memory_high_recovery_blocked` 和 `memory_high_recovery_failed`。开启 `events_enabled` 还会在 `state_dir/events.jsonl` 导出摘要。验收以 `crg status` 中 `actual` 的内核回读或本容器 `memory.high` 的直接读取为准。高于软阈值时还应核对 `memory.current`、`memory.events` 的 `high` 与 `oom_kill`、内存 PSI 和实际业务延迟。内核支持用量暂时高于软阈值。参考 [Linux cgroup v2 内存控制器](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory-interface-files)。

隔离 Linux 验证入口为 [native-memory-high-recovery.py](../tests/native-memory-high-recovery.py)。覆盖 60 秒间隔、DBS 30 GiB、HISDBS 15 GiB、热重载、暂停、容器更换和 journal 隔离、重复覆盖、未开启时的旧冲突行为，以及恢复 96 MiB 阈值时的 PostgreSQL 查询延迟和内核压力。开发验证使用临时测试容器。
