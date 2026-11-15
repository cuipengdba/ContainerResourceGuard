# 下一独立任务：实际公开 preview.4 → preview.5 百分比策略迁移

这是执行前设计，尚未开发冻结驱动、预检、启动或取得结果。接续已公开的40/40同预算手动维护结果，不替代该结果或默认20%业务失败。

目标：用1255/1263逐字节核对的实际公开旧4(6088721c…)/新5(be6b0aa9…)程序，在97的两个原厂商镜像/真实挂载路径的全新私有测试副本，验证默认配置`{}`时，旧4的四轴IO百分比转为新5的BPS-only，并验证旧身份的active journal不串用于新容器的外部IOPS基线。每容器一份程序，所有命令只在本容器运行。

本轮是**控制层迁移测试**。保持业务gate关闭，原业务、原缓存helper均不启动；使用有界900秒的测试等待gate。它不声称原业务在线性能、健康探针或300秒启动通过。已完成的两角色manual600/备份恢复和manual维护600是另行证据，不继承其运行时间。资源用原fixture的8核/20GiB外部上限，不改数据库参数。测试运行前重新检查28GiB内存/20GiB磁盘、持续8GiB内存余量，只有上一1261任务精确终态与所有登记记录/namespace/父叶独立消失才创建新输出。

拟复用1261真实镜像/路径/私有输入哈希/namespace分离/eth0断网/gate/UID及进程start_ticks清理保护。DBS、HISDBS顺序运行；每角色一个namespace、两个顺序创建的不同Pod/container ID，二者挂载同一份自己的config/state/profile/log/程序目录。第一次使用公开旧4，candidate只读staging；binary-install原子替换后第二次继续新5。运行`run --once`，前后独立检查没有其他CRG run写者；gate关闭所以原helper不会并发启动Agent。不得手工构造或编辑profile/journal；旧程序真实自动标定、真实写journal，新程序真实读取/迁移；保留所有原始文件哈希与mtime。

第一次容器：

1. 原厂商镜像、隔离namespace、当前PID1/cgroup与实际旧4版本/哈希匹配。
2. 预声明8项runtime原值、宿主在线CPU/MemTotal、页大小及默认3个20%，不从输出计划反向定义预期。
3. 旧4运行一次，实际默认自动最大合格本地FS/3样本profile，读取并独立计算CPU/high、BPS及旧IOPS百分比，检查全部实际值和其他5项原值。
4. 核对旧journal的身份/设备身份/三项所有权和真实runtime originals，PID1保持，旧run已结束。
5. quiesce并核对内核值/journal不变；由实际新5使用明确old/new SHA和全新收据执行binary-install。
6. enable后新5 run一次：CPU/high/BPS按默认20%，旧CRG自有IOPS按guard恢复原基线max；同一identity、profile字节/mtime不变，status.io_policy为calibrated-bandwidth，只有三类资源。
7. 检查journal原值仍为旧runtime baseline、IOPS不被继续当作默认限额；PID1、额外控制保持。
8. disable恢复全部8项runtime原值和同身份空journal。
9. 再次enable/run新5，保持同profile、BPS-only、原值所有权；保留**active journal**后删除第一次Pod，独立确认全部登记实例与父叶消失。

第二次容器：

1. 新Pod UID/container ID/cgroup inode/identity，复用同一config/state/profile/log/安装目录，旧active journal字节保留供自动处理；程序仍是新5。
2. 只由测试harness在已校验属于本轮新容器的leaf设置外部IOPS197/149，记录新的8项runtime baseline。禁止改父组或任何其他容器。
3. 新5 run一次，必须新身份journal、旧active journal.previous准确归档；BPS/defaultCPU/high独立换算，外部IOPS197/149保留，不使用旧恢复原值。
4. profile字节/mtime原样复用、无再次标定；三项控制及其他5项原值保持；日志保留旧前缀并追加v2事件。
5. disable恢复当前新runtime baseline（包含外部197/149）及新身份空journal，PID1不变、无遗留run写者。
6. 删除第二次Pod与namespace，所有登记PID/start、两个leaf/parent独立消失；导出两次身份、基线/实际值、journal前后/previous、profile、收据、配置、状态、日志，逐文件SHA/index/source-map联合校验。

计划检查点拟每角色24项/总48项；只有在驱动完成后用AST精确计算实际record数并冻结，不能把本设计数当作结果。预计独立计算old4IOPS floor/max1、CPU quota与页对齐high，并考虑外部约束；算法以准确公开源码和runtime readback为准，不放宽阈值来适配观察结果。新5计划的IOPS省略不等于统一写max，第一组恢复自有基线、第二组保留外部基线必须分开接受。任何失败/未知设备身份/外部修改/权限不足保留原件，不能修改profile、补journal或自动重试覆盖。驱动/协调器/只读断言/计划须先冻结、结构及native预检、GitHub归档，再唯一启动。

后续仍是准确新源码的24h observe +24h enforce及至少7天；旧576约30小时的55432端口冲突必须在新引擎harness加入只读端口所有者采集后再跑，不能继承旧运行时间。原52任务需逐项复核（取消的额外资源按最新需求解释），ARM厂商/多独立物理盘仍按用户已说明暂不可用明确列范围；不因单一测试通过宣布稳定1.0。


[只读断言工具](../tests/public-percent-migration-contract.py)、[20项回放检查](test-results-public-percent-migration-contract.json)、[四组快照准确输入](test-evidence-public-percent-migration-contract.json.gz)。回放不是实际迁移结果，执行驱动尚未冻结或启动。
