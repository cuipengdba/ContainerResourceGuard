# 三项百分比、cgroup版本门禁与日志实测

2026-11-10，针对R27/R29/R30；对应工程预览`v0.1.0-rc.3-preview.1`。[机器可读结果](test-results-three-percent-cgroup-logs.json)。两套源码和二进制分别核对，未改正在运行的正式基线或原业务部署。

| 候选 | 程序源码 | Linux amd64二进制SHA256 | CI |
|---|---|---|---|
| 本次发布的main预览 | 7638ee9f871287d1056e267034e0c4e46903b66e | f07973272313db26d359797dda4665145f7dd6490bac2a55f9084bd367faf361 | [通过](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42785715660) |
| 未发布的1.0组合开发线 | d6ea6572dc423397ca496a5277d2af4496c6970c | 0a0799f5c992b8b4ddb983bec12a8061965a4fbed4c419d47cd7c7607dbecf15 | [通过](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42785715856) |

## 结果

两线Windows测试/vet、测试节点Go1.22.5 Linux vet及全包race/cover通过；每线6项辅助故障和6项生成补丁故障通过（原业务退出码37、缓存启动保留）。Go1.27.3构建Linux amd64/arm64成功，ARM64未执行真机验收。日志包语句覆盖率78.4%，Linux单测包含跨日、并发、链接/FIFO保护、真实1GB稀疏文件清理和失败降级。

独立临时Pod的实际cgroup v2和日志检查**每线19项、总38项全部通过**：

- 子挂载命名空间模拟v1、hybrid、unknown：正常退出、版本日志清楚，控制文件无变化、资源状态目录为空、无自动profile；v1显式calibrate也跳过。
- v2只读cgroup：记录v2及只读失败原因，原PID1继续运行，原控制值不变；不以v2检测成功冒充限额成功。
- 默认20%仅生成CPU/内存/IO三类设置，回读cpu.max/memory.max/io.max；五项其他控制值与原值一致。
- 分别10%CPU、15%内存、30%IO，四项IO按各自标定基准换算；CLI25%/25%/40%只覆盖对应三项。
- 同设备标定文件内容及mtime保持，后续启动复用；不反复测速。
- 日志0600、每天一个JSON Lines文件、stderr与原stdout结构保留，记录启动/版本/标定/资源/退出事件。
- 实际只读日志目录、256KiB临时文件系统ENOSPC：文件日志降级stderr，三个资源继续执行、PID1保持。
- 第30天前删除、第29天保留、不删除业务其他文件；两个600MB稀疏日志先删最旧，总量不超过1GB。
- 当天1GB稀疏日志清空重写并保留清理标记，不生成编号分片。
- disable恢复三项真实原值，其他控制仍未改；Pod新ID重新发现、基准复用、同日日志追加、旧journal隔离。
- 业务哨兵未变、测试Pod OOM计数为0；最后临时namespace API核对已不存在。

## 判定边界

v1/混合/未知使用隔离proc输入模拟，**不是v1真机内核验收**。实际限额和日志测试使用原镜像中的占位PID1，不运行原DBS/HISDBS业务，因此不能替代SQL、API、备份/同步/独立恢复及持续性能验收。内存检查使用低占用夹具，不能证明正式业务任意限额下不会OOM。

旧八项R28候选两线的28项工程检查通过，但需求已被R29收窄，其二进制不作为本次交付。历史自动30%/手动16MiB/s业务失败记录保留，不用本次38项抹除。原24h observe基线继续，24h enforce及至少7天业务验收未完成；缺ARM64、Linux6.x和多设备节点的范围仍未验证。

发布包里的BUILD.json分别记录程序源码和打包文档修订；本次测试针对上表程序源码，后续仅文档/证据提交不等同重新测试另一个程序。
