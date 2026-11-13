# 原52项任务与当前用户范围复核

当前交付为preview.4，产品源码固定为`180c86ad7986a76526a41575cc1c176d5da98a9c`。本页是范围与证据入口复核，**不是52项已完成或稳定1.0验收报告**。原定义和完成声明保持；[机器可读52项](requirements-evidence-review.json)保留逐项原文及摘要，[原登记表](current-task-registry.json)和[十版规划](roadmap.md)继续可追溯。

用户后来的明确需求优先：每容器一份Agent，只控制CPU、内存、IO，各百分比省略默认20；设置前识别v1/v2；内存只新增`memory.high`目标，保留外部`memory.max`。pids、CPU/IO权重、swap额度不再作为新增控制任务。high可低于当前用量并回收/节流，原max下调窗口不应阻止high生效；仅仍自有的历史硬限额恢复沿用保护。详见[内存合同](memory-reclaim-policy.md)。只读统计、诊断、恢复与升级仍继续。

证据列是对应主题的可复核入口，包含历史结果、失败与当前源码说明，不能把一个链接理解成整项通过。main保留原程序实现，下载入口指向新工程包；本范围指当前preview.4程序，不以main旧代码推断新策略。普通CI、单设备和手动预算通过不能代替ARM厂商业务、独立多实盘或默认比例业务。[最新默认20%终态](testing-default20-memory-high-business.md)为16项记录14项通过、两业务项失败，仍需处置。

| ID | 当前范围 | 仍需完成或说明 | 证据入口 |
|---|---|---|---|
| P01.1 | 保留两角色原启动链、缓存共存与独立备份/同步/恢复验收 | 手动预算短测与默认20%失败分别保留；完整业务、厂商未公开接口及长期条件尚不能整体接受。 | [memory-high-business](testing-memory-high-business.md) / [default20-memory-high-business](testing-default20-memory-high-business.md) |
| P01.2 | 保留固定额度冷启动、解包后和备份后启动20%/30%矩阵 | 逐格冻结预算、数据、原探针和就绪界限并记录成功/失败；现有默认20%短测不能替代全部矩阵。原文要求如实记录，不等于保证任意负载20%都通过。 | [default20-memory-high-business](testing-default20-memory-high-business.md) / [memory-high-cold-rebuild](testing-memory-high-cold-rebuild.md) |
| P01.3 | 保留Agent额外开销与业务额度不足的区分 | 原30秒失败及新默认20%备份300秒超时需分别形成证据和处置；低标定IOPS与超时并存不构成单因素因果证明。 | [memory-high-overhead](testing-memory-high-overhead.md) / [default20-memory-high-business](testing-default20-memory-high-business.md) |
| P01.4 | 保留已知supervisor、备份回退与可选辅助失败继续原业务 | 现有两角色故障证据按原超时判断；未知脚本拒改，继续老化与全生命周期组合复核。 | [memory-high-faults](testing-memory-high-faults.md) / [installation](installation.md) |
| P01.5 | 保留percent/manual两模式，只控制三类资源 | 内存规范字段memory_high；旧memory_max仅为high兼容别名，不能恢复新增硬限额语义。整体业务另验。 | [configuration](configuration.md) / [memory-reclaim-policy](memory-reclaim-policy.md) |
| P01.6 | 用户后续要求替代：不新增pids_max或cpu_weight控制 | 危险下调、所有权及恢复规则只继续适用于当前三类资源；旧扩展资源测试作为历史，不作为重新开放功能的理由。 | [configuration](configuration.md) / [memory-reclaim-policy](memory-reclaim-policy.md) |
| P01.7 | 保留最大合格文件系统自动选盘、后台标定、持久复用 | 默认20%已完成首次自动标定/原路径启动，但完整业务失败；旧RC3名称和旧测试结果不能冒充当前发布字节。 | [automatic-io](testing-automatic-io.md) / [default20-memory-high-business](testing-default20-memory-high-business.md) |
| P01.8 | 保留每日一个文件、30日及总1GB清理、记录失败放行 | 功能与故障证据保留；不因日志局部通过关闭长期业务条件。 | [three-percent-cgroup-logs](testing-three-percent-cgroup-logs.md) / [memory-high-faults](testing-memory-high-faults.md) |
| P01.9 | 保留CPU/内存/IO独立百分比，各省略默认20；v1跳过/v2检查 | 当前内存仅high；保留旧percent/manual兼容，重载和完整业务证据分别判断。 | [configuration](configuration.md) / [memory-high](testing-memory-high.md) / [default20-memory-high-business](testing-default20-memory-high-business.md) |
| P02.1 | 保留每种目标业务24h observe基线及24h enforce真实高峰 | 既有旧策略基线、共存短测和七天任务不能拼接为当前high正式独占对照；必须按原负载/高峰标准取得结果。 | [baseline24h-final](testing-baseline24h-final.md) / [memory-high-seven-day](testing-memory-high-seven-day.md) |
| P02.2 | 保留错误、分位数、备份/同步/恢复、OOM/节流/IO压力 | 默认20%真实失败与960 SQL失败保持；预算不足也不能被忽略或改称通过。 | [default20-memory-high-business](testing-default20-memory-high-business.md) / [full960-native-child-fixed](testing-full960-native-child-fixed.md) |
| P02.3 | 保留重建/重启/撤权/状态故障/外部改值/停用/回退组合 | 现有故障与维护证据不替代老化及状态保留/丢失的完整组合验收。 | [memory-high-faults](testing-memory-high-faults.md) / [public-preview-memory-high-maintenance](testing-public-preview-memory-high-maintenance.md) |
| P02.4 | 保留精确支持矩阵和安装/卸载/回退合同 | 当前仅工程预发布；逐架构、镜像、内核、运行时、存储与权限说明范围，不发布未测组合稳定性结论。 | [installation](installation.md) / [compatibility-contract](compatibility-contract.md) / [releases/v1.0.0-preview.4](releases/v1.0.0-preview.4.md) |
| P03.1 | 保留本地重载、文件替换及保留上一有效配置 | 现有重载证据需与当前发布源码和high语义绑定，坏输入不清空预算。 | [three-percent-reload](testing-three-percent-reload.md) / [configuration](configuration.md) |
| P03.2 | 保留完整候选校验、逐项持久化/写入/回读、外部约束 | 三项不是原子切换；需分别展示实际结果，不借high迁移覆盖外部硬上限。 | [memory-high-maintenance](testing-memory-high-maintenance.md) / [memory-reclaim-policy](memory-reclaim-policy.md) |
| P03.3 | 用户high语义替代旧max危险下调等待，保留代次与逐项状态 | high允许低于当前用量并回收/节流；不为遵守旧句子重新延后所有high写入。历史硬限额恢复仍用保护，冲突/失败必须可见。 | [memory-reclaim-policy](memory-reclaim-policy.md) / [memory-high](testing-memory-high.md) |
| P03.4 | 保留双模式切换、并发重载、删除项目与明确停用恢复 | state_dir受控升级、enforce转observe不隐式撤限；需保留当前high维护及业务验证边界。 | [configuration](configuration.md) / [memory-high-maintenance](testing-memory-high-maintenance.md) |
| P03.5 | 保留双模式切换、并发重载、删除项目与明确停用恢复 | state_dir受控升级、enforce转observe不隐式撤限；需保留当前high维护及业务验证边界。 | [configuration](configuration.md) / [memory-high-maintenance](testing-memory-high-maintenance.md) |
| P04.1 | 保留自动选盘、三次顺序BPS/随机IOPS、质量及身份记录 | 当前默认20%测得低IOPS，不能称物理峰值；需核对竞争和可用预算，不擅自用人工高基准替换失败。 | [automatic-io](testing-automatic-io.md) / [default20-memory-high-business](testing-default20-memory-high-business.md) |
| P04.2 | 保留本容器profile检查/合并/替换/迁移预览与设备身份 | 工程证据与实际替盘、重复身份、缺样本处理分别记录；新机器基准不得无验证套用。 | [configuration](configuration.md) / [partition-io-core](testing-partition-io-core.md) |
| P04.3 | 保留数据/WAL/备份路径覆盖及选定分区/映射栈报告 | 不能确认的NFS/对象/Overlay显示未覆盖；可见路径不等于已测任意存储栈。 | [native-cgroup-dm-loop](testing-native-cgroup-dm-loop.md) / [partition-cgroup](testing-partition-cgroup.md) |
| P04.4 | 保留至少两块独立块设备及一个选定映射栈实测 | 用户暂时没有额外节点；单设备、loop或同设备分区不代替两块独立实盘，缺证据明确保留。 | [native-cgroup-dm-loop](testing-native-cgroup-dm-loop.md) / [compatibility-contract](compatibility-contract.md) |
| P04.5 | 用户后续要求取消io_weight；多路径/多设备仍属IO范围 | 只用io.max表达IO预算；多设备/替盘实机条件仍未由单设备节点满足。 | [configuration](configuration.md) / [partition-io-core](testing-partition-io-core.md) |
| P05.1 | 保留只读内存统计、events/PSI、swap/HugeTLB范围 | 统计缺失显示不可用；诊断不是新增swap/OOM/数据库或缓存策略控制。 | [configuration](configuration.md) / [memory-reclaim-policy](memory-reclaim-policy.md) |
| P05.2 | 用户high策略替代新max安全下调窗口，保留历史max恢复保护 | high可能同步回收并明显延迟，不承诺限时写入；不得强杀业务、强制drop_caches或擅自加预算。 | [memory-reclaim-policy](memory-reclaim-policy.md) / [memory-high](testing-memory-high.md) |
| P05.3 | 保留原缓存与查询/备份/WAL/回收压力重叠 | 950手动预算业务通过与960 SQL失败属不同运行；压力、缓存和新策略长期需分别验收，不能用诊断通过替代。 | [full950-bytecode-export-fixed](testing-full950-bytecode-export-fixed.md) / [full960-native-child-fixed](testing-full960-native-child-fixed.md) / [memory-high-pressure](testing-memory-high-pressure.md) |
| P05.4 | 保留三百分比与已受控/不足/冲突/缺统计的解释 | 默认20%能写入不表示适配业务；high不是硬上限，也不保证绝不OOM。 | [memory-reclaim-policy](memory-reclaim-policy.md) / [default20-memory-high-business](testing-default20-memory-high-business.md) |
| P05.5 | memory_high成为唯一新内存目标；取消memory_swap_max控制 | 保留Kubernetes/祖先max。只按同身份/仍自有journal恢复旧CRG硬值，禁止盲目写max；恢复低旧值仍需保护。 | [memory-reclaim-policy](memory-reclaim-policy.md) / [memory-high](testing-memory-high.md) |
| P06.1 | 保留按内核/运行时/挂载/权限逐组合兼容矩阵 | 5.14厂商业务与Linux6/7控制器CI分别列明；新内核CI不代表该内核厂商完整业务已验收。 | [memory-high-native](testing-memory-high-native.md) / [linux6-current-integration](testing-linux6-current-integration.md) / [compatibility-contract](compatibility-contract.md) |
| P06.2 | 保留原生ARM64控制器、恢复及厂商业务实机验收 | 已有原生ARM64工程控制器证据；缺可访问ARM64 DBS/HISDBS真机业务环境，不能以交叉编译或普通CI替代。 | [memory-high-native](testing-memory-high-native.md) / [compatibility-contract](compatibility-contract.md) |
| P06.3 | 保留只读/委派/私有namespace/systemd/祖先/可信宿主容量发现 | 不确认自身目标则不写；当前节点和CI工程证据不能推断所有发行版/运行时组合。 | [memory-high](testing-memory-high.md) / [compatibility-contract](compatibility-contract.md) |
| P06.4 | 保留重建、路径复用、CPU在线变化及只读切换 | 新身份不得套用旧journal；各控制器可用性独立，继续对应发布程序组合证据核对。 | [memory-high-cold-rebuild](testing-memory-high-cold-rebuild.md) / [memory-high-faults](testing-memory-high-faults.md) |
| P06.5 | 保留双模式容器/Pod/节点重启及状态保留/丢失矩阵 | 现有冷重建与故障用例不是实际主机重启及全部状态组合证明，缺项仍保留。 | [memory-high-cold-rebuild](testing-memory-high-cold-rebuild.md) / [memory-high-faults](testing-memory-high-faults.md) |
| P07.1 | 保留human/JSON原因、比例/基数/外限/代次与状态过期区分 | CLI状态不等于数据库健康；已归档合同和当前high字段继续按发布源码复核。 | [compatibility-contract](compatibility-contract.md) / [cli-contract-ci-20261111](testing-cli-contract-ci-20261111.md) / [memory-reclaim-policy](memory-reclaim-policy.md) |
| P07.2 | 保留白名单、脱敏、有界、本地诊断包 | 不采全集env、业务数据/私有脚本/别容器；本轮22原件明确清单不是默认扩大产品采集范围。 | [diagnostics](testing-diagnostics.md) / [diagnostics-development](diagnostics-development.md) |
| P07.3 | 保留默认关闭、仅本容器、本地指标、无默认网络端口 | 指标失败不影响业务、端点不成为原健康前置条件；工程证据与长期预算分别核对。 | [metrics](testing-metrics.md) / [configuration](configuration.md) |
| P07.4 | 保留有界事件/每日清理与高频异常低IO | 原值journal持久化不省略；三场景30分钟工程预算和长期异常/低IO证据不互相替代。 | [events](testing-events.md) / [memory-high-overhead](testing-memory-high-overhead.md) |
| P08.1 | 保留当前容器安装预览/备份/卸载及已知模板 | 产品不操作Kubernetes API；测试协调器使用API仅为隔离夹具，不成为产品架构的一对多管理。 | [installation](installation.md) / [upgrade-check](testing-upgrade-check.md) |
| P08.2 | 保留单写入者、兼容锁、受控换程序及失败回退 | 现有preview3→preview4工程迁移不等于两个正式小版本迁移；不让旧新Agent争写。 | [public-preview-memory-high-maintenance](testing-public-preview-memory-high-maintenance.md) / [installation](installation.md) |
| P08.3 | 保留journal/profile版本、备份预览和不兼容回退 | 缺失/损坏旧journal不得猜原硬上限；兼容失败拒绝，不能删状态或全写max。 | [memory-reclaim-policy](memory-reclaim-policy.md) / [compatibility-contract](compatibility-contract.md) |
| P08.4 | 保留镜像持久化、重建、永久停用及升级演练 | 运行容器内改文件不会自动进入新镜像；新身份不复用旧身份停用/恢复状态。 | [installation](installation.md) / [memory-high-cold-rebuild](testing-memory-high-cold-rebuild.md) |
| P09.1 | 保留固定工具链、修订/包/SBOM/摘要与可重复构建来源 | preview.4固定工具链二次构建与公开八文件校验有证据；不得把本地构建描述为GitHub签名产物。 | [releases/v1.0.0-preview.4](releases/v1.0.0-preview.4.md) / [test-results-preview4-publication](test-results-preview4-publication.json) |
| P09.2 | 保留安装前完整性/来源与离线校验 | 实际安装应核对对应架构八文件清单，不执行未校验远程shell，不把私有profile或凭据打包。 | [installation](installation.md) / [releases/v1.0.0-preview.4](releases/v1.0.0-preview.4.md) |
| P09.3 | 保留解析器fuzz、长故障及持久化中断 | 强杀和满盘等证据不能声称真实掉电已测；隔离掉电与长期撤权/慢文件系统缺项单列。 | [d370-parser-fuzz-windows](testing-d370-parser-fuzz-windows.md) / [memory-high-faults](testing-memory-high-faults.md) |
| P09.4 | 保留15s周期/30min CPU≤单核0.1%/RSS≤20MiB/状态≤5min一次预算 | 当前发布程序三场景1800秒证据可复核；长期低IO/持续异常及业务吞吐不是同一指标。 | [memory-high-overhead](testing-memory-high-overhead.md) / [memory-high-seven-day](testing-memory-high-seven-day.md) |
| P10.1 | 保留三独立20%默认、旧配置兼容、格式合同与真实发布迁移 | preview3/4均为prerelease；已做的准确包迁移不能冒充最近两个已发布正式次版本验证，也不补造历史版本。 | [compatibility-contract](compatibility-contract.md) / [public-preview-memory-high-maintenance](testing-public-preview-memory-high-maintenance.md) |
| P10.2 | 保留当前策略两业务至少604800秒和28实际备份/同步周期 | high576原任务继续同PID/start；需真实时间和周期完整/老化后验证，旧硬策略时长不可转记，单纯七天也不自动通过。 | [memory-high-seven-day](testing-memory-high-seven-day.md) / [aged-postflight-execution](testing-aged-postflight-execution.md) |
| P10.3 | 保留目标隔离/权限/冲突/脱敏/来源/恢复所有权最终复核 | 默认20%和960业务失败及缺失证据需有处置；辅助启动放行不保证资源节流不影响业务。 | [default20-memory-high-business](testing-default20-memory-high-business.md) / [full960-native-child-fixed](testing-full960-native-child-fixed.md) / [installation](installation.md) |
| P10.4 | 保留精确支持矩阵/运维/问题分级/补丁与证据归档 | 稳定发布与生产部署各自记录；未测组合不包装为全面支持。 | [operations](operations.md) / [compatibility-contract](compatibility-contract.md) / [releases/v1.0.0-preview.4](releases/v1.0.0-preview.4.md) |
| P10.5 | 保留组合1.0候选自动标定/双模式/故障/重建/升级/两业务 | 实现与工程包已存在；原24h+24h、至少七天、业务与支持矩阵门槛没有满足前不能标记稳定1.0发布。 | [current-acceptance](current-acceptance.md) / [memory-high-seven-day](testing-memory-high-seven-day.md) / [default20-memory-high-business](testing-default20-memory-high-business.md) |
| P10.6 | 保留每日一个文件、30日及总1GB清理、记录失败放行 | 功能与故障证据保留；不因日志局部通过关闭长期业务条件。 | [three-percent-cgroup-logs](testing-three-percent-cgroup-logs.md) / [memory-high-faults](testing-memory-high-faults.md) |
| P10.7 | 保留CPU/内存/IO独立百分比，各省略默认20；v1跳过/v2检查 | 当前内存仅high；保留旧percent/manual兼容，重载和完整业务证据分别判断。 | [configuration](configuration.md) / [memory-high](testing-memory-high.md) / [default20-memory-high-business](testing-default20-memory-high-business.md) |

下一步优先处理默认20%备份超时的预算与标定解释、固定20%/30%启动矩阵和当前high策略实际长期结果。现有960诊断资格已经通过，不再用增加可选BPF资格替代业务处置。测试失败不自动放宽额度或延长原界限；缺少硬件/时长如实记录，不能写成已测。此复核没有新增限制参数、改现有业务、重启长期任务或补造正式版本。
