# 源37新候选的打包、SBOM与来源演练

## 当前阶段

本轮先冻结[准确计划](test-plan-live-capacity-package-v1.json)、[候选身份](live-capacity-candidate-identity.json)与[单独workflow](../.github/workflows/capacity-fixed-package.yml)，尚未调度，不代表构建或验收通过。产品源37ca44e0/两个准确ELF与当前新长稳一致；此工作仅在GitHub临时runner进行，不连接测试节点、不修改长稳19输入、资源预算、时钟或业务。源37的[正式18项/另4辅助](development-fresh-formal18.zh.md)和[当前长稳](development-new-long1880.zh.md)保持各自资格。

旧ced/576打包演练和原final-package.yml/final-v1-candidate-identity.json逐字保留，不能借用其结果。其它分支保留其产品源，本轮仅从集成分支调度；误从旧产品源分支调度时，50文件/ELF绑定必须拒绝，不以文档相同假装程序相同。新workflow只手动触发，不改变原CI或发布附件。

## 准确源与产物绑定

固定Go1.27.3和原四个构建输入，从source37单独checkout重建Linux AMD64/ARM64静态ELF，分别必须等于ee4f0a14…和865459b0…；完整摘要、长度、两份SBOM及build-manifest原摘要在计划列出。检查当前打包树及独立源码树全部50生产文件、12个打包/校验依赖和准确metadata；任一不符停止，不重建一个较易通过的程序。候选身份本身的摘要在workflow常量绑定，workflow及身份全部字节由CI run head/API绑定。

程序源固定为37ca44e0完整40位SHA；打包/文档源为实际唯一CI run的另一个完整head SHA。SOURCE、BUILD.json、SBOM、PACKAGE-DOCUMENTATION和签名分别核对，不把二者混为一个版本。原脚本从committed Git archive收集公开文档，60MiB/4000成员上限不放宽，不加入工作区文件、私有profile、凭据、数据库数据或测试机回执目录。

## 必须实际执行的检查

1. 两架构实际build/package、包内准确ELF/BUILD/SBOM及文档链接检查，原14个离线完整性正常/拒绝场景均保持；校验不解压或执行任意未受信文件。
2. 在不同绝对路径的独立源码/打包checkout，原两架构ELF、SBOM、manifest、归档和SHA256SUMS重复构建逐字相等；不宣称不同平台/第三方复现。
3. 从准确成功run下载完整artifact ZIP，按GitHub digest和长度复算并核对精确11文件白名单/CRC；客户端独立校验两份下载归档，并用原本地官方三schema锁与jsonschema4.26.0验证两个实际SBOM。
4. 四个在线签名正向：两归档SLSA provenance与两ELF的CycloneDX SBOM，证书必须命中本仓库/owner ID、集成ref、准确workflow、打包commit、GitHub-hosted及准确run/attempt/subject SHA。禁止自托管身份替代。
5. 将成功验证出的bundle与预先获取的可信根留存，用原关闭loopback代理/空NO_PROXY条件做三个离线正向和错误源/错误workflow/篡改归档三个负向，共10个签名场景；网络错误、参数错误不算预期拒绝。此条件不是OS防火墙隔离；信任根引导与CLI版本公开记录。

原脚本及CLI/Schema工具按准确摘要/版本绑定。失败保留原步骤、输入、错误和下载资格，不自动重复dispatch/更改阈值。计划中的数字是待执行条件，只有实际原件/签名校验可授予本次演练通过。

## 完成边界

本次是新候选打包/离线/来源演练，不是稳定v1.0.0附件、生产安装或老化后验收。完整24h基线/同容器24h限制/新七天、原后置故障/恢复/维护/升级、缺失厂商ARM与独立物理多盘范围及最终稳定身份仍按原条件处理。preview.5八资产/正文/tag不改，52原任务定义/18既有完成声明不增加；开发任务和结果按P09.1/P09.2独立归档。
