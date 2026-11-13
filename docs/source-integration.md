# 1.0 主线源码集成候选

状态：准确源码7823d8d5da8d1f25909e26660697b36f0e0e9e2e的全部工程CI已通过，44项原生cgroup及164项分区实际检查通过。草稿PR #1未合并、未部署、未发布；业务和稳定版门槛仍开放。

当前下载preview.4从固定源码构建，但main源码仍旧。为使最终1.0有统一可检出、可构建的源码，本候选把组合分支已实现的cmd/internal、测试、示例、构建/包校验脚本和工作流按准确提交汇入。main当前文档和历史证据继续保留，不导入工作区未提交文件；[来源、范围及逐文件Git对象清单](source-integration-plan.json)列出准确基线与来源。

包含百分比/手动模式、每容器一对一自发现、memory.high及自有旧max迁移保护、v1跳过、自动选盘标定、每日30天/1GB日志和已有深入能力。默认IO百分比四轴换算保持；用户IO口径选择尚未答复，现有手动对照也不构成默认变更。候选另外含开发分支已完成的IOQuality日志和公共文档闭包打包修复，因此不能称为与preview.4程序字节一致。

验证顺序：先检查导入对象与固定来源逐一相等，再做本地gofmt/vet/Go测试及文档包闭包检查；提交候选后执行准确提交的完整Linux构建/竞态/集成/两架构包/完整性/可复现检查、原生ARM64及实际cgroup工作流。失败必须保留，不通过不能合并。即使工程CI全部通过，也不能将preview.4真机/七天经过时间移作此候选业务通过；原DBS/HISDBS全业务、百分比矩阵、物理备份、独占24h+24h、七天老化、硬件及正式版本升级门槛仍独立开放。

正在运行的manual1080与high576保留原二进制、PID/startticks、配额、目录与既定时限；没有在运行中替换或重启。原52项定义、旧失败和稳定版发布标准保持。此文档记录源码集成任务，不宣称功能/业务/发布已全部完成。

[本地Go检查原始输出](test-results-source-integration-local.json)已归档；Windows结果不冒充Linux竞态、原生ARM、实际cgroup或厂商业务验收。


## 分区驱动的内存语义修正

[首轮CI分析](test-results-source-integration-first-CI.json)及[28份精确成员与四份失败日志](test-evidence-source-integration-first-CI.json.gz)保留。Linux6.8/7.0×amd64/arm64均已实际进入分区夹具，各6项先通过，第7项期望memory.max而实际三项是cpu.max/memory.high/io.max；不是环境门槛失败。四格均记录清理完成。成功的44项原生cgroup及226个ARM测试事件只支持对应工程范围，不替代分区后续检查或厂商业务。

[驱动差异](partition-memory-high-port.diff)只把三项集合和预期内存目标从max改为high，保留八个实际控制文件的完整相等核对，并额外显式核对原外部memory.max未变和计划memory_policy。旧manual memory_max配置保留为别名，用于原发布程序disable/恢复兼容验证。全部原检查名称/数量、CPU/IO负载与吞吐标准、真实同盘两分区、重标定/几何失效、旧程序恢复、只读失败和清理时限继续；不删项或改变工程通过标准。程序Go代码和默认IO策略不变，需用新提交完整复验。

CI派发后的初次列表摘要过早要求恰好4个run而失败，三个dispatch均已受理；随后按相同提交取得实际四个run，没有重派或重启。首次日志读取发生在运行尚未终结时不可用，之后从同一已完成job取得原日志。原错误保留在本轮私人执行记录，不修改CI失败或补算通过。


## 第二轮失败与补正

[第二轮12份精确成员及5份日志](test-evidence-source-integration-second-CI.json.gz)保留：分区仍在第7项失败，首轮修正遗漏旧memory_max别名警告使状态为degraded。本次主流程/只读夹具改用规范memory_high；不把degraded放宽为通过。旧发布程序不认识这个新JSON字段，使用它已有的disable --state-dir /state入口，仍恢复同一journal，并完整核对八个运行时原值、Agent退出和PID1。

该轮构建/包/完整性检查已走到最后的可复现步骤，但新检出因一份既有部署记录的CRLF被text/eol=lf规则视作脏源而拒绝。该文件的提交/集成工作区/main原工作区字节摘要完全相等，均为6389ac109a1a17f78aab30554747eadc6d44a76ee03ea34090ab9450fa80f3db，63个CRLF。本次只为这一记录设置-text !eol保留原字节，不改记录、不忽略内容变更，也不删除dirty-source拒绝或可复现逐字节比较。main原工作区文件仍未触碰。两轮失败不能改写为通过，第三个准确提交需重新执行全部工程/分区检查。

## 当前准确提交复验通过

[独立资格分析](test-results-source-integration-current-CI.json)、[28份精确成员及原始job步骤元数据](test-evidence-source-integration-current-CI.json.gz)归档。四格各41项完成，规范memory_high及旧程序同state-dir恢复通过；八个实际控制文件保持完整比较，外部max为4294967296、high为134217728。完整构建的新检出可复现也通过，旧记录原字节未变。第一轮“保留旧别名”的描述是当时策略，第二轮已补正为规范high夹具；两个失败来源仍在历史归档中，不能抹去。

原生ARM64为真实机器ELF183和226测试事件；两架构各22项cgroup，Linux6.8/7.0两架构各41项同盘双分区，均有自己的清理证据。[集成与业务范围](source-integration-status.md)和[现有preview.4手动对照终态](testing-manual-IOPS-comparison.md)独立列出。PR事件额外构建成功可能采用合成merge SHA，准确源码采用push43438798105及三个固定dispatch，不混用来源。
