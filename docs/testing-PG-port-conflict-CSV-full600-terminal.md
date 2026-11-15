# 修正CSV后的真实PG冲突与完整600秒终态

修正CSV来源后的新套件通过：计划44项，记录44项、44通过、0失败、0未执行。先前套件18记录/16通过/2失败/26未执行仍为失败，不追认。本轮全新四个namespace/Pod/container ID及私有数据目录，未替换或重跑旧结果。

| 组别 | 通过/记录 | native实际秒数 | SQL次数/错误 | API次数/错误 |
| --- | --- | --- | --- | --- |
| conflict-dbs | 13/13 | 预期冲突，engine仍failed | — | — |
| conflict-hisdbs | 13/13 | 预期冲突，engine仍failed | — | — |
| normal-dbs | 9/9 | 600.277 | 301/0 | 121/0 |
| normal-hisdbs | 9/9 | 600.269 | 301/0 | 121/0 |

冲突组仍要求实际物理备份后PG启动失败、engine保持failed/非零退出。stderr重定向提示和current_logfiles指定的实际CSV分别保存；全部CSV记录须属于本次启动PID/时间窗，准确日志含55432 bind/address-in-use。受控占用者在失败与cleanup后保持，只有明确本轮EOF才移除；原primary启动时间、API、PID1和两helper身份及配额均核对。

正常组沿用原每角色完整600秒、SQL/API零错误、最大5秒/p95桶1秒/计划覆盖98%、64MiB内容校验及真实PG备份/同步/独立恢复十项要求。每个内容周期必须处于成功native窗口；不能单以内容通过抵消native错误或中断。另核对standby55432/restore55433真实postgres拥有者的cgroup/cwd及启动、停止、cleanup八阶段。具体原始指标与每项真假见机器报告，不将本轮manual预算当作默认百分比性能。

端口扫描保留原始partial状态（扫描期间有进程消失）；限定断言只使用已实际核对的本轮占用者/PG拥有者和稳定目标身份，不能称所有扫描完整或证明PID复用。原始问题字段保留，不补造缺失记录。

实际仍用公开preview.5 ELF，源码`ced461705ebc27315a59aefe463f9b4af47130a3`，manual7.2CPU/memory.high20001980416B/读写64MiB/s/手动IOPS4096，外部8CPU/20GiB及原PG超时不变。44份白名单原件571921字节逐项摘要匹配；134条登记进程记录（110唯一PID/start实例）、原runner/全部driver、已创建namespace及每组父叶cgroup均由终态后独立只读观察确认消失。

[逐项结果及独立复核](test-results-PG-port-conflict-CSV-full600-terminal.json)、[准确原件与终态回执](test-evidence-PG-port-conflict-CSV-full600-terminal.json.gz)、[冻结计划/源码](testing-PG-port-conflict-CSV-full600.md)、[首次失败及独立实际CSV诊断](testing-PG-port-conflict-terminal.md)。job `61e0ab046295950d63dc53e46e888a6702b42129f1252e940afd9520584475f7`，plan `2f80abd5d869e17d7d0f6794255a5f71fd38fd49a1fe5e1ef139276779ff682a`。只导出明确白名单，不导出私有Pod/env/数据库凭据。

本轮是共享amd64/Linux5.14单设备环境的manual参考预算限定回归。此前默认20%完整业务失败仍保留；48/48默认百分比控制迁移、40/40公开维护及其他来源证据各自保持。新源码的独占24h基线+24h限额与至少七天、原52项逐项审核及硬件支持边界继续，稳定1.0未接受。下一步先冻结当前实际产物及独占长期计划，重新核对节点与无其他业务测试夹具的门槛；旧preview.4约30h失败时长不能计入新版本。
