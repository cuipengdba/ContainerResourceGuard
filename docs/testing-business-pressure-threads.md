# 完整压力联测接入只读线程采样

R167[冻结计划](test-plan-business-memory-pressure-threads.json)及`tests/vendor-business-memory-pressure-threads.py`已执行并失败；[完整终态](test-results-business-pressure-threads-failure.json)记录DBS实际600秒/两次SQL错误，HIS业务未执行。原开始快照作为历史保留。原R142失败、执行器、计划和原32项主检查全部保留；两角色各600秒、七次重载和四个压力恢复区间、原数据/配额/余量/所有SLA/原10项引擎及30秒备库停止不变。通过AST逐项比对，原完整业务方法仅增加一次观察器启动和一次进度保存。

新增`vendor-thread-session.py`只用于测试，按各自cgroup中8090监听socket的唯一所有者定位，不猜HIS程序路径。固定PID/start/exe后，调用已通过19项及两角色15秒实际观察的原只读采样器。先收到完整首样本握手，才开始原引擎和压力窗口。最多900秒/每秒64线程/32MiB，原业务的超时不延长。主报告只存身份、有界摘要和原始报告SHA256/路径，完整样本单独保存。

进程生命周期使用自己创建的子进程PID/start/入口和pidfd；TERM后等待15秒落盘，必要KILL也仅针对相同子进程并明确判诊断失败。没有向DBS/HISDBS发信号或直接写控制文件。wait4只统计这个观察器的完整CPU/块IO/峰值RSS，包含启动哈希和末尾写盘；采样CPU单列，不能代替完整开销。原生请求和exec探针分别计数，原生聚合缺少逐请求时间的盲区保持。

[实际14项生命周期资格](test-results-thread-session.json)已在Linux/Python3.9.21、内核5.14节点通过，覆盖首样本握手、错误start拒绝信号、TERM和自然退出、独立wait4统计、目标/控制值保持、二次停止幂等、原业务错误对象优先及成功业务仍暴露诊断故障。两个观察器已独立核对消失，临时sleep退出也已在资格报告中验证。首次R164在任何观察器启动前因SSH用户会话不暴露cpu.max而失败，完整失败记录保留；R165将控制文件缺失明确记录为unknown，不创建控制器，也不将此资格作为厂商容器控制器验收。

默认只读前置还会检查R142实际失败/清理/原输入恢复，固定19项和14项资格报告及两角色原15秒报告摘要。新root/namespace/run-id，计划和工具不可替换，execute需要新隔离marker。采样故障、缺字段、截断及采样间隔分别记录，不将缺失当零。清理异常单列，不能覆盖最初业务错误；完整成功仍须原32项和两角色600秒证明。

这是诊断接入和工具资格，尚未关闭R142三个原生API错误、两次内层timeout、历史exec延迟或R120备库停止超时。正式24h+24h、实际七天及后置、ARM厂商业务、多物理设备和原52项全部范围保持。产品程序和已发布预览包不变。


[实际前置9项](test-results-pressure-thread-preflight.json)通过：默认只读、缺少隔离marker、namespace/criteria/线程协议/观察器路径/压力协议/工具摘要/API摘要篡改拒绝，目标root及namespace独立核对仍不存在。此时新压力业务尚未启动。[原七天固定进程](test-progress-seven-day-during-thread-session.json)继续各自原计时，无原生SQL/API错误，仍未604800秒。


R167完整压力线程联测[已启动并归档开始快照](test-start-business-pressure-threads.json)：固定原运行器/worker/观察器PID及启动ticks；快照时DBS11区间、13项局部检查通过，真实高于20%目标时延后，释放后同gen7自动应用20%再恢复30%。原600秒负载/引擎仍pending、HIS业务尚未执行，不计完整业务通过。协议源码三个固定提交的CI均通过，公开45个来源/证据blob已核对，原发布包和历史失败保持。


## R167完整终态：失败，SQL慢响应已获得服务端证据

[终态结果](test-results-business-pressure-threads-failure.json)：DBS实际600.269469秒，原生SQL297次/2错误，最大5.013924秒、p95桶0.05秒、覆盖99%；API121次/0错误，最大0.010644秒。64MiB完整性、原PG实例和线程停止均保持。11个重载/压力区间和13项局部检查通过；原10项引擎只完成content-passed-native-pending，93个分段API探针最大外层3.975154秒。原零错误/最大5秒未通过，主执行器按NATIVE_COMPLETION_EXIT退出1，HIS业务未执行，整轮不接受。

取得[601个原始只读样本gzip](test-evidence/pressure-thread-dbs.json.gz)，原文9160761字节，解压SHA256为3e919b62b9b02c134da9c45383b031e46f14c417c30be4694d147ad2bcf3afcb。首样本比原生负载开始晚约1.004秒，覆盖全部引擎/重载/压力区间，最大采样间隔1.000684秒，47线程，无race/截断。预定业务结束后TERM观察器保存partial，原报告incomplete/observer-interrupted及退出2保持；不改称自然900秒完成。采样CPU2.750426秒，整个观察器wait4 CPU3.145690秒，峰值RSS76864KiB，末尾写盘/停止0.401589秒；这些开销不证明无业务影响。

601样本中cgroup CPU nr_throttled和throttled_usec增量均0，OOM kill均0；PSI三个文件均不可用。DBS API进程仅一次D/folio_wait_bit_common样本，不能解释SQL根因，也不能排除其他进程IO等待。

独立取到实际主库日志postgresql_2026-11-11_194403.csv，原文件SHA256 a1d62f17e52c34d3cbc3e5a2009132695b50104a6f74147d28c66692342ffb3a。19:46:08.291/.292 CST附近，三个后端对同一合成键769–784的UPDATE记录13661.481、8648.039、3633.872毫秒服务端执行时间。原负载源码在捕获SQL异常时关闭连接并保持iteration，下一次连接重复这一键范围；日志因此显示重叠慢UPDATE，不能仅凭它认定行锁、磁盘或内存回收是初始阻塞原因。原生聚合未记两次错误各自时间/异常，不能硬配成逐请求证明。日志duration倒推的约19:45:54.630至19:46:08.291区间，其周围实际memory.max已恢复30%，CPU无节流；先前压力后的影响、PG等待事件和宿主IO仍需分别证据。

运行器/worker/观察器、Pod namespace及全部所建cgroup独立核对消失；两角色原config字节、profile缺省状态和发布ELF摘要保持。旧R142/R120和其他失败不关闭。下一步先补原生SQL/API逐错误时间与类别、PostgreSQL活动/等待事件及会话身份诊断，保留原600秒、相同请求/重试行为、配额、32项主标准及全部历史证据；补证工具不能成为业务启动条件。暂不直接重复同一盲区的压力轮次。


R194[原生请求/PG等待诊断资格](testing-native-request-pg-diagnostics.md)完成：Linux23项、两厂商镜像各23项+3入口保护+16真实PG检查通过；正常请求通过，受控锁各保留一次原SQL超时，并取得对应后端/等待/阻塞者。三次先前资格失败和旧源码保留，四Pod cgroup/namespace/运行器独立确认消失，原输入/程序保持。仅采集链路资格，不关闭R167/R142/R120、原32项/两角色600秒或长期条件。
