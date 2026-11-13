# 当前交付与后续验收

[PSI兼容重测实际启动](test-start-high-percent-startup-psi-compatible.json)：节点2026-11-13T10:40:13.454202+00:00确认同一runner/DBS20驱动仍活跃，原任务身份及前轮148实例/四namespace/父叶清理门槛通过。首个DBS空配置20%在62.508秒业务就绪且managed，7项已记录检查均通过；CPU4.8核、high13334654976B、自动IO读15131041/写8097125Bps及10/15IOPS，外部20GiB max保持。14次启动采样，PSI明确不可用；原实际探针仍observing，后续重建/其余三格未到，不能按12次/144项或业务终态接受。首轮失败、默认业务失败、原52项及稳定条件保持。

[20%/30%启动矩阵首轮终态与PSI兼容重测](testing-high-percent-startup-psi-compatible.md)：原四格首次业务采样因节点无io.pressure中止，144项只记录4项独立原kubelet探针成功，140项/8次依赖重建未执行，整体failed。18份113346字节原件及148个登记实例/四namespace/父叶清理确认。修正为明确PSI不可用，保持必需IO/CPU/内存计数、所有额度和原业务/探针门槛，38项离线工具检查通过，新编号启动前冻结，尚未运行。high576越过24h原生SQL/API0错，第五次内容备份完成但DBS exec诊断API6.43s超原5s，保留原结果；默认业务、原52项及稳定条件不变。

[20%/30%三状态启动矩阵](testing-high-percent-startup-matrix.md)已启动前冻结：四格12次启动/144项预期，保留三项独立百分比与memory.high、首次自动标定、原300秒SQL/API门槛和实际原Kubernetes liveness；旧克隆仅显式ls的证据边界已更正。21项离线工具检查通过，尚未上传或启动，业务不计通过。待原high576同一进程的第五次备份完成且清理后顺序运行；不重启长期任务。默认980完整业务失败、原52项及稳定条件不变。

[原52项当前范围与证据复核](requirements-evidence-review.md)已逐项归档：用户后续三资源/high语义覆盖旧pids/权重/swap及新max下调要求，保留原文、恢复保护与全部未满足验收。表中证据入口不表示整项通过，原52项完成声明未改；默认业务失败、正式24h/七天、硬件与真实发布迁移仍分别处理。

[空配置默认20%原业务终态](testing-default20-memory-high-business.md)：原16项记录16、通过14；两角色启动/单Agent/缓存/三项high-only控制/日志各7项通过，但物理备份均触发原300秒超时，各仅完成1/10内容检查。DBS原生被中断且SQL24/API5错误，HIS原生只有旧running快照，不能按600秒零错接受。22份270144字节原件及66个登记进程实例、两个namespace和自有父叶cgroup清理独立确认；保留engine/exec清理错误。低标定IOPS与超时并存尚无单因素因果结论，不提高配额或延长超时。preview.4产品/附件不变，默认业务与稳定1.0未接受。

[空配置20%实际启动快照](test-start-default20-memory-high-business.json)：节点2026-11-13T07:51:58.042161+00:00确认同一协调器/DBS驱动PID及start仍活跃，DBS在66.292秒就绪且managed，7项启动/默认换算/单Agent/缓存/high-only journal/v2日志检查通过。实际CPU4.8核、high13334654976B，自动选中/etc/crg所在XFS253:0，IO基准20%为读9831622/写4251266B/s、读12/写6IOPS。原生尚在preparing，零计数不代表600秒零错，HISDBS未开始；当前不作业务或稳定接受。见[冻结计划](testing-default20-memory-high-business.md)。

[memory.high空配置默认20%计划](testing-default20-memory-high-business.md)已冻结：准确preview.4、原DBS/HISDBS镜像及真实路径，首次自动选盘/标定，三项各20%，外部硬上限保持；两独立namespace顺序运行原600秒/内容/覆盖标准，预期16项，未执行不计通过。原native/campaign/engine字节不变，凭据不导出，旧默认与960失败/52项/长期/稳定条件保持。

[子进程句柄修复完整终态](testing-full960-native-child-fixed.md)：两角色各600秒/11区间，BPF与私有通道原工厂及独立30项通过；原业务子进程退出1/0准确保留。DBS出现5次SQL超时且覆盖不足，原32项只记录29项通过、三项未执行，整体业务失败；HIS SQL/API0错。首个窗口WALWrite、后四BufferContent，原PG诊断另有5次采集错误，不宣称因果或全面诊断完整。35份49549278字节原件及59进程/96对象清理确认，历史失败/52项/默认20%/长期与稳定条件保持，memory.high产品及preview.4附件不变。

[原业务子进程句柄修复](testing-native-child-lifecycle.md)：宿主真实14个子进程/15用例及原工厂17项通过，退出后清空/替换worker不再误判；原启动异常、结果、非零退出与故障继续性保持。新隔离完整960任务通过全部预检并开始DBS，终态未到，业务/诊断尚未接受。950的原工厂失败保留；memory.high产品及preview.4附件不变，原52项与长期/稳定条件继续。

[字节码/导出修复完整复测](testing-full950-bytecode-export-fixed.md)：独立22项通过，包含原镜像Python2/Python3真实缓存负例、匹配命令禁用缓存、正常/读端故障和19项有界导出。原标准32项记录32、通过32；独立30/30，业务接受=True、诊断接受=False。正式清单35份48493981字节原件，历史930/831失败与原52项保留。memory.high产品/preview.4附件不变，默认20%及长期/稳定条件独立继续。

[memory.high完整私有通道/准入联调](testing-full930-private-admission.md)：原标准32项记录32、通过32；独立检查28/30，业务接受=True、诊断接受=False。保持core/worker和全部业务标准，实际私有FIFO原件与原始边界保留，35份48324339字节完整归档。只写memory.high的preview.4附件不变，历史失败、原52项和长期/稳定条件保持。

[准入状态故障与新候选600秒](testing-bpf-admission-faults-long.md)：同一910Go/ELF完成注入故障17项、并发参考600秒及洪泛13项；原始错误/丢失不隐藏，917夹具删除参数失败保留，实际OS线程号复用未验收。三轮24注册进程/480对象独立消失，内存high产品未改。完整厂商FIFO联调、原52项/历史失败、长期与稳定条件保持。

[调用准入与停止排空](testing-bpf-admission-drain.md)：自有五组18项及Go顶层14项通过，原始边界记录和incomplete保留，一秒超时明确失败；906不可达指令加载失败原件保留，修正只改指令生成器及重建ELF。两轮14个注册进程/248对象独立消失。实际TID复用、容量/深度故障、新候选600秒/开销及厂商联调尚未验收；原52项、历史失败、长期与稳定条件保持，已发布内存百分比仍只写memory.high。

[BPF边界对照](testing-bpf-pair-boundaries.md)：自有四组/13项完成，延后目标map启用解决半挂接窗口；启动前在途与停止时在途仍明确incomplete。首轮跨页计数夹具失败保留，采集器/探针/严格配对未因重试改变；两轮12进程/225对象独立消失。仅部分顺序修复，完整准入/排空和厂商600秒联调未验收，原52项/历史失败/长期/稳定条件及memory.high产品保持。

[接收端自有600秒与内存交付复核](testing-private-fifo-receiver-long600.md)：882七项通过，121条显式合成记录/14047字节完整，接收父进程CPU占单核约0.252%，真实线程/FD及身份清理确认；无HTTP/DB/Pod/BPF或全Agent开销声明。精确preview.4六项本地内存策略回归通过，公开八附件元数据及tag不变。memory.high选择、外部硬上限、原52项、完整联调/BPF边界/长期与稳定条件保留。

[私有接收端与工厂接线](testing-private-fifo-receiver-factory.md)：867真实接收资格15项通过，保留17工厂用例、新18接收及8通道故障用例，两个原镜像各3次postgres启动；873工厂启动路径9项通过，采集器/K8s身份为模拟而FIFO/线程/FD真实。生产程序/preview.4不变，完整600秒联调、接收端长期CPU及BPF边界仍待验收；原52项和全部失败保留。

[原镜像启动/FIFO资格](testing-native-startup-private-fifo.md)：最终19项通过，保留原9传输/19参数并新增13通道用例；两镜像各4次真实postgres启动及自有HTTP，缺失/无读取端/写满均不阻断，stdout标志未改。843、848、850三轮失败与完整源码原件保留。仅测试诊断器资格，完整工厂接收端及BPF启动边界待完成，产品/preview.4及原52项完成声明不变。用户内存选择保持memory.high，不新增memory.max。

[修复预检后的完整压力](testing-fixed-null-full-pressure831.md)：两角色原600秒/11区间、32项业务检查本轮全部通过，SQL/API零错误；历史超时未解释。真实诊断仍失败：DBS就绪前3个函数返回缺失引发12条配对问题，两角色均0/121请求注解。25项独立诊断检查17项通过；33份41839701字节原件及57进程/90对象独立清理归档。下一步独立复现目标激活边界和Python2启动自动加载。memory.high产品及preview.4附件不变，默认20%/长期/原52项及稳定1.0条件保持。

[完整压力诊断接入](testing-full-pressure-diagnostic-integration.md)：内存继续只下发memory.high。DBS/HISDBS原600秒和11区间均完成，计划32项，实际记录29项均通过；DBS业务异常导致最后三项未执行，API错误原样保留。辅助诊断在null字段计数时失败，未挂接BPF，原业务仍继续；原件回放及修复候选17个用例通过，修复版完整真机诊断未验收。报告输出Linux5项、原镜像传输注解9项通过，完整原件已按长度和摘要下载归档。52项原条件、全部旧失败与稳定1.0未接受状态保留，产品及preview.4附件未变。

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
