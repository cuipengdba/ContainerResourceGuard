# 原七天身份的单次采集保存

本工具补齐[capture-v3只读适配器](development-source37-capture-v3.zh.md)stdout到[v2后续执行契约](development-source37-aged-evidence-v2.zh.md)固定seal路径之间的准确持久化。它是隔离实验工具，不是产品Agent，不改DBS/HISDBS、Pod、进程或资源。只接受当前原1880两段24h与全新604800秒的身份，不继承旧时长或旧源资格。

## 窗口与固定输入

[保存工具](../tests/live-capacity-aged-v1/capture-save.py)及[固定契约](../tests/live-capacity-aged-v1/capture-save-contract.json)绑定正确capture-v3入口和原8文件逐字摘要。原reader、adapter、binding、原长测19、executor15及旧/新wrapper冻结目录均不修改。默认与--save在baseline/enforce阶段返回exit2/pending，不创建正式input、seal、attempt、authority或执行目录，也不调用capture子进程。

允许保存必须同时满足：原baseline与同容器enforce完整24h各自原独立审计passed、native_accepted=true；真实新七天仍measuring，原runner/worker身份live。终态后明确拒绝，不能补采。默认在窗口内也只读返回ready-to-save，只有--save才持久化。

工具创建/验证固定input目录0700且属当前root，在其内独占创建.capture-v1尝试目录。已有seal/attempt、错误权限、符号链接或输入源码不符都会拒绝；并发或重复调用不覆盖原尝试。先记intent，再运行准确适配器--capture，保留实际退出码、准确stdout候选和stderr；stdout不重排JSON。它校验schema/源/launch/namespace/两角色/原24h报告绑定，并再次检查真实window/process及原源，窗口关闭时保留候选与错误，不发布seal。

## 原子发布与失败边界

候选以O_EXCL/O_NOFOLLOW创建为0600，fsync文件和目录。发布使用当前Linux文件系统已实际测试的libc renameat2/RENAME_NOREPLACE：原子移动到lineage-seal.json，保持单链接，目标已有时保留源与原目标。系统/文件系统不支持时拒绝，没有覆盖式rename回退。最终核对准确stdout字节/0600，写入独占receipt.json记录摘要、字节数、capture/saved时间及源绑定。目录均0700、私有文件0600；无配置内容写到公开归档。

错误和部分完成现场保留，不移除guard、不自动再采。若发布后回执写入或后续fsync失败，seal可能已存在但调用失败，必须核对准确字节和现场，不得重新覆盖。本工具不宣称所有故障/掉电情形下完成记录原子一致；保存成功也只代表身份证据，actual_duration_accepted/postflight_allowed/P10_complete/release_accepted均false。

## 已验证与未完成

[13组检查](../tests/live-capacity-aged-v1/capture-save-checks.py)在当前Linux全部通过：旧完整双角色受控capture配真实临时文件/0600/renameat2，原样四空格stdout与摘要，重复/已有guard拒绝、发布目标竞争不覆盖、子进程失败保留候选、采集中窗口关闭不发布、源/角色/报告绑定/链接拒绝，以及默认/缺前置/禁止execute或目录覆盖参数。proc/Pod/native记录为受控替身，不能作为真实七天证据。Windows通过5组、8项Linux检查跳过。真实节点默认与--save均exit2/pending，所有正式目标仍不存在；原5组冻结目录共19/15/8/3/5文件逐字保持。

[结果](test-results-source37-capture-save.json)、[冻结11文件](test-plan-source37-capture-save.json)、[准确原件证据](test-evidence-source37-capture-save.json.gz)归档。没有真实seal、authority、老化执行或稳定发布资格。当前稳定1.0仍未发布，原52定义/18完成声明与所有旧失败/unknown保留。

## 后续实际用法

当前冻结入口/var/tmp/crg-save1979-tools-20261116/tests/live-capacity-aged-v1/capture-save.py。只读检查可随时调用；**--save只能在真实measuring-acceptance、两段24h已接受且native仍运行时使用**。源/进程/控制值均复核后单次调用：

```bash
python3 -B tests/live-capacity-aged-v1/capture-save.py
# 仅上述实际窗口内；stdout摘要作为后续可信输入单独保留：
python3 -B tests/live-capacity-aged-v1/capture-save.py --save
```

固定seal为/var/tmp/crg-aged-source37-inputs-20261116/lineage-seal.json，准确输出摘要与私有receipt对应。原capture-v3直接--capture仍是正确只读底层，但后续实际保存优先使用本工具；不能用旧lineage.py --capture，也不能等七天终态后再采。未来authority/previous准确下载、脱离SSH的[wrapper-v3](development-source37-aged-runner-v3.zh.md)单次启动及原独立qualify-v2真实回执/磁盘/清理/36检查仍待，不放宽原时长、维护、恢复及发布验收。
