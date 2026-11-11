# 首轮写带宽对照失败与测试适配修正

[实际终态](test-results-write-bps-comparison-failure.json)保留全部三组失败。协调器退出0只表示序列结束，不能作业务通过：A1与B分别只有4项局部检查，均因RELOAD_DEADLINE_invalid-IO-retains-entire-policy提前停止，原生实际95.725/94.676秒、interrupted=true、采样覆盖不足，不能用其SQL/API零错误推断600秒达标。A2仅2项启动检查，NATIVE_PREPARATION_EXIT，测量未开始。三组不能回答写带宽因素，原R235失败仍未解除。

原百分比测试用io_percent=101并预期错误中包含io_percent；手动对照适配后，这条输入同时混入两种模式。实际Agent正确保留generation3的上一整套策略，错误为manual resource_mode cannot include percentage parameters，测试器却等待另一条错误而超时。原执行器/计划/失败快照保持，不将产品正确拒绝改成允许混用。新v2测试器只把该输入换为manual limits.io_write_bps="bad"，预期io_write_bps解析错误；其余拒绝/保留与控制读回继续。

A2的最终原生报告只记录RuntimeError类别、零SQL/API样本；实际PostgreSQL CSV在23:54:14.120 CST记录本轮CREATE TABLE耗时5469.527ms，超过原默认5秒查询期限，时间与准备退出相符。没有原生异常消息或准备阶段逐请求诊断，不能把它说成已精确确认的完整异常链，也不延长该期限。pg_tblspc为空；原源目录配置、PG控制及程序摘要保持，先前两组失败数据不写回源。全部三个namespace/cgroup、主协调/负载入口已证明退出，配置恢复/profile缺省状态恢复；副本及失败数据保留。

已冻结[修正v2计划](test-plan-write-bps-comparison-v2.json)，改动清单与[实际12项前置](test-results-write-bps-comparison-v2-qualification.json)明确区分。额外用已发布的精确ELF及只读doctor实际验证混用模式、非法手动IO、半截JSON、重复键四种错误；首次误用了不存在的plan命令，得到usage_invalid/unknown command，未启动负载，改为已有doctor后才计数。准备或重载夹具失败将停止后续组，不继续生成无效对照。原业务超时/载荷/配额与诊断A/B写BPS差异不变。

原[首轮GitHub CI](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/43053718436)在安装包文档链接检查失败：两个文档引用了未打包的tests下新增脚本；另两分支对应43053762756/43053812606同一步失败。已改为指向固定已提交GitHub源码的链接，保留包装检查，不计原失败CI为通过；修正后独立CI另行核对。
