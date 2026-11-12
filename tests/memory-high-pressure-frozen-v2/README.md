# memory.high 完整压力验收第二轮的冻结源

此目录为[冻结计划](../../docs/test-plan-memory-high-pressure-v2.json)中测试驱动、压力核心及全部相邻Python依赖的精确副本。摘要逐项见计划；运行时还依赖精确发布preview.4二进制、资格JSON、原镜像/原私有缓存程序、专用隔离节点上的预建来源及固定新目录。完整输入见[冻结源码归档](../../docs/test-evidence/memory-high-pressure-v2-frozen.json.gz)，范围和预算见[测试说明](../../docs/testing-memory-high-pressure.md)。

入口固定一次性namespace、新路径、显式授权测试标记和原前置资格；不能直接在业务库运行，不能复用既有目录或修改冻结门槛。这里不是随产品启用的后台程序。首轮准备失败保留，本轮尚未完成，不能据源码存在推断验收通过。
