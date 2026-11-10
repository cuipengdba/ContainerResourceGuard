# 开发进展（2026-11-10）

> 最新范围：R29只保留CPU/内存/IO独立百分比，各默认20；R30设置前检查cgroup（v1跳过、v2校验）。日志保留，诊断/热重载/升级等深入功能继续。历史扩展资源规划暂缓。详见[当前配置](independent-percentages.md)和[下一版交付](next-version.md)。

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

30% 限额引擎回归出现临时备库退出/探测超时；手动 16MiB/s + 256 IOPS 回归出现原主库连接失败与数据库内部重启，两轮均失败。第三轮 16MiB/s + 4096 IOPS 明确新手动预算，两类业务共 20 项短测通过且主库未重启；清理等待 120s 超时保留，后续独立核对确认真实原值/observe 和 SQL 正常，见 [包含失败的报告](testing-vendor-enforce.md)。已开发 [原生持续负载入口与判定条件](continuous-acceptance.md)，已完成 fresh/reuse、600s 原生/周期组合短测；24h observe 基线已于中国时间 2026-11-10 07:25:53 开始，尚未完成。

安装升级的 [开发分支](https://github.com/cuipengdba/ContainerResourceGuard/tree/next/install-upgrade) 已实现持锁兼容预检和显式私有原值备份，16 项真实检查通过；新 CLI 暂停旧版 Agent 的 20 项检查通过。显式二进制安装/回退已完成 16 项真实往返检查，保留两轮开发失败，限额、真实原值和 PID 1 保留，见该分支的 [升级结果](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/install-upgrade/docs/testing-upgrade-check.md)。已开发 supervisor 摘要/结构/语法预览、私有备份、原子接入和有资源恢复门槛的卸载，真实接入及持久化演练正在进行，见 [接入设计](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/install-upgrade/docs/supervisor-install.md)。不把已有二进制往返等同厂商业务在线升级或未知日志自动迁移。三组实际 30 分钟低 IO/持续故障测试已按原判定通过，见 [开销结果与边界](overhead-acceptance.md)。

DBS observe 初始化约 25s，20% 在预设 300s 内未就绪，30% 初始化约 251s；首轮重建探测超时保留，后续独立复测两次就绪约 205s/211s，128 行标记校验一致，新身份和旧日志隔离均确认。HISDBS observe 约 20s，20% 超过 300s，30% 初始化约 250s、备份后重建约 204s。详见 [保留失败的冷启动进展](testing-cold-start-progress.md)。实际原 liveness 只执行 ls，不能把它与 SQL/API 就绪条件等同。

后续按十版安排继续补齐多设备竞争、缓存高峰、环境矩阵、安装升级、构建来源和兼容契约。跨周期内存窗口已有 11 项真实检查；io_weight、memory_high、memory_swap_max 和本地观测功能仍只在开发分支，尚未合入 main 或发布；RC2 不接受这些字段。

24h observe 基线正在运行；24h 限额对照、arm64 真机、实际多设备及 1.0 的至少 7 天目标业务验收均未完成。完成源代码、通过短测或创建版本标签都不能替代持续运行和真实业务证据。业务节点当前只读检查，未修改其部署和控制文件。


可信发布的 [开发分支](https://github.com/cuipengdba/ContainerResourceGuard/tree/next/release-provenance) 已完成固定工具链、逐架构 SBOM、14 项包完整性正反检查、官方 schema 核对和另路径复现。GitHub 实际生成 provenance 与 SBOM 证明，限定仓库/工作流/源码/ref 的四项在线验证及三个错误身份/篡改反例均通过；预取可信根与 bundle 后，正确离线验证和三个反例通过。首轮缺 serialNumber 的 CI 失败保留。跨宿主首轮校验和因 CRLF/LF 不同；274ec3c 明确输出 LF 后，Windows 新克隆与 Linux CI 的两程序、两包、两 SBOM、清单、校验和共八项字节一致，见 [证据与边界](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/release-provenance/docs/release-provenance.md)。来源证明不代替功能或长期业务验收；这些开发分支仍未合入 main 或发布。


## 组合候选补充记录

[next/compatibility-contract](https://github.com/cuipengdba/ContainerResourceGuard/tree/next/compatibility-contract) 已组合后续开发代码，并汇入 main 的业务证据与持续测试入口，尚未合入 main 或发布。该分支已经补齐配置表中的五项可选控制和观测参数、热重载/维护手册以及[兼容契约草案](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/docs/compatibility-contract.md)。固定 Go1.27.3 的实际程序完成[31项独立容器维护检查](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/docs/testing-combined-maintenance.md)，包括接入后六种辅助故障、真实限额/原值恢复、持久重建、永久卸载及锁/维护错误码；Go1.22.5最低源码工具链与Go1.27.3 CI分别归档。相同候选的三组30min预算和两个解析器各10min fuzz已完成；含R26的74693候选两个解析器也各完成10min fuzz，见[独立结果](testing-combined-long.md)，不同源码的开销证据不混用。

正式24h observe基线仍在运行，24h enforce和至少7天业务验收未开始；最新采样与最终判定分开，未发布1.0。业务节点保持只读，厂商专用接口、真实掉电及未测硬件组合不扩成已验证范围。

## 最新追加：真实路径与自动标定

R25/R26与P01.7/P10.5已归档，十版任务增加到48项。当前RC3及1.0组合开发线已编写默认自动选盘/首次标定/稳定身份复用，实现与验收状态分别记录；原24h基线容器不改动。详见[自动标定设计](automatic-io-calibration.md)。

最新证据：两候选默认自动标定22项、真实满/只读状态9项检查通过；首轮失败完整保留，Linux/race及CI通过。见[自动IO实测](testing-automatic-io.md)。真实路径业务仍按独立报告判定。

真机路径前两轮脚本超时保留；后续证实直接以root运行就绪探针缺libpq库路径，数据库实际已接受连接。修正为postgres原登录环境的新夹具保持30%和300秒预算，DBS约53.12秒、HISDBS约63.62秒就绪且managed，两套自动30%业务短测均失败；原路径手动16MiB/s DBS、HISDBS均跑满600秒，分别因1次、2次SQL错误失败；HISDBS早先观察脚本失败单独保留。新64MiB/s手动矩阵执行中；在线升级等待四组合通过，尚未执行。见[诊断与真实路径进展](testing-realpaths-progress.md)。

组合候选长时工程检查已归档：1bc9三组实际30min及其两项10min fuzz、含R26的74693两项10min fuzz通过；不等同业务长期验收，见[源码分别列明的结果](testing-combined-long.md)。

原路径手动对照的失败、探针修正与新预算冻结计划见[手动测试记录](testing-realpaths-manual.md)。

自动标定候选的真实路径辅助故障测试已完成：RC3/DBS与组合候选/HISDBS各10场景，共108项检查通过，夹具全部清理；不代替业务性能与长时验收。见[故障实测](testing-realpaths-faults.md)。

## R27 / R28 追加（总计52项）

| 任务 | 内容 | 当前状态 |
|---|---|---|
| P01.8 / P10.6 | RC3及1.0组合线：默认每日日志、30天及总1GB清理、失败放行 | 已实现并本地测试；Linux及业务实测待归档，未发布 |
| P01.9 / P10.7 | RC3及1.0组合线：仅CPU/内存/IO独立百分比，各默认20；v1跳过、v2校验设置；旧配置兼容及manual保留 | 已实现并本地测试；Linux回读/恢复/重载/业务验收待归档，未发布 |

用户已要求优先开发。R29已取消扩展资源的默认接管，R30要求设置前先检测cgroup；原安全保护保留；原P04/P05深入验证、24h+24h、>=7d及未测硬件门槛保留。设计及参数见[独立百分比](independent-percentages.md)、[每日日志](logging.md)。

## R29 / R30 当前任务

保留52项任务索引。P01.9/P10.7收窄为三百分比并新增版本门禁验收（v1/混合/未知不写、v2权限及实际回读）；P01.8/P10.6日志继续保留。扩展资源交付暂缓，原诊断、热重载、升级、身份与长期验收继续，不以源码完成替代业务门槛。工程预览与正式RC3/1.0分开标记，见[交付说明](next-version.md)。
