# PostgreSQL 实际路径等待诊断资格

本阶段实现独立的[PG等待采集库](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-pg-wait.py)，属于隔离测试诊断代码。生产每容器一份Agent及preview.2安装包不变。它与前阶段[设备会话和并行采集适配](testing-device-sessions.md)均尚未被原32项完整压力执行器调用；完整两角色业务复测、全部原时限和历史失败继续保留。

[结构结果](test-results-pg-wait.json)和[原始证据包](test-evidence/pgwait314-qualification.json.gz)记录本次资格。证据含节点协调报告的逐字节原文、其SHA256、六份固定源码、独立清理复查；容器内资格报告是协调器收取并解析后的结构，不能声称保留了容器原文件的逐字节内容或摘要。

## 实际检查

| 环境 | 检查 | 结果 |
|---|---|---|
| Linux宿主Python3.9.21 | 选择器、过滤、边界、缺失和只读基础调用 | 32项通过 |
| DBS原镜像Python2.7.5 | 同一份检查源码 | 32项通过 |
| HISDBS原镜像Python2.7.5 | 同一份检查源码 | 32项通过 |
| DBS原镜像及PG二进制，新建空库 | 实际路径和后端身份、等待、故障恢复、成本 | 14项通过 |
| HISDBS原镜像及PG二进制，新建空库 | 同上 | 14项通过 |

共124项通过，资格执行器exit0。两个容器均UID999/GID998、只读根文件系统、drop ALL、无服务账号令牌、拒绝网络进出；PG bin/lib/share以只读方式挂载，原数据库、配置及产品目录没有挂载。每个空库使用新的512MiB emptyDir，其PGDATA保持厂商实际路径`/opt/postgresql/pgdata`，PG可执行文件保持`/opt/postgresql/pgsql/bin/postgres`。初始化与标准pg_ctl启停只作用于本次空库；不能据此声称整套资格没有启停信号。等待采集库本身不发信号、不写控制项。节点内存预留、Pod截止时间和自有目录均受限制。

实际检查使用一条本轮标记后端、另一轮标记后端和另一个数据库的后端，验证SQL只读、1秒statement_timeout、确切数据库/本轮标记过滤和PID/backend_start复查。正常空闲和真实3秒PgSleep均保持后端身份，原查询完成、没有取消；原PGDATA下实际打开的关系文件通过白名单。资格器为验证白名单枚举过该测试后端的至多256个FD链接并只保留至多8条允许路径；采集库只读取当前系统调用所选FD链接，不枚举FD、不读FD内容。

故障检查包括注入缓存start_ticks错误、两个SELECT之间真实改变应用标记，以及实际创建5个同标记后端。它们均拒绝元数据或返回明确unknown，随后恢复到同一原后端。缓存注入不等于实际制造PID复用；解析器替身也不冒称真实进程换代。5条SQL结果用于识别超过4目标的边界，不能静默截断成完整观察。

三个预先规定的连续采样中，DBS最大墙钟约2.643ms、观察线程CPU约1.252ms；HISDBS最大墙钟约2.765ms、线程CPU约1.234ms，均低于每次250ms/100ms的资格门槛。线程CPU来自CLOCK_THREAD_CPUTIME_ID，不把未来业务线程CPU算成观察器开销。Python资格进程RSS低于128MiB。仅三个采样的短测，不证明900秒或完整600秒业务开销。

## 选择、身份与隐私边界

本轮应用名为`crg-disposable-soak-<run_id>`，只接受8至14位数字轮次；SQL仅选择postgres数据库中的该标记，排除观察器自己。返回datname/application_name/PID/backend_start/state/wait_event_type/wait_event，不读取SQL正文。backend_start保留精确十进制文本，作为PG身份字段；它不是/proc start_ticks，不进行两者互换或时间差猜测。

采集库复用已资格的有界只读reader并核对源码摘要。它在两次只读SELECT之间读取选定后端，再复查PID/backend_start及/proc身份；核对boot、PID/start_ticks、非Z/X、同一cgroup、同UID、exe路径及inode、PGDATA路径及inode和cwd。每次最多4个后端、每目标1900字节、总记录8KiB；上限或采集异常保留unknown。跨多次读取不是原子快照，身份复查不提供请求IO因果证明。

仅识别已明确的Linux x86_64 IO系统调用类别及其逻辑FD号；其他ABI或系统调用保留unknown。返回值不含原始寄存器、地址、偏移或其他调用参数。FD路径仅允许实际PGDATA、pg_log及本轮basebackup子目录；旧`/opt/postgresql/data`和其他路径被隐去。栈至多读取4KiB、保留8个符号，不保留地址或偏移，不使用ptrace。

**两镜像的实际内核栈均读取失败并记录OSError/available=false，不能声称已经采到PG内核栈，也不能在未记录errno时断言失败原因。** 实际空闲/PgSleep样本的系统调用编号为232，当前白名单将其操作标为unknown，不能冒称采到了IO FD或写回栈。缺失是允许的诊断结果，不提升权限来强行采集。

独立SSH复查确认资格父进程原PID/start_ticks、两个容器原进程、Pod、cgroup和namespace均已退出，原只读二进制与share文件摘要仍相同。该检查不修改七天测试、原API观察器或历史等待报告。

下一步冻结新的诊断worker/接入版本：旧worker使用无轮次后缀的应用名，不能直接声称本库已覆盖它。新版本需使用本轮唯一标记，接入已资格设备会话及PG等待字段，实际验证缺失/故障放行后运行原32项、DBS/HISDBS各600秒、64MiB与11区间的完整复测。原配额、SQL/API零错误及延迟门槛保持；短资格不关闭历史业务失败、P10或稳定1.0。七天、正式24h及后置、ARM厂商业务和独立物理多盘仍按原计划，未测项保持未测。
