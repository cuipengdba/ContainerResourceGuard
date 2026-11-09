# 故障排查和恢复

先执行 `crg doctor --percent 20`，再检查 `crg status` 中的 `time_utc`、`state`、逐项结果与 warnings。doctor 为只读计划，不会替代真实写入验证。

| 现象 | 含义与处理 |
|---|---|
| `permission denied` / `read-only file system` | 没有自身 cgroup 写权限，保持业务运行；由部署维护者提供受控写权限 |
| `host root ... refusing mutation` | 在宿主根执行或缺控制器；不写宿主根、不自动启用父控制器 |
| `self and container PID 1 differ` | 可能处在业务子组或 hostPID 环境，拒绝不明确目标 |
| `IO unmanaged: profile unavailable` | 尚未分发标定文件，CPU/内存可继续独立管理 |
| `calibrated device missing or ambiguous` | 设备身份变化或该设备在容器内不可见，需要核对/重标定 |
| `unsafe memory decrease...` | 内存余量/增长、events 或 PSI 不适合下调，本轮跳过；核对目标和负载 |
| `conflict` | 外部改写了同一控制项，CRG 暂停该项，保留外部值 |
| `lock unavailable` | 当前 cgroup 或状态目录已被控制操作持锁；不同 state_dir 也不能再启动一份 RC2 |
| `invalid journal` / 持久化失败 | 无法保证恢复依据，停止新增写入，检查目录和磁盘 |
| `degraded` | 有跳过、冲突或 IO 基准缺失，不能当成三项全部受控 |

## 停用

RC2 推荐：

```bash
crg disable --config /etc/crg/config.json
crg status --config /etc/crg/config.json --format human
```

停用标记阻止原辅助循环重新施加限额；有外部冲突时返回非 0，外部值保留。重新启用用 enable；具体行为见 [运维说明](operations.md)。

使用底层 restore 时，先让现有 supervisor 停止并不再重启 CRG 辅助管理循环，再执行：

```bash
crg restore
# 自定义过目录时必须使用同一目录
crg restore --state-dir /tmp/crg-state
```

恢复只作用于当前自身 cgroup 和自己仍持有的字段，不能删除整个组或清空全部外部 IO 设置。发生冲突时人工核对外部管理者与状态日志，不能盲目把限制改成 max。

Agent 崩溃、被 kill -9、权限被撤销后，已生效限制仍在。此时不能承诺立即自动恢复；需要有权限的维护者处理，或者在确认新的外层配置后正常重建容器。

状态目录的日志仅用于当前容器，不能人工复制成另一个容器的恢复依据。容器重建时身份校验会归档旧日志并从当前控制值建立新基线。

## 外部资源管理

Kubernetes resources 是调度/运行时声明，内部写入不会更新它。要避免 kubelet 更新与 CRG 同时管理相同字段。CRG 检测到外部变化会让出该项，不无限覆盖。
