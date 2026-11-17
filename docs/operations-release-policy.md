# 当前运维、问题分级与补丁发布规则

> 2026-11-17用户明确要求现在正式发布v1.0.0，本次按此要求提前发布；该发布决策优先于下文此前“未达全部稳定条件仅预发布”的项目流程。已发布版本身份与完整稳定性资格分别记录，未完成的限制24h、新七天、老化后和真实回退不改为通过，52任务/18原完成声明保持，测试继续。[正式版说明](releases/v1.0.0.md)与[决策记录](release-decision-v1.0.0.json)。以下保留历史时点及原验收条件。

> 2026-11-17用户明确要求现在正式发布v1.0.0，本次按此要求提前发布；该发布决策优先于下文此前“未达全部稳定条件仅预发布”的项目流程。已发布版本身份与完整稳定性资格分别记录，未完成的限制24h、新七天、老化后和真实回退不改为通过，52任务/18原完成声明保持，测试继续。[正式版说明](releases/v1.0.0.md)与[决策记录](release-decision-v1.0.0.json)。以下保留历史时点及原验收条件。

当前公开下载仍为preview.5；最终v1.0.0候选尚待长期验收和剩余发布检查。稳定发布与生产部署分别记录。[准确已测环境](tested-environment-matrix.md)只覆盖列出的内核、运行时、权限、架构和存储组合；ARM原生控制不替代厂商ARM业务，兄弟分区不等于独立物理多盘。

## 每容器检查和恢复

每个容器独立配置、Agent、状态和日志。以下命令只在目标容器内部执行；路径以实际部署记录为准。

~~~sh
/opt/crg/crg build-info
/opt/crg/crg doctor --config /etc/crg/config.json --format human
/opt/crg/crg preflight --config /etc/crg/config.json --format human
/opt/crg/crg status --config /etc/crg/config.json --format human
~~~

核对可信二进制摘要、架构/源码、自身cgroup、容量来源、设备/profile身份、权限及祖先限制。preflight只检查打开入口，不写资源值；实际启用后核对逐项actual、generation、accepted_hash、原因码和原业务。writer_lock_held只表示协调锁持有，不证明数据库健康；快照无变化时约5分钟才写一次，mtime不是每秒心跳。

CPU、内存、IO三个独立百分比各默认20。memory.high是回收/节流目标，允许超出，既有memory.max仍有效，不能保证绝无OOM。IO百分比只按真实标定BPS；IOPS仅显式manual管理，外部IOPS保持。自动选择最大合格本地文件系统并复用当前设备基准，不复用其他机器能力。v1/混合/未知跳过，权限不足降级；业务继续不等于资源限制成功。

合法配置支持原子文件替换后的自动重载，或显式执行：

~~~sh
/opt/crg/crg reload --config /etc/crg/config.json
/opt/crg/crg status --config /etc/crg/config.json --format human
~~~

requested仅表示持久送达，继续核对request_id、accepted/rejected、generation与各项实际值。等价配置不必增加代次，坏配置保留完整上一策略。运行中不得变更state_dir；manual无profile转percent的首次IO准备边界见[配置](configuration.md)。业务不等待CRG初始化、标定或日志写入。

需要解除CRG管理时由当前匹配版本执行：

~~~sh
/opt/crg/crg disable --config /etc/crg/config.json
/opt/crg/crg status --config /etc/crg/config.json --format human
~~~

仅退出Agent不会撤销内核限额。disable先保存停用标记，再等待锁并恢复仍拥有的值。外部冲突、只读、坏journal或内核IO阻塞可造成未完整恢复；保留标记和错误，核对逐项读回，不删除journal或批量写max。永久停用须关闭原supervisor的可选入口；重建后的新cgroup不继承旧身份停用标记。原业务和缓存启动/退出逻辑保持独立。

升级先核对包SHA256、BUILD.json的source_revision/package_revision及build-info，使旧Agent和辅助重试循环静默，保留配置/profile/journal、日志与supervisor备份，按[逐容器维护](upgrade-preview4-preview5.zh.md)和[安装回退](installation.md)原子替换程序。不要截断运行中的二进制。先验收一份受控部署，再分别更新其他容器。旧收据与当前状态不匹配必须拒绝自动回退；建立当前quiescent状态的反向收据或用当前程序disable，不能覆盖journal强迫旧版读取未知格式。退回preview.4还会恢复旧四轴IO百分比语义。

## 问题分级

等级决定处置顺序，不承诺尚未建立的服务响应时限。记录时间、版本/摘要、当前容器身份、脱敏触发配置、预期/实际、处理与复测；根据实际影响调整等级。

| 等级 | 触发和处置 | 必须留下的证据 |
| --- | --- | --- |
| P0 | 写到其他容器/父级、敏感信息泄露、辅助故障改变原业务启动/退出。暂停新增部署，逐容器关闭可选入口并受控停用，优先保护业务。 | 目标/身份/原值/实际值、业务时间线、受控恢复及仅自身所有权复测；涉及隐私先走既有私有渠道。 |
| P1 | 项目持续错值/冲突、有效配置失效、错误标定，或限制伴随SQL/API/备份恢复不达原标准。保留现场，按明确预算受控回退或停用。 | 同一程序和实例的内核回读、journal、容量/设备来源、外部约束、原业务指标及失败；不自动加配额或改数据库参数绕过。 |
| P2 | 日志/指标/诊断或文档缺陷，控制与原业务可独立确认正常。保留降级输出，修复可选功能并复查。 | stderr/原因码、控制和业务证明、输出恢复结果；预期只读/v1跳过仍须检查部署目标是否满足。 |

缺统计或不能确认的值标unknown，不能填0冒充正常。默认20%完整业务失败继续保留，manual参考通过不能覆盖。

## 补丁发布和证据归档

1. 用Markdown记录复现、原任务编号、准确程序/源码/配置/环境和失败原件；冻结修复范围、格式/配置语义、升级与恢复边界。三资源、一对一、v2才写、辅助故障放行业务、high/BPS、30日/1GB日志及外部限额保护逐项检查。
2. 对准确源码做必要unit/race/边界验证，并验证实际将发布的ELF及受影响DBS/HISDBS原路径。备份、同步、独立恢复、长期/老化问题沿用对应原协议，不用占位PID1或短时长代替。不为通过而提高预算、放宽SLA或删失败。
3. 程序重建、重链接或修订改变后重新固定ELF身份，不借用其他ELF运行时间。固定工具链、两架构摘要、SBOM和构建来源，分开记录source_revision与package_revision。包校验失败拒绝安装。
4. 逐项审核原门槛、未知项、失败、回退和支持范围。未达稳定条件只发布明确限制的prerelease；新补丁用新版本，不移动旧标签、覆盖同名附件或改原结果。当前没有最近两个已发布minor，预发布不冒充该历史。
5. 发布后下载实际附件核对摘要，公布变更、配置、升级/回退、支持矩阵和证据入口。代码合入、发布、生产部署验收分别记录；先一份受控部署验收原SQL/API/备份/同步/独立恢复，再逐容器扩展，失败停止扩展。

每次运行使用唯一run_id、目录和namespace，记录计划/执行器/程序SHA256、原生起止与实际秒数、样本、SQL/API错误/延迟覆盖、引擎阶段、内核读回和退出码。清理独立核对PID/start、namespace UID和父叶cgroup。观察超时不代表进程终止，不据此重启或重新计时。

准确原件保存UTF-8、长度、逐文件摘要及解释范围；压缩证据、失败、未执行项和旧计划一起保留，修订追加新收据并链接旧结果。公开仓库、发行包或Issue不含完整Pod/env/postgres配置、凭据、私钥、服务器地址或业务SQL/数据。

~~~sh
/opt/crg/crg diagnose --config /etc/crg/config.json --output /private-maintenance/crg-diagnostic.json
~~~

先准备容器内私有维护目录。diagnose是最多64KiB的有限白名单诊断，不自动上传，公开前仍要复核。state-backup及supervisor备份含私有原值/身份，与脱敏诊断分开保存。源码提交和原件摘要共同追溯来源。

产品日文件一天一个，今天及前29个日历日保留，超过1,000,000,000字节先删最旧；只剩当天超限时清理当天旧内容，不生成同日分片。此规则只管理CRG日文件，不是发布/测试证据的保存期限；已归档失败与发布身份不能由日志清理删掉。持久日志需独立持久目录，Pod可写层/emptyDir销毁后不能恢复旧文件。

本规则交付操作与发布流程，不将尚未发生的稳定发布、生产变更、灾难恢复或长期验收称为已执行。[当前交付](release-readiness-current.md)和[逐项任务证据](current-52-task-audit.md)保留实际状态。
