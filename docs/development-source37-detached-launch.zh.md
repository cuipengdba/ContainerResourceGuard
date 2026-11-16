# 原老化验收的一次性后台启动

本工具补齐[前台wrapper-v3](development-source37-aged-runner-v3.zh.md)的安全后台交接，避免55秒SSH会话结束影响正式验收。它是隔离实验工具，产品Agent的每容器一对一和业务原启动链保持不变。当前只通过受控保护测试，没有启动真实老化验收。

## 准入和固定入口

[启动器](../tests/live-capacity-aged-v1/launch-aged.py)与[固定契约](../tests/live-capacity-aged-v1/launch-contract.json)固定正确wrapper-v3入口、原5文件摘要、独立launch目录。导入原wrapper后继续核对原executor15，调用原readiness；默认只读，--launch在原长测未完成时仍exit2/pending，不创建launch/runner/input/postflight。只有原两24h+新604800秒全部终态原审计通过、真实运行窗口采集的seal及可信authority、准确high-compatible previous等原条件完整，并提供明确实验标记/authority摘要，才允许启动；独占目录前再次核对readiness和源。

正确wrapper入口/var/tmp/crg-runner1971-tools-20261116/tests/live-capacity-aged-v1/runner-v3.py，SHA0c0ab9d433ed7e9aa59b81de4cf0fede1d876df79aa9b86074e4d91a3bb4dad3。旧runner-v2有放行信号缺口，不作为正式入口。新启动器单独使用/var/tmp/crg-aged-source37-launch-v3-20261116，不预建wrapper独占目录/var/tmp/crg-aged-source37-runner-v2-20261116，也不改变其实际exit.json路径/原schema。

## 一次交接及不确定结果

launch目录独占0700，intent/start/launch/error记录及stdout/stderr均O_EXCL/O_NOFOLLOW创建0600并持久化。新子进程先等待管道字节；父进程必须先保存实际PID和/proc start ticks，随后才放行。子进程再复核wrapper摘要，把stdin切换/dev/null后exec到正确wrapper，PID/start不变。start_new_session/close_fds及私有输出文件让它脱离SSH且不继承会话输出管道。子进程再由原wrapper负责真正执行器退出和清理，启动器不等待或伪造1200秒。

放行提交段暂屏蔽父进程SIGINT/SIGTERM，避免状态不一致；提交后记录到达的信号，不宣称已取消后台任务，也不把父进程信号转发给已交接的wrapper。提交前观察到信号则拒绝放行。写G已经尝试但flush/回执失败时，后台可能继续，保留PID/start、guard和error，必须核对原尝试；不重试、不kill、不删除guard。明确未尝试放行的子进程只会看到EOF并退出，父进程只等待该自有子进程。

launch.json的handed-off-not-qualified只证明交接已尝试/flush并记录，不是wrapper已经执行成功、不是执行器退出或业务通过。早期源校验失败可使子进程exit126；启动回执仍不能代替后续原exit.json。已有launch或wrapper尝试均拒绝新spawn，信号/SIGKILL/写入错误后也不能自动换目录再跑。不宣称掉电下整个交接事务原子一致。

## 已验证和边界

[12组检查](../tests/live-capacity-aged-v1/launch-aged-checks.py)在Linux全部通过：真实短子进程PID/start、setsid与stdin/devnull、0700/0600、重复拒绝、start落盘失败不运行、子进程源变化exit126、放行后回执失败仍保留原尝试、原wrapper目录/再次readiness保护、提交瞬间真实SIGTERM记录，以及真实启动器父进程已经退出后短子进程继续写完成文件。测试替换原readiness和wrapper为短受控程序，不运行DBS/HISDBS或真正老化。Windows4通过/8项Linux检查跳过。

真实节点默认与带环境标记的--launch均exit2/pending，四类正式目标均不存在。全部旧冻结源19/15/8/3/5/11保持，新工具独立冻结8文件。[结果](test-results-source37-detached-launch.json)、[计划](test-plan-source37-detached-launch.json)、[原字节证据](test-evidence-source37-detached-launch.json.gz)保留。无真实后台老化启动、无实际执行器回执、无时长/P10/发布接受，原52定义/18完成声明、旧失败/unknown、preview8不变。

## 后续实际顺序

当前冻结启动器/var/tmp/crg-launch1987-tools-20261116/tests/live-capacity-aged-v1/launch-aged.py。先等原两个24h全部接受，在原新七天仍运行窗口调用[单次capture-save](development-source37-capture-save.zh.md)并私下保留准确seal摘要；终态后不能补采。再完成准确previous与authority，原三段全终态通过后才允许带可信authority/摘要和明确实验标记单次--launch。默认只读查看：

```bash
python3 -B tests/live-capacity-aged-v1/launch-aged.py
```

实际后台启动后，保存启动器准确stdout/摘要及原PID/start。后续核对原wrapper/实际executor句柄与真实exit.json，再用[qualify-v2](development-source37-aged-evidence-v2.zh.md)可信authority/receipt摘要重算36原检查、两角色600秒、原维护/恢复/磁盘/清理。启动成功、exit0、1200秒均不能各自单独作为最终接受。用户high-only范围及其它所有原门槛保持，正式1.0未发布。
