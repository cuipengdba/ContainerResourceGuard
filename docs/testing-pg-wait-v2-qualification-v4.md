# PG等待诊断v2：修正引用后的独立资格轮

本轮承接[上一轮的实际guard失败](testing-pg-wait-v2-qualification-v3.md)，不修改任何已冻结输入。新[冻结计划](test-plan-pg-wait-v2-qualification-v4.json)先核对完整工具/输出/namespace常量和无旧路径残留，已通过本地inert入口检查；这些不计原生运行通过。

原四份v2文件保持原摘要。独立runtime-v3只将原runtime的helper引用从vendor-pg-wait.py改为vendor-pg-wait-v2.py，18项检查逐字保持；同一读取器、边界、宿主保留、隔离配置、540秒整轮期限和退出清理要求沿用上一冻结合同。v4驱动匹配新namespace，同时保留投射源诊断、逐项SHA256复制到UID999私有常规0400文件、先记录子命令输出再读取报告及两个独立退出文件。

计划仍为宿主Python3解析44项、DBS/HISDBS原Python2各44项解析与各18项新emptyDir真实PG，共168项。原32项解析和14项真实PG基线，以及v2新增12+4项均保留；4目标/5行溢出检测、1900B/目标、8192B/样本、4096B栈/8帧、wall0.25秒/线程CPU0.1秒/RSS128MiB保持。每个实例512MiB/1核、UID999/GID998、drop ALL/只读根、无原数据/业务配置/Agent挂载，使用实际厂商PG路径与只读核对摘要的bin/lib/share。

已完成本轮168项资格检查和独立清理；这里只接受诊断读取器资格，不计持续业务通过。所有源、计划、runner及本地inert结果见[精确冻结源码](test-evidence/pg-wait-v2-qualification-v4-frozen.json.gz)。实际投射源诊断不能补写最初v2缺失stderr，也不把栈权限错误当135写IOPS业务延迟的根因；默认百分比、真实high压力、持续业务和长期门槛继续独立判定，现有三个长任务不改。


## 实际终态：168项资格检查通过

[完整结果与原观察](test-results-pg-wait-v2-qualification-v4.json)记录宿主Python3.9.21的44项、两个厂商镜像Python2.7.5各44项解析及各18项真实PG；所有原边界保持。两角色新PG已正常停止，两个Pod父/叶cgroup、原PID1及runner/worker由独立观察确认消失；外层退出和资格退出均为0、未超时。

在这次新轮中，两个投射源诊断都捕获O_NOFOLLOW读取ConfigMap符号链接时的ELOOP/40；复制为相同SHA256的私有常规文件后原44项均通过。该结果复现装载故障机制，不补填旧轮缺失的stderr，也不倒改最初失败原因。独立runtime仅改helper引用，18项断言保持，实际加载v2读取器；两个真实PG目标的栈读取均记录read/EACCES/13且不含异常消息、路径或栈内容，真实目标退出后丢弃旧proc/缓存身份，新backend独立身份检查通过。

三次正常采样最大wall小于0.0027秒、线程CPU小于0.0013秒；资格进程峰值RSS为DBS13812KiB、HISDBS14004KiB，分别在原0.25秒/0.1秒/128MiB以内。这些是该隔离资格轮的开销，不外推持续业务开销。原namespace guard失败、原runtime错引旧读取器以及最初缺失报告记录均独立保留；未把权限错误当受限IO业务延迟的因果证据，135写IOPS/默认百分比/真实high回收压力和长期条件继续未完成。
