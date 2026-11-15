# 正式1396长期试验：基线失败终态

2026-11-16 CST。原长期任务已失败并结束，不再是“正在运行”。未重启，也未拼接原时长。

直接失败点为协调器定期 `exclusive()` 检查中的 `kubectl get pods -A -o json --request-timeout=10s` 返回1。
原job.py只记录退出码，没有保存原命令的stdout/stderr，因此底层API错误原因未知；不能据此认定CRG限额故障。
协调器随后进入原清理路径，campaign捕获KeyboardInterrupt，两个负载中断退出。
原namespace、叶/父cgroup及登记进程清理通过；新增只读观察再次确认不存在。

## 实际完成与未完成

- 原启动12/12通过，一次备份/同步/独立恢复内容周期通过但仍为native-pending，不能计入24h验收。
- DBS/HISDBS各约15230秒（4.23小时）基线负载、254份宿主采样。已观测片段SQL/API零错误、最大延迟小于5秒，数据完整及主库未重启。
- 相对86400秒计划，SQL/API覆盖率仅约17.6%，原要求98%；原负载标记failed/interrupted，基线不能判通过。
- enforce和新七天阶段都未开始；原24h observe→24h enforce→新7天和后续老化验收标准保持。
- 原最终ELF/16项冻结输入未修改。本次处于observe，尚未应用enforce限额。

[原文件证据](test-evidence-final-v1-long1396-terminal.json.gz)包含9份准确终态文件、完整原只读记录JSONL、原plan/job/runner及逐文件摘要。
当前清理观察只公开所列字段；私有kubelet日志窗口另留，不把该窗口当原命令错误输出。
[独立复算结果](test-results-final-v1-long1396-terminal.json)可复现：

```sh
python3 tests/long1396-terminal-review.py --evidence docs/test-evidence-final-v1-long1396-terminal.json.gz
```

## 后续任务

补齐测试协调器命令失败的原输出、超时与退出记录，核对控制面当前状态，再以新身份冻结后续方案。
若调整重试，须保持原独占确认及总观察时限，不放宽业务、SLA和持续时长。
不得就地修改原job/plan、改判失败或静默重启。后续新的长期运行须从零计时，原失败和全部原件继续归档。
稳定1.0尚未接受。
