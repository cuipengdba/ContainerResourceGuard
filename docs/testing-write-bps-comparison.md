# 写带宽 A/B/A 隔离诊断

实际终态为[三组均失败、未形成有效对照](testing-write-bps-comparison-failure.md)；下文启动快照按原时点保留，后续见[独立v2](testing-write-bps-comparison-v2.md)。

[冻结计划](test-plan-write-bps-comparison.json)、[执行器](https://github.com/cuipengdba/ContainerResourceGuard/blob/dbe5ecee372c28eed59118aee30339471dfbc7f2/tests/vendor-write-bps-comparison.py)、[资格记录](test-results-write-bps-comparison-qualification.json)及[启动快照](test-start-write-bps-comparison.json)用于定位R235超时。当前只是已启动的DBS因果诊断，**不代表原32项/DBS与HISDBS各600秒/百分比验收通过**。产品二进制和每容器一份Agent保持，测试协调器不属于产品。

固定A1→B→A2三组：A为37470104 B/s写带宽，B为67108864 B/s（64 MiB/s），A2重复A。只在原第一策略对应区间改变wbps；原第二策略、启动manual64策略均不变。读BPS/读写IOPS/CPU/内存、11个重载区间与代数、30%→20%实际内存压力/延迟/释放自动重试、64MiB负载、600秒、备份/同步/独立恢复及所有原时限相同。两组都明确用manual配置数值，不伪造实测IO profile；百分比模式的原验收另行保留。源码中的每个适配点及出现次数入计划，离线检查证明适配点以外的原业务方法字节未变；这不是实际业务通过证明。

源为原DBS真机路径的完整目录，含以前失败的schema、备份及历史，没有删掉数据以降低压力。只读清单确认PostgreSQL clean shut down、无postmaster.pid、无Pod挂载、程序/配置/pg_control摘要保持。XFS支持reflink，操作前剩余约192 GB，要求至少64GiB可用盘及28GiB主机可用内存。先用cp --reflink=always --archive --one-file-system生成全部三份副本，再启动首组，防止后组继承前组写入。三份共25338项的全树元数据摘要均df104d1af0ce211dbd4b942274b4f93b67ee75f8f76abaf104236f417eb91146；所有常规文件与源inode不同，关键文件内容SHA核对一致。未对全树每个文件重新做完整内容SHA，不作该声明。完整副本及失败现场保留。

每组使用独立命名空间、deny-all及启动前网络隔离，原厂镜像/原启动链/一个Agent和缓存；同一run_id在三份独立数据中产生相同负载。通过原Agent的配置路径设置，测试器不直接写cgroup。沿用已资格化的原生诊断/失败最终落盘和线程观察器，不向业务/PG/Agent发诊断信号。只有证明上一组自己的Pod、namespace、cgroup已退出且副本配置/profile恢复才进入下一组；失败业务结果仍保留，未证明清理则停止，禁止重启来覆盖。

最初Windows生成计划的两个路径含反斜杠，被Linux只读门禁拒绝，未创建测试根或负载；[原计划](test-evidence/writebps261-initial-windows-plan.json)和实际diff保留。改为明确POSIX路径后，实际8项只读/缺授权/计划篡改检查通过。一次启动前校验又发现传输JSON与节点缩进JSON的原始摘要不同，校验拒绝发生在写runner/启动负载前；按节点实际序列化核对后才启动原定一次任务，不是观察超时后重启。

首个实际快照为2026-11-11T15:47:47Z：runner4086220/start135194745、worker4086221/start135194748同实例存活，三份副本已冻结，A1 testing-dbs，只有2项启动检查；尚无600秒终态，也没有B或A2结果。精确工具SHA66c7e45b14c8a4fbea6301848d781851a58617a9cc65a3915416321e2f70781f，计划SHAdc8d8f60b0713817ca47e3d0db55c1a34347900341008c308423553c6611dee1。

对照的解释有边界：新inode冷副本与R235长期复用的源inode不同；顺序组与原长期任务共享同一物理后端，缓存/写回状态不宣称相同。至少需要A重现、B改善及A重复才支持带宽因素，不能只挑B的通过结果。即使该模式支持，也不能修改原验收额度后宣布原测试通过。原R235失败、全部52任务、七天及24h+24h要求继续；ARM厂商与独立物理多设备仍待可用环境。
