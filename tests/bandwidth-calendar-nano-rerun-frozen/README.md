# 独立HISDBS30纳秒日志兼容补测冻结工具

源码ced461705ebc27315a59aefe463f9b4af47130a3、同一preview.5发布程序，SHA256 be6b0aa9f9bf932d8b02872e86a9cffcfea6d7199e39c274694dce904af07333。只修正验收工具，不重新打包程序。旧1170报告、工具和冻结计划保留。

旧节点Python3.9.21的fromisoformat拒绝Go日志9位纳秒。显式验证RFC3339Nano日期/时间/时区并构造calendar时间，保留原字符串；18项正负回归默认使用真实9位格式，已在节点执行。重新独立跑完整HISDBS30的36项/三次启动，原全部业务/负载/探针/超时保持。

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
