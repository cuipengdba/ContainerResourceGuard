# preview.5 手动模式原完整业务验收

手动参考预算任务已唯一启动。节点2026-11-13 18:30:11 UTC快照：DBS在32.12秒受控就绪，7项启动检查通过；实际7.2核、memory.high20001980416B、读写64MiB/s及IOPS4096一致，无自动标定。native仍运行，HISDBS按顺序等待。[启动身份与只读原件](test-start-manual-reference-full600.json)归档；初始零计数不是600秒或物理备份同步验收，默认20%失败保持。


启动前冻结新任务`fc981713aa1d45833c161776bb005e874cb51fc8ac20117c5d1f26e2f0dd654d`、计划`7562087a52b9ddc44d81cbd91b6146ee27467e5aed534724343ca4ef49ce5e74`。准确产品ced4617及公开preview.5程序不变；本轮是独立手动模式验收。[默认20%完整业务的16记录/14通过/2失败](testing-bandwidth-default20-full600-terminal.md)保持，不能用本轮结果替代。

预算逐项等于此前[手动模式业务v2计划](test-plan-memory-high-business-v2.json)：CPU7.2核（cpu.max=720000 100000）、memory.high=20001980416B（约18.6GiB）、读写带宽各67108864B/s、读写IOPS各4096；外部memory.max=21474836480B由原fixture保留，CRG不新增硬上限。目录/opt/postgresql，仅本容器；manual不自动测速/profile。可选IOPS仅手动设置，不改百分比模式BPS-only默认。

使用原DBS/HISDBS镜像、supervisor、缓存程序、挂载及真实业务路径，各自新隔离fixture、回环DCS和断网namespace，DBS后HISDBS顺序运行。每角色7项启动/控制/单写者/日志检查和1项完整业务，共16项；保留原PG/API/managed300秒、缓存45秒、native600秒、零SQL/API错误、最大5秒、p95桶上界1秒、98%计划覆盖、16384行/64MiB、主库不重启、十项物理备份/同步/独立恢复，备份完整落在成功native窗口内；原引擎300秒/备用库停止30秒不变。原native/campaign/engine/optional-helper文件与原完整业务任务逐字节相同，适配仅模式/预算和新测试身份/输出，不加诊断负载。

15项结构/真机资格检查通过，尚未启动或接受业务终态。新驱动逆向适配可完整还原原默认20%驱动；预算与先前计划一致，全部原criteria保持。节点18:23:05 UTC核对前一默认20%终态及54个登记实例、两namespace/两组父叶消失，新namespace不存在；MemAvailable=38686449664B、磁盘空闲75127549952B，满足原28GiB/20GiB保留量。协调器创建新结果目录前再次执行同一清理硬门槛；不继承旧运行时间。

任一失败完整保留，不自动重试、增加额度、修改PG或放宽原时限。原业务fixture没有Kubelet liveness；精确原探针三次启动组合为[另一独立证据](testing-bandwidth-current-combinations.md)。共享节点不作独占24h/因果开销/高压/七天验收。旧preview.4通过结果不能计为新源码通过。原52项、正式升级与长期/硬件发布门槛继续，稳定1.0未接受。

[冻结计划](test-plan-manual-reference-full600.json)、[15项资格与真机预检](test-results-manual-reference-preflight.json)、[完整冻结工具](../tests/manual-reference-full600-frozen/README.md)。
