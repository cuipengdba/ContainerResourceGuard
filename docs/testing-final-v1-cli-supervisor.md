# 固定最终候选：CLI状态与可选启动安装验收

本轮已于节点2026-11-15T11:56:13.864889+00:00唯一启动，runner 588532/start168371697。11项输入、17项本地核对和原生准入保持；DBS首次快照8项主检查、20项在线子检查通过，正在自然老化等待。两角色完整600秒及终态仍待。旧1523稿漏掉移除维护块后的两个恢复配置变量，在上传前静态检查拦截，原字节保留，新1525显式初始化；不是产品或真机运行失败。

仅使用准确源码 ced461705ebc27315a59aefe463f9b4af47130a3 的固定 v1.0.0 ELF 9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8，不升级或重建程序。沿用1501实际通过的原业务夹具/原生worker与完整配额契约；契约遗留 old/new doctor 字段在本轮均为同一个最终ELF的实际只读doctor结果，不冒充两版本。

DBS/HISDBS分别新namespace/输出/run-id，各13项主检查，总26；每角色22项在线子检查和2项post600子检查。SQL/API原600秒、零错误、最大5秒、p95桶上界1秒、98%覆盖率与64MiB内容、主库/业务/缓存身份不变。manual固定7.2CPU/high20001980416B/双向64MiB每秒/手动4096IOPS，外部8CPU/20GiB保持；默认20%性能失败保留。

实际 status/doctor/preflight 的human与JSON核对自身目标、主机容量、手动请求、目标及实际三项控制；状态四次观察分别为初始持锁、quiesce后未持锁、自然快照年龄至少305秒、最终单写者恢复。status读取不改持久快照字节或mtime，内存统计不同次采样不要求原子相等。没有虚构stale布尔字段。quiesce期间保留journal/额度及业务，按实际cgroup inode写锁检查无写入者；可选helper短暂启动的disabled尝试会在获取资源锁前退出，不当作持续托管者。

在原600秒业务内完成两种已知公开源码模板（shutdown结尾 || : 与 || true）的plan、活动锁拒绝、受信源/辅助脚本/ELF摘要错误拒绝、未知布局/别名拒绝、静默后的副本安装、重复旧源拒绝、仍有自有journal时拒绝卸载。原厂私有脚本仅复制到私有目录，核对原摘要；支持布局才允许副本安装，否则明确拒绝且不改动。公开证据不含私有脚本/备份内容，不执行任何脚本副本，不改实际只读CCG或业务启动链。

自然老化及重新enable/单Agent恢复必须全部位于本轮成功原600秒内。业务测量完成后再disable恢复8项运行时原值和空自有journal，随后合法卸载所有已安装副本并核对原字节/模式；这一post600阶段不冒充在线动作。只读命令以及模板安装都不是可选helper故障启动链验证的替代品，原有fail-soft来源单列。

启动前准确要求：1465完整诊断业务和71登记记录清理；1461两档1800秒开销与全部自有对象清理；1501升级回滚40/40、64登记记录及runner/driver/两namespace/父叶清理。原生预检已执行同一runner的实际只读前缀；启动时再执行一次。旧七天任务保留，1396正式长测未开始。新夹具需28GiB可用内存、20GiB磁盘，运行保持8GiB内存余量。

P07.1/P08.1等待本轮实际证据；当前16/52完成和稳定版未接受保持。未来格式、镜像持久化、故障压力和长期等分别继续；不是默认20%性能、厂商ARM/独立物理多盘、自动业务故障切版或两次正式minor证明。

[原设计](testing-final-v1-cli-supervisor-design.md)、[冻结计划](test-plan-final-v1-cli-supervisor.json)、[准确工具](../tests/final-v1-cli-supervisor-frozen/README.md)、[适配记录](test-adapter-final-v1-cli-supervisor.json)、[本地核对](test-results-final-v1-cli-supervisor-local-preflight.json)、[原生准入](test-results-final-v1-cli-supervisor-native-preflight.json)、[上传前拒绝原件](test-results-final-v1-cli-preupload-rejection.json)、[1501前置终态](testing-final-v1-binary-maintenance-terminal.md)。

[启动快照](test-start-final-v1-cli-supervisor.json)、[准确原件](test-evidence-final-v1-cli-supervisor-start.json.gz)。额外[启动守卫](../tests/final-v1-cli-supervisor-launch.py)和[只读观察器](../tests/final-v1-cli-supervisor-observe.py)不替换11项冻结测量输入；观察器对写入中的报告只做最多1秒只读稳定重读，绝不启动/重启测量。
