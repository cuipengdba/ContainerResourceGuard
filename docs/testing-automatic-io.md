# 默认自动 IO 标定实测（RC3 / 1.0 候选）

2026-11-10，在授权测试节点的独立原镜像占位容器中，两开发线各11项、共22项实际检查全部通过；私有状态文件系统故障另9项通过。不是DBS/HISDBS业务验收通过，真实路径业务结果单独记录。完整摘要见[结果JSON](test-results-automatic-io-linux-amd64.json)。

| 候选 | 源码 | Go1.27.3 二进制 SHA256 | 首次标定 |
|---|---|---|---|
| RC3 | `023becfbed94045b16439b8cbdb61e80520c00bb` | `b9baa7e3fd39fcccf9d3ca5adf6640c0a7836e05e90aa6744f4da40e01cff615` | 51.278s，v1汇总 |
| 1.0组合候选 | `74693efcb01441fdb6a91269bbbedff3e16c4691` | `c6be514f289bbe9580701afb93ffdc1a21a0dec0a689c86e32f219fcd97651b9` | 48.027s，v2三次样本 |

两者均直接运行 `crg run --percent 20 --once`，没有directory、output或io-profile参数。自动选择容器内最大合格可写XFS文件系统，容量965,520,392,192字节；多个bind目录同属一个设备时按路径字典序选到`/etc/crg`，不代表配置目录自身有这么多文件。16TiB容量的私有tmpfs没有被误选。读写BPS和IOPS均写入并回读，独立业务哨兵文件原字节不变，临时测速文件删除。

再次启动复用profile，不改摘要或mtime；删除并重建测试容器后ID改变、旧journal隔离，新容器仍按稳定设备身份复用。输出目录只读时分别在0.763s/0.613s内降级，没有测速；已有IO上限时保留外部限制且不测；observe/off不生成profile。两容器PID1、哨兵及OOM计数保持预期，测试namespace删除。

两个源码在测试节点Linux Go1.22.5分别通过vet、完整race/cover、6类可选helper故障和6类生成接入脚本故障；实际运行的ELF为固定Go1.27.3构建。GitHub CI [RC3](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42742885845)与[组合候选](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42742885059)均通过，后者含两架构构建、包检查及来源证明；交叉构建不等于arm64真机通过。

另在自身挂载命名空间建立256KiB私有tmpfs，实际填满产生ENOSPC，不填宿主磁盘。连续64.638s/11次满状态失败及60.727s/10次只读状态失败均保留原journal、控制值和PID1。disable在满盘时诚实失败并保留限额；释放空间后可应用新额度，最终精确恢复运行时原值，宿主目录/挂载不变，namespace删除。

首轮45秒超时失败及旧只读锁原因误判保留在JSON。前者未计足三轮文件预填充，现为180秒总协作期限；正式测量仍是每阶段3秒×4阶段×3次。后者只把实际锁竞争归类为ErrLocked，文件系统错误保留原始类型。没有通过缩短测试样本、放宽业务5秒/1秒阈值或改写历史失败取得通过。

真实硬件只有一个合格块设备，最大容量排序/不可写/满空间/覆盖挂载等差异由Linux单元检查补充，不冒充多块真盘证据。此处不关闭DBS/HISDBS真机路径、24h+24h、至少7天或完整升级回退验收，也不表示新版本已经发布。

## 真机路径启动补充

两类原镜像使用真实容器路径及原CCG只读挂载，最小配置只有percent30：RC3 DBS自动选择/etc/crg、53.124秒就绪且managed，组合候选HISDBS选择/data、63.616秒就绪且managed。两套后续业务短测均失败，不能把本页22+9项工程检查或这两项启动结果等同业务通过；详见[完整失败与后续对照](testing-realpaths-progress.md)。

自动标定候选的真实路径辅助故障测试已完成：RC3/DBS与组合候选/HISDBS各10场景，共108项检查通过，夹具全部清理；不代替业务性能与长时验收。见[故障实测](testing-realpaths-faults.md)。
