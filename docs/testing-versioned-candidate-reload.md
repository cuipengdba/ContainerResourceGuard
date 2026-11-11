# 精确发布候选的15项热重载补测

2026-11-11，在隔离Linux AMD64/5.14节点运行。程序为已发布preview.1/preview.2内同一`v1.0.0` ELF，SHA256 `dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8`，源码`d3706f3ea7ad279fea818e5ad1aa62ac5d3f8710`。[实际15项终态与门禁](test-results-versioned-candidate-reload.json)、[冻结计划](test-plan-versioned-candidate-reload.json)。旧d6程序的[原15项结果](testing-three-percent-reload.md)保持原来源。

本轮补齐新程序自身的工程重载证据。测试使用原DBS镜像的占位PID1，没有启动原厂商业务；不是DBS/HISDBS原启动、原生SQL/API、备份负载下的热重载验收。

## 冻结条件和实际执行

[执行器](https://github.com/cuipengdba/ContainerResourceGuard/blob/7787ffb0abacf2616fb46905457b260da5282ab3/tests/vendor-versioned-reload.py)与[旧检查模板](fixtures/reload-three-percent-reference.py.txt)的15个`record`调用逐个AST相等；没有为了新程序通过而改旧判定。程序、profile、模板和计划均先固定SHA256。默认调用只做只读门禁，实际exit0/ready且未创建目录或namespace；`--execute`缺少隔离节点标记时exit1/EXPLICIT_LAB_MARKER，目标仍未创建，随后才明确启动唯一实测实例。

CPU外部8核、内存20GiB；重载等待60秒、Agent周期1秒，宿主可用内存至少8GiB、磁盘至少20GiB。测试自建的Pod使用私有PID/网络/挂载命名空间，启动Agent前已隔离网络。产品仍是一容器一Agent；Kubernetes命令只属于节点隔离测试工具，不是产品权限或部署前提。

15项全部通过：独立比例与CLI CPU25优先、两维变更、IO101坏配置保留整份旧策略和代次、修复/省略项默认20、空资源配置、同一Agent/PID1、CLI日志目录优先、profile内容和mtime复用、disable恢复、manual显式两资源、manual转三比例、删除manual内存/IO后恢复、外部CPU冲突保留、disable返回冲突，以及PID1不变/无OOM。具体名称逐项保留在JSON中。

正向重载的部分旧判定检查的是已接受计划、状态和代次，未对每一步三个资源的数值全部独立读取内核核对；不能扩大为“所有动态写入逐值已验收”。恢复、坏配置保持、外部CPU冲突及五个额外控制项则包含实际cgroup读取。进一步的厂商业务负载、逐值回读、危险内存延后、文件替换和并发分支仍按原P03任务核对。

同一运行器/worker均退出，exit0；namespace、自有主cgroup及Pod内所有容器scope均独立确认不存在。只读来源程序和profile的前后SHA256一致。最后CPU0.5核是本测试有意模拟的外部改值，Agent按冲突规则保留，随后整个自有Pod已清理；没有将此状态写到其他业务。

## 复核和重跑边界

执行器为本次已冻结的专用计划，包含一次性节点目录；不要对业务环境或完成后的旧目录直接重跑。需要复现时先审查测试源码，在新的隔离节点准备精确程序、同设备profile和独立目录，重新冻结路径/执行器/计划摘要。默认只读入口：

```bash
python3 vendor-versioned-reload.py --plan reload-plan.json --plan-sha256 PLAN_SHA256
```

只有同时指定`--execute`和`CRG_VERSIONED_RELOAD=authorized-disposable-test-node-only`才允许进入测试。缺少profile的manual转百分比自动标定不是本轮覆盖项；既有[重载契约](https://github.com/cuipengdba/ContainerResourceGuard/blob/7787ffb0abacf2616fb46905457b260da5282ab3/docs/compatibility-contract.md)保持。实际七天、默认20%性能及稳定1.0仍未接受。本轮证据归档发生在preview.2发布后，没有覆盖其既有安装包或附件。
