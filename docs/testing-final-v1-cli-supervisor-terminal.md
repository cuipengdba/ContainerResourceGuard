# 固定最终候选：CLI状态与可选启动安装实际终态

固定最终ELF与准确源码保持。本轮26/26主检查、48/48子检查通过，两角色各自新600秒；没有重建ELF、替换公开下载或更改配额/SLA。

| 角色 | 实际秒 | SQL 成功/错误 | API 成功/错误 | CLI命令 | 状态观察 |
| --- | --- | --- | --- | --- | --- |
| dbs | 600.36 | 301/0 | 121/0 | 31 | 4 |
| hisdbs | 600.382 | 301/0 | 121/0 | 31 | 4 |

每角色22项在线子检查、2项测量后的卸载子检查。status/doctor/preflight实际human/JSON核对手动请求、宿主基数、自身cgroup、目标与实际CPU/内存/IO。四次status分别观察持锁、静默后未持锁、快照自然老化至少305秒、恢复后的单一最终ELF写入者；不编辑时间戳或mtime，status读取不改原持久快照。静默及恢复、全部在线命令和状态观察均独立核对位于各自成功的原600秒内；没有把快照年龄或写锁当作数据库健康。

两种已知公开模板（shutdown结尾 || : 和 || true）均完成只读预览、摘要保护和私有副本安装；活动Agent写锁、错误源/辅助脚本/ELF摘要、未知布局、链接别名、重复旧源及仍有自有journal时卸载均明确拒绝。真实私有厂商脚本只复制并核对摘要，本轮两角色布局不在支持模板内，均安全拒绝且保持原字节；不声明自动改写任意DBS/HISDBS私有启动脚本，不执行副本或再起业务。

成功原600秒结束后才disable，恢复全部8项运行时原值和空自有journal，再合法卸载两种已安装副本，冻结检查程序核对原字节/模式和私有回执。公开准确原件含CLI响应及断言结果，不含私有脚本/备份内容，因此独立复算不冒充重新读取已清理的私有文件。原SQL/API零错误、最大5秒、p95桶上界1秒、98%覆盖率、64MiB内容及主库/PID1/缓存保持。

准确导出18份、791216字节；55条登记记录（53个去重PID/start）、runner/两driver、两namespace及父叶cgroup均已独立确认消失。旧七天任务保持；本轮不转记长期。

[独立复算](test-results-final-v1-cli-supervisor-terminal.json)、[全部准确原件](test-evidence-final-v1-cli-supervisor-terminal.json.gz)、[冻结协议及输入](testing-final-v1-cli-supervisor.md)、[准确源码5项unit/race事件复核](test-results-final-v1-supervisor-source-event-review.json)。源码事件是既有同修订证据，不能替代本轮运行或声称新的故障注入/厂商ARM。

P08.1在“仅支持已验证模板、未知脚本/摘要拒绝、当前容器内预览/备份/卸载”的原定义范围完成，当前17/52。P07.1仍部分完成：本轮补齐手动状态、年龄、写锁和业务区分；独立百分比、上层约束、外部冲突、profile覆盖及重载代次的human/JSON逐字段兼容覆盖仍须闭环。不借本轮结果扩大完成范围。

manual固定7.2CPU/high20001980416B/双向64MiB每秒/手动4096IOPS，外部8CPU/20GiB保持；不代表默认20%业务性能通过。未知未来状态格式、镜像持久化、压力和真实长期分别继续。稳定1.0尚未接受，当前公开下载仍preview.5，所有旧失败和上传前拒绝保留。
[可选helper准确源码shell补验](test-results-final-v1-optional-source-shell.json)：在本轮业务终态之后，三个准确同修订脚本实际运行missing/denied/invalid/crash/hang/ignore-term六种模拟辅助故障，模拟业务均正常结束并保留原退出码37，整个自有进程会话成员消失。此为单独源码shell集成验证，不计入26/48，不冒充最终ELF或厂商业务故障注入。
[下一项P07.1完整输出组合设计](testing-final-v1-cli-output-matrix-design.md)仅设计归档，尚未冻结、上传或启动。
