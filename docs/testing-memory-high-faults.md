# memory.high 发布程序的辅助故障复验

[冻结计划](test-plan-memory-high-faults.json)使用已发布的v1.0.0-preview.4、生产源码180c86ad与ELF6088721c，须先核对其自身[三场景1800秒开销](testing-memory-high-overhead.md)和[DBS/HISDBS各600秒真实路径业务](testing-memory-high-business.md)的实际终态、固定作业摘要、退出0及独立清理；不能把计划或旧硬上限程序的结果记为本版通过。

每个角色依次验证缺失、无效配置、崩溃、卡住、忽略TERM、撤销、cgroup只读、profile只读、state只读、真实标定取消，共20场景/108项。保留原镜像/start.sh、PG参数、只读缓存程序、真实容器路径和单容器单Agent，使用新私有隔离背板及loopback DCS。沿用原DB/API90秒、缓存随后45秒、TERM12秒门槛；30%配置只用于辅助故障隔离，不代表其持续业务性能已经接受。

新增核对只允许CPU、IO与memory.high三个资源，外部memory.max及其他值保持。profile只读时CPU/memory.high可成功而IO因无法保存标定结果跳过；其余故障场景应在首次资源修改前停止。取消标定须真实观察同一发布Agent持有自己的标定临时文件FD，核对程序摘要后通过pidfd发送TERM，并确认无profile和资源修改；不以伪造标定器代替。

冻结阶段尚无通过结论。测试记录自身Pod UID、父/叶cgroup和原进程PID/start ticks，结束后独立核查这些身份是否消失。新策略实际回收压力、脏页及受限IO、默认百分比业务、老化故障和长期门槛仍单独开放；原52项未完成状态和稳定发布条件不改变。

## 首轮预期值计算错误保留

[原始失败及独立清理](test-results-memory-high-faults-v1.json)保留：20场景执行完毕，18个场景完整通过，两角色profile只读场景在测试额外控制值断言失败。测试漏算了内存页向下对齐，产品实际memory.high=20001980416B，CPU和外部硬限额等值均符合原设计；不能改记首轮108项通过。两个原协调器、20个Pod父/叶cgroup和已记录原进程已独立核查消失。

[第二轮冻结计划](test-plan-memory-high-faults-v2.json)仅修正测试期望值按宿主实际页大小对齐，并使用新目录及namespace，发布程序、30%请求、20场景/108项与原90/45/12秒标准不变；新结果尚未取得。
