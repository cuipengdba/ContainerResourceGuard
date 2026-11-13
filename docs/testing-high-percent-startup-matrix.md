# memory.high：20%/30%原厂商启动矩阵

状态：启动前冻结，尚未上传或启动，144项预期检查均不计通过。原默认20%完整物理备份失败继续保留，本矩阵只补充原P01.2的配置/三种启动状态/原健康探针联合证据，不替代P01.1/P04完整业务或稳定1.0验收。

## 固定产品和输入

- 产品：`v1.0.0-preview.4`，源`180c86ad7986a76526a41575cc1c176d5da98a9c`；AMD64程序SHA256 `6088721cd4846f95b3b71c82f9884e1909797a199d962b50519c9e013de98b4e`，发布附件、正文与tag不变。
- [完整计划](test-plan-high-percent-startup-matrix.json) SHA256 `f431ff2866e6648d2afa385294b72665484769d8dd883223dca1c00ca50c456b`；驱动SHA256 `7fbb3645c068053ef3fc48a46eb95e406e8bfdd36b9d36ca859549c6807ffb81`；[冻结源码](../tests/high-percent-startup-frozen-v1/README.md)。
- 使用原DBS/HISDBS镜像和真实挂载/原start/PG/缓存。容器单独运行自己的Agent；20%配置准确为`{}`，30%只写三个独立百分比。CPU以宿主在线核数换算；内存只写`memory.high`，原20GiB `memory.max`、pids/权重/swap均保留；IO以首次自动选择最大合格文件系统的三次测量中位基准换算，不代表物理峰值。

## 四格、三种状态与原门槛

按DBS20、HISDBS20、DBS30、HISDBS30顺序，四个独立namespace，前格精确Pod UID、cgroup父叶和登记PID/start全部确认消失才进下一格。每格三次启动：首次空数据初始化；保留原解包/数据目录重建；完成schema逻辑备份后再重建。原start可能再次解包，不宣称无IO重启或宿主缓存全冷。重建后必须为新Pod/容器/cgroup身份，journal隔离旧身份，同一配置/精确自动IO profile/64MiB表及128行标记保持，并做独立数据库逻辑恢复。

每次SQL/API/managed必须在原300秒内；缓存45秒且也须落在同一300秒内；每项负载/逻辑备份/恢复操作仍300秒。记录IO统计、IO压力、CPU/内存事件与就绪耗时，不提高配额、IO基准或修改PG配置以追求通过。每格36项，最多12次启动/144项；前置失败后的依赖项明确未执行。5400秒只是每格外层隔离收容上限，不改变各业务门槛。

只读复核原部署发现：原DBS和HISDBS仅有`livenessProbe`，命令`ls`、initialDelay300/period120/timeout300/failure3/success1，无startup/readinessProbe。此前克隆只执行了显式`ls`检查，没有创建真实Kubernetes探针；不把旧44项改称原探针联合通过。新矩阵准确拷贝这些探针参数；仍以restartPolicy Never收容，不声称完整生产重启策略等价。

原节点实际提供kubelet `/metrics/probes`，指标`prober_probe_total`带Pod UID。新观察器只保存当前格/本次启动精确UID/namespace/pod/container/Liveness的计数，至少一次successful且没有记录到非成功计数才接受；其窗口为业务gate起720秒，与300秒SQL/API门槛分别判定。此窗口用于原delay300/period120探针观测，绝不延长业务就绪时间。其他容器计数不会归档。参见[Kubernetes指标定义](https://kubernetes.io/docs/reference/instrumentation/metrics/)；本节点实际HELP仍为ALPHA，记录原样，不套用当前文档成熟度。

## 长期任务保护与证据边界

启动前必须只读确认原high576的同一runner/worker/campaign PID+start+entry和作业摘要仍活跃，并等待指定`2026111257604`备份offset≥86400、两角色各10项且cleanup=true、原内容阶段成功。最多等待10800秒，原任务终止/身份改变/指定备份失败则不创建新fixture，不重启原任务。该备份native-pending只说明内容阶段完成，不等于七天604800秒/28次备份/aged通过。

节点2026-11-13 09:50:21UTC的只读快照：原任务仍测量，两角色native约85882/85879秒，SQL/API各0错误、各一个准确Agent、控制和journal匹配；仅4次实际完成备份，未到七天。其余长期fixture仍在共享单盘，不能把本矩阵作为正式独占24h验收或性能因果对照。

[准备证据](test-evidence-high-percent-startup-preparation.json.gz)含原部署探针白名单观察、实际端点能力、精确只读查询源程序与21项离线工具检查；离线检查不等于真机通过。终态仅导出白名单report、日志、profile等，单文件32MiB/总256MiB/64文件/1MiB分块并比对摘要；不导出Pod/env/PG凭据、业务数据目录。

## 保留的未接受项

[默认20%完整业务终态](testing-default20-memory-high-business.md)的两次物理备份300秒超时、DBS原生中断/错误及HIS缺最终原生快照不变。本矩阵采用schema逻辑备份及独立数据库恢复，不能覆盖原物理备份/同步/独立物理恢复要求。`memory.high`允许短时超过目标，也不能保证无OOM；本测试未强制触达high，不作内存压力结论。[原52项复核](requirements-evidence-review.md)、正式24h、当前high七天、硬件覆盖、真实发布迁移和稳定1.0条件均独立保留。
