# 双资源模式与可选参数设计

> 2026-11-12已选定的新内存语义：百分比及手动内存写memory.high，不新增memory.max；允许超目标，外部硬限额保留。旧硬限额仅凭同身份journal及仍持有的值恢复。下述旧版实现/测试保持历史来源，不能替代新策略验证。见[内存策略](memory-reclaim-policy.md)。

> 最新范围：R29只保留CPU/内存/IO独立百分比，各默认20；R30设置前检查cgroup（v1跳过、v2校验）。日志保留，诊断/热重载/升级等深入功能继续。历史扩展资源规划暂缓。详见[当前配置](independent-percentages.md)和[下一版交付](next-version.md)。

需求日期：2026-11-10。本文是 RC2 之后的设计；交付状态以任务清单和报告为准。`resource_mode` 选择预算算法；现有 `mode` 继续表示 `enforce`（执行）或 `observe`（只观察）。

## 百分比模式

R29/R30覆盖R28：只接管CPU、内存、IO，分别设置百分比，各默认20%；额外资源不接管，设置前检查cgroup版本。最小配置`{}`，示例`{"cpu_percent":30,"memory_percent":40,"io_percent":25}`。完整口径见[独立百分比](independent-percentages.md)。旧percent只作部署兼容，不能与新字段混用。

## 手动模式

```json
{
  "resource_mode":"manual",
  "limits":{
    "cpu_cores":4,
    "memory_high":"8GiB",
    "io_read_bps":"100MiB",
    "io_write_bps":"50MiB",
    "io_read_iops":1000,
    "io_write_iops":500
  },
  "data_paths":["/data"]
}
```

- CPU 是容器合计 CPU 时间核数，可为小数，不是绑核。
- 内存和带宽使用明确单位；带宽字段是每秒，不需再写 `/s`。支持的单位和溢出校验会在配置文档列明。
- manual 不混用 percent；percent 模式不混用 limits。手动至少指定一个 limits 项，省略项不接管；0 不表示无限制。
- 手动 IO 不需要性能标定。按当前容器 data_paths 的文件系统解析实际块设备，相同设备去重，不让用户填写易变的设备编号或容器 ID。
- 这组 IO 数值是每个确认设备的上限，不是多个设备的合计上限。无法确认的 Overlay/NFS 路径明确未管理，不猜后端设备。
- 两种模式共用外部硬上限约束、单实例锁、原值日志、回读、冲突保护和受控恢复。

## 五个可选参数

R29已暂停新增五项资源控制的交付，当前推荐配置仅三项百分比。下表仅保留原规划及历史兼容说明，默认全部不改，不提供额外百分比。诊断、热重载、安装升级等深入功能继续推进。语义依据 [Linux cgroup v2 官方文档](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)。

| 参数 | 接口 | 作用与边界 | 计划版本 |
|---|---|---|---|
| pids_max | pids.max | 容器任务数上限，包含线程；危险下调要保留创建任务余量 | RC3 |
| cpu_weight | cpu.weight | CPU 竞争相对权重，1–10000；不是硬上限 | RC3 |
| io_weight | io.weight | IO 竞争相对权重，1–10000；依赖内核/设备支持，不替代限速 | v0.3.0 |
| memory_high | memory.high | 内存压力阈值，可能触发回收/节流，不是 OOM 硬上限 | v0.4.0 |
| memory_swap_max | memory.swap.max | Swap 上限，0B 禁止新增 Swap；省略则不改，已有用量下调需保护 | v0.4.0 |

计划使用示例（只能在对应功能已交付的版本使用）：

```json
{"percent":20,"pids_max":1024,"cpu_weight":100,"io_weight":100,"memory_high":"10GiB","memory_swap_max":"0B"}
```

memory_high 要与实际 memory.max 做一致性检查。新增项目全部纳入状态、原值日志、冲突保护、恢复和故障测试；不接管原缓存程序，不修改数据库参数。未知字段继续拒绝，不能接受后悄悄忽略。

## 十版中的任务安排

| 新增任务 | 内容 |
|---|---|
| P01.5 | 双模式 CPU/内存/IO 与旧最小配置兼容 |
| P01.6 | pids_max、cpu_weight 及危险下调/恢复保护 |
| P03.5 | 双模式热重载与切换，明确删除项目的恢复/保留规则 |
| P04.5 | io_weight、手动多路径/多设备与替盘回归 |
| P05.5 | memory_high、memory_swap_max 和下调保护 |
| P06.5 | 双模式下容器/Pod/节点重启及状态保留/丢失组合回归 |

十版顺序不变，总计 46 项任务。P02/P07/P08/P09/P10 的业务、诊断、升级、开销和 1.0 验收同时覆盖两种模式及届时已实现的全部参数。用户已授权规划后直接持续开发到 1.0 并更新 GitHub，发布仍需满足证据条件。

R27/R28新增日志与独立百分比任务后总数52项；旧46/48项数字作为当时规划历史保留。原任务深入验收和发布条件不删除。
