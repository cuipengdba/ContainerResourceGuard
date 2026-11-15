# 固定最终候选：完整输出组合1551失败终态

实际唯一启动后，两角色均在首次50/50/100状态检查遇到同一测试断言错误，整体failed/exit1。本轮不是600秒业务通过，不接受P07.1，17/52保持。两角色实际完成各8项启动主检查、1项初始manual输出子检查；合计16项已记录主检查通过、10项未执行，2项输出子检查通过、26项未执行。另有两次在汇总主检查之前抛出的AssertionError，不能因已记录检查全true把整轮改判通过。

实际CPU=800000 100000、memory.high=21474836480、IO=rbps64700080/wbps37470104/IOPS原基线max，均与预先独立算出的50%裁剪目标相等；configuration.accepted、generation2，三项items均applied/unchanged。human与JSON均返回degraded，且完整显示两条上层约束警告。测试程序错误地只在坏配置或冲突时允许degraded，遗漏准确源码Engine.Apply“只要plan.warnings非空就聚合为degraded”的既有定义。

因此观察到的是执行器预期错误，没有观察到额度换算或读回错误，也不能据此宣称数据库已完成600秒验证。后续独立百分比、坏配置、profile只读覆盖、外部CPU冲突与显式恢复均未执行；不声称已恢复所有运行时原值。隔离夹具按原finally清理，全部56条登记记录（54个去重PID/start）、runner/两driver、两namespace和父叶cgroup已独立确认消失，产品/原厂部署未被修改。旧七天任务保留，时长不转记。

准确导出20份共336920字节；全部成员字节/SHA、source-map、原coordinator及两角色报告、实际JSON/human响应、失败栈和已知句柄/namespace/cgroup清理逐项复核。原要求、原配额和原SLA保持，失败原件不改写。修订应仅按源码将已验证约束警告纳入聚合状态预期，继续严格核对两条警告、三控制applied及目标/实际值，并在全新冻结协议/namespace/输出/run-id重新运行原600秒，不能沿用本轮短时计数。

[独立复算](test-results-final-v1-output-matrix-failed.json)、[全部准确原件](test-evidence-final-v1-output-matrix-failed.json.gz)、[启动与首次观察原件](test-evidence-final-v1-output-matrix-start.json.gz)、[实际启动器](../tests/final-v1-output-matrix-launch.py)、[只读观察器](../tests/final-v1-output-matrix-observe.py)、[原冻结协议](testing-final-v1-output-matrix.md)。稳定1.0尚未接受，公开preview.5及八附件/标签不因本轮改变。
