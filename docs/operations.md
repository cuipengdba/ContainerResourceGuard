# RC2 本地运维与恢复

用户已明确选择：下一版IO百分比只限制标定读写BPS，IOPS留手动，外部IOPS保留且自有旧值按身份/journal迁移；内存继续memory.high。[新策略](io-bandwidth-policy.md)的准确源码ced4617已通过完整Linux/原生ARM64、52项实际cgroup及180项分区检查；[默认20/30真机矩阵](testing-bandwidth-percent-startup.md)已冻结/预检，尚未启动。preview.4仍为旧四轴、未改附件，原52项和历史失败保持，当前不作新业务或稳定发布接受。

最新用户选择已覆盖旧R10：下一版io_percent仅限制标定读写BPS，IOPS留手动；既有外部IOPS保留，旧自有限额按身份/journal安全迁移。实现与新增回归见[IO带宽策略](io-bandwidth-policy.md)，当前待准确Linux/原生/真机验证；preview.4及旧结果保持，原52项不补算完成。

当前建议配置为 `{"cpu_percent":20,"memory_percent":20,"io_percent":20}`，三项各自省略时默认20；旧单`percent`只作历史兼容。本页的命令只作用于执行命令的当前容器；没有远程容器管理入口。与 Agent 使用同一个 `--config` 或 `--state-dir`。

## 安装前检查

```bash
crg preflight --config /etc/crg/config.json --format human
crg status --config /etc/crg/config.json --format human
```

preflight 发现自身 cgroup、换算预算，并只打开/关闭控制文件检查写入入口，不写资源值。`open_writable=true` 仍不能证明内核会接受特定限额，实际启用后必须查看回读及负载结果。原业务不能等待此命令完成才启动。

status 同时显示请求比例、计划值、逐项结果、当前控制文件读值及快照年龄；拒绝读取其他或旧容器身份的快照。`writer_lock_held` 表示 cgroup 协调锁被持有，可能是 Agent 或恢复操作，并不是数据库健康证明。无法检查锁时输出 `lock_check_error`。

状态无变化时最多每 5 分钟更新一次文件，有变化时下一检查周期立即保存。`time_utc` 是快照保存时刻，不是每秒心跳；查询时的 `actual` 才是当时重新读取的控制值。原值/写入意图日志始终同步保存，不使用低频策略。

## 受控停用并恢复

```bash
crg disable --config /etc/crg/config.json
```

该命令先同步保存当前 cgroup 的停用标记。运行中的 Agent 每秒检查标记，停止下一轮控制并释放锁；命令最多等待约 5 秒取得锁，然后只恢复仍属于 CRG 的值。辅助重试循环仍可存在，但它启动的 Agent 看到标记会直接退出，不会重新施加限额。

- 成功返回一个 JSON 对象，`mode=disable`、`state=restored`，退出码 0。
- 外部改动、只读或恢复失败时返回单个 `degraded` JSON，退出码非 0；停用标记继续保留。检查原因后可重试 disable。
- 若 Agent 卡在内核 IO 或日志损坏，可能无法取得锁或恢复。命令报错，业务不因此退出；标记保留。不要删除 journal 或用 `max` 批量覆盖。
- 停用与 Agent 某次正在进行的控制写入可能短暂重叠；命令取得锁后才开始恢复。没有“写标记瞬间所有值已经恢复”的承诺。

标记绑定当前 cgroup 身份；容器重建后的新 cgroup 不继承旧身份的停用状态。永久停用应移除/关闭可选启动入口并保留恢复日志。不要通过更换 state_dir 绕过停用；更换目录也会失去原值记录。

## 重新启用

```bash
crg enable --config /etc/crg/config.json
```

此命令在持有协调锁时删除停用标记，不重启业务。原辅助循环将在下次退避重试时重新启动 Agent，可能等待 5–300 秒；也可按现有 supervisor 的管理方式仅重启辅助循环。运行后的配置仍从启动时读取，不支持热加载。

`restore` 继续保留给已停止 Agent **及辅助重试循环**的维护场景。需要自动协调停用时优先使用 disable。

## 单实例与版本升级

RC2 同时持有自身 cgroup 目录 inode 的独占非阻塞锁及状态目录锁。同一容器更换状态目录也不能启动另一份 RC2 写入者。锁不创建 cgroup、不写父级控制文件，进程退出由内核释放。

锁是 CRG 实例之间的协作约束，不阻止运行时、管理员或其他程序改值；这些变化仍由原值日志/冲突检测处理。RC1 没有 cgroup 目录锁，升级前应先停止全部旧 Agent 和辅助循环，保留原状态目录；不能将混合版本、不同目录的并行运行视为受到新锁保护。

## IO 覆盖范围

可以额外配置路径以便诊断，而无需单独指定资源预算：

```json
{"cpu_percent":20,"memory_percent":20,"io_percent":20,"data_paths":["/data","/backup"]}
```

路径只用于只读查询其文件系统设备，不读取业务文件内容。输出实际设备号、是否存在计划限额；未配置路径时只报告 profile 中的设备，不声称覆盖所有容器 IO。Overlay/NFS/缺基准路径不会被猜成某个本地盘。

基准依靠 UUID/WWID、大小等身份重新定位设备。编号变化可重新识别，更换设备不能复用旧基准。同一 profile 同时出现某层设备和其下层/分区父设备时，两者都跳过并说明，避免在同一路径上盲目重复限流。共享下层的两个独立逻辑卷不直接当成同一设备层；复杂存储栈仍需实机验收。

## memory.high回收目标与历史硬限额预检

preview.4的memory_percent和手动limits.memory_high写memory.high，可设置到当前用量以下，触达后由内核回收/节流，允许超目标；不使用下面的硬限额余量条件阻止high生效。它不能任意释放业务仍在使用的堆/共享内存。high本身不触发OOM killer，CRG也不新增memory.max；外部/Kubernetes/祖先硬限额或宿主内存耗尽仍可能OOM。见[内存策略与旧版升级](memory-reclaim-policy.md)。

下面只描述历史硬限额降低/恢复的保护路径：下调前间隔 50ms 读取两次 memory.current；除了 `5% + 16 MiB` 余量，还为采样到的增长率预留约 1 秒空间。期间 memory.events 的 high/max/oom/oom_kill 增加，或可读取的 PSI `full avg10 >= 1%`、`some avg10 >= 10%`，均跳过本次下调。日志同步保存后、真正写入前再次检查用量。

缺少可选 PSI/events 文件时继续执行用量余量检查；无法读取有效 memory.current 则拒绝下调。恢复到较低的旧 memory.max 同样检查。没有主动回收数据库缓存、修改数据库参数或自动放宽用户百分比。

这些是瞬时保守预检，无法保证后续分配不 OOM，也无法使多个 cgroup 控制文件成为原子事务。跳过意味着该项尚未施加请求上限，必须结合状态处理。
