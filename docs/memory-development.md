# 可选内存压力与 Swap 参数（v0.4 开发中）

分支 `next/memory-pressure`，基于未发布的 v0.3 开发代码。该文档记录 P05.5 的实现，不表示已发布，也不代替 P05 业务高峰和缓存共存验收。

```json
{"percent":20,"memory_high":"10GiB","memory_swap_max":"0B"}
```

两种资源模式都可使用。省略则不修改；没有从总百分比自动推导这两个额外阈值，原最小配置不变。

| 参数 | 规则 | 作用 |
|---|---|---|
| memory_high | 与 memory_max 相同的整数字节单位，至少 16MiB，按页向下对齐 | 对应 memory.high，超过后回收/节流，可能明显增加延迟；不是硬内存上限 |
| memory_swap_max | 整数字节单位，0B 或至少一页，按页向下对齐 | 对应 memory.swap.max；0B 限制新增匿名页换出，省略保持原策略 |

显式手动 memory_high 大于请求的 memory_max 时拒绝配置；百分比模式按宿主基数计算后发现 high 超过请求的内存预算，同样拒绝候选。实际计划还受已有高水位、硬上限及父层约束，不放宽更严格的外部限制。

memory.high 下调沿用当前 memory.max 的用量/增长预留、PSI/events 预检和意图落盘后的复查，危险下调会延后。恢复原来的更低 high 也必须满足预检。它不能保证未来分配绝不引起节流或 OOM；memory.max 仍可能触发 OOM。

Swap 下调先读 memory.swap.current；目标低于已有用量时延后，不强制把现有换出页调回 RAM。非零用量还保留 5% 加一页余量；目标 0 仅在当前 Swap 为 0 时设置。日志落盘后再次复查。撤销恢复原来更低的 Swap 额度时执行同样保护。

接口缺失、只读、无权限只跳过相应项目。它不启用/关闭宿主 Swap、不改 swappiness、不写 memory.reclaim、不清理全局缓存、不修改 PostgreSQL 或原缓存程序。宿主无 Swap 时，回读成功不等于已验证实际换入换出行为。

所有项目纳入原值日志、外部冲突保护、逐项回读、disable 恢复和重载删除项处理。旧版本不认识新控制项时会拒绝日志，降级前必须先用支持它们的版本停用并核对恢复；不能删除原值日志。

## 当前验证

Windows 通用单元和 vet 通过，覆盖参数边界、high/硬预算一致性、祖先/原值夹限、零 Swap、危险下调、落盘期间 Swap 增长、恢复原来为零的 Swap 限额、外部改值。Linux race/CI 和 16 项真实控制/工具检查已通过，见 [实测](testing-memory-io.md)。实际 Swap、跨周期稳定窗口和原缓存回收高峰仍待验收。

内核接口依据 [Linux cgroup v2 官方文档](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)。
