# CLI契约CI子进程终止记录：2026-11-11

组合分支`0f92af197183af32bc736f0f763cdc609f12c908`的[首次完整CI](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42967613817/attempts/1)中，`TestCLICommandFailureJSONAndLegacyBuildFields`的`run --percent 0`子进程报`signal: killed`，未达到预期exit1。原测试配置5秒context，但旧失败输出没有context.Err、子进程耗时，因而不能确定是超时还是外部终止。不能把先前“按5秒超时被终止”的推断写成已证实原因。

保留首次失败的日志摘要、测试源码摘要、固定case和完整来源；仅复验相同提交的失败job，没有改程序、超时、断言或业务预算。[第二次同提交CI](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42967613817/attempts/2)通过。该时点另外两分支的完整CI和两项ARM64检查也通过；这不消除首次失败，也不证明其原因已修复。[完整机器记录](test-results-cli-contract-ci-20261111.json)。

为使再出现时能定位，只在组合/分区两分支的`cmd/crg/errors_test.go`中补充失败诊断：在cancel之前记录context.Err及子进程耗时，原退出断言失败时打印stdout与exec.ExitError已限长的stderr。保留原5秒context、所有exit/JSON/旧build-info字段断言；不增加重试，不放宽阈值，不改任何生产Go文件。main没有这份候选专用测试，不向它移植候选运行时代码；本说明在三线同步。

新增诊断的编译/回归由其新提交的真实CI另行判断，旧提交复验不能冒充它的检查。持续实际七天和原业务预算、内核限额、已发布preview.1/preview.2资产保持；没有将这次CI事件记为业务实际故障，也没有声称程序从不出现阻断缺陷。若后续复现，应凭新诊断继续定位，不能再次只靠重跑结束调查。
