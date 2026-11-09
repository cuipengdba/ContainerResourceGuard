# 跨周期内存窗口实测

2026-11-10，源码 b0ed1e09be5c518564c79aa7c90e4f4c9afe1a35，二进制 SHA256 a90bd0bf1cb1c3a0d97a7bf3a8de1c68adaa3f80c0b82ff63d318174c53ab2db。[该源码 CI](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42698634875) 通过；测试节点 Go 1.22.5 的 Linux race/vet、16 个建模强杀检查点及两组共 12 类可选进程脚本故障通过，guard 覆盖率 72.1%。

独立命名空间内使用占位 PID 1，每容器外部保护 CPU 1/内存 256MiB。真实 cgroup 共 11 项检查通过，见 [JSON](test-results-memory-window-linux-amd64.json)。

- 初始 6 秒窗口等待时 CPU 0.25 已施加，内存保持外部原值；等待期间 journal 修改时间不变；安全后 128MiB 生效。
- 分配并触碰 70MiB 内存后，下调到 64MiB 被 memory_safety 延后；当次 memory.current 约 78.1MiB，内存硬值保留 128MiB，journal 不反复写。
- 释放分配后先重新进入 memory_window，观察到约 4.21 秒后 64MiB 生效，没有直接跳过窗口。
- observe 下不写入；回到 enforce 重新等待窗口，最终 56MiB 生效。
- disable 恢复 CPU/内存的真实原值，PID 1 存活，未新增 OOM kill；测试命名空间确认消失。

本次恢复是回到较大的原值，没有冒充“真实低原值恢复已测”。低原值恢复、慢持久化期间分配和重启丢弃历史有单元证据；实际 Swap、PSI、高峰负载/原缓存并发及长期延后仍待验收。后续 f7b4a56 的事件实现有独立来源，不把这个二进制结果移用于新代码。
