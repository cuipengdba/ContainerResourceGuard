# 安装、升级与回退

CRG 是放进既有业务容器的静态二进制，不需要安装 Operator、不修改 Kubernetes 控制平面。首次持久接入仍要发布原 supervisor 的可选子进程管理逻辑，并在计划内重启时加载。

## 安装包

从本仓库 Releases 下载匹配架构的 `containerresourceguard-VERSION-linux-amd64.tar.gz` 或 arm64 包，同时下载 `SHA256SUMS`。

```bash
sha256sum -c SHA256SUMS --ignore-missing
tar -xzf containerresourceguard-VERSION-linux-amd64.tar.gz
./crg version
```

发布包包含程序、示例配置、可选启动脚本、文档和许可证，不包含设备标定文件、服务器地址或凭据。arm64 若只经过交叉编译，测试报告会明确说明。

## 放入每个容器

可以在现有可选工具目录挂载下部署，或在构建业务镜像时复制静态文件。不要把运行中容器里一次手工复制当作重建后仍然存在的部署。

典型目录：

```text
/opt/crg/crg                    程序，可只读
/opt/crg/optional-agent.sh      可选辅助管理脚本，可只读
/etc/crg/config.json           每个容器独立，例如 {"percent":20}
/etc/crg/io-profile.json       当前节点/目标设备标定文件，可只读
/tmp/containerresourceguard/   当前容器自己的可写状态目录
```

节点工具分发目录必须在该工作负载可能调度到的节点存在，或者将程序放进镜像。IO profile 必须对应当前节点的设备身份；不能把其他服务器的 profile 原样当作本机能力。

先显式标定，再分发 profile。每个容器先执行 `crg doctor --percent 20`，检查容量来源和限制预览，再通过现有 supervisor 的可选分支启用。详见 [集成说明](integration.md)。

RC2 可执行 `crg preflight --config /etc/crg/config.json --format human` 查看打开权限和换算；不写资源限额，不能代替启用后的真实回读。发布包还包含 supervisor 补丁生成工具，生成时不修改原文件。

## 权限

默认不自动 remount、升权、授予 capabilities 或挂载全宿主 cgroup。部署维护者负责提供自身目标组可写的视图；只读/无权限时程序报告降级，业务继续运行。

对于已有可写特权环境，可以不增加权限直接使用，但仍应执行真实写入与回读验证。不能把 `test -w` 当作内核一定接受写入的证明。

## 升级

保持配置、profile 和状态目录。先停止辅助重试循环及 Agent；以同目录临时文件加原子替换发布新二进制，然后仅重新启动辅助进程。不要在仍执行的脚本上做非原子原地覆盖。

RC1 到 RC2 必须先停止全部旧 Agent；不同 state_dir 的混合版本并行运行不受 RC2 完整单实例保护。保留原状态目录可继续使用版本 1 日志及原值；损坏/缺少关键字段的日志拒绝写入。

若新版本不支持已有日志格式，应该拒绝新增写入，不能删除日志强行继续。当前日志版本为 1。

## 回退

只停 Agent 不会撤销限额。需要解除本程序管理时，先停止它，再用匹配版本 `crg restore`，确认逐项恢复结果。保留外部已改写的值，不盲目写 max。之后可换回旧二进制或停用可选入口。

RC2 优先使用 `crg disable --config FILE` 协调停止写入和恢复，确认成功后再停辅助循环；停用标记须保留到完成回退，详见 [本地运维](operations.md)。RC1 不识别新停用标记，回退旧程序前必须关闭其自动启动入口，不能依赖标记阻止旧版重新施加限额。

资源限额测试、业务性能验收、备份恢复验证完成前，不应把候选版本直接视为生产验收通过。
