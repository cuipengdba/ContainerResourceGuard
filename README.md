# ContainerResourceGuard

ContainerResourceGuard（CRG）在容器内部控制当前容器的 CPU、内存和 IO。**一个容器一份 Agent**，DBS 与 HISDBS 分别运行；无需 Operator、CRD、Docker socket 或 Kubernetes API。容器或 Pod 重建后重新发现自身 cgroup，不需要保存或手改旧 ID。

当前交付：[v1.0.0-preview.5 工程预览及下载](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v1.0.0-preview.5)。[逐容器升级步骤](docs/upgrade-preview4-preview5.zh.md)说明下载校验、配置/profile/journal保留、安装及回退。八项公开附件已[实际下载校验](docs/test-results-preview5-publication.json)，后续补充测试不替换已发布文件。

## 快速使用

百分比模式只需以下配置；省略的每一项各默认 **20%**，最小配置为`{}`。

```json
{"cpu_percent":30,"memory_percent":40,"io_percent":25}
```

| 参数 | 计算基准与控制文件 |
| --- | --- |
| `cpu_percent` | 宿主在线逻辑CPU容量，写`cpu.max` |
| `memory_percent` | 宿主`MemTotal`，按页取整后写`memory.high`，用于回收/节流 |
| `io_percent` | 自动标定读/写带宽，写`io.max`的`rbps/wbps`；IOPS留给手动模式 |

百分比取值大于0且不超过100，可填小数。CPU/IO上限不是资源预留；多个容器的比例之和由部署者配置，每份Agent只控制自身。IO百分比是实测基准的百分比，不是磁盘固定物理极限或吞吐保证；已有外部IOPS保留，旧CRG自有IOPS仅在身份、设备、journal及当前值保护均成立时恢复原值。

手动模式为每项填写绝对值，省略的项不管理，例如：

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

手动模式的目录用于明确设备；默认百分比模式不要求指定测速目录。详见[配置参数](docs/configuration.md)、[独立百分比](docs/independent-percentages.md)和[双模式](docs/resource-modes.md)。

安装发布包并保存独立配置后，在每个容器内部运行：

```sh
crg doctor --config /etc/crg/config.json --format human
crg preflight --config /etc/crg/config.json --format human
crg run --config /etc/crg/config.json
crg status --config /etc/crg/config.json --format human
```

`doctor`只读；`preflight`只检查写入口可打开，不写限额；`run`默认enforce。原`start.sh`/supervisor异步启动可选helper，然后独立启动原业务和缓存程序，业务不等待标定完成。具体见[容器接入](docs/integration.md)，不要直接把前台`crg run`作为业务启动的等待条件。

## 业务优先

先识别cgroup版本：**纯v2才设置**；v1、混合、无法确认、只读或权限不足都记录具体跳过/降级原因。辅助程序缺失、配置错误或崩溃不决定业务容器退出。CRG不改原DBS/HISDBS启动参数或缓存程序策略。

`memory.high`触达后由内核回收/节流，允许超过目标。CRG不新增`memory.max`硬上限；已有运行时/Pod硬上限继续有效，宿主内存不足或触达原硬上限仍可能OOM，不能保证任意内存都可被释放。

Agent退出不会自动撤销已生效的内核限额。需要解除自身限制时使用`crg disable --config /etc/crg/config.json`并核对实际恢复结果；外部改写的值不会被强制覆盖。见[本地运维](docs/operations.md)。过低的CPU/IO额度或内存回收目标会拖慢业务，默认20%不是对任意数据库负载的性能承诺。

## 自动标定与日志

默认在容器内选择容量最大的合格、可写本地磁盘文件系统，使用独立临时测试文件做三样本标定，保存基准后按设备身份复用；无需手工执行带directory/output参数的标定命令。测速有真实IO负载，不改业务文件；设备不明确、标定失败、只读或缺少权限时明确降级。规则和局限见[自动IO标定](docs/automatic-io-calibration.md)。

程序打印结构化运行日志，按容器本地日期**一天一个文件**，默认保留30个日历日、总量超过1GB时清理旧日志；文件权限0600。写日志失败仍放行业务。见[日志参数与清理规则](docs/logging.md)。配置、profile、状态和日志应使用各容器自己的持久化目录，以便Pod重建后继续使用。

## 支持范围

- Linux cgroup v2；提供静态linux/amd64与linux/arm64二进制。
- 仅发现并管理自身，不接受其他容器、目标PID或目标cgroup参数。
- 不改父级Pod、不创建业务子cgroup、不移动进程；已有上层限制继续有效。
- v1/混合/未知及控制器不可用时安全跳过；不能把降级状态称为三项均受控。

[DBS/HISDBS 20%与30%的四种启动组合](docs/testing-bandwidth-current-combinations.md)分别完成各36项、包含重建后新ID、原探针、逻辑备份/恢复及原值恢复。它们来自不同隔离任务，不把保留的失败矩阵改判通过。准确源码已通过52项实际cgroup与180项分区CI，分区不等于独立物理多盘。

完整持续业务、正式升级、独占24h与七天老化等仍按原门槛验收；默认20%持续业务测试已观察到SQL超时，不能据启动检查称业务性能已接受。最新结果和已知限制统一见[当前验收入口](docs/current-acceptance.md)。**稳定v1.0.0尚未发布。**

[手动参考预算完整业务终态](docs/testing-manual-reference-full600-terminal.md)：通过，16/16项；两角色原600秒及备份同步恢复独立判定。默认20%的失败仍保留，手动结果不替代长期或稳定1.0验收。

[preview.4→preview.5在线维护验收](docs/testing-preview45-manual-maintenance.md)已冻结并预检，尚未取得业务终态。

## 文档

| 文档 | 内容 |
| --- | --- |
| [全部需求](docs/requirements.md) / [开发任务](docs/tasks.md) | 需求归档、实现与验证状态 |
| [后续十版规划](docs/roadmap.md) | 十版、原52项任务和发布条件 |
| [下载与升级](docs/upgrade-preview4-preview5.zh.md) | 当前逐容器安装、校验、升级和回退 |
| [配置](docs/configuration.md) / [重启ID](docs/restart-behavior.md) | 两种配置模式、自身发现和持久化 |
| [架构](docs/architecture.md) / [接入](docs/integration.md) | 一对一、原启动链与故障降级 |
| [运维](docs/operations.md) / [排查](docs/troubleshooting.md) | 状态、停用、冲突和恢复 |
| [当前验收](docs/current-acceptance.md) | 准确测试范围、失败与未完成条件 |
| [历史README](docs/readme-history-before-preview5-overview.md) | 完整保留此前各时点记录，仅调整相对链接 |
| [变更记录](CHANGELOG.md) / [安全边界](SECURITY.md) | 版本与权限边界 |

## 构建和测试

新策略准确产品源码为`ced461705ebc27315a59aefe463f9b4af47130a3`，发布标签文档打包提交为`d32987af8c02319f949b2e7bcc1429d598553921`。main与旧开发分支的程序尚未合并到新策略；部署请使用发布包。复现新程序时检出准确产品源码，使用固定Go1.27.3：

```sh
git checkout ced461705ebc27315a59aefe463f9b4af47130a3
go test -race ./...
go vet ./...
bash scripts/build.sh v1.0.0-preview.5
```

BUILD.json分别记录产品源码与文档打包身份；工程CI、厂商业务及长期验收不能互相替代。标准库实现，无第三方运行时依赖。MIT License。
