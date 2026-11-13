# 当前验收入口

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

2026-11-12：[直接BPF诊断自建探针14项通过](testing-direct-bpf-host.md)，正常18事件有精确回环连接/同TID阻塞写关联，真实输出失败标记不完整，30个内核对象独立确认释放。尚未接入厂商副本或解决原API超时；当前仍使用memory.high版preview.4，所有原业务/长期/52项验收条件保持。

[最新第五轮high压力终态](testing-memory-high-pressure.md)：DBS实际600.289秒，HISDBS实际600.447秒；两者SQL错误0、API错误各1，均未中断且11个重载区间和10项引擎内容检查完成。整体失败、实际26/预定32；完整原件及独立清理归档，旧失败和全部稳定门槛保持。

[精确preview.4真实high压力终态](testing-memory-high-pressure.md)：DBS实际145.053秒后按原失败收尾，SQL/API错误2/5、9区间；HISDBS实际600.513秒，SQL/API错误0/0、11区间，角色状态short-acceptance-passed。两角色均观察到high下调和high事件，原20GiB硬上限保持；整体失败，完整请求/线程/PG/设备及独立清理归档，不能计稳定通过。

已发布[memory.high版preview.4](releases/v1.0.0-preview.4.md)，[八项公开下载校验](test-results-preview4-publication.json)。每容器分别更新，保留原配置/profile/state_dir/journal，核对旧硬限额恢复；源码构建使用发布标签。完整业务和长期门槛继续。

> 2026-11-12已选定的新内存语义：百分比及手动内存写memory.high，不新增memory.max；允许超目标，外部硬限额保留。旧硬限额仅凭同身份journal及仍持有的值恢复。下述旧版实现/测试保持历史来源，不能替代新策略验证。见[内存策略](memory-reclaim-policy.md)。

P06[当前组合候选Linux6.8两架构实际控制器44项通过](testing-linux6-current-integration.md)：原22项驱动/预算不变、同次attempt1，真实三资源/独立百分比/新ID/恢复/只读降级及独立夹具清理；主线源码未变沿用旧来源。本次不关闭ARM厂商业务、独立物理多设备、原32项双角色业务与长期/旧次版本迁移条件。

下方历史快照保留原观察时点。

[固定IO四臂449终态](test-results-agent-fixed-io-comparison-v3.json)：A1/B1/B2/A2的SQL,API错误依次为0,0/0,0/2,5/1,0；B2暂停Agent时仍实际600.294秒/SQL2/API5，原业务失败保留。独立结论为preplanned-association-not-observed，不作Agent因果或产品性能修复；30个原实例、四namespace和父叶cgroup独立清理，原来源和副本恢复。只读分析器修正业务失败出口无重复摘要的读取缺陷，旧源码/错误原件保留，3个真实臂及17个合成反例共20项复核通过。对照结构资格不等于原业务SLA通过；原32项/两角色/配额/门槛、52任务和长期条件保持。

下方旧快照仅对应原观察时点。

[固定IO后续449进展](test-progress-agent-fixed-io-comparison-v3.json)：A1/B1分别实际600.307/600.350秒，SQL/API均0、原十项引擎检查及每臂七个实例/namespace/父叶cgroup独立清理复核合格；2026-11-11T23:59:37Z原runner/worker和B2 Agent/watchdog存活。全四臂尚未完成，不计有效ABBA、原32项压力/两角色或稳定验收。新只读分析器按完整证据独立判定，两个真实臂复核及16个合成反例共18项通过；原两轮失败和严格资格保持。

[固定IO的Agent活动对照](testing-agent-fixed-io-comparison.md)保留两轮失败：首轮准备ValueError，修订A1实际600.165秒SQL/API错误5/1，SQL覆盖率97%低于98%，9次PG等待超过四目标而缺失；其余三臂未运行，结论inconclusive。九个原实例及四namespace/父叶cgroup独立确认清理。错误边界24项及含两类合成反例的离线26项通过；后续449源/计划冻结，15项只读门禁通过，实际A1运行中快照已归档。继续记录不合格性能/明确溢出只用于观察，严格四臂资格和原32项/两角色/稳定门槛不变。

[原七天进程快照](test-progress-seven-day-during-fixed-agent-comparison.json)：2026-11-11T23:40:13Z原R57约95185/95173秒、5周期，精确发布R78约81670/81668秒、4周期；原实例与SQL/API错误0保持，尚非实际604800秒及后置通过。

2026-11-12即时交付：[v1.0.0-preview.3](releases/v1.0.0-preview.3.md)，[八项公开下载校验](test-results-preview3-publication.json)。沿用受测程序并更新文档，稳定1.0及原验收条件继续；下方历史记录保留原时点。

[Agent活动生命周期工具资格](testing-agent-activity-qualification.md)已实际完成：宿主机27项、原DBS/HISDBS各16项/共32项通过，正常和异常恢复均为同一Agent；暂停期间实际八项控制值、SQL/API、原PG/缓存身份保持，原进程/watchdog/两Pod父叶cgroup及namespace独立确认清理。首轮root直接psql缺libpq.so.5的退出127失败原件保留，修订采用原postgres登录环境；没有改配额/SLA。此项仅短生命周期工具资格，四臂固定83/135 IOPS对照执行器和完整600秒测量尚未完成，不代替原32项压力/两角色业务或稳定条件。

[原七天句柄最新只读快照](test-progress-seven-day-during-agent-qualification.json)仍为measuring：原R57两角色约90382/90367秒、5周期，精确发布候选R78约76868/76866秒、4周期，所记录原实例与SQL/API错误0保持。未重启、未替换进程，尚非实际604800秒及后置通过。

[真实已发布旧版受控迁移](testing-published-migration.md)26项通过：DBS/HISDBS各实际600.405/600.322秒、SQL/API错误0，升级与回退后原值记录/实际三资源阶段值、原PID1/PG/缓存及独立清理通过。首轮journal阶段断言缺陷与14项失败原件保留，不补称初始零计数通过。此结果只覆盖0.1旧发布次版本到1.0候选的明确停用/恢复迁移，不替代原同限额维护、两个已发布旧次版本、原32项百分比业务或长期条件。

[七天原句柄只读快照](test-progress-seven-day-during-published-migration.json)记录服务器UTC 2026-11-11T21:15:43Z：原R57为5周期/DBS86478.878与HIS86464.281秒，精确发布候选R78为4周期/DBS72965.441与HIS72963.549秒，所记录原实例保持、SQL/API错误0；仍为measuring，非604800秒通过，未重启或替换原长期进程。

[相同内核限额下的Agent活动对照](plan-agent-fixed-io-comparison.md)已归档设计，尚未实现或执行；保持135写IOPS等原主要稳态额度，对比正常活动与精确暂停Agent，不再提高额度或原样重跑IOPS矩阵，不改变正式验收标准。

[写IOPS单变量对照终态](testing-write-iops-comparison.md)：A1600.299秒/SQL0/API4；B600.182秒/SQL0/API0；A2600.386秒/SQL3/API0。预定IOPS模式出现，但仍存在混杂因素；三组均11区间/10引擎内容，完整逐请求/线程/设备/PG与独立退出清理归档，并提供可重放严格判读和不完整矩阵拒绝检查。B单组不替代原32/两角色百分比验收，不改变原额度/SLA；旧失败/52任务/长期条件及产品程序保持。

[写IOPS单变量A/B/A诊断](testing-write-iops-comparison.md)已冻结并启动：三完整冷副本先冻结，主策略仅135/4096/135写IOPS变化，CPU/内存/BPS/第二策略及原600秒/64MiB/11区间/SLA保持；预先规定三组完整600秒且A错/B零/A再错方记录模式，仍保留共享后端混杂。首次Windows路径计划拒绝原件保留，修正后12项前置通过；开始快照A1仅2项启动局部，不是原32/两角色百分比验收。旧失败/52任务/长期及产品程序不变。

[设备/唯一轮次PG等待完整压力终态](testing-business-pressure-device-pgwait.md)失败：DBS实际600.412秒/SQL0错/API3次超时，HIS未执行；13局部/11区间/10引擎内容不抵消失败。422请求、601PG、598线程和599设备样本完整归档，22个DBS.log写D观测，3错误各重叠4个严格D样本；PG栈未知、全设备队列不等于本组因果。5原实例/namespace/cgroup及原输入恢复独立核对，46原始文件及可重放分析归档，旧失败/原32项门槛/52任务/长期条件不变。

[设备与唯一轮次PG等待完整压力接入](testing-business-pressure-device-pgwait.md)已另建冻结执行器并实际启动：18项前置通过，原业务方法AST仅诊断依赖/worker/标记变化，原32项、每角色600秒、64MiB、11区间及配额/SLA不变。开始快照DBS13局部/11区间且原四个实例存活，不代表完整业务通过；等待同一运行器终态与独立清理。全部历史失败、52任务及长期条件保持，产品和preview.2程序不变。

[唯一轮次PG等待接入worker资格](testing-native-diagnostics-v2.md)完成：最终宿主及两原镜像各15项、两个实际路径空库各26项，共97项通过，覆盖正常、受控锁失败保留和缺标记故障放行。前两轮PG初始化失败完整归档；修复Python2临时模块回收清空全局字典的问题，保留模块引用并增加GC与正确拒绝回归。15份源码及三轮清理证据归档。尚待新完整执行器接入本worker及设备会话，原32项/各600秒/配额/11区间/历史失败与52任务及长期条件均保持；产品和preview.2程序不变。

[PG实际路径等待诊断资格](testing-pg-wait.md)已完成：宿主及DBS/HISDBS原镜像各32项、两个新建空库各14项，共124项通过；按实际PGDATA及本轮唯一标记筛选，复查PG和/proc身份，边界/采集失败保留unknown。实际内核栈不可读，未宣称采到IO写回栈。六份源码和节点原始协调报告归档，父进程/Pod/cgroup/namespace独立确认退出。下一步冻结并资格新的worker/联合接入，尚未执行原32项完整压力；原业务门槛、历史失败、52任务及长期条件保持，产品和preview.2程序不变。

[设备采集会话与接入资格](testing-device-sessions.md)已完成：宿主26项会话与20项实际并行/故障放行检查通过，首轮执行至第12项时因目标已回收却要求Z状态而出现的一次断言失败完整保留并分场景修正；15份原始观察报告和9份固定源码归档，3个资格父进程/16个观察器独立确认退出。仅宿主诊断资格，尚未接入原32项完整压力；PG实际路径选择器、全部原业务/长期条件与52任务保持，产品及preview.2程序不变。

[有界设备状态采集器](testing-device-state-observer.md)已实现：节点Python3.9与DBS/HISDBS原镜像Python2.7各32项实际通过（每份3秒/4样本），另2项节点真实自然退出/观察器pidfd TERM部分报告检查通过；原进程/两Pod scope/namespace独立确认退出。仅只读诊断资格，未接入原32项完整压力，不关闭历史失败；三资源比例、产品程序、52项和长期handle保持。

[写BPS对照v2终态](testing-write-bps-comparison-v2-result.md)：三组均实际600秒，A1 SQL4/API4错、B SQL0/API1错、A2同原上限SQL0/API0且16项组内通过；未形成预定A失败/B改善/A再失败模式，不能认定仅写带宽是原因。三namespace/cgroup及已固定负载/API/观察进程独立确认退出，配置和原源关键摘要保持；15份原始结构报告及8项离线复现/拒绝检查归档。原32项/两角色百分比、52任务和长期条件继续，不改变配额或原时限。

[首轮写BPS对照实际失败](testing-write-bps-comparison-failure.md)：A1/B因测试器错误预期提前结束且不足600秒，A2准备失败/实际建表5.47秒，均不作业务通过；三组全部退出/恢复、源保持。已修正手动模式非法IO测试输入并新增精确ELF四项只读校验，[v2](testing-write-bps-comparison-v2.md)12项前置通过、独立三份完整冷副本已冻结并启动，首快照尚无600秒终态。包装CI发现的源码链接已修正，旧CI失败保留；原R235/52项/长期门槛继续。

已完成[R235逐秒IO复现](testing-pressure235-IO-timeline.md)：599区间/6错误窗口均在最后切换后，控制读回与配置一致，严格请求内D样本4与IO括区间D样本5分开。基于该线索已启动[完整冷副本写BPS A/B/A诊断](testing-write-bps-comparison.md)，原native/备份/内存压力/SLA保留，两组manual且仅写带宽轨迹不同；8项前置通过、三副本先冻结，首快照A1仅启动2项，非原32/两角色百分比验收。初始跨平台计划及启动校验拒绝均留档，旧失败/原标准/52项不变。

[R235完整压力终态](testing-business-pressure-final-wait-failure.md)已确认失败并清理：DBS实际600.292秒、SQL1/API5错（HIS未执行），13局部/11区间及引擎10内容检查不抵消业务失败。新诊断取得419请求/601PG样本、600线程样本；SQL对应5个LWLock/WALWrite样本，36个D样本均为DBS.log的write/XFS等待，5次原生API超时各重叠4个D样本。因果仍待设备/限额/日志关系核对；原预算/旧失败/52项和长期要求保持。

已归档[完整压力等待诊断/失败收尾接入](testing-business-pressure-final-wait.md)：只读采集24项、观察器19项、选取预算10项，两业务API各16个短样本（未见D）及同实例/控制值保持；12项接入与15项只读/拒绝检查实际通过，原生部分PG报告仍拒绝作600秒。新R235完整32项/每角色600秒/11区间原配额SLA未变并已启动，固定启动快照不代表通过；原R203停库/API失败、所有52任务和长期要求保持。

已完成[提前失败原生负载最终清理资格](testing-native-final-flush.md)：Linux18项、DBS/HISDBS两原镜像各8项实际通过并退出/清理；精确pidfd仅向本轮worker发TERM，实际部分诊断落盘，原600秒/failed/interrupted保持。首轮长无关参数拒绝及旧源码保留。尚待完整压力工具接入与原业务复测，R203停库和API失败/全部52项/长期标准不因此解除。

R203[原生诊断压力联测终态](testing-business-pressure-native-diagnostics-failure.md)失败：DBS13局部/11区间通过，但备库停库31.421秒超过原30秒，71个引擎探针另有7次API内部超时；未完成两角色600秒/HIS。提前外部失败导致原生最终诊断未落盘，初始零计数不可当通过。原始185线程样本、日志和输入恢复/进程清理已核对；保留旧失败/原预算/52项和七天任务，不放宽标准。

当前即时交付：[v1.0.0-preview.2](releases/v1.0.0-preview.2.md)，与preview.1同一受测程序；[实际发布/下载核对](test-results-preview2-publication.json)。本版仅刷新文档和证据，稳定1.0尚未发布。

当前尚未发布稳定1.0。[52项原始任务索引](current-task-registry.json)、[十版规划](roadmap.md)和[需求档案](requirements.md)保留全部范围；R29暂缓其他资源的新交付，未删除历史任务。当前资源入口仅CPU/内存/IO独立百分比，各自省略默认20；v1/混合/未知跳过，纯v2通过身份和权限检查后设置；每日日志保留30日或总1GB，辅助故障不作为原业务启动前提。

## 已发布与当前候选

| 范围 | 可核对的实际证据 | 不能据此宣称 |
|---|---|---|
| [已发布工程预览](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v0.1.0-rc.3-preview.1) | 三独立比例/cgroup门禁/日志；原资产Linux6.8/7.0、AMD64/ARM64四格[88项控制器检查](testing-released-cgroup-ci.md) | 正式RC3或稳定1.0、ARM厂商业务 |
| d3706f3程序（现已工程预发布） | [自身CI/原生ARM及整盘44项](testing-partition-integration.md)、[构建身份9项](testing-partition-build-identity.md)、[三场景各1800秒开销](testing-partition-steady-overhead.md) | 把其他源码结果改名为当前程序，或以工程检查替代完整业务长测 |
| 当前程序DBS/HISDBS真实路径 | [各600秒/12项业务](testing-partition-realpaths-business.md)、[20场景/108项辅助故障](testing-partition-realpaths-faults.md)、[开发构建维护22项/各600秒](testing-partition-realpaths-maintenance.md)、[四次冷启动44项](testing-partition-realpaths-cold-rebuild.md)，各终态通过且清理 | 默认20%或自动30%持续性能、最近两个已发布次版本维护 |
| 分区IO增强 | 468fe73的真实GPT双分区四格[164项](testing-partition-cgroup.md)；与组合生产源码逐文件合同独立列明 | 两块独立物理盘，或当前d370实际跑过同一164项 |
| 版本门禁与权限降级 | [版本输入模拟/真实v2及日志](testing-three-percent-cgroup-logs.md)、当前[真实只读/辅助故障](testing-partition-realpaths-faults.md)分别留档 | 真实v1内核已测，或权限丢失时一定能恢复已生效的配额 |

当前程序实际摘要、预算、环境和时长决定证据范围。原[默认20%四格业务失败](testing-three-resource-default20-business.md)及[补测](testing-three-resource-default20-supplement.md)保留；默认20不是已验证的DBS/HISDBS生产推荐额度。当前业务通过的是既定manual64测试预算。

## 长期阶段与后置

| 阶段 | 固定来源与当前证据 | 尚未完成 |
|---|---|---|
| 正式24h observe基线 | 原fc2程序，[两角色各实际86400秒终态通过](testing-baseline24h-final.md)，4周期原生组合接受，协调/负载入口已退出；exec超5秒诊断保留 | 旧observe结果不能代表新候选或限额阶段 |
| 正式等时enforce | 固定d6候选、预算及切换方案保留；须先有接受的完整基线再核对实时前置 | 独立24h enforce及对照报告；[完整基线后13/14前置](test-results-formal-stage-after-baseline.json)要求其他业务夹具先清理，不能以d370七天替换 |
| 当前d370七天连续组件 | [已开始及首周期观察](testing-seven-day-current-candidate.md)，首周期两角色各10项内容及临时清理完成，仍native-pending | 实际604800秒、28周期和完整原生判定 |
| 七天实际老化状态后置 | [只读采集/门禁](testing-aged-postflight-preflight.md)及[恢复/重建/维护执行器](testing-aged-postflight-execution.md)已实现，Linux自检和真实提前执行拒绝通过；独立短数据演练36项/各600秒终态通过且清理，原控制保持 | 真实七天后的执行及老化辅助故障/最终综合审计 |

[报告核验器](soak-report-audit.md)和只读前置门禁通过自检不代表真实长测通过；合成报告、真实pending和终态分开记录。采集计划及私有身份记录固定，后续执行另行引用，不能用新的空夹具替代七天实际使用的数据。当前P10_complete=false。

## 最终发布仍需核对

- 原24h+24h、至少七天综合验收及真实老化状态后置全部达标。
- 最近两个已发布次版本的维护兼容，而不只两个未发布开发构建往返。
- ARM厂商业务、独立物理多设备、未测运行时/内核和节点重启/掉电等原规划范围，按实际证据逐项处理。
- [环境覆盖索引](environment-coverage.md)、运维/恢复边界、诊断脱敏、冲突及所有权、包来源和全部52项最终审计。

环境索引是按源码/程序/内核/架构/存储限定的草案，不是稳定支持承诺。当前不恢复pids/权重/memory.high/Swap的新交付；旧实现仅按已有配置与恢复兼容规则处理。程序发布与生产接入分别记录，业务节点仍保持本任务只读范围。

历史固定观察保留原时刻：[故障中间采样](test-progress-partition-realpaths-faults.json)、[维护等待](test-start-partition-realpaths-maintenance.json)、[七天首300秒](test-progress-seven-day-current-candidate-start.json)等均未覆盖或删除，终态应沿上表对应的最终报告判断。

## 版本化v1.0.0候选的独立资格

候选来源与包身份见[固定身份](release-candidate-identity.md)。该版本化程序现已作为工程预发布交付，AMD64摘要dbc48aa5，ARM64摘要a01a5c2b，均与旧开发程序分别计数。

| 已完成项 | 实际结果 |
|---|---|
| 原生架构/内核 | [Linux6.x/7.x、AMD64/ARM64四格88项](testing-versioned-candidate-native.md)，八项产物均与Windows逐字节一致 |
| 自身运行开销 | [三场景各1800秒](testing-versioned-candidate-overhead.md)通过，运行器退出0，namespace独立确认清理 |
| 原厂商真实路径业务 | [DBS/HISDBS各600秒、12项](testing-versioned-candidate-business.md)通过，原manual64预算及启动/延迟/覆盖/数据/备份/独立恢复标准保持，退出0/清理 |
| 自身辅助故障 | [两角色20场景/108项](testing-versioned-candidate-faults.md)通过，原90秒/45秒/12秒及实际标定取消条件保持，退出0/清理 |
| 自身短保留数据后置 | [36项/两角色各600秒](testing-versioned-aged-postflight-execution.md)通过，四次Pod及cgroup清理；实际七天后置另待 |
| 自身短保留数据故障 | [20场景/152项](testing-versioned-aged-faults.md)通过，20个Pod及cgroup清理；实际七天故障另待 |

新摘要的[在线升级/回退两角色各600秒、22项终态通过且清理](testing-versioned-candidate-maintenance.md)，[冷重建四次启动44项终态通过](testing-versioned-candidate-cold-rebuild.md)，[自身实际七天原生测量已开始](plan-seven-day-versioned-candidate.md)；未将旧开发版3a1、原observe或固定d6阶段的运行时间转给新程序。默认20%和自动30%持续性能未因此通过，当前稳定1.0尚未发布。

实际老化辅助故障[执行器及冻结计划](testing-aged-faults.md)已实现并通过8项Linux自检；长门禁及提前执行真实返回pending且无工作目录/namespace。明确分开的[短保留数据20场景/152项终态通过并清理](testing-aged-faults.md)，原数据、输入和日志保留。原七天和其恢复/维护后置不因短演练完成而自动通过。


新摘要dbc48aa5的[七天首次固定测量观察](test-progress-seven-day-versioned-candidate-start.json)和[自身谱系采集/只读门禁](testing-versioned-aged-preflight.md)已归档：首周期内容通过但native-pending，Linux8项通过、实际谱系已封存，提前后置仍exit2/pending且目标未创建。原R57同时独立确认在线。预发布包不因这些中间证据成为稳定版；真实七天及后置执行尚未完成。


版本化候选的[实际老化后置执行器](testing-versioned-aged-postflight-execution.md)已实现并通过Linux10项检查；真实七天默认/execute两次门禁均pending且未创建目标，独立短数据readiness通过并启动原实例演练，首观察DBS13项通过、尚未计两角色600秒终态。绑定本程序R64数据和新R78/R80b谱系，原R57/R59/R60保持；实际七天后置、老化故障和稳定全部条件继续。


版本化候选自己的[短保留数据后置演练](testing-versioned-aged-postflight-execution.md)现已36项/DBS600.332秒/HISDBS600.307秒通过，16个维护区间完整覆盖、原进程退出0、namespace和四Pod容器scope独立确认清理。原13项开始快照保留；这不是实际七天后置，P10/稳定版仍未接受。


版本化候选自己的[保留数据故障执行器](testing-versioned-aged-faults.md)已通过Linux9项与真实长默认/execute两次pending门禁，未提前创建目标；短前置通过并启动，固定首观察只有1场景/7项，20场景/152项待终态。原七天/正式对照/其他稳定门槛保持。


## 独立现场记录的限制

另一项[171现场更新记录](https://github.com/cuipengdba/ContainerResourceGuard/blob/c050b34ac15d2b8ea101bbe1b76e796e1ce6eb65/docs/deployment-dbs-hisdbs-update-20261111.zh.md)报告，同一dbc48aa5预发布程序安装后DBS出现两次新的PostgreSQL cgroup OOM kill和SQL/API错误，随后数据库重新启动；HISDBS未报告新增OOM。该记录显示更新前后配置和实际限额保持，但尚未证明新二进制导致或排除其影响。本轮97隔离验收没有独立重测171，不将其短期更新探针作为整体稳定接受，也不以隔离短演练覆盖现场故障。保留这一待核查运行记录，不修改171配置、限额或业务。


版本化候选自身的[短保留数据故障矩阵](testing-versioned-aged-faults.md)现已20场景/152项通过，原进程退出0、namespace及20个不同Pod/容器cgroup独立确认清理，原64MiB数据/输入/journal/日志前缀保留。首个运行中快照保持；三个来源明确分支的完整CI与两个ARM64检查通过。真实七天后置、正式对照及其他稳定条件仍待，未重发或替换既有下载资产。


本轮已补齐精确发布候选的[15项工程重载终态](testing-versioned-candidate-reload.md)及当前d370源码[两个10分钟解析器fuzz](testing-d370-parser-fuzz-windows.md)，21,680,191次执行、exit0。同步[修正任务索引中旧24h基线等状态](task-index-review-20261111.md)，保留52项原定义和旧scope_note；未将工程重载或源码fuzz计为厂商业务/实际七天验收。preview.2既有资产保持，长期及原稳定条件继续。


精确版本化候选[真实DBS/HISDBS业务热重载联测](testing-versioned-business-reload.md)现已24项主检查通过；两角色各600秒、14次配置观察均有8文件实际回读，原引擎各10项/原生阈值/同一业务与辅助进程/原值恢复及清理通过。仅覆盖本协议场景；实际七天、正式对照和原稳定条件继续。


本轮HISDBS保留一次[exec API 7.017秒诊断失败](testing-versioned-business-reload.md#保留的exec探测超阈值)，超过原5秒；原生API整段最大0.008936秒/错误0。原因尚未确定，未将诊断失败改成通过或关闭P01.3。


[业务exec分段终态](testing-business-exec-timing.md)：26项主检查、DBS/HISDBS各600秒及各10项原备份/同步/恢复通过且独立清理。DBS另有外层5.000814秒超原5秒诊断失败，内层HTTP0.008885秒、区间外4.991929秒，窗口本容器CPU节流增量0、PSI不可用；同脚本日志仅候选关联。原HIS7.017秒根因未定，P01.3不关闭，七天及稳定条件继续。


[热重载边界R113失败](testing-business-reload-edges.md)：DBS目录配置恢复观测超原60秒，17项局部检查不计完整业务，HIS未执行；清理和配置/profile/ELF保持独立确认。终态Agent已恢复accepted9，测试等待有重复写入/错误起点的时序缺陷，精确旧mark未保存；新协议修正观察、不延长阈值，原失败保留。


R120[配置恢复边界联测失败](testing-business-reload-source-recovery.md)：DBS22段/24项局部主检查和五类恢复均通过原门槛，但备库fast stop超30秒，日志restartpoint37.924秒/sync37.713秒，整轮失败；未完成600秒、HIS未执行，运行器/Pod/cgroup及输入恢复独立确认。原失败、配额及SLA保持；[七天固定实际进程观察](test-progress-seven-day-during-source-recovery.json)仍为measuring，未接受稳定版。


原P03.3/P05.2[精确30→20压力与释放后重试](testing-business-memory-pressure.md)已启动；[开始快照](test-start-business-memory-pressure.json)仅DBS8项局部主检查，不计32项/两角色600秒完成。辅助工具7项释放、真实前置7项、三个源码分支CI及42份公开文件摘要通过，原R113/R120失败/原预算/30秒停止及全部长期条件保持。


R130[压力补测失败](testing-business-memory-pressure.md)：辅助工具在Python2/linux2平台名判断处拒绝，未申请压力内存，仅DBS10项局部检查，无600秒/HIS业务接受。新工具[实际运行时兼容/释放检查](testing-memory-pressure-legacy-runtime.md)通过Linux7项及两镜像16项并独立清理；产品与原执行器/计划保持，真实高用量及R120/长期仍待。


R142[真实30→20压力失败终态](testing-business-memory-pressure-legacy.md)：DBS实际分配约10.06GiB，延后缩减与释放后同generation7自动重试局部通过；11段/13项后，原生600.315秒API3次错误使整轮失败，HIS未执行。10项引擎内容及控制局部成功不抵消失败；独立清理/原输入和ELF保持。业务HttpTest日志出现17.857秒间隔，根因未定，原32项/全部SLA和长期门槛继续。


[单目标只读线程工具](testing-thread-observer.md)现已Linux19项资格、DBS/HISDBS各15秒/16样本/47线程观察完成，原实例和限额保持；PSI不可用明确unknown。首次HIS路径假设错误及DBS完整CPU缺失保留；修正后单独完成HIS观察。未复现压力/未关闭R142，原32项和长期条件继续。


R167[完整压力线程诊断](testing-business-pressure-threads.md)已实现并冻结；新增实际14项生命周期资格通过，首次SSH作用域缺控制文件失败保留。原完整业务方法AST除观察器启动/保存外一致，原32项/两角色各600秒及全部配额、SLA、历史失败不变；此时压力业务尚未执行，52项不宣称完成。


R167完整压力线程联测[已启动并归档开始快照](test-start-business-pressure-threads.json)：固定原运行器/worker/观察器PID及启动ticks；快照时DBS11区间、13项局部检查通过，真实高于20%目标时延后，释放后同gen7自动应用20%再恢复30%。原600秒负载/引擎仍pending、HIS业务尚未执行，不计完整业务通过。协议源码三个固定提交的CI均通过，公开45个来源/证据blob已核对，原发布包和历史失败保持。


R167[完整线程压力终态](testing-business-pressure-threads.md)失败：DBS600.269秒/SQL2错/API0错/13局部检查，601样本及实际主库三次慢UPDATE已归档；HIS未执行，CPU无节流/PSI未知不等于根因明确。全清理/原输入和ELF恢复已核对。下步补原生逐错和PG等待证据，不提高配额或放宽原32项/SLA。


R194[原生请求/PG等待诊断资格](testing-native-request-pg-diagnostics.md)完成：Linux23项、两厂商镜像各23项+3入口保护+16真实PG检查通过；正常请求通过，受控锁各保留一次原SQL超时，并取得对应后端/等待/阻塞者。三次先前资格失败和旧源码保留，四Pod cgroup/namespace/运行器独立确认消失，原输入/程序保持。仅采集链路资格，不关闭R167/R142/R120、原32项/两角色600秒或长期条件。


R203[完整压力接入原生/PG诊断](testing-business-pressure-native-diagnostics.md)已冻结并实际启动：12项只读前置和6项实际旧报告采集检查通过，开始快照DBS10局部/8区间、压力辅助仍在工作，各600秒/HIS及终态未接受。原完整业务方法AST仅诊断绑定变化，原32项/全部配额/SLA、旧失败与长期条件保持；不以初始报告零计数证明当前零错误。


已补充[R235实际PGDATA及IO映射只读核对](testing-final-wait-io-map.md)：原Pod明确PGDATA=/opt/postgresql/pgdata，实际WAL/日志/备份均为同一XFS253:0→sda2→sda，原标定profile保持。初次/data猜测路径的不存在和纠正完整保留；失败后队列快照不替代故障时刻或证明因果，不计独立物理多盘/业务通过。

<!-- memory-high-preview4-current:start -->
2026-11-12 preview.4：memory.high精确发布程序已通过[原生四格88项](testing-memory-high-native.md)、[身份与重建](test-results-memory-high-identity.json)、[三场景各1800秒开销](testing-memory-high-overhead.md)、[两角色各600秒真实路径业务](testing-memory-high-business.md)、[20场景/108项故障](testing-memory-high-faults.md)、[在线维护26项](testing-memory-high-maintenance.md)、[保留数据四次新ID/44项冷重建](testing-memory-high-cold-rebuild.md)。命名手动预算、原时限及独立清理保持；旧硬上限到high往返、过期快照拒绝、journal归属与原值恢复均实测。前一维护程序仍为未发布协议构建。默认百分比、真实回收/脏页与受限IO、老化故障、新策略实际长期和其他原稳定门槛继续独立判定，旧源时间不转移，52项未关闭，稳定版尚未接受。
<!-- memory-high-preview4-current:end -->


[memory.high独立七天组件已进入真实测量](testing-memory-high-seven-day.md)：精确preview.4程序、自己的计时/数据/句柄，10项启动检查通过，首个实际请求快照已记录；完整604800秒/28轮、老化postflight及全部其他原稳定条件尚未接受。只读观察字段修正保留原错误，业务作业未重启，旧源时长不移入。


[实际已发布preview.3→preview.4包内程序维护26项](testing-public-preview-memory-high-maintenance.md)通过：实际公开tar/manifest/ELF摘要绑定、两角色各600秒/各9命令区间/原全部SLA、hard/high往返及独立清理。旧506开发构建结果独立保留，这两个预发布tag不代替两个实际已发布次版本；[专用逐容器升级回退步骤](upgrade-preview3-preview4.zh.md)已归档，原52项及其他稳定条件保持。
