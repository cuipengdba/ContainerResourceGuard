# 厂商小块日志写入分阶段诊断：原失败保留

内存继续使用memory.high，CPU/内存/IO独立百分比各默认20%；产品源码、依赖及preview.4附件均未改变。本轮把[自有44项资格](testing-iomap-stage-timing.md)中的精确线程/cgroup门控用于DBS和HISDBS原启动链隔离副本，结果为失败。[结构化结果](test-results-iomap-vendor-stages.json)、[完整原件](test-evidence/iomap-vendor-stages.json.gz)、[冻结源码](../tests/iomap-stage-vendor-frozen-v1/vendor-diagnostic.py)均可核对。

## 设计、条件阶段及负载

每个角色保留原26项诊断范围，合计增加4项阶段和采集范围检查，计划30项。原120秒原生SQL/API、64MiB/16384行负载、SQL两秒/API五秒及四秒socket期限不变，仍执行manual→百分比A→manual两次切换，以及原备份/同步/独立恢复10项内容检查。正式业务期限仍600秒，本轮不替代正式压力与业务验收。

新增八个阶段只在BTF已验证的普通文件write(2)、请求1至4096字节、同PID/TID/cgroup且进入到返回之间采集。原五个函数范围保持，共40个hook、5个map；逐CPU环仍八页，原记录上限、期限、真实满环故障及丢失判定不变。六份共享BPF/布局/函数配对及门控源码与通过44项的自有host-v4逐字节相同。

七个必经阶段是iomap_iter、iomap_write_iter、iomap_write_begin、iomap_write_end、__filemap_get_folio、__iomap_write_begin、balance_dirty_pages_ratelimited_flags。folio_wait_stable只在适用分支记录，不能要求新页分支也出现；其进入/返回也不代表必定实际睡眠等待。阶段摘要在严格端口关联和完整性断言前保存。

四个合成用例已核对：新页无stable可通过必经阶段检查，已有页实际stable保留；缺少必经阶段或线程不符必须失败，失败前原摘要仍存在。这些仅为合成单元验证，不是厂商运行通过。

## 实际结果

计划30项，实际记录18项，通过16项；两角色均在事件流零丢失/完整性检查失败，各自余下六项未执行，不能补记通过。

| 角色 | 实际秒数 | SQL次数/错误 | API次数/错误 | 已保存接收/发送端口关联 | perf丢失 | BPF输出失败 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DBS | 120.071681844 | 61/0 | 25/0 | 25/25 | 230 | 230 |
| HISDBS | 120.075867064 | 60/0 | 25/0 | 25/25 | 63 | 63 |

两角色原API最大耗时分别约8.459毫秒、9.322毫秒，但这只是本次120秒窗口。两角色各25个请求已保存严格接收和发送端口关联，后续完整性断言失败后normal_fast_request_binding_accepted仍为false，不能将关联明细存在当作整个工具资格通过。两次切换及每角色10项内容检查的原结果保留为content-passed-native-pending，没有提升为全业务通过。

| 函数 | DBS完整配对数 | HISDBS完整配对数 |
| --- | ---: | ---: |
| __filemap_get_folio | 125 | 130 |
| __iomap_write_begin | 125 | 129 |
| balance_dirty_pages | 1 | 1 |
| balance_dirty_pages_ratelimited_flags | 125 | 130 |
| folio_wait_stable | 120 | 125 |
| iomap_file_buffered_write | 119 | 124 |
| iomap_iter | 243 | 252 |
| iomap_write_begin | 125 | 129 |
| iomap_write_end | 125 | 129 |
| iomap_write_iter | 123 | 127 |
| rwsem_down_write_slowpath | 5 | 4 |
| xfs_file_buffered_write | 119 | 124 |

两角色都出现function_unfinished_entry，incomplete为true；门控错误/剩余条目各为0，但已配对新阶段无法全部落入完整保存的syscall区间，范围完整性条件为false。事件有丢失时无法据这些不完整记录证明门控越界、零额外影响或精确全量阶段分布。

DBS保存119次正返回日志write，HISDBS保存124次；已保存的这些write都含七个必经阶段，分别保存120/125次stable配对。这些是缺失流中的可见配对，不能补全丢掉的事件或将全会话判通过。

下表只展示各角色“已保存最长write”内可见的单次最大阶段时长，单位纳秒；原write分别860726/1330387纳秒。0表示该write内没有保存该阶段配对，不代表该阶段实际耗时为0。嵌套函数的包含时长不可相加，丢失流也无法保证它们是全会话真正最大值。

| 阶段 | DBS可见纳秒 | HISDBS可见纳秒 |
| --- | ---: | ---: |
| xfs_file_buffered_write | 851872 | 1321060 |
| iomap_file_buffered_write | 840562 | 1310594 |
| folio_wait_writeback | 0 | 0 |
| balance_dirty_pages | 803880 | 1249758 |
| rwsem_down_write_slowpath | 0 | 0 |
| iomap_iter | 2582 | 2490 |
| iomap_write_iter | 829364 | 1275189 |
| iomap_write_begin | 11241 | 12036 |
| iomap_write_end | 1467 | 2890 |
| __filemap_get_folio | 4845 | 5246 |
| __iomap_write_begin | 1672 | 1918 |
| balance_dirty_pages_ratelimited_flags | 809653 | 1254706 |
| folio_wait_stable | 1411 | 1468 |

前轮DBS约5.61秒write以及更早DBS/HISDBS API超时的原失败继续保留；本轮没有复现同等长写，也没有获得完整事件流，不能宣称已经解释或修复这些延迟。

## 原件传输与清理

原报告7937733字节，超过旧6MiB读取边界。新只读观察器保留报告原始UTF-8字节及SHA，再将完整观察JSON进行gzip/base64传输；本次解压12715512字节，压缩666529字节，未截断、删事件或改写原报告。解码检查压缩/解压长度及摘要、gzip结束和尾部、摘要一致性，并逐字段比对原报告；只有观察器独立添加的两个cgroup清理字段在对比时排除。压缩上限4MiB、解压40MiB，外层SSH读取仍8MiB，不扩大远程工作期限。

另有14800420字节合成Unicode报告完整往返，并验证错误压缩摘要、解压摘要、长度、非法base64、截断gzip及摘要不一致均拒绝。无损传输只证明原件搬运完整，不会修复BPF/perf采集丢失。

首次SSH上传在open_sftp时连接重置，发生于远程目录创建、上传和启动前；本地收据保留。随后只启动一次固定任务，使用独占目录避免重复。一次本地只读观察进程等待密码时会话句柄丢失，核对命令、PID、启动时间且确认无网络连接后结束该本地进程，再观察同一远端任务；未重启远端任务。

远端任务自然终止exit1，未超时；64个记录的原进程实例已独立消失，180个自有BPF对象通过两份成功完整对象清单核对消失。namespace、两角色Pod、叶/父cgroup清理；原配置和标定文件不存在状态恢复。没有碰生产副本或原长期任务，也没有把失败后的清理当作未执行阶段检查通过。

## 后续开发任务

先处理诊断采集突发容量：八个新阶段增加一笔小块write内的事件突发量，当前八页环已实际丢失；容量不足是待验证候选原因，不能只由丢失计数断言唯一原因。准备有明确总内存预算的有限环容量方案，记录实际分配并以原44项、自有小块突发负载及真实满环故障验证，保留零丢失、错误计数和不完整失败条件，再用于新隔离副本。不直接重跑相同失败工具，也不提高业务限额、socket期限或放宽错误标准。

继续核对完整新阶段中的长write，只有获得完整证据且有可审核的修复后，才恢复原默认20%与600秒压力标准。原[52项任务](current-task-registry.json)、正式24小时、真实high七天604800秒/28周期与老化后置、ARM64/Linux6、多独立设备及实际发布次版本升级条件继续开放。可下载版本仍是[memory.high preview.4](releases/v1.0.0-preview.4.md)，本轮不创建新产品发布或稳定1.0声明。
