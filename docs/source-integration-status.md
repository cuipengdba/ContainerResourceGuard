# 源码集成与当前验收状态

手动参考预算完整业务已经终结：16项记录/16通过/0失败，每角色原600秒及备份同步恢复/SLA按原标准独立核对，接受值为true；两namespace/两组父叶及54登记实例独立确认消失。[完整终态与准确原件](testing-manual-reference-full600-terminal.md)已归档。默认20%失败保持，不改默认值或宣称稳定1.0通过。[实际公开preview.4→preview.5维护设计](testing-preview45-manual-maintenance-design.md)另行规划，16个公开附件重核，仅是输入/设计，尚未执行。

以下保留原时点记录。

默认20%原完整业务验证已经终结：16项记录/14通过/2业务失败。DBS实际600.248秒中SQL6错误；HISDBS343.329秒中断，SQL18/API5错误，standby停止超过原30秒。两角色物理备份已完成，但完整native/收尾未通过，不能算完整备份同步验收；两namespace/两组父叶及54登记实例独立确认消失。[完整终态与准确原件](testing-bandwidth-default20-full600-terminal.md)保留全部原门槛、失败和瞬时诊断局限。preview.5程序及八项附件不变，稳定版未接受。

以下保留原时点记录。

HISDBS30纳秒兼容v2独立补测已完成36/36项、三次不同ID受控启动60.51 / 62.66 / 65.85秒，原300秒业务、45秒缓存及原探针/删除门槛保持；日志追加、逻辑备份、独立恢复和八项原值恢复通过，namespace/三组父叶及106个登记实例独立确认消失。[完整终态与准确原件](test-results-bandwidth-calendar-v2-terminal.json)已归档。与原1129的DBS20/HISDBS20/DBS30三个完成组相结合，[四种组合均有各自完整36项通过](testing-bandwidth-current-combinations.md)，跨独立任务共144项完整组检查；原1129的128通过/1失败/15未执行及1170的9通过/27未执行保持，不把原矩阵改判通过。preview.5程序/八项附件不变；完整600秒/物理备份同步、正式迁移与长期稳定门槛继续。

以下保留原时点记录。

纳秒兼容v2完整HISDBS30补测已唯一启动。节点2026-11-13 17:05:31 UTC快照：7项通过、首次PG/API/受控启动28.23/28.49/60.51秒，内存oom_kill=0；runner/driver的PID/start及全部冻结哈希一致。[准确启动原件](test-start-bandwidth-calendar-HIS30-v2.json)已归档，36项/三次启动等待实际终态。程序仍为已发布preview.5，原1129/1170失败、未执行步骤及旧576端口冲突均保持，原300秒及其它业务门槛不变。

以下保留原时点记录。

截至节点2026-11-13 16:26:50 UTC，已发布[工程预览preview.5](releases/v1.0.0-preview.5.md)，八项公开附件已逐字节校验。新默认值真机原矩阵已经结束：DBS20/HISDBS20/DBS30各36项通过；HISDBS30记录20通过、1失败、15项未执行，共129项记录/128通过/1失败、11次启动。失败是冻结脚本要求跨午夜后旧日期日志继续增长，与每日轮转规则冲突；实际新日期日志已有轮转及新Agent启动。保留原失败，另行修正脚本独立补测，不把原144项改成通过。四namespace、11组父叶及369登记实例独立确认消失。[原矩阵终态及精确原件](testing-bandwidth-percent-terminal.md)已归档。旧preview.4七天任务也已在约30小时的第六轮standby启动失败退出，未达到七天；[独立终态](testing-memory-high-seven-day-terminal.md)保留51个初始登记实例清理及第六轮cleanup未接受的区别。稳定1.0、原52项及其它完整业务/升级/长期门槛继续。

以下保留按原时点记录的历史进展。

截至节点2026-11-13 15:41:11 UTC的已完成组快照，已发布工程预览[preview.5](releases/v1.0.0-preview.5.md)，两架构包及[八项公开附件下载](test-results-preview5-publication.json)逐字节核对通过。CPU/内存/IO独立百分比各默认20，memory.high、IO百分比仅读写BPS且IOPS手动可选/外部原值保留。新程序在原DBS/HISDBS路径下，默认20%两组各36项、合计[72项完整组通过](testing-bandwidth-default20-two-role.md)，六次不同ID启动均在原300秒内，189登记实例与两namespace/六组父叶独立清理。该快照四组144项矩阵处于DBS30、HIS30未执行，后续继续；工程CI为准确ced4617的52项实际cgroup/180项分区/原生ARM64。稳定1.0及其它原门槛继续，历史记录不改。

准确产品源码ced461705ebc27315a59aefe463f9b4af47130a3，已发布标签v1.0.0-preview.5、打包提交d32987af8c02319f949b2e7bcc1429d598553921。草稿PR #1未合并，main和其它旧开发分支本次仅同步文档/读取工具；新程序在release/integration-v1及发布标签，源码复现检出ced4617并使用固定工具链/preview.5版本。原导入来源、两次工程失败、旧手动及旧百分比失败全部保留。

## 历史进展记录

当前新带宽默认值候选准确源码ced4617已通过完整Linux、原生ARM64、52项实际cgroup和180项分区检查；[默认20/30真机矩阵](testing-bandwidth-percent-startup.md)已唯一启动。节点15:06:47 UTC快照：DBS20已记录17项通过、两次不同ID启动在58.60/85.87秒就绪，后续冷重建及其余三组仍运行，尚非144项终态。IO百分比只新增读写BPS、IOPS留手动且保留外部原值；内存继续memory.high。[首轮实际证据](test-start-bandwidth-percent.json)已归档，preview.5尚未发布，preview.4附件/原52项/历史失败保持。

当前准确工程源码为`ced461705ebc27315a59aefe463f9b4af47130a3`，后续提交仅文档/证据。四项准确CI及精确原件见[IO带宽CI分析](test-results-IO-bandwidth-CI.json)，逐文件来源见[集成来源计划](https://github.com/cuipengdba/ContainerResourceGuard/blob/release/integration-v1/docs/source-integration-plan.json)。草稿[PR #1](https://github.com/cuipengdba/ContainerResourceGuard/pull/1)尚未合并；main/其余旧开发分支仅同步本次文档，不能据此把其旧程序视为新源码。

稳定1.0的原完整业务、物理备份/同步、正式升级、独占24h+24h、七天/老化及未满足硬件范围保持独立门槛。以下是原始历史进展，按当时源码与政策保留；当前状态以上文及首轮证据为准。

## 历史进展记录


已建立[草稿PR #1](https://github.com/cuipengdba/ContainerResourceGuard/pull/1)，准确工程验证源码为7823d8d5da8d1f25909e26660697b36f0e0e9e2e。[来源与集成范围](https://github.com/cuipengdba/ContainerResourceGuard/blob/release/integration-v1/docs/source-integration-plan.json)、[验证分析](https://github.com/cuipengdba/ContainerResourceGuard/blob/release/integration-v1/docs/test-results-source-integration-current-CI.json)及[精确证据](https://github.com/cuipengdba/ContainerResourceGuard/blob/release/integration-v1/docs/test-evidence-source-integration-current-CI.json.gz)可复查。

该源码完整Linux格式/vet/竞态/集成/两架构包/完整性/新检出可复现通过；原生ARM64有226个测试通过事件，实际cgroup两架构共44项通过；Linux6.8/7.0×amd64/ARM64真实同盘两分区共164项通过，含memory.high、外部memory.max不变、旧发布程序独立恢复八个原值、IO/CPU负载、几何失效重标定及完整清理。不是独立物理多盘或DBS/HISDBS全业务验收。前两轮失败均保留，未通过的旧记录不改写。

PR仍为草稿，未合并main、未部署、未重新发布；main程序源码仍旧，当前下载仍为v1.0.0-preview.4。集成候选包含开发分支已完成的IOQuality日志和公共文档包闭包修复，不能移用preview.4的二进制摘要、业务结果或七天经过时间。候选也保持每容器一对一、v1跳过、三项独立百分比默认20、memory.high和每日30天/1GB日志；未增加其它默认资源控制。

[已完成的手动IOPS对照](testing-manual-IOPS-comparison.md)使用preview.4，不是此候选的业务通过。默认IO四轴百分比语义保持；用户口径选择仍待答复。原52项、原百分比矩阵失败、物理备份/同步、独占24h+24h、七天/老化、正式版本迁移和未满足硬件范围继续按原定义验收，稳定1.0尚未通过。
