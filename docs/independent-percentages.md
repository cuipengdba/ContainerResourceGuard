# 独立资源百分比（R28）

2026-11-10用户最新要求覆盖早期“一个总百分比”：CPU、内存、IO各自设置，其他资源参数也各自设置百分比，省略时分别默认20。当前RC3和1.0组合开发线已接入，尚未发布；旧版RC2不接受新字段。

最小配置是`{}`。等价的显式配置：

```json
{
  "cpu_percent": 20,
  "memory_percent": 20,
  "io_percent": 20,
  "pids_percent": 20,
  "cpu_weight_percent": 20,
  "io_weight_percent": 20,
  "memory_high_percent": 20,
  "memory_swap_percent": 20
}
```

只写`{"cpu_percent":30,"memory_percent":40,"io_percent":25}`即可单独调整三项，其余五项仍分别20；没有全局比例。百分数20表示20%，不是0.2%。普通资源百分比须大于0且不超过100；`memory_swap_percent`也接受0。小数允许，null、非有限值、重复键和混用两类模式拒绝。

| 字段 | 换算基准 | 生效边界 |
|---|---|---|
| cpu_percent | 宿主在线逻辑CPU数 | cpu.max总CPU时间配额，受原外部配额/cpuset约束 |
| memory_percent | 宿主MemTotal | memory.max，向下按页取整；危险下调仍延后 |
| io_percent | 自动标定设备的读写BPS及读写IOPS基准 | 四项io.max硬上限；默认自动选盘/标定/复用，不需指定目录 |
| pids_percent | 可信procfs的宿主kernel.pid_max | pids.max任务数（含线程）；不超过原外部上限，下调保留余量 |
| cpu_weight_percent | 合法权重最大值10000 | 20映射为2000，最小1；相对竞争权重，不承诺20%CPU份额 |
| io_weight_percent | 合法权重最大值10000 | 20映射为default2000，保留设备覆盖；依赖后端支持，不替代限速 |
| memory_high_percent | 宿主MemTotal | memory.high；受请求memory_percent和已有high/max约束，可能节流；不是默认不管理 |
| memory_swap_percent | 可信宿主SwapTotal | memory.swap.max，仅swap；无宿主swap时为0，不创造swap；危险下调延后 |

容量来源不可信或控制器缺失时，逐项跳过并报告，不猜容量，不影响业务启动。低于内核最小CPU/内存/IO单位的目标也跳过。默认20%不保证所有DBS/HISDBS负载都满足性能标准；旧30%和16MiB/s失败记录继续保留。

```bash
crg doctor --format human
crg run --config /etc/crg/config.json
crg run --cpu-percent 30 --memory-percent 40 --io-percent 25
```

八个JSON字段均有对应连字符CLI选项，例如`--pids-percent`、`--memory-high-percent`。显式CLI覆盖优先，组合候选热重载后继续保留；配置文件改动不能覆盖这些CLI值。手动绝对值模式继续保留，省略项目仍不接管，不加隐含20%限额。

## 旧配置兼容

旧`{"percent":30}`只作为兼容入口，仍按原三项同30%执行，省略的扩展项仍不管理；不是新配置的默认或推荐入口。它不能与任何新`*_percent`字段混用，避免预算歧义。旧绝对值扩展字段在旧配置及manual中保留；新的独立百分比模式须使用相应`*_percent`，绝对值请用manual。

升级可将旧percent文件替换为独立三项，其他五项此时默认20并开始接管，须预览实际计划。回退到不识别新字段的旧二进制前，恢复其匹配配置及已有私有备份；不把新配置强行交给旧读取器。

配置、状态、日志使用独立比例；日志规则见[运行日志](logging.md)。各容器独立Agent、配置、状态和日志目录；不管理其他容器，不改业务或缓存程序。
