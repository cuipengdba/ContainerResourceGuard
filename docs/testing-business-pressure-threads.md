# 完整压力联测接入只读线程采样

R167[冻结计划](test-plan-business-memory-pressure-threads.json)及`tests/vendor-business-memory-pressure-threads.py`已实现，压力业务尚未执行。原R142失败、执行器、计划和原32项主检查全部保留；两角色各600秒、七次重载和四个压力恢复区间、原数据/配额/余量/所有SLA/原10项引擎及30秒备库停止不变。通过AST逐项比对，原完整业务方法仅增加一次观察器启动和一次进度保存。

新增`vendor-thread-session.py`只用于测试，按各自cgroup中8090监听socket的唯一所有者定位，不猜HIS程序路径。固定PID/start/exe后，调用已通过19项及两角色15秒实际观察的原只读采样器。先收到完整首样本握手，才开始原引擎和压力窗口。最多900秒/每秒64线程/32MiB，原业务的超时不延长。主报告只存身份、有界摘要和原始报告SHA256/路径，完整样本单独保存。

进程生命周期使用自己创建的子进程PID/start/入口和pidfd；TERM后等待15秒落盘，必要KILL也仅针对相同子进程并明确判诊断失败。没有向DBS/HISDBS发信号或直接写控制文件。wait4只统计这个观察器的完整CPU/块IO/峰值RSS，包含启动哈希和末尾写盘；采样CPU单列，不能代替完整开销。原生请求和exec探针分别计数，原生聚合缺少逐请求时间的盲区保持。

[实际14项生命周期资格](test-results-thread-session.json)已在Linux/Python3.9.21、内核5.14节点通过，覆盖首样本握手、错误start拒绝信号、TERM和自然退出、独立wait4统计、目标/控制值保持、二次停止幂等、原业务错误对象优先及成功业务仍暴露诊断故障。两个观察器已独立核对消失，临时sleep退出也已在资格报告中验证。首次R164在任何观察器启动前因SSH用户会话不暴露cpu.max而失败，完整失败记录保留；R165将控制文件缺失明确记录为unknown，不创建控制器，也不将此资格作为厂商容器控制器验收。

默认只读前置还会检查R142实际失败/清理/原输入恢复，固定19项和14项资格报告及两角色原15秒报告摘要。新root/namespace/run-id，计划和工具不可替换，execute需要新隔离marker。采样故障、缺字段、截断及采样间隔分别记录，不将缺失当零。清理异常单列，不能覆盖最初业务错误；完整成功仍须原32项和两角色600秒证明。

这是诊断接入和工具资格，尚未关闭R142三个原生API错误、两次内层timeout、历史exec延迟或R120备库停止超时。正式24h+24h、实际七天及后置、ARM厂商业务、多物理设备和原52项全部范围保持。产品程序和已发布预览包不变。


[实际前置9项](test-results-pressure-thread-preflight.json)通过：默认只读、缺少隔离marker、namespace/criteria/线程协议/观察器路径/压力协议/工具摘要/API摘要篡改拒绝，目标root及namespace独立核对仍不存在。此时新压力业务尚未启动。[原七天固定进程](test-progress-seven-day-during-thread-session.json)继续各自原计时，无原生SQL/API错误，仍未604800秒。
