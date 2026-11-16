# 老化维护恢复原始证据与独立审核 v2

## 用户决定和开发任务归档

用户已明确选择：**仅支持回退到memory.high版本；旧memory.max开发版明确拒绝并保留不兼容记录。** 这是当前兼容范围，旧max版managed-resume不再作为当前验收要求；其历史定义、不兼容和未通过事实完整保留，不声称旧版通过。其它原长稳、恢复和发布要求不因此豁免。

本轮在[冻结v1执行器](../tests/live-capacity-aged-v1/executor.py)旁新增[证据增强v2](../tests/live-capacity-aged-v1/executor-v2.py)、[固定合同](../tests/live-capacity-aged-v1/execution-contract-v2.json)、[完整派生记录](../tests/live-capacity-aged-v1/executor-v2-derivation.json)、[独立只读审核](../tests/live-capacity-aged-v1/qualify-v2.py)，及[执行保护测试](../tests/live-capacity-aged-v1/executor-v2-checks.py)、[审核故障测试](../tests/live-capacity-aged-v1/qualifier-v2-checks.py)。这些是实验验收工具，不改变每容器一对一Agent架构或原产品启动链。

## 修正的证据缺口

v1的wait_guard主要凭单一进程和准确ELF判断Agent已恢复，既有“managed”命名检查没有保存足够的新状态快照，不能据此单独证明恢复后的管理状态。v2保留原全部方法、预算、300秒启动/45秒cache和每角色完整600秒/SLA，只增加证据与更严恢复检查，不改冻结旧文件和长测19输入。

恢复必须同时满足：唯一准确版本进程、正确身份的managed状态、三项applied、准确high/CPU/IO与五项外部控制不变，且状态文件mtime严格晚于enable前快照。记录旧/新stamp、实际ELF/PID/start、状态和journal摘要。不能用旧managed快照配新进程通过。

原八段在线维护记录实际CLI结果、安装程序摘要、控制值/journal/PID1/cache；每段结果状态必须符合操作。另保存老化最终校验、备份摘要/目录列表、恢复数据库与原库校验、两次journal轮换、disable返回/全部八项原值/空journal/零OOM，以及原目录/输入/日志前缀与追加数据。全部原条件保留；[逐字派生记录](../tests/live-capacity-aged-v1/executor-v2-derivation.json)可审核。

## 独立审核的范围

审核程序逐项重算两角色原18个命名检查，共36项，要求准确顺序、无遗漏/重复、严格布尔通过；另核对实际记录的恢复校验、两次新Pod/ID/PG/journal、600秒原生错误/最大5秒/p95桶1秒/98%覆盖、八段维护时间/顺序/来源、两次新鲜managed恢复、high与外部控制、disable和原日志。不能只靠36个passed标志。

真正接受还必须有原三阶段完整审计、真实七天seal、准确授权文件以及可信独立固定摘要的终态执行回执。回执格式crg-source37-aged-exit-v2绑定准确entry/PID/start、源/合同/授权/最终报告摘要、exit0及至少1200秒原执行时长。未来必须由单次运行包装器保存真实回执；**当前包装器尚待开发、没有回执，不生成合成回执用于实际验收**。

审核随后只读核对实际命名空间和两次Pod cgroup及父组消失、无其它数据消费者、保留目录inode/输入/当前程序、原日志前缀和每日0600日志、空journal/轮换/禁用标记、实际备份和native原件，以及审查期间报告摘要不变。报告层通过不等于实际文件/清理通过；实际组件通过仍不授予完整P10或稳定发布资格。

## 实际验证及边界

Windows执行器14组通过；审核16组中15通过、1项Linux文件权限测试跳过。Linux执行器14组、审核16组全部通过，其中实际临时文件测试核对inode/摘要/0600并注入配置、journal和日志前缀篡改；该合成测试的集群盘点被替身隔离，不是老化业务实测。

真机三个只读入口（v2默认、v2执行开关加测试节点标记、独立审核默认）均exit2/pending。新执行/输入/回执目录前后不存在，原长测19文件未变；随后原进程/八控制/ELF观察保持。Windows首轮审核15组有1失败，是夹具对象共享导致故障提前触发原值检查；按真实独立JSON文件拆开对象后通过，原检查不放宽。失败源和输出保留。

[完整结果](test-results-source37-aged-evidence-v2.json)、[15文件冻结计划](test-plan-source37-aged-evidence-v2.json)、[原字节证据](test-evidence-source37-aged-evidence-v2.json.gz)归档。当前只有保护/审核代码验证：没有真实seal、authority、执行回执或老化实际通过；原52定义/18完成声明保持，稳定1.0未发布。

## 后续执行顺序

继续准确1880的24h基线、同容器24h enforce、新604800秒/28周期；真实七天运行时采集[冻结reader身份快照](development-source37-aged-reader-v2.zh.md)。终态后独立核对全部原门槛，准备high预览目标准确附件和真实授权/单次执行回执，再运行v2及独立审核。固定执行入口为受权节点已冻结的/var/tmp/crg-aged1952-tools-20261116/tests/live-capacity-aged-v1/executor-v2.py；不能换旧d370/78源或借用旧时长。当前只读检查可以运行：

```bash
python3 -B tests/live-capacity-aged-v1/executor-v2.py
python3 -B tests/live-capacity-aged-v1/qualify-v2.py
```

[当前交付](release-readiness-current.md)、[完整需求](requirements.md)、[原52项审核](current-52-task-audit.md)、[新长稳](development-new-long1880.zh.md)继续分别记录。旧max不兼容保留，支持high版本的准确来源和真实恢复仍须实测，不能称两个已发布minor已经通过。
