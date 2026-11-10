# 分区组合候选：稳定开销终态

当前未发布组合程序d3706f3、AMD64程序3a1ce7dbf5630f8f1c823005ceb4958653c6c235b2ba5026956ca6597f1926f9，按[第二次冻结计划](test-plan-partition-steady-overhead-retry.json)完成45秒预热后的实际测量。总实际秒数为1800.039758，三场景均通过，运行器已退出0，namespace独立确认不存在。[结果和逐场景指标](test-results-partition-steady-overhead.json)固定程序、内核、阈值与范围。

| 场景 | 样本数 | 单核平均CPU | RSS最大 | Agent写入增量 | 状态最短写入间隔 |
|---|---:|---:|---:|---:|---:|
| healthy | 181 | 0.021667% | 10342400B | 159744B | 300.001s |
| export-failure | 181 | 0.021667% | 10027008B | 45056B | 300.000s |
| readonly | 181 | 0.031111% | 10018816B | 1142784B | 300.024s |

每次采样核对同一PID1与唯一Agent的start ticks/cgroup关系，以及全部8项实际控制值不漂移；Agent只接管CPU/内存/IO，其他5项原值保持。三组无新增OOM kill，日文件为0600且启动记录v2；持续导出失败仍保持标记和unavailable，只读cgroup持续degraded。原单核CPU≤0.1%、RSS≤20MiB、健康写入≤8MiB/故障≤16MiB及状态写入间隔≥299秒均未放宽。

只读场景CPU1核、内存256MiB为原外部值，夹具仅对自有叶cgroup设置读写64KiB/s和各8IOPS；不能描述为只读Agent设置成功。另两场景实际CPU0.25核、内存128MiB及相同IO上限。该轮是手动固定预算，不包括首次磁盘标定，原镜像只作为shell环境/占位PID1使用，不能替代DBS/HISDBS业务或宿主采集器成本。

[首轮遗漏私有可选启动脚本而失败](test-results-partition-steady-overhead-startup-failure.json)保留，补齐同源码脚本及前置摘要检查后才重测；产品和原90秒启动期限、45/1800秒时长、预算及阈值均未改变。旧d6开销结果独立保留。

本轮通过后，当前程序真实路径DBS/HISDBS顺序复验可按[已冻结计划](test-plan-partition-realpaths-business.json)继续；开销通过不能反推业务通过。默认20%业务失败、正式24h+24h、至少7天和未测硬件/发布维护门槛仍保留，尚未正式发布。
