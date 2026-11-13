# 修复字节码清理与注解导出的完整复测

内存百分比继续只写memory.high，不新增memory.max，保留Kubernetes等外部硬上限。CPU/内存/IO独立百分比及各默认20%、每容器一个Agent、v1跳过、权限不足继续原业务、每日一文件/30天/1GB日志策略保持。[preview.4](releases/v1.0.0-preview.4.md)及其八份下载附件、标签未改。high回收和节流允许超额，不能保证系统或外部硬上限永不OOM。

## 独立复现与最小修复

[结果JSON](test-results-full950-bytecode-export-fixed.json)、[完整原件](test-evidence/full950-bytecode-export-fixed.json.gz)、[资格冻结源码](../tests/private-bytecode-export-frozen-v1/checks.py)及[完整接线源码](../tests/full-pressure-bytecode-fixed-frozen-v4/full-pressure-integration.py)一并归档。

原DBS和HISDBS镜像分别按准确image ID、pod UID、container ID和init PID/start绑定，使用独立占位pod，以原postgres身份、原Python2.7.5真实启动冻结shim和worker的--help路径，发一次自有loopback请求。没有启动原数据库服务或把它计为完整600秒业务。旧命令环境在两镜像均产生未登记sitecustomize.pyc，严格receiver以UNEXPECTED_CHANNEL_CONTENTS拒绝清理，负例按预期通过；额外文件只随测试pod销毁，未将其删除加入receiver。

修复只在精确匹配的诊断native命令前增加PYTHONDONTWRITEBYTECODE=1。receiver、shim、业务core/native worker逐字节不变，原Popen输入、原结果与异常保持。两镜像各验证正常、有界无读取端及已停止读取端三场景；环境来自实际factory的匹配命令重写前缀。正常仍收到一条原4秒请求注解，读端不可用时原帮助路径正常结束，未新增重试或业务成功标记。宿主Python3另实际验证默认会产生__pycache__并拒绝清理，禁用后不产生缓存且严格清理成功；负例缓存只由测试临时根目录整体拆除，不宣称receiver清除了未知文件。

资格实际22项通过，其中保留原工厂17项、真实私有通道工厂9项、原receiver18项、原传输12项，新增19项导出检查。导出器仅增加dbs-transport-annotations.jsonl与hisdbs-transport-annotations.jsonl两个准确文件名，各上界1MiB；原32MiB普通文件、256MiB总量、64文件及1MiB分块上界不变。新增检查覆盖两角色精确传输、截断、尾随字节、篡改、超界、其他名字/大小写/路径穿越，以及真实文件系统索引中的符号链接、硬链接、FIFO、过大文件和打开时inode替换。两角色原init及叶/父cgroup、资格namespace均独立确认消失。

## 原标准完整业务与诊断

新任务使用新隔离身份。Go仅修改vendor固定范围及其测试，重新编译并在真机预检14项；内核、准入、严格配对、perf预算和排空源码维持独立资格的准确字节。业务driver所有函数AST与原件相同，core/native worker逐字节不变。每角色600秒、11操作区间、32项主检查、64MiB负载、原socket4秒/SQL5秒、零错误、覆盖率、宿主保留量及指定CPU/IO/内存预算不改。环境及导出修复不会替代业务验收。

实际主检查记录32/32、通过32；本轮业务接受=True。独立检查30/30，完整诊断接受=False。独立失败项：无。缺失或未执行不能计为通过。

本轮两角色transport_channel均实际cleaned=true、读取线程/FD关闭且无incomplete，新增JSONL进入正式35份清单；原工厂仍将private-transport-channel-bounded-cleaned-and-original-native-exited判为false，所以整体诊断资格保持失败，不能用独立30项覆盖它。冻结core在native_exit==0后关闭日志并将self.worker=None，hook在原业务方法返回后才执行Observer.finish；该复合检查随后要求self.execution.worker非空。源码控制流和报告中的原native_exit=0共同定位到这个可变字段检查问题；运行没有额外采样finish时的字段值，不伪称有该动态快照。

下一步保留实际Popen返回的原子进程句柄，独立验证正常退出后字段清空、字段被另一个进程替换、子进程仍运行、原Popen异常、记录失败和重复调用等情形，再执行完整复测。不能简单去掉“原native已退出”的条件，也不修改core/worker或把本轮失败改判为通过。本轮32项、30项和工厂失败原件分别保留。

| 角色 | 原业务秒 | SQL/API错误 | 原始事件 | 原始不完整 | 已准入不完整 | 角色诊断通过 |
| --- | ---: | ---: | ---: | --- | --- | --- |
| v10-dbs-bw64 | 600.273264 | 0/0 | 16264 | False | False | False |
| v10-hisdbs-bw64 | 600.272904 | 0/0 | 15842 | False | False | False |

整段原始流的incomplete、全部边界/invalid和配对问题保留；已准入视图不能覆盖整段判定。仍使用40个挂接程序、1个关闭控制程序及7个map，最多一秒准入排空和原150ms perf排空、20000事件/32MiB报告、16MiB perf映射预算不变；16MiB不是整个诊断器RSS上限。控制程序ID来自最终原始流与summary，ready只提供挂接程序和map。

每条私有FIFO注解从正式导出清单逐字节下载，按原请求窗口、run_id、迭代及事件发生时的精确收发端口关联。注解不进入业务stdout，响应头不能替代原完整响应成功；清理失败、丢失、缺少收发、超界或排空失败均不能改判。未强制结束collector才可通过自然排空项。

## 原件、清理与开放条件

同一任务自然终结后，56个注册进程实例、96个BPF对象、namespace和报告记录的叶/父cgroup独立核对消失。一次正式清单真实下载35份原件，共48493981字节；逐份核对长度、EOF及SHA256，完整UTF-8字节归档，两份JSONL不再依赖额外补取。冻结全部文本和manifest公开，三个ELF只公开长度/摘要；按manifest重建同一平面目录，不混用资格/完整版本。观察与下载未热改或重启任务。

[930的28/30诊断及清理失败](testing-full930-private-admission.md)、其两次离线分析准备错误、[831配对/注解失败](testing-fixed-null-full-pressure831.md)、历史API超时和内核丢失等均原样保留，不重评旧结果。新结果不等于解释历史长write/API超时或证明隔离因果开销，不能替代默认20%业务、实际OS TID复用、正式24小时、七天604800秒/28周期与老化后置、架构/内核/多设备和实际已发布次版本迁移门槛。原52项定义与未完成声明保持，稳定1.0未接受。
