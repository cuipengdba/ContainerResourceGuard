# 已测诊断源码副本

这里九个文件来自[集成资格第二轮101项](../../docs/testing-native-diagnostics-v3.md)的精确输入，逐项摘要见[完整结果](../../docs/test-results-native-diagnostics-v3-v2.json)。包含worker、诊断模块、15项回调检查、28项新PG/模拟HTTP检查以及全部相邻加载依赖。旧源保持，副本不自动接入任何生产容器或现有长任务。

测试入口只允许Linux隔离新PG/模拟HTTP和显式测试标记；不要对现有业务数据库运行。资格启动器、原路径/镜像/bin/lib/share要求、预算、固定namespace/目录及inert/execute入口见[冻结第二轮计划](../../docs/test-plan-native-diagnostics-v3-v2.json)和[完整冻结源码](../../docs/test-evidence/native-diagnostics-v3-v2-frozen.json.gz)。应连同依赖放在同一全新私有目录，先核对摘要，再由专用资格夹具复制为UID999常规0400文件；源码在仓库可读不表示可绕过O_NOFOLLOW或原隔离条件。

本轮仅为工具资格；第一轮正常请求失败原因未证实，不能计为稳定性、600秒原厂商业务、受限IO因果或真实high压力通过。
