# 配置参数

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
| `percent` | 无，必填 | 三类资源共同百分比，范围 `(0,100]` |
| `mode` | `enforce` | `enforce` 写入，`observe` 仅预览 |
| `io_profile` | `/etc/crg/io-profile.json` | 该节点显式标定产生的设备基准 |
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
