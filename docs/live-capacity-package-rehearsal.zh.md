# 源37新候选的打包、SBOM与来源演练

## 本轮实际结果

2026-11-16，[唯一GitHub运行](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/43797520716)已成功；程序源码为`37ca44e0e24a0eaa14e52b5c8bbbda54c76364b0`，打包/文档提交为`9deb9426f9f974744beb667d2cf83266cb49c012`，准确workflow为[capacity-fixed-package.yml](../.github/workflows/capacity-fixed-package.yml)。这是新源37的独立候选演练，未发布稳定版、未替换preview.5附件、未进行实际生产安装。

[冻结计划](test-plan-live-capacity-package-v1.json)、[候选身份](live-capacity-candidate-identity.json)、[完整复核](test-results-live-capacity-package-v1.json)和[原字节证据](test-evidence-live-capacity-package-v1.json.gz)一并归档。冻结前说明保留在[该次提交](https://github.com/cuipengdba/ContainerResourceGuard/blob/9deb9426f9f974744beb667d2cf83266cb49c012/docs/live-capacity-package-rehearsal.zh.md)。旧ced/576流程、身份和结果保持原资格，未移作新源通过。

|实际检查|结论与范围|
|---|---|
|两架构实际构建/打包|固定Go1.27.3；AMD64 ee4f0a14…、ARM64 865459b0…与正在长测的候选准确ELF逐字一致；50生产文件、12配方和原metadata摘要绑定通过|
|原包结构/完整性|两个Linux归档静态ELF、内层BUILD/SBOM及文档检查通过，原14个正常/拒绝场景通过；未缩减案例|
|独立路径重复构建|两份ELF、两份归档、两份SBOM、build-manifest与SHA256SUMS共8输出逐字相等；限此次工具链/runner，不冒充跨平台复现|
|完整artifact下载|精确11文件白名单、ZIP长度/CRC及GitHub SHA256独立核对；下载初次串行改分块、分块超时后使用更小块有界重试，不重跑CI、不以断点当通过|
|客户端内容|下载的AMD64/ARM64归档分别由原verify-release独立通过；两个实际SBOM按本地官方三schema锁和jsonschema4.26.0通过，4/4|
|签名|两归档SLSA provenance、两ELF/SBOM共4在线正向；两架构离线正向、末尾正向对照、错误源码/工作流/篡改包3有效拒绝，共10/10|

签名证书逐项匹配仓库/owner ID、集成ref、准确workflow、**打包提交**、GitHub-hosted、准确run/attempt及文件subject SHA；BUILD/SBOM保留**程序源码**，二者不可混用。离线为HTTP/HTTPS/ALL代理指向关闭loopback端口、清空NO_PROXY，不宣称OS防火墙隔离；网络和CLI用法错误不计有效拒绝。可信根在线取得后用于离线，bundle只从成功在线核验结果提取；信任引导为既有GitHub CLI 2.103.3/TUF。可复核[签名执行源码](../tests/live-capacity-package-v1/verify-attestations.py)及[下载内容核验源码](../tests/live-capacity-package-v1/verify-downloaded-content.py)，需按冻结布局准备工具与附件。

本轮只在GitHub临时runner及本地验包，不改测试节点产品/19长测输入/资源预算/时钟。另一次独立只读快照确认原1880长测仍在baseline，原进程、两角色八控制及实际Agent保持；快照不授予24h/24h/7d资格。原18业务及另4辅助、四组44项对照、同源原生284项各保持独立范围。

## 仍需完成

本次Actions附件30天后过期，既不是稳定Release附件，也不是安装/回退或老化后验收。后续正式包需按最终打包提交/附件身份重新验证来源、SBOM、完整性、实际下载和安装/回退，不能沿用本轮包摘要代替。原长稳、老化后故障/维护/升级、52项逐项剩余要求保持；[当前交付](release-readiness-current.md)、[新长稳](development-new-long1880.zh.md)、[任务审核](current-52-task-audit.md)明确边界。其它分支仍保留各自原产品源，本轮只从集成分支运行，旧源误调度应在50文件绑定处拒绝。
