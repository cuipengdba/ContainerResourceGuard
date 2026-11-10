# 版本化候选DBS/HISDBS真实路径复验

[冻结计划](test-plan-versioned-candidate-business.json)针对真实v1.0.0候选AMD64程序dbc48aa5。先接受[四格原生88项](testing-versioned-candidate-native.md)及[自身三场景1800秒开销](testing-versioned-candidate-overhead.md)，才能创建业务Pod；运行器已启动但停留在前置等待；[固定观察](test-progress-versioned-candidate-start.json)确认业务namespace尚未创建、0项业务检查，不能写成业务已开始或通过。使用测试节点原镜像、原start.sh、原PG参数、原CCG只读挂载与真实容器路径，各自独立Agent。宿主背板、私有DCS、凭据和64MiB合成数据均为新隔离夹具，先断开测试Pod外部网络再释放启动门禁。

DBS/HISDBS按原manual64预算顺序执行：CPU7.2核、内存20001980416B、双向64MiB/s及各4096IOPS，其他5项实际原值保持。启动总300秒、缓存45秒及各实际600秒SQL和/test测量不变；零错误、最大5秒、p95桶上界1秒、样本覆盖98%，原备份/同步内容10项及独立恢复、原生主库不重启、数据完整性和每日0600/v2日志均需通过。开始前每格内存保留28GiB，运行中8GiB/磁盘20GiB门槛不变。

该轮不会重用开发版3a1ce7db的600秒时长，也不能将manual64结果解释成默认20%或自动30%的业务性能。只验证现有5.14/AMD64/单设备环境，不代表ARM厂商业务、两块物理盘、24h+24h、七天或稳定发布。现有长测及正式候选不修改。
