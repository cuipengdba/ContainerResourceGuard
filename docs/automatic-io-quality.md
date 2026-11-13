# 自动标定质量直接进入状态与日志

开发状态：两个开发分支已实现，Windows聚焦单元和vet通过；原生ARM及两架构cgroup CI通过，首次构建CI在安装包文档链接检查失败。修复包内容后继续完整CI；尚未发布，也没有替换preview.4或真机冻结程序。

对应P04.1和用户自动标定/日志需求。原先`profile inspect`能显示质量，自动启动却只记录calibrated/reused。新增输出`automatic_io.quality`，并由现有`automatic_io_prepared.fields.result.quality`写入日志；无需新配置。包含samples、四维spread_percent、warnings；离散度仍为原有(max-min)/中位数×100，超过原25%阈值给警告。少于三次或旧v1无样本保持信息不足警告，不能编造测量或当前性能保证。

首次完整保存成功后才附上所选设备质量；复用时从匹配稳定身份的设备读取，其他设备的质量不能串用；保存失败不展示为已接受质量。沿用现有Quality计算，代码只增加五行状态赋值/字段，不修改profile/中位数/任何百分比/IO四轴/资源或日志保留参数，不自动重标定或放宽额度。输出字段可追加，严格配置和journal输入不变。

[本地检查](test-results-automatic-io-quality-local.json)覆盖七个新增情景：首次稳定/波动、复用波动、匹配设备位于另一设备之后、旧无样本profile、首次测量合并旧设备、保存失败；复用不测量不保存，原基准值不变。首次Windows夹具直接调用Linux目录fsync失败已保留，修正为prepareAutomaticIO已有注入写入边界；生产AtomicJSON和持久化测试未改。

首个开发提交分别为[兼容分支](https://github.com/cuipengdba/ContainerResourceGuard/commit/67a9db1be0f334d16eaf32f157ac83c988c7cbb7)及[分区分支](https://github.com/cuipengdba/ContainerResourceGuard/commit/ec4376c27ba988759d8a6068a1831fc3d5191ea5)。这次变化用于诊断质量，不作为默认20%业务失败的修复或稳定1.0接受。

## 同期重建观察

[原冻结矩阵](testing-high-percent-startup-psi-compatible.md)仍使用准确preview.4。节点11:11UTC观察：DBS20/HIS20首次分别62.508/69.325秒就绪，但保留数据重建均未在原300秒内SQL/API就绪；原ls liveness成功不能替代业务就绪。整体矩阵尚未结束，其他格继续。

[只读证据](test-evidence-rebuild-controller-and-startup.json.gz)确认DBS失败重建的新cgroup/journal身份、缓存profile摘要、三项实际控制符合原宿主/三次中位数公式，automatic_io=reused，外部20GiB memory.max不变。这是独立资源控制证据，不给原144项补算通过；业务失败保持。

原start日志显示再次解包约数秒，不能直接把整个超时归因于解包IO；预算内PG探针最后exit2，采样CPU未见节流，单个postgres程序在登记清单中；这些不能确定数据库停在哪一阶段。结束后etcd连接失败在Pod收尾窗口出现，不能拿它解释预算内原因。仅有已过滤/截取日志，尚无完整PG启动根因链，不声称磁盘或Agent因果。
