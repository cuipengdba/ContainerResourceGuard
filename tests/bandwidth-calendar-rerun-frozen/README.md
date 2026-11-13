# 独立HISDBS30日历日志补测冻结工具

准确产品ced461705ebc27315a59aefe463f9b4af47130a3，preview.5已发布程序SHA256 be6b0aa9f9bf932d8b02872e86a9cffcfea6d7199e39c274694dce904af07333。二进制不放测试目录，使用该发布的amd64程序。只运行新namespace的新HIS30完整36项/三次启动，原300秒业务、45秒缓存、原探针与删除门槛不变。原1129失败/未执行步骤保留；此任务不是修改旧报告或继承旧时间。

修正两处日志验证：删除前重新列出当前所有日文件、保留所有历史前缀、要求新增且仅新增一次准确版本/源码Agent启动，允许旧日期文件保持不变。十项正负边界回归和Linux0600检查已通过。旧576已经失败，使用终态报告/原进程消失及51个初始实例清理检查，原等待活跃长任务的门槛作为历史计划保留；不声称旧任务七天通过。

源码清单与哈希均由plan.json固定。工具会创建明确授权的隔离测试fixture，不是生产安装命令。

- [startup-matrix-driver.py](startup-matrix-driver.py)
- [runner.py](runner.py)
- [scoped-probe.py](scoped-probe.py)
- [backup-gate.py](backup-gate.py)
- [startup-sample.py](startup-sample.py)
- [artifact-transfer.py](artifact-transfer.py)
- [daily-log-continuity.py](daily-log-continuity.py)
- [daily-log-checks.py](daily-log-checks.py)
- [examples/optional-agent.sh](examples/optional-agent.sh)
- [plan.json](plan.json)
