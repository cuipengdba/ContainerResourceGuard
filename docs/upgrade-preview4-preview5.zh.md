# preview.4升级到带宽百分比版preview.5

本页适用于已经接入可选helper的单个容器，不需要Operator或重装Kubernetes。DBS和HISDBS分别执行，各自保留自己的配置、profile、state_dir/journal和日志。下面命令以已部署`/opt/crg/crg`、`/etc/crg/config.json`的linux/amd64容器为例；不是为未接入helper的容器自动修改start.sh。

## 下载并确认程序身份

从[preview.5发布页](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v1.0.0-preview.5)下载架构匹配的包及SHA256SUMS，解包到新的私有暂存目录。发布的八项附件均已[实际下载核对](test-results-preview5-publication.json)。以下`/staging/preview5`表示本次新解包目录，不与业务数据或原安装目录重叠。

```sh
sha256sum -c SHA256SUMS --ignore-missing
sha256sum /opt/crg/crg /staging/preview5/crg
/opt/crg/crg build-info
/staging/preview5/crg build-info
```

| linux/amd64程序 | SHA256 | 产品源码 |
| --- | --- | --- |
| preview.4 | `6088721cd4846f95b3b71c82f9884e1909797a199d962b50519c9e013de98b4e` | `180c86ad7986a76526a41575cc1c176d5da98a9c` |
| preview.5 | `be6b0aa9f9bf932d8b02872e86a9cffcfea6d7199e39c274694dce904af07333` | `ced461705ebc27315a59aefe463f9b4af47130a3` |

只有实际旧程序匹配上表时，才能照用下面的previous-sha256。其他版本或arm64使用对应发布记录中的实际摘要；不能用文件名替代身份核对。BUILD.json的产品源码与文档打包提交可以不同。SHA256核对不等于构建签名证明。

## 保留配置并暂停辅助写入

三个字段继续是`cpu_percent`、`memory_percent`、`io_percent`，各自省略默认20；不需要重建配置。示例：

```json
{"cpu_percent":30,"memory_percent":40,"io_percent":25}
```

preview.5只将io_percent换算为标定读写BPS，不新增IOPS限额；手动模式的显式IOPS仍可用。内存继续使用memory.high，外部memory.max保持。不要删除旧journal、io-profile.json或停用标记来强行更新。旧profile仍含IOPS测量值，这些诊断数据不会变成新的默认IOPS限额；设备身份不匹配时由自动流程处理。

在本容器内逐条执行，确认成功再进行下一条。下列维护父目录必须全新、私有且持久，`forward`子目录必须不存在，也不能与安装、状态或profile重叠。

```sh
mkdir -m 0700 /recovery/crg-preview5-session-001
/opt/crg/crg quiesce --config /etc/crg/config.json
/opt/crg/crg upgrade-check --config /etc/crg/config.json
/staging/preview5/crg upgrade-check --config /etc/crg/config.json
```

quiesce只暂停本容器CRG写入者，保留当前内核值和journal。upgrade-check应显示当前身份、compatible、disabled且quiescent。原业务继续运行，现有资源限额仍然生效。不能通过换state_dir绕开锁或启动第二个Agent。

## 替换程序并恢复辅助循环

原安装目录必须允许安全的同目录原子替换。若程序是只读挂载点，应更新原镜像或持久分发来源，按原部署流程加载，不能假定以下在线替换命令可用。临时向运行中的容器复制文件不会自动进入将来重建的Pod。

```sh
/staging/preview5/crg binary-install --config /etc/crg/config.json \
  --install-dir /opt/crg \
  --backup-dir /recovery/crg-preview5-session-001/forward \
  --previous-sha256 6088721cd4846f95b3b71c82f9884e1909797a199d962b50519c9e013de98b4e \
  --candidate-sha256 be6b0aa9f9bf932d8b02872e86a9cffcfea6d7199e39c274694dce904af07333
/opt/crg/crg build-info
/opt/crg/crg enable --config /etc/crg/config.json
/opt/crg/crg status --config /etc/crg/config.json --format human
```

binary-install持锁保存旧程序、状态及私有收据后替换程序，不修改数据库、缓存或原start.sh。若安装返回错误，先核对实际目标摘要和receipt：rename后的同步失败可能已完成替换，不能假定完全未改动后直接重复安装。enable后由原helper在下次重试中恢复Agent，可能等待5–300秒，不需要为了CRG重启业务。

检查新鲜状态与实际回读：一个Agent、新策略日志、cpu.max、memory.high以及io.max的rbps/wbps。新百分比不盲目清空IOPS：外部值保留；只有原容器/设备/journal/当前值保护成立时才恢复旧CRG自有IOPS到记录基线。状态缺失、外部改动或恢复冲突应按逐项结果处理，不能统一写max。进程存在、总状态词或预检打开成功都不能替代实际回读。

v1/混合/未知Cgroup或权限不足会记录跳过/降级，辅助失败继续原启动链。已生效的节流会影响业务速度。memory.high允许短时超过目标，也不能保证宿主或外部硬上限下绝不OOM。日志按容器本地日期一天一个文件，30个日历日/1GB清理。

## 回退与验收范围

尚未enable且配置、profile、journal仍与forward收据快照匹配时，可以按[安装与回退](installation.md)使用当前收据的binary-rollback。新版运行并更新状态后，旧收据必须拒绝快照不一致的自动回退；保留当前状态并从当前quiescent状态建立全新的显式反向安装收据，不能覆盖旧journal。若目的是解除CRG限制，优先由当前程序disable并核对原值恢复。

回到preview.4还会恢复它的四轴IO百分比语义，可能再次得到较低IOPS限制。回退同样要逐容器核对预算、单实例、实际值及数据库健康。恢复文件包含原状态，只在私有维护目录保存。

本页列出受保护的维护操作流程，不声明已完成preview.4到preview.5的正式已发布包全流程升级验收。准确CI的同容器旧IOPS基线恢复及新容器外部IOPS保留检查、[默认20/30原矩阵](testing-bandwidth-percent-terminal.md)、[独立HIS30补测](testing-bandwidth-calendar-HIS30-v2.md)与正式迁移是不同范围。以[当前验收入口](current-acceptance.md)为准；预发布不能当作稳定1.0已经接受。
