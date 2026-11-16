# 七天身份采集入口修复 v3

## 提前发现的两个缺陷

审查后续真实七天采集步骤时发现，冻结reader的capture分支传给旧core的计划没有roles字段；即使补上，复制的core还缺少path_clean全局绑定。此前已验证的baseline pending/提前capture拒绝在进入这段前就返回，因此并未证明完整采集路径。现在用受控输入明确复现KeyError roles和NameError path_clean；它们是采集工具缺陷，未发生真实长测采集失败，也不需重启1880。

原reader、binding、原core文件和现有v2执行器15文件保持逐字不变。本轮新增[只读采集适配器](../tests/live-capacity-aged-v1/capture-v3.py)、[完整受控采集与故障测试](../tests/live-capacity-aged-v1/capture-v3-checks.py)、[准确派生记录](../tests/live-capacity-aged-v1/capture-v3-derivation.json)。适配器保留原core体，只绑定原base.path_clean；原wrapper只改函数名并补固定dbs/hisdbs两角色。原资源、源/进程、Pod/目录/文件/journal/日志全部保护不删。

## 验证与实际资格

Linux8组全部通过，包含完整两角色临时文件采集、准确权限/摘要、原restart/ELF/journal权限/程序摘要/native阶段故障拒绝；Pod、proc和cgroup盘点为受控替身。Windows8组中6通过、2项Linux文件权限测试跳过。真实节点默认调用exit2/pending，提前--capture明确exit1/CAPTURE_ONLY_DURING_FRESH_SEVEN_DAY。未创建真实seal/authority/执行目录，19长测文件及原v2冻结15文件逐字保持。

输出仍为原crg-aged-lineage-seal-v1与原binding摘要，原v2执行器的readiness可继续验证；不重写冻结binding来加入roles，不修改长测源，也不让合成测试产生真实时长或采集资格。旧lineage.py默认/终态只读审计仍可用；**旧lineage.py --capture不再作为实际采集入口**。

[完整结果](test-results-source37-capture-v3.json)、[冻结8文件](test-plan-source37-capture-v3.json)、[原字节证据](test-evidence-source37-capture-v3.json.gz)归档。当前真实长测仍处于基线，真实七天采集和后续老化均未接受，稳定1.0未发布。

## 真实采集窗口和命令

必须等当前原24h observe与同容器24h enforce分别完整通过原审计，进入measuring-acceptance后，在其原604800秒native worker仍运行时采集；终态后不能补采，baseline/enforce不能采集。匹配完整且可信仓库的命令：

```bash
python3 -B tests/live-capacity-aged-v1/capture-v3.py
# 仅真实七天阶段允许；stdout含实验身份，私下保存准确字节/0600及摘要：
python3 -B tests/live-capacity-aged-v1/capture-v3.py --capture
```

当前受权节点已冻结入口为/var/tmp/crg-capture1958-tools-20261116/tests/live-capacity-aged-v1/capture-v3.py，准确源码摘要见计划；实际采集前再核对所有输入及原进程。程序不写文件、不发信号、不改Pod/cgroup，无execute开关；由后续单次采集保存工具在真实门禁通过后私下持久化，不能先造seal。

[v2执行器/独立审核](development-source37-aged-evidence-v2.zh.md)、[当前交付](release-readiness-current.md)、[完整需求](requirements.md)与[原52项任务](current-52-task-audit.md)保持原资格及用户high-only回退范围。未来还须真实seal、原三段终态、单次执行真实回执、原老化/恢复/发布等所有门槛。
