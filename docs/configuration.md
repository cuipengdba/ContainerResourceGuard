# 配置参数

开发分支新增双资源模式；已发布 RC2 尚不接受这些新字段。见 [设计及分版安排](resource-modes.md)。`resource_mode` 是预算算法，`mode` 仍是 enforce/observe。

## 手动资源模式（RC3 开发中）

```json
{"resource_mode":"manual","limits":{"cpu_cores":2.5,"memory_max":"4GiB"}}
```

省略的资源不接管，不要求 IO 标定。需要手动 IO 时添加 `limits.io_read_bps`、`io_write_bps`、`io_read_iops`、`io_write_iops` 及 `data_paths`；各路径必须能确认当前块设备和稳定身份，相同设备去重。BPS/IOPS 按每设备应用，不能解释为多设备合计。

CPU 核数范围 0.01–1048576；内存至少 16MiB 并向下按页对齐。字节字符串支持整数及 B/KiB/MiB/GiB/TiB/KB/MB/GB/TB 后缀；无后缀表示字节，区分大小写，不接受小数、负数、指数、/s 或超出有符号 64 位范围的数值。IOPS 是正整数。manual 不能填写 percent，percent 模式不能填写 limits。

新可选参数：`pids_max` 为 1–2147483647 的任务数上限（包含线程）；`cpu_weight` 为 1–10000 的相对权重。两者不填写就不改；pids 下调需当前用量之外保留至少 32 个任务或 10% 的余量，并在日志持久化后复查。CPU 权重不是 CPU 配额，不限制其他容器。

首次从百分比切到手动、或删除已管理项目时，开发阶段应先用同版本 disable 完成恢复，再调整配置并 enable；自动热切换/移除项目的规则由 P03.5 实现，不能把遗漏的旧限额默认为已撤销。

## 最小配置

```json
{"percent":20}
```

20 表示 20%，不是 0.2%。允许大于 0 且不超过 100 的数，可有小数。CPU、内存和标定 IO 默认使用同一比例，无需分别指定核数、内存容量或每秒字节数。

例如 24 个在线逻辑 CPU、64 GiB 宿主机：20% 的请求为 4.8 核 CPU 时间与约 12.8 GiB 内存。内存向下按页对齐，CPU 使用 100000 微秒周期；实际值受既有上限和 cpuset 约束。CPU 不是绑定固定的若干核。

宿主机内存取 `MemTotal`，不是随时变化的空闲内存；CPU 取 sysfs 在线 CPU 列表，而不是 Go 进程当前可调度核数。状态输出容量来源。如果 `/proc/meminfo` 被 lxcfs 等虚拟化，应只读提供 `/host/proc/meminfo`，CRG 优先使用该文件。

## 全部可选字段

| JSON 字段 | 默认值 | 含义 |
|---|---|---|
| `resource_mode` | `percent` | 开发分支新增；percent 自动换算，manual 分别指定 |
| `percent` | 无 | 百分比模式必填，范围 `(0,100]`；手动模式不能混用 |
| `limits` | 无 | 手动模式必填对象，至少一项 CPU/内存/IO；省略项目不接管 |
| `pids_max` | 不修改 | 开发分支新增；任务数硬上限，包含线程 |
| `cpu_weight` | 不修改 | 开发分支新增；CPU 相对竞争权重 1–10000 |
| `mode` | `enforce` | `enforce` 写入，`observe` 仅预览 |
| `io_profile` | `/etc/crg/io-profile.json` | 默认自动标定/复用的本地设备基准 |
| `state_dir` | 系统临时目录下 `containerresourceguard`，通常 `/tmp/containerresourceguard` | 本容器独立、可写的锁、状态和原值日志 |
| `interval_seconds` | 15 | 检查周期，1–3600 秒；仅有变更才输出日志 |
| `data_paths` | 无 | 可选的容器内绝对路径列表；只读显示 IO 设备覆盖，不改变统一预算 |

不支持的 JSON 字段、重复键、多个 JSON 对象、无效范围均拒绝，防止拼写错误悄悄失效。不能在配置里指定目标 cgroup/PID/容器。

## CLI

| 命令/选项 | 用途 |
|---|---|
| `doctor --percent 20` | 只读发现与计算，输出设备及降级原因；不承诺内核一定接受写入 |
| `run --percent 20` | 只管理自身，持续执行 |
| `run --config FILE` | 从文件读取配置 |
| `--percent N` | 显式覆盖配置文件的 percent |
| `--state-dir DIR` | 覆盖默认状态目录，必须容器独立 |
| `--io-profile FILE` | 覆盖标定文件路径 |
| `run --once` | 执行一轮并退出；已写限额继续存在 |
| `status [--config FILE] [--state-dir DIR] [--format human]` | 身份校验、快照年龄、当时读到的控制值 |
| `preflight --percent 20 [--format human]` | 计划与控制文件打开权限预检，不写资源值 |
| `disable [--config FILE] [--state-dir DIR]` | 标记停用、等待 Agent 释放锁、恢复自有原值 |
| `enable [--config FILE] [--state-dir DIR]` | 删除停用标记，辅助循环下次重试时重启 Agent |
| `restore [--state-dir DIR]` | Agent 停止后恢复自己仍持有的配置 |
| `calibrate --directory DIR --output FILE [--seconds 3]` | 显式 IO 标定，每阶段 1–30 秒，默认 3 秒 |
| `version` | 输出版本 |
| `build-info` | 输出版本、源码修订与运行架构 |

Agent 启动时读取配置；持续运行不会热加载。重启 Agent 可更新 percent，原始外部上限通过日志保存，不会把 CRG 上一次 20% 误当作不可提高到 30% 的外部上限。

## 安全计算

- 既有外部 CPU/内存/IO 限额更严格时保留更严格值。上级内存和 CPU 配额也参与约束；隐藏的祖先仍由内核限制。
- 内存下调检查 `5% + 16 MiB` 余量、采样增长、可用的 events/PSI，并在日志同步后复查；见 [运维说明](operations.md)。瞬时检查不能保证并发增长后绝不 OOM。
- 不修改 `memory.high`、swap、OOM 策略、cpuset 和资源 requests；HugeTLB 单独记账是否纳入内存上限取决于内核配置。
- 缺 IO profile 时 CPU/内存仍可受控，但总体标记 `degraded`，不会显示全部成功。
- IO 换算后任何维度低于 1 个整数 BPS/IOPS 时跳过该设备并报告，不能向上取整伪称符合更小的百分比。极低 IO 限额也会拖慢 Agent 自己的状态持久化。
- 同一台机器上两个容器各设 20%，表示各自上限；本程序不统计全节点所有容器的比例。

JSON 输出继续是默认格式；doctor、preflight 和 status 可指定 `--format human`。状态没有变化时最多每 5 分钟保存一次，原值日志不减频。

`io_calibration` 默认 `auto`，可选 `off`；percent/enforce首次启动自动选最大合格文件系统，缺基准才测，observe/manual及只读命令不测。默认输出 `/etc/crg/io-profile.json`，详见[自动标定](automatic-io-calibration.md)。RC3写v1汇总；1.0组合候选写v2样本，未发布版本勿混用。
