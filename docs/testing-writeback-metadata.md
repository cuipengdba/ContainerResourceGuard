# 普通文件、回写等待元数据及厂商路径复验

内存继续按用户选择使用memory.high，CPU、内存、IO独立百分比各默认20%。当前公开程序仍为preview.4。本轮只开发独立实验诊断及其测试记录，没有更换产品源码、依赖、发布标签或八项公开附件。独立进程28项资格通过；新厂商副本原22项实际19项、18项通过，HISDBS一次原4秒接口超时，整体失败。见[结构化结果](test-results-writeback-metadata.json)和[完整原始证据](test-evidence/writeback-metadata.json.gz)。

## 独立工具与边界

[通过资格的冻结源码](../tests/writeback-metadata-host-frozen-v2/main.go)先验证独立实验标记、原PID/start_ticks、ELF、叶cgroup及本轮创建关系；默认只做只读预检。19个BTF字段验证类型、大小和关系，14个临时hook只在精确目标TGID及cgroup匹配后采集。新增普通文件inode、设备号、mode、flags整数，以及balance_dirty_pages的五个整数和folio_wait_writeback的inode/index；不保存指针、业务缓冲、日志内容、物理页号或任意堆内存。FD槽复查及路径注释都不是原子快照，失败保留unknown，不宣称并发复用竞态全部解决。

首次元数据扩展为72字节后，每CPU四页缓冲在故意暂停解码500毫秒的32连接检查中产生63次BPF输出失败，实际记录13项、12项通过，保持失败；6个原进程实例及34个BPF对象已独立消失。该轮尚未进入脏页测试，不编造回写资格。其[冻结源码](../tests/writeback-metadata-host-frozen-v1/main.go)与原收据完整保留。

仅将自己的诊断缓冲调整到每CPU八页，使72字节记录及perf头开销能容纳同CPU的284条受控突发，原丢失检查及业务限额/时限没有放宽。新轮28项全部通过：正常18事件及真实EAGAIN/半秒阻塞、32个立即关闭连接的284事件与端口关联均完整；真实满环仍产生199632次BPF输出失败、perf丢失0，正确标记incomplete。两类丢失计数不相加，也没有采集输出失败errno。

独立32MiB缓冲写及4096字节O_DSYNC写只针对新建的自有测试文件、直接子进程和独立叶cgroup：memory.high=16MiB，写带宽1MiB/s，不更改根控制器或业务限额。实际33558528字节用时32.678294306秒；普通文件inode、设备、mode和DSYNC位与真实fstat/fcntl一致。采到1930条balance_dirty_pages和69条对应自有文件inode的folio等待事件，正常回写流3047事件无观察到丢失。memory.events.high增加60，oom/oom_kill为0，仅限本次观察；10个不同原进程实例、68个BPF对象及自有叶cgroup独立消失，测试文件清理，根控制值保持。

## 失败前保存证据

前一厂商诊断在严格断言失败前没有保存局部关联结果。本轮[修正记录逻辑](../tests/vendor-diagnostic-persistence-v1/vendor-diagnostic.py)，先落盘原窗口的关联、丢失状态及accepted=false，再执行原断言。合成成功/失败两条单元路径通过；新的真实HISDBS失败报告也保留25条关联及超时原记录。该修正不改变原窗口、错误数或是否通过，不用迟到事件重评失败。

## 新厂商隔离副本

[冻结厂商源码](../tests/writeback-metadata-vendor-frozen-v1/fixture.py)使用与独立28项完全相同的kernel.go、layout.go、wait.go，保留原镜像、启动链和挂载、每容器一对一Agent及缓存、原CPU/IO预算、memory.high和外部Kubernetes硬上限。新namespace/UID、Pod UID、containerID、PID/start_ticks、PID1与命名空间/挂载/ELF分别验证；未附加到旧七天任务或生产实例。只做原120秒诊断、两段手动→百分比A→手动及+30秒原备份/同步/独立恢复；不代表完整600秒/11段/实际高内存压力。

| 项目 | DBS | HISDBS |
| --- | ---: | ---: |
| 实际原生秒数 | 120.144869 | 120.088167 |
| SQL次数/错误 | 61/0 | 61/0 |
| API次数/错误 | 25/0 | 25/1 |
| 原请求窗口内recv/send均有关联 | 25/25 | 24/25 |
| 事件数/系统调用对数 | 1056/528 | 1027/513 |
| 最大原日志write | 660086ns | 7655366993ns |
| balance/folio事件 | 0/0 | 0/1 |

两流均无观察到的perf丢失或BPF输出失败且完整排空；两个原引擎各10项为content-passed-native-pending。DBS本次范围通过不能清除前一轮DBS两次超时。HISDBS失败后剩余三个检查（含显式disable）未执行，不算通过；独立最终清理另记。67个不同原进程实例、68个临时BPF对象、两个Pod及父叶cgroup和namespace确认消失，配置字节及profile缺省恢复。

HISDBS线程3959811对FD3、inode2085517600的原/opt/dbs/log/DBS.log写143字节，用时7.655366993秒并返回143。事件发生时flags=33793（0102001，O_WRONLY|O_APPEND|O_LARGEFILE），未观察到O_DSYNC/O_SYNC。客户端44860的完整4秒超时发生在该write内部；同线程后续accept/recv/send已在请求开始约4.14秒后，不能把迟到处理计为成功。

该write内部同TID、同cgroup、同日志inode采到一条folio_wait_writeback，逻辑文件页index24。但该事件在write开始7.563532596秒后、原客户端超时之后才出现，距write返回还有91.834397毫秒；事件本身没有结束标记。由此确认进入对应回写等待路径，不能将全部7.66秒归到这一等待，更不能据此证明IO限制、内存回收、锁或调度是全部超时的根因。没有balance事件也不排除未采集的内核路径。

## 匹配运行节点的内核语义

节点包为AlmaLinux9.6的kernel-core-5.14.0-570.22.1.el9_6.x86_64。已从[AlmaLinux官方归档](https://vault.almalinux.org/9.6/BaseOS/Source/Packages/kernel-5.14.0-570.22.1.el9_6.src.rpm)完整下载其SOURCERPM，149371669字节，SHA256=df5afcfc6287992d078093fea5fc1b42612c5ea827e18bd6e625f75482a394e2；RPM签名未独立验证。这是对应包源码及现场BTF/trace格式的核对，不是运行内核二进制可复现构建证明。检查十份附加patch均未改动所选文件，源码只在本地解包，没有安装到节点。

匹配源码确认pause已由jiffies转换为毫秒，是有符号的计划节流值；paused是该balance调用以来的累计毫秒，不是每条事件的已完成IO等待。事件也有不睡眠和BDP_ASYNC返回路径，不能求和当作真实阻塞时长。folio事件在检查到writeback后、folio_wait_bit之前发出，不能用单条事件测得实际睡眠时间。冻结采集器仍保留原整数，源码摘录、文件摘要及解释独立归档，未改写原报告。

## 接续任务与发布状态

下一步在新的独立资格环境验证等待函数进入/返回的时长配对及边界丢失，再观察新厂商副本中写入前段与folio阶段；保留原4秒socket超时、IO限额、零错误业务标准，不以加大预算或重复未改观测的全量验收取得通过。此处是规划，尚未取得函数配对资格或产品修复证据。

所有[原52项](current-task-registry.json)、默认20%与既有完整压力失败、正式24小时、memory.high实际七天604800秒/28周期和老化后置、ARM64/Linux6真机、多独立物理设备及实际已发布次版本升级条件保持开放。原长期任务未重启，旧策略时间不转移。[memory.high版preview.4](releases/v1.0.0-preview.4.md)可下载，日志仍一天一文件、30天或超过1GB清理；当前未发布1.0稳定版。
