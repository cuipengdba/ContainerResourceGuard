# 1.0 兼容契约草案

2026-11-10，next/compatibility-contract，P10.1/P10.4 开发草案。本文固定计划中的兼容规则，不表示 1.0 已发布，也不代替至少七天目标业务验收。当前公开稳定发布事实以 GitHub Releases 为准；开发分支不能当作已发布次版本。

## 配置与资源语义

1. 保留最小 `{"percent":20}`。省略 resource_mode 等价 percent，省略 mode 等价 enforce；resource_mode 的 percent/manual 与 mode 的 enforce/observe 分别表示预算方式和写入方式。配置严格拒绝未知字段、重复键、null/无效必要值、超过1MiB或64层输入，不通过忽略拼写错误改变预算。
2. percent 是每个容器相对当前宿主 CPU 总量、内存总量及显式设备标定基准的独立上限。IO 不是磁盘固定物理总量，缓存命中、网络和数据库共享内存不等同磁盘 IO。不得悄悄把宿主口径换成上层 cgroup 百分比，或为通过测试自动增大预算；更严格的祖先/运行时/cpuset 仍限制实际可用量。无法确认宿主总量时跳过相应百分比维度并报告，不能编造总量。
3. manual 省略维度表示不接管该维度；不把缺省项目设成 max。移除已经接管的维度按所有权规则恢复真实原值。manual 与 percent 同时出现即拒绝，包含显式 percent:0。IO 绝对值需 data_paths 发现当前设备，不在业务启动时测速。
4. pids_max、cpu_weight、io_weight、memory_high、memory_swap_max 均为可选，省略不改；权重不等于硬上限或竞争时固定比例。memory_stable_seconds 默认为0，保留既有瞬时安全检查；新窗口 opt-in。metrics/events 默认关闭，不引入服务端口。
5. 新版本可增加可选字段，但旧读取器严格拒绝新字段。降级前必须显式移除旧版不支持的配置，并检查原值日志能否读取；“配置保持最小形式兼容”不等于旧程序支持所有新能力。既有字段的含义、单位、默认值及安全检查不得在补丁版悄悄改变。

配置目前为隐式第一代格式，没有可随意填写的 schema_version 字段；增加显式版本要经过兼容设计。ConfigMap 的合法原子符号链接配置读取继续支持，私有状态文件保持更严格的普通文件/不跟随链接规则。

## CLI 与 JSON

原命令名和成功输出结构保留；version 仍输出纯版本行，build-info 保留 version/revision/os/arch，并追加 go_version、锁协议、可读版本和 writer_controls。JSON 字段顺序、空白和 detail/error 的自然语言不是接口。消费者须忽略新增输出字段，对未知状态/原因保守显示，不能据未知值认定已生效或允许恢复。输入配置和安全状态仍严格验证，不能套用输出宽容规则。

| 输出/退出 | 契约 |
|---|---|
| 未输出资源结果的命令失败 | stdout 一个 JSON：schema=crg-command-error-v1、state=degraded、reason_code、error、business_action=none；退出1 |
| restore/disable 返回未完整恢复 | 保留完整资源结果，stdout 增加 reason_code=restore_incomplete，退出1；不再追加第二份 JSON |
| run 的某维度被内核拒绝/延后/冲突 | 逐项 state/reason_code 解释；进程可继续协调，不能仅靠进程存活或退出0断言限额全部生效 |
| reload 请求已落盘 | requested 只代表已请求；需核对会话/配置代次和逐项实际结果，不能认定已全部应用 |
| status | 最后快照结合 snapshot_age_seconds、writer_lock_held 和 actual 判断；旧身份快照拒绝 |
| quiesce | 保留内核限额与 journal，暂停当前写入者；不等价 disable/restore |
| diagnose | 有界白名单快照，私有 journal/state-backup/安装 receipt 不属于脱敏诊断包 |

命令级原因按操作阶段与类型化原因生成，不解析英文错误文本：

- 参数与读取：usage_invalid、config_invalid、discovery_failed、profile_operation_failed、calibration_failed、status_unavailable、preflight_failed、plan_failed、diagnostic_failed。
- 运行与维护：runtime_failed、reload_request_failed、quiesce_failed、disable_failed、enable_failed、restore_failed、restore_incomplete、upgrade_check_failed、state_backup_failed、binary_maintenance_failed、supervisor_maintenance_failed。
- 可识别的具体原因优先：lock_unavailable、permission_denied、filesystem_read_only、storage_full、cancelled、operation_timed_out；没有类型化原因时保留操作类别，不猜测根因。command_failed 作为无上下文的兼容后备。

human 格式供人阅读，不作为机器接口；普通 CLI 可能含私有路径/错误信息，分享时优先使用 diagnose。控制项原因和有界事件各自按已知白名单管理，命令失败不会被补写成未发生的资源变更。

## journal、profile 与恢复所有权

journal v1 和 IO profile v1/v2 为当前读取范围；未知版本、无效条目、未知控制项或损坏文件拒绝继续写。journal 的版本相同也不自动意味着旧程序理解新版控制项，须结合 build-info.writer_controls 和实际条目逐一核对。字段/控制语义有破坏性变动时升级格式并提供显式兼容预检、私有备份、迁移预览和失败回退；没有迁移器时明确拒绝，不删除日志“重建”，不以 max 代替原值。

自身身份绑定 boot ID、真实 cgroup 路径及 inode/device，并要求自身和容器 PID1 同组。容器/Pod ID 不在配置中；新实例重新发现，不能对新目标恢复旧日志。每容器独立 state_dir、写入者、持久启动入口和可写安装目录。重复 Agent 由 cgroup inode 与已有 state lock 协调，不接受跨容器目标。锁协议变更必须显式不兼容，不以新 state_dir 绕过旧写入者。

只恢复本 Agent 记录且仍持有的值；外部修改保留并报告，pending 意图依据持久状态与实际值协调。observe 不自动撤销先前限额。程序退出、崩溃或无权限不改变这些内核事实；业务可继续启动不代表已生效的过低限额不会降低性能。

受控二进制回退不导入旧 journal，要求原身份/配置/日志兼容且未发生不允许的漂移。supervisor 卸载要求 disable 与 journal 已清空，持久移除入口才能跨新容器永久停用；旧身份 disable 标记不永久禁用新实例。扩展属性、挂载点或未知启动模板的部署变更另按已审阅源文件处理。

## 版本与维护政策

1.0 计划验证最近两个**已发布次版本**到候选版的升级与兼容范围内回退；尚未发布的开发分支短测不能关闭该项。目前已有开发版本二进制往返证据，真实发布版本对照仍待执行。补丁版保持配置含义、所有权/锁/恢复协议和已有输出字段；安全修复可收紧此前错误接受的输入，须在变更日志写清触发条件及迁移步骤。

弃用先在文档和变更日志说明替代方式、影响及至少一个已发布次版本的过渡；1.x 不删除已承诺的必要字段或改变默认资源语义，破坏性变更另列大版本。不能因旧配置在新版本被拒绝而静默启用另一预算。格式迁移、支持矩阵扩展和默认安全门槛变更单独评审与留证。

每次发布归档完整源码 SHA、工具链/包摘要、SBOM/来源证明、真实测试二进制、通过与失败、适用环境和未测项目。已构建 arm64 不代表真机验收；当前实际 Linux5.14/amd64/cgroupv2/单设备证据不能扩大为全内核/架构/存储支持。v1 写入不在当前范围。生产部署与 GitHub 发布分别记录，测试节点授权不扩展为改业务节点。

支持问题按影响处理：目标越界、原值/日志丢失、辅助故障阻断业务或未经校验写入属于阻断发布；功能维度降级、外部冲突和资源预算不足须如实解释；性能结论绑定实际镜像、预算、负载、就绪与采样条件。厂商专用备份/同步接口和正式 SLA 未核验时，不以引擎短测替代。

本草案及命令原因仍需 Linux/真实 CLI 回归。至少七天业务周期、最近两个已发布次版本升级、支持边界复核与最终维护手册都完成后，才可关闭 P10 并发布1.0。
