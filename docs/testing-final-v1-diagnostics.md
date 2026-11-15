# 固定最终候选：厂商只读诊断与内存统计补验

准确产品源码ced461705ebc27315a59aefe463f9b4af47130a3，v1.0.0 AMD64 ELF摘要9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8。输入已冻结，原生只读准入通过；尚未启动本轮业务，不能计为诊断或业务通过。

为P05.1/P07.2补齐最终ELF现场证据。两角色各全新隔离namespace/Pod/目录，使用原镜像、真实路径、原启动链和缓存程序，每容器一份Agent。沿原manual参考7.2CPU、memory.high20001980416字节、64MiB/s双向BPS/手动IOPS4096及默认15秒周期；外部8CPU/20GiB和其余五项保持。不测试默认20%性能，不触碰旧七天任务。

先执行诊断检查，再按原标准测量完整600秒SQL/API与实际备份/同步/独立恢复。每角色原9项加1项诊断主检查，共20项；诊断子检查单独列出，不重复累计。原300/45秒启动、600秒、零错误/最大5秒/p95桶上界1秒/覆盖98%、64MiB数据、PG原命令及停库超时、8阶段PG拥有者和共享节点28/8GiB内存与20GiB磁盘保护全部保持。

诊断执行前公开内容说明：只包含平台、已确认宿主容量、最多64项控制结果和本容器内存计数；不包含配置原文、路径、身份、journal原值、环境全集、凭据或业务内容。通过CLI传入虚构私密标记，检查标准输出/本地文件白名单及标记排除；每份最多65536字节、本地新文件0600。尝试覆盖已有文件、符号链接、状态文件和profile均应拒绝，原件不变；不自动上传诊断包，测试完成后仅导出预先列明的白名单原件。

对照本叶memory.current、swap.current、stat、events及PSI，核对字段可用性、字节/百分比/微秒单位和缺失为null/不可用，不用0伪造统计。内核计数是分时采样：events按单调前后包络核对；变化的内存gauge不要求不同时间读取数值相等，同值端点比较仅记录，不能宣称原子快照。anon/file/kernel及shmem/slab等可能重叠，不另造可相加总量；独立HugeTLB控制器统计不冒充memory.stat字段存在。异常/缺失解析语义另由准确源码原生unit/race支持。

诊断前后全部8项控制、journal摘要、Agent/PID1/缓存和PG启动时间保持；之后完整业务终态独立验收。最后确认runner、driver、登记PID/start、父叶cgroup及namespace消失。任一失败保留准确原件，不自动重跑、加额度或放宽规则。老化、物理掉电、厂商ARM、多物理盘及长期验收不由本轮代替。

[固定计划](test-plan-final-v1-diagnostics.json)、[原生准入原件](test-results-final-v1-diagnostics-preflight.json)、[可逆适配](test-adapter-final-v1-diagnostics.json)、[非二进制准确输入](../tests/final-v1-diagnostics-frozen/README.md)。前轮[热重载终态](testing-final-v1-business-reload-terminal.md)已通过，不将该轮计时移记本轮。稳定1.0尚未接受，公开下载仍为preview.5。
