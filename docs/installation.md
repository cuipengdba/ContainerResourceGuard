# 安装、升级与回退

preview.3到preview.4的已发布包内程序迁移实测与受控操作见[专用升级步骤](upgrade-preview3-preview4.zh.md)及[26项终态](testing-public-preview-memory-high-maintenance.md)。下述开发记录保留原时点；不把过期快照自动回退与显式反向安装混用。

已发布[memory.high版preview.4](releases/v1.0.0-preview.4.md)，[八项公开下载校验](test-results-preview4-publication.json)。每容器分别更新，保留原配置/profile/state_dir/journal，核对旧硬限额恢复；源码构建使用发布标签。完整业务和长期门槛继续。

2026-11-12即时交付：[v1.0.0-preview.3](releases/v1.0.0-preview.3.md)，[八项公开下载校验](test-results-preview3-publication.json)。沿用受测程序并更新文档，稳定1.0及原验收条件继续；下方历史记录保留原时点。

当前即时交付：[v1.0.0-preview.2](releases/v1.0.0-preview.2.md)，与preview.1同一受测程序；[实际发布/下载核对](test-results-preview2-publication.json)。本版仅刷新文档和证据，稳定1.0尚未发布。

CRG 是放进既有业务容器的静态二进制，不需要安装 Operator、不修改 Kubernetes 控制平面。首次持久接入仍要发布原 supervisor 的可选子进程管理逻辑，并在计划内重启时加载。

## 安装包

从本仓库 Releases 下载匹配架构的 `containerresourceguard-VERSION-linux-amd64.tar.gz` 或 arm64 包，同时下载 `SHA256SUMS`。

```bash
sha256sum -c SHA256SUMS --ignore-missing
tar -xzf containerresourceguard-VERSION-linux-amd64.tar.gz
./crg version
```

发布包包含程序、示例配置、可选启动脚本、文档和许可证，不包含设备标定文件、服务器地址或凭据。arm64 若只经过交叉编译，测试报告会明确说明。

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

## 权限

默认不自动 remount、升权、授予 capabilities 或挂载全宿主 cgroup。部署维护者负责提供自身目标组可写的视图；只读/无权限时程序报告降级，业务继续运行。

对于已有可写特权环境，可以不增加权限直接使用，但仍应执行真实写入与回读验证。不能把 `test -w` 当作内核一定接受写入的证明。

## 升级

保持配置、profile 和状态目录。先停止辅助重试循环及 Agent；以同目录临时文件加原子替换发布新二进制，然后仅重新启动辅助进程。不要在仍执行的脚本上做非原子原地覆盖。

RC1 到 RC2 必须先停止全部旧 Agent；不同 state_dir 的混合版本并行运行不受 RC2 完整单实例保护。保留原状态目录可继续使用版本 1 日志及原值；损坏/缺少关键字段的日志拒绝写入。

若新版本不支持已有日志格式，应该拒绝新增写入，不能删除日志强行继续。当前日志版本为 1。

RC3 开发分支为 IO 日志增加设备身份，且可记录 pids.max/cpu.weight；旧 RC2 不认识新字段/控制项。降级前必须用新版本完成 disable/restore，确认恢复成功并关闭辅助循环；旧程序拒绝新日志时不能删除日志强行绕过。旧格式日志仍可由新版本读取。

## 回退

只停 Agent 不会撤销限额。需要解除本程序管理时，先停止它，再用匹配版本 `crg restore`，确认逐项恢复结果。保留外部已改写的值，不盲目写 max。之后可换回旧二进制或停用可选入口。

RC2 优先使用 `crg disable --config FILE` 协调停止写入和恢复，确认成功后再停辅助循环；停用标记须保留到完成回退，详见 [本地运维](operations.md)。RC1 不识别新停用标记，回退旧程序前必须关闭其自动启动入口，不能依赖标记阻止旧版重新施加限额。

资源限额测试、业务性能验收、备份恢复验证完成前，不应把候选版本直接视为生产验收通过。
