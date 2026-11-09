# 本地诊断开发（未发布）

分支 next/local-diagnostics。实现 P05.1 的按需内存分类及 P07.2 的本地白名单诊断；P07 的统一原因码、可选指标和有界事件尚未完成。该分支包含前期 v0.2–v0.5 开发代码，不能将它等同于已发布版本。

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
