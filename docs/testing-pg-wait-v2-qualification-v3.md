# PG等待诊断v2：新版隔离资格验证

本轮只验证后续受限IO诊断的有界读取器，不是资源控制程序新版本，也不代表默认20%、135写IOPS、真实high压力或长期业务已通过。原生产程序、业务SLA、预算和三个长任务不变。

## 保留原失败

上一资格作业只完成宿主Python3的44项；DBS原Python2未产出unit报告，尚未启动真实PG，HISDBS未执行，资格未通过。原驱动先读取缺失报告才记录子命令stderr，未捕获最初错误；不能把推测当根因。[原失败与精确旧源码](test-evidence/pg-wait-v2-qualification-original.json.gz)保留，历史generic OSError的errno继续未知，不补写为13。

## 独立冻结的新轮

[冻结计划](test-plan-pg-wait-v2-qualification-v3.json)保持原四份v2源码、原32项解析/14项真实PG基线及新增12项解析/4项真实PG检查；预期宿主44、两角色各44解析与各18真实PG，共168项。原每目标1900B、每样本8192B、4目标/5行截断检测、栈4096B/8帧、正常wall0.25秒/线程CPU0.1秒/RSS128MiB及540秒整轮上限不变。新轮未运行、未计通过。

新增驱动修复测试装载与取证流程：先单独记录投射ConfigMap源的诊断命令退出码/stdout/stderr，不计资格通过且不预设原因；随后将逐项SHA256锁定的源复制到全新UID999私有0700目录、常规0400文件，保留读取器O_NOFOLLOW保护，再执行同一原生44/18项。每个unit/runtime子命令的输出先写报告，之后才取结果文件；资格自身退出与外层runner退出使用不同文件，避免重复创建掩盖结果。投射文件与私有常规文件验证同一精确源码。

两角色使用原厂商镜像中Python2、同一已核对摘要的PG二进制/库/share只读挂载，新的512MiB emptyDir数据目录与真实容器PG路径；以UID999/GID998、drop ALL、只读根、网络隔离、无ServiceAccount运行。原数据、配置、凭据、Agent与缓存不挂载。每次仅一个512MiB/1核实例、宿主至少8GiB+512MiB可用内存，结束验证Namespace/Pod父叶cgroup/原PID1及外层协调进程清理。新测试不能冒用此前PID、时间或结果。

冻结源码包括计划、驱动、runner和全部依赖的exact_utf8及SHA256，见[新轮精确源码](test-evidence/pg-wait-v2-qualification-v3-frozen.json.gz)。它只证明输入固定，不能代替实际原生运行或完整业务验收。
