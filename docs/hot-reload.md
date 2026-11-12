# 安全配置热重载（v0.2 开发中）

> 2026-11-12已选定的新内存语义：百分比及手动内存写memory.high，不新增memory.max；允许超目标，外部硬限额保留。旧硬限额仅凭同身份journal及仍持有的值恢复。下述旧版实现/测试保持历史来源，不能替代新策略验证。见[内存策略](memory-reclaim-policy.md)。

当前适用未发布的`next/compatibility-contract`及同内容分区开发线；原`next/safe-reload`为历史来源。已发布RC2及v0.1.0-rc.3-preview.1没有此功能。只管理CPU/内存/IO，三个独立百分比各默认20%；设置前仍须通过纯cgroup v2门禁，v1/混合/未知跳过并记录日志。十版顺序和所有发布验收条件继续有效。

## 用法

以文件启动，例如 `crg run --config /etc/crg/config.json`。用原子替换更新同一路径，Agent 每个协调周期读取新内容，支持 Kubernetes ConfigMap 符号链接切换。可在当前容器内执行 `crg reload --state-dir /var/lib/crg`，请求下一次每秒控制轮询重载；状态目录必须与运行中的 Agent 相同。可选 `--config` 只能指向原路径，不接受其他容器、PID 或 cgroup。

`reload` 返回 `requested` 只表示请求文件已落盘。请执行 `crg status --state-dir /var/lib/crg`，检查 `configuration.request_id`、`generation`、`state`、`accepted_hash` 和各个 `items`/`actual`。已接受配置不等于全部内核限额已生效。代次从每次 Agent 运行的 1 开始；有效配置摘要可跨重启对比。

显式CLI的`--cpu-percent`、`--memory-percent`、`--io-percent`分别持续覆盖文件中的对应项；`--log-dir`、`--state-dir`、`--io-profile`同样保持CLI优先。想通过文件调整某项时，启动时不要为该项传入CLI覆盖。旧`--percent`仅保留部署兼容，不与三个新字段混用。

## 两种模式与移除项

- 百分比模式可只填`{}`，或`{"cpu_percent":30,"memory_percent":40,"io_percent":25}`。合法修改只影响对应项；省略的一项独立恢复默认20%，无须重启业务或Agent。旧单percent仅兼容原部署。
- 手动模式如 `{"resource_mode":"manual","limits":{"cpu_cores":2,"memory_high":"8GiB"}}`，只管理明确填写的维度。允许与百分比模式切换；手动模式不得同时填写 `percent`。
- 移除明确管理的手动CPU/内存/IO维度时，只恢复仍由CRG拥有的原值；恢复更低内存上限仍必须通过安全预检，否则保留现值并报告未完成。历史扩展控制不作为当前配置推荐；曾运行过八项候选时，按[迁移规则](independent-percentages.md)使用对应旧程序恢复。
- 临时无法解析仍请求的维度（例如 IO 标定文件丢失）保留已有受管限额，报告 `retained`，不能误判为要求取消限额。
- 更换 IO 设备范围暂保留旧设备限额并报告。需要清除时先显式 `disable`，核对恢复结果，再调整范围和 `enable`；多设备维护工具由 v0.3 承接。
- `enforce` → `observe` 不写控制文件，也不隐式撤销原限额。需要撤销时使用 `disable`；返回 `enforce` 才协调新策略。

## 失败与并发

先完整校验候选配置和计划，再接受新代次，随后逐项持久化意图、写入、回读、完成日志。跨文件不是原子事务，一项失败时其余项可能已生效。外部改值、设备身份变化、不安全内存下调仍受保护。

半写入、坏 JSON、重复键、未知字段、越界、缺文件和读错误均保留上一份有效配置。源文件必须解析到不超过 1MiB 的普通文件；Linux 非阻塞打开避免 FIFO 卡住读取。运行中拒绝更换状态目录，目录迁移留给受控升级。

每秒控制检查先处理 disable，再处理重载。请求绑定当前 cgroup 身份和随机 Agent 会话，旧容器/旧进程请求不重放。单实例锁继续绑定自身 cgroup inode，不以状态目录不同绕过。每项控制文件写入都必须先成功持久化对应意图；移除项恢复返回日志错误时不再应用后续计划。

本地配置/profile/状态目录是可信管理员配置，不构成对容器 root 的安全边界。不开放端口，不使用 Kubernetes API，不依赖容器 ID 查询。

## 验证状态

Linux Go 1.22.5 的 vet、race/coverage、16 个建模强杀检查点及 12 个辅助进程故障场景通过。源码 CI 同样通过。真实 cgroup 完成 13 项检查，包括 60 秒周期下约 1.42 秒响应显式请求、坏配置保留、双模式切换、移除项恢复、observe 不写、IO profile 缺失保留、状态目录拒绝变更、外部改值和 disable 优先；业务 PID 1 与另一容器保持运行。完整结果见 [重载实测](testing-reload.md)。这不是厂商业务或稳定版验收。


三独立百分比、CLI比例/日志目录优先、坏配置保持、遗漏项回20、manual切换及外部冲突的[15项持续重载实测](testing-three-percent-reload.md)对应d6ea657程序，不能改称新分区程序的真机重载执行记录。从manual启动且没有可用profile时，热切换为百分比不会启动测速；IO明确降级，需受控重启可选Agent进入首次自动标定流程，业务仍独立运行。
