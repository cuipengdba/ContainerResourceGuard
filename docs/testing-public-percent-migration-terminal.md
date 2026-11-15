# 公开程序默认百分比控制层迁移终态

实际公开preview.4→preview.5，DBS/HISDBS各24项、共48/48项通过，0失败/0未执行。候选源码`ced461705ebc27315a59aefe463f9b4af47130a3`，发布程序/标签/八项附件不变。job `eb067f58a193e22740938ffdd6cea9e9a86d45fbab54d168bb1ff98de9f1d537`，plan `e01b628b45cf910fc64f825bc9ae868149e49d6e5c569340b3cf70d0608ba781`。冻结预检记录保留原样，当前终态取代其中“尚未启动”的时点状态。

原厂镜像和实际挂载路径，每角色先后两个不同Pod/container ID，复用各自持久配置、profile、journal和日志。每容器只运行本容器的CRG；没有一个Agent管理多个容器。全程业务gate关闭，原DBS/HISDBS业务及缓存helper没有启动。本轮只接受资源控制层迁移，不接受SQL/API/备份性能或默认20%完整业务。

## 实测行为

- 空配置`{}`，CPU、内存和IO各自默认20%。CPU按宿主在线CPU、内存按宿主MemTotal并按页取整、IO按真实三样本标定带宽独立换算；Kubernetes原硬上限仍适用。
- 实际旧程序自动选盘、标定并写入真实四轴IO journal；quiesce后安装实际新程序，新版维持BPS，恢复旧CRG自有IOPS到原基线max。profile字节与纳秒mtime保持，不重复测速。
- disable恢复八项原值后再次启用，保留真实active journal删除Pod。新Pod具有不同UID、container ID和cgroup，自动归档旧journal、重新发现自身身份，只操作新leaf。
- 已验证新leaf的外部IOPS基线197/149被保留；新版仍只设置CPU、memory.high和IO带宽。最终disable恢复当前外部基线和空journal。memory.max、pids.max、cpu.weight、io.weight、memory.swap.max均未改动。
- 每日日志包含v2识别事件并跨重建追加。此短测不新增30天或1GB清理通过的声明；滚动保留功能与既有独立验收记录保持。

|角色|cpu.max|memory.high B|新版自有IOPS恢复后io.max|新ID外部IOPS保留后io.max|
|---|---|---|---|---|
|DBS|480000 100000|13334654976|`253:0 rbps=5272984 wbps=3789080 riops=max wiops=max`|`253:0 rbps=5272984 wbps=3789080 riops=197 wiops=149`|
|HISDBS|480000 100000|13334654976|`253:0 rbps=7578057 wbps=6527754 riops=max wiops=max`|`253:0 rbps=7578057 wbps=6527754 riops=197 wiops=149`|

IO标定是该节点当时的实测基准，不能视为磁盘固定物理极限或吞吐保证。全程原额度及门槛不放宽。

## 独立证据复核

20份305712字节准确原件与终态索引、协调器和source-map逐项核对；八份实际控制值/状态/journal快照用冻结只读断言重新计算，34项独立证据检查通过。独立核对实际公开程序buildinfo/摘要、真实镜像、profile字节/mtime、身份变化、旧journal归档、外部IOPS、五项未管理控制、最终八项当前基线/空journal、安装收据与日志事件。旧Pod中间disable的瞬时读回和日志前缀保持由冻结驱动检查点记录，未伪装成额外独立读回。

终态观察时，原runner和两driver均已退出；两namespace、四组cgroup父叶、八个登记PID/start实例独立确认消失。仅操作授权隔离测试夹具；未重启其他业务或放宽配额。公开证据不导出私有Pod/env/数据库凭据。

[完整指标](test-results-public-percent-migration-terminal.json)、[准确原件gzip](test-evidence-public-percent-migration-terminal.json.gz)、[冻结计划](test-plan-public-percent-migration.json)、[驱动与预检](testing-public-percent-migration-frozen.md)。

## 尚未完成的范围

原默认20%完整600秒业务失败记录不变；本轮不借用已完成manual业务16/16或manual在线维护40/40的业务时长。原52项任务逐项状态、专用24h观察+24h执行、新源码七天及已声明硬件范围继续，稳定1.0未发布。当前可下载版本仍为工程预发布preview.5。
