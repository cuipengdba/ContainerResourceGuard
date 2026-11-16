# 老化单次执行包装器 v3：放行信号保护

复核[v2包装器](development-source37-aged-runner-v2.zh.md)发现一个保护缺口：父进程已flush放行字节，但released标志尚未设为true时收到SIGTERM，旧handler只记录信号，没有转发给子进程。受控真实Linux回归在该准确位置发送SIGTERM，明确复现旧子进程继续运行并exit0；此前11组通过并未覆盖此窗口。这是实验包装器缺陷，尚未发生正式老化执行，产品Agent及原长测不受影响。

[新v3入口](../tests/live-capacity-aged-v1/runner-v3.py)在放行字节/flush/released状态提交段暂时屏蔽SIGINT/SIGTERM，finally恢复原signal mask，届时pending信号看到准确released状态，按原身份规则转发给自有直接子进程。真实同位置回归验证子进程实际exit -SIGTERM。原v2冻结文件不修改、不重跑正式测试，改用独立目录的新v3。无强杀、killpg、无业务信号，无自动重试或删除guard。

[v3契约](../tests/live-capacity-aged-v1/runner-v3-contract.json)继续绑定原executor15文件、准确固定入口及同一runner-v2实际回执路径，兼容原qualify-v2的真实退出审计；额外固定旧wrapper摘要和signal策略。[13组检查](../tests/live-capacity-aged-v1/runner-v3-checks.py)包含旧11组和真实旧问题复现/新保护两组。Linux13全部通过，Windows4通过/9项依赖Linux的检查跳过。受控短子进程的真实耗时小于1200，不能当作实际老化回执或发布证明。

真实节点默认调用与--execute加环境标记都exit2/pending；原两段24h及新七天尚未完成，没有创建正式runner/input/postflight目录，原long19、executor15、capture8保持。原文件/进程/PID1/业务/资源/产品源码与现有preview均不改。[结果](test-results-source37-aged-runner-v3.json)、[冻结5文件](test-plan-source37-aged-runner-v3.json)、[准确字节证据](test-evidence-source37-aged-runner-v3.json.gz)保留实际边界及旧缺陷记录。

v3仍是前台supervisor，其余单次独占、0700/0600、先持久化真实PID/start再放行、子进程执行前复核源码、实际wait退出/报告与输出摘要、首信号向准确子进程转发并等待原清理、出错保留现场规则沿用v2。**旧runner-v2不再是正式执行入口。** 正式脱离SSH的单次启动器仍待单独审核，必须源固定、setsid/DEVNULL且记录真实wrapper PID/start；不能在55秒短SSH运行后把超时当退出，不能在spawn结果不确定时再启动。

当前冻结入口/var/tmp/crg-runner1971-tools-20261116/tests/live-capacity-aged-v1/runner-v3.py。只读查看条件：

```bash
python3 -B tests/live-capacity-aged-v1/runner-v3.py
```

实际执行仍需原三段时长和审计通过、在真实七天窗口通过[capture-v3](development-source37-capture-v3.zh.md)采集的seal、准确high-compatible previous和authority、明确实验标记和可信authority摘要。实际exit.json再交[原独立qualify-v2](development-source37-aged-evidence-v2.zh.md)审36项原证据/两角色600秒/磁盘与清理，exit0与1200秒各自都不能单独通过。包装器始终不宣布P10或release完成，原52任务定义/18完成声明保留。用户high-only回退与旧max拒绝范围不变，稳定1.0仍未发布。
