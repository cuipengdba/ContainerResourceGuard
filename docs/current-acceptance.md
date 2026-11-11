# 当前验收入口

当前尚未发布1.0。[52项原始任务索引](current-task-registry.json)、[十版规划](roadmap.md)和[需求档案](requirements.md)保留全部范围；R29暂缓其他资源的新交付，未删除历史任务。当前资源入口仅CPU/内存/IO独立百分比，各自省略默认20；v1/混合/未知跳过，纯v2通过身份和权限检查后设置；每日日志保留30日或总1GB，辅助故障不作为原业务启动前提。

## 已发布与当前候选

| 范围 | 可核对的实际证据 | 不能据此宣称 |
|---|---|---|
| [已发布工程预览](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v0.1.0-rc.3-preview.1) | 三独立比例/cgroup门禁/日志；原资产Linux6.8/7.0、AMD64/ARM64四格[88项控制器检查](testing-released-cgroup-ci.md) | 正式RC3或稳定1.0、ARM厂商业务 |
| 当前未发布d3706f3程序 | [自身CI/原生ARM及整盘44项](testing-partition-integration.md)、[构建身份9项](testing-partition-build-identity.md)、[三场景各1800秒开销](testing-partition-steady-overhead.md) | 把其他源码结果改名为当前程序，或以工程检查替代完整业务长测 |
| 当前程序DBS/HISDBS真实路径 | [各600秒/12项业务](testing-partition-realpaths-business.md)、[20场景/108项辅助故障](testing-partition-realpaths-faults.md)、[开发构建维护22项/各600秒](testing-partition-realpaths-maintenance.md)、[四次冷启动44项](testing-partition-realpaths-cold-rebuild.md)，各终态通过且清理 | 默认20%或自动30%持续性能、最近两个已发布次版本维护 |
| 分区IO增强 | 468fe73的真实GPT双分区四格[164项](testing-partition-cgroup.md)；与组合生产源码逐文件合同独立列明 | 两块独立物理盘，或当前d370实际跑过同一164项 |
| 版本门禁与权限降级 | [版本输入模拟/真实v2及日志](testing-three-percent-cgroup-logs.md)、当前[真实只读/辅助故障](testing-partition-realpaths-faults.md)分别留档 | 真实v1内核已测，或权限丢失时一定能恢复已生效的配额 |

当前程序实际摘要、预算、环境和时长决定证据范围。原[默认20%四格业务失败](testing-three-resource-default20-business.md)及[补测](testing-three-resource-default20-supplement.md)保留；默认20不是已验证的DBS/HISDBS生产推荐额度。当前业务通过的是既定manual64测试预算。

## 长期阶段与后置

| 阶段 | 固定来源与当前证据 | 尚未完成 |
|---|---|---|
| 正式24h observe基线 | 原fc2程序，[两角色各实际86400秒终态通过](testing-baseline24h-final.md)，4周期原生组合接受，协调/负载入口已退出；exec超5秒诊断保留 | 旧observe结果不能代表新候选或限额阶段 |
| 正式等时enforce | 固定d6候选、预算及切换方案保留；须先有接受的完整基线再核对实时前置 | 独立24h enforce及对照报告；[完整基线后13/14前置](test-results-formal-stage-after-baseline.json)要求其他业务夹具先清理，不能以d370七天替换 |
| 当前d370七天连续组件 | [已开始及首周期观察](testing-seven-day-current-candidate.md)，首周期两角色各10项内容及临时清理完成，仍native-pending | 实际604800秒、28周期和完整原生判定 |
| 七天实际老化状态后置 | [只读采集/门禁](testing-aged-postflight-preflight.md)及[恢复/重建/维护执行器](testing-aged-postflight-execution.md)已实现，Linux自检和真实提前执行拒绝通过；独立短数据演练36项/各600秒终态通过且清理，原控制保持 | 真实七天后的执行及老化辅助故障/最终综合审计 |

[报告核验器](soak-report-audit.md)和只读前置门禁通过自检不代表真实长测通过；合成报告、真实pending和终态分开记录。采集计划及私有身份记录固定，后续执行另行引用，不能用新的空夹具替代七天实际使用的数据。当前P10_complete=false。

## 最终发布仍需核对

- 原24h+24h、至少七天综合验收及真实老化状态后置全部达标。
- 最近两个已发布次版本的维护兼容，而不只两个未发布开发构建往返。
- ARM厂商业务、独立物理多设备、未测运行时/内核和节点重启/掉电等原规划范围，按实际证据逐项处理。
- [环境覆盖索引](environment-coverage.md)、运维/恢复边界、诊断脱敏、冲突及所有权、包来源和全部52项最终审计。

环境索引是按源码/程序/内核/架构/存储限定的草案，不是稳定支持承诺。当前不恢复pids/权重/memory.high/Swap的新交付；旧实现仅按已有配置与恢复兼容规则处理。程序发布与生产接入分别记录，业务节点仍保持本任务只读范围。

历史固定观察保留原时刻：[故障中间采样](test-progress-partition-realpaths-faults.json)、[维护等待](test-start-partition-realpaths-maintenance.json)、[七天首300秒](test-progress-seven-day-current-candidate-start.json)等均未覆盖或删除，终态应沿上表对应的最终报告判断。

## 版本化v1.0.0候选的独立资格

候选来源与包身份见[固定身份](release-candidate-identity.md)。该未发布程序AMD64摘要dbc48aa5，ARM64摘要a01a5c2b，均与旧开发程序分别计数。

| 已完成项 | 实际结果 |
|---|---|
| 原生架构/内核 | [Linux6.x/7.x、AMD64/ARM64四格88项](testing-versioned-candidate-native.md)，八项产物均与Windows逐字节一致 |
| 自身运行开销 | [三场景各1800秒](testing-versioned-candidate-overhead.md)通过，运行器退出0，namespace独立确认清理 |
| 原厂商真实路径业务 | [DBS/HISDBS各600秒、12项](testing-versioned-candidate-business.md)通过，原manual64预算及启动/延迟/覆盖/数据/备份/独立恢复标准保持，退出0/清理 |
| 自身辅助故障 | [两角色20场景/108项](testing-versioned-candidate-faults.md)通过，原90秒/45秒/12秒及实际标定取消条件保持，退出0/清理 |

新摘要的[在线升级/回退验证已开始](testing-versioned-candidate-maintenance.md)，冷重建和实际长期资格仍分别推进；未将旧开发版3a1、原observe或固定d6阶段的运行时间转给新程序。默认20%和自动30%持续性能未因此通过，当前稳定1.0尚未发布。

实际老化辅助故障[执行器及冻结计划](testing-aged-faults.md)已实现并通过8项Linux自检；长门禁及提前执行真实返回pending且无工作目录/namespace。明确分开的[短保留数据20场景/152项终态通过并清理](testing-aged-faults.md)，原数据、输入和日志保留。原七天和其恢复/维护后置不因短演练完成而自动通过。
