# 完整压力接入设备与唯一轮次 PG 等待诊断

原 32 项完整压力执行器已经接入已资格的设备会话与新版 PG 等待 worker，并在隔离节点实际完成一轮。**终态失败：DBS实际600.412秒，SQL0错、API3次超时；HISDBS按原失败流程未执行。** [终态与独立清理](test-results-business-pressure-device-pgwait.json)、[逐窗口复核](test-analysis-business-pressure-device-pgwait.json)。[开始快照](test-start-business-pressure-device-pgwait.json)只证明启动时的局部进展，不是业务通过或稳定版发布证据。

## 固定协议和变化

[新执行器](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-business-memory-pressure-device-pgwait.py)另建文件，保留原 R235 执行器、计划及失败原件。旧诊断 contract 仍指向原资格报告；新 worker 和设备各有独立摘要 contract，避免把旧报告冒认为新源码资格。源码和计划 SHA256 见开始快照及其压缩原始证据。

原业务方法 AST 在剔除明确声明的三个诊断依赖复制、新 worker 绑定及 PG 只读授权后与旧方法完全一致。保留原 32 项、两个角色各 600 秒、64MiB 载荷、11 个重载区间、内存 30→20 的真实高用量延后与同代次重试、SQL/API 原请求周期、4/5 秒截止、错误 0、覆盖率和延迟门槛。原配额 A 为 CPU30/内存30/IO100，B 为 CPU25/内存29/IO80；IO100仍是原标定上限，并非不限速。

新版 worker 使用本轮唯一 application_name；只向诊断子进程传入已资格的 PG 只读标记，复制固定摘要 helper 到当前隔离容器。原请求和 PG 锁采集保留，新等待快照按实际 PGDATA 及 PG/proc 身份复查。PG 样本与等待、线程和设备读取各有独立时间区间，不能当作原子快照或 IO 因果证明；不可读的可选字段仍为 unknown。

设备会话包装原线程会话，在同一引擎和压力前启动；启动或保存失败仍放行原业务，最终诊断失败保持可见，原业务异常保持优先。只用 pidfd 清理本轮观察器，不向业务目标发信号，不写控制项。按实际 dm-0→sda2→sda 三层分别记录，不相加、不计为三块独立物理盘。正常业务结束后可对自己的 900 秒观察器发 TERM 形成部分报告，这不宣称观察满900秒；仍要求实际引擎/重载区间包络及不超过3秒的采样间隔。

## 实际启动

18 项实际前置通过：默认只读、缺少执行标记拒绝，以及改动 namespace、原标准、历史/新诊断 contract 等拒绝；全部之后目标目录和 namespace 仍不存在。两角色缓存镜像、原离线配置与精确 ELF 摘要也核对后，另建唯一 R342 namespace 和运行器。

开始快照 DBS 13 项局部检查、11 个重载区间；原运行器/worker 和两个观察器均按 PID、启动 ticks、入口核对为同一实例。此时原生600秒尚未结束，HISDBS尚未执行，不根据正在运行报告中的初始零值判断业务零错误。首次私有状态读取脚本误取报告中不存在的 folder 字段，已改为固定计划来源，原执行器未重启。

## 后续判定

继续等待原句柄自然终态；失败时保留原错误、全部请求/线程/PG/设备报告，独立核对原进程退出、namespace/cgroup清理及原配置/缺省profile恢复。采集链资格、局部检查或某次未复现都不关闭 R235/R203 等历史失败。所有52项原任务、真实七天原句柄及后置、正式24h对照、ARM厂商业务、独立物理多设备等原稳定条件继续，产品及preview.2下载程序没有变化。

## 实际终态和逐窗口观察

原运行器自然结束、exit1，原因 NATIVE_COMPLETION_EXIT。DBS 13项局部、11个重载区间及10项引擎内容通过，但不能抵消原生API3次约4.004秒的socket超时；SQL301请求0错，API121请求3错。原600秒真实运行结束，未向业务native发送TERM，未以部分报告充当600秒；HISDBS未执行。

完整原生诊断有422请求及601个PG/PG等待样本，诊断完整、0丢弃/0采集错，原内部线程CPU合计1.576秒。线程598样本、设备599样本，分别覆盖全部引擎/重载包络，最大采样间隔约1.003秒；各900秒观察器由自己的pidfd TERM结束为部分报告，未使用KILL，不宣称观察满900秒。设备观察器完整子进程CPU1.659秒、线程3.417秒，各记录自身wait4数据，不把它们算进原native内部线程统计。

共22个D线程观测，均为同一TID/启动ticks，捕获write/FD3/DBS.log及XFS buffered-write/folio等待。3个API错误各有4个严格请求内D观测，均在最后重载之后。其独立设备括区间和PG快照已逐项保留。同期选中的本轮native SQL客户端共12个快照均idle/ClientRead，不能据此判断其他API数据库后端；PG内核栈601次均不可用并保留unknown。

错误窗口的dm-0本容器wios约0～64/s，端点是原135wiops配置；dm-0端点in_flight在9～125之间。这些是不同层和时间区间的观测，既不能证明没有限流，也不能把全设备队列归因于本容器。三层分别保存，未相加、不把1秒速率峰值当限额违例；没有完成IO因果判定，不修改原配额或SLA。

节点独立复核5个已记录原实例全部消失、namespace及Pod cgroup不存在，两个原输入目录的配置字节/精确ELF和缺省profile状态恢复。46份原始文本文件逐字节保存、SHA256核对；离线分析从原目录和压缩原件运行结果一致，改动原报告却保留旧摘要的负例明确拒绝。

复现：从源码仓库运行下列命令，只读本地归档，不连接节点：

```bash
python3 tests/analyze-pressure-device-pg.py --evidence docs/test-evidence/pressure342-terminal.json.gz --output /tmp/pressure342-review-new.json
```

本轮仍未满足原32项/两角色各600秒，旧失败和全部52任务不关闭。后续先根据日志写入等待、设备及原限额的联合证据设计有明确对照的诊断；不重复无变化的完整测试或提高配额冒充解决。七天原句柄、正式24h及后置、ARM厂商业务和独立物理设备等原稳定要求继续，preview.2安装包不变。
