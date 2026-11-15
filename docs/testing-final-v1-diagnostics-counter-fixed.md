# 只读诊断执行器计数修订

原1448诊断执行器新增第10项检查后，末尾仍使用旧条件len(tests)==9。节点09:22:38只读观察发现DBS10项全通过、原生600.367秒业务/备份通过，但driver按旧计数退出1，协调报告相应失败；HISDBS当时8项初始检查及19项诊断子检查通过、原业务仍运行。不能把失败终态重标通过，也不能声称此计数错误证明产品业务失败。

原冻结14项输入不修改，原任务继续自然终态及清理，不为修订重启原Agent或中断HIS。新1465独立工具/目录/namespace/run ID把汇总条件改为冻结计划planned_checks，保持每角色10项/总20。诊断模块、ELF、worker、campaign、engine、端口观察、全部额度/15秒周期/业务300/45/600秒与PG超时/零错误/延迟/覆盖标准逐字节或对象保持；只增加前置守卫：原1448必须确认两组共20项实际全通过、原driver均因汇总退出1、业务/诊断原阶段通过并完全清理，才能进入修订轮。

不是遇错就盲目重跑或放宽标准；有确定的执行器根因，原失败按原样归档后才允许新的具名修订。新轮独立完成全部原600秒和清理，不能继承原1448业务秒数。当前仅冻结修订输入，未原生准入、未创建业务夹具或启动；P05.1/P07.2仍不提前勾选。

[原执行计划](testing-final-v1-diagnostics.md)、[修订计划](test-plan-final-v1-diagnostics-counter-fixed.json)、[准确可逆变化](test-adapter-final-v1-diagnostics-counter-fixed.json)、[新冻结输入](../tests/final-v1-diagnostics-counter-fixed/README.md)。产品源码及固定最终ELF不变，稳定1.0尚未接受。

原1448现取得[完整失败终态及准确原件](testing-final-v1-diagnostics-counter-failure-terminal.md)：20项实际主检查及38项诊断子检查通过，整体failed/退出1来自汇总计数错误，清理独立完成。修订1465新准入通过，尚未启动新轮。原失败不改判，完成数仍12。
