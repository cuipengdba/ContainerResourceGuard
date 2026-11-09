# 原镜像按需诊断实测（未发布）

2026-11-10，诊断源码 c3a2071，SHA256 `b0b0cc9e763056184fb3fae08d3d8a9870ba95fa53728038d8f1148787c5291b`。在两个原厂镜像隔离业务副本中执行，每种业务 8 项，共 16 项通过，见 [JSON](test-results-diagnostics-linux-amd64.json)。原资源 Agent 仍为 fc2e26d/observe，本次没有切换运行中业务的资源 Agent。

实测包括：读取既有状态并采集实时内存；PSI 缺失明确不可用；诊断白名单不带入测试凭据、业务路径、容器 ID 或完整 cgroup 路径；显式输出约 1.8KiB 的 0600 新文件；拒绝覆盖已有输出；拒绝在状态目录输出；CPU/内存/IO 控制值不变且业务 PID1 存活；只删除本次新建诊断文件。

Linux Go 1.22.5 vet/race、16 个建模 SIGKILL 检查点和 12 个辅助启动故障检查通过，guard 语句覆盖率 70.8%。配置 fuzz 30s/740,305 次，profile fuzz 31s/542,052 次，均无失败；后者请求 30s，实际含结束阶段约 31s。[CI](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42691163930) 通过。

这些是短时证据，不替代长时模糊/故障测试、真实掉电或 Agent 开销预算。该二进制早于 5c707d9 的 metrics_enabled 实现，不能据此宣称本地指标已完成真实验证。最新代码需另跑竞态、强杀和指标文件故障矩阵。
