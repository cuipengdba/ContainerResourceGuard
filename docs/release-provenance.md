# 可信构建与离线校验开发

2026-11-10，next/release-provenance 开发分支，尚未发布 v0.8/1.0。承接 P09.1/P09.2；实现与实测结果分别归档，不能把编写 workflow 等同生成了可验证证明。

发布构建固定 Go1.27.3，并禁用自动切换/下载工具链、外部模块代理和本地 Go 环境文件。`go.mod` 的最低源兼容版本不因此改变。官方归档摘要见 [工具链记录](../scripts/toolchain.json)，来自 [Go 官方下载清单](https://go.dev/dl/?mode=json)；版本/摘要应按维护更新流程一起更改。构建要求 checkout 精确且已提交的源码修订，版本号严格限定；不允许把当前代码随意标成别的修订。build-info 增补 go_version，既有字段保持。

构建清单记录两架构实际二进制摘要、Go 内嵌模块/构建信息和源码时间。CycloneDX 1.6 SBOM 逐架构从相同工具链与目标的 `go list -deps` 生成标准库包清单，绑定实际二进制 SHA256。该清单是包级构建依赖，不声称所有源函数都进入最终二进制。编译器列为构建工具，不作为分发载荷；厂商数据库、libpq 与独立缓存程序不随本产品分发，不属于本包 SBOM。新外部 Go 依赖须补许可证和清单支持，不能自动漏记。

打包只从已提交的 Git blob 中选择公开文档/脚本/示例；未跟踪文件、工作区临时文件和私有配置不进入包。gzip 时间置零、成员顺序/属主/模式/时间固定，包中包含 BUILD.json 与 SBOM.cdx.json。包修订与二进制源码修订分别记录；固定二进制、两项修订及工具链才具有可重复性意义。源码时间不是实际构建时刻，真实构建来源由 CI 证明补充。

```sh
bash scripts/build.sh v0.8.0-dev
python3 scripts/package.py v0.8.0-dev
python3 scripts/check-package.py v0.8.0-dev
python3 tests/release-integrity.py v0.8.0-dev
python3 scripts/check-reproducible.py v0.8.0-dev

# 此摘要必须来自独立可信渠道或已验证证明，不能只信同目录下载的 SHA256SUMS。
python3 scripts/verify-release.py containerresourceguard-VERSION-linux-amd64.tar.gz \
  --sha256 TRUSTED_PACKAGE_SHA256 --source-revision EXPECTED_FULL_SOURCE_SHA --arch amd64
```

离线校验先对有大小上限的压缩包建立私有临时快照并匹配外部可信摘要，再检查包结构、目标 ELF、源码修订和内部二进制/SBOM 摘要。拒绝链接、特殊文件、重复项、越界路径、过多成员和过大展开体积，不解包或执行载荷。摘要只解决内容完整性，摘要来源的可信度需要用户的发布渠道或签名身份策略。安装前应分别验证包来源及解包后的候选摘要，再使用显式维护命令；不把安装维护接入数据库启动前置条件。

可选 schema 核对入口为 `python3 scripts/validate-sbom.py dist/sbom-linux-amd64.cdx.json --schema-directory LOCAL_SCHEMA_DIRECTORY`。在独立开发工具环境安装 jsonschema==4.26.0，预先从 [CycloneDX 官方 1.6 schema 目录](https://github.com/CycloneDX/specification/tree/1.6/schema) 获取 BOM/SPDX/JSF 三个文件；本脚本先按 [锁定摘要](../scripts/sbom-schema-lock.json) 校验，再本地验证，不自动下载或解析远程引用。该依赖不进入 CRG 二进制或业务镜像。

CI 固定 Actions 的完整提交摘要；非 PR 构建拟生成包的 provenance、两种二进制各自 SBOM attestation。公开仓库使用 GitHub OIDC，不把长期签名私钥写入仓库。来源验证使用 [GitHub 的证明说明](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations) 与 [gh attestation verify](https://cli.github.com/manual/gh_attestation_verify)，约束仓库、工作流、预期源码修订及托管 runner；仅“签名有效”不足以证明是预期版本。离线验证另需预先从可信渠道保存 bundle 与信任根，不能用未知包自带的根建立信任。

```sh
gh attestation verify PACKAGE_FILE --repo cuipengdba/ContainerResourceGuard \
  --signer-workflow cuipengdba/ContainerResourceGuard/.github/workflows/ci.yml \
  --source-digest EXPECTED_FULL_SOURCE_SHA --source-ref EXPECTED_REF \
  --deny-self-hosted-runners
# EXPECTED_REF 对开发证明使用完整 refs/heads/next/release-provenance；
# 正式版需对应预期 refs/tags/VERSION，并核对完整源码 SHA。
# SBOM 证明针对二进制，另加 --predicate-type https://cyclonedx.org/bom。

# 在已建立信任的联网工具机预取，保存在新建的私有工作目录。
gh attestation download PACKAGE_FILE --repo cuipengdba/ContainerResourceGuard
gh attestation trusted-root > trusted_root.jsonl
# 离线使用同样身份/源码策略，加 --bundle BUNDLE_FILE
# 和 --custom-trusted-root trusted_root.jsonl；实际文件名以 download 输出为准。
```

重复构建检查在另一个绝对路径的新克隆中执行同一提交和固定配方，比较两种二进制、两种压缩包、两份 SBOM、清单与校验和的字节摘要；它证明本机同工具链的路径独立性，不替代另一平台或独立第三方复现。跨平台结果、完整 SBOM schema 核对、实际证明生成/验证、安装前演练与长期回归继续分别验收。


## 实测结果

[逐项证据](test-results-release-provenance.json) 分别标明源码/构建版本，不能将不同修订、版本字符串或编译器的二进制摘要混用。cce9018 在 Windows Go1.27.3 下完成两个目标 ELF/包校验、14 项正反完整性检查、另一绝对路径克隆重建；两二进制、两压缩包、两 SBOM、构建清单与 SHA256SUMS 的字节均相等。另用 jsonschema4.26.0 / Draft7Validator 与 CycloneDX 官方 1.6 标签的 BOM/SPDX/JSF schema 验证两份 SBOM，均无错误，schema 摘要已归档。没有把这一结果称为漏洞扫描或标准认证。

首轮 [CI42720487857](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42720487857) 的构建/包/完整性/复现和 provenance 已通过，但 SBOM action 要求 serialNumber，缺该字段导致失败；后续绑定二进制摘要生成确定性 UUID，重复构建使用同一逻辑 BOM 身份，保留可复现性。修复后的 [CI42721505581](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42721505581) 与 [CI42721825291](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42721825291) 全部通过，两个架构分别生成 SBOM 证明。

对 7844ba5 的真实 CI 产物执行 gh attestation verify：限定本仓库、ci.yml、完整源码 SHA、开发分支 ref，拒绝 self-hosted runner。两种包的 provenance 与两种二进制的 CycloneDX 证明四项通过；错误源码、错误工作流和篡改包三个反例拒绝。先从既有可信 GitHub CLI/TUF 引导获取 root 与 bundle，再把 HTTP/HTTPS/ALL 代理设成不可达本地地址，正确 root/bundle/身份的本地验证通过，错误源码、篡改产物与空信任根拒绝。没有执行操作系统防火墙隔离，不把代理条件夸成物理断网。

这些是开发分支的发布工具证据，仍未发布 v0.8/1.0。验证构建证明只证明来源/内容绑定，仍须核对该版本的功能验收、已知问题与正式发布状态。跨宿主重建、实际安装前验证联动和更长故障回归继续单独归档。
