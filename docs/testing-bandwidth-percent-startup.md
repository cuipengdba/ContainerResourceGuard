# 新带宽默认值的真机启动/重建矩阵

截至节点2026-11-13 16:26:50 UTC，已发布[工程预览preview.5](releases/v1.0.0-preview.5.md)，八项公开附件已逐字节校验。新默认值真机原矩阵已经结束：DBS20/HISDBS20/DBS30各36项通过；HISDBS30记录20通过、1失败、15项未执行，共129项记录/128通过/1失败、11次启动。失败是冻结脚本要求跨午夜后旧日期日志继续增长，与每日轮转规则冲突；实际新日期日志已有轮转及新Agent启动。保留原失败，另行修正脚本独立补测，不把原144项改成通过。四namespace、11组父叶及369登记实例独立确认消失。[原矩阵终态及精确原件](testing-bandwidth-percent-terminal.md)已归档。旧preview.4七天任务也已在约30小时的第六轮standby启动失败退出，未达到七天；[独立终态](testing-memory-high-seven-day-terminal.md)保留51个初始登记实例清理及第六轮cleanup未接受的区别。稳定1.0、原52项及其它完整业务/升级/长期门槛继续。

以下保留按原时点记录的历史进展。

当前已完成默认20%两角色各36项，合计72项；六次启动、真实新ID/同profile、逻辑备份及独立恢复/还原均通过，189登记实例及两namespace/六组父叶独立清理。[准确终结组分析及十份原件](testing-bandwidth-default20-two-role.md)已归档。节点15:41:11 UTC正在DBS30，HIS30未执行，完整144项未接受；[工程preview.5已发布并核对八项下载](test-results-preview5-publication.json)，程序与本测试字节相同，原计划/门槛及旧失败保持。以下是冻结方案与早期快照。

最新已完成子集：DBS20的36项全部通过，三次不同ID受控就绪58.60/85.87/83.43秒；节点15:24:52 UTC独立确认95登记实例、namespace及三组父叶消失。[准确子集与取证补充](testing-preview5-qualified-subset.md)已归档。四组矩阵整体仍运行，原144项、原业务和清理时限不变；本工程预发布先交付已完成范围，不作完整矩阵/稳定接受。以下是启动前计划及首轮历史快照。

状态：按冻结方案唯一启动，原300秒/探针/删除等门槛保持；DBS20首轮17项通过，尚未终结。

[首轮只读证据](test-start-bandwidth-percent.json)：节点15:06:47 UTC，原runner PID4039696/start152166052；DBS20初始化及第一次冷重建容器/Pod ID各不相同，PG/API及受控就绪在58.60/85.87秒以内，已记录17项通过。首次真实io.max为rbps8408293/wbps7905573、riops/wiops=max；外部memory.max20GiB未变，memory.high13334654976。每次自动发现自身ID并沿用已标定profile；其它组未执行不计通过。第二次冷重建与后续三组继续，未改程序/计划/原时限。

准确产品源码ced461705ebc27315a59aefe463f9b4af47130a3，内置版本v1.0.0-preview.5、amd64二进制SHA256 be6b0aa9f9bf932d8b02872e86a9cffcfea6d7199e39c274694dce904af07333，尚未发布。使用准备发布的版本字符串构建并固定字节；不在测试中替换。新策略memory.high、io_percent仅标定读写BPS，手动IOPS可选；[策略及用户选择](io-bandwidth-policy.md)和[准确工程CI](test-results-IO-bandwidth-CI.json)已归档。

| 顺序 | 产品配置 | 角色 | 原标准 |
| --- | --- | --- | --- |
| 1 | 空配置{}，CPU/内存/IO各默认20 | DBS | 三次启动/重建、36项 |
| 2 | 空配置{}，CPU/内存/IO各默认20 | HISDBS | 三次启动/重建、36项 |
| 3 | 三项各显式30 | DBS | 三次启动/重建、36项 |
| 4 | 三项各显式30 | HISDBS | 三次启动/重建、36项 |

[冻结计划](test-plan-bandwidth-percent-startup.json)按真机原镜像、原supervisor/start/PG/缓存与实际容器路径执行，四个独立namespace依次运行。全新配置20用{}、30只填三百分比；首次自动选择最大合格文件系统并标定三样本中位数，原profile跨三次启动保留。CPU/内存按独立宿主基准计算，IO仅用实际profile的读写BPS；要求首次自身io.max原值为空，避免把外部约束混为产品默认。完整八项控制和journal原值/身份相等、外部20GiB max不变仍核对。

原PG/API/managed每次300秒、缓存45秒且仍在300秒内；原liveness exec ls延迟300/周期120/超时300/失败3/成功1，实际自身PodUID探针单独最多观察720秒，不延长业务300秒。保留64MiB数据/128标记、逻辑备份与独立数据库恢复、两次冷Pod重建的新ID/journal、日志追加、单Agent、disable完整还原。Pod删除120秒/父叶30秒及全部负载和业务尾部字节保持；mandatory io.stat/cpu.stat/memory.current，PSI缺失明确unavailable。

[结构检查](test-results-bandwidth-startup-structural.json)及[原生预检查](test-results-bandwidth-startup-native-preflight.json)已完成，预检查重新确认前轮四namespace/八leaf-parent/219登记进程清理，同一原576长期任务的三PID/start及五次备份门槛仍在，没有重启或改变原任务。旧候选后缀1122仅上传/预检未启动，使用实际preview.5版本的1129取代它；所有业务代码、探针及时限等价，原因已记结构检查。

这是新源码的144项独立复验，不改写旧1020/默认980/手动1080失败或借用旧七天经过时间。只证明本次实际完成范围，物理备份/同步、600秒完整业务、正式升级、独占24h+24h、七天老化和其它硬件门槛仍独立继续；未执行不能计通过，稳定1.0未接受。
