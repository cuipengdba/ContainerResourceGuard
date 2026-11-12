# 内存百分比使用 memory.high

> 本次实现位于next/compatibility-contract及next/partition-io；main既有程序尚未回移。下载发布附件应核对BUILD.json与版本说明，不能从main源码推断新策略已生效。

2026-11-12用户已明确选择：“memory.high 限制内存用这个，别用 memory.max 这个了。”本需求覆盖旧版默认硬限额语义，保留CPU、内存、IO三个独立百分比、各默认20%；其他资源不新增控制。

## 当前开发合同

`memory_percent`按宿主机MemTotal换算并按页向下对齐，写入本容器的`memory.high`。例如`{"cpu_percent":30,"memory_percent":40,"io_percent":25}`分别控制CPU、内存回收目标、标定IO。手动模式使用`{"resource_mode":"manual","limits":{"memory_high":"4GiB"}}`；旧`limits.memory_max`仅作配置别名，实际也写high并记录兼容警告，两种名称不能同时填写。

high是回收/节流目标，允许用量超过，不能描述成严格内存使用上限。内核可回收干净文件缓存、回写脏页或在允许时换出匿名页，不能任意释放数据库仍在使用的堆与共享内存。不可回收工作集可能持续超目标并导致明显延迟；不新增数据库缓存命令、不杀业务、不写宿主drop_caches或memory.reclaim。

CRG不新增memory.max硬限额。Kubernetes、运行时、祖先及其他管理者原有memory.max仍有效，更严格的现有high也不被放宽。缺少high或无写权限时仅该项降级，绝不回退到新增max。high自身不触发OOM killer；外部硬限额、宿主内存耗尽及其他内核路径仍可能OOM，不能保证绝不OOM。

## 旧版升级及恢复

沿用原state_dir及journal。仅当当前容器身份吻合、旧memory.max当前值仍等于CRG记录的applied/pending值且无冲突时，先通过已有恢复路径恢复其原值，再设置high。原值可能是Kubernetes的有限硬上限，不得一律写max。外部已经改值则保留外部值、记录冲突和降级；journal丢失或不可信时不猜测原值，也不放宽现存硬限额。恢复失败不能宣称旧硬限额已经解除。

新的high同样保存原值、写前意图和回读结果。重载、删除手动内存项或disable只恢复仍拥有的值；新Pod/容器ID每次自发现，旧身份journal不能套用。observe不执行迁移或写入。

high可设置为低于当前用量，以启动回收压力；它不再使用原memory.max的下调余量/稳定窗口。`memory_stable_seconds`仍保护需要降低的历史硬限额恢复，不把等待窗口用来阻止high生效。内核支持时以O_NONBLOCK打开high，避免写入者同步回收；旧内核（包括上游5.14实现）可能仍在write中回收，因此不承诺所有内核上的写入时延有界。原PID1与CRG辅助启动解耦，但资源节流本身仍可能影响业务。

日志继续一天一个文件，保留30天，目录总量超过1GB时从最旧日志清理，失败降级stderr。`resource_status.plan.memory_policy`为`high-reclaim-throttle`，实际项目显示memory.high；兼容别名、恢复、冲突和写入失败均可见。

## 验证和交付任务

- 已实现：百分比及手动high计划、旧max别名警告、外部high/max约束、自有旧max恢复、冲突保护、high低于用量、缺接口不回退硬限额；本地Go测试已通过。
- 待真机：两厂商镜像的真实v2写入、旧发布程序迁移、干净文件缓存回收、匿名工作集超目标、外部限额与权限不足、新ID及停用恢复，分别记录events/oom_kill、用量和延迟。
- 待交付：当前源码Linux检查、测试证据归档、GitHub同步及新预览附件。已发布preview.3仍使用旧memory.max程序，不能把本地修改说成已更新发布包。
- 后续深入验证：脏页与IO受限、缓存回收高峰和两角色完整业务/故障/长期验证；现存旧策略长期任务保留原句柄和来源，不能冒充新策略验证。

原52项定义、既有失败和稳定1.0发布门槛保留。此语义变更列入内存开发主题，不补造历史次版本，也不因单次回收演示关闭业务验收。

接口依据：[Linux内核cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)、[上游5.14内存控制器实现](https://github.com/torvalds/linux/blob/v5.14/mm/memcontrol.c)、[Kubernetes资源管理](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)。
