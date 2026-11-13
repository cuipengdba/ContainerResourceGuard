# 源码集成与当前验收状态

最新用户选择已覆盖旧R10：下一版io_percent仅限制标定读写BPS，IOPS留手动；既有外部IOPS保留，旧自有限额按身份/journal安全迁移。实现与新增回归见[IO带宽策略](io-bandwidth-policy.md)，当前待准确Linux/原生/真机验证；preview.4及旧结果保持，原52项不补算完成。

已建立[草稿PR #1](https://github.com/cuipengdba/ContainerResourceGuard/pull/1)，准确工程验证源码为7823d8d5da8d1f25909e26660697b36f0e0e9e2e。[来源与集成范围](https://github.com/cuipengdba/ContainerResourceGuard/blob/release/integration-v1/docs/source-integration-plan.json)、[验证分析](https://github.com/cuipengdba/ContainerResourceGuard/blob/release/integration-v1/docs/test-results-source-integration-current-CI.json)及[精确证据](https://github.com/cuipengdba/ContainerResourceGuard/blob/release/integration-v1/docs/test-evidence-source-integration-current-CI.json.gz)可复查。

该源码完整Linux格式/vet/竞态/集成/两架构包/完整性/新检出可复现通过；原生ARM64有226个测试通过事件，实际cgroup两架构共44项通过；Linux6.8/7.0×amd64/ARM64真实同盘两分区共164项通过，含memory.high、外部memory.max不变、旧发布程序独立恢复八个原值、IO/CPU负载、几何失效重标定及完整清理。不是独立物理多盘或DBS/HISDBS全业务验收。前两轮失败均保留，未通过的旧记录不改写。

PR仍为草稿，未合并main、未部署、未重新发布；main程序源码仍旧，当前下载仍为v1.0.0-preview.4。集成候选包含开发分支已完成的IOQuality日志和公共文档包闭包修复，不能移用preview.4的二进制摘要、业务结果或七天经过时间。候选也保持每容器一对一、v1跳过、三项独立百分比默认20、memory.high和每日30天/1GB日志；未增加其它默认资源控制。

[已完成的手动IOPS对照](testing-manual-IOPS-comparison.md)使用preview.4，不是此候选的业务通过。默认IO四轴百分比语义保持；用户口径选择仍待答复。原52项、原百分比矩阵失败、物理备份/同步、独占24h+24h、七天/老化、正式版本迁移和未满足硬件范围继续按原定义验收，稳定1.0尚未通过。
