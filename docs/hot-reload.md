# 安全配置热重载（v0.2 开发中）

适用分支：`next/safe-reload`。尚未发布为稳定版，不表示 RC2/RC3 已有此功能。十版顺序和所有发布验收条件继续有效。

## 用法

以文件启动，例如 `crg run --config /etc/crg/config.json`。用原子替换更新同一路径，Agent 每个协调周期读取新内容，支持 Kubernetes ConfigMap 符号链接切换。可在当前容器内执行 `crg reload --state-dir /var/lib/crg`，请求下一次每秒控制轮询重载；状态目录必须与运行中的 Agent 相同。可选 `--config` 只能指向原路径，不接受其他容器、PID 或 cgroup。

`reload` 返回 `requested` 只表示请求文件已落盘。请执行 `crg status --state-dir /var/lib/crg`，检查 `configuration.request_id`、`generation`、`state`、`accepted_hash` 和各个 `items`/`actual`。已接受配置不等于全部内核限额已生效。代次从每次 Agent 运行的 1 开始；有效配置摘要可跨重启对比。

显式 CLI 的 `--percent`、`--state-dir`、`--io-profile` 在重载后继续覆盖文件字段。如果想仅通过文件调整百分比，启动时不要同时指定 `--percent`。

## 两种模式与移除项

- 百分比模式仍可只填 `{"percent":20}`，将 20 改为 30 无需重启业务或 Agent。
- 手动模式如 `{"resource_mode":"manual","limits":{"cpu_cores":2,"memory_max":"8GiB"}}`，只管理明确填写的维度。允许与百分比模式切换；手动模式不得同时填写 `percent`。
- 明确移除手动维度或可选 `pids_max`/`cpu_weight` 时，只恢复仍由 CRG 拥有的原值。恢复原来的更低内存/任务上限也必须通过安全预检；否则保留现值，报告未完成并在后续周期重试。
- 临时无法解析仍请求的维度（例如 IO 标定文件丢失）保留已有受管限额，报告 `retained`，不能误判为要求取消限额。
- 更换 IO 设备范围暂保留旧设备限额并报告。需要清除时先显式 `disable`，核对恢复结果，再调整范围和 `enable`；多设备维护工具由 v0.3 承接。
- `enforce` → `observe` 不写控制文件，也不隐式撤销原限额。需要撤销时使用 `disable`；返回 `enforce` 才协调新策略。

## 失败与并发

先完整校验候选配置和计划，再接受新代次，随后逐项持久化意图、写入、回读、完成日志。跨文件不是原子事务，一项失败时其余项可能已生效。外部改值、设备身份变化、不安全内存下调仍受保护。

半写入、坏 JSON、重复键、未知字段、越界、缺文件和读错误均保留上一份有效配置。源文件必须解析到不超过 1MiB 的普通文件；Linux 非阻塞打开避免 FIFO 卡住读取。运行中拒绝更换状态目录，目录迁移留给受控升级。

每秒控制检查先处理 disable，再处理重载。请求绑定当前 cgroup 身份和随机 Agent 会话，旧容器/旧进程请求不重放。单实例锁继续绑定自身 cgroup inode，不以状态目录不同绕过。原值日志持久化失败后，不继续发起新控制文件写入。

本地配置/profile/状态目录是可信管理员配置，不构成对容器 root 的安全边界。不开放端口，不使用 Kubernetes API，不依赖容器 ID 查询。

## 验证状态

已加入坏配置保留、CLI 覆盖、双模式切换、移除项恢复、外部冲突、缺 IO 计划保留、会话绑定、Linux FIFO 和 ConfigMap 链接切换回归。Linux 完整回归、真实 cgroup 重载和故障注入待归档，不能以本文件代替测试证据。
