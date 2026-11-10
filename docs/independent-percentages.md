# CPU、内存、IO 独立百分比（R29 / R30）

最新需求以R29/R30为准：仅接管CPU、内存、IO，三个百分比分别设置，未填写的一项独立默认20%。R28中五项扩展百分比已取消，不再默认管理任务数、权重、memory.high或Swap；这些额外的`*_percent`字段和CLI参数会被拒绝，避免配置误用。

最小配置是`{}`，等价于：

```json
{"cpu_percent":20,"memory_percent":20,"io_percent":20}
```

分别修改示例：

```json
{"cpu_percent":30,"memory_percent":40,"io_percent":25}
```

| 字段 | 默认 | 换算依据 |
|---|---|---|
| cpu_percent | 20 | 宿主在线逻辑CPU数，写cpu.max总CPU时间配额 |
| memory_percent | 20 | 宿主MemTotal，向下按页取整，写memory.max |
| io_percent | 20 | 自动标定读/写BPS及读/写IOPS基准，写io.max四项硬上限 |

取值大于0且不超过100，允许小数；20表示20%，不是0.2%。显式0、null、重复键、未知字段或与旧percent混用均拒绝。上层限额更严格时保留上层边界；危险内存下调、设备不明确和标定失败均报告跳过/降级原因，不宣称已成功限制。20%不能保证所有DBS/HISDBS负载都满足性能要求。

```bash
crg doctor --config /etc/crg/config.json --format human
crg run --config /etc/crg/config.json
crg run --cpu-percent 30 --memory-percent 40 --io-percent 25
```

显式CLI只覆盖对应项；组合开发候选热重载后仍保留CLI优先级。默认自动选择容量最大的合格本地磁盘文件系统，首次后台标定并按稳定设备身份复用，不要求手工指定目录。业务启动独立，不等待标定完成。

## cgroup版本与日志

设置前检查自身`/proc/self/cgroup`与挂载信息。纯v2才进入自身身份、权限和资源安全校验；v1直接跳过并正常退出，不标定、不建立资源状态或写控制文件。混合模式和无法确认版本同样跳过；读取proc失败则记录错误并停止Agent写入。均不改变业务启动结果。不会切换宿主机cgroup版本。

日志事件`cgroup_detected`给出版本、是否允许、动作和原因；v2后续逐项结果由`resource_status`记录，权限或启动失败由`agent_exit`记录。每日文件、30天/1GB清理继续默认启用，见[运行日志](logging.md)。

## 兼容与升级

旧`{"percent":30}`仍仅作为已部署配置兼容入口，不能混用新字段。手动CPU/内存/IO绝对值模式保留，省略项不管理。历史扩展控制实现保留在兼容/开发代码中，不是当前推荐配置；新三百分比模式拒绝额外绝对值资源控制，深入诊断、热重载、升级回退等开发继续。

若曾实际运行R28八项开发候选，先用**对应旧候选**disable恢复它写入的扩展限额，再更换本版和三项配置，核对实际值；不要假定删掉参数会自动撤销旧内核限额。本版也不会重置外部原有扩展限额。正式RC2不接受新字段，回退时必须使用匹配的旧配置。

每个容器独立Agent、配置、日志和状态；每次启动重新发现自身cgroup，容器/Pod ID变化不需手工改路径。持久卷保留配置、基准、日志和私有原值；不管理其他容器，不修改DBS/HISDBS及原缓存逻辑。

默认空配置第16轮main/DBS已完成600秒，SQL10次/API57次错误，业务验收失败；实际三项换算生效不能代替性能验收，见[具体配额和结果](testing-three-resource-default20-business.md)。
