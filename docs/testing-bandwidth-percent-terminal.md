# 带宽百分比原矩阵终态

源码ced461705ebc27315a59aefe463f9b4af47130a3、实际preview.5发布程序不变。原冻结任务3533a4d6…、计划b2c68f37…已经失败退出，不再运行或重启。

| 角色与百分比 | 检查通过 / 已记录 / 计划 | 受控就绪秒数 | 未执行 |
| --- | --- | --- | --- |
| DBS20 | 36 / 36 / 36 | 58.60 / 85.87 / 83.43 | 0 |
| HISDBS20 | 36 / 36 / 36 | 60.44 / 80.85 / 27.23 | 0 |
| DBS30 | 36 / 36 / 36 | 65.92 / 55.53 / 24.23 | 0 |
| HISDBS30 | 20 / 21 / 36 | 59.06 / 86.27 | 15 |

合计128通过、1失败、15未执行，11/12次启动。三个完成组保留64MiB数据/128标记、逻辑备份及独立恢复、两次冷重建/不同ID、原探针及disable八项恢复。原300秒PG/API/managed、45秒缓存、720秒探针观察和120秒删除预算均未放宽。

HISDBS30失败项为after-extraction-daily-log-appends-across-ID-change。冻结脚本在首次启动后缓存旧日期文件列表，原liveness观察跨过午夜，之后却要求每个旧日期文件在第二个容器启动后继续增长。精确日志显示：Nov13文件最后记录23:56:24；Nov14文件00:00:00写log_day_started、00:02:18写第二次agent_start，符合每日一文件。原断言不适用于跨日期，程序无须因本项改动。仍保留原失败及15项未执行；需要修正验收脚本后另建独立HISDBS30完整36项任务，不能补写原报告或借用其它角色。

节点16:26:50只读复核：runner及四driver原PID/start均消失，四namespace、11组父叶及369个登记进程实例消失。冻结runner的导出路径仍错误使用preview4目录，原10份导出和缺失清单保持；单独只读索引绑定准确报告，补充实际13份配置/profile/逐日日志，没有修改冻结工具、业务或原件。共23份528700字节逐件核对SHA256。

[逐项结果](test-results-bandwidth-percent-terminal.json)、[23份精确原件及独立清理](test-evidence-bandwidth-percent-terminal.json.gz)、[原冻结计划](test-plan-bandwidth-percent-startup.json)、[旧默认20%两组快照](testing-bandwidth-default20-two-role.md)。preview.5包与标签保持；原完整矩阵、稳定1.0均未接受。
