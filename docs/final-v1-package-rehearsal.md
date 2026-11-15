# 最终候选打包与来源核对

本项是 P09.1/P09.2 的开发任务，不等于稳定版发布。长期试验仍沿用[既定协议](testing-final-v1-long-node-admission.md)，没有重启、改配额或替换程序。当前18/52项完成；发布必须另外满足原有业务和长期门槛。

## 固定程序，更新文档

程序源码固定为 `ced461705ebc27315a59aefe463f9b4af47130a3`，内嵌版本 `v1.0.0`，Go 1.27.3。amd64 ELF SHA256 为 `9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8`，arm64 为 `ff1a2c1c599eb38fde6857c2eede70a1deabf0c2c89977ab92e71ec52ec3982b`。[候选身份](final-v1-candidate-identity.json)登记50份运行时源码；后续文档更新不应改变这两份已受测程序。

新增[手动打包工作流](../.github/workflows/final-package.yml)：当前提交提供文档和打包工具，单独检出上述源码构建；比较全部50份运行时源码和两架构精确 ELF 摘要后，才允许打包。`BUILD.json` 中 `source_revision` 表示程序来源，`package_revision` 表示文档/打包来源，两者允许不同。常规分支 CI 仍测试各分支提交，不能将其产物冒充此固定候选。

工作流不创建标签、不合并 PR、不上传 Release。成功后仅提供候选 Actions 附件和对应 GitHub attestations。它验证两架构完整包、离线拒绝检查及另一绝对目录中的重新构建和重新打包；同一次演练必须有相同环境下的逐字节相等，跨 Python/zlib 平台的压缩包摘要不要求相同。ELF 两个固定摘要始终必须相同。

## 可执行核对

在含固定源码对象的完整仓库中，将准确的两份 ELF、两份 SBOM 和 `build-manifest.json` 放入 `dist/`，执行：

```sh
python3 scripts/package.py v1.0.0 --source-revision ced461705ebc27315a59aefe463f9b4af47130a3
python3 scripts/check-package.py v1.0.0
python3 tests/release-integrity.py v1.0.0 --source-revision ced461705ebc27315a59aefe463f9b4af47130a3
python3 scripts/check-reproducible.py v1.0.0 --source-revision ced461705ebc27315a59aefe463f9b4af47130a3
```

离线检查覆盖两份正常包及错误外部摘要、架构、源码、截断、路径穿越、绝对路径、Windows 盘符、反斜杠、符号链接、重复条目、包内程序被篡改及篡改包复用旧摘要。验证器不解压或执行程序。它只证明与调用者提供的可信摘要一致；同目录下载的 `SHA256SUMS` 本身不建立发布者信任。

来源验证使用已修复的 GitHub CLI（本地工具为2.103.3；至少2.102.0），在独立取得预期打包提交后执行：

```sh
gh attestation verify dist/containerresourceguard-v1.0.0-linux-amd64.tar.gz \
  --repo cuipengdba/ContainerResourceGuard \
  --signer-workflow cuipengdba/ContainerResourceGuard/.github/workflows/final-package.yml \
  --source-digest "$CRG_PACKAGE_COMMIT" --signer-digest "$CRG_PACKAGE_COMMIT" \
  --deny-self-hosted-runners --format json
```

这里的证书源码/工作流提交是**打包提交**，不是 ELF 内嵌的旧程序源码；签名验证通过后还须核对包内 `BUILD.json`、SBOM 和固定程序摘要。离线来源验证需预先通过可信渠道取得 attestation bundle、信任根和预期仓库/工作流/提交；参见[官方离线说明](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/verify-attestations-offline)。不能用自签 JSON 或 SHA256 冒充 GitHub 签名通过。CLI 参数及信任边界见[官方验证说明](https://cli.github.com/manual/gh_attestation_verify)；最低版本依据[完整工作流身份修复公告](https://github.com/cli/cli/security/advisories/GHSA-wjmr-j3rp-mh2g)。

## 验收记录要求

归档实际打包提交、源码提交、工具版本、每个产物摘要/大小、离线正常和拒绝结果、SBOM schema 核对、重复构建结果，以及实际 Actions run 与签名核对。失败必须保留原结果后修订，不替换正在长期测试的 ELF。没有取得的来源证明或最终安装验证保持待完成；候选包即使文件名含 v1.0.0，也不表示稳定版已发布。

## 本次实际结果

[Actions 43729111057](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/43729111057)在打包提交 `576e6070b09804017ececf3f82fb2f6517c18316` 成功：50份运行时源码及两份 ELF 固定摘要匹配，两架构包检查、14项离线检查和另一绝对目录重复构建/打包通过。实际下载 ZIP 与 API 公布摘要一致；两份包内 BUILD/SBOM/ELF 绑定另行核对。文件详情见[CI原件与独立复核](test-results-final-v1-package-CI.json)。临时 Actions 附件30天过期，不是稳定 Release。

[Windows 本地演练](test-results-final-v1-package-local.json)另有14项及两份官方 schema 核对和完整重复构建通过；本地演练提交未公开，不能冒充上述公开打包提交。两平台压缩包摘要各自记录，不要求跨平台 gzip 字节相同；两架构 ELF 始终分别等于固定候选摘要。

[独立签名复核](test-results-final-v1-package-signatures.json)共10项通过：两架构归档来源和两份 ELF/SBOM 在线验证；两架构离线正常验证；错误源码、错误工作流、篡改包三个有效策略拒绝；末尾正常对照。每项证书精确核对仓库、工作流、分支、打包提交、GitHub托管环境及准确 run/attempt，并绑定实际文件摘要；没有把网络/CLI用法失败计作拒绝。离线环境为关闭代理端口与空NO_PROXY，不宣称OS防火墙隔离。公开[签名原件](test-evidence-final-v1-package-signatures.json.gz)及[本次执行源码](../tests/final-v1-package-attestation-rehearsal.py)；执行源码需按冻结布局准备工具和附件，通用操作以上述CLI步骤为准。

当前从 `release/integration-v1` 的已核对提交手动运行该流程；main 尚未合入产品实现，在旧运行时源码上运行会被50份源码检查拒绝。本次没有新标签、Release附件替换、生产安装或长期试验变更；P09.1/P09.2的最终稳定发布/安装门槛仍开放。
