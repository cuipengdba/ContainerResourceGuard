# 可选内存 / IO 工具实测（开发版）

日期：2026-11-10。源码 `36551fb283dd8d9809dd7e842ede3c15b9c461c1`，`v0.4.0-dev`，amd64 SHA256 `6049b0ac24d197ff3d5c4ca1cc29f7b6dab51bd62ceccfef1343c11f9c395b22`。包含 v0.3 开发功能，不表示 v0.3/v0.4 已发布。

Linux 5.14 / cgroup v2 / amd64 / 单 XFS-LVM 设备，独立 namespace 的占位业务命令。没有在该夹具内运行厂商 API 或原缓存程序。Linux Go 1.22.5 的 race/vet、16 个建模强杀检查点和 12 个辅助进程故障场景通过；guard 覆盖率 65.8%。[该源码 CI](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42681895886) 通过。

## 16 项实机检查通过

| 检查 | 结果 |
|---|---|
| memory.high 与零 Swap | 256MiB 和 0 写入/回读 |
| 默认 IO 权重 | default 200 写入/回读 |
| IO 默认权重重载 | default 300 生效 |
| 有界内存夹具 | 200MiB 分配成功，运行时硬保护 1GiB |
| 危险 high 下调 | 目标 128MiB 时保持 256MiB，报告 skipped |
| 用量下降后重试 | 释放夹具内存后 128MiB 生效 |
| 外部 high 改值 | 保留外部 160MiB，报告 conflict |
| 外部 IO 默认改值 | 保留 default 400，报告 conflict |
| disable | Swap 恢复真实原值，外部 high 保留，未伪报全部恢复 |
| 重复标定 | v2 profile 含三轮样本 |
| profile 诊断 | 身份解析成功，四维离散程度可见 |
| 临时文件 | 标定临时文件全部清理 |
| 重复身份合并 | 未显式 replace 时拒绝 |
| 合并预览 | 不写入，输入摘要不变 |
| 显式输出 | 只在指定输出时创建合并文件 |
| 业务存活 | 控制与冲突测试后占位 PID 1 存活 |

## 保留的失败与边界

第一次检查在尝试设置每设备 IO 权重时得到 `EOPNOTSUPP (95)`，随后完成测试 namespace/数据清理。该设备/内核后端不支持此操作；没有启用宿主控制器或切换调度器。默认权重回读成功不证明 IO 调度份额有效。修正夹具识别这个能力边界后，使用**同一二进制**重跑上述 16 项；每设备覆盖保留仅有单元证据，不能标为本机已通过。

节点没有实际 Swap 工作负载。测试仅在无换出页的独立夹具叶组，把初始 swap.max 预置为 max，再验证程序写 0 和恢复 max；没有开启宿主 Swap、没有改父组，不能声称实际换入换出已验证。

三轮 1 秒阶段样本中，读 BPS/读 IOPS/写 IOPS 离散程度分别约 48.86% / 41.10% / 25.37%，质量诊断按设计给出警告。这个 profile 仅用于工具验证，未用于业务限额，不把它认定为高质量性能基准。

两次 namespace 和临时数据均已清理；私有原值、原报告和源码留存。去标识机器结果见 [JSON](test-results-memory-io-linux-amd64.json)。真实多设备、竞争权重效果、实际 Swap、跨周期稳定窗口和原缓存回收高峰仍待验收。
