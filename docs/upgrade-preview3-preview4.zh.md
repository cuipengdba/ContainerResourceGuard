# preview.3 升级到 memory.high 版 preview.4

本页针对已经接入可选helper、遵循相同锁协议和journal v1的两个已发布预发布包。升级逐容器执行，不需要Operator或重装Kubernetes。当前目录以真实路径验收中的`/opt/crg/crg`为例，必须与本容器原有`CRG_BIN`一致；安装/配置/profile/state/log/恢复目录均为该容器专属。尚未完成的业务与稳定条件以[当前验收](current-acceptance.md)为准。

## 核对包与原配置

从[preview.3](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v1.0.0-preview.3)和[preview.4](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v1.0.0-preview.4)获取与架构匹配的包，先按可信发布摘要核对，再解包到全新私有目录。下面只给AMD64受测程序摘要：

| 程序 | 程序SHA256 | 程序版本字符串 |
|---|---|---|
| preview.3 | `dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8` | `v1.0.0` |
| preview.4 | `6088721cd4846f95b3b71c82f9884e1909797a199d962b50519c9e013de98b4e` | `v1.0.0-preview.4` |

完整包、清单、发布ID与源码对应见[公开包绑定记录](test-inputs/public-preview3-preview4-artifacts.json)。检查程序摘要和build-info，不能只看文件名或版本字符串。SHA256验证传输和来源记录的一致性，不等同于签名证明。

```sh
sha256sum /opt/crg/crg /staging/preview4/crg
/opt/crg/crg build-info
/staging/preview4/crg build-info
```

保留当前配置、profile、state_dir及journal。三项百分比字段无需改名，省略仍各自默认20%；本轮测试并未把默认20%判为DBS/HISDBS已验收业务预算。手动配置若要保留回退兼容，先保留旧`limits.memory_max`输入：preview.4将其解释为high并打印已知警告，preview.3仍解释为硬max。本轮测试配置字节全程不改。新手动配置规范字段是`limits.memory_high`，不要同时填两者，也不能假定新配置可直接交给旧版本。

升级前确认每个容器只有自己的一个Agent；原helper独立后台重试，CRG失败不得控制业务PID1退出。安装目录需要可原子替换且不是组/其他用户可写目录；只读挂载或不能rename的挂载点按[持久部署](installation.md)更新，不能假定在线命令必定可写。新镜像/每容器专用挂载必须持久保存新程序，临时复制不会自动进入未来Pod。

## 暂停、检查并安装

在本容器内串行执行。`/recovery/crg-preview4-session-001`应是本容器全新私有维护父目录，子目录`forward`必须不存在，不与安装目录、state_dir或profile重叠。保留所有私有恢复文件，不上传GitHub。

```sh
mkdir -m 0700 /recovery/crg-preview4-session-001
/opt/crg/crg quiesce --config /etc/crg/config.json
/opt/crg/crg upgrade-check --config /etc/crg/config.json
/staging/preview4/crg upgrade-check --config /etc/crg/config.json
/staging/preview4/crg binary-install --config /etc/crg/config.json \
  --install-dir /opt/crg \
  --backup-dir /recovery/crg-preview4-session-001/forward \
  --previous-sha256 dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8 \
  --candidate-sha256 6088721cd4846f95b3b71c82f9884e1909797a199d962b50519c9e013de98b4e
/opt/crg/crg build-info
```

逐项确认命令成功；预检应属于当前身份、compatible、当前禁用且quiescent。`quiesce`只暂停CRG写入者，保留内核控制和journal；`binary-install`持锁、保存旧程序/状态/收据再替换单个程序，不修改原start.sh、数据库或缓存。安装返回错误时先核对目标摘要与receipt，rename后同步失败可能已经换过文件，不能重复执行或假定完全未变更。

尚未启用新版且配置/journal/profile保持时，可以用当前安装收据做即时自动回退：

```sh
/staging/preview4/crg binary-rollback --config /etc/crg/config.json \
  --install-dir /opt/crg \
  --backup-dir /recovery/crg-preview4-session-001/forward
```

如果实际执行了这次回退，forward收据已结束；再次升级必须用新的全新恢复目录和匹配摘要，不能复用这张收据。

## 启用并核对内存迁移

保留新版时执行：

```sh
/opt/crg/crg enable --config /etc/crg/config.json
/opt/crg/crg status --config /etc/crg/config.json --format human
```

由原可选helper在下次重试中启动新Agent，不把CRG接入业务启动前置条件，不重启业务。检查最新而非旧status快照，实际写入者摘要/单实例、每项applied/恢复/跳过原因以及每日日志。旧手动字段兼容警告可能让总状态显示degraded，不能只凭该词认定失败或成功；三项实际结果及已知警告必须分别核对。

新版只将同身份journal仍归属自己的旧max恢复到记录原值，再设置high；外部或祖先硬上限保留。记录缺失、冲突、pending不匹配或恢复失败必须按实际结果处理，不能删除journal、强改身份或一律写`max`。CPU/IO预算及其他控制值应保持原约定；手动模式不应突然触发标定。high允许实际用量超过目标，不等于强制释放数据库所有工作集，也不能保证宿主或祖先限制下绝不OOM。

## 新版运行后的受控回退

新版迁移journal后，原forward收据的自动`binary-rollback`必须因状态快照变化而拒绝。拒绝时保留当前程序/收据/限额/journal，不能把旧state.json覆盖回去。此时继续使用原收据不是正确回退方法。

确需回到受测preview.3，先检查旧读取器与当前配置/journal兼容，并检查内存用量和旧硬目标的余量；回退会恢复旧硬max语义，当前用量超过旧硬目标时不能直接启用旧Agent。下列显式反向安装使用forward中已核对摘要的旧程序，从当前静默状态建立新收据，`reverse`目录必须全新：

```sh
/opt/crg/crg quiesce --config /etc/crg/config.json
/recovery/crg-preview4-session-001/forward/previous-crg upgrade-check \
  --config /etc/crg/config.json
/recovery/crg-preview4-session-001/forward/previous-crg binary-install \
  --config /etc/crg/config.json --install-dir /opt/crg \
  --backup-dir /recovery/crg-preview4-session-001/reverse \
  --previous-sha256 6088721cd4846f95b3b71c82f9884e1909797a199d962b50519c9e013de98b4e \
  --candidate-sha256 dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8
/opt/crg/crg build-info
/opt/crg/crg enable --config /etc/crg/config.json
```

反向安装只换程序，不导入旧journal、不绕过自动回退保护；启用旧Agent后再次核对原值归属、high恢复及旧max设置。若只想撤销CRG当前管理，使用当前版本`disable`并核对逐项恢复及剩余journal，而不是换回旧版本；外部冲突不强制覆盖。

## 验收边界

公开包迁移的实际终态从[本轮验证入口](testing-public-preview-memory-high-maintenance.md)查看。这里的两个预发布tag不代替实际已发布次版本验收，命名手动预算与合成64MiB真实路径检查不代替默认百分比、真实回收压力、老化状态和长期门槛。原七天任务继续同一来源、数据和计时，文档命令不自行修改任何现有环境。
