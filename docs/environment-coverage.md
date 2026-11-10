# 环境覆盖与未完成边界

本页落实P06/P10.4的证据索引，按实际程序、环境和负载区分；不是最终1.0支持承诺。三个资源、权限失败放行和日志语义见[独立百分比](independent-percentages.md)、[当前验收](current-acceptance.md)。每行独立成立，不把架构、内核和存储任意交叉组合成已测环境。

| 程序/环境 | 实际覆盖 | 证据与边界 |
|---|---|---|
| 已发布7638预览；Linux6.8.0-1070-azure/7.0.0-1017-azure、AMD64/ARM64、Docker28.0.4、独占dm/loop整盘ext4 | 原下载包四格88项控制器检查 | [原包报告](testing-released-cgroup-ci.md)；占位容器，非ARM厂商业务，非物理独立盘 |
| 当前d370；Linux5.14/AMD64、containerd、单XFS/LVM数据设备、原DBS/HISDBS镜像及路径 | 两格各600秒/12项业务、20故障场景108项、维护22项、四次冷启动44项、自身三场景1800秒开销 | [业务](testing-partition-realpaths-business.md)、[故障](testing-partition-realpaths-faults.md)、[维护](testing-partition-realpaths-maintenance.md)、[冷重建](testing-partition-realpaths-cold-rebuild.md)、[开销](testing-partition-steady-overhead.md)；仅手动64预算与私有64MiB负载 |
| 当前d370；Linux7.0原生AMD64/ARM64、Docker28.0.4、独占dm/loop整盘ext4 | 两格44项控制器；ARM原生单元/race/CLI/辅助链 | [当前程序报告](testing-partition-integration.md)；不扩大为ARM DBS/HISDBS或当前程序164项分区运行 |
| 分区程序468fe73；Linux6.8/7.0原生AMD64/ARM64、Docker、独占scsi_debug一盘两个真实GPT/ext4分区 | 四格164项、父盘共享预算、稳定profile及新ID | [分区报告](testing-partition-cgroup.md)、[接入合同](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/docs/test-plan-partition-integration.json)；生产源码等同不等于把运行来源改成d370，双分区不等于两块独立物理盘 |
| v1/混合/未知布局 | 写入前跳过并打印版本；版本输入模拟已验证 | [门禁与日志报告](testing-three-percent-cgroup-logs.md)；没有真实v1内核运行结论，不提供v1控制写入 |
| v2控制/状态/profile只读及辅助异常 | 当前原镜像故障夹具验证业务放行 | [108项故障](testing-partition-realpaths-faults.md)；已生效的有限配额会保持，权限丢失不能承诺自动恢复原值 |
| 正式fc2 observe /固定d6 enforce | observe已有22h观察，完整86400秒及等时enforce未接受 | [持续验收](continuous-acceptance.md)；与d370七天组件的程序和计时独立 |
| 当前d370七天组件 | 已开始，首周期各10项内容及清理完成，仍native-pending | [七天状态](testing-seven-day-current-candidate.md)；完整604800秒、28周期和实际老化状态后置未完成 |
| ARM厂商业务、独立物理多设备、其他运行时/内核、节点重启/掉电、未知复杂存储栈 | 尚无完整目标验收 | 保持未测/未支持结论；原生CI、交叉编译及单盘分区结果不能替代 |

默认三项各20是产品默认配置，不是已验证的DBS/HISDBS性能推荐。旧默认20%四格业务均未接受，记录不改为通过；CPU7.2核、内存20001980416B、读写各64MiB/s及4096IOPS只对应上述手动测试，不换算为通用推荐比例。

自动选盘只覆盖容器里可确认的合格可写本地块文件系统，百分比IO依赖已测基准；Overlay/网络存储/未暴露设备不能猜测映射。环境不满足时日志解释跳过，原业务独立启动。[自动标定](automatic-io-calibration.md)和[分区边界](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/docs/partition-io.md)详述身份规则与首次真实IO负载。

稳定发布仍须完整业务长测、实际老化状态后置、最近两个已发布次版本维护、52项审计和最终支持范围判定；工程能力、源码等同、CI绿色与生产部署分别记录。该节点全局PSI接口缺失的事实不因CI环境有接口而消失。
