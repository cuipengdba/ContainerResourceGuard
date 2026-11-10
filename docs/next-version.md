# 下一版：v0.1.0-rc.3-preview.1

当前工程预览候选实现用户最新R27/R29/R30，两套候选的Linux检查和38项隔离实测已通过，见[测试证据](testing-three-percent-cgroup-logs.md)。本次发布main的工程预览包，组合开发线不作为发布物。正式RC3、稳定版及1.0的业务与长期验收未完成，不因本工程预览标签提前关闭。

## 交付内容

1. 只接管CPU、内存、IO：cpu_percent/memory_percent/io_percent，各自默认20%，配置可为{}。
2. 设置前检测cgroup：v1跳过且正常退出，混合/无法确认也不写；v2校验自身身份、权限、上层限额及内存下调安全后逐项执行。
3. 默认自动选最大合格本地磁盘文件系统、首次后台标定/稳定设备缓存复用；容器或Pod重启重新发现自身ID。
4. 每日日志、30天/总1GB滚动清理，版本判断/实际结果/失败原因可见，日志无权限/满盘仅降级stderr。
5. 严格一容器一Agent，资源与原缓存辅助程序/原业务独立启动，业务不等待辅助程序；缺权限不阻断原业务。

[配置说明](independent-percentages.md)、[日志规则](logging.md)、[接入方案](integration.md)、[需求](requirements.md)、[任务](tasks.md)。使用新配置前核对二进制版本，正式RC2不识别三个新字段。

本预览不改现有业务部署；使用独立配置/状态/日志。若以前跑过八项开发候选，先使用旧候选disable恢复其额外限额后再切换；本版不擅自重置原有外部控制。

深入功能继续在next/compatibility-contract开发，包括安全热重载、诊断/指标、升级/回退及兼容性验证。尚未全部发布，不把开发分支中的额外功能当成本预览支持范围。原预览AMD64/ARM64资产现已在[实际Linux6.8/7.0四格原生控制器88项通过](testing-released-cgroup-ci.md)；后续源码CI另记，ARM厂商业务、物理多设备、分区映射与长期DBS/HISDBS业务验收仍未完成。

## 下载与配置

[GitHub预览发布及下载](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v0.1.0-rc.3-preview.1)。选择对应架构tar.gz及SHA256SUMS，按[安装说明](installation.md)核对。此发布仍为prerelease；两架构原资产有上述占位容器控制器实测，ARM厂商业务尚未验收。

```json
{"cpu_percent":30,"memory_percent":40,"io_percent":25}
```

未写的一项独立默认20；无新配置时也默认三项20%。进程命令为`crg run --config /etc/crg/config.json`。cgroup版本日志事件为`cgroup_detected`，查看每天的`/var/log/crg/crg-YYYY-MM-DD.log`或容器stderr；每个容器分别运行。

第12轮最新三资源程序四格真实路径业务验收已结束：24项通过，各格完整600秒、SQL/API零错误及10项引擎内容通过，夹具清理确认；仅为预先声明的手动64MiB/s预算。第13轮在线升级/回退已终止：首次安装失败，后续回退及600秒未完成；24h+24h和至少7天仍待完整实测。见[按程序摘要归档的结果](testing-three-resource-business-matrix.md)。

第13轮DBS/HISDBS首次安装均拒绝，旧预览缺少锁/日志协议广告，安装文件摘要保持、recovery为空，夹具清理；保留失败及原始输出未留存的证据限制，不绕过协议保护。见[维护失败与诊断](testing-three-resource-online-maintenance.md)。

第14轮最新三资源程序×DBS/HISDBS的40场景、216项辅助故障检查通过，全部夹具清理；独立30%配置，只证明辅助隔离，未追认自动30%持续业务性能或第13轮维护。见[新源码完整故障矩阵](testing-three-resource-fault-matrix.md)。

第16轮默认空配置首格main/DBS完整600秒但SQL10次/API57次错误，未通过；Pod清理命令失败使其余三格未执行，终态namespace已移除。保留实际20%限额、失败与诊断，见[默认配置结果](testing-three-resource-default20-business.md)。

第17轮真实路径备份/新Pod ID冷重建四格、8次启动、88项检查通过，数据/独立逻辑恢复库/一对一身份/日志追加及新容器原值恢复核对，全部夹具清理；仅为手动64MiB/s预算。见[冷重建结果](testing-three-resource-cold-rebuild.md)。

第18轮默认20%剩余三格补测结束：18项启动/控制/日志通过，三格业务组合均失败；main/HIS有完整失败原生结果，两个组合格仅有未完成快照，不计600秒通过。清理确认，连同第16轮四格均未通过，见[补测结果](testing-three-resource-default20-supplement.md)。

发布后工程进展：旧observe到已声明候选的[首次接入/旧参考入口恢复四格68项通过](testing-observe-first-adoption.md)；后续源码在原生AMD64/ARM64的[独占dm/loop控制器四格88项通过](testing-native-cgroup-dm-loop.md)。两项均有精确来源和范围，不替代本预览ARM64资产、默认20%业务或长期条件。
