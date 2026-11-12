# 当前交付与后续验收

[memory.high与长会话诊断](testing-long-perf-session.md)：内存百分比只对应memory.high，不新设memory.max，保留外部硬上限。自有600秒/120请求及56项检查通过，前后perf映射3244032字节一致；MaxRSS仅为序列化前观测值。完整压力调用包装九个合成用例通过，真实工厂和厂商600秒/11区间尚未接入；旧失败与52项原条件保留，稳定1.0未接受，产品及preview.4附件未变。

[有限perf缓冲与阶段计时](testing-bounded-perf-timing.md)：原44项加六项实际小块突发/预算/清理共50项通过；每CPU固定32页、含元数据的实测总映射3244032字节、16MiB预算，真实满环仍明确incomplete。本轮厂商诊断30项全部通过，仍仅为120秒诊断资格。原230/63项事件丢失失败保留，产品及preview.4附件未变，完整600秒/默认20%/压力/长期及52项原条件继续开放。

[厂商小块写入新阶段诊断](testing-iomap-vendor-stages.md)：两角色原启动链各120秒SQL/API零错误，但新增40-hook采集流分别丢失230/63项，计划30/记录18/通过16，原失败及未执行检查保留；64个原实例、180个自有BPF对象、namespace和cgroup独立清理已核对。条件阶段四个合成用例及大原件无损传输另行验证，不代表厂商资格通过。下一步开发有限突发容量并先按原44项及满环故障验证；产品及preview.4附件不变，52项、原完整业务/压力/长期条件继续开放。

[小块日志写入分阶段计时](testing-iomap-stage-timing.md)：原五类路径及35项范围继续保留，八个额外阶段以普通文件1至4096字节write门控，已有页/新页与大块排除边界实际44项通过；三个原失败、静态内核调用核对和观察超时全部归档。新阶段尚未用于厂商副本，不宣称业务修复或稳定1.0；产品源码及preview.4附件未变，52项和原长期门槛保持。

[分阶段函数计时](testing-paired-wait-timing.md)：独立35项通过，五种实际函数进入/返回计时及自有真实锁等待已验证，三个准备/校验失败全部保留。新厂商副本计划26项、实际26项/26通过，API错误dbs:0,hisdbs:0；这只是120秒诊断，不清除原默认20%/完整压力失败，不宣称因果修复或稳定验收。产品源码及preview.4附件未变，52项和长期门槛保持。

[普通文件与回写元数据复验](testing-writeback-metadata.md)：首次四页缓冲63次输出失败原件保留；调整自有采集缓冲后独立28项通过，实际1930/69条回写事件。新厂商副本DBS120秒0错，HISDBS一次4秒API超时，22项实际19项/18通过，整体失败。已保存失败前关联及同日志inode的folio事件，匹配Alma内核源码核对字段；不能将7.655秒write全归于单条等待或宣称根因/业务修复。副本和采集对象独立清理，产品包/旧失败/52任务及长期门槛保持。

[内核端点诊断](testing-event-time-kernel-endpoint.md)：独立快速连接21项/32端口通过；新厂商副本原22项实际19项/18通过，DBS两次API超时，整体失败。已捕捉同一服务线程原日志write持续12.149秒及随后迟到accept/recv/send时序；完整会话50个端口可见不抵消原4秒超时，不宣称内核等待根因或业务修复。HISDBS本轮120秒0错；全部副本/采集对象独立清理。五种回写静态格式只读发现，待独立资格后定位等待路径；产品发布/原失败/52任务及长期门槛保持。

[厂商副本直接BPF诊断](testing-direct-bpf-vendor.md)：两角色各120秒/SQL和API0错，18项范围/持有连接/恢复清理通过，但正常快速连接端口关联0/50，仍未资格、未证明原API超时原因。16字段BTF只读布局可用，内核端点采集尚未实现；原完整600秒、七天及全部52条件保持。

当前可更新包是[memory.high版v1.0.0-preview.4](releases/v1.0.0-preview.4.md)，详见[配置](configuration.md)、[内存策略和旧max迁移](memory-reclaim-policy.md)及[公开preview.3→4更新手册](upgrade-preview3-preview4.zh.md)。当前仍为工程预览；[正式验收入口](current-acceptance.md)和[52项任务注册表](current-task-registry.json)优先于下方历史快照。

只控制CPU/内存/IO，分别设置百分比、缺省各20%；内存回收目标使用high，原外部硬上限不放宽。一容器一Agent、自动自身ID发现、v1跳过/v2校验、自动IO标定及每日30天/1GB日志保留。最新完整high压力两角色各600秒/SQL零错误但API各一次超时，尚未通过；[连接与日志写诊断](testing-perf-metadata.md)资格未通过，不能以实验工具替代业务验收。

[直接BPF诊断自建探针14项](testing-direct-bpf-host.md)已通过，取得精确回环连接与同线程阻塞写关联，并验证输出失败标记和独立清理；厂商模式及API超时归因尚未验证，不能替代业务验收。

后续继续完成原十版及全部52任务，包括默认百分比、真实压力/受限IO、各自七天及老化后置、正式24h对照、实际已发布次版本迁移和未测硬件条件；不补造历史版本或改变门槛。以下保留旧计划原文及来源时点。

# 历史下一版计划：v0.1.0-rc.3-preview.1

当前工程预览候选实现用户最新R27/R29/R30，两套候选的Linux检查和38项隔离实测已通过，见[测试证据](testing-three-percent-cgroup-logs.md)。本次发布main的工程预览包，组合开发线不作为发布物。正式RC3、稳定版及1.0的业务与长期验收未完成，不因本工程预览标签提前关闭。

## 交付内容

1. 只接管CPU、内存、IO：cpu_percent/memory_percent/io_percent，各自默认20%，配置可为{}。
2. 设置前检测cgroup：v1跳过且正常退出，混合/无法确认也不写；v2校验自身身份、权限、上层限额及内存下调安全后逐项执行。
3. 默认自动选最大合格本地磁盘文件系统、首次后台标定/稳定设备缓存复用；容器或Pod重启重新发现自身ID。
4. 每日日志、30天/总1GB滚动清理，版本判断/实际结果/失败原因可见，日志无权限/满盘仅降级stderr。
5. 严格一容器一Agent，资源与原缓存辅助程序/原业务独立启动，业务不等待辅助程序；缺权限不阻断原业务。

[配置说明](independent-percentages.md)、[日志规则](logging.md)、[接入方案](integration.md)、[需求](requirements.md)、[任务](tasks.md)。使用新配置前核对二进制版本，正式RC2不识别三个新字段。

本预览不改现有业务部署；使用独立配置/状态/日志。若以前跑过八项开发候选，先使用旧候选disable恢复其额外限额后再切换；本版不擅自重置原有外部控制。

深入功能继续在next/compatibility-contract开发，包括安全热重载、诊断/指标、升级/回退及兼容性验证。尚未全部发布，不把开发分支中的额外功能当成本预览支持范围。原预览AMD64/ARM64资产现已在[实际Linux6.8/7.0四格原生控制器88项通过](testing-released-cgroup-ci.md)；后续源码CI另记，ARM厂商业务、物理多设备、分区映射与长期DBS/HISDBS业务验收仍未完成。

## 下载与配置

[GitHub预览发布及下载](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v0.1.0-rc.3-preview.1)。选择对应架构tar.gz及SHA256SUMS，按[安装说明](installation.md)核对。此发布仍为prerelease；两架构原资产有上述占位容器控制器实测，ARM厂商业务尚未验收。

```json
{"cpu_percent":30,"memory_percent":40,"io_percent":25}
```

未写的一项独立默认20；无新配置时也默认三项20%。进程命令为`crg run --config /etc/crg/config.json`。cgroup版本日志事件为`cgroup_detected`，查看每天的`/var/log/crg/crg-YYYY-MM-DD.log`或容器stderr；每个容器分别运行。

第12轮最新三资源程序四格真实路径业务验收已结束：24项通过，各格完整600秒、SQL/API零错误及10项引擎内容通过，夹具清理确认；仅为预先声明的手动64MiB/s预算。第13轮在线升级/回退已终止：首次安装失败，后续回退及600秒未完成；24h+24h和至少7天仍待完整实测。见[按程序摘要归档的结果](testing-three-resource-business-matrix.md)。

第13轮DBS/HISDBS首次安装均拒绝，旧预览缺少锁/日志协议广告，安装文件摘要保持、recovery为空，夹具清理；保留失败及原始输出未留存的证据限制，不绕过协议保护。见[维护失败与诊断](testing-three-resource-online-maintenance.md)。

第14轮最新三资源程序×DBS/HISDBS的40场景、216项辅助故障检查通过，全部夹具清理；独立30%配置，只证明辅助隔离，未追认自动30%持续业务性能或第13轮维护。见[新源码完整故障矩阵](testing-three-resource-fault-matrix.md)。

第16轮默认空配置首格main/DBS完整600秒但SQL10次/API57次错误，未通过；Pod清理命令失败使其余三格未执行，终态namespace已移除。保留实际20%限额、失败与诊断，见[默认配置结果](testing-three-resource-default20-business.md)。

第17轮真实路径备份/新Pod ID冷重建四格、8次启动、88项检查通过，数据/独立逻辑恢复库/一对一身份/日志追加及新容器原值恢复核对，全部夹具清理；仅为手动64MiB/s预算。见[冷重建结果](testing-three-resource-cold-rebuild.md)。

第18轮默认20%剩余三格补测结束：18项启动/控制/日志通过，三格业务组合均失败；main/HIS有完整失败原生结果，两个组合格仅有未完成快照，不计600秒通过。清理确认，连同第16轮四格均未通过，见[补测结果](testing-three-resource-default20-supplement.md)。

发布后工程进展：旧observe到已声明候选的[首次接入/旧参考入口恢复四格68项通过](testing-observe-first-adoption.md)；后续源码在原生AMD64/ARM64的[独占dm/loop控制器四格88项通过](testing-native-cgroup-dm-loop.md)。两项均有精确来源和范围，不替代本预览ARM64资产、默认20%业务或长期条件。
