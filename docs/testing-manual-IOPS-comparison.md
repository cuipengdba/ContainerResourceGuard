# DBS/HISDBS 手动模式 IOPS 对照诊断

状态：启动前冻结、原生节点预检查通过，尚未运行。此项定位业务启动/重建失败；不改变产品默认策略，不代替原百分比20/30矩阵或稳定版验收。

用户已确认内存百分比使用memory.high；preview.4继续保留外部memory.max。上次[实际等待诊断](diagnosis-PG-rebuild-fsync.md)采样到PostgreSQL在自己的45字节PID文件fsync等待XFS回写，整组同时存在较多待回写页和低IOPS限额。尚未通过对照证明唯一原因。

[冻结计划](test-plan-manual-IOPS-comparison.json)使用现有手动模式，四组依次为DBS four、DBS bps、HISDBS bps、HISDBS four，每组独立namespace、独立数据目录、每业务容器一个Agent；组间只在前组原进程、namespace及登记父叶全部实际消失后继续。两角色使用相反组序，仍不是随机/重复/独占试验，时间、宿主其他负载和缓存差异需要保留为局限。

两组固定CPU4.8核、memory.high=13334654976B、读带宽12554471B/s、写带宽7746597B/s。four另外指定读IOPS27、写IOPS11；bps省略这两项，保留运行时原有IOPS设置。本次每次gate前必须实际验证io.max原为空，不能放宽继承的外部限制。数值来自上轮准确保存的三次标定中位数的20%，计划绑定原profile摘要，测试前不重新标定或提高带宽。手动模式不生成/要求profile，开始即限制；这与首次自动标定期间的默认启动存在差异。

每组仍按原真实镜像、原DBS/HISDBS业务/PG/cache/挂载路径运行，保留三次启动的36项检查、SQL/API/managed及cache共300秒门槛、cache就绪后最多45秒、64MiB数据/128标记、逻辑备份、重建ID/原journal归档、独立库恢复、日志跨ID追加、disable恢复原值。实际原厂liveness为ls、delay300/period120/timeout300/failure3/success1，按准确PodUID独立观察；不是SQL/API门槛的延期。原120秒Pod删除/30秒父叶消失也不放宽。此处144项属于新诊断，不能补算原百分比矩阵的144项。

[驱动差异](https://github.com/cuipengdba/ContainerResourceGuard/blob/ed47cad3ab07599f712b7e5102fdfba7e280bb58/tests/manual-IOPS-comparison-frozen/driver-changes.diff)、[冻结驱动](https://github.com/cuipengdba/ContainerResourceGuard/blob/ed47cad3ab07599f712b7e5102fdfba7e280bb58/tests/manual-IOPS-comparison-frozen/startup-matrix-driver.py)、[协调器](https://github.com/cuipengdba/ContainerResourceGuard/blob/ed47cad3ab07599f712b7e5102fdfba7e280bb58/tests/manual-IOPS-comparison-frozen/runner.py)及[8项结构预检查](https://github.com/cuipengdba/ContainerResourceGuard/blob/ed47cad3ab07599f712b7e5102fdfba7e280bb58/tests/manual-IOPS-comparison-frozen/offline-qualification.json)可审阅。8项只验证对照配置、保留的检查/时限/实际原值核对及业务逻辑差异边界，不能说业务已通过。本地冻结前的三次准备脚本错误和修正已在资格报告保留，期间没有上传或创建测试容器。[Linux原生预检查](test-results-manual-IOPS-native-preflight.json)核对准确上传摘要、二进制build-info、源码可编译、上一诊断准确failed终态及48登记实例/namespace/父叶清理；同时原长期任务相同三个进程与第五次内容备份仍在，不重启它。

程序Go代码、已发布附件、默认百分比四轴换算及原52项状态保持原样。默认IO是否改成只限制带宽，仍等待用户明确选择；本手动对照不是替用户决定。原矩阵失败、物理备份、24h+24h独占、七天、硬件和正式升级门槛继续开放。
