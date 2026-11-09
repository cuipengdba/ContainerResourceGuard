# 开发进展（2026-11-10）

本文件区分已发布、开发完成与仍需验收的事项。当前公开发布仍为 `v0.1.0-rc.2`，没有发布 RC3、v0.2 或 1.0。

## 已完成并有证据

- 重启身份设计及百分比/手动两种模式、五个额外可选参数已纳入 [46 项任务的十版规划](roadmap.md)。
- main 已实现双模式 CPU/内存/IO、可选 pids_max 和 cpu_weight；[22 项分阶段 Linux 验证](testing-dual-modes.md) 已归档，包含新 Pod 身份发现、真实硬限额和恢复原值。原失败记录保留。
- 已补充 [有界任务耗尽及 CPU 权重竞争](testing-pids-weight.md)：耗尽后 PID 1 存活并能恢复真实原值；8s 权重测试失败，30s 沿用相同区间通过，两个阶段均归档。
- [next/safe-reload 分支](https://github.com/cuipengdba/ContainerResourceGuard/tree/next/safe-reload) 提前开发 v0.2。源码 8401515 的 [CI](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42676218251)、Linux race/vet、辅助进程故障与建模强杀回归通过；13 项真实 cgroup 重载验证通过。见该分支的 [详细报告](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/safe-reload/docs/testing-reload.md)。功能尚未合入 main 或发布。
- DBS/HISDBS 原镜像已只读导出到隔离测试节点，传输摘要与各自原镜像 config digest 核对通过。未把厂商镜像、业务数据或脚本纳入公开仓库。
- 原镜像启动链、SQL 和 POST /test 已通过，保留主库 8960MB shared_buffers；CRG observe 与原缓存程序 enforce 共存。两种业务的备份、流复制及独立恢复共 18 项短测通过，见 [结果与边界](testing-vendor-backup.md)。尚未证明限额模式下的性能。
- [IO 开发分支](https://github.com/cuipengdba/ContainerResourceGuard/tree/next/io-controls) 已实现默认 io.weight、重复标定、质量检查与 profile 合并；[内存开发分支](https://github.com/cuipengdba/ContainerResourceGuard/tree/next/memory-pressure) 已实现 memory_high/memory_swap_max。16 项联合控制/工具实测见该分支 [报告](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/memory-pressure/docs/testing-memory-io.md)。内核拒绝设备权重后端时如实记录，不把默认值回读当作竞争效果。
- [环境开发分支](https://github.com/cuipengdba/ContainerResourceGuard/tree/next/environment-checks) 已实现宿主容量来源校验；无法确认总量时跳过对应百分比维度，保留手动绝对值与恢复能力。Linux race/vet、启动故障检查及分阶段 37 条真实检查记录已归档，包含五次连续重建和单独只读命名空间测试，见该分支 [报告](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/environment-checks/docs/testing-environment.md)。硬件矩阵仍未完成。
- [诊断开发分支](https://github.com/cuipengdba/ContainerResourceGuard/tree/next/local-diagnostics) 已开发按需内存分类、白名单诊断、输入保护、可选本地指标/有界事件及逐项原因码。已有 16 项原镜像只读诊断、10 项指标检查、11 项真实内存窗口检查和新二进制 17 项指标/事件联合检查，Linux race/vet、短时 fuzz 及强杀回归分别归档；命令级统一原因与长时门槛仍未完成。
- [原镜像故障及回退](testing-vendor-faults.md) 两轮各 14 场景完成：SQL/API 与 TERM 通过，后轮确认原缓存进程/enforce 与随后 SQL。前轮早期缓存 false 快照保留；所有本次临时 Pod 已移除。

## 当前开发与验收

接下来使用原镜像克隆补齐 enforce 冷启动、探针、相同负载和辅助故障回归。POST /test 与引擎备份结果不能代替尚未提供的厂商专用业务接口验收。

30% 限额引擎回归出现临时备库退出/探测超时；手动 16MiB/s + 256 IOPS 回归又出现原主库连接失败与数据库内部重启，两轮均失败。真实原值和 observe 已恢复，容器未重建、随后 SQL 正常，见 [失败报告](testing-vendor-enforce.md)。已明确另测 4096 IOPS 新手动预算，新增主库启动时间对比；不替换原失败。已开发 [原生持续负载入口与判定条件](continuous-acceptance.md)，短时 fresh/reuse 验证待完成，24h 尚未开始。

DBS observe 初始化约 25s，20% 在预设 300s 内未就绪，30% 初始化约 251s；首轮重建探测超时保留，后续独立复测两次就绪约 205s/211s，128 行标记校验一致，新身份和旧日志隔离均确认。HISDBS observe 约 20s，20% 超过 300s，30% 初始化约 250s、备份后重建约 204s。详见 [保留失败的冷启动进展](testing-cold-start-progress.md)。实际原 liveness 只执行 ls，不能把它与 SQL/API 就绪条件等同。

后续按十版安排继续补齐多设备竞争、缓存高峰、环境矩阵、安装升级、构建来源和兼容契约。跨周期内存窗口已有 11 项真实检查；io_weight、memory_high、memory_swap_max 和本地观测功能仍只在开发分支，尚未合入 main 或发布；RC2 不接受这些字段。

24h 基线/24h 限额运行、arm64 真机、实际多设备及 1.0 的至少 7 天目标业务验收均未完成。完成源代码、通过短测或创建版本标签都不能替代持续运行和真实业务证据。业务节点当前只读检查，未修改其部署和控制文件。
