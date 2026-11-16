# 老化后单次执行包装器 v2

> 当前执行入口改为[runner-v3](development-source37-aged-runner-v3.zh.md)：旧放行信号窗口已受控复现并修复，旧runner-v2仅留历史，不再用于正式执行。

本工具补齐[v2老化执行与独立审核](development-source37-aged-evidence-v2.zh.md)之间的实际退出回执。它属于隔离实验工具，不是每容器产品Agent；产品的一对一、辅助失败不阻断业务、三项百分比/high-only策略均不变。

## 单次执行和真实身份

[包装器](../tests/live-capacity-aged-v1/runner-v2.py)按[固定契约](../tests/live-capacity-aged-v1/runner-v2-contract.json)核对原执行器全部15文件，固定入口、实验目录与原执行契约。默认调用只做原readiness；即使给--execute，原24h/同容器24h/新七天尚未接受，也只返回pending，在读seal/previous盘点和创建包装器目录前返回。实际操作必须同时提供真实authority及其可信摘要、明确实验环境标记；创建独占目录前再次原readiness。

包装器目录/var/tmp/crg-aged-source37-runner-v2-20261116只允许独占创建，保留intent.json、start.json、stdout.log、stderr.log及最终exit.json；目录0700、文件0600，独占新文件写入并fsync文件和目录。它不移除guard，不重用旧目录，不盲目重试。发现已有目录时停下核对原尝试，无论旧尝试是否退出都不自动再跑。

执行器作为真实直接子进程运行。子进程先等待管道放行；父进程必须先把实际PID、/proc start ticks和源摘要持久化，再发放行字节。身份记录失败或管道EOF时子进程不执行负载。放行后子进程再核对原执行器摘要，并exec到固定入口，保留同一PID/start。包装器实际wait获取退出码、真实monotonic耗时、完整报告和输出摘要；不伪造1200秒，不用日志推算退出，不把包装器启动等同执行成功。

首个SIGINT/SIGTERM只转发SIGTERM给仍匹配原start ticks的自有直接子进程，等待其原清理完成，不killpg、不发业务信号、不强杀、不重复信号打断清理。包装器自身崩溃/SIGKILL或放行后异常可能留下可识别运行进程，guard与错误记录保留，必须人工核对原PID/start和现场，不得自动重试。此边界不宣称掉电原子完成。

## 验证范围

[11组检查](../tests/live-capacity-aged-v1/runner-v2-checks.py)在Linux全部通过：真实临时短子进程/PID/start/退出码/报告摘要/0600，重复拒绝不改原字节，子进程源变化拒绝，身份落盘失败不放行，真实自有子进程信号，符号/硬链接拒绝，再次readiness变化不建目录，以及默认/缺标记/缺authority保护。Windows通过4组，7项依赖Linux proc/权限/实际子进程的检查跳过。受控测试临时目录与短程序明确替代正式固定入口，实际耗时小于1200，不能作为真实老化回执。

真实节点默认调用exit2/pending，带--execute及环境标记仍exit2/pending；未创建正式runner/input/postflight目录。原19长测输入、原v2执行器15文件和capture8文件逐字不变。[结果](test-results-source37-aged-runner-v2.json)、[冻结3文件](test-plan-source37-aged-runner-v2.json)、[准确字节证据](test-evidence-source37-aged-runner-v2.json.gz)全部保留。

## 后续真实执行

当前工具为前台supervisor，不负责脱离SSH。真实长测终态、[真实七天窗口采集](development-source37-capture-v3.zh.md)、原独立审计、准确high-compatible previous和authority均完整后，仍需单独审核一次性启动器：将这个准确包装器以setsid/DEVNULL启动并记录其PID/start，启动结果不确定时只能核对原尝试，不能重新spawn。禁止通过55秒短SSH执行包装器后把连接超时当作任务退出。

当前冻结入口/var/tmp/crg-runner1965-tools-20261116/tests/live-capacity-aged-v1/runner-v2.py，摘要见计划。无执行条件时可只读运行：

```bash
python3 -B tests/live-capacity-aged-v1/runner-v2.py
```

未来实际exit.json必须交给原qualify-v2，附真实authority/receipt各自可信摘要；审核仍重算原36检查、每角色600秒原门槛、维护/恢复/日志/目录/清理证据。exit0或1200秒单独不等于通过；包装器始终qualification_accepted/P10_complete/release_accepted为false。没有真实postflight、真实exit.json、七天时长或稳定发布资格。用户已确定仅支持high回退、旧max应拒绝并保留记录，其余原门槛不豁免。
