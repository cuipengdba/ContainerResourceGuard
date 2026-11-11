# 固定 IO 下的 Agent 活动对照：失败原件与继续验证

当前结论仍为 **inconclusive**。首轮在准备阶段失败；第二轮 A1 实际运行600.165秒，SQL错误5、API错误1，SQL采样覆盖率97%低于原98%，并有9次PG等待采样因超过四目标上限而失败。B1/B2/A2未执行。这些不是有效四臂对照，也不是产品性能修复或稳定版验收通过。[结果索引](test-results-agent-fixed-io-comparison-v2.json)、[独立分析](test-analysis-agent-fixed-io-comparison-v2.json)。

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
