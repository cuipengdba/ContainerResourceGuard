# 配置参数

> 最新范围：R29只保留CPU/内存/IO独立百分比，各默认20；R30设置前检查cgroup（v1跳过、v2校验）。日志保留，诊断/热重载/升级等深入功能继续。历史扩展资源规划暂缓。详见[当前配置](independent-percentages.md)和[下一版交付](next-version.md)。

本页描述 next/compatibility-contract 的组合开发候选，尚未发布。已发布 RC2 不接受后续新增字段；各版本安排见 [双模式设计](resource-modes.md)。`resource_mode` 是预算算法，`mode` 是 enforce/observe。

## 手动资源模式（RC3 开发中）

```json
{"resource_mode":"manual","limits":{"cpu_cores":2.5,"memory_high":"4GiB"}}
```

省略的资源不接管，不要求 IO 标定。需要手动 IO 时添加 `limits.io_read_bps`、`io_write_bps`、`io_read_iops`、`io_write_iops` 及 `data_paths`；各路径必须能确认当前块设备和稳定身份，相同设备去重。BPS/IOPS 按每设备应用，不能解释为多设备合计。

CPU 核数范围 0.01–1048576；内存至少 16MiB 并向下按页对齐。字节字符串支持整数及 B/KiB/MiB/GiB/TiB/KB/MB/GB/TB 后缀；无后缀表示字节，区分大小写，不接受小数、负数、指数、/s 或超出有符号 64 位范围的数值。IOPS 是正整数。manual 不能填写 percent，percent 模式不能填写 limits。

新可选参数：`pids_max` 为 1–2147483647 的任务数上限（包含线程）；`cpu_weight` 为 1–10000 的相对权重。manual或旧percent兼容配置中两者不填写就不改；新三项百分比模式不接受这两项绝对值，不管理这些控制。pids 下调需当前用量之外保留至少 32 个任务或 10% 的余量，并在日志持久化后复查。CPU 权重不是 CPU 配额，不限制其他容器。

组合候选已经实现双模式热切换和移除项协调，详见 [热重载](hot-reload.md)。完整候选先校验，再逐项应用；删除维度尝试恢复自有原值，内存/任务安全下调可能延后，需核对实际结果。旧版没有热重载时，先用匹配版本 disable 完成恢复，再改配置并 enable。

## 最小配置

```json
{}
```

仅CPU、内存、IO各自默认20%。可写`{"cpu_percent":30,"memory_percent":40,"io_percent":25}`单独调整；其他资源保持原值。完整字段、换算基准、范围、旧配置兼容见[独立百分比](independent-percentages.md)。

例如 24 个在线逻辑 CPU、64 GiB 宿主机：20% 的请求为 4.8 核 CPU 时间与约 12.8 GiB 内存。内存向下按页对齐，CPU 使用 100000 微秒周期；实际值受既有上限和 cpuset 约束。CPU 不是绑定固定的若干核。

宿主机内存取 `MemTotal`，不是随时变化的空闲内存；CPU 取 sysfs 在线 CPU 列表，而不是 Go 进程当前可调度核数。状态输出容量来源。如果 `/proc/meminfo` 被 lxcfs 等虚拟化，应只读提供 `/host/proc/meminfo`，CRG 优先使用该文件。

## 当前配置字段（资源仅三项）

| JSON 字段 | 默认值 | 含义 |
|---|---|---|
| `resource_mode` | `percent` | 开发分支新增；percent 自动换算，manual 分别指定 |
| `cpu_percent` / `memory_percent` / `io_percent` | 各20 | 分别换算CPU/内存/标定IO，独立生效 |
| `percent` | 不使用 | 仅旧配置兼容入口，不能混用独立百分比；manual禁用 |
| `log_dir` | `/var/log/crg` | 一天一文件、30天/1GB自动清理，失败降级stderr |
| `limits` | 无 | 手动模式必填对象，至少一项 CPU/内存/IO；省略项目不接管 |
| `io_weight` | 不修改 | IO 默认竞争权重 1–10000；保留每设备覆盖，需要内核后端支持，不是硬上限 |
| `memory_high` | 不单独填写 | 旧绝对值兼容参数；推荐手动使用limits.memory_high，百分比自动生成memory.high，允许低于当前用量 |
| `memory_swap_max` | 不修改 | 字节字符串，0B或至少一页；仅限制交换空间，不包含普通内存；有用量时保留余量，0B须已无swap用量 |
| `memory_stable_seconds` | 0 | 仅历史硬限额降低/恢复：0保留瞬时安全检查，或2–3600秒连续稳定窗口；不阻止memory.high回收目标；至少3个分隔样本，等待期间不写新意图 |
| `metrics_enabled` | false | 当前 state_dir 的有界 metrics.prom，默认无监听端口；导出失败不停止资源协调 |
| `events_enabled` | false | 当前 state_dir 的有界 events.jsonl，最多64条/64KiB，默认无监听端口；不包含原值/路径/原始错误 |
| `mode` | `enforce` | `enforce` 协调写入；`observe` 不新增写入，也不撤销此前已生效限额 |
| `io_profile` | `/etc/crg/io-profile.json` | 默认自动标定/复用的本地设备基准 |
| `state_dir` | 系统临时目录下 `containerresourceguard`，通常 `/tmp/containerresourceguard` | 本容器独立、可写的锁、状态和原值日志 |
| `interval_seconds` | 15 | 检查周期，1–3600 秒；仅有变更才输出日志 |
| `data_paths` | 无 | 最多64个容器内绝对路径、每个最多4096字节；百分比模式诊断覆盖，手动 IO 模式必须用它发现当前设备 |

不支持的 JSON 字段、重复键、多个 JSON 对象、无效范围均拒绝，防止拼写错误悄悄失效。不能在配置里指定目标 cgroup/PID/容器。

## CLI

| 命令/选项 | 用途 |
|---|---|
| `doctor` | 只读发现与计算，输出设备及降级原因；不承诺内核一定接受写入 |
| `run` | 只管理自身，持续执行 |
| `run --config FILE` | 从文件读取配置 |
| `--cpu-percent N` / `--memory-percent N` / `--io-percent N` | 独立覆盖对应百分比，未设置的一项默认20；仅这三个资源百分比选项 |
| `--percent N` | 仅旧配置兼容，不能与独立百分比混用 |
| `--log-dir DIR` | 覆盖每日私有日志目录，详见[日志](logging.md) |
| `--state-dir DIR` | 覆盖默认状态目录，必须容器独立 |
| `--io-profile FILE` | 覆盖标定文件路径 |
| `run --once` | 执行一轮并退出；已写限额继续存在 |
| `status [--config FILE] [--state-dir DIR] [--format human]` | 身份校验、快照年龄、当时读到的控制值 |
| `preflight [--format human]` | 计划与控制文件打开权限预检，不写资源值 |
| `disable [--config FILE] [--state-dir DIR]` | 标记停用、等待 Agent 释放锁、恢复自有原值 |
| `enable [--config FILE] [--state-dir DIR]` | 删除停用标记，辅助循环下次重试时重启 Agent |
| `reload [--state-dir DIR] [--config FILE]` | 向同一容器/当前 Agent 会话请求重载；requested不等价已生效 |
| `quiesce --config FILE` | 暂停写入者，保留内核限额和原值日志；供显式维护 |
| `diagnose [--config FILE] [--output FRESH_PRIVATE_FILE]` | 默认输出白名单诊断快照，显式新输出文件0600且有界；不复制原始日志 |
| `upgrade-check --config FILE` / `state-backup --config FILE --output FRESH_PRIVATE_FILE` | 持锁兼容核对 / 显式私有状态备份，见安装升级说明 |
| `binary-install` / `binary-rollback` | 显式摘要/私有receipt控制的单程序替换，不重启业务，不自动enable |
| `supervisor-plan` / `supervisor-install` / `supervisor-uninstall` | 已审阅模板的预览/接入/恢复门槛卸载，显式维护路径和摘要，见接入设计 |
| `restore [--state-dir DIR]` | Agent 停止后恢复自己仍持有的配置 |
| `calibrate [--seconds 3] [--samples 3]` | 无目录/输出参数也可自动选择；维护时主动重标定，默认后台首次流程见自动标定说明 |
| `profile-check --io-profile FILE` / `profile-merge --io-profile A --merge-profile B [--replace] [--output FILE]` | 基准质量/身份核对及默认只读合并预览，显式输出才保存 |
| `version` | 输出版本 |
| `build-info` | 输出版本、源码修订与运行架构 |

文件启动的组合候选每个协调周期检查同一路径的新配置，显式reload使用每秒控制轮询；无效候选保留最后有效配置，state_dir不能运行中改变。CLI覆盖持续生效，单纯文件调百分比时不要同时指定--percent。原始外部上限通过日志保存，不会把CRG上次20%误当作不可提高到30%的外部上限。维护参数、错误码与兼容规则见 [契约草案](compatibility-contract.md)。

## 安全计算

- 既有外部 CPU/内存/IO 限额更严格时保留更严格值。上级内存和 CPU 配额也参与约束；隐藏的祖先仍由内核限制。
- 内存百分比写memory.high，允许超过并可能节流；旧硬限额降低/恢复仍检查余量、增长及可用events/PSI。原有外部memory.max仍可能导致OOM，见[内存策略与升级](memory-reclaim-policy.md)。
- 独立百分比及旧percent配置的内存预算均写memory.high；manual使用limits.memory_high，旧limits.memory_max作为带警告的high别名。默认不设置Swap。不主动回收页缓存、改数据库参数或修改 OOM 策略、cpuset、资源 requests。HugeTLB 单独记账是否纳入内存上限取决于内核配置。
- 缺 IO profile 时 CPU/内存仍可受控，但总体标记 `degraded`，不会显示全部成功。
- IO 换算后任何维度低于 1 个整数 BPS/IOPS 时跳过该设备并报告，不能向上取整伪称符合更小的百分比。极低 IO 限额也会拖慢 Agent 自己的状态持久化。
- 同一台机器上两个容器各设 20%，表示各自资源目标（内存high不是硬上限）；本程序不统计全节点所有容器的比例。

JSON 输出继续是默认格式；doctor、preflight 和 status 可指定 `--format human`。状态没有变化时最多每 5 分钟保存一次，原值日志不减频。

`io_calibration` 默认 `auto`，可选 `off`；percent/enforce首次启动自动选最大合格文件系统，缺基准才测，observe/manual及只读命令不测。默认输出 `/etc/crg/io-profile.json`，详见[自动标定](automatic-io-calibration.md)。RC3写v1汇总；1.0组合候选写v2样本，未发布版本勿混用。

R29/R30覆盖旧默认：仅CPU、内存、IO各自默认20，v1跳过、v2校验后设置，运行日志默认启用；手动模式仍按绝对值且省略项不接管。具体示例以[独立百分比](independent-percentages.md)及[日志](logging.md)为准，历史测试使用的旧配置不追改。
