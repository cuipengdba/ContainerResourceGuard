# 分区组合候选：真实路径冷重建终态

当前未发布d3706f3程序、AMD64摘要3a1ce7dbf5630f8f1c823005ceb4958653c6c235b2ba5026956ca6597f1926f9，按[冻结计划](test-plan-partition-realpaths-cold-rebuild.json)完成DBS/HISDBS各两次启动：两格、四次原启动、44项检查通过。运行器退出0，Pod与namespace独立确认清理。[机器结果](test-results-partition-realpaths-cold-rebuild.json)固定实际程序、控制回读、缓存新鲜状态和数据核对。

| 业务 | 首次就绪且managed秒 | 备份后新Pod就绪且managed秒 |
|---|---:|---:|
| v10-dbs-manual64-rebuild | 29.093 | 25.276 |
| v10-hisdbs-manual64-rebuild | 20.250 | 18.476 |

保留原镜像、start.sh、PG参数、真实容器路径及只读缓存挂载，私有数据/凭据/DCS隔离。CPU7.2核、内存20001980416B、读写各64MiB/s与4096IOPS，其他5项原值保持。每次启动PG/API/managed总300秒，缓存在就绪后45秒且总300秒内enforce；额外核对当前cgroup只有一份摘要匹配的缓存run进程、状态文件在本次启动门之后已更新，排除旧缓存状态误判。

每格64MiB有效载荷与128标记行（合计8256）生成逻辑备份；旧Pod正常删除且旧cgroup消失后，重用同一数据/配置/状态/缓存/日志目录创建新Pod。新容器及资源身份变化、配置不变、旧journal隔离到previous、新journal对应新身份。原PG正常冷重启，数据与备份一致，日文件0600/v2记录和旧内容追加保持，每次只有一个当前程序Agent。

独立逻辑恢复库核对有效载荷和标记且不改主库原数据；末尾disable恢复新容器真实原值（8核、20GiB、io.max空及其他5项原值），无新增OOM。恢复库仍在同一PG服务，不声称独立物理服务器；之前原生引擎周期的物理恢复独立归档。

本轮是现有Linux5.14/AMD64/单设备的当前二进制冷重建结果，不复用旧7638/d6的88项，也不替代默认20%/自动30%持续性能、节点重启、24h+24h、七天或未测硬件。当前[七天安排](plan-seven-day-current-candidate.md)仍须实际测量及老化状态后置，不凭这44项提前关闭。
