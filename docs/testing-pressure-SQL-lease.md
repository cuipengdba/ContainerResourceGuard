# 压力辅助进程的SQL等待续租

第四轮完整压力测试里，[DBS原失败](test-results-memory-high-pressure-v4.json)为真实SQL/API错误2/5与释放命令BrokenPipe。源代码显示同步PG身份SQL检查期间存在心跳空档，可能超过原辅助的10秒租约；该轮辅助终态stdout丢失，不能回填为已证明的退出原因，更不能把原超时算作驱动修正后已经解决。

[新模块](../tests/vendor-pressure-sql-lease.py)只用于测试驱动：PG身份SQL仍用原30秒subprocess超时，只在一个新线程执行该原调用；主线程独占压力管道并串行发送/接收原ping，期间继续检查宿主余量、控制值、进程及OOM事件。SQL不重试，异常对象保持；SQL与心跳同时失败时保留SQL异常。31秒仅为观察SQL完成的检查点，回调仍有自己的时限，不宣称所有内核调用都能严格有界。模块不发业务信号、不写cgroup、不延长native/SLA。

测试节点上用原未改辅助进程做[9项真实检查](test-results-pressure-SQL-lease.json)：不续租保留真实10.001秒SIGALRM释放原因/退出1；续租同一进程跨过15.016秒、59次ping并在EOF正常零分配释放；SQL和心跳错误优先级、原真实子进程超时及立即返回均通过。全程辅助分配0字节，没有使用业务数据库或写cgroup。两个辅助PID、runner及检查进程经独立观察不存在。此项是宿主测试驱动的生命周期资格，不是厂商业务或压力负载通过。

[冻结计划](test-plan-pressure-SQL-lease.json)、[精确全部源码](test-evidence/pressure-SQL-lease-frozen.json.gz)和[检查源](../tests/vendor-pressure-sql-lease-checks.py)归档。实际厂商管道/高压调用将在[第五轮完整压力](testing-memory-high-pressure.md)验证；原配额、租约10/寿命240、原32项及600秒门槛保持，四轮旧失败与原52项不关闭。
