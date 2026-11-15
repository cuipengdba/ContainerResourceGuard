# 固定最终候选：同一Agent业务热重载终态

2026-11-15节点08:43:12独立观察确认通过。沿冻结1429协议执行，准确源码 ced461705ebc27315a59aefe463f9b4af47130a3，最终AMD64 ELF 9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8。未重建产物、重置业务计时或放宽原标准。

| 角色 | 主检查 | 配置观察 | 实际业务秒 | SQL次数/错误 | API次数/错误 |
| --- | --- | --- | --- | --- | --- |
| normal-dbs | 9/9 | 13/13 | 600.498 | 300/0 | 121/0 |
| normal-hisdbs | 9/9 | 13/13 | 600.442 | 301/0 | 121/0 |

18项主检查与26次配置观察分别统计。每角色真实逻辑/物理备份、同步和独立恢复的10项内容检查嵌套于业务主检查，不重复累计。SQL/API满足原零错误、最大5秒、p95桶上界1秒及98%采样覆盖；原PG不重启、64MiB完整性与8阶段真实端口拥有者检查保持。

13场景包括manual转独立百分比、分别改比例、IO101/半截JSON/重复键/短缺文件/FIFO拒绝、ConfigMap链接恢复、等价空白显式reload确认、manual仅CPU移除自有high/IO、恢复manual三项、再转百分比及回原manual。每次全部8项内核值、accepted_hash、generation与状态均由准确原件独立复算。代次序列2,3,3,3,3,3,3,3,3,4,5,6,7。拒绝保留整份旧策略；第一有效切换与真实备份引擎重叠，所有观察位于各自原生600秒窗口。

Agent、PID1、CCG及PG保持；没有停止Agent再启动来模拟热重载。IO百分比仅改变读写BPS，自有手动IOPS恢复原值；百分比不使用标定IOPS。memory.high改变、外部memory.max及其余五项保持。复用三次真实标定profile，准确字节/mtime在运行观察和终态保持，业务中不重新测速。

独立检查runner和两个driver原PID/start均消失；两组namespace、父叶cgroup以及68条登记进程记录（52个唯一PID/start实例，含额外PG拥有者）全部消失。22份准确原件共520361字节逐份核对长度与SHA256、artifact index、source map及协调报告。协调报告SHA256：24ec1ad49b4919ba1a8c27a10eda871e230203db75f2325b4930c8aecb1a3803。端口扫描partial状态如实保留，不能将局部扫描写为全系统扫描完成。

两角色默认未生成metrics.prom/events.jsonl；status对应可选字段省略或null。另两次活HIS Agent快照无socket FD，不能宣称全程抓包。已开启导出及持续导出失败各1800秒/181样本由同一最终ELF既有独立开销原件复核：正常ready有本地输出，故障unavailable但控制保持managed；这是可选输出隔离证据，非新增厂商业务故障压测。[指标复核](test-results-final-v1-optional-metrics.json)、[默认导出观察原件](test-evidence-final-v1-default-exports.json.gz)、[准确源码unit/race事件复核](test-results-final-v1-reload-metrics-source-review.json)。

本轮使用manual参考启动并在业务中切换所列百分比，不能改判默认三项20%的历史完整业务失败。CLI优先、旧percent和类型边界由准确源码原生unit/race另证，不伪称本轮厂商CLI覆盖。删除自有high/IO和IOPS的运行证据已补齐；CPU删除、外部冲突等完整厂商组合仍保留在P03.5，不扩大范围。并发disable、掉电、热插拔和老化后故障未由本轮证明。24h+24h/七天仍待新候选真实计时，稳定1.0未接受。

[执行协议](testing-final-v1-business-reload.md)、[固定非二进制输入](../tests/final-v1-business-reload-frozen-v2/README.md)、[独立复算JSON](test-results-final-v1-business-reload-terminal.json)、[22份准确原件及终态观察](test-evidence-final-v1-business-reload-terminal.json.gz)。首版1425从未启动，原计划及启动时点快照仍保留。
