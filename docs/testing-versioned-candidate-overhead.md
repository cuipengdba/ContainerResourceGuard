# 版本化候选的稳定开销复验

按[冻结计划](test-plan-versioned-candidate-overhead.json)在独立测试节点测试真实v1.0.0候选AMD64程序dbc48aa5，已开始真实测量，[固定早期观察](test-progress-versioned-candidate-start.json)记录三组各23个样本、约220秒，仍pending。先接受[四组原生88项及跨主机产物一致性](testing-versioned-candidate-native.md)，再创建三个独立占位PID1容器，每个容器一个Agent，分别验证健康、持续指标/事件导出失败、真实只读cgroup。

沿用原45秒预热、各实际1800秒、10秒采样、单核CPU≤0.1%、RSS≤20MiB、状态写入间隔≥299秒、健康写入≤8MiB/故障≤16MiB、零OOM及唯一进程/全部8项实际控制不漂移等标准。每日0600日志必须记录v2，原其他5项控制保持；只读场景的外部IO上限由私有测试夹具设置，不能描述为Agent设置成功。宿主内存8GiB/磁盘20GiB保留门槛不变。

该项不包含首次标定、DBS/HISDBS业务、宿主采集器成本或长期验收。开发版3a1ce7db的既有1800秒结果独立保留，不计入新程序。现有正式基线和七天组件不修改；未发布或宣称稳定版。
