# preview.5 手动参考预算：完整业务终态

本轮通过。使用同一已发布preview.5程序/ced461705ebc27315a59aefe463f9b4af47130a3，在原DBS/HISDBS镜像、启动链及真实路径下顺序运行。预算与失败默认20%之前已记录的手动计划一致：CPU7.2核、memory.high20001980416B、读写各64MiB/s、可选IOPS各4096；外部20GiB硬上限及另外四项控制值保持。没有自动标定或profile。

| 角色 | 阳性/记录检查 | native实际秒数 | SQL次数/错误 | API次数/错误 | 引擎内容检查数 | 受控就绪秒数 |
| --- | --- | --- | --- | --- | --- | --- |
| DBS | 8/8 | 600.286 | 300/0 | 121/0 | 10 | 32.117 |
| HISDBS | 8/8 | 600.295 | 300/0 | 121/0 | 10 | 28.825 |

本轮共16项记录、16项通过、0项失败、0项未执行；完整业务接受值为true。每角色独立复核原native600秒、SQL/API零错误、最大5秒/p95桶上界1秒/98%计划覆盖、64MiB数据完整性、主库不重启、线程结束；十项物理备份/流同步/独立恢复内容及完整备份周期必须位于成功native窗口内。原启动300秒、缓存45秒、引擎300秒/停库30秒不变；原native/campaign/engine/optional-helper字节不变，没有增加额度、改PG设置、放宽时限或重试覆盖失败。

节点2026-11-13T18:51:05.324053+00:00的独立只读观察确认runner/两driver原PID/start实例消失、两个namespace及两组父叶cgroup消失，54个已登记进程实例全部消失。22份准确原件共217571字节，终态exit/index/coordinator/角色报告、完整source-map及逐项SHA/大小绑定；配置导出代替不应存在的自动profile，不采集私有Pod/env/数据库凭据。

这是独立手动模式预算验收，不把[默认20%完整业务16记录/14通过/2失败](testing-bandwidth-default20-full600-terminal.md)改判通过，也不能单独证明某一种资源的因果或跨负载性能。原业务fixture没有Kubelet liveness，[精确原探针三次启动组合](testing-bandwidth-current-combinations.md)是另一证据。共享节点不等于独占24h/七天、压力或硬件全面验收；原52项、正式升级和长期条件继续。稳定1.0仍未接受，发布附件/标签与程序未改。

[完整结果与独立复核](test-results-manual-reference-full600-terminal.json)、[全部准确原件](test-evidence-manual-reference-full600-terminal.json.gz)、[启动前冻结标准](testing-manual-reference-full600.md)。下一步[已发布preview.4到preview.5维护设计](testing-preview45-manual-maintenance-design.md)只完成输入绑定及设计，尚未冻结执行驱动、预检或启动，不能作升级通过证据。
