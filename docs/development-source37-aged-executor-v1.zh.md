# 源37老化执行器与保护检查

## 本轮交付及需求归档

继续用户要求的每容器独立资源控制、memory.high策略及原DBS/HISDBS路径验收。本轮开发[新执行器](../tests/live-capacity-aged-v1/executor.py)、[固定执行合同](../tests/live-capacity-aged-v1/execution-contract.json)、[故障检查](../tests/live-capacity-aged-v1/executor-checks.py)和[逐项派生记录](../tests/live-capacity-aged-v1/executor-derivation.json)。它们属于测试节点验收工具，产品运行仍为每容器自己的Agent，不增加集中管理器，不接入生产start.sh。

已完成两平台各12组保护测试、测试节点两次真实pending调用。**未执行老化业务测试，没有真实七天seal或执行授权文件，原三阶段时长和稳定发布均未接受。** [完整结果](test-results-source37-aged-executor-v1.json)、[冻结10文件](test-plan-source37-aged-executor-v1.json)、[原字节证据及失败](test-evidence-source37-aged-executor-v1.json.gz)归档。原52项定义、18项既有任务完成声明不变。

## 保留原验收要求

执行逻辑从原vendor-versioned-aged-postflight独立派生，旧文件不改；原所有方法及no_other_mounts/adapt_pod原体保留，准确改动逐条记录。继续要求28GiB克隆/8GiB稳态可用内存、20GiB磁盘余量、300秒PG/API/managed启动、45秒新cache，以及每角色完整600秒原生SQL/API零错误、最大5秒、p95桶不超过1秒、覆盖至少98%、64MiB数据完整性和零OOM。

保留原老化目录inode/私有输入/原日志前缀、原启动链和只读CCG、唯一Agent/cache、独立逻辑备份及新数据库恢复、同数据新Pod/新ID/journal轮换、完整600秒内原八段在线维护操作、PID1/PG/cache不变、程序恢复、disable还原全部八项运行时原值及归属UID清理。主资源用cpu.max、memory.high、io.max；memory.max、memory.swap.max、pids.max、cpu.weight、io.weight五项必须原值不变。保留原手动参考预算与SLA，不代表默认20%业务保证。

## 旧回退目标不兼容的发现

原执行器固定的旧binary SHA3f69370b、源50671aa7是未发布开发版，只支持memory.max。只读version输出为next-compatibility-contract，不能误称已发布的小版本。当前用户已明确只用memory.high，因此新执行器拒绝此目标，不运行旧版硬内存上限。**原旧开发版的managed-resume兼容项仍未接受**，不删除原定义、不用新目标冒充原通过。

另固定支持high的公开preview.5目标：源ced46170、准确AMD64 SHAbe6b0aa9、4026528字节、release444410114。它的下载/安装及在本次老化数据上的恢复仍须实际核验；新旧二者的通过不能互换，也不等于“两个已发布minor”覆盖。这个选择遵循现有high要求，后续若改变兼容范围须单独记录，不能默许旧memory.max控制。

## 执行保护与后续步骤

默认只读。先运行冻结reader对准确1880进程/19输入与原24h、同容器24h、新604800秒报告审计；任何pending先返回，**不读seal/旧包、不做后续挂载盘点、不创建执行对象和工作目录**。执行开关及测试节点标记不能绕过。

仅真实七天阶段且前两段通过时，用[冻结reader](development-source37-aged-reader-v2.zh.md)采集原始身份快照。终态之后，保留真实原始seal到合同指定的私有路径，并通过可信渠道另行固定execution-authority摘要。授权JSON必须准确绑定schema、合同摘要、执行器摘要、reader/binding摘要、真实seal路径/摘要、previous准确SHA/源/tag/releaseID，字段集合完全一致；执行器不自动创建seal或authority。当前二者均不存在，不能用合成样本生成。

只有原三段、目录/日志/journal/源和旧命名空间/cgroup消失全部满足，才会检查独立目标未使用、旧包和worker准确摘要、无其它数据消费者。--execute另外要求CRG_AGED_POSTFLIGHT=authorized-disposable-test-node-only，并在独占新工作目录创建前重新完整检查。只操作固定实验命名空间及原保留的实验数据，保留原归属保护；线上容器不加入范围。

受权测试节点上默认只读入口：

```bash
python3 -B tests/live-capacity-aged-v1/executor.py
# 仅完成全部真实前置步骤后，以私下固定的实际授权文件及摘要检查：
python3 -B tests/live-capacity-aged-v1/executor.py --authority /var/tmp/crg-aged-source37-inputs-20261116/execution-authority.json --authority-sha256 "$TRUSTED_AUTHORITY_SHA256"
# 同一入口加 --execute 才可能执行；目前仍因真实前置条件不足而pending。
```

旧只读binding的executor_available=false保留其发布时事实，不回写冻结件；当前执行器状态另在本页及当前任务登记中说明。

## 实际验证与失败保留

Windows首次12组有1个测试夹具错误：importlib未登记模块，使inspect.getsource(class)报TypeError；修正测试加载后12组通过。首次原生传输因224226字节命令超过shell参数上限，在Python执行前拒绝；保留原回执。改用含摘要断言的压缩传输，解码内容逐字相同，新工具目录独占创建后Linux12组通过。

实际默认及--execute+明确标记均返回exit2/pending；新执行目录及输入目录前后都不存在，长测19输入逐字不变。随后独立观察原runner/worker/recorder、两角色八控制及实际ELF均保持，当前仍为baseline。测试只证明前置保护及合成故障行为，不授予真实老化/回退/发布资格。此前失败及unknown原因、全部原门槛保持。

[当前交付](release-readiness-current.md)、[完整需求](requirements.md)、[原52任务](current-52-task-audit.md)、[新长稳](development-new-long1880.zh.md)、[包演练](live-capacity-package-rehearsal.zh.md)。后续须继续真实长测、适时采集、终态独立审计、原老化执行及稳定包/下载/安装回退门槛。
