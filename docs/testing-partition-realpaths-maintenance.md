# 分区组合候选：真实路径维护终态

按[冻结计划](test-plan-partition-realpaths-maintenance.json)，50671aa开发程序与当前d3706f3组合程序在DBS/HISDBS原镜像和真实容器路径完成升级、回退和恢复旧Agent。两角色各完整600秒、22项检查通过；运行器退出0，所有测试Pod及namespace独立确认清理。[结果](test-results-partition-realpaths-maintenance.json)固定两个程序摘要及实际操作时间。

| 业务 | 原生测量秒 | SQL最大秒 | API最大秒 |
|---|---:|---:|---:|
| dbs | 600.247 | 0.010915 | 0.008842 |
| hisdbs | 600.243 | 0.010985 | 0.012045 |

每套8个命令区间均完整位于原生600秒内：quiesce、安装、即时回退、再次安装、enable新Agent、再次quiesce/回退、enable旧Agent；Agent恢复身份也在活动窗口检查。原值journal字节、8项实际控制、业务PID1和原缓存进程身份保持；SQL/API零错误、最大≤5秒、p95桶上界≤1秒、样本覆盖≥98%，64MiB载荷完整、PG未重启、线程正常退出，无新增OOM。测量结束后disable恢复真实运行时原值，其他5项保持。

两个程序都显式声明同一锁协议和journal v1；已发布main预览缺声明而拒绝首次安装的结果不变。这里的两个对象均未发布，不能关闭最近两个已发布次版本升级条件。原镜像、start.sh、PG参数、只读缓存挂载保持；预算仍为CPU7.2核、内存20001980416B、读写各64MiB/s与各4096IOPS。

本轮只覆盖本机Linux5.14/AMD64/单设备整盘manual IO及原生SQL/API维护窗口，备份内容在独立业务轮次验收；不声明分区profile迁移、ARM厂商业务或独立物理多盘已测。默认20%失败及自动30%持续性能、正式24h+24h、至少7天与最终发布审计条件不变。旧fc2基线和固定d6后续enforce保持原来源，当前组合仍未正式发布。
