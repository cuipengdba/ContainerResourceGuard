# 本地诊断开发（未发布）

分支 next/local-diagnostics。实现 P05.1 的按需内存分类、P07.2 的本地白名单诊断和 P07.3 的可选本地指标；新增 [逐项原因码](reason-codes.md) 和 [可选跨周期内存窗口](memory-stable-window.md)。命令/计划级统一原因与有界事件尚未完成。该分支包含前期 v0.2–v0.5 开发代码，不能将它等同于已发布版本。

## 内存统计

`crg status` 的 JSON 新增 memory，human 格式展示相同内存字段。它在调用时只读采样 memory.current、memory.swap.current、memory.stat、memory.events、memory.pressure，时间与已有 Agent 状态快照分别记录。没有采样完整性的原子保证。

anon、file、kernel 及各自子项按内核字段名展示；shmem 与 file、slab 与 kernel 等存在包含关系，**不能把所有字段相加作为另一份总用量**。缺失字段保留不可用，不将未知值当成 0；PSI 缺失也不假造“无压力”。hugetlb 仅在 memory.stat 提供对应字段时展示，不推断为完整 HugeTLB 统计；不同内核和挂载方式的计费范围需分别核对。

动态计数不写进 Agent 循环持久状态，不因此增加周期磁盘写入。这里没有缓存清理、强制回收、Swap 开关或数据库参数调整。

## 白名单诊断

```bash
# 默认只在标准输出预览
crg diagnose --state-dir /run/crg

# 显式写入全新的、本地私有文件；不会自动上传
crg diagnose --state-dir /run/crg --output /tmp/crg-diagnostic-001.json
```

输出格式 crg-diagnostics-v1，硬上限 64KiB，最多 64 个控制项，超出的数量另行记录。内容仅包括平台架构、已确认宿主总量、状态类别、实际控制值和当次内存数字。状态缺失/损坏时仍可生成只读诊断，但不会复制错误原文。

不纳入完整配置、路径、cgroup/容器 ID、命令行、环境变量、journal 原值、业务脚本/日志/数据；通过字段白名单生成，不能依赖字符串替换密码。已有输出、状态目录内部及 IO profile 路径拒绝写入，包括可解析的目录别名；新文件权限为 0600。不新建网络监听，不访问 Kubernetes API。

输出目录须已存在。文件/目录同步失败会报告错误；可能留下本次私有的部分文件，需用户显式检查/删除，不能据此显示导出成功。未得到身份确认时仍拒绝操作。

## 验证状态

Windows 单元与 vet 已通过；用例覆盖重叠计数、未知与零区分、异常数字/PSI、白名单脱敏、64 项/64KiB 上限、拒绝覆盖及状态路径保护。Linux race、目录同步/权限与真实容器按需诊断待验收。没有把开发实现、短测与后续长时门槛混为一项。

统计解释依据 [Linux cgroup v2 官方文档](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)，未把最新内核存在的字段作为旧内核必备字段。

## 输入规模与状态读取保护

提前承接 P09.3：所有 JSON 解码限制为 1MiB、最多 64 层嵌套，data_paths 最多 64 项且每项不超过 4096 字节，防止小配置展开出过大的状态报告。journal、status、disable 和重载会话/请求均有界读取；Linux 使用非阻塞、禁止最终符号链接的文件打开方式，拒绝 FIFO、设备、目录和超大状态。配置/profile 文件仍可读取指向普通文件的 ConfigMap 符号链接。

这些边界不删除或重建坏日志，不省略原值落盘。异常状态会拒绝相应控制或读取，诊断命令不复制错误原文。新增配置/profile 模糊测试入口；长时运行、真实掉电和持续满盘故障仍待验收，不能只凭模糊测试种子通过关闭 P09.3。

## 可选本地指标

```json
{"percent":20,"metrics_enabled":true}
```

metrics_enabled 是运维开关，默认 false，不增加资源模式必填项。开启后仅在当前容器 state_dir 下写 metrics.prom，每次启用立即采样，持续开启期间每分钟最多尝试一次，单次最多 64KiB；显式反复关闭/开启会触发新采样。不监听端口，不启动远程控制服务，也不访问其他容器。指标文件使用私有权限和临时文件原子替换；它可丢弃，因此不要求 fsync，原值 journal 的同步持久化完全保留。

提供当次采样时间、Agent 状态、CPU 用时/节流、内存/Swap、分类与 events/PSI、当前任务数及按设备的 IO 统计。缺失统计通过 collector_available=0 表示，不伪造零压力。IO 最多展示 32 个设备并报告省略数量；映射栈同一 IO 可能在多个设备计数，不能相加。没有业务路径、环境变量或业务数据标签。

写出失败仅在 status.metrics 中显示 unavailable，主资源协调继续，失败也按一分钟重试，不逐周期反复写错误。关闭开关后停止更新，保留旧 metrics.prom；采集者必须检查 crg_metrics_sample_timestamp_seconds 判断过期，不能仅看文件存在。此文件不是业务健康探针。

本地单元/vet 验证了默认关闭、失败限频与恢复、计量单位、设备数边界、无控制写入，以及持续指标错误不让 status 每周期写盘。5c707d9 的 Linux 竞态/强杀回归及 10 项真实文件/控制检查通过，见 [指标实测](testing-metrics.md)；此前 c3a2071 的测试与这次结果分别记录。
