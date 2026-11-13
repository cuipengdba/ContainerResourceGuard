# memory.high完整业务及私有FIFO/准入联调

内存百分比只写memory.high，不设置新的memory.max。CPU、内存、IO各自默认20%，一容器一个Agent，v1跳过、权限不足继续业务，每日一个日志文件、30天及1GB滚动清理均保持。[preview.4公开下载](releases/v1.0.0-preview.4.md)及原八份附件、标签未改。high允许使用量超过目标，超出时回收和节流；业务工作集无法回收时可能变慢。外部硬上限和系统内存压力仍可能导致OOM，符合[内核文档](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory-interface-files)的语义。

## 原标准与实际结果

[结果JSON](test-results-full930-private-admission.json)、[原件压缩归档](test-evidence/full930-private-admission.json.gz)、[冻结源码](../tests/full-pressure-private-admission-frozen-v3/full-pressure-integration.py)一同归档。先在实际Linux完成Go顶层14项、原工厂17项、原件传输12项、真实私有FIFO工厂9项预检，再执行新的DBS/HISDBS隔离副本。core/native worker逐字节不变，原业务driver所有函数AST不变，仅隔离身份路径与接线更新；600秒每角色、全部11操作区间、32项主检查、零错误、原socket4秒/SQL5秒、64MiB负载、内存与IO配额均未放宽。

实际主检查记录32/32，通过32项；本轮业务接受=True。独立检查28/30通过，完整诊断接受=False。业务和诊断分别判定。记录缺失或尚未执行的项目不能视为通过。

| 角色 | 原业务秒 | SQL/API错误 | 原始事件 | 原始不完整 | 已准入不完整 | 角色诊断通过 |
| --- | ---: | ---: | ---: | --- | --- | --- |
| v10-dbs-bw64 | 600.213061 | 0/0 | 15839 | False | False | False |
| v10-hisdbs-bw64 | 600.312455 | 0/0 | 15756 | False | False | False |

独立检查失败项：dbs-private-FIFO-reader-drained-closed-cleaned-no-incomplete, hisdbs-private-FIFO-reader-drained-closed-cleaned-no-incomplete。准确事件、错误、边界数量、原生请求及逐项状态以JSON和原件为准。原始incomplete不会被已准入视图覆盖；完整诊断通过仍要求整段原始流完整，不能通过丢弃边界帧、过滤缺失返回或补造配对改判。

DBS首先记录transport-cleanup的Rejected，诊断必须失败。HISDBS仍运行时，另一次只读检查核对原init PID/start、pod UID、container ID及接收器目录dev/inode后，实际看到未登记的sitecustomize.pyc（9585字节）；其摘要和头部16字节随原始观察归档。receiver原代码要求目录内容严格等于其创建的sitecustomize.py和annotations.fifo，因此额外字节码文件会被拒绝清理。DBS目录当时已随原隔离容器消失，不能宣称读到了其额外文件或确证两个失败完全同因。

后续先独立复现真实解释器缓存行为，尝试只在匹配诊断命令的环境中禁用字节码写入，再验证实际Python2/3启动、原命令/异常保持、权限及清理负例。不会在运行中的930热改源码，也不会放宽目录身份或删除未登记文件来让清理检查通过。本轮失败原样保留。

首个离线分析还错误地从ready读取control_program_ids：ready只公开挂接程序和map，而控制程序ID在最终原始流及session summary中。该分析实际8/10项、两角色KeyError原件保留；修正仅改这一字段读取位置并重新分析同一批下载字节，不改变运行报告、阈值或清理失败判定。

第二次离线分析发现原件传输白名单只收json/log，没有包含新增的jsonl，实际22/26项并保留缺文件失败。原索引33份及其摘要不改：另外在同一终结任务中核对原report字节一致，再按原report的annotation_artifact长度与SHA256、文件类型、EOF及前后元数据只读补取两份jsonl，共61248字节。第二次分析原件本地保留，公开投影仅移除工作站绝对路径，同时保存原长度/摘要并明确投影不是原字节；最终分析使用同一35份真实原件，不重建注解，也不改运行结果。

## 接线与验证范围

内核、准入、严格配对、perf预算和排空源码保持已通过独立18项、注入17项及600秒/洪泛13项的冻结字节；vendor固定身份范围及其单元更新为本轮，重新编译Linux ELF并在真机验证。新ELF摘要与旧资格ELF分别归档，不能称两者二进制相同。仍为40个实际挂接程序、1个关闭控制程序、7个map，最多一秒准入排空、原150ms perf排空、20000事件/32MiB报告和16MiB perf映射预算不变。16MiB只限制perf mmap，不代表整个诊断进程的内存上限。

原镜像Python2自动激活shim、私有FIFO receiver均采用已验证的准确字节。只改匹配的原native命令环境，worker源码、调用次数、期限及成功判定不变。注解通过每角色独立非阻塞FIFO及宿主有界读取线程收集，不进入原业务stdout。下载的transport-annotations.jsonl原字节保留，逐条核对原请求窗口、run_id、迭代、4秒超时和事件发生时的精确收发端口；响应头不能替代原完整响应成功。通道停止、字节/记录上界、线程/FD/私有文件清理单独检查。没有注解、收发缺失、超界或排空失败都必须保留失败。

## 结束、归档与开放条件

同一任务终结后，59个报告注册进程实例及96个BPF程序/map对象，通过PID/start及完整BPF清单独立核对消失；namespace和报告记录的叶/父cgroup单独核对。真实SFTP下载35份原件，共48324339字节（原索引33份与额外2份分别记账），逐份核对长度、EOF及SHA256，完整UTF-8字节归档。冻结的全部文本与manifest公开，三个ELF仅公开长度和摘要；按manifest在同一目录重建，不混用版本。观察与下载未重启或热改任务。

[831原业务32项通过而诊断17/25失败](testing-fixed-null-full-pressure831.md)、历史API超时、旧夹具失败、原始边界和丢失全部保留。通过本轮不等于解释历史长write/API超时，不代表默认20%业务、真实OS线程号复用、隔离因果开销、正式24小时或七天604800秒/28周期与老化后置已通过。原52项定义与未完成声明保持；架构/内核/多设备和真实发布次版本迁移等剩余条件独立判定，稳定1.0未接受。
