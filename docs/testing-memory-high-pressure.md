# memory.high 原厂商热更新及真实内存压力验收

本计划使用实际发布的 preview.4（source 180c86ad、ELF6088721c），每个 DBS/HISDBS 容器只运行自己的一个 Agent；独立新数据目录、原真机挂载路径及原 start.sh/PG 参数/只读缓存挂载。不是生产部署命令，不对现有数据运行。

用户已选择百分比写 `memory.high`。它是回收与节流目标，允许短时超过；Kubernetes 20GiB 的原 `memory.max` 保持。这里不新增硬上限、不强制释放应用堆、不写 drop_caches，也不承诺整个系统不 OOM。

## 冻结范围

保留原32项框架：每角色两项原启动与缓存检查、11个热更新区间、600秒包围/进程身份两项及显式恢复一项。唯一内存语义调整是将旧 memory.max 的“压力时拒绝写入、释放后重试”两项，换成“真实超过20%目标时 memory.high 生效并出现 high 事件、释放后同一配置代际恢复”。这是用户需求对应的新检查，不能表述成旧硬上限检查原样通过。

- 原 CPU/IO 预算不变：A为30/30/100%，7.2核、20001980416B、设备253:0的64700080/37470104 B/s与83/135 IOPS；B为25/29/80%，6核、19335249920B、51760064/29976083 B/s与66/108 IOPS。
- 启动300秒、缓存就绪后45秒且总计300秒；两角色各实际600秒、64MiB数据、SQL每2秒/API每5秒、请求上限5秒、错误0、P95桶不超过1秒、覆盖率98%。原十项备份/流复制/独立恢复必须全部完成并位于本角色600秒内，从负载第30秒启动。
- 测前宿主可用内存28GiB、持续8GiB、磁盘余量20GiB。压力辅助最多12GiB、64MiB增量、10秒租约、240秒寿命、准备60秒；首次 memory.current 必须高于20%目标13334654976B加256MiB，且组内低于30%旧目标减2GiB。
- high生效60秒、保持6秒、memory.events.high必须增加、oom/oom_kill为0；释放后60秒内按原5%+16MiB余量恢复，同一已接受generation7及配置hash且不重写配置。其他七项控制保持，最后停用须恢复真实八项运行时原值。
- 保留原线程、设备、逐请求和PG等待诊断；使用[已测九份v3/PGv2源](../tests/diagnostics-v3-frozen/README.md)。诊断失败保留，原业务错误优先，不改变原请求超时或结果；失败后的pidfd精确负载进程收尾最多120秒，不是额外合格测量时间。

完整数值、依赖摘要及原32项源摘要见[首次冻结计划](test-plan-memory-high-pressure.json)及[首次全部源码](test-evidence/memory-high-pressure-frozen.json.gz)。只接受本次实测来源，旧硬上限失败、ABBA和default20%失败不被抵消；101项工具资格也不替代业务验收。

## 首轮准备失败

[原始结果](test-results-memory-high-pressure-v1.json)记录四项启动检查通过，两角色均在 EDGE_TIMED_API_COPY 退出。测试适配器传递脚本时缺少 kubectl exec -i，非空标准输入未被转发；实际复制后摘要未保存，不能补造。两角色均未启动native、引擎或压力。独立观察确认两个Pod父叶cgroup、原进程、namespace及协调进程消失，配置原字节/profile缺省恢复。该轮不计完整业务通过。

## 第二轮

[第二轮冻结计划](test-plan-memory-high-pressure-v2.json)与[完整源码](test-evidence/memory-high-pressure-v2-frozen.json.gz)只修正测试适配器的stdin转发，并使用新的目录/namespace/run ID，逐个核对原帮助脚本字节不变。原配额、所有上述标准及32项结构保持。启动前还要求首轮退出1及独立清理证据。第二轮只启动了外层runner，其摘要断言在创建business worker前拒绝，实际没有进入业务；[失败与原stderr](test-results-memory-high-pressure-v2.json)保留，namespace不存在、runner原实例消失。

[第二轮精确测试源副本](../tests/memory-high-pressure-frozen-v2/README.md)用于审阅；公开产品包保持原发布资产，不因测试夹具变更而重打标签。


## 第三轮

[第三轮冻结计划](test-plan-memory-high-pressure-v3.json)、[全部输入源](test-evidence/memory-high-pressure-v3-frozen.json.gz)及[精确源码副本](../tests/memory-high-pressure-frozen-v3/README.md)只修正启动器摘要绑定，精确替换路径/namespace/run ID，不再全局替换数字；启动前逐个核对全部帮助脚本摘要、CPU/IO数值、原native标准和high压力契约相等。首次本地绑定检查还发现退出记录内残留旧摘要，已在首次第三轮启动前一并修正并再次验证。前两轮失败不覆盖。第三轮仍在准备阶段失败：[四项启动检查与原NameError](test-results-memory-high-pressure-v3.json)保留；抽取的方法引用here但新适配器未定义它，native/引擎/压力未开始，两角色原进程及namespace/父叶cgroup独立清理且配置/profile恢复。


## 第四轮

[冻结计划](test-plan-memory-high-pressure-v4.json)、[完整输入](test-evidence/memory-high-pressure-v4-frozen.json.gz)及[精确测试源](../tests/memory-high-pressure-frozen-v4/README.md)补齐源目录变量，静态符号表分析确认核心/驱动无未定义全局，精确核对全部帮助脚本、原CPU/IO/SLA和压力契约不变。第四轮已进入DBS原启动链和600秒native活动，最早快照仅两项启动检查；这不是完整压力、两角色业务或稳定1.0通过，实际终态另行归档。前三轮失败保持。
