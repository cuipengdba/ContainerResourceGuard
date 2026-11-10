# 分区实现接入组合候选

组合开发提交d3706f3已接入af1a34d分区实现：11个实现/单元测试文件，全50个生产源码及Go模块文件与已验收分区分支逐文件一致。此前实际分区四格164项的程序仍是468fe73，保留原报告，不能改写成d3706f3的二进制执行记录。接入范围和摘要见[组合线冻结合同](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/docs/test-plan-partition-integration.json)。

本提交自身的[完整构建CI](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42882251278)、[原生ARM64检查](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42882251248)、[原生整盘控制回归](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42882251208)均成功。包含Linux vet/race、辅助故障/启动链检查、包完整性/另路径复现、provenance和两架构SBOM证明生成；原生ARM64各项Go pass事件212，包含新增分区单元测试；原生AMD64/ARM64两组原整盘22项、共44项实际控制和清理通过。[本提交结果和来源](test-results-partition-integration.json)独立归档。

Windows在全新独立checkout、固定Go1.27.3/目标参数构建，两目标程序及完整build-manifest与本提交Linux CI相同。AMD64程序SHA256为3a1ce7dbf5630f8f1c823005ceb4958653c6c235b2ba5026956ca6597f1926f9，ARM64为d26c2336dfa7b98f3d87d0dad8520d6fbb852f40761b70060b455f91f119fc26。本轮已完成[当前提交的4项在线构建/SBOM证明验证、2项离线正常对照及3项离线拒绝反例](testing-partition-build-identity.md)，共9项通过。原生CLI/控制回归使用各自注明的CI版本字段，和此next-compatibility-contract构建分别列明，不混用程序摘要。

新候选另按[开销冻结计划](test-plan-partition-steady-overhead.json)复验：原45秒预热、1800秒实际测量、三独立占位容器、原CPU/RSS/写入/间隔/OOM阈值均不变，增加每次采样的PID1/Agent/cgroup身份和8项实际控制保持检查。首轮因测试包漏带optional-agent.sh而在90秒状态等待截止前失败，未进入采样；[失败记录](test-results-partition-steady-overhead-startup-failure.json)及退出1/夹具清理保留。补齐同源码辅助脚本并增加摘要前置检查后，按[第二次冻结计划](test-plan-partition-steady-overhead-retry.json)重测，现已进入实际采样；[固定启动观察](test-start-partition-steady-overhead-retry.json)每组6个样本仅证明开始，尚非1800秒验收。程序、超时和验收阈值均不变，前一d6程序结果不直接沿用。

此接入只在组合开发线，尚未合入main或发布；既有预览资产不改，97正式基线和正式共享切换的d6候选/工具/预算不改。ARM厂商业务、独立物理设备、24h+24h、至少7天和最近两个正式次版本维护仍不据此关闭，默认20%业务失败保持原结论。
