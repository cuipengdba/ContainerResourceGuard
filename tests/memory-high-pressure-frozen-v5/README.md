# memory.high 完整压力验收第五轮冻结源

[冻结计划/摘要](../../docs/test-plan-memory-high-pressure-v5.json)、[完整输入](../../docs/test-evidence/memory-high-pressure-v5-frozen.json.gz)和[说明及原失败](../../docs/testing-memory-high-pressure.md)对应的精确源码。测试适配器用[9项已测续租模块](../../docs/testing-pressure-SQL-lease.md)在原PG身份SQL执行期间维持原辅助租约，并保留原SQL超时、异常及辅助终态；测试间隔结束时间包含身份检查。原CPU/IO预算、所有帮助脚本、原600秒/SLA/11区间/32项框架不变。

一次性隔离夹具需要固定新目录、显式测试标记、精确preview.4、原私有镜像/缓存和前置资格。不得对原业务数据运行。启动前须确认第四轮失败/清理和续租资格终态；源码存在不等于业务或稳定验收通过。
