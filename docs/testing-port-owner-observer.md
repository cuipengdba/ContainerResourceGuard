# 临时备库端口只读归属采集

[端口诊断已接入engine/campaign](testing-port-diagnostic-integration.md)：28项结构/故障、两原镜像Pod共14项真机及13项独立复核通过。启动前/后、启动失败、stop失败和cleanup后采集；普通诊断失败放行，执行器停止请求继续传递。尚无新执行器的真实PG冲突/完整业务或长期计时通过；默认20%业务失败与原52项保持。以下保留此前时点记录。


长期执行器以前曾在临时端口55432被占用时失败，未取到占用者；旧七天任务约30小时的失败和旧结论保留。本工具为下一轮增加诊断能力，不修改产品或业务配额，不替代长期验收。

`tests/port-owner-observer.py`按调用方事先授权的目标PID/start_ticks、网络命名空间inode及完整cgroup成员身份先后核对，读取目标`/proc/PID/net/tcp`、tcp6、unix，按指定端口筛选监听socket inode，再在相同网络命名空间的FD中查找所属PID/start。返回comm、观测cwd、fd及是否同一cgroup；同网络命名空间的其他cgroup拥有者也可记录，适用于Pod共享网络。cwd仅为该时点观测，不断言一定是PGDATA。

不读命令行或环境、不发送信号、不修改资源或网络、不停止任何监听者。默认2秒、32768进程、65536个FD、256监听、每表1MiB上界；权限错误、读取缺失、进程/FD变化或达到边界明确partial/unknown。它是区间快照，无法原子保留端口，即使没有匹配监听也不宣布端口可用。现阶段API调用方仍须先验证隔离Pod归属，本模块不自行授权目标。

## 原生资格

现有amd64/Linux5.14节点27项检查通过。测试仅创建本轮子进程，绑定系统分配的空闲回环端口和本轮临时PG风格Unix socket，实际取得TCP4/TCP6/Unix三种监听及同一拥有者。检查错误start/netns/cgroup拒绝、非法参数和零边界、表/监听/进程/FD上界、受控身份变化注入、目标退出、子进程和Unix文件清理。仅本轮子进程收到管道EOF退出，没有kill其他进程或绑定业务固定端口。

原始正常快照实际耗时0.20100676687434316秒，扫描1156进程/9430FD；三类监听及正确拥有者取得，但其他进程扫描中消失，所以整体phase为partial。此原件保持partial，不以27项资格通过声称快照完整。身份变化测试为受控故障注入，不声称真实触发PID复用。

运行资格：`python3 tests/port-owner-observer-checks.py tests/port-owner-observer.py`，需要Linux /proc读取权限。Windows只做语法解析，未计Linux原生通过。

[原生结果](test-results-port-owner-observer.json)、[准确原始回执gzip](test-evidence-port-owner-observer.json.gz)、[只读模块](../tests/port-owner-observer.py)、[资格入口](../tests/port-owner-observer-checks.py)。

## 后续接入约束

尚未接入engine/campaign或启动新长期测试。下一执行器应在本轮临时实例启动前、pg_ctl启动失败后、stop/cleanup之后采集55432/55433，并将partial/unknown保留到原报告；诊断失败不覆盖原始业务异常，不得据占用结果终止未确认属于本轮的进程。保持原300/60/30秒等业务时限、零错误/延迟/覆盖SLA、配额及数据量；精确冻结新增源码和计划后重新资格，不借用旧约30小时为新七天计时。

本轮默认百分比控制层48/48结果保持；默认20%完整业务失败、原52项、24h+24h/七天和硬件范围仍待，稳定1.0未接受。
