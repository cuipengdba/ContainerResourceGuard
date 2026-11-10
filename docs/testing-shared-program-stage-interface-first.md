# 共享程序演练工具接口拒绝

[采样修正计划](test-plan-shared-program-stage-cadence.json)的两角色observe基线均实际600秒、SQL/API零错误；候选固定采样120.001秒取得60次，原59次门已通过。但随后旧冻结campaign不认识--smoke-enforce，未创建新enforce工作目录或启动原生负载便退出，切换工具读取不存在回执得到FileNotFoundError，本轮整体失败。

这次有保留的原始campaign stderr，明确记录unrecognized arguments: --smoke-enforce，不是仅从源码推断。旧参考入口自动恢复实际原值和旧observe程序，两Pod/cgroup、namespace与协调进程清理并独立确认。[详细结果](test-results-shared-program-stage-interface-first.json)保存60次采样、错误行/原始日志摘要、CLI和清理记录；首轮55次失败也保留。

[新冻结计划](test-plan-shared-program-stage-interface.json)分别声明正式86400秒与短时600秒工具摘要。正式阶段保留原campaign/engine，绝不改正在运行的基线文件；短时两阶段均使用已有并固定源码的managed-smoke/选角色工具。逐行差异只涉及这两个选项、smoke显式状态和角色传递，负载worker、所有数字预算/期限、数据/延迟/覆盖/零错误和清理条件不变。

切换前除摘要还静态检查实际CLI能力，不执行工具或创建状态，缺managed-smoke/engine-role接口立即拒绝。13项本地检查已通过，包含旧接口拒绝、当前固定源码接口通过和两套来源不能混用。后续使用全新夹具和run ID重新做两阶段完整600秒及独立恢复，不把本轮候选保持当成业务enforce通过。
