# 已发布 preview.4 → preview.5：同预算在线维护终态

本轮限定范围通过：计划40项，实际40项记录、40通过、0失败、0未执行。节点终态观察2026-11-13T19:37:16.807554+00:00。使用实际公开preview.4与preview.5包内的AMD64程序，不重编译替代；源文件和冻结计划分别为`e7239815f60ca28a0bb5e59735c3e61bf8bc68458736f47d31d9039355760b6a`、`fb6dc754e3c0b260c3ba869ec30f682a94641e3e9217d4c8bd8c2a8e7df5a6a1`。

| 角色 | 通过/记录 | native秒 | SQL次数/错误 | API次数/错误 | 维护命令数 | 八项原值与空journal恢复 |
| --- | --- | --- | --- | --- | --- | --- |
| DBS | 20/20 | 600.3298759169411 | 301/0 | 121/0 | 16 | True |
| HISDBS | 20/20 | 600.3051197489258 | 301/0 | 121/0 | 16 | True |

两角色各自新隔离namespace、原DBS/HISDBS镜像/启动/真实路径及原CCG，每容器只维护自己的一个Agent。CPU7.2核、memory.high20001980416B、读写64MiB/s、手动可选IOPS4096保持，原外部20GiB硬上限不动；没有自动标定，不改变产品默认百分比。原手动完整600秒与十项备份/同步/独立恢复16/16通过是另外的前置证据，本轮不重复或混算引擎内容。

按启动前冻结标准独立核对原600秒、零SQL/API错误、请求最大5秒、p95桶上界1秒、98%计划覆盖、64MiB数据、原主库/PID1/CCG不重启。在线步骤包括quiesce、原子安装立即回退、运行新版后未变化快照回退、再次升级、变化配置拒绝、全新收据显式反向安装及旧版恢复。变化负例只在暂停写者时临时增加interval_seconds=16，不改资源额度，拒绝后准确恢复原配置。所有在线命令及后续resume必须完全位于实际成功native窗口内；单写者、额度、journal及最终disable恢复均逐项检查。详细原始指标、时段、收据、控制值和失败信息在完整证据内，不靠总状态词接受。

两namespace、两组父叶及59个登记进程实例独立核对消失；26份准确原件共329417字节，经索引/source-map/逐文件SHA256/协调器报告联合核对。[逐项判定](test-results-preview45-manual-maintenance-terminal.json)、[完整准确原件](test-evidence-preview45-manual-maintenance-terminal.json.gz)、[冻结计划](test-plan-preview45-manual-maintenance.json)、[17项资格与真机预检](test-results-preview45-manual-maintenance-preflight.json)、[冻结工具](../tests/preview45-manual-maintenance-frozen/README.md)。

本结论只覆盖两个实际公开预发布程序、规范manual高水位配置和本次私有可写安装路径。未声称百分比策略迁移、全部分发安装器/生产镜像持久化、两个正式次版本、Kubelet liveness、独占24h+24h或七天已验收。共享amd64/Linux5.14/单物理设备，未测厂商ARM等硬件范围继续。原默认20%失败、52项任务及所有历史失败保持；稳定v1.0.0尚未接受或发布。
