# 组合候选：长时工程检查结果

2026-11-10，以下均为未发布开发候选。两个源版本分别记录，不能把旧二进制的开销数字说成新自动标定启动过程的数字。见[去标识数值摘要](test-results-combined-long-linux-amd64.json)。

源码 `1bc9bcb0a6d5c446f6e36220b5ad4db1bdef8bb7`、Go1.27.3实际程序 SHA256 `41713d40f380046ef2489cb2f978ce959984d73df767f8ca552b7f0ac287ee42`，在三份独立占位容器分别覆盖健康、持续导出失败、只读cgroup。沿用[开销验收](overhead-acceptance.md)原预设：45秒预热后实际测量1800.0255秒，每组181个样本，15秒协调周期、读写64KiB/s及8 IOPS，三组全部通过并清理namespace。

| 场景 | 单核平均CPU | RSS最大 | Agent写入增量 | 最小状态写入间隔 |
|---|---:|---:|---:|---:|
| 健康 | 0.016667% | 8,257,536B | 139,264B | 300.000s |
| 持续导出失败 | 0.016111% | 7,864,320B | 20,480B | 300.000s |
| 只读cgroup | 0.026111% | 8,495,104B | 1,126,400B | 300.030s |

三组均保持同一Agent进程，无新增OOM kill。其私有完整样本和失败前置检查保留。该轮采用手动固定预算，不包含R26首次标定的真实磁盘负载，也不是DBS/HISDBS业务性能测量。

Go1.22.5最低源码工具链下，两个候选各完成两个解析器的10分钟fuzz，均退出0；systemd限制CPU50%、内存512MiB、任务48、总运行1500秒。实际耗时包括Go收尾，以下不将配置的10分钟冒充精确墙钟时长。

| 源码前缀 | 解析器 | 执行次数 | Go实际秒数 |
|---|---|---:|---:|
| 1bc9bcb | 配置 | 2,551,832 | 601.133 |
| 1bc9bcb | IO profile | 2,498,437 | 601.091 |
| 74693ef（含R26） | 配置 | 1,326,447 | 744.357 |
| 74693ef（含R26） | IO profile | 1,593,451 | 601.173 |

首次基准创建的磁盘写入另见[自动IO实测](testing-automatic-io.md)，不能按上述稳定状态写入预算判定。有限fuzz不证明所有输入绝对安全；24h+24h、至少7天、厂商业务接口、真实掉电及未测硬件矩阵仍保留独立门槛。

## 三独立百分比当前源码：Windows解析器补充

50671aa原样源码在Windows/amd64、固定Go1.27.3下完成两个解析器各10分钟fuzz；只在独立工作区补充12条明确列出的合法/非法语料，包括`{}`、三个百分比、遗漏默认、越界、null、重复字段、旧新混用及未知字段。未修改产品或原测试源码。[运行前语料与计划](test-plan-three-resource-parser-fuzz-windows.json)及[结果](test-results-three-resource-parser-fuzz-windows.json)单独归档。

| 目标 | 执行次数 | Go报告秒数 | 含编译/收尾墙钟秒 |
|---|---:|---:|---:|
| FuzzDecodeConfig | 5601420 | 602.825 | 646.187 |
| FuzzDecodeProfile | 7503502 | 600.979 | 602.829 |

两项均退出0。GOMAXPROCS/并行worker各2，GOMEMLIMIT256MiB为软目标；未宣称Windows硬资源预算或Linux真机结果。有限fuzz不替代DBS/HISDBS业务、正式长时及硬件验收，也不能把旧74693/1bc9数据合成当前源码的统一执行量。

三资源/每日日志当前d6ea657程序已按[冻结计划](test-plan-three-resource-steady-overhead.json)完成三场景实际1800秒稳定开销，均通过且夹具清理，见[独立结果](testing-three-resource-steady-overhead.md)。[固定启动快照](test-start-three-resource-steady-overhead.json)仍仅表示开始时刻；当前终态另行归档，旧长时源码结果不替代本轮。
