# 原30→20压力补测：绑定已验证的旧Python运行时工具

状态：R142新执行器和[计划](test-plan-business-memory-pressure-legacy.json)已冻结，业务尚未执行。原[R130失败](test-results-business-memory-pressure-failure.json)、执行器、计划、辅助工具及开始快照保留；R113/R120等历史失败也不改写。

完整协议沿用[原30→20压力及安全重试](testing-business-memory-pressure.md)：两角色各600秒、原七次重载加四个压力/恢复区间、32项主检查、相同CPU/IO/内存数值、真实用量大于20%目标、六秒保持、释放后同代次重试。8个控制文件回读、原PID1/PG/Agent/cache/零OOM、原10项引擎、30秒备库停止和所有原SLA/余量/期限不变。不是1%替代，不提高额度或延长等待。

唯一运行工具变化是绑定已在两种原镜像验证的v2辅助工具，接受实际Python2.7.5的linux2平台名。12GiB/64MiB/十秒租约/240秒寿命/自身14GiB地址空间及释放逻辑保持；新增在握手校验前保存完整hello供失败定位。Linux7项与两镜像16项仅验证64MiB协议/释放，不替代真实高用量或业务。见[运行时终态证据](testing-memory-pressure-legacy-runtime.md)。

使用新执行根/namespace/run-id，固定原R130失败及运行时资格原报告摘要，前置重新核对运行器/worker/namespace/cgroup消失、原输入恢复、原Pod和程序/profile摘要。默认只读，显式execute需隔离marker；计划/工具摘要或预算篡改拒绝。辅助工具不直接写任何cgroup控制文件，主程序和已发布资产保持。

原R120来源错误完整业务联测、默认20%和自动30%持续性能、完整并发、正式24h+24h、真实七天及后置、ARM厂商业务和独立物理多设备继续分别验收。本协议不能关闭它们或将旧失败改成通过。
