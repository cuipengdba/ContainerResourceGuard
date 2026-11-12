# memory.high 完整压力验收第四轮冻结源

这是[范围与历史失败](../../docs/testing-memory-high-pressure.md)、[冻结计划/逐项摘要](../../docs/test-plan-memory-high-pressure-v4.json)及[完整输入](../../docs/test-evidence/memory-high-pressure-v4-frozen.json.gz)对应的精确测试源码。固定新namespace、私有数据目录、显式隔离测试标记、精确发布preview.4及原私有厂商镜像/缓存/资格是必要条件。不得对原业务数据运行。

第四轮补齐测试适配器遗漏的源目录变量，启动前静态符号分析未发现核心或驱动的未定义全局，且全部帮助脚本/配额/时限/压力契约与此前逐一相等。前述准备错误及原证据保持。源码存在或静态检查通过不等于业务、压力或稳定验收通过。
