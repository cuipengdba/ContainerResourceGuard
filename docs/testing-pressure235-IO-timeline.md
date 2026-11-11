# R235 逐秒 IO 与请求窗口核对

[复现脚本](https://github.com/cuipengdba/ContainerResourceGuard/blob/dbe5ecee372c28eed59118aee30339471dfbc7f2/tests/vendor-pressure-io-timeline.py)只读已公开的原始线程、请求/PG和失败报告，不连接节点、发信号或写控制文件。运行 `python3 tests/vendor-pressure-io-timeline.py --output /tmp/crg-io-analysis.json`，结果用O_EXCL/0600写入新文件。[结构摘要](test-analysis-pressure235-IO-timeline.json)及[完整599区间结果](test-evidence/pressure235-IO-timeline.json.gz)固定源码/输入/输出摘要。它验证600个线程样本、419个请求、601个PG样本；单调时钟差为速率分母，时钟跳变、输入过大、错误来源或未记录控制值会拒绝。

6次原生请求错误均不与11个配置切换区间重叠。相对最后一次切换完成，SQL69开始晚22.486秒；API83/86/90/93/111分别晚46.483/51.483/56.484/61.484/86.484秒。相关采样读回CPU720000/100000、memory.max20001980416、253:0的读64700080/写37470104 B/s及读83/写135 IOPS，与记录配置一致。此结果排除了“错误窗口采到另一配额”这一解释，但不证明其他瞬间没有变化或限流本身无影响。

覆盖SQL请求的完整计数区间合计约6秒，253:0写计数差速率约37.342 MB/s；五个API窗口的完整区间各约5秒，依次约38.122、37.544、28.152、40.592、19.321 MB/s。这是邻接采样的计数差，不是精确请求时段的物理完成带宽。IO窗口需要首尾两个样本，因此D_bracketing_sample_count会各包含5个D样本；严格落在每个API请求开始/结束内的D_samples_within_request_count均为4，与旧报告一致。两种范围不可混用，也不能据此确认日志锁或API线程职责。

按[Linux官方cgroup v2说明](https://docs.kernel.org/admin-guide/cgroup-v2.html)，IO限制允许短时突发，缓冲写回具有异步及内存/IO共同参与的语义。因此单秒计数速率超过io.max不直接证明限额失效；整段平均偏低也不能排除短窗口限制。253:0与8:0分别保留，不相加当作两盘。旧SQL的LWLock/WALWrite、DBS.log写入等待、旧失败及原稳定条件均保持。

这一结果使后续优先核对写BPS这一单一变量，见[冻结A/B/A诊断](testing-write-bps-comparison.md)。它不自行修改标定profile、业务日志、内核参数、IOPS、配额或验收时限。
