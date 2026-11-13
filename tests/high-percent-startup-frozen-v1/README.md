# 冻结的厂商启动矩阵工具

与[计划](../../docs/testing-high-percent-startup-matrix.md)绑定；这些脚本是授权测试节点上的隔离验收工具，包含固定的私有临时目录，不能作为生产启动程序使用。生产程序仍为准确 preview.4，二进制只记录摘要，不在此重复提交。

`startup-matrix-driver.py` 保留原启动链、缓存及真实路径，分别执行20/30三次启动；`scoped-probe.py`仅保存自己Pod UID的实际kubelet探针计数；`backup-gate.py`只读原长期任务；`runner.py`顺序创建和核验清理；`artifact-transfer.py`沿用已验证的有界字节导出，仅更换固定ROOT。

`offline-qualification.json`绑定最终被测模块摘要，21项只验证解析/门槛和语法，不能代替活进程、实际探针或业务验收。原件及资格检查源程序见准备证据。首次启动必须满足原长期任务同一进程和指定第五次备份完成门槛；此门槛不等于七天验收。
