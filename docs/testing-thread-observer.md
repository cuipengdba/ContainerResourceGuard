# API停顿的只读线程诊断工具

针对[R142真实压力业务失败](testing-business-memory-pressure-legacy.md)补充诊断，产品CRG、原启动链、既有测试来源及发布附件不变。该工具只用于已授权隔离测试节点，每次绑定一个业务进程与其所属cgroup；不接入start.sh，不成为DBS/HISDBS启动前提，也不是管理多个容器的Agent。

## 实现与边界

`tests/vendor-thread-observer.py`在Linux/Python3主机执行。计划固定源代码摘要、单一PID、启动ticks、实际exe摘要、纯v2成员路径、1至900秒及一个全新私有输出文件。默认仅校验，不创建输出；显式execute还需隔离marker。持有原proc/cgroup目录FD，逐次核对启动时间、exe设备/inode、成员关系及cgroup设备/inode；变化或消失便停止，不自动寻找替代进程。

每秒最多64线程，读取stat、wchan、schedstat、白名单status及cpu.stat、io.stat、memory.current/stat/events、PSI和三个实际控制值。每个输入最多64KiB、单样本32KiB、报告32MiB；样本缓存在内存，结束才一次写入并fsync。新输出0600且拒绝既有文件/符号链接。TERM只处理本观察器并保存partial；不向业务发信号，不写任何cgroup控制值。缺失/无权限字段记录unknown，不补成0；不收集命令行、环境、用户栈、进程内存或FD内容。

字段依据Linux内核的[/proc说明](https://docs.kernel.org/filesystems/proc.html)和[cgroup v2说明](https://docs.kernel.org/admin-guide/cgroup-v2.html)。wchan是内核等待位置，不能替代用户栈；0或缺失不能排除阻塞。stat/schedstat的零值也不证明没有资源等待。cgroup内存信息按字段名解释，不依赖顺序。观察有开销，不能仅凭工具结果把停顿唯一归因于资源限额或厂商程序。

## 实际检查

[结果索引](test-results-thread-observer.json)：隔离新建sleep进程的Linux19项通过，覆盖默认无写、显式marker、来源/计划/进程/exe/cgroup错误拒绝、时长及输入上限、既有输出/符号链接保护、缺失指标未知、正常采样、只终止观察器及目标退出不重绑。测试sleep实例已确认消失，原控制值保持。正常2秒3样本采集CPU约0.00443秒；这是工具资格，不是完整业务性能验收。

在既有隔离R78业务进程上，各做一次15秒只读观察，两角色各16样本、47线程/样本、无截断或线程race，采样CPU分别约0.07033/0.07567秒，单次采集最大约5.07/5.47毫秒。HIS完整观察进程CPU0.233968秒、外层15.335931秒，包含启动及结束；DBS完整进程CPU未保存，明确未知，不能拿采样CPU代替。实际PSI三文件均不可用，保留unknown。原业务/Agent实例和限额保持；后续七天原报告仍pending，不将这些短观察作为无干扰或长期接受。

首次双角色采集器在DBS完成后，因错误假定HIS程序在/opt/hisdbs/bin/hisdbs，未找到监听者而失败；HIS观察器尚未启动，失败保留。实测路径为/opt/dbs/bin/hisdbs。新的HIS单独采集按所属cgroup内8090监听socket唯一归属选取，再绑定PID/start/exe；完成了HIS观察，没有重跑已完成DBS观察。原始样本分别以[DBS gzip](test-evidence/thread-observer-dbs.json.gz)、[HISDBS gzip](test-evidence/thread-observer-hisdbs.json.gz)归档，解压后的逐字节SHA256及压缩文件摘要均在结果索引中。

## 执行示例

以下是隔离测试工具命令，不是生产安装步骤。先准备新计划并固定SHA256；计划由本轮绑定的目标身份生成，不能沿用历史PID：

```sh
python3 tests/vendor-thread-observer.py --plan /var/tmp/crg-test-tools/observer-plan.json --plan-sha256 <SHA256>
CRG_THREAD_OBSERVER=authorized-disposable-loopback-only python3 tests/vendor-thread-observer.py --plan /var/tmp/crg-test-tools/observer-plan.json --plan-sha256 <SHA256> --execute
```

输出为同一个全新JSON文件；首样本产生一条observing事件，结束再打印终态。未完成、被打断或缺字段的观察不能解释为通过。工具资格检查的实际入口：

```sh
CRG_THREAD_OBSERVER_SELFTEST=authorized-disposable-test-node-only python3 tests/vendor-thread-observer-checks.py --work-dir /var/tmp/crg-thread-checks-<唯一编号>
```

[下一轮完整压力诊断设计](plan-business-pressure-thread-diagnostics.md)要求保留原32项/两角色各600秒和全部门槛，再将API事件与线程/资源样本按时间关联；本轮没有重跑压力，也没有关闭R142、R120或历史延迟问题。新的[七天固定进程观察](test-progress-seven-day-during-thread-observation.json)继续分别计时，稳定1.0尚未接受或发布。
