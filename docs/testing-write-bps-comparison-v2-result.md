# 写带宽对照 v2：两组失败，一组通过

[冻结计划](test-plan-write-bps-comparison-v2.json)、[实际终态与摘要](test-results-write-bps-comparison-v2.json)、[可重复离线分析](test-analysis-write-bps-comparison-v2.json)共同绑定此次结果。节点2026-11-11T16:43:01Z独立终态核对时，原runner176383/start135319371及worker176395/start135319375已经退出。协调器退出0表示三组执行结束，业务并非全部通过。

| 组 | 主策略写BPS | 实际原生时长 | SQL尝试/错误 | API尝试/错误 | D样本 | 组内主检查 |
|---|---:|---:|---:|---:|---:|---|
| A1 | 37470104 | 600.267秒 | 293/4 | 121/4 | 22 | 13局部；原生失败 |
| B | 67108864 | 600.241秒 | 301/0 | 121/1 | 9 | 13局部；原生失败 |
| A2 | 37470104 | 600.226秒 | 299/0 | 121/0 | 5 | 16项组内通过 |

三组均为DBS独立完整冷副本、manual模式、64MiB原生载荷和11个原重载/压力区间；第二策略与启动策略在三组中相同，详见计划。不是全程恒定上述写BPS，不能以表中数值覆盖原策略切换。原百分比/32项/DBS和HISDBS两角色验收没有执行，A2的16项不能冒充32项通过。原始首轮夹具错误、R235及其他历史失败继续保留。

## 结果能说明什么

B的SQL错误少于A1，但仍有API超时；A2恢复同一低上限后通过，**没有形成预定的A重现、B改善、A重复失败模式**。因此不据此提高默认额度、不修改标定结果、不认定写带宽是唯一原因，也不声称原失败已修复。顺序组共享后端，缓存/写回状态未重置或随机化，新副本inode/cgroup和时点不同；这些边界从执行前即已记录。A2的SQL最大4.841秒、API最大1.394秒仍按原5秒/错误0/p95≤1秒/覆盖≥98%判定，不缩小负载或放宽门槛。

A1的4次SQL超时重试同一iteration50/首key801，首次后端的5个样本为LWLock/WALWrite，之后三个重新连接后端各5个样本为LWLock/BufferContent。分析按PID、backend_start、连接观察时点及PG采样边界筛选；这些LWLock样本的blocking_pids未测，null不等于已证明没有阻塞者。4次API超时各严格重叠4个D样本；不能因此证明该线程就是请求执行者或持锁者。

三组D样本均实际捕获write到/opt/dbs/log/DBS.log。A1同一TID22样本跨约21秒，栈含folio_wait_writeback、truncate_inode_partial_folio及XFS缓冲写路径；B为9样本跨约8秒，A2为5样本跨约4秒，后两组栈含__filemap_get_folio及XFS缓冲写路径。样本跨度不是完整连续等待时长。B唯一原生API错误严格重叠4个D样本；A2存在D样本但原生请求没有失败。

三组每组另有10项引擎内容检查；引擎自己的API探针分别3/2/0条失败或外层超5秒，与原生请求计数分开。A1/B引擎phase仍content-passed-native-pending，A2的独立组内原生判定已完成。CPU节流时间增量、memory.events各项增量均0；PSI全部不可用，保持unknown。io.stat按253:0和8:0分别列出，不能相加当作两盘或把计数速率当成物理完成带宽。短时速率超过io.max也不直接证明限额失效。

## 退出、恢复和证据复现

三组namespace/cgroup、各组固定PID/start_ticks的原生worker、API进程及观察器均独立确认消失；配置原始SHA和profile缺省状态恢复，源config/pg_control/程序SHA保持且源postmaster.pid仍不存在。副本与失败现场保留。原生worker均自然结束，最终收尾0 TERM/0 KILL；线程观察器按原会话在600秒结束后停止，原始phase=incomplete/observer-interrupted、每组601样本，不冒充900秒观察完成。

每组五份原始结构报告（main/native/request-PG/threads/engine）以gzip归档，共15份，未公开业务日志内容。组内manifest固定原始SHA256/字节数，终态索引另记gzip摘要。[分析源码](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-write-bps-arm-analysis.py)只读本地文件，以O_EXCL/0600输出新结果；不连接节点、不发信号、不读实时proc、不写控制项。完整仓库中执行：

```bash
python3 tests/vendor-write-bps-arm-analysis.py --directory docs/test-evidence/writebps272/a1 --arm a1 --output /tmp/crg-a1-analysis.json
python3 tests/vendor-write-bps-arm-analysis.py --directory docs/test-evidence/writebps272/b --arm b --output /tmp/crg-b-analysis.json
python3 tests/vendor-write-bps-arm-analysis.py --directory docs/test-evidence/writebps272/a2 --arm a2 --output /tmp/crg-a2-analysis.json
```

[8项实际离线检查](test-results-write-bps-arm-analysis.json)覆盖三组压缩/未压缩/重复输出逐字节一致、三组已有输出拒绝覆盖、实际PG身份与等待匹配、错误组输入/摘要/解压超过32MiB拒绝。运行环境为Windows/Python，属于证据分析检查，不充当Linux产品资格或业务接受。后续先补齐同时间轴的只读设备状态及PG实际路径等待采集资格，再决定完整业务复测；不盲目重复改额度，具体约束见[后续诊断计划](plan-post-write-bps-diagnostics.md)。

preview.2程序、现有长测handle与计时均保持；稳定1.0、原24h+24h、真实604800秒/28周期及老化后置仍未接受。全部52任务原定义及completion_claim=false保持。
