# 原生控制器第二轮：独立dm/loop夹具冻结计划

首轮[四格分区IO失败](testing-native-cgroup-partition-first.md)保留，不作重跑覆盖。[新冻结摘要与条件](test-plan-native-cgroup-dm-loop.json)在新push前生成；两线AMD64/ARM64仍独立判断。产品运行时代码没有修改；CPU/内存/IO三项、独立百分比及每日30天/1GB日志需求不变。

本次只改变临时VM的测试存储夹具：用独占私有文件作为2GiB稀疏loop后端，新建有真实内核dm UUID的dm-linear设备，再在该新设备创建ext4。所有case的config/state/data位于此文件系统。不是伪造profile、raw分区通过或两块独立物理设备；loop和dm层的性能受宿主文件系统影响，原始测量完整保留。

格式化之前先确认私有文件独占创建、loop后端路径、dm UUID/name、唯一slave和线性表大小/偏移完全相符；不接受外部设备参数，不格式化已有磁盘。只有一次性CI驱动可创建该夹具，CRG本身仍仅在每个容器内发现自己的cgroup和目录，不装载文件系统或管理其他容器。

原[首轮验收数值](test-plan-native-cgroup-ci.json)保持：手动0.5核/128MiB/读写4MiB/s与256IOPS；CPU8秒/平均0.2至0.65核及真实节流；三类O_DIRECT各6秒、每命令45秒、速率上界1.35倍；安全内存32MiB/4秒；CPU10%、内存1%、IO20%的真实自动标定；产品180秒加观察30秒；普通Agent30秒。没有抬高限额、延长负载期限或补造profile。新建文件系统mkfs固定90秒上限，不计业务或标定时间。

继续检查只三个实际控制、其他五项不变、唯一Agent定向崩溃/同journal重启/显式恢复、正常重建新ID和profile内容/mtime复用、每日日志追加、真实只读cgroup加撤销全部能力的降级及PID1存活。OOM kill必须0；安全分配不代表内存耗尽边界通过。

清理先确认随机标签容器及cgroup正常消失，再核实所有权并依次正常umount、dm remove、detach本loop；逐项回读确认消失。没有全局prune/detach或force。未完整建成或无法证明归属时，保留失败及私有文件，交由临时VM销毁，不尝试猜测清理目标。产品/基线节点及厂商镜像均不接触。

第二轮现已终态[两线双架构88项通过](testing-native-cgroup-dm-loop.md)，此页及JSON保留为执行前冻结条件。即使通过，也只覆盖实际记录的VM内核/Docker/原生架构及此占位夹具；ARM64厂商业务、原分区、独立多设备、Linux6.x（若实际不是）、长期和已发布次版本门槛继续开放。
