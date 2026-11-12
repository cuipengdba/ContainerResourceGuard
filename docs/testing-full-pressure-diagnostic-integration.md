# memory.high与完整压力诊断接入

内存百分比只换算为 `memory.high`，不下发新的 `memory.max`，保留Kubernetes/运行时已有硬上限。达到high会触发回收和分配节流，允许超过目标；不能保证业务堆自动释放或系统绝不OOM。已发布的[preview.4](releases/v1.0.0-preview.4.md)采用该策略，本次改动属于独立测试诊断和文档，没有修改产品、依赖或发布附件。每容器一个Agent、CPU/内存/IO独立百分比各默认20%、v1不写控制值、无权限时记录并继续业务、每日日志文件/30天/1GB策略继续保持。

## 实际结果

[结果](test-results-full-pressure-diagnostic-integration.json)、[完整原件](test-evidence/full-pressure-diagnostic-integration.json.gz)及[本轮冻结源码](../tests/full-pressure-diagnostics-frozen-v1/full-pressure-integration.py)均已归档。97节点新隔离命名空间内，DBS/HISDBS分别执行原600秒负载和全部11个配置、压力、释放区间；原32项计划检查、SQL两秒/API五秒/四秒socket、64MiB负载、覆盖率和零错误标准均未改。实际记录29项，29项通过；DBS原业务异常使其最后三项检查未执行，本轮业务验收失败，不能把29项通过视为原32项通过。

| 角色 | 实际负载秒 | SQL错误 | API错误 | 完整区间数 |
| --- | ---: | ---: | ---: | ---: |
| v10-dbs-bw64 | 600.319388 | 0 | 2 | 11 |
| v10-hisdbs-bw64 | 600.393184 | 0 | 0 | 11 |

原业务失败：`v10-dbs-bw64: NATIVE_COMPLETION_EXIT`。未记录项为DBS的600秒完整业务成功、同一Agent/PID1/PG/cache/profile及零OOM、显式disable恢复三个后置检查；原驱动在业务异常后按原路径清理fixture，没有补造通过记录。原始请求时间、异常、业务与主机采样随完整报告保留，不以诊断器失败忽略API错误，也不把历史失败重新判成通过。原内存high、CPU、IO值和外部memory.max按原区间核对。

可选诊断在两角色启动时均遇到TypeError，发生在只读预检结果投影阶段，尚未挂接BPF、安装请求注解或替换业务启动调用。原包装层随后继续原业务，两个原600秒及11区间均完成。这证明本轮该辅助启动故障未阻断原业务流程，不能据此宣称所有故障或资源限额对业务都无影响。两角色的结束诊断也失败，错误均保留。

终止后独立核对57个记录的原进程实例已消失，命名空间、两角色叶和父cgroup均消失。没有创建BPF对象，因此没有实际挂接后的BPF清理资格。完整索引中的27份原件共25061645字节，经真实SFTP分块下载，每份核对长度、EOF及SHA256，保留完整UTF-8内容；未截断事件或日志。只读观察及下载均针对同一固定PID/start任务，未重启或中途替换冻结文件。

## 已完成的前置开发

1. [报告输出](../tests/compact-report-output-host-frozen-v1/report_output.go)：改为紧凑JSON，仍以32MiB（含换行）为上界。溢出、编码、短写、write、sync、close错误均明确失败，不再静默产生空文件并返回成功。实际Linux五项检查通过，包含真实CLI零文件大小限制下的REPORT_WRITE、失败退出码与空文件识别，没有加载BPF。
2. [请求端口注解](../tests/native-transport-shim-frozen-v1/sitecustomize.py)：仅对冻结原native脚本、当前容器PID1 cgroup和精确本地/test请求生效，保持四秒socket、原返回对象与异常、原业务脚本字节。注解最多512字节，使用独立非阻塞FIFO描述符；满管道丢弃注解，不等待、不重试、不改变原stdout标志。host Python3及两个原镜像Python2.7.5分别通过九个用例；原业务完整运行时尚未启用它。HTTP响应头返回不能当作完整业务成功。
3. [有界原件传输](../tests/full-pressure-diagnostics-frozen-v1/artifact-transfer.py)：单文件32MiB、总计256MiB、最多64份、1MiB分块，严格固定目录和文件名，拒绝路径逃逸、重复项、符号链接、源文件变化、截断、尾随字节及摘要不符。12个用例在本轮Linux预检通过，其中22400000字节是合成传输用例；真实网络传输字节数以上表述为准。
4. [完整压力工厂](../tests/full-pressure-diagnostics-frozen-v1/full-pressure-integration.py)：保留原核心与native脚本，围绕单次原业务调用创建单独诊断实例。只在本轮隔离fixture身份匹配时允许采集，原40个hooks、5个maps、16MiB perf映射/32MiB报告/20000事件/1200秒诊断上界不变。本轮Linux预检通过Go单元、16个工厂合成用例和12个传输用例，但实际工厂启动失败，不能当作完整诊断资格通过。

## 已确认的缺陷与修复范围

实际只读Go预检输出 `function_pairs: null`，冻结工厂用 `len(value)` 投影计数，触发TypeError。用这份13000字节原件（SHA256 `765e9a891d3e7eced53d02a5bf6596079a9989c4b79145e418f9b35cec14e751`）回放，可重现冻结版本异常。

[修复候选](../tests/full-pressure-diagnostics-null-fix-v1/full-pressure-integration.py)将空数组按0项处理，不改写原件。回放中修复版成功，原件字节和摘要不变；17个本地Python3用例通过，其中新增真实null原件回归。旧冻结版本、原16个用例、实际错误和新17个用例分别保留。修复未热改当前真机轮次，修复版完整真机诊断仍未验收。

## 后续与验收边界

下一轮须先验证修复版，再用新的隔离身份执行原600秒/全部11区间/32项检查，并保留逐请求端口、全部事件、业务超时与清理证据。需要确认采集实际启动、无丢失/未闭合函数、报告完整及请求全时间窗关联；仅响应头或晚到的同端口事件不足以解释API超时，历史长write的完整耗时仍未归因。

原[完整压力失败](testing-memory-high-pressure.md)、[阶段丢失失败](testing-iomap-vendor-stages.md)、[厂商120秒资格](testing-bounded-perf-timing.md)和[自有600秒资格](testing-long-perf-session.md)保留各自范围。52项原定义和未完成声明不变，默认20%完整业务、正式24小时、memory.high七天604800秒/28周期及老化后置、ARM64/Linux6/多设备和已发布次版本升级等仍开放。七天任务本次只读快照约42940/42938秒、SQL/API零错误，尚未满足七天条件；未重启或转移旧策略时长。稳定1.0未接受。
