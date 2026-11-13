# 当前带宽百分比的四个完整启动组合

产品源码ced461705ebc27315a59aefe463f9b4af47130a3，同一preview.5发布程序。每个完成组都是原36项/三次不同Pod和容器ID启动，完整组来源如下：

| 角色/百分比 | 完成任务 | 通过检查 | 受控就绪秒数 |
| --- | --- | --- | --- |
| DBS20默认 | 原1129 | 36/36 | 58.60 / 85.87 / 83.43 |
| HISDBS20默认 | 原1129 | 36/36 | 60.44 / 80.85 / 27.23 |
| DBS30显式 | 原1129 | 36/36 | 65.92 / 55.53 / 24.23 |
| HISDBS30显式 | 独立1190纳秒兼容v2 | 36/36 | 60.51 / 62.66 / 65.85 |

这些是跨独立任务的四个完整组，共144项完整组检查；不能将原四组矩阵称为144项全部通过。原1129确实有日志跨午夜断言失败，终态129记录/128通过/1失败/15未执行，369登记实例清理；独立1170又因Python3.9.21纳秒解析失败，9通过/27未执行、31登记实例清理，两份原报告保留。1190修正的是验收日志读取/日历规则，程序字节、原业务负载和时限不变。

1190三次启动各自核对原300秒PG/API/managed、45秒缓存、原Kubelet exact PodUID探针、单Agent、真实内核值和完整journal，memory.max外部20GiB保持、无新增默认IOPS。自动最大合格文件系统的三样本中位数profile跨ID复用，64MiB/128标记、逻辑备份及独立数据库恢复、八项disable原值恢复通过。namespace、三组父叶及106登记实例独立确认消失。该项不是物理备份/同步或压力/长期验收。

[原1129终态及23份原件](testing-bandwidth-percent-terminal.md)、[1170失败及七份原件](test-results-bandwidth-calendar-v1-terminal.json)、[1190逐项分析](test-results-bandwidth-calendar-v2-terminal.json)、[1190精确原件及独立清理](test-evidence-bandwidth-calendar-v2-terminal.json.gz)、[当前验收入口](current-acceptance.md)。[发布与升级](upgrade-preview4-preview5.zh.md)及[下载页](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v1.0.0-preview.5)保持工程预发布标记。原52项、正式升级、完整600秒/物理备份同步、独占24h+24h、七天和硬件范围继续。
