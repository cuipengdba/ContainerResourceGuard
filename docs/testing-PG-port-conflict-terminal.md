# 首轮真实PG冲突：失败终态与独立诊断

原计划44项，实际18项：16通过、2失败、26未执行。两个冲突组均停在第9项；两个正常完整600秒组从未启动。原失败不改判，engine也始终保留failed/非零退出。

实际完成物理备份后，standby启动失败。原断言读取standby.log，但该文件只有logging collector重定向提示。终态后另取本次current_logfiles指定CSV，核对全部记录属于本次启动PID/日期，DBS PID2118、HISDBS PID2137，各6条1186字节，均有127.0.0.1:55432 Address already in use及FATAL无法创建TCP/IP sockets。这个补充诊断解释失败，不补执行未跑的检查，不追认原套件通过。

22份白名单原始文件204277字节，逐项摘要绑定原索引、source-map、协调器及独立终态观察。原runner及两driver、60条登记进程记录（52个唯一PID/start实例）、两个namespace及父叶cgroup独立确认消失。原始报告/日志完全保留，没有触碰生产容器。

[终态资格](test-results-PG-port-conflict-terminal.json)、[原始证据及后续独立诊断](test-evidence-PG-port-conflict-terminal.json.gz)、[原冻结计划](test-plan-PG-port-conflict-full600.json)。修正读取器的25项回放包括两角色实际CSV逐字节恢复、混合PID、日期/时间窗不符、空/损坏/过大/丢失文件、越界路径及不支持目的地；不合格只返回partial且不导出日志。这是回放资格，不是新的PG或业务验收。

[修正后的全新44项计划](testing-PG-port-conflict-CSV-full600.md)使用全新namespace、run ID和私有数据目录；要求此前失败任务终结清理，并在节点只读重放两份实际CSV。CPU/内存/IO预算、原PG命令/超时和原600秒业务SLA全部保留。默认20%完整业务失败、原52任务及长期门槛继续，稳定1.0尚未接受。
