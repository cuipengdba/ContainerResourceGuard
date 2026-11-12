# memory.high验证与交付

用户已选择内存百分比使用memory.high；实现源码为e7b1a38c4fe5ad8ad237093c11cf8dc92b68c403，内存策略与升级合同见[设计](memory-reclaim-policy.md)。真实DBS/HISDBS镜像均在独立占位PID1容器中测试，不启动原业务、不挂载原数据；本项不等价两角色完整业务验收。

## 首轮失败保留

[首轮固定计划](test-plan-memory-high-v1.json)及[实际失败结果](test-results-memory-high-v1.json)保留。97的5.14内核、DBS镜像先通过五项：旧发布程序写256MiB硬限额、新版恢复512MiB运行时硬上限并写high、160MiB文件缓存夹具、high低于当前用量的真实回收、原值恢复。随后96MiB匿名工作集高于64MiB high时，容器内CLI等待超过35秒；HISDBS尚未运行，不计首轮整体通过。原runner/worker已退出，namespace和自有cgroup均已观测清理。

匿名工作集不可任意回收，high下的同步回收与分配节流也作用于Agent。产品不承诺写入时延有界。修订夹具从宿主只读观测自身测试组，确认high与用量/事件后仅释放已记录身份的测试分配进程，再等待CLI完成；不提高配额、不换memory.max、不据此声称无延迟。

[修订固定计划](test-plan-memory-high-v2.json)已经冻结，结果待取得；覆盖两原镜像的真实回收、原发布程序迁移、外部边界/冲突、新ID、恢复与只读降级。首轮源文件[保留](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/tests/vendor-memory-high.py)，修订使用[独立版本](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/tests/vendor-memory-high-v2.py)。

## Linux控制器回归

源码首次CI中，[原硬限额驱动两架构失败](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/43154931487)，均在manual-exact-three-actual-controls断言；原驱动仍期望memory.max并使用旧别名。该失败保留，不把旧44项结果改称新策略通过。新增native-cgroup-high.py使用规范memory_high及high期望，保留相同CPU/IO负载、恢复、ID、只读和清理检查；原native-cgroup.py逐字节保留。workflow按程序build-info的memory_policy选择匹配驱动，main旧程序仍使用旧驱动。新结果待取得。

源码Linux构建/竞态及原生ARM64测试已通过，但不代替实际控制器或厂商业务。旧策略的七天、24h、完整业务及其他稳定门槛仍保留原句柄和证据，新high策略需要自己的业务验证；本次仅工程预览交付。

## 第二轮日志缺项

[第二轮失败](test-results-memory-high-v2.json)保留：DBS九项通过，包括真实缓存回收、96MiB匿名工作集允许超过64MiB high且OOM计数不增、释放测试分配后CLI恢复、外部high和硬限额冲突保护。第十项发现每日resource_status未包含策略字段和计划警告；该项失败，HISDBS尚未运行。现已补充memory_policy与warnings，保持原日志轮转及其他行为；新程序另建固定计划验证，不把旧失败改成通过。两次失败的原namespace/cgroup及runner/worker均已观测退出。
