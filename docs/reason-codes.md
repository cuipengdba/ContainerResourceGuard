# 逐项原因码（开发功能）

next/local-diagnostics 的 items[] 新增可选 reason_code，human 输出展示同一字段。旧字段 state/detail 保留；旧版本保存的状态可能没有原因码。原因码来自具体判断分支，不解析英文错误文本来决定重试、控制权或安全性。当前覆盖逐项施加、恢复和保留结果；容量/profile 警告、命令级错误及重载错误还保留各自既有字段，不能称所有错误都已统一编码。

| reason_code | 含义与处置 |
|---|---|
| observe | 只计算，不写入 |
| applied / unchanged | 已写入并回读 / 已为目标值 |
| invalid_request | 请求不是允许的控制项或有效值 |
| device_identity | 无法确认 IO 设备身份，不写或恢复 |
| controller_read / controller_recheck / controller_verify | 原值读取 / 写前复查 / 写后回读失败；检查权限和内核接口 |
| unrestorable_original | 原值格式不能安全保存和恢复 |
| external_conflict | 外部值或设备身份冲突；保留当前值，显式审阅 |
| memory_window | 等待跨周期内存安全窗口，尚未下调 |
| memory_safety | 内存用量、增长、压力、事件或必要统计不适合下调 |
| task_safety / swap_safety | 当前任务数 / Swap 用量不适合下调 |
| journal_intent | 写意图未成功持久化，未发起该次控制写入 |
| controller_write | 内核写入失败，意图保留供恢复 |
| journal_finalize | 控制已写入，但最终日志同步失败；不能认定全部完成 |
| restored | 已回到保存的真实原值 |
| restore_incomplete | 恢复路径其他失败；结合 detail 和实际值判断 |
| observe_retained | observe 保留此前已写入的限额 |
| plan_unresolved | 本次仍请求该控制，但计划无法解析；保留旧限额 |

逐项 applied/restored 也不能替代数据库健康判断。诊断白名单不复制任意 detail 错误原文；这里未增加网络端点。后续新增原因码按附加字段兼容，调用者必须允许未知码并结合 state 处理。
