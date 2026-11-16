# 新候选原18项正式业务复验：启动前冻结

DBS、HISDBS各新建独立namespace和输出，依次各跑一次原600秒enforce业务。每组原9项启动/业务检查，另2项辅助观察单独计数，总计原18项+辅助4项=22。前一组准确归属清理完成才开始下一组，原镜像/start.sh/软件和数据路径/只读CCG不变，每容器仅一个CRG控制自身，原缓存程序继续enforce。

本文件发布时15输入冻结、原生22项来源绑定故障检查、Windows21通过/1Linux专用跳过及只读服务器准入完成，尚未启动。本次来源与上一轮仅新路径、两个enforce矩阵和准确对照终态前置核对不同；业务campaign/worker/观察器字节相同，原测量代码块和全部原SLA/备份验收保持。冻结plan中的fault_qualification字段为前置对照原有资格，当前正式来源逐摘要原生检查在[本轮准备结果](test-results-fresh-formal18-v1-preparation.json)另列，不把两者混同。

[15输入和参数冻结](test-plan-fresh-formal18-v1.json)、[准确文本来源](../tests/fresh-formal18-v1/)、[独立复算程序](../tests/fresh-formal18-v1/qualify-selected-originals.py)。准确ELF仍为37ca44e0、AMD64 ee4f0a14，CRG产品源没有改动。外部8核/20GiB，手动7.2核、memory.high20001980416、读写64MiB/s和手动4096IOPS不变；此固定测试预算不改变产品三个独立百分比默认20或百分比IO仅带宽语义。

## 不借用前轮资格

[四组原600秒对照44/44、56准确原件和154清理登记](development-original600-comparison.zh.md)已结束并独立复算，本轮以其准确plan/report摘要和全部原进程/namespace/父叶组消失为前置；不借用其测量时间、数据或结果作为新原18项。旧1761 DBS错误仍失败且原因unknown。对照中的两个exec原5秒标志false完整保留，不作全部延迟通过或确定因果的断言。

原600秒、SQL/API零错误、max5秒、p95桶1秒、98%覆盖，以及备份/同步/独立恢复十项内容、原生窗口包围完整备份周期、真实PG端口归属和归属清理均保持。单独kubectl exec探针仍按既有规则原样保留诊断标志，只有原生完整成功窗口能验证内容周期。任何失败保留；无重试抹去失败、资源放宽或PG参数修改。

辅助观察与对照相同，每2秒只读本容器计数及固定PG等待，先于负载首样本、1800秒/900样本/4MiB上限、完整窗口后身份标记正常退出，绝不停止原PID1/Agent/cache。PSI若缺失仍明确unavailable，不能冒充压力实测。两组逐一清理，终态统一索引取回所有选定原件逐长度/摘要及业务条件复算。原9项与辅助2项不得混算或漏掉失败。

## 后续门槛

只有本轮原18项及辅助4项实际完成并独立核验，才准备全新从零24h observe、同容器24h enforce、新七天和原老化后故障/恢复/升级/稳定包门槛。当前新长稳未开始，稳定1.0未接受，preview.5保持。52项定义和18项既有完成声明不增加。

## 复用驱动的旧报告标签修正说明

运行后检查发现复用的per-role驱动仍写旧scope“fixed one-pair…not formal original18 acceptance”和formal_original18_acceptance=false。它不单独授予整体18项资格；这些原始字段按原件保留，不在测试后修改。正式复验的独立namespace/两个enforce矩阵/原600秒和原18+4门槛，已由启动前发布的正式coordinator和plan明确，不由这个旧标签决定。

[元数据修正记录及摘要](test-results-fresh-formal18-metadata-amendment.json)。[独立复算v2](../tests/fresh-formal18-v1/qualify-selected-originals-v2.py)除既有全部窗口/SLA/备份/控制/清理检查，还严格核对每角色准确原9个检查名称和另外2个auxiliary-diagnostic标签，显式保留原报告的false和旧scope，只有两组新实际结果全部满足才能授予整体原18项。原复算程序保留；本修改不改变正在运行的15输入、业务命令、限额、超时、备份、次数、SLA或失败政策。旧标签并非一次通过声明，也不能代替新独立结论。
