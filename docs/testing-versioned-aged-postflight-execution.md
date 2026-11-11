# 版本化候选实际老化后置执行器

新程序dbc48aa5已有自己的执行器：[七天后置固定计划](test-plan-versioned-aged-postflight-execution.json)绑定R78真实七天数据、R80b私有谱系seal，另设[独立短数据演练计划](test-plan-versioned-aged-postflight-rehearsal.json)绑定本程序R64已完成业务的数据。原3a1/R57/R59/R60文件、计划、seal和计时全部保持。

[源码](https://github.com/cuipengdba/ContainerResourceGuard/blob/ee6d2e0e39e45690b3a6994b7b6ef64c0cbfe95e/tests/vendor-versioned-aged-postflight.py)明确分支出冻结0bd执行器，原controls/Pod适配/原生判定及全部Execution运行方法AST相同，仅报告元数据增加版本和模板身份；新的身份/计划/只读门禁独立实现。[10项回归](https://github.com/cuipengdba/ContainerResourceGuard/blob/ee6d2e0e39e45690b3a6994b7b6ef64c0cbfe95e/tests/vendor-versioned-aged-postflight-checks.py)核对原方法、原门槛、错误来源/模式、提前execute/权限标记/二次实时门禁、独占数据及UID清理。产品仍严格每容器一Agent；此程序仅为授权隔离节点的测试工具。

## 已核对的真实前置

[Linux10项自检和真实门禁记录](test-results-versioned-aged-postflight-readiness.json)：10项全部运行通过。七天默认检查及显式--execute均返回exit2/pending，未创建对应工作目录/namespace；独立短数据readiness通过。源码、读者、模板、固定worker/旧程序和两份计划分别有摘要；完整执行前仍二次核对实时门禁，缺明确隔离节点标记拒绝。

短数据证明来自R64原运行器私有报告的实际摘要66c381e4，而非公开脱敏报告的摘要；该报告12项/各600秒、正确程序/版本、原运行器退出0且同实例已消失、原namespace不存在重新核对。检查原生报告、原Pod模板、实际程序及缓存摘要，拒绝数据目录被其他Pod直接挂载或被可写/高权限上级挂载使用；只有满足严格只读及能力限制的上级节点监控视图可通过，无Pod名称白名单。原manual7.2CPU/20001980416B/64MiBps/4096IOPS和其他五项原值不变。

## 当前独立短演练

独立短保留数据演练已[终态36项通过](test-results-versioned-aged-postflight-rehearsal.json)：DBS实际600.332秒、HISDBS实际600.307秒，各8个维护区间均独立重算位于完整原生窗口内。运行器与worker原实例已退出、exit0；namespace及四次Pod的主cgroup/所有容器scope均独立确认不存在。[首个固定观察](test-progress-versioned-aged-postflight-rehearsal-start.json)保留当时13项pending，不覆盖为终态。原七天及新候选七天的原实例仍分别在线，短演练不接受七天。

实际复用本程序R64的64MiB/最终counter，重新开启原镜像/start.sh/PG及只读CCG；备份原schema并独立逻辑恢复、同数据再次新Pod ID/原journal隔离，在全新各600秒原生窗口内进行8段Agent安装/回退/恢复，核对PG/PID1/缓存/journal及八项控制保持；最终disable还原真正运行时原值、无OOM、日志0600前缀保留并追加，按UID清理所有本轮Pod/namespace。两角色共36项已通过，原启动300秒/缓存45秒/错误0/最大5秒/p95桶1秒/覆盖≥98%及宿主保留量不放宽。

实际七天门禁通过后才可运行七天计划，短数据不能充当老化数据或转移计时。执行器的加入不表示真实后置已执行：仍需完整604800秒/28周期及其真实备份恢复/新ID/维护、老化辅助故障和全部稳定条件。旧对端50671aa是未发布开发程序，不构成最近两个已发布次版本条件；默认20%/自动30%持续性能和未测硬件结论保持。
