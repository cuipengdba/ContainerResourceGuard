# 原生请求及 PostgreSQL 等待诊断

这组测试工具补充 R167 两次 SQL 错误缺少逐请求信息的盲区，供下一轮原完整压力协议使用。产品仍只控制 CPU、内存、IO 三项，独立百分比各默认 20%，保留手动兼容、纯 cgroup v2 判断、每日日志与 30 天/1GB 清理。诊断没有接入业务启动链，不管理其他容器；原已发布 preview.2 二进制不变。

## 采集契约

`tests/vendor-soak-load-diagnostics.py` 是原 `vendor-soak-load.py` 的独立测试分支。原文件 SHA256 为 `ba87ef2d646b723eb8419de25ffcd736f7a5b0925716f4b638761dff70bb2461`，没有改写或替换在线七天任务。原 11 个函数/类经 AST 对比，仅在 SQL/API 循环添加观察调用，连接、查询、异常后原重试行为、两秒/五秒周期、四秒 HTTP 超时、五秒 SQL/请求门槛及完整性判定保持。

新入口同时要求原隔离 marker 和 `CRG_VENDOR_NATIVE_DIAGNOSTICS=qualified-disposable-loopback-only`，只允许新 schema 的 smoke 阶段，实际时长最多 900 秒。启动前核对同目录 helper 固定 SHA256，禁止复用长期输出。它不是产品配置参数。

`vendor-native-diagnostics.py` 在内存中记录每次合成 SQL/API 的顺序、iteration、原始键区间起点、起止单调/实时时间、处理阶段、成功标志、五秒门槛与固定错误类别。SQL 连接成功后记录 libpq 返回的后端 PID。异常任意消息、凭据、SQL 原文、响应正文不落盘；错误类别无法识别时明确写 unclassified。

另一个线程使用独立只读连接，设置 `default_transaction_read_only=on` 和 `statement_timeout=1000`，客户端查询期限一秒，每秒读取本测试 `application_name` 的 PG 活动。最多取 17 行以识别超过 16 行的截断，只返回 PID、backend_start、state、wait_event_type/event、query/xact 起点、合成语句类别及锁阻塞者。仅在 wait_event_type 为 Lock 时调用 pg_blocking_pids；空阻塞列表、未测量、缺身份和无样本分别表达，不把未知当零。

PID 必须结合 PG backend_start 和请求连接观察时间使用。等待状态来自独立时间点，客户端超时与某次等待的关联须由时间窗口及相同会话证明，不能仅凭一个 PID 或历史慢日志判定根因。pg_blocking_pids 的零 PID 可以代表预备事务，不是信号目标；它还会短暂访问锁管理共享状态，因此采集成本仍须观察。[PG 活动字段定义](https://www.postgresql.org/docs/14/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW)、[libpq 后端 PID](https://www.postgresql.org/docs/14/libpq-status.html)、[阻塞者语义及开销](https://www.postgresql.org/docs/14/functions-info.html)。

每轮最多 1024 个请求、901 个 PG 样本，每样本最多 16 行，事件 2KiB、样本 16KiB、最终文件 8MiB。溢出、PG 错误、内部错误或线程未退出都会使诊断完整性不通过；它们不取消、重试、延长或修改原业务请求。最终只创建一次 0600 `native-diagnostics.json`，拒绝已有文件和符号链接。摘要、文件 SHA256、文件大小和末尾线程 CPU 计量写入原负载报告的独立字段，原业务 phase 仍由原标准决定。

## 资格验证及保留失败

完整结果及每轮源码/报告摘要见 [资格记录](test-results-native-request-pg-diagnostics.json)。实际顺序与最初失败均保留：

1. R185 在 Linux/Python3.9.21 上 23 项隔离检查通过；厂商镜像未挂运行时库，加载 libpq 失败，镜像检查未执行。
2. R188 将 bin/lib/share 组件只读挂载，root 丢弃全部 capabilities 后遇到目录访问拒绝，尚未进入 PG 测试。只读核对确认组件目录 0700、属主 999:998、SELinux disabled；未修改源权限。
3. R191 使用镜像实际 postgres 用户 999:998，DBS 的 23 项及 3 项入口保护通过；临时 PG 资格脚本在 Python2 中因函数内 exec 与生成器语法限制失败，未进入该脚本的初始化/测试。旧脚本和失败执行器逐字节归档。
4. R194 将资格脚本内该处改为执行 exec-mode code object 的 eval，并在开始 PG 测试前用镜像 Python2 编译。最终结果以资格记录的真实终态为准，不用源码检查代替执行结果。

`vendor-native-diagnostics-checks.py` 的 23 项覆盖错误白名单、身份/缺失值/阻塞者 0、行数和字段限制、时间/原键关联、记录异常隔离、容量限制、真实线程停止、文件模式/摘要/重入/符号链接及 CPU 时钟缺失。入口保护另查缺 marker、超过 900 秒和 helper 篡改，均须在创建负载目录前拒绝。

`vendor-native-diagnostics-runtime.py` 只在新的非 root、只读根文件系统、drop ALL capabilities 的隔离 pod 中运行。只读挂载厂商 PG bin/lib/share，PGDATA 和输出均是新的 emptyDir，不挂原数据、配置、备份、日志或 CRG 状态；deny-all 网络策略下 SQL/模拟 HTTP 只监听 loopback。每个镜像新建一次 PG：正常运行 12 秒，再对另一新合成 schema 制造八秒 ACCESS EXCLUSIVE 表锁并运行 16 秒。后者应保留原 SQL 超时失败，同时取得同一客户端后端的实际 Lock 等待和正确阻塞者，不能改成业务通过。

每角色的 16 项实际 PG 检查包含只读会话设置、正常原生门禁、故障保留、逐错误 PID/阶段/时间、实际等待关联、原校验和/PG 实例/线程停止、请求计数一致及内部线程计量 CPU 不超过一个核时长的 5%。该内部计量不包含所有调用边界和进程启动成本，短时资格不证明完整 600 秒没有观察影响。模拟 HTTP 仅验证采集链路，不等同 DBS/HISDBS 原业务接口验收。

测试按记录的 namespace UID 清理，只停止自己新建的 PG/子进程，不向原业务发信号。原 R167/R142/R120 等失败、完整 32 项、两角色各 600 秒、零错误/五秒/p95/覆盖率、全部配额和压力区间不变。下一轮必须先固定本资格的终态和工具摘要，再接入原完整压力协议；真实七天、正式对照、老化后置和其他原稳定发布条件仍独立验收。
