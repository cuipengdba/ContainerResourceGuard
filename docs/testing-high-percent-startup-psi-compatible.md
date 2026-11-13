# 20%/30%启动矩阵：可选PSI兼容重测

状态：已启动，尚未终态。[节点10:40:13UTC的准确启动快照](test-start-high-percent-startup-psi-compatible.json)确认首个DBS20空配置62.508秒managed，已记录7项且均通过；原实际探针observing，后续重建和三格未完成。预期12次/144项，不能按已全部通过接受。产品仍为准确preview.4，内存百分比只写memory.high，原外部memory.max保持。

## 首轮真实终态与原因

[首轮计划与终态](testing-high-percent-startup-matrix.md)绑定原作业`7fbb3645c068053ef3fc48a46eb95e406e8bfdd36b9d36ca859549c6807ffb81`，在四格首次启动时均发生`io.pressure` FileNotFoundError，整体failed。原144项只记录4项、通过4项，均为独立实际Kubernetes liveness；其余140项/8次依赖重建未执行，首次业务就绪、额度公式和数据恢复均未验证，不能说四格启动通过。

实际节点没有本cgroup io.pressure，宿主/proc/pressure/io也不存在，但io.stat/cpu.stat/memory.current存在。原因是新测试脚本把可选PSI当成必有文件，在首次业务采样前异常；不是本轮业务或资源参数失败结论。原件保持，18份113346字节完整下载并逐项校验，独立18项来源/结果检查，原runner/四驱动、四namespace/父叶及148个登记进程实例已确认消失。见[分析](test-results-high-percent-startup-first-attempt.json)与[逐字节证据](test-evidence-high-percent-startup-first-attempt.json.gz)。

## 精确修正与固定输入

新采样器仍要求io.stat、cpu.stat、memory.current；io.pressure存在则保存原文，缺失或无读权限则保存明确unavailable及原因，其他错误仍失败。不启用宿主PSI，不改内核参数，不把缺失转换成0压力。原始业务错误先保存，再独立观察原探针，避免等待探针时看不到根因。

同一preview.4源`180c86ad7986a76526a41575cc1c176d5da98a9c`，AMD64 SHA256 `6088721cd4846f95b3b71c82f9884e1909797a199d962b50519c9e013de98b4e`；[新计划](test-plan-high-percent-startup-psi-compatible.json) SHA256 `9d521f5615f4c72b69bfe7824962efc41bf8f1a385ff67126de389c0f05e5b7a`；新驱动SHA256 `d974b13ab1058277c0dcf08a29a5c7449d250a890582b8f72d1d3a32374d7408`；[冻结工具v2](../tests/high-percent-startup-frozen-v2/README.md)，原工具v1不修改。38项离线检查绑定最终源码，不能替代真机。

20%仍是准确空配置，30%只给三个独立百分比，DBS20/HIS20/DBS30/HIS30顺序分别首次初始化、保留解包数据重建、逻辑备份后重建，首次自动选最大合格文件系统标定并保留同一profile。CPU以宿主在线核数、high以MemTotal、IO以三次标定中位基准换算；保留原300秒SQL/API/managed、45秒缓存且同一300秒、每操作300秒、36项/格及相同数据量/恢复标准。原ls liveness delay300/period120/timeout300/failure3/success1及按本次Pod UID观察的720秒窗口不变，探针窗口不延长业务300秒。缺PSI只能支持IO计数和时序观察，不声称取得PSI压力数据。完整标准与限制继承[首轮文档](testing-high-percent-startup-matrix.md)。

## 清理、长期任务与保留边界

新轮先验证首轮相同失败终态、原report摘要、完整导出索引，以及runner/四驱动/四namespace/父叶和登记PID/start全部消失，再验证high576同一三进程/作业和指定第五次备份内容完成门槛。任何不一致不创建新fixture。每格之后继续严格独立清理核验，终态只用原有界白名单导出。

节点2026-11-13 10:25:20UTC：high576仍同一任务，两角色原生87983/87981秒，SQL/API各0错，单Agent、控制和journal匹配；实际5次内容阶段备份。第五次DBS独立exec诊断API max6.4315秒，原5秒标准为False，HIS为True；内容10项/cleanup和原生结果分别记录，不把诊断失败改成通过。仍未达到七天604800秒/28次备份/aged条件，也不是正式独占24h验收。

[默认20%完整物理备份失败](testing-default20-memory-high-business.md)、[原52项复核](requirements-evidence-review.md)、其他历史失败、正式24h、硬件覆盖、真实发布迁移及稳定1.0条件保留。此轮为隔离schema逻辑备份/独立数据库恢复，不能替代完整物理备份/同步/独立物理恢复；不新增memory.max、不承诺无OOM，不改发布包。

## 本轮终态（节点2026-11-13 11:36 UTC复查）

[独立分析](test-results-high-percent-startup-psi-compatible.json)和[十份准确原件](test-evidence-high-percent-startup-psi-compatible.json.gz)保留原冻结程序、job/plan摘要、终态索引、来源映射、各字节/SHA及只读观察。共246613字节，14项离线来源/结果复核通过，不能当业务检查数。

DBS20/HIS20首次分别62.508/69.325秒就绪，准确actual_controls和journal通过原宿主/三次中位数公式；last_controls只是循环较早采样，不替代门槛后的actual_controls。两次保留数据重建都未在原300秒SQL/API/managed门槛内就绪，旧原ls liveness成功不能代替SQL。HIS原120秒Pod删除又超时，协调器按原清理门槛停止，两格30%未创建。不存在四格通过或三次启动全部成功。

原144项只记录22项正向检查，另122项未执行；四次Pod启动只完成两次业务就绪，八次计划启动未执行，两个重建失败。后续只读观察确认同一runner及两驱动、登记107进程实例、四个已创建父叶和两namespace已消失；后续清理不抹掉原120秒失败。source-map中的六个缺失导出恰为未执行30%文件，不能说四格原件齐全。PG具体根因未建立，不改额度、业务参数、计时或冻结程序掩盖失败。
