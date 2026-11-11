# 版本化候选保留数据辅助故障验证

新候选dbc48aa5已有自己的[故障执行器](https://github.com/cuipengdba/ContainerResourceGuard/blob/d1ac202a5fd157912a5de0ca008485dc19d95800/tests/vendor-versioned-aged-faults.py)和[9项合成检查](https://github.com/cuipengdba/ContainerResourceGuard/blob/d1ac202a5fd157912a5de0ca008485dc19d95800/tests/vendor-versioned-aged-faults-checks.py)。源码摘要818f96fb与两份计划固定，导入的版本化后置执行器摘要9e0c5d5a、旧模板28b7a8ac均先校验；原Execution运行方法除报告身份外与冻结旧模板AST相同，原挂载隔离、状态复制、场景Pod生成方法保持。生产程序未修改，产品仍一容器一Agent。

[真实七天故障计划](test-plan-versioned-aged-faults.json)只绑定R78/R80b/R81这一套候选自己的七天谱系及36项实际后置；[独立短计划](test-plan-versioned-aged-faults-rehearsal.json)只绑定本程序R64保留数据和已通过的[36项短后置](test-results-versioned-aged-postflight-rehearsal.json)。旧3a1程序/R57七天/R59/R60/R69b的计划、数据和计时不变，不转移旧二进制的时长或成绩。

## 实际门禁

[Linux9及真实只读结果](test-results-versioned-aged-faults-readiness.json)：9项全部运行通过；默认长检查和显式--execute均exit2/pending，没有创建故障工作目录或namespace。短计划的实际前置通过后，才单独启动本轮演练。默认不创建报告、锁或业务目录，实际执行要求隔离节点标记、二次实时前置和独占新目录。

前置验证精确程序/计划/来源、实际七天原进程或终态、后置36项与两角色实际600秒/四次新ID及清理、旧64MiB数据校验和/counter、目录inode、私有输入/journal/日志前缀、无并发业务挂载及宿主余量。直接或子目录挂载拒绝；上级监控视图必须全只读、不可提权、drop ALL、无SYS_ADMIN/ALL及无双向传播，不使用Pod名称白名单。

Windows首次合成检查因夹具将POSIX字符串与Windows原生Path字符串比较而失败，仅修正测试夹具构造；执行器和原门槛没有改动。修正后Windows9项中3项POSIX专用跳过，Linux9项全部运行通过。合成检查不替代真实故障矩阵和七天终态。

## 当前独立短演练

独立短保留数据故障演练已启动。[固定首观察](test-progress-versioned-aged-faults-rehearsal-start.json)只有1个场景/7项通过，原运行器和worker仍在线；尚未宣称20场景/152项完整通过。真实七天后的故障运行尚未开始。

每个业务分别执行缺失、无效、崩溃、卡住、忽略TERM、原supervisor回退、cgroup只读、profile只读、state只读、真实标定取消，共20场景/152项。原PG/API90秒、缓存45秒、TERM12秒、降级180秒、取消60秒及64MiB数据/PG不重启/唯一缓存进程和新状态/取消FD及cgroup身份标准不变。只复制小型辅助程序和状态，不替换原PG数据库；保留原程序、配置、journal、日志前缀，最后按UID清理并保留数据。

三个独立30%仅用于本故障隔离计划，不能证明默认20%或自动30%的持续业务性能。七天及后置、完整24h对照、最近两个已发布次版本和未测硬件仍分别等待实际验收；P10与稳定1.0未完成。
