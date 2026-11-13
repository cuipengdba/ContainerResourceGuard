# 历史README：compatibility分支

以下完整保留此前内容，将原相对Markdown链接固定到当时源提交，避免跨分支或后续修改改变历史语义。文中的“当前/正在运行”只代表原时点；最新交付见[仓库首页](../README.md)和[当前验收](current-acceptance.md)。精确原文、摘要和变换记录见[归档记录](test-evidence/readme-before-preview5-overview.json.gz)。

# ContainerResourceGuard

HISDBS30纳秒兼容v2独立补测已完成36/36项、三次不同ID受控启动60.51 / 62.66 / 65.85秒，原300秒业务、45秒缓存及原探针/删除门槛保持；日志追加、逻辑备份、独立恢复和八项原值恢复通过，namespace/三组父叶及106个登记实例独立确认消失。[完整终态与准确原件](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/test-results-bandwidth-calendar-v2-terminal.json)已归档。与原1129的DBS20/HISDBS20/DBS30三个完成组相结合，[四种组合均有各自完整36项通过](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-bandwidth-current-combinations.md)，跨独立任务共144项完整组检查；原1129的128通过/1失败/15未执行及1170的9通过/27未执行保持，不把原矩阵改判通过。preview.5程序/八项附件不变；完整600秒/物理备份同步、正式迁移与长期稳定门槛继续。 下载及逐容器更新步骤见[preview.4到preview.5升级说明](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/upgrade-preview4-preview5.zh.md)。

以下保留原时点记录。

截至节点2026-11-13 16:26:50 UTC，已发布[工程预览preview.5](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/releases/v1.0.0-preview.5.md)，八项公开附件已逐字节校验。新默认值真机原矩阵已经结束：DBS20/HISDBS20/DBS30各36项通过；HISDBS30记录20通过、1失败、15项未执行，共129项记录/128通过/1失败、11次启动。失败是冻结脚本要求跨午夜后旧日期日志继续增长，与每日轮转规则冲突；实际新日期日志已有轮转及新Agent启动。保留原失败，另行修正脚本独立补测，不把原144项改成通过。四namespace、11组父叶及369登记实例独立确认消失。[原矩阵终态及精确原件](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-bandwidth-percent-terminal.md)已归档。旧preview.4七天任务也已在约30小时的第六轮standby启动失败退出，未达到七天；[独立终态](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-memory-high-seven-day-terminal.md)保留51个初始登记实例清理及第六轮cleanup未接受的区别。稳定1.0、原52项及其它完整业务/升级/长期门槛继续。

以下保留按原时点记录的历史进展。

截至节点2026-11-13 15:41:11 UTC的已完成组快照，已发布工程预览[preview.5](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/releases/v1.0.0-preview.5.md)，两架构包及[八项公开附件下载](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/test-results-preview5-publication.json)逐字节核对通过。CPU/内存/IO独立百分比各默认20，memory.high、IO百分比仅读写BPS且IOPS手动可选/外部原值保留。新程序在原DBS/HISDBS路径下，默认20%两组各36项、合计[72项完整组通过](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-bandwidth-default20-two-role.md)，六次不同ID启动均在原300秒内，189登记实例与两namespace/六组父叶独立清理。该快照四组144项矩阵处于DBS30、HIS30未执行，后续继续；工程CI为准确ced4617的52项实际cgroup/180项分区/原生ARM64。稳定1.0及其它原门槛继续，历史记录不改。

```json
{"cpu_percent":30,"memory_percent":40,"io_percent":25}
```

未填写各默认20；每容器独立一份Agent，重建后自动发现自身ID。纯Cgroup v2设置，v1/混合/未知及权限不足记日志降级，原启动链继续。自动选择最大合格本地可写文件系统后台标定，无需手填目录；一天一日志，30日/1GB清理。memory.high允许超过目标，原有硬限额或宿主不足仍可能OOM。

使用[当前下载及升级说明](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/releases/v1.0.0-preview.5.md)，逐容器保留配置/profile/journal。main与其它旧开发分支程序尚未变为新IO语义，源代码复现请检出ced461705ebc27315a59aefe463f9b4af47130a3并使用固定Go1.27.3执行`bash scripts/build.sh v1.0.0-preview.5`；BUILD.json分别记录产品源码与文档打包身份。[当前验收入口](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/current-acceptance.md)及[全部需求](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/requirements.md)列明未完成范围。

## 历史开发与发布记录

以下保留各历史版本当时进度，当前交付以上文为准。

当前新带宽默认值候选准确源码ced4617已通过完整Linux、原生ARM64、52项实际cgroup和180项分区检查；[默认20/30真机矩阵](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-bandwidth-percent-startup.md)已唯一启动。节点15:06:47 UTC快照：DBS20已记录17项通过、两次不同ID启动在58.60/85.87秒就绪，后续冷重建及其余三组仍运行，尚非144项终态。IO百分比只新增读写BPS、IOPS留手动且保留外部原值；内存继续memory.high。[首轮实际证据](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/test-start-bandwidth-percent.json)已归档，preview.5尚未发布，preview.4附件/原52项/历史失败保持。

实际公开preview.3→preview.4程序已通过[两角色在线迁移26项](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-public-preview-memory-high-maintenance.md)；需要更新现有容器时参阅[逐容器升级、即时回退与反向安装步骤](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/upgrade-preview3-preview4.zh.md)。其他原稳定条件继续独立判定。

当前可下载版本：[v1.0.0-preview.4](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v1.0.0-preview.4)。内存改用memory.high，保留CPU/内存/IO独立百分比与30天/1GB日志。[迁移、验证范围与下载](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/releases/v1.0.0-preview.4.md)、[八项公开下载校验](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/test-results-preview4-publication.json)。稳定1.0及完整业务/长期验收继续。

> 2026-11-12已选定的新内存语义：百分比及手动内存写memory.high，不新增memory.max；允许超目标，外部硬限额保留。旧硬限额仅凭同身份journal及仍持有的值恢复。下述旧版实现/测试保持历史来源，不能替代新策略验证。见[内存策略](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/memory-reclaim-policy.md)。

此前下载版本：[v1.0.0-preview.3](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v1.0.0-preview.3)。[功能、更新步骤和限制](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/releases/v1.0.0-preview.3.md)、[八项公开附件下载校验](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/test-results-preview3-publication.json)。程序与preview.1/preview.2相同，本版同步最新升级/回退及Agent工具验证文档；稳定1.0和长期验收继续。

此前预发布版本：[v1.0.0-preview.1](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v1.0.0-preview.1)。[更新步骤、功能与内嵌v1.0.0候选身份](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/releases/v1.0.0-preview.1.md)；[实际发布/下载校验及CI](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/test-results-preview1-publication.json)。这是预发布版，稳定1.0及长期验收继续；下文历史记录按原时点保留。

当前源码、已发布下载包、逐项实测与未完成条件，统一从[当前验收入口](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/current-acceptance.md)查看；[52项原始任务索引](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/current-task-registry.json)保留全部规划，未将历史构建结果改为当前程序结果。

未发布版本化候选已完成自身[两角色各600秒业务](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-versioned-candidate-business.md)及[20场景/108项辅助故障](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-versioned-candidate-faults.md)，原预算和门槛保持；[实际保留数据故障验证](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-aged-faults.md)继续，真实七天与稳定发布仍另判。

分区IO增强在独立开发分支完成[真实GPT双分区四格164项检查](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-partition-cgroup.md)，现已[接入组合开发线](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/partition-io.md)，[当前提交构建/原生回归已通过](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-partition-integration.md)，[自身三场景1800秒开销通过](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-partition-steady-overhead.md)，尚未发布；正式长测程序和现有下载包保持原来源。


[v0.1.0-rc.3-preview.1工程预览及下载](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v0.1.0-rc.3-preview.1)以R29/R30为准：只暴露三个独立资源百分比，cgroup v1跳过/v2校验设置，日志保留。两线38项隔离工程检查通过；发布范围与实测见[最新版本说明](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/next-version.md)，正式业务与长期验收继续。

原发布AMD64/ARM64下载包已在实际Linux6.8/7.0原生环境完成[四格88项控制器检查](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-released-cgroup-ci.md)，包括实际限额、自动百分比、新ID和恢复；ARM厂商业务及长期条件尚未完成。

容器内运行的轻量资源控制程序，简称 **CRG**。严格 **一个容器、一份 Agent、独立控制自身资源**。无需 Operator、CRD、Docker socket 或 Kubernetes API 权限。

CPU、内存、IO分别设置百分比，省略的资源项各自默认20%。最小配置`{}`，也可单独调整：

```json
{"cpu_percent":30,"memory_percent":40,"io_percent":25}
```

仅限制这三个资源，其他资源保持原值；先识别cgroup，v1跳过、v2校验后设置，详见[独立百分比](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/independent-percentages.md)。CPU/内存取宿主容量，IO取自动标定基准；不需手动填写核数、字节或测速目录。

**IO 的百分比是特定测试方法的实测基准百分比，不是磁盘固定物理极限。没有可用标定文件就显示 IO 未管理，不用竞争权重冒充硬限速。**

默认20%在DBS/HISDBS四格测试均未通过业务组合验收，不能作为这两类业务已验收的推荐配额；详见[首格失败](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-three-resource-default20-business.md)和[三格补测](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-three-resource-default20-supplement.md)。

## 快速使用

当前 RC3 / 1.0 开发候选已改为默认自动选盘：CPU、内存、IO独立百分比默认各20。原 supervisor 异步启动 CRG，首次选择容器内容量最大的合格可写本地磁盘文件系统并保存基准，重启后复用；不必手工指定目录或输出路径。业务和缓存程序独立启动，失败不阻断业务。已发布 RC2 仍是原显式标定行为。

测速只使用独立128MiB临时普通文件，不改业务文件；存在真实IO负载，额外设备覆盖不自动假定。只读、无稳定设备身份或已有限速等情况会明确降级。规则与验收状态见[自动IO标定](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/automatic-io-calibration.md)。

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

先观察时用 `examples/observe.json`。`run` 的默认模式是 **enforce**；`doctor` 始终只读。已发布preview.1运行时不热加载配置；本未发布组合/分区开发线已实现[安全热重载](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/hot-reload.md)，三个独立比例和CLI优先规则另有[明确程序来源的验证](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-three-percent-reload.md)。

## 业务优先

CRG 是可选辅助进程。原业务必须独立启动；无权限、只读 cgroup、程序不存在、配置错误、Agent 崩溃，不能决定业务容器退出。使用 [集成示例](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/integration.md)，不要把 CRG 设为业务启动前置条件或健康探针。

资源限额由内核执行，**Agent 退出不等于撤销已写入限额**。过低的CPU/IO额度或memory.high回收目标会拖慢业务。preview.4触达high会回收/节流、允许超目标；CRG不新增memory.max，外部硬限额或宿主内存耗尽仍可能OOM。可用 `crg disable --config /etc/crg/config.json` 协调停用并恢复；外部已经改写的值不会被强制覆盖。详见 [本地运维](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/operations.md)。

## 支持范围

- Linux cgroup v2，静态 Linux amd64 / arm64 二进制。
- 自动从 `/proc/self/cgroup` 与挂载信息发现自身 cgroup；重建后重新发现。
- 不接受其他容器、目标 PID 或目标 cgroup 参数；不扫描其他容器。
- 不改父级 Pod、不创建业务子 cgroup、不移动进程、不修改缓存控制策略。
- cgroup v1、缺少控制器或无法确认目标时安全降级，不能声称三项均已受控。
- 上层 Pod/运行时限制继续有效；CRG 不提高既有外部硬上限。
- 百分比是每容器独立上限，不是资源预留，也不保证获得对应吞吐；多个容器比例之和不由 CRG 协调。

## 文档

后续设计与历史兼容：[双资源模式（扩展资源暂缓）](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/resource-modes.md)；[容器/Pod 重启 ID 处理](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/restart-behavior.md)。交付状态以任务和发布报告为准。

持续开发与验收状态见 [当前进展](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/development-status.md)。安全热重载已在独立分支通过 13 项真实 cgroup 检查，尚未发布；原镜像业务验收正在推进。

开发分支已加入手动模式入口，例如 `{"resource_mode":"manual","limits":{"cpu_cores":2.5,"memory_high":"4GiB"}}`。完整示例见 [manual.json](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/examples/manual.json)，无需 IO 的示例见 [manual-cpu-memory.json](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/examples/manual-cpu-memory.json)。新增功能已完成 [Linux 隔离限额与恢复验证](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-dual-modes.md)，厂商业务验收仍未完成；已发布 RC2 仅支持原字段。

| 文档 | 内容 |
|---|---|
| [全部需求](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/requirements.md) | 用户需求、约定与边界，逐项编号 |
| [开发任务](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/tasks.md) | 实现、验证状态和证据 |
| [后续十版规划](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/roadmap.md) | 从 RC3 到 1.0 的十个版本、52 项任务与发布条件 |
| [配置](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/configuration.md) | 三项独立百分比默认20、手动模式与日志 |
| [安装与升级](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/installation.md) | 架构选择、持久部署、校验、升级和回退 |
| [安装接入开发](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/supervisor-install.md) | 摘要预览、私有备份、可选接入和有恢复门槛的卸载 |
| [可信发布开发](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/release-provenance.md) | 固定工具链、SBOM、来源证明及离线验证的真实证据 |
| [1.0 兼容契约草案](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/compatibility-contract.md) | 配置/CLI/日志兼容、原因码与维护边界；尚未发布 |
| [本地运维](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/operations.md) | 预检、人类可读状态、停用/启用、低频状态与覆盖范围 |
| [架构](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/architecture.md) | 一对一发现、写入、恢复和冲突处理 |
| [容器接入](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/integration.md) | 原 start.sh / supervisor / 缓存控制关系 |
| [IO 标定](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/io-calibration.md) | 方法、设备绑定、多设备和局限 |
| [故障排查](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/troubleshooting.md) | 权限、内存保护、冲突、重建和停用 |
| [测试报告](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing.md) | 实际执行范围、证据、局限 |
| [安全与运维边界](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/SECURITY.md) | 权限、自身目标和数据保护 |
| [变更记录](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/CHANGELOG.md) | 版本与已知限制 |

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

运行日志默认每天一个文件，保留最近30个日历日，总量不超过1GB，写日志失败仍放行业务。详见[每日日志](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/logging.md)。旧percent配置仅作兼容；上述功能已随工程预览发布，后续深入功能仍在开发，正式业务/长期验收状态见任务清单。

当前组合程序已启动[DBS/HISDBS七天持续组件](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-seven-day-current-candidate.md)，首300秒采样正常；完整604800秒和后置验收尚未完成。


当前精确候选已完成[DBS/HISDBS业务exec分段诊断](https://github.com/cuipengdba/ContainerResourceGuard/blob/8de448126f5d959412367a1618f0f67ea46dded0/docs/testing-business-exec-timing.md)：26项主检查/各600秒及67条有效分段，清理与原配置恢复完成；一次外层超5秒诊断失败和历史延迟待查继续保留，稳定版与长期条件未因此完成。
