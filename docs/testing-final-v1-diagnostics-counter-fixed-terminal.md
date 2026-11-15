# 固定最终ELF：只读诊断修订轮终态

冻结1465只修正测试末尾计数，并增加原失败终态与清理守卫；同一最终ELF、诊断模块、业务引擎、额度和全部原标准保持。原1448整体failed/exit1原件保留；本轮重新完整测量，不继承旧时长。

| 角色 | 主检查 | 诊断子检查 | 原生秒数 | SQL次数/错误 | API次数/错误 |
| --- | --- | --- | --- | --- | --- |
| normal-dbs | 10/10 | 19/19 | 600.304 | 300/0 | 121/0 |
| normal-hisdbs | 10/10 | 19/19 | 600.342 | 300/0 | 121/0 |

两角色均满足原600秒、SQL/API零错误、最大5秒、p95桶上界1秒和98%采样覆盖；实际逻辑/物理备份、同步、独立恢复及PG未重启/端口拥有者核对通过。诊断子检查与每角色10项引擎内容检查不重复累计到20项主检查。

只读诊断实际核对本容器三项控制、current/swap、可用stat/events/PSI；events按前后单调值核对，gauge不冒充原子快照、不相加重叠统计。
normal-dbs：标准输出1852字节，本地文件1852字节/0600；内核实际不可用字段 memory.stat.hugetlb, memory.pressure。
normal-hisdbs：标准输出1856字节，本地文件1853字节/0600；内核实际不可用字段 memory.stat.hugetlb, memory.pressure。

白名单及64KiB上限、内容说明、敏感环境标记排除、已有文件/链接/状态/profile拒绝覆盖均实际执行；全部8项内核值、journal、Agent/PID1/缓存/PG保持。仅本地生成，产品不自动上传。缺字段明确不可用，不以零或虚假完整总量代替。准确源码8项unit/race事件补充边界和可用PSI解析；缺失PSI的厂商内核不宣称实际产生压力数据。

22份准确原件共416966字节；29项独立复算通过。runner及两个driver、71条登记记录（55个唯一PID/start）、两组namespace及父叶cgroup独立确认消失。协调报告SHA256 4a7d0a3c04bf82aac0a91b65a44a01601c6e210b2b9b7e6eefacdbc20f674d03。

P05.1/P07.2按归档定义范围完成；不是默认20%业务性能通过，也不代替长期、厂商ARM或多物理设备验收。稳定1.0尚未接受。

[冻结计划与修订](testing-final-v1-diagnostics-counter-fixed.md)、[终态复算](test-results-final-v1-diagnostics-counter-fixed-terminal.json)、[准确原件](test-evidence-final-v1-diagnostics-counter-fixed-terminal.json.gz)、[源码边界事件](test-results-final-v1-diagnostic-memory-source-review.json)、[原失败保留](testing-final-v1-diagnostics-counter-failure-terminal.md)。
