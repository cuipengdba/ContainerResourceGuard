# 独立分支真实分区验证结果

开发分支next/partition-io的[运行前计划及边界](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/partition-io/docs/testing-partition-cgroup.md)和[冻结SCSI合同](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/partition-io/docs/test-plan-partition-cgroup-scsi.json)保留；本线尚未合入产品实现。


## 真实分区四格结果

[SCSI修正轮工作流](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42877343464)已完成：源码468fe73（产品实现af1a34d）在实际Linux6.8.0-1070-azure／7.0.0-1017-azure、Docker28.0.4、原生AMD64／ARM64四格各41项，共164项通过。两个真实GPT文件系统共享同一整盘限额，分别直接IO及同步双分区写入/随机写验证合计预算；CPU实际节流、内存安全分配、旧发布二进制独立恢复有限原值、换ID复用缓存/日志、真实几何变化重新标定、重叠profile拒绝、只读无权限回退及全部自有测试设备正常清理均通过。原数值、计时和三资源范围未改。

完整[结果、源码、程序摘要及首轮失败](test-results-partition-cgroup.json)归档。首轮DM四格各只有4项准备检查，均因内核禁止DM普通分区而失败，未进入资源效果；保留其部分磁盘准备未完成/交由临时VM销毁的状态，不计作正常清理通过。报告下载出现本地传输超时后，改为对同一不可变artifact的命名ZIP文件作HTTPS范围读取并验证ZIP CRC，未因此重新运行测试。新旧执行程序摘要由夹具及运行中/proc/exe核对；旧资产仍经固定发布合同独立校验，不把未完整下载的本地新ELF称为另一次字节复核。

共享顺序写只以字节速率验收；夹具在顺序模式的iops字段是4KiB等价数，不作为实际顺序操作率。IOPS判定只取实际4KiB随机写。几何变化后旧profile保留，须明确degraded和旧条目unavailable；正确生效的三项限额另行核对，不能称全部profile可用。RAM后端SCSI测试盘不代表物理盘容量基准或多块独立物理设备；ARM厂商业务、正式长测和1.0发布门槛仍独立保留。本分支尚未合入/发布，97固定程序和预算及现有发布资产不变。
