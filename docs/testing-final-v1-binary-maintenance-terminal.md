# 固定最终候选：二进制维护实际终态

实际公开 preview.5 到固定未发布最终 ELF，两者源码 ced461705ebc27315a59aefe463f9b4af47130a3，ELF和嵌入版本身份分别核实。没有重建最终产物，没有替换公开附件。本轮40/40主检查通过，以下均来自本轮各自新600秒。

| 角色 | 实际秒 | SQL 成功/错误 | API 成功/错误 | 维护命令 | 写入者快照 |
| --- | --- | --- | --- | --- | --- |
| dbs | 600.347 | 301/0 | 121/0 | 16 | 5 |
| hisdbs | 600.285 | 301/0 | 121/0 | 16 | 5 |

每角色16条维护命令含结束后的disable；15条在线命令和4次恢复Agent的时点全部落在对应成功的原600秒内。每次快照均只有一个实际ELF写入者，顺序为旧→最终→旧→最终→旧；journal摘要及全部8项内核控制保持。升级前静默Agent，安装后立即回退、候选运行后状态未变回退、变化配置拒绝旧回执及全新回执显式反向安装均通过。末尾disable恢复全部8项运行时原值及空自有journal，原配置字节、PID1/PG/缓存身份保持。

独立复算原SQL/API零错误、最大5秒、p95桶上界1秒和98%覆盖率，核对64MiB内容和主库启动时间；没有放宽配额或SLA。manual为7.2CPU/high20001980416B/双向64MiB/s/手动4096IOPS，外部8CPU/20GiB保持；不代表默认20%业务性能通过。

准确导出 26 份、333882 字节；runner、两driver、64条登记记录（62个去重PID/start）、两namespace及父叶cgroup已独立确认消失。旧七天任务保持运行，本轮时长不转记长期。

[独立复算及摘要](test-results-final-v1-binary-maintenance-terminal.json)、[全部准确原件](test-evidence-final-v1-binary-maintenance-terminal.json.gz)、[冻结计划](test-plan-final-v1-binary-maintenance.json)、[源码8项unit/race复核](test-results-final-v1-maintenance-source-event-review.json)。源码事件是既有准确修订的补充证据，不冒充本轮新注入ELF启动故障、未知协议可执行文件或厂商ARM。

启动器在唯一Popen之后、保存身份之前发生NameError，只读核实已有PID/start/入口后补记launch.json。原错误、补记和启动快照见[启动准确原件](test-evidence-final-v1-binary-maintenance-start.json.gz)；从未重启、改配额或改报告。公开原启动脚本仅作已执行错误的历史证据，勿复用。观察时一次读到正在写入的JSON不完整而失败，原回执保留；只读重读及最终准确下载不触发测试重跑。

P08.2按显式受控切换/回退的原工程范围补齐；不是自动业务故障检测/自动切版、未来所有格式、两次正式minor或任意安装布局的证明。P07.1/P08.1/P08.3/P08.4及压力、长期、老化等仍分别待验收。[下一项CLI/启动安装设计](testing-final-v1-cli-supervisor-design.md)只完成设计，执行器尚未冻结或启动。

[PR历史冲突处理](test-results-final-v1-integration-history-merge.json)仅在integration分支合入main历史，保留完整integration任务来源；合并后整个文件树与此前integration逐字节相同。不是向main合入候选产品，也不改变运行产物。

稳定1.0尚未接受，当前公开下载仍preview.5。原1498上传前拒绝、1448汇总失败、默认20%业务失败及其他历史全部保留。
