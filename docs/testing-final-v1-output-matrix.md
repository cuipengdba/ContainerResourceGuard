# 固定最终候选：完整CLI输出组合验收

状态：12项输入已冻结，19项本地核对及原生只读准入通过，尚未启动或创建业务夹具。当前17/52保持，P07.1不提前接受。

原DBS/HISDBS镜像、启动逻辑、路径、只读CCG、缓存与数据库参数保持；分别新namespace/输出/run-id。每角色13项主检查、14项在线输出子检查，总26/28；每角色10次status观察、6次配置转换、3种只读profile/路径场景。全部在线操作须位于各自新的成功原600秒SQL/API内，原零错误、最大5秒、p95桶上界1秒、98%覆盖率及64MiB内容和PID1/PG/缓存不变。每次转换仍限60秒，没有缩短原业务时长或放宽门槛。

固定源码ced461705ebc27315a59aefe463f9b4af47130a3及最终AMD64 ELF9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8保持。初末manual为7.2CPU/high20001980416B/双向64MiB每秒/手动4096IOPS，外层8CPU/20GiB。初始配置仅将观察间隔从15改为1秒，已在前次重载验收中实际使用。原生worker/campaign/engine/helper字节不变。

1. 初始manual实际JSON/human与目标、内核读回一致。
2. 同Agent切换独立50/50/100：按可信24核/66673278976B基数与原值、全部可见祖先及cpuset独立计算，CPU/内存被既有上层额度裁剪，核对两条约束警告。只改当前leaf，不写父组或memory.max。
3. 切换25/29/80，核对三个独立比例及原三次标定profile的BPS百分比；IOPS恢复自有journal记载的外部原基线，不能以IOPS标定值推导硬限额。
4. 非法IO101和坏JSON保留上一代有效hash/generation/plan/控制；空白格式变化显式reload确认request_id但不增加有效策略代次。六次代次为2/3/3/3/3/4，最后回到原manual。
5. 通过独立私有配置实际doctor/preflight核对profile缺失、设备身份不匹配、/proc未覆盖。只读取当前业务容器视图，不改活动profile/config/journal/控制，也不运行标定。
6. 将当前测试leaf的CPU写为预先记录的原值800000 100000，比自有720000 100000宽松；连续两次看到external_conflict及实际外部值保留，不覆盖。随后显式disable，原值相等分支安全消除冲突、还原其余控制并清空自有journal，再enable恢复一个最终ELF写入者。无journal编辑、父组写入或业务重启。新Agent代次回到1，原有效配置hash保持。
7. 成功原600秒后再disable，全部8项运行时原值及空journal保持，原配置与profile字节/mtime保持；清理自有进程/两namespace/父叶cgroup独立确认。

## 输出字段契约

| JSON内容 | human含义 |
| --- | --- |
| plan.percentages / resource_mode | Requested的三个独立比例或manual摘要 |
| environment.host_online_cpus / host_memory_bytes / cgroup | Host与自身Cgroup |
| plan.settings / warnings | Target与原样约束警告 |
| io_devices / data_paths | IO device与Data path的状态、原因和覆盖 |
| items.state / reason_code / detail | Result对应状态、原因码和解释 |
| actual.value / state | Actual内核读回，不能把目标当实际值 |
| state / mode / snapshot_age_seconds / writer_lock_held | State摘要；不能据此推断数据库健康 |
| configuration.generation / accepted_hash / state / source / request_id / error | 当前为JSON专有字段，human未打印这些字段，不声称同名行存在 |

human与JSON共享内容必须含义一致，不要求字段数量相同。快照年龄和锁与持续SQL/API业务结果分别验收。状态读取在稳定快照前后核对字节/mtime，允许独立内存采样和自然年龄变化。status通过已有--state-dir入口读取持久状态，不用坏配置作为状态命令的解析前置。doctor/preflight基于当前实际leaf限额生成只读计划，活动status基于Agent记载的原值生成计划，两者用途和基数不同，不强行比较计划相等。

复用原三次标定profile00e35e91594ed0ad1075a196c20bd8f4c6628c346c4bd6e901ac05d4cc90ef6b；原生profile-check确认设备身份resolved，但不证明当前物理性能。报告保留读IOPS波动警告；本轮仅按BPS，不能据此宣称测速总量固定或IOPS性能通过。

1545初稿在上传前发现status显式坏配置入口不合适，原字节及拒绝归档保留；1551修订后12项输入只上传一次。首轮额外原生检查误用不存在的--profile而退出，改用已存在的--io-profile后只读重检通过，不重传或改动冻结输入，未启动/重启任何业务。失败与修订原因如实存档。

准入同时核对1465的71、1501的64和1525的55条已登记实例及其runner/driver/namespace/父叶全部消失，并确认没有其他最终候选业务任务并行。需28GiB可用内存/20GiB磁盘，运行保留8GiB内存余量。旧七天任务原PID/start继续保留；1396正式长测仍未启动，时长不转记。

本轮不补算默认20%业务性能、未来格式、镜像持久化、故障压力、ARM厂商、多独立物理磁盘或长期老化。当前公开preview.5保持，稳定版未接受。

[完整计划](test-plan-final-v1-output-matrix.json)、[准确输入](../tests/final-v1-output-matrix-frozen/README.md)、[本地核对](test-results-final-v1-output-local-preflight.json)、[原生准入](test-results-final-v1-output-native-preflight.json)、[只读检查程序](../tests/final-v1-output-matrix-preflight.py)、[完整适配](test-adapter-final-v1-output-matrix.json)、[上传前拒绝](test-results-final-v1-output-preupload-rejection.json)、[首轮准入错误](test-results-final-v1-output-first-preflight-failure.json)、[命令修订](test-results-final-v1-output-preflight-correction.json)、[前置1525终态](testing-final-v1-cli-supervisor-terminal.md)。
