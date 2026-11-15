# 输出1571启动失败、旧78长测终态及节点准入修订

当前17/52，稳定1.0未接受；产品源码/最终ELF未改、未重建，公开preview.5保持。

## 输出1571真实结果

唯一启动后DBS原90秒Ready等待失败，kubelet明确ErrImageNeverPull：原镜像本地已不存在且策略为Never。CRG和600秒业务测量均未开始，0主/0输出检查执行，26主/28输出未执行；HISDBS未启动。runner拒绝在缺失夹具进程/cgroup身份时继续下一角色。不能把本地22检查或原生准入成功计成真实功能通过。旧1551错误预期已修正，但修订后的28项输出组合仍待独立实测。

冻结十二输入保持；准确导出5文件9264字节。原观察器对缺失group报错保持，修订只读观察器如实报告清理未证实。随后用kubelet记录的Pod UID及sandbox ID另行核对namespace、CRI sandbox/container、该UID的cgroup与/proc关联全部消失；原runner/DBS driver也已消失，不改写原失败报告，不假装记录过不存在的进程身份。

## 旧78七天试验

旧源码d3706f3e、ELFdbc48aa5、memory.max策略，原28周期/604800秒任务在第19次周期检查失败后自行退出1。两worker共同区间约388942.872秒（约4.50天），前18次是内容通过/native待定；19次整体failed，两个角色各10引擎检查记录、cleanup=false，HIS短exec诊断SQL最大5.4938秒超过原5秒。周期失败的完整根因与全部临时恢复夹具清理尚待原报告独立复核，不能归因于最新memory.high候选，也不声称七天通过。

各6483个宿主样本；DBS原生文件仍为running快照，HIS文件failed/interrupted，二者均不足604800秒。主报告10通过/1失败，原runner/campaign已消失、主namespace已删除。准确下载5文件14848929字节，SHA及JSON绑定保存。未对旧句柄发信号或重启，时长不继承；正式最终候选1396仍未启动。

## 磁盘与准入

节点曾出现DiskPressure；该时间点与缺镜像各自有记录，尚未凭单一事件断言GC因果。旧试验副本长期占用已纳入环境问题。仅删除已终态且已有完整公开报告/精确清理记录的449/441八份冷副本postgresql载荷：解析目标位于明确自有目录、无symlink/嵌套挂载、无活动Pod hostPath、无进程cwd/exe/fd引用，原PID/start和namespace/父叶再次核对。原报告、原件归档、源fixture、原镜像tar及其他目录保留。八项删除逐项落盘记录；reflink共享块使du表观减少与实际释放不同，真实可用增加5045620736字节，不能声称释放140GiB。旧78已在操作前退出，前后状态均如实记录。

13:28节点DiskPressure已恢复False，但当前可用约51GiB，仍不足后续长期任务的预留。新增仅用于隔离测试的只读节点准入：单一Ready节点、Disk/Memory/PID压力均False、空闲至少max(20GiB,文件系统15%)，两原厂镜像配置digest及原tag对应关系必须存在。八项离线正反例及真机实际拒绝归档；本次不创建夹具、拉镜像、改节点参数或产品控制。后续冻结测试需把此准入绑定到准确源码，容量与同摘要镜像恢复后使用新目录/run-id独立测试，禁止重启旧失败轮或放宽原SLA。

这些是测试存储与运行准入操作；CRG每容器一Agent、三独立百分比/memory.high/BPS-only百分比、v1跳过和每日日志保留30天/1GB要求保持。未完成默认20%业务性能或最终长期门槛。

[1571失败复核](test-results-final-v1-output1571-early-failure.json)、[1571准确原件](test-evidence-final-v1-output1571-early-failure.json.gz)、[旧78终态](test-results-old78-terminal-failure.json)、[旧78准确原件](test-evidence-old78-terminal-failure.json.gz)、[冷副本载荷清理](test-results-retired-payload-cleanup.json)、[节点准入程序](../tests/disposable-native-node-admission.py)、[八项离线检查](test-results-native-admission-offline.json)、[真机准入拒绝](test-results-native-admission-real-refusal.json)。
