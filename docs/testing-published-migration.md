# 已发布旧版的首次迁移与回退

本测试补充 P08 的实际发布包兼容证据。此前的 [22 项维护验收](testing-versioned-candidate-maintenance.md)使用未发布的 50671aa 开发构建作为旧程序；本轮改用 GitHub 的真实旧包。旧包没有声明维护锁协议，继续要求 `binary-install` 明确拒绝，随后测试文档规定的匹配旧版停用、原值恢复、私有备份、手动原子替换及回退。

此路径包含明确的恢复原值阶段，三项限额会按阶段变化，不能替代原“维护期间所有控制值保持”的 22 项条件。本轮只覆盖一个已发布旧次版本 0.1 到 1.0 候选的往返；preview.1 与 preview.2 的程序相同，不算两个不同旧次版本，尚不能关闭“最近两个已发布次版本”的原兼容条件。原百分比 32 项业务、历史失败和真实长期条件保持。

## 程序、启动链和固定预算

| 程序 | GitHub 发布 | 实际 AMD64 ELF SHA256 |
|---|---|---|
| 旧版 | [v0.1.0-rc.3-preview.1](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v0.1.0-rc.3-preview.1) | `f07973272313db26d359797dda4665145f7dd6490bac2a55f9084bd367faf361` |
| 当前版 | [v1.0.0-preview.2](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v1.0.0-preview.2) | `dbc48aa5a4aa4d4a77c6af03d3294a9fcf08a6855672a80b003fccd1fed8a2c8` |

资产 ID、压缩包 SHA256、字节数和依赖来源见[首轮计划](test-plan-published-migration.json)与[修订计划](test-plan-published-migration-v2.json)。旧版与当前包的可选 helper 摘要相同；不换用临时开发二进制。

使用已授权测试节点上的两个原厂商镜像和原 `start.sh` / supervisor，分别新建私有测试数据、配置、凭据及 loopback DCS，业务网络隔离。DBS 缓存状态路径为 `/home/ccg-backups/dbs`，HISDBS 为 `/opt/PUC-784/ccg-backups/hisdbs`；原 `/opt/ccg` 只读挂载、数据库参数和业务启动链保持。CRG 使用 `/opt/crg/crg`、`/etc/crg/config.json` 与同一 `/tmp/containerresourceguard` 状态目录。每个容器只由本容器一份 Agent 控制；不更改已有业务环境。

本轮使用原维护测试的手动额度：CPU 7.2 核、内存 20001980416 字节、读写各 67108864 B/s 与 4096 IOPS。明确停用/恢复时要求回到测试 Pod 的真正运行时原值：8 核、21474836480 字节、无 IO 限额。`cpu.weight`、`pids.max`、`io.weight`、`memory.high`、`memory.swap.max` 全程保持。该手动额度不是新的百分比默认或部署建议。

## 迁移阶段与接受标准

| 阶段 | 三项内核控制 | journal 要求 |
|---|---|---|
| 旧版托管、quiesce | 原手动额度 | 保留相同原值记录及容器身份；私有备份活动 journal |
| 匹配旧版 disable/restore | 精确运行时原值 | 恢复成功的条目清空；版本、容器身份和目标保持 |
| 禁用状态下替换二进制 | 精确运行时原值 | 无 Agent 写入者；原状态目录保留，私有备份不导入其他身份 |
| enable 后新/旧 Agent 恢复 | 相同手动额度 | 重新捕获与最初完全相同的原值记录 |

替换前后检查目标路径、ELF 摘要、禁用与无写入者状态；同目录独占临时文件、fsync、原子 rename。回退前由真实旧版读取当前版的三资源 journal 并恢复原值；不删 journal、不伪造身份、不绕过自动安装器的协议检查。原可选 helper 独立重试，不成为业务启动的前置条件。

两角色分别要求 PG/API/managed 在 300 秒内就绪，原缓存在就绪后 45 秒且总启动 300 秒内 enforce。每角色 13 项、合计 26 项；每角色原生 SQL/API 各连续 600 秒，错误 0、最大 5 秒、p95 上界桶不超过 1 秒、覆盖至少 98%，原 64MiB 内容和 PG 启动时间不变。所有迁移/恢复 Agent 操作必须完全落在原生测量窗口内；最后停用精确恢复运行时原值，PID1 与缓存进程保持，测试进程、namespace 与自有 cgroup 独立确认清理。

## 保留的首轮失败及修正

[首轮结果](test-results-published-migration-first-failure.json)为失败：两个角色各进行 7 项，分别在匹配旧版 disable 后触发断言，未执行替换或回退。旧版 `Restore` 在读回原值成功后删除对应 mutation；首轮测试错误地仍要求非空原值 map 保持。终态两 journal 均为空，但首轮没有保存断言时的内核控制向量，不能补称原值恢复验收通过。两份原生报告仅为中途 `running` 快照，零初始计数不是 600 秒业务通过。

首轮源码、计划、报告、局部负载与独立退出/namespace/两个 Pod 父 cgroup 清理记录均保留在[压缩原件](test-evidence/published-migration392-failed.json.gz)。没有修改首轮失败或把它记为产品恢复缺陷已排除。

修订执行器仅修正各阶段 journal 预期并增强记录：活动 journal 先做私有备份；禁用后要求空 journal；每次恢复 Agent 后要求重新捕获相同原值 map；逐次记录实际八控制值、身份/原值 map 摘要及独立不变量结果。原预算、路径、启动/SLA/600 秒条件不变。[修订源码](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-published-migration-v2.py)和首轮源码独立保留。

修订版实际通过两项二进制身份与十二项默认只读/缺标记/计划篡改拒绝检查，确认未创建业务目标后才启动。[固定开始快照](test-start-published-migration-v2.json)有 11 项 DBS 局部检查、15 段维护操作且原运行器和 worker 存活；此快照不是两角色终态或 600 秒通过。

原始私有 journal、状态备份、Pod 环境与凭据不上传。公开的备份只包含字节数、SHA256、权限/排除说明；公开证据不支持跨容器恢复原值。

## 独立复核

[只读复核工具](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/analyze-published-migration.py)先核对压缩原件、每个文件摘要及计划/源码/报告绑定，再独立检查 26 项、原生时长/直方图/覆盖率、实际三资源阶段值、其他五项保持、journal 重新捕获、私有备份元数据、迁移时间窗与独立清理。首轮原件必须返回 `not-accepted`，不会用初始零错误或运行器摘要补齐缺失测量。

本次仅更新测试、证据与文档，不更换既有发布资产，也不宣称稳定 1.0 已接受。

## 修订版实际终态

[26 项终态](test-results-published-migration-v2.json)及[独立复核](test-analysis-published-migration-v2.json)通过；原运行器自然退出 0，首轮失败及固定开始快照保持。

| 角色 | 原生实际秒数 | SQL/API 错误 | 主检查 |
|---|---:|---:|---:|
| DBS | 600.405 | 0 / 0 | 13 |
| HISDBS | 600.322 | 0 / 0 | 13 |

两角色各 15 段迁移操作均完全位于本轮原生 600 秒窗口内，实际三资源控制按声明阶段转换，其他五项保持；PID1、原数据库启动时间、缓存进程与 64MiB 数据校验保持。两次恢复 Agent 后重新捕获相同原值 map，最终停用后 journal 条目清空，精确恢复运行时原值。

独立终态确认两个原测试进程、两个 Pod 父 cgroup/业务容器叶 cgroup 与 namespace 均消失，全部冻结输入仍匹配。旧程序回退后已安装及私有备份 ELF 均等于原发布旧版；两份私有状态备份权限为 0600，摘要与运行记录一致，原始内容不公开。

离线复核另保留两项明确的合成负例：改变源码却保留旧摘要会拒绝；即使协调器写 26 项通过并重新计算一致的完整性元数据，缺失 HISDBS 原生报告仍不能接受。它们是读取器验证，不是新的实际业务故障。

在源码仓库只读复核：

```bash
python3 tests/analyze-published-migration.py --evidence docs/test-evidence/published-migration397-terminal.json.gz --require-pass
```

该结果补齐一个真实旧发布次版本的受控迁移路径，不修改原同限额维护、两个已发布旧次版本、原 32 项百分比业务、历史失败或长期条件。后续 IO 定位见[相同内核限额下的活动对照计划](plan-agent-fixed-io-comparison.md)，尚未执行。原 GitHub 资产保持。
