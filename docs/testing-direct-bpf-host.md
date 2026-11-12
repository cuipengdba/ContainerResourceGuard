# 直接BPF事件采集：自建探针14项通过

为继续排查[第五轮high压力业务](testing-memory-high-pressure.md)中DBS/HISDBS各一次API超时，新增独立Go诊断工程。此前[perf文本管道四轮失败](testing-perf-metadata.md)及全部原始业务失败保留，配额、请求时限、600秒和零错误标准不变。本次没有再次运行厂商业务，也没有修改CRG产品、发布标签或下载文件。

## 本轮实际结果

[14项结果与原始证据](test-results-direct-bpf-host-qualification.json)均通过。实际amd64/5.14节点上的自建Python HTTP探针保持原4秒请求超时、0.5秒阻塞写设计，不延长连接来取得成功。12个系统调用入口/出口探针在请求之前挂接：write、recvfrom、sendto、accept、accept4、close。正常场景18事件、9对，捕获真实EAGAIN(-11)、返回4096的500529188ns阻塞写；recvfrom入口的实际回环端口与本轮客户端/服务端端口吻合，同一TID上的接收→阻塞写→发送次序及期间无该FD关闭记录通过。

正常事件从内核时间到Go解码的延迟为14779–12137079ns，本轮未观察到丢事件。此延迟只属于本探针，不是厂商业务的性能承诺。发送及关闭时的FD元数据仍可能unknown；关联仅使用实际获得的接收端点及当轮事件，不能把所有unknown补为已知。

另外对另一个自建子进程执行100000次/dev/null写入，采集器有意暂停读取500ms，以验证输出失败的处理。保留255条事件、BPF输出失败计数199749，报告明确incomplete；perf LostSamples当轮为0。因此不能只用LostSamples判断完整，也不能把两个计数相加作去重后的丢失总数。程序未细分负返回的errno，不能据此宣称199749次全部是某个特定错误码。

两探针和两个采集器正常结束，无强杀。独立只读观察确认runner、checker、四个子进程原实例均已消失，24个BPF程序及6个映射对象共30个ID均不存在。首次只读观察器因局部变量覆盖出现AttributeError，错误收据、可按收据摘要核对的原源码及修订源码均保留；修复观察器后读取同一终态，没有重启资格任务。

## 边界和复现来源

[冻结工程](../tests/direct-bpf-host-frozen-v1/main.go)使用cilium/ebpf v0.17.3及固定go.sum，在独立模块交叉编译Linux/amd64，无C编译器或节点系统包安装。BPF程序直接用汇编构造，只读取已验证tracepoint格式中的整数FD/count/return以及PID/TID、单调时间和cgroup ID，不读取参数指针、用户缓冲、堆栈或请求/日志内容。当前源只支持本轮自建探针资格：目标必须是本控制器的直接子进程、固定实验目录/脚本、精确start_ticks/ELF/脚本摘要和同一纯v2 cgroup。

默认仅只读preflight。实际挂接同时要求--execute和CRG_DIRECT_BPF=authorized-disposable-loopback-only；最长20秒、最多20000事件、私有新建输出、有界元数据读取，不写bpffs、不改tracefs/sysctl/cgroup或目标资源。rlimit调整仅属于采集器自身。逐次/proc FD读取前后核对目标身份、exe inode和FD链接；这些读取不具备内核原子快照保证，其他类型/缺失/变化的元数据均不得当作已知连接。原始采样最多有7字节内核填充，仅解析固定48字节，填充不保存。

工程的PID/start/cgroup、父子关系与脚本约束专门针对本轮自建探针。它尚不能接收厂商PID，也没有验证厂商启动器/工作子进程边界、异步请求模型或业务采集开销。下一步先设计并资格一个严格限定到新建隔离厂商副本的模式，完整核对namespace/Pod UID/容器cgroup/进程后，再执行一次有界连接与原日志写诊断。不能直接放宽现有检查去挂接任意PID，也不把此次工具资格作为API超时已修复、默认20%通过或稳定1.0验收。

接口依据：[官方纯Go tracepoint示例](https://github.com/cilium/ebpf/blob/v0.17.3/examples/tracepoint_in_go/main.go)、[固定版本perf Reader](https://github.com/cilium/ebpf/blob/v0.17.3/perf/reader.go)、[Linux cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)。本工程不进入CRG的依赖与启动链。全部52项原定义、未完成状态和长期运行实例继续保留。
