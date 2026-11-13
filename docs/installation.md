# 安装、升级与回退

HISDBS30纳秒兼容v2独立补测已完成36/36项、三次不同ID受控启动60.51 / 62.66 / 65.85秒，原300秒业务、45秒缓存及原探针/删除门槛保持；日志追加、逻辑备份、独立恢复和八项原值恢复通过，namespace/三组父叶及106个登记实例独立确认消失。[完整终态与准确原件](test-results-bandwidth-calendar-v2-terminal.json)已归档。与原1129的DBS20/HISDBS20/DBS30三个完成组相结合，[四种组合均有各自完整36项通过](testing-bandwidth-current-combinations.md)，跨独立任务共144项完整组检查；原1129的128通过/1失败/15未执行及1170的9通过/27未执行保持，不把原矩阵改判通过。preview.5程序/八项附件不变；完整600秒/物理备份同步、正式迁移与长期稳定门槛继续。 [逐容器preview.4到preview.5操作说明](upgrade-preview4-preview5.zh.md)列出摘要、保留状态、静默安装和检查步骤；正式已发布包全流程迁移仍待单独验收。

以下保留原时点记录。

截至节点2026-11-13 16:26:50 UTC，已发布[工程预览preview.5](releases/v1.0.0-preview.5.md)，八项公开附件已逐字节校验。新默认值真机原矩阵已经结束：DBS20/HISDBS20/DBS30各36项通过；HISDBS30记录20通过、1失败、15项未执行，共129项记录/128通过/1失败、11次启动。失败是冻结脚本要求跨午夜后旧日期日志继续增长，与每日轮转规则冲突；实际新日期日志已有轮转及新Agent启动。保留原失败，另行修正脚本独立补测，不把原144项改成通过。四namespace、11组父叶及369登记实例独立确认消失。[原矩阵终态及精确原件](testing-bandwidth-percent-terminal.md)已归档。旧preview.4七天任务也已在约30小时的第六轮standby启动失败退出，未达到七天；[独立终态](testing-memory-high-seven-day-terminal.md)保留51个初始登记实例清理及第六轮cleanup未接受的区别。稳定1.0、原52项及其它完整业务/升级/长期门槛继续。

以下保留按原时点记录的历史进展。

截至节点2026-11-13 15:41:11 UTC的已完成组快照，已发布工程预览[preview.5](releases/v1.0.0-preview.5.md)，两架构包及[八项公开附件下载](test-results-preview5-publication.json)逐字节核对通过。CPU/内存/IO独立百分比各默认20，memory.high、IO百分比仅读写BPS且IOPS手动可选/外部原值保留。新程序在原DBS/HISDBS路径下，默认20%两组各36项、合计[72项完整组通过](testing-bandwidth-default20-two-role.md)，六次不同ID启动均在原300秒内，189登记实例与两namespace/六组父叶独立清理。该快照四组144项矩阵处于DBS30、HIS30未执行，后续继续；工程CI为准确ced4617的52项实际cgroup/180项分区/原生ARM64。稳定1.0及其它原门槛继续，历史记录不改。

以下历史记录按原时点保留。

preview.3到preview.4的已发布包内程序迁移实测与受控操作见[专用升级步骤](upgrade-preview3-preview4.zh.md)及[26项终态](testing-public-preview-memory-high-maintenance.md)。下述开发记录保留原时点；不把过期快照自动回退与显式反向安装混用。

已发布[memory.high版preview.4](releases/v1.0.0-preview.4.md)，[八项公开下载校验](test-results-preview4-publication.json)。每容器分别更新，保留原配置/profile/state_dir/journal，核对旧硬限额恢复；源码构建使用发布标签。完整业务和长期门槛继续。

2026-11-12即时交付：[v1.0.0-preview.3](releases/v1.0.0-preview.3.md)，[八项公开下载校验](test-results-preview3-publication.json)。沿用受测程序并更新文档，稳定1.0及原验收条件继续；下方历史记录保留原时点。

当前即时交付：[v1.0.0-preview.2](releases/v1.0.0-preview.2.md)，与preview.1同一受测程序；[实际发布/下载核对](test-results-preview2-publication.json)。本版仅刷新文档和证据，稳定1.0尚未发布。

CRG 是放进既有业务容器的静态二进制，不需要安装 Operator、不修改 Kubernetes 控制平面。首次持久接入仍要发布原 supervisor 的可选子进程管理逻辑，并在计划内重启时加载。

本页描述组合开发候选的维护流程，尚未发布；当前RC2没有后续开发工具/来源证明能力。功能和验收范围以所用标签及对应证据为准，不把开发CI当成正式发布。

## 安装包

从本仓库 Releases 下载匹配架构的 `containerresourceguard-VERSION-linux-amd64.tar.gz` 或 arm64 包，同时下载校验和、BUILD/SBOM和可获得的证明。校验和与包同目录下载只解决传输一致性，预期摘要和源码SHA须来自可信发布渠道；后续有证明的版本应先限定来源身份验证，再解包/执行。

```bash
sha256sum -c SHA256SUMS --ignore-missing
# 有证明的正式发布：用实际版本完整源码SHA与 refs/tags/VERSION，
# 限定仓库、ci.yml和托管runner；开发分支证明不能替代正式tag。
gh attestation verify containerresourceguard-VERSION-linux-amd64.tar.gz \
  --repo cuipengdba/ContainerResourceGuard \
  --signer-workflow cuipengdba/ContainerResourceGuard/.github/workflows/ci.yml \
  --source-digest EXPECTED_FULL_SOURCE_SHA --source-ref refs/tags/VERSION \
  --deny-self-hosted-runners
# 此脚本来自已信任的源码/工具目录，不从未知包中先解出再信任它。
python3 scripts/verify-release.py containerresourceguard-VERSION-linux-amd64.tar.gz \
  --sha256 TRUSTED_PACKAGE_SHA256 --source-revision EXPECTED_FULL_SOURCE_SHA --arch amd64
# 上述验证通过后，在新建的私有目录解包：
tar -xzf containerresourceguard-VERSION-linux-amd64.tar.gz
./crg version
```

发布包包含程序、示例配置、可选启动脚本、文档和许可证，不包含设备标定文件、服务器地址或凭据。arm64 若只经过交叉编译，测试报告会明确说明。

来源/离线bundle及可信根准备见[可信发布说明](release-provenance.md)。验证失败不继续安装；RC2缺少新证明时明确显示该能力缺失，不能伪造新版本证明套用旧包。

包内 BUILD.json 保存二进制 SHA256、程序源码修订 source_revision 与打包文档修订 package_revision；`crg build-info` 对应程序源码修订。测试结果归档的文档提交可能晚于程序构建，所以两个修订可以不同。SHA256SUMS 对应整个发布压缩包。构建/测试命令需在完整源码仓库执行。

## 放入每个容器

可以在现有可选工具目录挂载下部署，或在构建业务镜像时复制静态文件。不要把运行中容器里一次手工复制当作重建后仍然存在的部署。

典型目录：

```text
/opt/crg/crg                    程序，可只读
/opt/crg/optional-agent.sh      可选辅助管理脚本，可只读
/etc/crg/config.json           每个容器独立，例如{}或三个独立百分比
/etc/crg/io-profile.json       默认自动生成/复用的设备基准，首次需可写
/tmp/containerresourceguard/   当前容器自己的可写状态目录
/var/log/crg/                  当前容器自己的每日日志，持久挂载可跨Pod保留
```

节点工具分发目录必须在该工作负载可能调度到的节点存在，或者将程序放进镜像。IO profile 必须对应当前节点的设备身份；不能把其他服务器的 profile 原样当作本机能力。

默认不需要先手工标定或分发profile；提供容器独立、可写持久的默认profile位置，首次由辅助Agent自动标定，之后复用，见[自动流程](automatic-io-calibration.md)。每个容器先执行 `crg doctor --config /etc/crg/config.json`，检查容量来源和限制预览，再通过现有 supervisor 的可选分支启用。详见 [集成说明](integration.md)。

RC2 可执行 `crg preflight --config /etc/crg/config.json --format human` 查看打开权限和换算；不写资源限额，不能代替启用后的真实回读。发布包还包含 supervisor 补丁生成工具，生成时不修改原文件。

组合候选增加[显式接入工具](supervisor-install.md)：已有程序/helper/config先按可信摘要部署，supervisor-plan仅核对预览；supervisor-install明确备份再原子替换已验证模板，下一次计划重启生效。工具不替用户创建全节点必需挂载，不在文件/权限缺失时阻断原业务启动。29项实际接入/持久卸载证据归档在安装开发分支，厂商业务在线升级另行验证。

## 权限

默认不自动 remount、升权、授予 capabilities 或挂载全宿主 cgroup。部署维护者负责提供自身目标组可写的视图；只读/无权限时程序报告降级，业务继续运行。

对于已有可写特权环境，可以不增加权限直接使用，但仍应执行真实写入与回读验证。不能把 `test -w` 当作内核一定接受写入的证明。

## 升级

保持配置、profile 和状态目录。先停止辅助重试循环及 Agent；以同目录临时文件加原子替换发布新二进制，然后仅重新启动辅助进程。不要在仍执行的脚本上做非原子原地覆盖。

支持新维护协议的版本可使用[升级维护命令](install-upgrade.md)：用已信任候选quiesce当前写入者，upgrade-check/state-backup核对原值及读取兼容，再以显式新旧摘要binary-install；检查后enable，仅恢复原helper，不重启业务。自动工具不识别旧程序build-info中的锁/日志协议时拒绝；RC1/RC2等缺必要协议信息版本按完整停止全部旧Agent/辅助循环、保留状态与私有备份的人工发布步骤处理，不能假定“新程序有锁”即可安全混跑。

RC1 到 RC2 必须先停止全部旧 Agent；不同 state_dir 的混合版本并行运行不受 RC2 完整单实例保护。保留原状态目录可继续使用版本 1 日志及原值；损坏/缺少关键字段的日志拒绝写入。

若新版本不支持已有日志格式，应该拒绝新增写入，不能删除日志强行继续。当前日志版本为 1。

RC3 开发分支为 IO 日志增加设备身份，且可记录 pids.max/cpu.weight；旧 RC2 不认识新字段/控制项。降级前必须用新版本完成 disable/restore，确认恢复成功并关闭辅助循环；旧程序拒绝新日志时不能删除日志强行绕过。旧格式日志仍可由新版本读取。

## 回退

只停 Agent 不会撤销限额。需要解除本程序管理时，先停止它，再用匹配版本 `crg restore`，确认逐项恢复结果。保留外部已改写的值，不盲目写 max。之后可换回旧二进制或停用可选入口。

RC2 优先使用 `crg disable --config FILE` 协调停止写入和恢复，确认成功后再停辅助循环；停用标记须保留到完成回退，详见 [本地运维](operations.md)。RC1 不识别新停用标记，回退旧程序前必须关闭其自动启动入口，不能依赖标记阻止旧版重新施加限额。

资源限额测试、业务性能验收、备份恢复验证完成前，不应把候选版本直接视为生产验收通过。

永久卸载先disable并确认真实原值/剩余条目，再撤除持久supervisor入口。组合工具supervisor-uninstall只逐字节恢复已备份脚本，不删状态/程序/配置，不停止业务；quiesce保留限额，因此不能替代disable作为卸载前提。只在运行时临时层撤除不能保证新Pod继续停用。
