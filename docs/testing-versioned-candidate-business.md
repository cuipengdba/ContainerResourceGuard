# 版本化候选DBS/HISDBS真实路径终态

真实v1.0.0候选AMD64程序dbc48aa5，在自身1800秒开销通过且清理后，按[原冻结计划](test-plan-versioned-candidate-business.json)完成DBS/HISDBS各实际600秒业务，合计12项外层检查通过。原生SQL/API零错误、最大5秒及p95桶上界1秒、≥98%覆盖、64MiB完整性/主库未重启，原备份/同步10项内容及独立恢复/临时清理均通过。见[逐角色实际结果](test-results-versioned-candidate-business.json)。运行器退出0，业务Pod删除，namespace独立确认不存在。

原镜像/start.sh、PG参数、缓存进程和CCG只读挂载与真实路径保留，一容器一Agent；三个实际资源值符合manual7.2核、20001980416B内存、双向64MiB/s及各4096IOPS，其他5项原值保持。原总启动300秒、缓存45秒和每日0600/v2日志检查未放宽。

本结果仅属于实际新ELF，开发版旧600秒、原observe24h及d370七天结果独立保留。默认20%失败并未因此逆转，不能将manual64成绩写成自动30%业务性能；ARM厂商业务、物理多设备、实际长期及维护兼容条件独立继续，尚未发布稳定1.0。后续[自身辅助故障](testing-versioned-candidate-faults.md)另有固定计划及终态，不提前宣称通过。
