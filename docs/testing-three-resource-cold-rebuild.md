# 三资源程序的真实路径备份与冷重建

2026-11-10，第17轮四格、每格两次原启动，共**88项检查通过**；全部自有Pod已移除，终态及独立查询均确认namespace不存在。[计划](test-plan-three-resource-cold-rebuild.json)与[按真实二进制摘要归档的结果](test-results-three-resource-cold-rebuild.json)分别保留。

使用main7638和组合d6ea657程序、原DBS/HISDBS镜像、原start.sh/PG参数和只读缓存挂载，复现实际容器路径。固定手动CPU7.2核、内存20001980416B、读写各64MiB/s与4096IOPS，其他五项控制值保持。每次启动仍须在300秒内PG/API就绪且managed，原缓存在就绪观察后45秒内enforce且不超总启动期限。

| 程序/业务 | 首次就绪且managed秒 | 备份后新Pod就绪且managed秒 |
|---|---|---|
| rc3-dbs-manual64-rebuild | 20.735 | 54.091 |
| rc3-hisdbs-manual64-rebuild | 36.81 | 19.193 |
| v10-dbs-manual64-rebuild | 27.918 | 22.532 |
| v10-hisdbs-manual64-rebuild | 23.65 | 18.788 |

每格先生成16384行/64MiB固定payload与128行标记（合计8256），创建并核对schema级逻辑备份；正常删除旧Pod并确认旧cgroup消失，再以相同数据、配置、状态、缓存和日志目录创建新Pod。新容器/资源身份已变化，配置摘要不变，旧journal隔离、新journal对应新身份，不需填写容器或Pod ID。

重建后数据与备份摘要一致，PG按冷启动正常重启；日志旧内容前缀保留并追加，每个容器恰有一个摘要匹配的Agent。独立逻辑恢复库核对64MiB payload及标记，且不修改主库原数据。末尾disable恢复**新容器实际运行时原值**（8核、20GiB、io.max空及其他五项不变），OOM计数不增加。

本轮恢复库位于同一PG服务，不声称独立物理服务器恢复；之前第12轮物理恢复证据单独保留。本轮是手动预算的冷启动/备份/身份/日志验证，不能替代默认20%或自动30%性能验收，也不关闭24h+24h、七天和未测硬件门槛。
