# preview.5默认20%完整业务终态：未通过

同一个已发布preview.5程序、产品ced461705ebc27315a59aefe463f9b4af47130a3，任务8b61d73a06c79b99b7fdca8bc2a460b925f87e00b8a6089f1b1a9a948d787a39、计划7fdee53072afaef21e54450894d015f84267f1720976f05f3b1a946262752851。DBS、HISDBS顺序使用真实镜像、原路径、空配置{}默认三项20%、memory.high、自动最大合格文件系统三样本中位数、仅读写BPS，IOPS均为max。未改变原native/campaign/engine脚本、额度、300/45/600秒门槛或延迟/零错误/覆盖标准。

| 项目 | DBS | HISDBS |
| --- | --- | --- |
| 角色检查 | 7通过/1业务失败 | 7通过/1业务失败 |
| PG/API/受控就绪 | 27.25/29.32/55.15秒 | 见准确角色原件，受控63.03秒 |
| 实际native时长 | 600.248秒，完整计时但失败 | 343.329秒，中断，不计600秒完成 |
| SQL次数/错误 | 287/6 | 141/18 |
| SQL最大延迟/p95桶上界/计划覆盖 | 5.014秒/2秒/95.67% | 5.014秒/超过5秒桶/47% |
| API次数/错误 | 120/0 | 69/5 |
| API最大延迟/p95桶上界/计划覆盖 | 0.009秒/0.01秒/100% | 4.004秒/5秒/57.5% |
| 物理备份完成时间 | 34.742秒 | 54.432秒 |
| 引擎内容检查 | 十项完成，等待成功native验证 | 八项完成，standby停止超时 |

整体16项记录、14通过、2失败、无未执行角色检查。DBS的备份/同步/独立恢复十项内容检查完成且时间处于native窗口内，但包围它的native负载失败，所以仍为`content-passed-native-pending`，不能算完整业务通过。HISDBS已完成物理备份、流复制、独立恢复校验与逻辑恢复行数等八项内容检查，随后`pg_ctl`停止standby超过原30秒并返回“server does not shut down”，引擎回归失败后中断native；后续原PID/内容收尾检查未完成，不补算。

本次两角色的默认百分比和三项实际内核值正确，外部20GiB memory.max及另外四项控制值保持。DBS实际cpu.max480000/100000、memory.high13334654976、读13256766B/s/写9044830B/s；HISDBS同CPU/内存、读10309205B/s/写6115644B/s。标定样本离散提示保留，不把它们称为设备物理极限，也不把共享节点测试归因为单一资源。默认20%不是这两类负载已通过性能验收的推荐配额。

17:46:15 UTC的独立只读DBS瞬时补充快照中，cpu.stat的nr_throttled/throttled_usec均0，memory.high/oom/oom_kill事件均0，memory.current2309578752低于high13334654976；该节点不暴露PSI文件。此快照没有增加SQL、发送信号、修改限额或夹具，只描述当时状态，不能证明SQL超时的因果，也不能推广为HISDBS或全程无压力。首次PSI读取因文件不存在而失败的私有观察记录保留，随后按“不可用”明确记录。

节点2026-11-13 17:56:49 UTC另一个只读观察确认runner及两个driver原PID/start实例已消失，两namespace、两组父/叶cgroup及54个初始登记进程实例全部消失。最终环境清理不覆盖HISDBS原standby停止失败。终态exit1、完整artifact index绑定22份273848字节原件；逐项下载SHA/大小匹配、coordinator/角色报告/映射/设备及journal链一致。

[逐项终态及独立校验](test-results-bandwidth-default20-full600-terminal.json)、[22份精确原件和只读补充快照](test-evidence-bandwidth-default20-full600-terminal.json.gz)、[原冻结标准](testing-bandwidth-default20-full600.md)、[四种已完成启动组合](testing-bandwidth-current-combinations.md)。原980/1129/1170/576等失败保持，原52项/正式已发布升级/独占24h+24h/七天与硬件范围继续。该原业务对照fixture没有Kubelet liveness，不替代另行完成的精确探针启动组合；稳定1.0未接受。本轮不修改发布附件或生产环境。
