# 写带宽对照 v2

已结束：[A1/B失败、A2组内通过](testing-write-bps-comparison-v2-result.md)，未形成预定写带宽因果模式；下文首快照按当时状态保留。

此轮修正[首次无效对照](testing-write-bps-comparison-failure.md)的测试输入适配，保持[原对照设计](testing-write-bps-comparison.md)与全部原时限。产品、原R235方法、原32项/两角色百分比验收及52任务定义未变。[v2冻结计划](test-plan-write-bps-comparison-v2.json)绑定工具SHA bc4b46a8b43a6d6b787f6bc65b1c229774a02102af44a87f6f1b61610fda2a93，计划SHA b3b355e10ed21aca6e652e1ffb36c2ddadd1a5820393988b5b03de7e10425027；新[源码](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-write-bps-comparison-v2.py)保留显式、计数且字节可逆的适配清单，原源码不覆盖。

[实际资格记录](test-results-write-bps-comparison-v2-qualification.json)包含8项只读/拒绝门禁及精确发布ELF的4项非法配置读取。先证明首轮所有进程/namespace/cgroup已终止且输入恢复，才启动独立新根/新run_id。全部三份冷副本再次在首组前从同一原数据冻结，没有删除历史数据、放宽配额或延长查询时限。

[启动快照](test-start-write-bps-comparison-v2.json)在节点2026-11-11T16:08:18.572566Z确认runner176383/start135319371、worker176395/start135319375同实例存活，三份副本已冻结，A1 testing-dbs但尚无启动检查完成；这不是600秒结果。后续只观察同一handle，准备或重载夹具失败则本轮停止，保存终态再决定新工作。首轮全部失败、长测和发布门槛保持，不能将任何单组成功或协调器退出0当稳定发布通过。
