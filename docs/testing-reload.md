# v0.2 开发分支重载实测

日期：2026-11-10。源码 `840151595dc6570430bda2715b1c7128a122a69e`，版本标识 `v0.2.0-dev`，amd64 二进制 SHA256 `bc3b12543f9396fb5ff5aab2d859b2220e47aa930e4b1058d6197d00976e8ddd`。该版本尚未发布；不替代 RC3/稳定版的原业务验收。

环境为 Linux 5.14.0-570.22.1.el9_6 / cgroup v2 / containerd / amd64，独立测试 namespace、状态和数据目录。使用已缓存厂商镜像承载占位业务命令，**未运行原 start.sh、厂商 API 或缓存程序**。本报告验证自身 cgroup 的控制和重载行为。

## 自动检查

- Linux Go 1.22.5：`go vet ./...`、`go test -race -cover ./...`，guard 覆盖率 62.3%。包含 16 个临时文件建模的真实子进程 SIGKILL 检查点，不等价于对每个 cgroup 写系统调用强杀。
- `tests/supervisor.sh` 与 `tests/integration-patch.py` 共 12 个场景，缺程序/拒绝执行/坏配置/崩溃/卡住/忽略 TERM 时，占位业务保留退出码 37，原缓存占位辅助仍可启动。
- [GitHub CI](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42676218251) 通过。

## 真实 cgroup：13 项通过

| 场景 | 结果 |
|---|---|
| 初始五类控制 | 手动 CPU、内存、IO、pids、CPU 权重应用并回读 |
| 显式请求提前触发 | 配置周期 60s，CPU 1→2 核，约 1.42s 接受第 2 代 |
| 坏配置 | 有效 CPU 限额与 journal 摘要不变，配置 rejected |
| 移除内存/IO/pids | 恢复日志记录的真实原值；保留 CPU 所有权；权重变更成功 |
| enforce→observe | CPU/权重不写、不撤销 |
| observe→enforce | 新 CPU/权重生效 |
| manual→percent | 20% 产生 4.8 核；移除权重恢复原值 |
| profile 丢失 | 原 IO 硬限额保持，状态 retained/degraded |
| profile 恢复 | 无业务重启，返回受管状态 |
| 更换状态目录 | 拒绝候选，保留原目录和有效限额 |
| 外部 CPU 改值 | 保留外部 1.5 核，报告 conflict |
| disable 与重载同时待处理 | disable 优先；其他自有项恢复，外部 CPU 保留 |
| 目标隔离与业务存活 | 另一容器限额未变，两个业务 PID 1 存活 |

测试 namespace 和数据目录均已删除，源码、二进制、日志和原值证据保留在测试节点私有目录。机器可读结果见 [JSON](test-results-reload-linux-amd64.json)。

## 未完成

自动文件轮询在默认周期内的真实延迟、真实内存压力下多轮延后、ConfigMap 在真实 Kubernetes 挂载上的切换、慢/满状态盘与并发重建的组合测试还需补齐。Linux 单元测试覆盖普通符号链接原子切换与 FIFO。首次真正支持范围仍以发布时验收矩阵为准；厂商业务与长期验收继续独立执行。
