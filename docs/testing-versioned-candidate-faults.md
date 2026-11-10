# 版本化候选的辅助故障复验

[冻结计划](test-plan-versioned-candidate-faults.json)验证同一v1.0.0新ELF dbc48aa5，运行器已启动并[核实在前置等待](test-progress-versioned-candidate-faults-start.json)：故障namespace尚未创建，实际0场景/0检查；不能写成故障验证已开始或通过。必须先有自身[1800秒三场景开销](testing-versioned-candidate-overhead.md)与[DBS/HISDBS各600秒业务](testing-versioned-candidate-business.md)的完整通过、固定作业摘要及退出0、namespace独立确认不存在，才创建故障Pod。冻结计划本身不是通过结果，运行器将核对真实终态报告和业务记录引用的开销报告摘要。

沿用已通过的开发版20场景/108项标准：每角色缺失、无效、崩溃、卡住、忽略TERM、撤销、实际cgroup只读、profile只读、state只读及真实标定取消。原镜像/start.sh、PG参数、CCG只读挂载和真实路径保持，使用新私有隔离背板和DCS；单独30%仅验证辅助故障隔离，不能追认其持续业务性能。原PG/API90秒、缓存45秒、TERM12秒、宿主保留、实际取消的临时文件/程序/pidfd身份门槛不变。

旧开发版3a1ce7db的20场景结果单独保留，不能记为本次新程序通过。现有正式基线、固定d6阶段和d370七天组件不修改；本轮不代替真实老化状态故障、长期、未测硬件或稳定发布。
