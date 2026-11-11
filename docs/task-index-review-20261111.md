# 任务索引范围核对：2026-11-11

这是本轮新增证据和过时状态的核对记录，不是稳定1.0的最终52项完成审计。[原始十版任务](roadmap.md)和[52项索引](current-task-registry.json)的ID、定义、定义来源、completion_claim逐项保持；此前scope_note已写入对应条目的scope_note_history，含原索引SHA256，避免覆盖历史。全部52项仍未宣称整体完成。

| 本轮核对项 | 现在可证实的范围 | 仍需完成或独立核对 |
|---|---|---|
| P02.1–P02.4 | 原fc2 observe的[两角色86400秒终态](testing-baseline24h-final.md)已通过冻结原生协议，4周期已接受；原协调/原生负载入口退出，业务Pods/数据保留。修正旧索引22h/native-pending文字 | 7项exec超过5秒诊断保留；固定d6的[正式阶段13/14前置](test-results-formal-stage-after-baseline.json)不是已运行enforce。其他夹具自然结束后须重核实时门禁，再做24h enforce和完整对照 |
| P03.1–P03.5 | 精确发布ELF dbc新增[15项工程重载协议](testing-versioned-candidate-reload.md)，默认只读/缺标记拒绝、同一实例退出和全部自有scope清理已核对 | 原厂商启动和原生负载下重载、每步三资源数值独立回读、危险内存延后、原子/符号链接/缺失/半写入、并发分支分别核对；占位PID1不代替业务 |
| P09.1–P09.2 | [preview.2实际发布](test-results-preview2-publication.json)，同一受测程序，八项附件实际下载并核对。source和package_revision分开 | 新tag构建证明未宣称；既有来源、离线拒绝和维护范围保持原边界 |
| P09.3 | 当前d370源码[两个目标各10分钟fuzz](testing-d370-parser-fuzz-windows.md)，21,680,191次执行、exit0、源码合同不变 | 源码解析器崩溃/挂起覆盖不代替所有非法输入拒绝、长文件系统故障、真实强杀/掉电或Linux ELF运行 |
| P10.2 | [两个七天来源的固定活体观察](test-progress-seven-day-two-lineage-20261111.json)分别核对同一PID/start_ticks/entry及worker；版本化与开发ELF不串用 | 仍running/native-pending，实际604800秒、28周期、采样完整性及真实老化后置未接受；原生报告每300秒落盘，163–165秒年龄在该周期内；后续[针对性采样](test-progress-seven-day-freshness-20261111.json)确认两来源各角色宿主采样最大间隔约60.47/60.24秒，无超过120秒缺口，原生进程身份保持，尚不是终态 |

其余条目在本轮索引中保持原scope_note，不表示已完成最终复核。原默认20%业务失败、自动30%持续性能未接受、171独立现场同一程序出现的DBS OOM因果未定等记录均保留。暂缺ARM厂商业务和独立物理多块设备环境；不以单设备/分区或原生ARM控制器结果替代。

原P01.6/P04.5/P05.5等扩展资源任务受用户R29暂缓，新交付仍只默认控制CPU、内存、IO；历史兼容和原值恢复保留。当前三独立百分比各默认20、v1/混合/未知跳过、纯v2安全校验、每日30日/1GB日志、每容器一对一及辅助失败不阻断原业务均保持，未引入Operator或产品跨容器管理。

本轮延续到稳定1.0的原目标；preview.2是即时工程交付，长期、真实老化后置、正式等时对照、最近两个已发布次版本维护、最终支持矩阵和全部阻断缺陷复核继续。此次没有重链接程序、替换既有发布资产或改动业务环境。
