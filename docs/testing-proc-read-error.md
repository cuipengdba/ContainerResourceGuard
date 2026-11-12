# 只读 proc 失败错误码：独立运行时验证

此前449四臂的2410个PG内核栈读取结果仅保留`OSError`，没有errno，历史原因仍然未知。新增独立错误元数据模块，为后续诊断保存固定白名单异常类别、open/read/close阶段、有效整数errno及标准名称；不保存异常正文、文件名、原始内核栈、寄存器或任意异常类名。没有修改旧`vendor-pg-wait.py`及其冻结来源，也没有把本次新工具接入旧压力/长期任务。

[执行前冻结计划](test-plan-proc-read-error-runtime.json)绑定三份源码、24项次序对应的执行检查、专属目录/命名空间、240秒主截止和180秒Pod截止。[实际结果](test-results-proc-read-error-runtime.json)记录原测试节点Linux5.14.0-570.22.1.el9_6.x86_64上一次执行，共72项检查通过：

| 运行时 | 身份 | 检查数 | 本次读取自身/proc/PID/stack的实际结果 |
|---|---|---:|---|
| 宿主Python3.9.21 | root，已有有效CAP_SYS_ADMIN | 24 | 成功，只记录253字节的数量，不输出内容 |
| DBS原生Python2.7.5 | UID999/GID998，drop ALL | 24 | open成功，read返回EACCES/13 |
| HISDBS原生Python2.7.5 | UID999/GID998，drop ALL | 24 | open成功，read返回EACCES/13 |

各运行时检查包含八种合成errno、无效/未知errno、输出脱敏及边界、真实ENOENT/ELOOP/EBADF、自身栈读取与身份、缺失实验标记拒绝。合成检查不是厂商负载；读取自身栈也不等于已验证PG目标进程采样、已修复数据库超时，或已经证明旧2410个错误就是EACCES。宿主与容器权限上下文不同，本次没有做权限提升，也没有认定唯一内核拒绝机制。

两个临时Pod均直接使用原隔离业务Pod对应的相同镜像身份，但覆盖入口为sleep，未启动DBS/HISDBS/PostgreSQL/Agent或缓存程序。仅挂载只读ConfigMap与16MiB emptyDir；只读根文件系统、禁止提权、drop ALL、不挂宿主数据/设备/cgroup、不使用hostPID/hostNetwork、禁止服务账号自动挂载，并有deny-all网络策略。Pod资源为0.5核/128MiB的工具预算，不是原业务测试配额。

终态exit0、无截止超时。原runner/worker、两Pod主实例、两叶cgroup及专属namespace均已独立复核消失。[逐文件精确证据](test-evidence/proc-read-error-runtime.json.gz)包括源/计划、原报告/日志和独立清理。源码仅在完整Git仓库提供：[错误模块](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-proc-read-error.py)、[检查](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-proc-read-error-checks.py)、[隔离执行器](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-proc-read-error-runtime.py)，安装包不含这些执行器。

## 后续任务与发布边界

1. 后续PG诊断需要独立版本，将经过验证的错误元数据接到实际目标读取的准确阶段，并保留run/UID/可执行文件/cgroup/前后身份和采样上限；需要另行完成真实PG目标、目标退出、读取失败、输出界限及Python2兼容验证。不能直接把自身探针结果当作目标资格。
2. 新采样器需冻结、资格验证后才可用于下一项诊断；不改旧失败、不追填errno、不提高原配额/IOPS/时长或SLA，不原样重跑已经失败的矩阵。
3. 原32项双角色业务、七天与后置/故障、正式24h配对、两个实际已发布旧次版本迁移、未测硬件均继续保留。当前内存回收语义[仍待选择](memory-reclaim-policy.md)，默认与preview.3附件不变，稳定1.0未验收。

[本轮原长期任务只读快照](test-progress-seven-day-during-proc-error-qualification.json)在服务器UTC 2026-11-12T03:00:22Z确认原句柄仍运行：R57约107191/107184秒，精确发布ELF的R78约93676/93674秒，均5周期且SQL/API错误0。所有原runner/worker/campaign/Agent/cache/native出生ticks、来源和ELF保持，最大实际宿主采样间隔60.9811秒以内，未达到604800秒及后置条件。
