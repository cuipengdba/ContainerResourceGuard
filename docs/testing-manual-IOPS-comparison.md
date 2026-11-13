# DBS/HISDBS 手动模式 IOPS 对照诊断

最新用户选择已覆盖旧R10：下一版io_percent仅限制标定读写BPS，IOPS留手动；既有外部IOPS保留，旧自有限额按身份/journal安全迁移。实现与新增回归见[IO带宽策略](io-bandwidth-policy.md)，当前待准确Linux/原生/真机验证；preview.4及旧结果保持，原52项不补算完成。

状态：四组已终结，整体失败；bps两组各36项通过，four两组原300秒启动失败。默认策略保持，见新增实际终态。此项定位业务启动/重建失败；不改变产品默认策略，不代替原百分比20/30矩阵或稳定版验收。

用户已确认内存百分比使用memory.high；preview.4继续保留外部memory.max。上次[实际等待诊断](diagnosis-PG-rebuild-fsync.md)采样到PostgreSQL在自己的45字节PID文件fsync等待XFS回写，整组同时存在较多待回写页和低IOPS限额。尚未通过对照证明唯一原因。

[冻结计划](test-plan-manual-IOPS-comparison.json)使用现有手动模式，四组依次为DBS four、DBS bps、HISDBS bps、HISDBS four，每组独立namespace、独立数据目录、每业务容器一个Agent；组间只在前组原进程、namespace及登记父叶全部实际消失后继续。两角色使用相反组序，仍不是随机/重复/独占试验，时间、宿主其他负载和缓存差异需要保留为局限。

两组固定CPU4.8核、memory.high=13334654976B、读带宽12554471B/s、写带宽7746597B/s。four另外指定读IOPS27、写IOPS11；bps省略这两项，保留运行时原有IOPS设置。本次每次gate前必须实际验证io.max原为空，不能放宽继承的外部限制。数值来自上轮准确保存的三次标定中位数的20%，计划绑定原profile摘要，测试前不重新标定或提高带宽。手动模式不生成/要求profile，开始即限制；这与首次自动标定期间的默认启动存在差异。

每组仍按原真实镜像、原DBS/HISDBS业务/PG/cache/挂载路径运行，保留三次启动的36项检查、SQL/API/managed及cache共300秒门槛、cache就绪后最多45秒、64MiB数据/128标记、逻辑备份、重建ID/原journal归档、独立库恢复、日志跨ID追加、disable恢复原值。实际原厂liveness为ls、delay300/period120/timeout300/failure3/success1，按准确PodUID独立观察；不是SQL/API门槛的延期。原120秒Pod删除/30秒父叶消失也不放宽。此处144项属于新诊断，不能补算原百分比矩阵的144项。

[驱动差异](https://github.com/cuipengdba/ContainerResourceGuard/blob/ed47cad3ab07599f712b7e5102fdfba7e280bb58/tests/manual-IOPS-comparison-frozen/driver-changes.diff)、[冻结驱动](https://github.com/cuipengdba/ContainerResourceGuard/blob/ed47cad3ab07599f712b7e5102fdfba7e280bb58/tests/manual-IOPS-comparison-frozen/startup-matrix-driver.py)、[协调器](https://github.com/cuipengdba/ContainerResourceGuard/blob/ed47cad3ab07599f712b7e5102fdfba7e280bb58/tests/manual-IOPS-comparison-frozen/runner.py)及[8项结构预检查](https://github.com/cuipengdba/ContainerResourceGuard/blob/ed47cad3ab07599f712b7e5102fdfba7e280bb58/tests/manual-IOPS-comparison-frozen/offline-qualification.json)可审阅。8项只验证对照配置、保留的检查/时限/实际原值核对及业务逻辑差异边界，不能说业务已通过。本地冻结前的三次准备脚本错误和修正已在资格报告保留，期间没有上传或创建测试容器。[Linux原生预检查](test-results-manual-IOPS-native-preflight.json)核对准确上传摘要、二进制build-info、源码可编译、上一诊断准确failed终态及48登记实例/namespace/父叶清理；同时原长期任务相同三个进程与第五次内容备份仍在，不重启它。

程序Go代码、已发布附件、默认百分比四轴换算及原52项状态保持原样。默认IO是否改成只限制带宽，仍等待用户明确选择；本手动对照不是替用户决定。原矩阵失败、物理备份、24h+24h独占、七天、硬件和正式升级门槛继续开放。

[手动IOPS对照](testing-manual-IOPS-comparison.md)已按冻结方案唯一启动；[首个只读快照](test-start-manual-IOPS-comparison.json)确认准确runner/DBS四轴驱动及资源值，启动约44秒、PG尚未就绪、已记录业务检查0项。其余三组尚未运行，不宣称终态/对照因果/默认策略变更；原矩阵失败和52项仍保持。


## 冻结对照的实际终态

[手动IOPS四组对照](testing-manual-IOPS-comparison.md)已终结：仅带宽组DBS/HISDBS各36项通过、共六次启动85～114秒就绪；低IOPS四轴两组各仅记录1项原liveness成功，均未达原300秒业务启动标准，HISDBS另有原120秒Pod删除超时。共74/144项阳性、70项未执行，不能称整套通过；后续独立确认四命名空间、八组leaf/parent及219个登记进程实例清理。[完整结果](test-results-manual-IOPS-comparison.json)和[18文件443558字节精确归档](test-evidence-manual-IOPS-comparison.json.gz)保留。默认IO策略不变，原52项仍开放。[源码集成草稿及工程CI](source-integration-status.md)另列，工程通过不替代业务/稳定发布。

| 组别 | 原300秒启动 | 实际阳性检查/计划 | 三次启动就绪秒 |
| --- | --- | --- | --- |
| DBS four，riops27/wiops11 | 初次失败 | 1/36 | 未就绪，后两次未执行 |
| DBS bps，不额外设置IOPS | 三次通过 | 36/36 | 109.51 / 85.22 / 85.09 |
| HISDBS bps，不额外设置IOPS | 三次通过 | 36/36 | 114.32 / 88.15 / 84.77 |
| HISDBS four，riops27/wiops11 | 初次失败；Pod删除120秒也失败 | 1/36 | 未就绪，后两次未执行 |

两组bps都覆盖原启动链、缓存原只读挂载与enforce、原真实kubelet探针、SQL/API、64MiB载荷/128标记、逻辑备份和独立数据库恢复、两次Pod重建后的新ID/journal、日志追加及disable完整原值还原。四轴的单项阳性仅为原UID的实际liveness成功，不表示业务已就绪；后续清理成功也不撤销原删除超时。

各组CPU4.8核、memory.high13334654976字节、rbps12554471、wbps7746597均相同，外部memory.max21474836480保持；只使用既有手动配置的可选IOPS差异。四轴27/11，bps不额外设置且开测前原io.max必须为空。手动模式不运行标定，不能冒充默认百分比/首次自动标定通过。全部原36项/300秒业务/45秒缓存/720秒独立探针/120秒删除/30秒cgroup时限保持，未调大。

单节点、相反引擎顺序、没有重复随机试验的结果支持低IOPS导致启动敏感的判断，不能证明唯一因果。默认百分比仍按原四轴换算；待用户答复IO口径后才处理默认语义及迁移，再用新源码重新验收，不能用此诊断替代原百分比144项、物理备份、正式迁移或长期验收。

首个终态清理只读检查过早断言失败；没有重启测试或延长原时限。后续在同一报告摘要下独立查证runner/四驱动的PID/start、四命名空间、八组leaf/parent及219个进程实例均消失；原失败保持。首个启动快照仍是历史0项记录，以上终态为后续新增证据。
