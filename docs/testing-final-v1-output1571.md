# 固定最终候选：修订输出组合1571

状态：12项输入冻结，22项本地检查、原生只读准入通过；未启动，不计通过。17/52保持，P07.1仍待。

1551的[原失败及全部原件](testing-final-v1-output-matrix-failed.md)保持不变。本轮仅修正测试聚合状态：存在已核对plan.warnings、拒绝配置或external_conflict时应为degraded；无这些原因时应为managed。两角色真实失败响应回放及反例验证已纳入本地检查。警告不代表应用失败，也不能替代各控制applied/unchanged、目标/内核值精确相等的检查。生产源码ced461705ebc27315a59aefe463f9b4af47130a3和最终AMD64 ELF9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8均不变，不重建。

在新namespace、输出目录、run-id各独立执行原600秒DBS/HISDBS SQL/API；原镜像/启动路径/PID1/PG/缓存和业务worker保持。零错误、最大5秒、p95桶上界1秒、98%计划覆盖率、64MiB内容及原600秒均不放宽。共26主检查、28在线子检查；每角色10次状态视图、6转换、3只读覆盖场景，在线操作必须全部位于成功原600秒内。

初末manual7.2CPU/high20001980416B/双向64MiB每秒/手动4096IOPS，外层8CPU/20GiB；仅观察间隔15改1秒。百分比50/50/100裁剪到已有上层额度，并精确核对两条CPU/内存约束警告；再切换25/29/80。坏IO101/坏JSON保留上一策略和代次；空白格式reload不增有效代次；最后回manual，六转换代次2/3/3/3/3/4。复用原三次标定profile，不重新测速，BPS百分比不推导IOPS硬上限。

实际human/JSON共享字段核对请求、主机基数、自身cgroup、目标/读回/原因、警告与profile/路径覆盖、年龄与写锁。configuration代次/hash/state/source/request_id/error仍是JSON专有字段。status用--state-dir绕开坏配置解析；doctor/preflight用当前leaf基数，与Agent的原值计划不强行等同。

独立私有配置只读检查profile缺失、设备身份错误、/proc未覆盖，不改活动profile/config/journal/控制。仅在自有隔离leaf把cpu.max写为预先记录原值800000 100000，连续两次核对external_conflict且外部值保留；显式disable/enable通过既有原值相等分支恢复，不改journal、不写父组或memory.max，不重启业务。新Agent代次1，配置hash不变。成功600秒后disable，八项原控制/空journal及配置/profile字节mtime核对，再独立清理。

新runner启动前核对失败1551整体failed/exit1及准确report SHA、全部56登记实例/runner/driver/两namespace/父叶已消失；同样保留1465的71、1501的64、1525的55原成功前置，不把失败短时计数继承。本地原1551十二输入摘要不变。旧七天任务保留，正式1396仍未启动，时长不转记。

本轮不宣称默认20%业务性能、未来格式、镜像持久化、ARM厂商、多独立物理盘或长测完成。稳定1.0未接受，公开preview.5保持。

[计划](test-plan-final-v1-output1571.json)、[本地22检查](test-results-final-v1-output1571-local-preflight.json)、[原生准入](test-results-final-v1-output1571-native-preflight.json)、[全部适配](test-adapter-final-v1-output1571.json)、[准确输入](../tests/final-v1-output1571-frozen/README.md)、[准入源码](../tests/final-v1-output1571-preflight.py)。
