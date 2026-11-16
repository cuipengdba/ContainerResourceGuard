# DBS/HISDBS原600秒模式对照终态

固定顺序的四组对照已经终止，实际结果如下。此结论只属于本次对照，不替代另行执行的原18项正式复验，也不改变旧1761 DBS失败或其原因unknown。

|组|终态|通过/记录检查|原负载秒|SQL错误|API错误|
|---|---|---:|---:|---:|---:|---:|
|observe-dbs|passed|11/11|600.1089947919827|0|0|
|enforce-dbs|passed|11/11|600.3323967328761|0|0|
|observe-hisdbs|passed|11/11|600.3082121559419|0|0|
|enforce-hisdbs|passed|11/11|600.2693717109505|0|0|

[逐原件独立复算结果](test-results-original600-comparison-v1-terminal.json)、[全部选定原件及原生终态](test-evidence-original600-comparison-v1-terminal.json.gz)、[冻结15输入](test-plan-original600-comparison-v1.json)、[准确来源](../tests/original600-comparison-v1/)、[独立复算程序](../tests/original600-comparison-v1/qualify-selected-originals.py)。共56个选定原件/3274433字节，逐长度/摘要核对，缺失项在机器结果显式保留。准确PID/start、namespace、父叶cgroup及登记进程实例消失已另行复核。四组结果均保留，没有追加重试、资源放宽或SLA修改。

## 执行边界

CRG生产源37ca44e0、准确ELF、原镜像/start.sh/软件/数据路径、只读CCG及缓存enforce不变。外部8核/20GiB，手动7.2核、memory.high20001980416、读写64MiB/s和手动4096IOPS相同，仅CRG mode不同。产品仍是CPU/内存/IO各独立百分比默认20，百分比IO仅带宽，手动可选IOPS；不额外限制其他资源。

每组原9项检查与2项辅助观察分别保留，总计划44。原600秒、零错误/max5秒/p95桶1秒/98%覆盖、备份/同步/独立恢复十项内容和真实PG归属不变。observe没有变更journal属于预期，必须八控制维持门前原值；enforce只改原三项，其他控制保留。每组独立清理后继续，原件保留到整轮终态统一索引取回，不声称每组之间已经下载。

观察器每2秒只读本组计数和固定PG等待，1800秒/900样本/4MiB有界，负载之前取首样本、完整窗口后按身份标记停止；准确辅助入口/PID/start防止误停原PID1/Agent/cache。PSI缺失如实unavailable，不填零也不宣称无压力。错误事件与实际PG等待/计数区间的相关结果见独立JSON，采样非原子，单次固定顺序和缓存/宿主噪声不足以证明因果。

## 单独exec探针诊断必须保留

以下时间包含宿主kubectl exec/su/命令进程启动及请求，不能直接当作容器内原生请求时延。冻结前既有native-campaign模式将这个原5秒标志原样保留为诊断，只有成功原生负载完整覆盖备份窗口才接受内容周期；本轮没有修改此规则。false仍是false，不改成通过，也不据此宣称全部请求都低于5秒或确定CRG因果。

|组|单独exec原5秒标志|API最大秒|SQL最大秒|
|---|---|---:|---:|
|observe-dbs|True|2.5246027519460768|2.653988768113777|
|enforce-dbs|False|5.3326125962194055|2.000637812074274|
|observe-hisdbs|False|1.5596326820086688|8.214852486969903|
|enforce-hisdbs|True|4.073284145910293|2.455860415007919|


## 历史与接下来

[原冻结设计](development-next-business-comparison-frozen-design.zh.md)、[启动前及首个运行快照](development-original600-comparison-frozen-v1.zh.md)保留。原生22项/Windows21项加1项平台跳过为辅助代码资格，首次Windows夹具错误及两次SSH传输断开和未启动证明继续保留。[受控锁v1/v2失败与v3成功](development-controlled-sql-wait.zh.md)、旧1761业务失败不能被本次结果覆盖。

若本次通过，还需另行冻结新原18项/各600秒，再从零24h observe、同容器24h enforce、新七天及原老化后故障/恢复/升级/稳定发布门槛。若失败，先根据准确现象处理，保持原门槛和旧来源。本次同时归档了有明确终态前置断言的下一次正式18项准备程序；只有本次独立44/44、准确原件和清理都满足才允许生成新冻结目录，归档不代表该程序已执行、上传或启动。52项定义/18项既有范围声明不增加，稳定1.0未接受，preview.5不变。
