# 原生控制器第二轮：两线双架构88项通过

[第二轮运行前计划](test-plan-native-cgroup-dm-loop.json)冻结后，主线994643f、组合5280963均在实际原生AMD64/ARM64 VM执行。四格共88项全部通过，下载的程序ELF、build-info、驱动摘要及报告摘要已逐格核对并[长期归档](test-results-native-cgroup-dm-loop.json)。普通打包CI和native-arm64基础CI也独立成功。

| 程序线/架构 | 实测平均CPU核 | 顺序读/写MiB/s | 随机写IOPS | 检查 |
| --- | ---: | ---: | ---: | ---: |
| combined/amd64 | 0.500391 | 3.995/4.015 | 256.661 | 22/22 |
| combined/arm64 | 0.500140 | 3.996/3.997 | 256.632 | 22/22 |
| main/amd64 | 0.503897 | 3.974/3.997 | 256.663 | 22/22 |
| main/arm64 | 0.501785 | 3.995/4.002 | 256.686 | 22/22 |

固定手动预算0.5核、128MiB、读写4MiB/s及256IOPS，实际CPU节流增量均大于0；直接IO实际速率在预先声明1.35倍上界内。安全32MiB分配和OOM0通过，不等同于耗尽边界验收。

CPU10%/内存1%/IO20%在各VM的真实容量和新标定profile下独立换算，自动选择合格目录、保存真实基准；没有提供人工profile或抬高IO下限。实际叶cgroup三项回读与独立期望一致，其他五项保持。经精确PID/start_ticks及程序摘要核对只杀本Agent，限额仍保持，重新启动同journal成功；disable恢复实际八项原值。正常删除再建容器后ID/journal身份变化，profile内容和mtime原样复用、每日日志追加；真实只读cgroup加撤销全部能力时为degraded，控制值不变且原因可见，PID1继续运行。

实际环境为Linux7.0.0-1017-azure、Docker28.0.4，并非6.x。存储是临时VM内2GiB独占文件上的真实loop/dm-linear/ext4，UUID由内核暴露，所有case的config/state/data在该文件系统；它是实际内核控制夹具，不是独立物理设备或厂商数据库。只格式化新建且已验证UUID/表/slave的本夹具设备。

四格最终正常stop/remove、自己的cgroup和镜像消失、umount/dm remove/本loop detach及私有目录删除均回读确认。没有全局prune、force或业务节点操作。原[首轮分区IO四格失败](testing-native-cgroup-partition-first.md)完整保留；这里没有提交分区身份/控制目标运行时修复，也不能据本轮宣称原分区通过。

后续源码原生执行不追认已发布v0.1.0-rc.3-preview.1 ARM64资产；其摘要与这四个CI构建不同，发布物ARM64仍为构建证据。ARM64 DBS/HISDBS厂商镜像、分区整盘映射、多设备/映射栈、Linux6.x实际控制、24h+24h、七天及两个已发布次版本的条件继续开放。
