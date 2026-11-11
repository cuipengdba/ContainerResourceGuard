# 版本化候选的冷重建与恢复验证

[冻结计划](test-plan-versioned-candidate-cold-rebuild.json)针对实际v1.0.0程序dbc48aa5，验证DBS/HISDBS各两次启动、共四次启动及44项检查。沿用原manual7.2CPU/20001980416B/双向64MiB/s/各4096IOPS预算，原启动300秒、缓存45秒且在总启动内、宿主28/8GiB内存与20GiB磁盘保留不变。本轮已完成两角色四次启动、44项检查；退出0，namespace独立确认清理。

必须等待自身[在线维护](testing-versioned-candidate-maintenance.md)实际22项/两角色各600秒完整通过、退出0及namespace独立不存在，并核对该报告引用的自身开销/业务/故障实际终态链后，才创建冷重建Pod。冻结维护计划只是合同，不能作为通过成绩；旧3a1开发程序的44项也不转给新摘要。

原镜像/start.sh/PG参数、只读CCG和真实容器路径保留，使用新私有背板/DCS及64MiB合成数据、128个marker。备份后复用同一数据、配置、状态和日志，在旧cgroup消失后创建新Pod，检查新ID、原journal隔离、唯一正确Agent、原缓存新状态与正确程序、原日志前缀追加。独立逻辑恢复数据库核对全部payload/counter及marker；最终disable还原新容器真正运行时八项原值并检查无OOM。

这是新程序自身的冷重建短验证，不是新的600秒性能或长期验收。默认20%/自动30%持续业务、真实老化、两已发布次版本和未测硬件仍单独判断；业务节点、正式基线、固定d6阶段与原七天组件不修改。稳定1.0未发布。


实际终态见[逐项记录](test-results-versioned-candidate-cold-rebuild.json)。原数据、128个marker、备份/独立逻辑恢复、日志前缀追加、新ID/旧cgroup消失和最终真正运行时原值恢复通过；对应新程序dbc48aa5，未转用旧程序结果。
