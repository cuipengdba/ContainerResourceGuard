# preview.5 手动参考预算：原完整600秒业务工具

产品准确源码ced461705ebc27315a59aefe463f9b4af47130a3，匹配公开preview.5程序SHA256 be6b0aa9f9bf932d8b02872e86a9cffcfea6d7199e39c274694dce904af07333；此目录不提交二进制。使用已发布匹配包，计划记录全部源文件哈希。

本轮单独验证已存在的手动模式参考预算：CPU7.2核、memory.high=20001980416B、读写各64MiB/s、读写IOPS各4096；保留外部20GiB硬上限。该预算在默认20%失败之前已记录，不能把手动结果算成默认20%通过。默认值与旧失败均不变。不自动标定，检查manual计划和实际四轴IO值，其他资源保持原值。

DBS、HISDBS顺序运行，每容器一个Agent。原300秒启动、45秒缓存、600秒native、零SQL/API错误、最大5秒/p95桶1秒/98%覆盖、64MiB数据和十项物理备份/同步/独立恢复保持，原引擎300秒/停库30秒不变。原native/campaign/engine/optional-helper逐字节不变。不得重试、调额、修改PG或放宽原门槛。先独立确认前一默认20%任务失败终态与全部54登记实例/两namespace/两组父叶清理，再创建本轮结果目录。

共享节点，原业务对照fixture没有Kubelet liveness；不能替代另行完成的精确原探针三次启动组合、独占24h、因果开销或七天老化。当前仅冻结/预检，不是业务通过。

- [manual-business.py](manual-business.py)
- [runner.py](runner.py)
- [artifact-transfer.py](artifact-transfer.py)
- [tests/vendor-soak-load.py](tests/vendor-soak-load.py)
- [tests/vendor-soak-campaign.py](tests/vendor-soak-campaign.py)
- [tests/vendor-engine-smoke.py](tests/vendor-engine-smoke.py)
- [examples/optional-agent.sh](examples/optional-agent.sh)
- [plan.json](plan.json)
