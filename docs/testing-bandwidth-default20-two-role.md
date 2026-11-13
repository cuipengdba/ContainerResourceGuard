# 新默认20%的DBS与HISDBS已完成组

准确源码ced461705ebc27315a59aefe463f9b4af47130a3、内置v1.0.0-preview.5；与[已公开安装包](releases/v1.0.0-preview.5.md)中的amd64程序字节相同。节点2026-11-13T15:41:11.878815+00:00，默认20%两组各36项、合计72项全部通过。完整四组144项矩阵仍在运行DBS30，HIS30尚未执行，不将依赖步骤计通过。

| 角色 | 初始化 / 第一次冷重建 / 第二次冷重建受控就绪秒数 | 完成检查 | 独立确认消失的登记进程实例 |
| --- | --- | --- | --- |
| DBS20 | 58.60 / 85.87 / 83.43 | 36/36 | 95 |
| HISDBS20 | 60.44 / 80.85 / 27.23 | 36/36 | 94 |

两组使用空配置{}、首次后台自动选择最大合格文件系统/三样本标定，之后跨新Pod/容器ID保留同一profile。独立复算三样本中位数、主机24核及MemTotal/页取整的CPU/high；真实io.max只按读写BPS、IOPS保持max，外部20GiB memory.max不变。每次journal只管理cpu.max/memory.high/io.max。每组保留原镜像/路径/启动链、300秒PG/API/受控启动、45秒缓存以及原liveness和删除预算，实际自身PodUID探针通过。

64MiB/128标记、逻辑备份及独立数据库恢复、两次重建新ID/journal、日志追加、单Agent和disable八项原值还原全部通过。两组namespace、六组父叶和189个登记进程实例独立确认消失。不能据此替代物理备份/同步或600秒完整业务。

[逐项分析](test-results-bandwidth-default20-two-role.json)和[十份259868字节精确原件](test-evidence-bandwidth-default20-two-role.json.gz)包含两组报告、驱动日志、空配置、IO profile、逐日日志和准确只读观察器；[原冻结导出目录缺陷与补充](testing-preview5-qualified-subset.md)保留，没有改计划、原报告、源程序或重跑业务。安装包首次归档记录为当时完成的DBS36项，额外HIS36项在此单独归档；二进制未变。[八项公开下载核对](test-results-preview5-publication.json)已完成。

30%两组及原完整业务、物理备份/同步、正式升级、独占24h+24h、七天老化和未满足硬件门槛继续。所有原52项定义/完成声明、旧失败和旧发布附件保持，稳定1.0未接受。
