# 固定 IO 下的 Agent 活动对照：失败原件与继续验证

[固定IO四臂449终态](test-results-agent-fixed-io-comparison-v3.json)：A1/B1/B2/A2的SQL,API错误依次为0,0/0,0/2,5/1,0；B2暂停Agent时仍实际600.294秒/SQL2/API5，原业务失败保留。独立结论为preplanned-association-not-observed，不作Agent因果或产品性能修复；30个原实例、四namespace和父叶cgroup独立清理，原来源和副本恢复。只读分析器修正业务失败出口无重复摘要的读取缺陷，旧源码/错误原件保留，3个真实臂及17个合成反例共20项复核通过。对照结构资格不等于原业务SLA通过；原32项/两角色/配额/门槛、52任务和长期条件保持。

[固定IO后续449进展](test-progress-agent-fixed-io-comparison-v3.json)：A1/B1分别实际600.307/600.350秒，SQL/API均0、原十项引擎检查及每臂七个实例/namespace/父叶cgroup独立清理复核合格；2026-11-11T23:59:37Z原runner/worker和B2 Agent/watchdog存活。全四臂尚未完成，不计有效ABBA、原32项压力/两角色或稳定验收。新只读分析器按完整证据独立判定，两个真实臂复核及16个合成反例共18项通过；原两轮失败和严格资格保持。

前两轮结论为 **inconclusive**。首轮在准备阶段失败；第二轮 A1 实际运行600.165秒，SQL错误5、API错误1，SQL采样覆盖率97%低于原98%，并有9次PG等待采样因超过四目标上限而失败。B1/B2/A2未执行。这些不是有效四臂对照，也不是产品性能修复或稳定版验收通过。[结果索引](test-results-agent-fixed-io-comparison-v2.json)、[独立分析](test-analysis-agent-fixed-io-comparison-v2.json)。

## 原件和实际观察

| 轮次 | 实际结果 | 清理与证据 |
|---|---|---|
| 首轮435 | A1准备失败，报告只保留通用ValueError；未进入Session或600秒负载 | 原runner/worker已退出，四namespace及A1父叶cgroup独立确认不存在；完整原件保留 |
| 修订441 | A1满600.165秒、64MiB数据完整、PG未重启、原十项备份/同步/独立恢复内容检查通过；SQL/API为5/1，诊断不完整 | 九个已记录原实例退出、四namespace及父叶cgroup消失；原来源和副本配置/程序/profile恢复 |
| 后续449 | 2026-11-11T23:37:04Z实际快照为A1运行中；原runner/worker、Agent和watchdog存活 | [冻结计划](test-plan-agent-fixed-io-comparison-v3.json)、[实际启动和身份](test-start-agent-fixed-io-comparison-v3.json)；尚无本轮终态或有效ABBA结论 |

首轮源码错误地要求helper的argv包含optional-agent.sh；该文件由原supervisor通过source加载，实际子shell继承supervisor的argv。修订轮已实际核对直接父子关系、PID/start_ticks、同一叶cgroup、helper非PID1，以及helper/supervisor实际argv与exe摘要一致。首轮没有保留具体断言，不能倒推断定唯一运行时原因。

修订441完整保留了原SQL/API错误。连续SQL客户端超时后，PG内仍有同一唯一轮次的多个未结束后端；9次等待快照遇到5至6个目标，超过已冻结四目标上限，原工具明确报告PG_WAIT_ROW_BOUND_OR_TRUNCATED。原PG活动行仍保留，缺少的proc等待细节没有改成0或宣称采集成功。SQL覆盖率97%同样保留为不合格，不放宽98%门槛。

线程观察13次D状态均指向DBS.log，其中API错误区间有4次严格时间内重叠。SQL错误区间没有该DBS线程D采样，PG活动记录有WALWrite/BufferContent等等待；620份可选内核栈未知。重叠不是IO因果。Agent约616.427秒采样端点间累计CPU1.13秒、记账write_bytes增加24576字节；包含准备和末尾采集，不能当作独占600秒或设备归属IO，也不能仅据此排除影响。

## 后续执行边界

修订包装器此前还将原业务Rejected重新加上ACTIVITY前缀。原异常是ValueError子类，下一轮先原样传播业务异常，再处理独立辅助错误。[24项纯错误边界/继续记录检查](test-results-agent-fixed-io-boundary-checks.json)及[26项可重放检查](test-results-agent-fixed-io-offline-checks.json)已通过，后者包括源码变化、摘要宣称通过但缺少实际活动采样的合成负例。这些是离线单元检查，不是厂商负载通过。

后续449的严格arm_eligibility函数与修订441的AST完全相同。四臂仍为A1/B1/B2/A2，每臂预先冻结新的完整冷reflink副本，CPU7.2核、内存20001980416字节、读写BPS64700080/37470104、读写IOPS83/135保持；原600秒、64MiB、十项引擎、SQL/API截止时间、采样率和诊断四目标上限均不变。冷副本不表示清空宿主页缓存；共享后端、缓存和顺序混杂仍存在。

只有原600秒/数据/引擎、精确Agent生命周期、内核值、线程/设备和清理完整，而性能覆盖率或明确PG四目标溢出不合格时，允许把剩余臂作为额外观察继续记录。其他异常停止。该允许条件不是合格判定；任何臂仍不合格，最终必须为inconclusive，退出2，不能据剩余臂声称有效关联。只有四臂原严格资格全部满足后才判预定错误模式；仍不直接证明产品因果。

一容器一Agent保持。暂停仅用于自有一次性测试容器的精确Agent pidfd；业务PID1、数据库和缓存不暂停。正常/异常出口恢复同一Agent，保留独立watchdog保护和原资源恢复/清理。此工具不安装为产品功能。

## 离线复核

从完整源码运行，只有本地证据读取和自有临时合成文件，无节点连接或控制器写入：

```bash
python3 tests/analyze-agent-fixed-io-comparison.py --terminal docs/test-evidence/agent-activity441-terminal.json.gz --a1 docs/test-evidence/agent-activity441-a1.json.gz
python3 tests/agent-fixed-io-offline-checks.py
```

[首轮执行器](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-agent-fixed-io-comparison.py)、[修订441执行器](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-agent-fixed-io-comparison-v2.py)、[后续449执行器](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-agent-fixed-io-comparison-v3.py)、[独立只读分析器](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/analyze-agent-fixed-io-comparison.py)、[离线检查源码](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/agent-fixed-io-offline-checks.py)。发布包不含这些测试执行器，复核应使用完整源码。

[原七天句柄只读快照](test-progress-seven-day-during-fixed-agent-comparison.json)在2026-11-11T23:40:13Z仍存活：R57两角色约95185/95173秒、5周期；精确发布程序R78约81670/81668秒、4周期。SQL/API错误0，最大宿主采样间隔约60.47/60.33秒，未达到实际604800秒及后置条件。

本次不修改产品程序、已发布preview.3附件、52项原始任务定义、原32项压力/两角色业务、七天句柄、正式24h对照和未测硬件条件。稳定v1.0.0仍未验收。

## 后续449已完成的两个臂

[固定IO后续449进展](test-progress-agent-fixed-io-comparison-v3.json)：A1/B1分别实际600.307/600.350秒，SQL/API均0、原十项引擎检查及每臂七个实例/namespace/父叶cgroup独立清理复核合格；2026-11-11T23:59:37Z原runner/worker和B2 Agent/watchdog存活。全四臂尚未完成，不计有效ABBA、原32项压力/两角色或稳定验收。新只读分析器按完整证据独立判定，两个真实臂复核及16个合成反例共18项通过；原两轮失败和严格资格保持。

[部分独立分析](test-analysis-agent-fixed-io-comparison-v3-progress.json)记录A1/B1各25项资格条件。A1活动采样端点约619.410秒累计CPU1.19秒，记账write_bytes增加24576字节；B1端点约620.310秒CPU和进程IO记账均无进展，实际STOP/CONT各1次且正常恢复。此处端点包含准备和末尾采集，不是独占600秒的设备IO。B1有2个DBS.log线程D样本但无请求错误；不能仅据D状态或零错误证明因果。

[18项证据读取检查](test-results-agent-fixed-io-v3-evidence-checks.json)中，2项重放实际A1/B1，16项使用临时合成反例；包含同摘要重绑后的不足600秒、缺失/错位进程清理、helper父身份、实际配额、活动覆盖，以及B1未恢复/CPU继续增长/watchdog提前恢复。合成结果不计厂商负载。公开检查命令：

```bash
python3 tests/analyze-agent-fixed-io-comparison-v3.py --arm-evidence docs/test-evidence/agent-activity449-a1.json.gz --arm a1
python3 tests/analyze-agent-fixed-io-comparison-v3.py --arm-evidence docs/test-evidence/agent-activity449-b1.json.gz --arm b1
python3 tests/agent-fixed-io-v3-evidence-checks.py
```

[V3只读分析器](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/analyze-agent-fixed-io-comparison-v3.py)、[证据拒绝检查](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/agent-fixed-io-v3-evidence-checks.py)。这些测试源码不在安装包内，应使用完整仓库。B2/A2及最终独立清理仍待实际结果，未发布新的产品程序。

## 后续449完整四臂结果

[固定IO四臂449终态](test-results-agent-fixed-io-comparison-v3.json)：A1/B1/B2/A2的SQL,API错误依次为0,0/0,0/2,5/1,0；B2暂停Agent时仍实际600.294秒/SQL2/API5，原业务失败保留。独立结论为preplanned-association-not-observed，不作Agent因果或产品性能修复；30个原实例、四namespace和父叶cgroup独立清理，原来源和副本恢复。只读分析器修正业务失败出口无重复摘要的读取缺陷，旧源码/错误原件保留，3个真实臂及17个合成反例共20项复核通过。对照结构资格不等于原业务SLA通过；原32项/两角色/配额/门槛、52任务和长期条件保持。

| 臂 | 实际秒数 | SQL错误 | API错误 | 原业务结果 | 对照结构资格 |
|---|---:|---:|---:|---|---|
| a1 | 600.3067028289661 | 0 | 0 | passed | True |
| b1 | 600.3501063410658 | 0 | 0 | passed | True |
| b2 | 600.294336708961 | 2 | 5 | failed | True |
| a2 | 600.3254991818685 | 1 | 0 | failed | True |

[逐臂独立分析](test-analysis-agent-fixed-io-comparison-v3.json)与[固定原件索引](test-results-agent-fixed-io-comparison-v3.json)保留完整native、逐请求/PG、线程、设备、引擎、Session及独立清理。eligible仅表示数据适合本次诊断对照；B2的failed和2/5错误没有改成业务通过。B2约616.736秒活动采样端点间CPU ticks及进程IO记账无进展，25个DBS.log线程D样本，其中五个API错误区间各有4个严格重叠样本；两个SQL错误区间没有该DBS线程D样本。原内核限额始终有效，暂停Agent不等于解除资源限额。共享设备、缓存和顺序混杂仍在，不能据此认定完整根因或排除所有Agent影响。

旧读取器e23ba74e在B2原业务异常路径抛出KeyError(native)：原始600秒native文件完整且摘要绑定，但原包装器在异常前未保存boot.native重复副本。[旧源码/退出原件](test-evidence/agent-activity449-reader-failure.json.gz)保留。修订只在原报告failed/NATIVE_COMPLETION_EXIT且原始native确为failed、原始文件摘要绑定时允许缺少重复副本；存在副本仍必须逐值一致。源/计划、数值额度、原业务条件和严格四臂资格不变。[20项复核](test-results-agent-fixed-io-v3-evidence-checks-v2.json)含实际失败B2重放和“通过臂缺重复摘要仍拒绝”的反例。旧18项报告及旧进度索引继续对应原提交版本。

从完整源码复核最终证据：

```bash
python3 tests/analyze-agent-fixed-io-comparison-v3.py --terminal docs/test-evidence/agent-activity449-terminal.json.gz --a1 docs/test-evidence/agent-activity449-a1.json.gz --b1 docs/test-evidence/agent-activity449-b1.json.gz --b2 docs/test-evidence/agent-activity449-b2.json.gz --a2 docs/test-evidence/agent-activity449-a2.json.gz
python3 tests/agent-fixed-io-v3-evidence-checks.py
```

[原长期进程实际快照](test-progress-seven-day-during-final-agent-review.json)在2026-11-12T00:16:37Z仍为measuring：R57约97587/97575秒、5周期，精确发布R78约83771/83769秒、4周期，原实例/SQL/API错误0保持。尚非实际604800秒及后置通过。preview.3既有标签和八份附件不变，产品程序不因本轮诊断改变，稳定v1.0.0仍未验收。

2026-11-12完成[只读proc错误元数据运行时资格](testing-proc-read-error.md)：宿主与两厂商镜像各24项，共72项，两个新自身探针read为EACCES/13；旧2410个泛化OSError仍未知。后续PG目标集成/资格任务单独归档，不改变旧采样器、原配额/SLA/长期句柄或发布附件，稳定1.0仍待。
