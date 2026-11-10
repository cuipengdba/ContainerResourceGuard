# ContainerResourceGuard


[v0.1.0-rc.3-preview.1工程预览及下载](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v0.1.0-rc.3-preview.1)以R29/R30为准：只暴露三个独立资源百分比，cgroup v1跳过/v2校验设置，日志保留。两线38项隔离工程检查通过；发布范围与实测见[最新版本说明](docs/next-version.md)，正式业务与长期验收继续。

容器内运行的轻量资源控制程序，简称 **CRG**。严格 **一个容器、一份 Agent、独立控制自身资源**。无需 Operator、CRD、Docker socket 或 Kubernetes API 权限。

CPU、内存、IO分别设置百分比，省略的资源项各自默认20%。最小配置`{}`，也可单独调整：

```json
{"cpu_percent":30,"memory_percent":40,"io_percent":25}
```

仅限制这三个资源，其他资源保持原值；先识别cgroup，v1跳过、v2校验后设置，详见[独立百分比](docs/independent-percentages.md)。CPU/内存取宿主容量，IO取自动标定基准；不需手动填写核数、字节或测速目录。

**IO 的百分比是特定测试方法的实测基准百分比，不是磁盘固定物理极限。没有可用标定文件就显示 IO 未管理，不用竞争权重冒充硬限速。**

## 快速使用

当前 RC3 / 1.0 开发候选已改为默认自动选盘：CPU、内存、IO独立百分比默认各20。原 supervisor 异步启动 CRG，首次选择容器内容量最大的合格可写本地磁盘文件系统并保存基准，重启后复用；不必手工指定目录或输出路径。业务和缓存程序独立启动，失败不阻断业务。已发布 RC2 仍是原显式标定行为。

测速只使用独立128MiB临时普通文件，不改业务文件；存在真实IO负载，额外设备覆盖不自动假定。只读、无稳定设备身份或已有限速等情况会明确降级。规则与验收状态见[自动IO标定](docs/automatic-io-calibration.md)。

在每个目标容器内部执行：

```bash
# 只读检查与预览；不写限额
crg doctor

# 当前容器持续管理；各资源默认20%
crg run

# 也可使用最小{}或分别填写百分比的配置文件
crg run --config /etc/crg/config.json

# 本容器状态
crg status --format human

# 安装预检（只打开/关闭写入入口，不写资源值）
crg preflight --format human
```

先观察时用 `examples/observe.json`。`run` 的默认模式是 **enforce**；`doctor` 始终只读。运行时不热加载配置，修改后仅重启辅助 Agent。

## 业务优先

CRG 是可选辅助进程。原业务必须独立启动；无权限、只读 cgroup、程序不存在、配置错误、Agent 崩溃，不能决定业务容器退出。使用 [集成示例](docs/integration.md)，不要把 CRG 设为业务启动前置条件或健康探针。

资源限额由内核执行，**Agent 退出不等于撤销已写入限额**。过低的 CPU/IO 会影响性能，过低的内存可能 OOM。RC2 可用 `crg disable --config /etc/crg/config.json` 协调停用并恢复；外部已经改写的值不会被强制覆盖。详见 [本地运维](docs/operations.md)。

## 支持范围

- Linux cgroup v2，静态 Linux amd64 / arm64 二进制。
- 自动从 `/proc/self/cgroup` 与挂载信息发现自身 cgroup；重建后重新发现。
- 不接受其他容器、目标 PID 或目标 cgroup 参数；不扫描其他容器。
- 不改父级 Pod、不创建业务子 cgroup、不移动进程、不修改缓存控制策略。
- cgroup v1、缺少控制器或无法确认目标时安全降级，不能声称三项均已受控。
- 上层 Pod/运行时限制继续有效；CRG 不提高既有外部硬上限。
- 百分比是每容器独立上限，不是资源预留，也不保证获得对应吞吐；多个容器比例之和不由 CRG 协调。

## 文档

后续设计与历史兼容：[双资源模式（扩展资源暂缓）](docs/resource-modes.md)；[容器/Pod 重启 ID 处理](docs/restart-behavior.md)。交付状态以任务和发布报告为准。

持续开发与验收状态见 [当前进展](docs/development-status.md)。安全热重载已在独立分支通过 13 项真实 cgroup 检查，尚未发布；原镜像业务验收正在推进。

开发分支已加入手动模式入口，例如 `{"resource_mode":"manual","limits":{"cpu_cores":2.5,"memory_max":"4GiB"}}`。完整示例见 [manual.json](examples/manual.json)，无需 IO 的示例见 [manual-cpu-memory.json](examples/manual-cpu-memory.json)。新增功能已完成 [Linux 隔离限额与恢复验证](docs/testing-dual-modes.md)，厂商业务验收仍未完成；已发布 RC2 仅支持原字段。

| 文档 | 内容 |
|---|---|
| [全部需求](docs/requirements.md) | 用户需求、约定与边界，逐项编号 |
| [开发任务](docs/tasks.md) | 实现、验证状态和证据 |
| [后续十版规划](docs/roadmap.md) | 从 RC3 到 1.0 的十个版本、52 项任务与发布条件 |
| [配置](docs/configuration.md) | 三项独立百分比默认20、手动模式与日志 |
| [安装与升级](docs/installation.md) | 架构选择、持久部署、校验、升级和回退 |
| [安装接入开发](docs/supervisor-install.md) | 摘要预览、私有备份、可选接入和有恢复门槛的卸载 |
| [可信发布开发](docs/release-provenance.md) | 固定工具链、SBOM、来源证明及离线验证的真实证据 |
| [1.0 兼容契约草案](docs/compatibility-contract.md) | 配置/CLI/日志兼容、原因码与维护边界；尚未发布 |
| [本地运维](docs/operations.md) | 预检、人类可读状态、停用/启用、低频状态与覆盖范围 |
| [架构](docs/architecture.md) | 一对一发现、写入、恢复和冲突处理 |
| [容器接入](docs/integration.md) | 原 start.sh / supervisor / 缓存控制关系 |
| [IO 标定](docs/io-calibration.md) | 方法、设备绑定、多设备和局限 |
| [故障排查](docs/troubleshooting.md) | 权限、内存保护、冲突、重建和停用 |
| [测试报告](docs/testing.md) | 实际执行范围、证据、局限 |
| [安全与运维边界](SECURITY.md) | 权限、自身目标和数据保护 |
| [变更记录](CHANGELOG.md) | 版本与已知限制 |

## 构建和测试

```bash
go test -race ./...
go vet ./...
bash tests/supervisor.sh
python3 tests/integration-patch.py
bash scripts/build.sh dev
python3 scripts/package.py dev
python3 scripts/check-package.py dev
```

标准库实现，无第三方运行时依赖。最低 Go 版本见 `go.mod`。MIT License。

运行日志默认每天一个文件，保留最近30个日历日，总量不超过1GB，写日志失败仍放行业务。详见[每日日志](docs/logging.md)。旧percent配置仅作兼容；上述功能已随工程预览发布，后续深入功能仍在开发，正式业务/长期验收状态见任务清单。
