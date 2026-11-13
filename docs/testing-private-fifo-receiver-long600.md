# 接收端自有 600 秒与 memory.high 交付复核

[结果](test-results-private-fifo-receiver-long600.json)、[冻结源码](../tests/private-fifo-receiver-long-frozen-882/manifest.json)、[完整原件](test-evidence/private-fifo-receiver-long600.json.gz)。本轮仍使用 [preview.4](releases/v1.0.0-preview.4.md)：CPU、内存、IO 独立百分比，各默认20%；内存百分比写 memory.high，不新增 memory.max。外部硬上限、每日/30天/1GB日志、一对一及辅助故障放行合同保持。

## 实测与边界

882 在现有测试节点使用与867相同摘要的接收端和写端，运行一个专属宿主机私有 FIFO。写端每5秒产生一条显式标记为 synthetic_receiver_probe 的记录，首尾共121条，实际600.000324秒；这些记录未执行 HTTP、SQL、Pod 或 BPF，不能作为业务时延、请求端口或完整联调证据。

接收端保留完整14047字节，逐字节长度、SHA256和全部121个序号与写端预期相符，无错误、溢出或 incomplete。七项检查全部通过。真实线程、读取及目录描述符已关闭；独立只读观察确认原父进程和写进程身份均退出、专属通道目录消失，冻结四个源码摘要全部一致。

接收端父进程从模块加载及通道准备到导出、fsync、关闭和清理，实际603.697343秒，CPU1.519265秒，约占一个核心的0.251660%，满足本次1%门槛。初始import及最终报告序列化不在CPU计量窗口；写端子进程CPU另记0.117732秒。整个父进程MaxRSS观测16128KiB仅为观测值，未设置RSS硬限额，也不能描述为整个Agent开销或16MiB的perf映射预算。

## 用户选择的内存策略

本轮对精确preview.4源码额外执行六个本地Windows回归用例：百分比及手动配置只生成high目标、保留外部high/max、仅恢复仍自有的旧max后设置high、外部冲突不覆盖、缺少high不回退max且CPU仍处理、high低于用量的恢复。六项均通过；这是本地策略回归，未新增Linux真机资格。公开release、tag、八个附件ID/长度/摘要和发布说明与既有逐字节下载记录相符，本轮没有重复下载或替换附件。操作与迁移见[内存策略](memory-reclaim-policy.md)和[逐容器升级步骤](upgrade-preview3-preview4.zh.md)。

memory.high是回收/节流目标，允许超过；它自身不触发OOM killer，外部硬上限与宿主内存压力仍可能OOM。程序不主动清除数据库工作集。历史旧硬限额仅按同身份journal和当前归属恢复，不能一律写max。

## 仍未完成

本轮完成的仅是新接收端自有600秒CPU资格；原工厂两角色600秒/11区间/32业务检查与新接收端/BPF完整联调尚未完成。BPF目标激活、在途调用与停止边界仍未修复，旧831诊断失败及全部历史超时保留。默认20%业务、正式24小时、新策略七天及老化后置、原52项和稳定1.0条件继续开放，不能据本轮通过发布稳定版。
