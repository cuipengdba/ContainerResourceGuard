# preview.5默认20%原完整业务验收

本任务已唯一启动。节点17:37:37 UTC快照DBS7项启动检查通过、PG/API/受控就绪27.25/29.32/55.15秒；cpu.max480000/100000、memory.high13334654976，io.max读13256766B/s、写9044830B/s且IOPS均max。native初始running及零计数不是完整业务结果。HISDBS按顺序等待。[准确启动原件](test-start-bandwidth-default20-full600.json)。


启动前冻结新任务8b61d73a06c79b99b7fdca8bc2a460b925f87e00b8a6089f1b1a9a948d787a39、计划7fdee53072afaef21e54450894d015f84267f1720976f05f3b1a946262752851。产品为同一个已发布preview.5/ced4617程序。原四种[完整启动组合](testing-bandwidth-current-combinations.md)已有各36项通过；这不替代本轮物理备份同步和原生完整负载验收。

DBS/HISDBS按实际原镜像及原路径分别创建新私有测试背板、回环DCS和断网namespace，按顺序运行，各自空配置{}，各默认CPU/内存/IO20%、memory.high及自动最大合格文件系统三样本标定BPS-only。每角色原300秒PG/API/managed、45秒缓存、7项启动/控制/身份/日志及1项完整业务，共16项。原native600秒、SQL/API零错误、最大5秒、p95桶上界1秒、98%计划覆盖、64MiB数据、主库不重启、十项物理备份/同步/独立恢复，以及原生命周期清理门槛保持。备份必须完整落在成功native窗口内。原native/campaign/engine脚本字节不变，没有加入压力或BPF诊断。

15项结构及真机预检通过：完整业务驱动反向还原后除新身份/版本/已授权IO公式外逐字相等；全部原criteria相同。17:28:19节点确认1190的106登记实例、namespace与三组父叶已经消失，MemAvailable约35.98GiB、磁盘空闲约73.00GiB，满足原28GiB/20GiB克隆前保留量。先前1190退出后才允许本轮创建新结果目录，不继承其时间或数据。旧980的物理300秒失败、旧576端口占用与其它失败保持；失败不会加额度、放宽超时或自动重试。

本轮是原980业务对照fixture的BPS-only新来源验证，原fixture没有Kubelet liveness，不能将其视为包含原探针的生产等价；精确原探针已在单独三次启动组合中实际验证。共享节点也不能作为独占24h、因果开销或七天验收。

[冻结计划](test-plan-bandwidth-default20-full600.json)、[15项资格及native预检](test-results-bandwidth-full600-preflight.json)、[完整冻结工具](../tests/bandwidth-default20-full600-frozen/README.md)。此时尚未接受业务终态。原52项/正式迁移/长期及硬件门槛继续，稳定1.0未发布。[preview.5最新发布说明核对](test-results-preview5-full-startup-followup.json)保持八项附件及标签不变。
