# 修正PG启动CSV来源后：新的完整44项冻结计划

修正执行器，不改变产品源码、配额、原PG命令、超时或SLA。此前套件18/16/2/26失败归档，不重试覆盖。当前16项结构/节点预检和25项读取器回放通过，尚未启动新业务夹具。

与[原计划](testing-PG-port-conflict-full600.md)相同，先两个真实PG冲突组（各13项），均限定资格通过并清理后，才跑两个全新正常业务组（各9项），共44项。四独立克隆原镜像、真实挂载、原启动链、只读CCG及每容器一份Agent保持；manual7.2CPU、memory.high20001980416B、读写64MiB/s、手动IOPS4096，外部8CPU/20GiB保持。正常组原native每角色600秒、SQL/API零错误、最大5秒/p95桶1秒/98%覆盖、64MiB内容、物理备份/同步/独立恢复和10项引擎检查均保持。

唯一行为修正：冲突引擎失败后，根据本次standby/current_logfiles寻找CSV，要求整个文件所有记录均为本次启动PID、同一90秒启动窗口，并验证固定挂载目录、文件上限、普通文件/单链接、前后inode/大小/mtime。partial不能通过冲突断言。stderr和实际CSV分别按原始字节导出；不支持的日志格式保留partial，不扫描或导出其他业务日志。

新任务必须先独立核对原失败任务runner、driver、登记进程、namespace、父叶cgroup全部清理，并在节点按冻结读取器只读回放两份原实际CSV。仅当全部源文件与计划摘要相符且内存/磁盘门槛满足才启动。新job `61e0ab046295950d63dc53e46e888a6702b42129f1252e940afd9520584475f7`，新plan `2f80abd5d869e17d7d0f6794255a5f71fd38fd49a1fe5e1ef139276779ff682a`。

[完整冻结源码](../tests/PG-port-conflict-CSV-full600-frozen/business-driver.py)、[协调器](../tests/PG-port-conflict-CSV-full600-frozen/runner.py)、[读取器](../tests/PG-port-conflict-CSV-full600-frozen/tests/own-pg-startup-log.py)、[冻结计划](test-plan-PG-port-conflict-CSV-full600.json)、[16项预检资格](test-results-PG-port-conflict-CSV-full600-preflight.json)、[25项读取器回放](test-results-own-PG-startup-reader.json)、[可逆适配记录](test-adapter-PG-port-conflict-CSV-full600.json)、[原失败终态](testing-PG-port-conflict-terminal.md)。公开文件不含二进制或私有Pod/env/数据库凭据；实际仍用原公开preview.5 ELF。

共享amd64/Linux5.14单设备范围。此前manual业务/维护和默认百分比控制迁移结果分别保留；本轮不能代替默认20%业务失败、新24h+24h、新七天或未覆盖硬件验收。稳定1.0尚未接受。
