# PG等待诊断v2：修正引用后的独立资格轮

本轮承接[上一轮的实际guard失败](testing-pg-wait-v2-qualification-v3.md)，不修改任何已冻结输入。新[冻结计划](test-plan-pg-wait-v2-qualification-v4.json)先核对完整工具/输出/namespace常量和无旧路径残留，已通过本地inert入口检查；这些不计原生运行通过。

原四份v2文件保持原摘要。独立runtime-v3只将原runtime的helper引用从vendor-pg-wait.py改为vendor-pg-wait-v2.py，18项检查逐字保持；同一读取器、边界、宿主保留、隔离配置、540秒整轮期限和退出清理要求沿用上一冻结合同。v4驱动匹配新namespace，同时保留投射源诊断、逐项SHA256复制到UID999私有常规0400文件、先记录子命令输出再读取报告及两个独立退出文件。

计划仍为宿主Python3解析44项、DBS/HISDBS原Python2各44项解析与各18项新emptyDir真实PG，共168项。原32项解析和14项真实PG基线，以及v2新增12+4项均保留；4目标/5行溢出检测、1900B/目标、8192B/样本、4096B栈/8帧、wall0.25秒/线程CPU0.1秒/RSS128MiB保持。每个实例512MiB/1核、UID999/GID998、drop ALL/只读根、无原数据/业务配置/Agent挂载，使用实际厂商PG路径与只读核对摘要的bin/lib/share。

尚未运行，不能计资格或业务通过。所有源、计划、runner及本地inert结果见[精确冻结源码](test-evidence/pg-wait-v2-qualification-v4-frozen.json.gz)。实际投射源诊断不能补写最初v2缺失stderr，也不把栈权限错误当135写IOPS业务延迟的根因；默认百分比、真实high压力、持续业务和长期门槛继续独立判定，现有三个长任务不改。
