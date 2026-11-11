# 有界只读设备状态采集资格

此工具落实[写BPS对照后续计划](plan-post-write-bps-diagnostics.md)，用于补齐同时间轴的设备/脏页/cgroup观测。[实际结果](test-results-device-state-observer.json)和[完整原始结构证据](test-evidence/device295-qualification.json.gz)固定源码、计划、运行器及输出摘要。三组写BPS对照的两次失败与一次通过继续保留，本工具尚未接入原32项完整压力验收，也没有证明超时根因或稳定1.0达标。

## 已实际验证

| 范围 | Python | 检查数 | 真实观察 | 子进程CPU秒 | 子进程高水位RSS KiB | 单次采集最大毫秒 |
|---|---|---:|---|---:|---:|---:|
| Linux测试节点 | 3.9.21 | 32 | 3秒/4样本 | 0.056005 | 15552 | 2.310 |
| DBS原镜像 | 2.7.5 | 32 | 3秒/4样本 | 0.057299 | 11928 | 3.886 |
| HISDBS原镜像 | 2.7.5 | 32 | 3秒/4样本 | 0.057605 | 12108 | 4.522 |

两镜像均与原长测镜像ID一致，Pod配置UID999/GID998、只读根文件系统、drop ALL capability，只挂emptyDir，没有原数据库目录或产品程序挂载。32项各自包含解析/重置反例、只读预检、缺少执行标记、900秒边界、源或计划摘要、PID/start_ticks、cgroup/设备inode/路径、重复设备/JSON、符号链接及已有报告拒绝覆盖，另有短期真实采样。预先预算为子进程CPU≤1秒、单次采集≤100毫秒、子进程高水位RSS≤128MiB。RSS为该资格父进程已回收子进程的高水位口径，不是一次采样的增量或业务内存。

节点另有2项真实生命周期检查：测试子进程自然退出后，观察器拒绝其Z身份并只保留此前有效样本；通过pidfd只向自己创建并核对PID/start_ticks/入口的观察器发送一次TERM，得到phase=incomplete、observer-interrupted的部分报告。目标信号0、观察器TERM1、KILL0，两个观察器原实例独立确认退出。部分报告没有被改为3秒完整观察通过。

资格运行器最终退出0且原PID/start_ticks已消失；两个Pod、其scope及namespace独立确认清理。该资格只有短期设备采样，不是业务、900秒持续观察、真实热插拔或七天接受。

## 采集与边界

[采集器](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-device-state-observer.py)兼容此次实际Python2/3环境，每份计划只固定一个进程及其cgroup，并绑定boot_id、设备号、sysfs真实路径和目录inode。每次采集前后重查，身份变化则丢弃整行并结束；缺失的可选字段保持unknown。默认仅预检，执行须有明确测试标记及计划SHA，输出以O_EXCL/0600新建；原始记录在内存中累计，最后一次写入/fsync。上限900秒、4设备、单文件读取64KiB、单行8KiB、报告8MiB；尚未实际运行900秒。

只读/sys内已确认设备的stat、/proc/meminfo和vmstat白名单，以及指定cgroup的数值统计和三项当前控制值。没有打开/dev块设备、测速、全局sync/drop_caches、控制写入、进程命令行/环境/内存或任意文件内容采集。vmstat字段保留原始单位，meminfo的选定kB字段单独转字节。设备编号253:0/8:2/8:0只属于本次已核对布局的资格夹具，产品仍在每次容器启动时重新发现自身身份。

按[Linux块统计说明](https://docs.kernel.org/block/stat.html)，扇区计数以512字节为单位，in_flight为当前在途量；按[内核IO计数说明](https://docs.kernel.org/admin-guide/iostats.html)，计数可能在重启、设备重新附加或溢出后重置，io_ms也有内核实现边界。因此解析保留11/15/17字段布局差别，增量函数对重置或字段改变输出unknown，并将in_flight作为可下降的量。全节点设备统计包含其他活动，不代表某个容器或请求；253:0、其分区和父盘分别呈现，不能相加、推断精确排队深度或构成独立多盘证据。不同文件的读取不是原子快照。

[资格脚本](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-device-state-observer-checks.py)只适用于上述已确认三设备布局的隔离节点；[生命周期脚本](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-device-state-lifecycle-checks.py)为Linux宿主Python3测试，仅使用自建进程。这些不是容器安装步骤，也不是新的多容器资源管理程序。生产仍每容器一份Agent；CPU/内存/IO三个独立百分比、日志保留和辅助失败放行语义保持。

后续先将该工具的启动、身份固定、部分报告及限时收尾接入独立会话，并验证采样包络与故障放行，再冻结新完整压力计划。PG真实路径白名单及PG目标选择器仍须另行资格；旧冻结观察器不覆盖。原业务额度、载荷、时限、52任务定义和长期handle均保持，所有历史失败与正式24h+24h/真实604800秒后置继续。
