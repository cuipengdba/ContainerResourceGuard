# 开发进展（2026-11-11）

> 最新范围：R29只保留CPU/内存/IO独立百分比，各默认20；R30设置前检查cgroup（v1跳过、v2校验）。日志保留，诊断/热重载/升级等深入功能继续。历史扩展资源规划暂缓。详见[当前配置](independent-percentages.md)和[下一版交付](next-version.md)。

本文件区分已发布、开发完成与仍需验收的事项。本次交付`v0.1.0-rc.3-preview.1`工程预览；正式RC3、稳定版、v0.2和1.0仍未发布，原RC2保持历史基线。

## 当前结果与边界

| 项目 | 当前结论 | 证据 |
|---|---|---|
| 已发布工程预览 | 只三项独立百分比、cgroup版本门禁、每日日志；正式RC3/1.0未发布 | [交付与下载](next-version.md) |
| 新程序工程检查 | 38项通过；真实控制为v2，v1/混合/未知为隔离proc模拟 | [版本/日志/三资源](testing-three-percent-cgroup-logs.md) |
| 新程序原业务手动64预算 | 四格各600秒，24项通过 | [业务矩阵](testing-three-resource-business-matrix.md) |
| 新程序默认20% | 第16/18轮四格业务组合均失败；两个组合格只有未完成原生快照 | [首格](testing-three-resource-default20-business.md)、[补测](testing-three-resource-default20-supplement.md) |
| 备份后新Pod ID | 四格8次原启动、88项通过，数据/日志/原值保持，仅手动64预算 | [冷重建](testing-three-resource-cold-rebuild.md) |
| 在线维护 | 第13轮已发布预览首次安装拒绝；第15轮两套协议兼容开发构建22项/各600秒通过，不代表两个已发布次版本 | [拒绝记录](testing-three-resource-online-maintenance.md)、[开发构建往返](testing-three-resource-protocol-maintenance.md) |
| 分区接入前d6程序开销 | 三场景各1800秒、181样本通过；仅其占位PID1工程结果，不能沿用为新分区程序 | [三资源/日志开销](testing-three-resource-steady-overhead.md) |
| 当前分区组合d3706f3 | 原生ARM212个Go pass事件、实际整盘44项及构建身份9项通过；自身三场景1800秒开销及DBS/HISDBS各600秒/12项通过且清理；当前辅助故障108项、维护22项/两格600秒、冷重建44项/四次启动通过且清理 | [当前提交与范围](testing-partition-integration.md) |
| ARM64原生基础CI | 两线vet/race、辅助脚本与CLI通过；实际内核7.0，无实际资源/厂商业务证明 | [原生CI与包校验](native-arm64-ci.md) |
| 原发布包原生控制器 | 原AMD64/ARM64资产、实际Linux6.8/7.0四格88项通过；非ARM厂商业务 | [精确下载资产结果](testing-released-cgroup-ci.md) |
| 长期验收 | 旧observe基线已有固定22h快照，四周期内容完成但native-pending；24h enforce和至少7天未开始 | [固定22h快照及边界](continuous-acceptance.md) |

以下保留早期源码/预算的开发历史，各自结论仅适用于报告中的程序和配置。R29暂缓的扩展资源不因历史实现而恢复为当前交付。

## 历史实现与对应证据

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

## 早期开发与验收记录

接下来使用原镜像克隆补齐 enforce 冷启动、探针、相同负载和辅助故障回归。POST /test 与引擎备份结果不能代替尚未提供的厂商专用业务接口验收。

30% 限额引擎回归出现临时备库退出/探测超时；手动 16MiB/s + 256 IOPS 回归出现原主库连接失败与数据库内部重启，两轮均失败。第三轮 16MiB/s + 4096 IOPS 明确新手动预算，两类业务共 20 项短测通过且主库未重启；清理等待 120s 超时保留，后续独立核对确认真实原值/observe 和 SQL 正常，见 [包含失败的报告](testing-vendor-enforce.md)。已开发 [原生持续负载入口与判定条件](continuous-acceptance.md)，已完成 fresh/reuse、600s 原生/周期组合短测；24h observe 基线已于中国时间 2026-11-10 07:25:53 开始，尚未完成。

安装升级的 [开发分支](https://github.com/cuipengdba/ContainerResourceGuard/tree/next/install-upgrade) 已实现持锁兼容预检和显式私有原值备份，16 项真实检查通过；新 CLI 暂停旧版 Agent 的 20 项检查通过。显式二进制安装/回退已完成 16 项真实往返检查，保留两轮开发失败，限额、真实原值和 PID 1 保留，见该分支的 [升级结果](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/install-upgrade/docs/testing-upgrade-check.md)。已开发 supervisor 摘要/结构/语法预览、私有备份、原子接入和有资源恢复门槛的卸载，真实接入及持久化演练正在进行，见 [接入设计](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/install-upgrade/docs/supervisor-install.md)。不把已有二进制往返等同厂商业务在线升级或未知日志自动迁移。三组实际 30 分钟低 IO/持续故障测试已按原判定通过，见 [开销结果与边界](overhead-acceptance.md)。

DBS observe 初始化约 25s，20% 在预设 300s 内未就绪，30% 初始化约 251s；首轮重建探测超时保留，后续独立复测两次就绪约 205s/211s，128 行标记校验一致，新身份和旧日志隔离均确认。HISDBS observe 约 20s，20% 超过 300s，30% 初始化约 250s、备份后重建约 204s。详见 [保留失败的冷启动进展](testing-cold-start-progress.md)。实际原 liveness 只执行 ls，不能把它与 SQL/API 就绪条件等同。

后续按十版安排继续补齐多设备竞争、缓存高峰、环境矩阵、安装升级、构建来源和兼容契约。跨周期内存窗口已有 11 项真实检查；io_weight、memory_high、memory_swap_max 和本地观测功能仍只在开发分支，尚未合入 main 或发布；RC2 不接受这些字段。

24h observe 基线正在运行；24h 限额对照、arm64 真机、实际多设备及 1.0 的至少 7 天目标业务验收均未完成。完成源代码、通过短测或创建版本标签都不能替代持续运行和真实业务证据。业务节点当前只读检查，未修改其部署和控制文件。


可信发布的 [开发分支](https://github.com/cuipengdba/ContainerResourceGuard/tree/next/release-provenance) 已完成固定工具链、逐架构 SBOM、14 项包完整性正反检查、官方 schema 核对和另路径复现。GitHub 实际生成 provenance 与 SBOM 证明，限定仓库/工作流/源码/ref 的四项在线验证及三个错误身份/篡改反例均通过；预取可信根与 bundle 后，正确离线验证和三个反例通过。首轮缺 serialNumber 的 CI 失败保留。跨宿主首轮校验和因 CRLF/LF 不同；274ec3c 明确输出 LF 后，Windows 新克隆与 Linux CI 的两程序、两包、两 SBOM、清单、校验和共八项字节一致，见 [证据与边界](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/release-provenance/docs/release-provenance.md)。来源证明不代替功能或长期业务验收；这些开发分支仍未合入 main 或发布。


## 组合候选补充记录

[next/compatibility-contract](https://github.com/cuipengdba/ContainerResourceGuard/tree/next/compatibility-contract) 已组合后续开发代码，并汇入 main 的业务证据与持续测试入口，尚未合入 main 或发布。该分支早期曾补齐五项可选控制（其交付现已按R29暂停），观测参数、热重载/维护手册以及[兼容契约草案](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/docs/compatibility-contract.md)。固定 Go1.27.3 的实际程序完成[31项独立容器维护检查](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/docs/testing-combined-maintenance.md)，包括接入后六种辅助故障、真实限额/原值恢复、持久重建、永久卸载及锁/维护错误码；Go1.22.5最低源码工具链与Go1.27.3 CI分别归档。相同候选的三组30min预算和两个解析器各10min fuzz已完成；含R26的74693候选两个解析器也各完成10min fuzz，见[独立结果](testing-combined-long.md)，不同源码的开销证据不混用。

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
| P01.8 / P10.6 | RC3及1.0组合线：默认每日日志、30天及总1GB清理、失败放行 | Linux/race及每日日志真实只读/满盘/1GB清理已通过；业务长期验收独立继续 |
| P01.9 / P10.7 | RC3及1.0组合线：仅CPU/内存/IO独立百分比，各默认20；v1跳过、v2校验设置；旧配置兼容及manual保留 | 三项默认/独立换算/CLI、版本门禁、实际回读/恢复/Pod重建已通过；热重载及业务验收继续 |

用户已要求优先开发。R29已取消扩展资源的默认接管，R30要求设置前先检测cgroup；原安全保护保留；原P04/P05深入验证、24h+24h、>=7d及未测硬件门槛保留。设计及参数见[独立百分比](independent-percentages.md)、[每日日志](logging.md)。

## R29 / R30 当前任务

保留52项任务索引。P01.9/P10.7收窄为三百分比并新增版本门禁验收（v1/混合/未知不写、v2权限及实际回读）；P01.8/P10.6日志继续保留。扩展资源交付暂缓，原诊断、热重载、升级、身份与长期验收继续，不以源码完成替代业务门槛。工程预览与正式RC3/1.0分开标记，见[交付说明](next-version.md)。

当前R29/R30的两线Linux/race及38项隔离工程检查通过，结果与未测范围见[三项百分比/版本/日志实测](testing-three-percent-cgroup-logs.md)。本次可交付工程预览，不将正式RC3、24h+24h或1.0长期门槛标为完成。

旧源码第9轮已结束：64MiB/s三格通过，组合/DBS在缓存前置检查处停止、未进入负载；依赖的第10轮在线升级未执行。第11轮交叉故障另108项通过，同组旧源码故障矩阵合计216项；完整结果见[手动矩阵](testing-realpaths-manual.md)和[故障覆盖](testing-realpaths-faults.md)。新三资源候选另起四格验收，不混用程序来源。

未发布组合线d6ea657的三项百分比持续热重载15项实际检查通过，包含独立默认/CLI优先/坏配置保持/manual切换/外部冲突及停用；夹具已清理，见[明确程序来源和边界的结果](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/docs/testing-three-percent-reload.md)。main预览不因此新增热重载功能。

第12轮最新三资源程序四格真实路径业务验收已结束：24项通过，各格完整600秒、SQL/API零错误及10项引擎内容通过，夹具清理确认；仅为预先声明的手动64MiB/s预算。第13轮在线升级/回退已终止：首次安装失败，后续回退及600秒未完成；24h+24h和至少7天仍待完整实测。见[按程序摘要归档的结果](testing-three-resource-business-matrix.md)。

三资源组合开发线50671aa完成当前源码的跨Windows/Linux八项字节复现，以及限定仓库/工作流/源码/ref的四项在线证明验证和三项拒绝反例；不替代正在测试的d6ea657程序业务证据，也不扩大为main预览已具备组合线发布证明。详见[构建身份结果](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/docs/test-results-combined-build-identity.json)。

第13轮DBS/HISDBS首次安装均拒绝，旧预览缺少锁/日志协议广告，安装文件摘要保持、recovery为空，夹具清理；保留失败及原始输出未留存的证据限制，不绕过协议保护。见[维护失败与诊断](testing-three-resource-online-maintenance.md)。

第14轮最新三资源程序×DBS/HISDBS的40场景、216项辅助故障检查通过，全部夹具清理；独立30%配置，只证明辅助隔离，未追认自动30%持续业务性能或第13轮维护。见[新源码完整故障矩阵](testing-three-resource-fault-matrix.md)。

第15轮协议已声明的两套未发布组合程序在线往返通过：DBS/HISDBS各600秒、22项检查，原值/业务/缓存/数据保持，最终恢复真实原值且夹具已清理。第13轮main预览首次安装失败保留，不替代两个已发布次版本或长期门槛。见[独立维护结果](testing-three-resource-protocol-maintenance.md)。

第16轮默认空配置首格main/DBS完整600秒但SQL10次/API57次错误，未通过；Pod清理命令失败使其余三格未执行，终态namespace已移除。保留实际20%限额、失败与诊断，见[默认配置结果](testing-three-resource-default20-business.md)。

第17轮真实路径备份/新Pod ID冷重建四格、8次启动、88项检查通过，数据/独立逻辑恢复库/一对一身份/日志追加及新容器原值恢复核对，全部夹具清理；仅为手动64MiB/s预算。见[冷重建结果](testing-three-resource-cold-rebuild.md)。

组合开发源码50671aa在Windows/amd64、Go1.27.3下两个解析器各10分钟fuzz通过，包含12条明确归档的新百分比/默认/非法语料；不是Linux业务或资源开销结论，见[独立结果](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/docs/test-results-three-resource-parser-fuzz-windows.json)。

第18轮默认20%剩余三格补测结束：18项启动/控制/日志通过，三格业务组合均失败；main/HIS有完整失败原生结果，两个组合格仅有未完成快照，不计600秒通过。清理确认，连同第16轮四格均未通过，见[补测结果](testing-three-resource-default20-supplement.md)。

当前三资源/日志组合程序的正常、持续导出失败、只读cgroup三组30min工程开销测量已开始，尚未结束；不代替业务性能或正式长期验收。见[冻结计划和启动状态](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/docs/testing-combined-long.md)。

P04/P06分区修复在[独立next/partition-io分支](https://github.com/cuipengdba/ContainerResourceGuard/tree/next/partition-io)开发：文件系统/控制目标分离、同盘共享限额和标定/诊断已接入，Linux race及原整盘四格88项回归通过；[来源及未完成范围](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/partition-io/docs/testing-partition-io-core.md)。真实分区IO/旧二进制恢复仍待验收，未合入本线、未发布；正式长测程序和预算不变。


分区开发线现已完成[真实GPT双分区四格164项验收](testing-partition-cgroup.md)，独立分支实现af1a34d、实际运行468fe73；尚未合入本线或发布，正式长测/物理多设备/ARM厂商业务门槛未关闭。


组合d3706f3已完成[当前提交CI/两架构跨宿主构建及原生回归](testing-partition-integration.md)，原生ARM212个Go pass事件、实际整盘44项通过；新开销按固定计划待启动，既有正式长测和未发布边界不变。


当前分区组合候选首轮开销夹具漏带可选启动脚本，90秒前置超时，0秒测量、退出1、namespace已清理；[失败和原标准第二次计划](testing-partition-integration.md)均保留。补全夹具，不修改产品、预算或超时。


当前d3706f3两架构包/ELF完成[9项在线及离线构建身份验证](testing-partition-build-identity.md)；补齐辅助脚本的开销重测已进入三组实际采样，固定开始快照不计完整1800秒通过，原失败保留。


已冻结[当前d3706f3真实路径DBS/HISDBS复验](test-plan-partition-realpaths-business.json)，先满足本程序开销/夹具清理，再顺序运行两格原手动预算600秒。正式基线/固定d6切换候选不改，默认20%失败和长期门槛保留。


当前d3706f3真实路径复验的协调进程已启动，先等本程序开销通过且夹具独立确认不存在后才创建业务Pod；[固定等待快照](test-start-partition-realpaths-business.json)0个测量格。正式旧observe基线另有[20h固定观察](continuous-acceptance.md)，尚未完成86400秒，不替代新源码长测。


当前d3706f3完成[本程序三场景实际1800秒稳定开销](testing-partition-steady-overhead.md)，原阈值通过、退出0且夹具独立确认不存在。真实路径业务复验继续独立判断，不沿用旧d6业务结果；默认20%失败、正式长期和未测硬件门槛不变。


当前分区组合程序另按[真实路径故障冻结计划](test-plan-partition-realpaths-faults.json)复验DBS/HISDBS各10场景，原90/45/12秒门槛不变；须先等同程序两格600秒业务通过且夹具独立确认不存在，再创建故障Pod。当前未启动，不沿用旧40场景/216项结果。


当前d3706f3完成[DBS/HISDBS两格各600秒真实路径短业务](testing-partition-realpaths-business.md)，12项通过、退出0、namespace独立确认不存在；只适用冻结manual64预算。当前同程序故障矩阵另判，默认20%失败及正式长期/未测硬件条件不变。


当前d370另按[真实路径维护冻结计划](test-plan-partition-realpaths-maintenance.json)验证50671aa开发程序到当前程序的升级/回退，两角色各600秒、预计22项；必须等当前20场景故障通过且夹具独立不存在后才创建维护Pod。当前未启动，不替代最近两个已发布次版本，也不绕过旧预览缺协议的拒绝。


当前同程序故障[中间观察](test-progress-partition-realpaths-faults.json)9场景checked/49项通过，整轮尚未接受；[维护协调已启动但仅等待前置](test-start-partition-realpaths-maintenance.json)，0个Pod/0项。程序、预算和期限保持冻结，正式基线另有[21h固定观察](continuous-acceptance.md)，尚非86400秒通过。


当前d370[真实路径辅助故障20场景/108项通过](testing-partition-realpaths-faults.md)，退出0且namespace独立确认清理；升级/回退另按冻结计划判断。仅辅助隔离短测，不追认默认20%/自动30%持续性能，不替代正式长期或未测硬件。


当前d370另按[真实路径冷重建冻结计划](test-plan-partition-realpaths-cold-rebuild.json)复验两业务各两次启动、预计44项，沿用原300/45秒与manual64预算，核对备份/独立逻辑恢复、新ID及日志追加；须等当前维护通过且夹具独立确认不存在后才创建Pod。当前未启动，旧88项不改来源。


当前候选另有[七天综合验收安排](plan-seven-day-current-candidate.md)：实际604800秒连续组件和使用七天后的老化状态/冷重建/维护后置分开留证。先等本程序维护和冷重建通过清理，当前未启动，不替代原24h+24h或其他P10发布条件。


当前d370与50671aa开发程序的[真实路径升级/回退22项、两角色各600秒通过](testing-partition-realpaths-maintenance.md)，原值/业务/缓存/数据保持、最终恢复真实原值且namespace独立确认清理；两者未发布，不替代最近两个已发布次版本、正式长期或未测硬件门槛。


当前d370[两业务四次启动/44项冷重建通过](testing-partition-realpaths-cold-rebuild.md)，包含新ID/旧journal隔离、真实缓存新进程与状态更新、日志追加、逻辑备份/独立恢复和新容器原值恢复；退出0且namespace独立确认不存在。旧88项保持原程序来源，七天组件及正式发布条件另判。


P10.2/P10.5与R24落实：[当前d370七天组件已开始](testing-seven-day-current-candidate.md)，两业务首300秒实际采样、各一份资源Agent及缓存通过核对；首个周期正在执行。原fc2/d6正式24h+24h保持，当前七天未接受，老化状态后置另行执行，未新增或删除52项原任务。


R24/P10.2/P10.3验收落实：新增[持续报告只读核验器](soak-report-audit.md)，固定五个工具/程序摘要与86400/604800秒门槛，合成反例及4个真实报告只读检查通过；真实长测中间态仍pending。仅测试/文档/CI变更，不修改当前d370程序或52项任务定义。


P06/P10.4补充[环境覆盖索引](environment-coverage.md)，按实际程序/内核/架构/存储列明证据及未测范围；运维示例改为三独立百分比。正式旧observe已有22h观察、七天首周期内容完成但仍native-pending；新报告核验器三分支CI通过，产品长测程序未替换，52项完成审计继续。


R24/P10.2/P10.3/P10.5增加[七天老化身份采集与只读前置门禁](testing-aged-postflight-preflight.md)：Linux7方法通过，两业务真实采集及pending拒绝提前后置通过，原目录/控制保持。首次测试夹具预期原因码失败已保留并修正，产品程序未变。后置执行器和实际老化恢复/重建/升级仍未完成，原52项定义及最终发布门槛不变。


原fc2 observe的DBS/HISDBS已[各实际86400秒终态通过](testing-baseline24h-final.md)，原生SQL/API零错误、四轮内容随完整窗口接受、工作线程/协调入口已退出，原exec超5秒诊断保留。原固定d6阶段重新只读前置13/14，通过完整前序但仍需其他业务夹具先正常清理；无阶段切换/写限额。原24h enforce及七天/当前v1.0.0新摘要资格仍独立，未发布1.0。


本轮新v1.0.0程序dbc48aa5的[DBS/HISDBS各600秒业务](testing-versioned-candidate-business.md)及[20场景/108项辅助故障](testing-versioned-candidate-faults.md)终态通过，退出0且namespace独立确认清理；只对应既定预算和环境。另完成[实际保留数据辅助故障执行器](testing-aged-faults.md)、两套冻结计划与8项Linux自检，真实长门禁/提前执行pending且无写入，独立短数据20场景/152项演练已启动、尚未终态。原七天、正式阶段、未测环境及52项发布审计保持，未发布稳定1.0。


[实际短保留数据辅助故障20场景/152项终态通过](testing-aged-faults.md)，20次新容器ID、各场景旧64MiB及counter/PG/缓存/PID1/无OOM/TERM符合原条件，原输入/source journal及daily0600日志前缀保持；退出0且namespace独立确认清理。仅属于开发程序3a1的短演练，真实七天后阶段和新dbc程序的长期仍独立验收。


新v1.0.0程序dbc48aa5已完成[自身在线升级/回退两角色各600秒、22项终态](testing-versioned-candidate-maintenance.md)，八段维护均被实际原生测量覆盖，原业务/缓存/journal/控制保持，最终disable还原真正原值；退出0且namespace独立确认清理。对端50671aa未发布开发构建，不能关闭两个已发布次版本条件，实际长期及未测环境另判。


新版本化程序的[冷重建四次启动44项终态](testing-versioned-candidate-cold-rebuild.md)通过并清理，[自身七天测量](plan-seven-day-versioned-candidate.md)实际开始、首周期内容通过但native-pending；[独立实际谱系/只读后置门禁](testing-versioned-aged-preflight.md)已实现，Linux8项通过、真实封存及提前pending核对完成。初次报告结构错误拒绝和原计划/源码已保留，修正后未改业务进程、限额或验收门槛。本程序后置执行绑定、真实604800秒和全部稳定条件继续；工程预发布不关闭52项原任务。


版本化候选的[实际老化后置执行器](testing-versioned-aged-postflight-execution.md)已实现并通过Linux10项检查；真实七天默认/execute两次门禁均pending且未创建目标，独立短数据readiness通过并启动原实例演练，首观察DBS13项通过、尚未计两角色600秒终态。绑定本程序R64数据和新R78/R80b谱系，原R57/R59/R60保持；实际七天后置、老化故障和稳定全部条件继续。


版本化候选自己的[短保留数据后置演练](testing-versioned-aged-postflight-execution.md)现已36项/DBS600.332秒/HISDBS600.307秒通过，16个维护区间完整覆盖、原进程退出0、namespace和四Pod容器scope独立确认清理。原13项开始快照保留；这不是实际七天后置，P10/稳定版仍未接受。


版本化候选自己的[保留数据故障执行器](testing-versioned-aged-faults.md)已通过Linux9项与真实长默认/execute两次pending门禁，未提前创建目标；短前置通过并启动，固定首观察只有1场景/7项，20场景/152项待终态。原七天/正式对照/其他稳定门槛保持。


## 独立现场记录的限制

另一项[171现场更新记录](https://github.com/cuipengdba/ContainerResourceGuard/blob/c050b34ac15d2b8ea101bbe1b76e796e1ce6eb65/docs/deployment-dbs-hisdbs-update-20261111.zh.md)报告，同一dbc48aa5预发布程序安装后DBS出现两次新的PostgreSQL cgroup OOM kill和SQL/API错误，随后数据库重新启动；HISDBS未报告新增OOM。该记录显示更新前后配置和实际限额保持，但尚未证明新二进制导致或排除其影响。本轮97隔离验收没有独立重测171，不将其短期更新探针作为整体稳定接受，也不以隔离短演练覆盖现场故障。保留这一待核查运行记录，不修改171配置、限额或业务。


版本化候选自身的[短保留数据故障矩阵](testing-versioned-aged-faults.md)现已20场景/152项通过，原进程退出0、namespace及20个不同Pod/容器cgroup独立确认清理，原64MiB数据/输入/journal/日志前缀保留。首个运行中快照保持；三个来源明确分支的完整CI与两个ARM64检查通过。真实七天后置、正式对照及其他稳定条件仍待，未重发或替换既有下载资产。


本轮已补齐精确发布候选的[15项工程重载终态](testing-versioned-candidate-reload.md)及当前d370源码[两个10分钟解析器fuzz](testing-d370-parser-fuzz-windows.md)，21,680,191次执行、exit0。同步[修正任务索引中旧24h基线等状态](task-index-review-20261111.md)，保留52项原定义和旧scope_note；未将工程重载或源码fuzz计为厂商业务/实际七天验收。preview.2既有资产保持，长期及原稳定条件继续。
