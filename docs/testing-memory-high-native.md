# memory.high 发布程序的原生复验

[冻结计划](test-plan-memory-high-native.json)锁定 preview.4 的程序源码 180c86a、发布包修订 7a20c3b 和两份已发布 ELF。运行前核对 50 个生产文件与三个测试输入；四格分别要求实际 Linux 6.x/7.x 和原生 AMD64/ARM64。先在 Linux 重建，再要求两 ELF、两包、两 SBOM、清单和 SHA256SUMS 与 Windows 发布构建逐字节一致，随后执行每格 22 项自身 cgroup 测试及清理。

内存断言按用户要求改为 memory.high 回收和节流目标，容器运行时设置的 memory.max 保持。CPU、IO、唯一 Agent、恢复、只读降级、日志及清理标准保持。旧硬上限策略的原生结果和冻结计划保留；本次不借用其时长、通过项或业务结论。

当前已冻结，尚无本次四格终态。该验证不代表 DBS/HISDBS 业务、物理多盘、长期验收或稳定版接受，也不生成来源签名证明。
