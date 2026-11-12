# 集成PG v2读取器的原生诊断资格

本轮把[独立资格168项已通过的PG v2读取器](testing-pg-wait-v2-qualification-v4.md)接入实际诊断线程与测试客户端。新建native-diagnostics-v3/soak-load-diagnostics-v3源，旧v2原件及其历史结果保持，已发布CRG程序和现有三个长任务不变。这仍是诊断集成资格，不是完整厂商业务或受限IO因果验收。

## 冻结范围

[计划](test-plan-native-diagnostics-v3.json)保留旧集成工具每运行时15项回调/故障隔离检查，以及每角色26项新PG+模拟HTTP检查，新增每角色两项实际PG栈read/EACCES/13且无私有消息/路径/栈内容的集成断言。预计宿主15、两厂商Python2各15+28，共101项。第一轮已失败，不能计完整资格通过，实际终态与第二轮安排见后文。[精确冻结源码](test-evidence/native-diagnostics-v3-frozen.json.gz)记录全部依赖、计划、runner和本地inert入口检查；inert不能代替原生资格。

新worker相对原worker只更换诊断模块文件名及锁定摘要。原64MiB新测试schema、SQL每2秒/API每5秒、5秒最大耗时、p95桶上界1秒、零错误和98%覆盖标准不改；三个短资格场景保持正常12秒、受控锁16秒、缺少PG权限标记12秒。受控锁场景必须保留原SQL超时失败并关联真实backend/锁等待，缺少标记时必须使诊断失败可见且原请求继续、业务stop不被置位。短资格时长不能计600秒、24小时或七天。

原诊断8MiB报告、1024请求、901样本/16行、1秒采样/只读查询时限、内部三类线程CPU合计不超过单核5%的边界保持。PG模块按已验证的SHA256从同一私有常规目录载入；O_NOFOLLOW、Python2模块生命周期引用、请求错误优先及未知元数据规则保留。测试源保留独立版本，不把历史generic OSError补写为errno13，也不把权限错误当受限IO业务延迟根因。

两角色顺序运行原厂商镜像Python2与核对摘要的只读PG bin/lib/share；新emptyDir PG数据与模拟HTTP服务，不挂载原业务数据、配置、Agent或缓存。UID999/GID998、drop ALL、只读根、无ServiceAccount/hostPID/hostNetwork，每Pod最多512MiB/1核；源为私有0700目录下常规0400文件。沿用540秒整轮上限和每次宿主至少8GiB+512MiB可用内存；退出后独立核对Namespace、Pod父/叶cgroup、原PID1与协调进程清理。

后续完整受限IO/真实high压力轮仍须预先冻结源、预算、600秒负载、备份/同步/独立恢复及所有原业务标准。本轮通过也不抵消此前默认20%或135写IOPS失败，不关闭原52项及其他稳定门槛。


## 第一轮实际失败与独立复测

[原终态、观察和源码绑定](test-results-native-diagnostics-v3-v1.json)记录宿主15项、DBS原Python2回调15项通过；DBS正常场景runtime退出1，stdout报告第10项normal-original-native-gate-passes失败，HISDBS尚未执行。外层先检查子命令成功才存储已读取的runtime报告，导致正常场景的具体SQL/API/覆盖/时延数据未归档；不推断是哪项指标失败，不把它归因于读取器或放宽标准。原空卷Pod删除后这些未归档指标不能恢复。独立观察确认namespace、DBS父/叶cgroup、原PID1与runner/worker均消失；两个退出文件均为1。

[第二轮冻结计划](test-plan-native-diagnostics-v3-v2.json)只修正报告保留次序：先保存raw/解析报告，再判断子命令成功；宿主也先记录子命令输出。原四份新集成源码、三个场景时长、全部15/28项、CPU/内存/报告/540秒边界逐项保持，新namespace/目录/计时，不复用旧结果。节点在创建新夹具前重新核对第一轮失败报告/退出/进程与父叶cgroup消失。第二轮已完成101项及独立清理；[第二轮精确源码](test-evidence/native-diagnostics-v3-v2-frozen.json.gz)含独立inert检查，不代表实际运行。


## 第二轮实际终态：集成资格101项通过

[原始报告、各场景请求统计和独立清理](test-results-native-diagnostics-v3-v2.json)确认宿主15项、两厂商Python2.7.5各15项回调/28项真实PG+模拟HTTP，共101项通过，两个退出文件为0且未超时。两角色均验证正常/受控锁/缺少标记的原行为；受控锁必须保留SQL超时失败并关联真实backend与锁等待，缺少标记时诊断失败可见且原请求仍按原门槛通过。两个有标记场景均集成PG v2 read/EACCES/13且无私有异常内容，原身份复查保持。

同一helper/worker/unit/runtime字节与第一轮保持，只有外层报告保存次序修正；所有原15/26项、另加2项以及预算/时限不变。内部三类线程CPU占单核最大实测0.3948%，在原5%以内，不外推持续业务开销。新PG均正常停止，namespace、两个Pod父/叶cgroup、原PID1和runner/worker经独立观察确认消失。

已归档[九份完整的已测源码副本](../tests/diagnostics-v3-frozen/README.md)，摘要与本轮逐项相同，不覆盖原v2源或正在运行的任务。原第一轮正常请求失败的具体指标已丢失、原因仍未知；本轮通过不能证明该不稳定现象已解决，也不抵消受限IO/default20%等原失败。当前只接受本轮诊断集成资格，不接受短正常场景稳定性、完整厂商业务、真实high压力或1.0稳定发布。
