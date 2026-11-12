# 已发布 preview.3 → preview.4 内存策略升级验证

[冻结计划](test-plan-public-preview-memory-high-maintenance.json)直接使用GitHub上已发布的两个AMD64包中的精确程序。先核对两个release/tag、各八个当前附件的ID/大小/摘要与原下载验收，再核对本地公开下载的两个tar及manifest，最后只读取tar内唯一常规crg成员、核对ELF摘要。节点在任何业务夹具前再次核对实际上传的两个tar、manifest与测试程序，见[发布包绑定记录](test-inputs/public-preview3-preview4-artifacts.json)。这验证包内程序的安装和状态迁移，不等于已经测试每种发行安装器路径。

上一程序为preview.3的d3706f3/dbc48aa5，包内版本字符串为v1.0.0；新版为preview.4的180c86a/6088721c，版本字符串v1.0.0-preview.4。上一轮[50671aa开发构建到新版的维护26项](testing-memory-high-maintenance.md)保持原始结论，不改标为已发布包；本轮另起私有namespace、目录、凭据、句柄及计时。

两角色使用原镜像、start.sh/PG参数、只读原缓存程序和真实容器路径。每容器一份Agent，CPU7.2核、内存目标20001980416B、读写各64MiB/s及各4096IOPS，运行时原硬上限20GiB。启动/资源300秒、缓存随后45秒且同在300秒内，各实际600秒SQL/API零错误、最大5秒、p95桶上界1秒、覆盖98%、64MiB完整性和原PID1/PG/缓存不重启要求保持；宿主开始28GiB/稳态8GiB可用内存及20GiB空闲磁盘要求保持。

每阶段完整八项控制值及journal身份、真实原值和归属在门禁前构造，期望不取自迁移后的观察值。原配置使用旧memory_max兼容输入且字节保持：旧程序写自己的max，新版解释为high并仅发出已知别名警告；新版仅恢复仍归属于同身份journal的旧max至原20GiB，再写high。回到旧程序时反向恢复high并重设自己的max。其他控制值和CPU/IO预算保持，纯quiesce/文件交换时原始journal字节也保持。

每角色9个维护命令区间必须完全处于各自600秒负载内。首次安装、尚未启用新版时自动回退应成功；启用新版改变journal后旧收据自动回退必须拒绝，程序/收据/内核/journal均保持，再由精确旧程序执行显式反向binary-install，建立当前静默状态的新收据。最终停用恢复原始八项与同身份空journal。每角色13项、两角色26项，另有35项纯合同检查；独立只读观察核对Pod父/叶cgroup、全部已记录原进程和runner/worker清理。

当前只冻结，尚未启动，不能计为业务通过。这两个tag都是预发布，不算“最近两个实际已发布次版本”；默认百分比、真实high压力、老化故障、七天、ARM厂商节点、多物理设备和原52项/稳定门槛继续独立判定。正在运行的[新策略七天组件](testing-memory-high-seven-day.md)保持原句柄，不修改程序、预算或计时。

[冻结作业源码](test-evidence/public-preview-memory-high-maintenance-frozen.json.gz)压缩SHA256=`93c04a40660ceeb08ca400cdabc67d4728d3eebfe7085840cf7cd98f356e4ef7`，解压SHA256=`17f9f9fb47102164863cfaff17dc0f723d9dfeec3e0d0d4b92b3628f81079e82`；它固定输入，不能作为实际600秒通过证据。
