# 日志写与API连接关联：perf管道资格尚未通过

[第五轮真实high压力](test-results-memory-high-pressure-v5.json)中，两角色各600秒、SQL零错误/API各一次超时；错误均早于压力准备及high下调，DBS窗口内有6个原日志缓冲写等待样本。原IOPS单变量对照曾出现预定总错误关联，Agent活动四臂对照没有出现预定关联；这些结果仍不足以把具体HTTP请求归给同一日志写线程，不能直接改配额或数据库行为来宣称修复。

本次只读确认节点有perf/tracepoints、libbpf和BTF；两原厂商ELF均为30814840字节、摘要bd21a02c74b4e416439d72f1cc5039280bea6399f67e2923dff6a743c189fdcb、没有调试符号。节点没有clang/BPF编译后端和bcc模块。未安装系统包、加载BPF程序或修改tracefs/cgroup/业务。

新[实验模块](../tests/vendor-perf-metadata.py)尝试用标准perf record到perf script的内存管道，仅保留PID/TID、单调时间、FD/字节数/返回值和白名单FD元数据；不保存原始perf文件、指针、目标内存或请求/日志内容。明确实验标记、同一v2 cgroup及PID/start_ticks/ELF核对在前；每次FD读取前后再核对身份和exe inode。它不是产品功能，不应接入业务环境。

[四轮全部失败和精确源码](test-results-perf-metadata-unqualified.json)已归档，不合并不同轮次的通过项：首轮握手拒绝且SSH观察超时，随后只读确认同入口已无运行实例，才修订而非因超时重启；该轮没有完整stream终态，不能回填确切ACK。第二轮观察到5字节ACK，修订接收C字符串末尾NUL；原采集器按自己的pidfd SIGINT收尾，真实退出为-2，不能伪称退出0，目标仍活着。第三轮修正这个采集器退出期望并通过自身控制FD ping唤醒稀疏流，仍未取得连接FD。第四轮关闭perf script排序队列、事后只排序筛选后的整数事件并记录实际解码时间，仍失败。

第四轮记录8/预定9项，其中7项通过，第8项“同线程/精确回环连接包围阻塞写”失败，第9项未执行。自身HTTP请求实际完成、真实EAGAIN(-11)和约0.5秒管道阻塞写可配对，但事件解码晚于短连接关闭、FD全部unknown。失败收尾向自身探针stdin发EOF导致退出1，不是正常通过；未强杀，三个修订轮的runner/checker/perf record/perf script/探针原实例都经独立观察消失。没有业务数据库、业务信号或控制写入。

该管道目前只证明所选系统调用的时间记录机制，不能用于认定请求到日志写的因果，也不接入正式32项业务重跑。下一步选择不依赖延后文本解码的、只输出所需字段的直接BPF观察；优先在独立工具工程用现有本地Go交叉构建，避免改动节点系统工具或产品依赖。需先验证当前节点真实加载/绑定/关联、丢事件及退出行为，能力不足保持unknown；不以工具资格关闭原业务失败、52项或稳定门槛。

接口依据：[perf record](https://github.com/torvalds/linux/blob/v5.14/tools/perf/Documentation/perf-record.txt)、[perf script](https://github.com/torvalds/linux/blob/v5.14/tools/perf/Documentation/perf-script.txt)、[控制ACK实现](https://github.com/torvalds/linux/blob/v5.14/tools/perf/util/evlist.c)、[事件排序与输出实现](https://github.com/torvalds/linux/blob/v5.14/tools/perf/builtin-script.c)。以上仅帮助解释工具合同，实际节点失败以原件为准。
