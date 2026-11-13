# 保留数据重建的 PostgreSQL 进程诊断

状态：[准确源CI通过](test-results-PG-rebuild-process-CI.json)，[已唯一启动](test-start-PG-rebuild-process.json)，原始观察时间及三个进程身份见记录；本轮已终态失败，实际卡点、原始记录和后续语义选择见[fsync诊断](diagnosis-PG-rebuild-fsync.md)。此项推进P01.2/P01.3实际业务失败定位，不改原52项或144项矩阵定义和失败结果。

[原矩阵终态](test-results-high-percent-startup-psi-compatible.json)为failed：DBS/HIS20首启通过、重建超原300秒，HIS原120秒删除也失败，30%未执行。[新增只读片段](test-evidence-PG-rebuild-startup-selected.json.gz)显示原厂程序已经执行pg_ctl start，随后报告PG startup fail且没有第二次PG启动日志。保留PID文件的数值启动时间位于本次重建门槛之后，不能仅凭残留文件将原因说成旧PID；HIS文件来自后续启动重试。未采集当时的内核等待栈，尚不能确定卡在IO、同步或其他阶段。

[新计划](test-plan-PG-rebuild-process.json)只运行一个DBS20诊断格，沿用准确preview.4原镜像、原真实挂载路径/业务启动/PG/cache程序、空配置20%、三状态36项原检查。驱动只有独立目录/namespace、测试环境标记、私有SQL schema编号更换，业务/缓存/操作/原探针时限及资源公式不变。首次仍自动选最大合格分区标定三次，重建复用该profile；不人工提高或重标定额度。该单格即使36项全过也不替代原四格144项、HIS/30%或物理备份/长期验收。

新加的独立宿主观察器仅在第二次启动读取该已声明PodUID/容器ID叶，核对init PID/startticks/cgroup/独立PID namespace；只对该叶的postgres和pg_ctl采集wchan、可读内核栈、数值syscall、io和少量status字段，以及标准FD的种类/pipe inode。前后核对PID启动时间和cgroup，拒绝其他进程或容器。不读取cmdline/env、进程内存或FD内容，不发送业务信号、不修改资源/数据库参数。最多180次×5秒、每次4个PG进程、输出8MiB，内核栈无权限明确不可用。

观察器等待第二次gate_epoch等身份字段齐备后采样，独立退出或失败会保留状态，不能说业务门槛已通过；业务驱动仍按原时限清理。新计划先要求上轮准确终态及107登记实例/四namespace/已创建父叶全部实际清理，再核对原high576相同三个进程和第五次内容备份已完成，未改长期任务。原24h+24h独占、七天及其他硬件条件仍开放。

[本地冻结来源和16项观察器检查](../tests/pg-rebuild-process-frozen/offline-qualification.json)、[原生Linux16项与准确上传摘要](test-results-PG-rebuild-process-native-preflight.json)、[观察器](../tests/pg-rebuild-process-frozen/pg-process-observer.py)、[驱动](../tests/pg-rebuild-process-frozen/startup-matrix-driver.py)及[协调器](../tests/pg-rebuild-process-frozen/runner.py)均在启动前归档。检查覆盖目标叶、拒绝父级/兄弟/错误Pod/非规范路径、等待状态/FD分类、非PG/外组排除、缺栈/超大字段明确不可用、采样中PID复用和迁组。Windows早期Path拼写夹具错误已在冻结资格报告注明，修正后本地/原生均16项通过；不计真实业务结果。

程序生产代码、preview.4发布附件及正在运行的长期Agent均保持原样；memory_percent仍写memory.high，外部memory.max保留。

[PG重建诊断已实际启动](test-start-PG-rebuild-process.json)：节点12:16UTC确认同一runner、只读观察器和DBS20驱动三者的PID/startticks/入口均在运行。上轮准确失败与107实例/四namespace实际清理、原长期任务同句柄第五备份门槛均通过；当前首次PG探针exit0，但仍未记录业务检查，观察器等第二次启动。两开发分支[完整CI及新增16项](test-results-PG-rebuild-process-CI.json)通过。第一次SSH启动请求中断后先证实无launch/日志/结果目录，再修正本地字符串编码后唯一启动；冻结源和计划未改。原业务失败及稳定条件保持。

[重建fsync诊断终态](diagnosis-PG-rebuild-fsync.md)已定位实际等待点：87次采样/114条PG记录均在XFS fsync写回等待，两次FD设备/inode核验确认第一进程同步的是自身45字节PID文件。写IO约9.99IOPS/0.763MiB/s，额度11IOPS且仍有约415MiB写回；低IOPS影响为强线索，尚无A/B因果结论。该格重建仍超原300秒，11项通过/25未执行，48登记实例/父叶/namespace实际清理，八份387429字节原件已归档。默认IO百分比改为只约束带宽还是继续四轴，等待用户选择；当前语义及原144项失败/52项定义/preview.4不变。
