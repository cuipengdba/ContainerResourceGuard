# ContainerResourceGuard

容器内运行的轻量资源控制程序，简称 **CRG**。严格 **一个容器、一份 Agent、独立控制自身资源**。无需 Operator、CRD、Docker socket 或 Kubernetes API 权限。

只设置一个总百分比：

```json
{"percent":20}
```

- CPU：宿主机在线逻辑 CPU 数 × 20%，转换为整个容器共享的 CPU 时间配额。
- 内存：宿主机 `MemTotal` × 20%，转换为整个容器的内存硬上限。
- IO：已标定设备的读写 BPS、读写 IOPS 基准分别 × 20%，通过 `io.max` 设置硬上限。

**IO 的百分比是特定测试方法的实测基准百分比，不是磁盘固定物理极限。没有可用标定文件就显示 IO 未管理，不用竞争权重冒充硬限速。**

## 快速使用

在维护窗口、明确的块设备数据目录中显式标定一次：

```bash
crg calibrate --directory /data --output /etc/crg/io-profile.json
```

标定只使用新建的 128 MiB 临时普通文件，执行短时 direct IO，结束后删除；不会打开数据库文件、写裸设备或清理全局缓存。运行中业务容器不会自动测速。多个数据设备见 [IO 标定](docs/io-calibration.md)。

在每个目标容器内部执行：

```bash
# 只读检查与预览；不写限额
crg doctor --percent 20

# 当前容器持续管理；percent 同时作用于三类资源
crg run --percent 20

# 也可使用仅包含 percent 的配置文件
crg run --config /etc/crg/config.json

# 本容器状态
crg status --format human

# 安装预检（只打开/关闭写入入口，不写资源值）
crg preflight --percent 20 --format human
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

后续设计：[双资源模式与五个可选参数](docs/resource-modes.md)；[容器/Pod 重启 ID 处理](docs/restart-behavior.md)。交付状态以任务和发布报告为准。

| 文档 | 内容 |
|---|---|
| [全部需求](docs/requirements.md) | 用户需求、约定与边界，逐项编号 |
| [开发任务](docs/tasks.md) | 实现、验证状态和证据 |
| [后续十版规划](docs/roadmap.md) | 从 RC3 到 1.0 的十个版本、40 项任务与发布条件 |
| [配置](docs/configuration.md) | 一个 percent 的语义与所有可选参数 |
| [安装与升级](docs/installation.md) | 架构选择、持久部署、校验、升级和回退 |
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
