# 测试说明

## 自动检查

```bash
go test -race -cover ./...
go vet ./...
bash tests/supervisor.sh
python3 tests/integration-patch.py
```

单元测试覆盖配置、cgroup namespace 路径解析、目标越界拒绝、百分比与既有限额、IO 取整、写入前持久化、幂等、只读/权限失败、内存下调保护、外部冲突、pending 恢复和正常恢复。

RC2 增加不同 state_dir 下的目录 inode 锁、损坏/重复键日志、写意图期间外部变更、内存增长/PSI/events/慢落盘、低频状态预算和设备身份重识别。Linux 上对 apply/restore 的 8 个位置各强杀一个真实测试子进程，共 16 个中断检查点；控制值使用临时普通文件建模，不能把它说成每个真实 cgroup 系统调用都做了强杀。

`supervisor.sh` 启动真实模拟业务进程和异常辅助进程，检查业务启动/完成标记、原退出码 37 与有界退出时间。模拟返回错误不等价于所有业务集成已经验收。

`integration-patch.py` 还检查候选补丁保留原件、拒绝未知结构，并对生成的 supervisor 验证业务、缓存和资源辅助进程独立运行。Python 需要 3.9+；这些 shell/进程测试在 Linux 上执行。

## 真实 cgroup 验证方法

只在专用临时 namespace、容器和测试目录执行。测试节点应已有 Linux cgroup v2 与可用容器运行时，不要以真实业务容器承担故障演练。

1. 将 Linux 静态 CRG 和 `tests/load` 构建物、示例 supervisor 放入只读工具挂载；提供独立可写测试数据目录和临时状态目录。
2. 显式对测试数据设备标定，并只给临时容器分发 profile。先 observe 检查容量与 cgroup 目标。
3. 两个临时容器分别使用 20%、30%，先只启用第一个，确认第二个的控制文件未变，再启用第二个。
4. 读回各自 `cpu.max`、`memory.max`、`io.max`，与换算结果比较，检查目标不同。
5. 在容器内部运行 `crg-load --mode cpu --seconds 4 --workers 12`，比较该组 `cpu.stat` 前后增量与壁钟时间。
6. 运行 `crg-load --mode read/write --seconds 5 --directory /crgdata`，核对速率。该负载只新建临时文件，不允许指向既有业务文件。
   RC2 增加 `--mode randread` / `--mode randwrite` 的 4KiB 同步 direct IO，输出 `iops` 与四维限额比较。
7. 在只读 cgroup 容器启用 enforce，确认逐项 skipped 且业务主进程仍存活。
8. 在临时组内模拟外部修改，确认 CRG 不覆盖，停用恢复时也保留外部值。
9. 对正常持有的配置执行 restore，确认回到原值；删除/重建测试 Pod，确认 ID 和路径变化后自动重新应用。
10. 另建带运行时内存保护的临时容器，先确认其实际内存上限足够小，再用有界 memory 负载验证 cgroup OOM 计数，不对节点实施内存压力。
11. 测试后删除本次创建的临时容器/namespace，保留去标识报告。

RC2 另外检查不同状态目录拒绝第二个写入者、静态限额下状态/journal 修改时间不变、disable 后辅助重试不重新施加、enable、外部冲突单 JSON 返回和路径覆盖。

## 隔离 PostgreSQL 引擎验证

在独立测试容器提供明确的 PostgreSQL 二进制目录及一个**尚不存在**的工作路径，以 postgres 等非 root 用户执行：

```bash
PG_BINDIR=/path/to/pgsql/bin CRG_PG_WORK=/disposable/new-run \
  bash tests/postgres-smoke.sh
```

脚本创建本地 Unix socket 访问的全新主库、流复制库和恢复库，检查 20,000 行 SQL、pg_dump/pg_restore 摘要一致、追加一行后的流复制追平；退出时停止这三个测试实例，保留证据文件。只适用于新建隔离目录，不连接既有数据库，不调用厂商 start.sh。镜像内的依赖库须由测试环境提供。

通过此项代表 PostgreSQL 引擎场景通过，不代表 DBS/HISDBS API、业务同步、原缓存 Agent 共存或长期性能门槛已经完成。

原厂镜像主库的隔离入口为 `vendor-engine-smoke.py`；它会向专用克隆主库写入全新测试 schema、执行备份/流复制/独立恢复并探测 POST /test，不能用于现有业务命名空间。前提、参数和本次实际执行边界见 [原镜像备份短测](../docs/testing-vendor-backup.md)。

真实测量值及未覆盖范围见 [测试报告](../docs/testing.md)。源码中的测试负载不是产品命令，不包含跨容器资源管理功能。


持续测试报告另有[只读核验器](../docs/soak-report-audit.md)。运行 `python3 tests/soak-report-audit-checks.py` 验证合成报告正反例；不需要root、容器或Linux，不会启动业务。实际报告的pending与通过分开，不能将核验工具通过等同24h/七天已完成。


七天实际老化数据后置另有[身份采集和只读门禁](../docs/testing-aged-postflight-preflight.md)。`python3 tests/vendor-aged-preflight-checks.py`只使用合成报告和临时普通文件；Linux执行全部POSIX检查，Windows明确跳过相关方法。真实七天及后置操作未因此通过。


老化数据恢复/重建/维护另有[显式后置执行器与独立短数据演练](../docs/testing-aged-postflight-execution.md)。`python3 -B tests/vendor-aged-postflight-checks.py`仅检查合成/临时文件；正式604800秒及实际老化后置不因此通过。


实际保留数据辅助故障执行器及两套分离计划见[门禁、挂载范围和验收状态](../docs/testing-aged-faults.md)；合成自检命令`python3 tests/vendor-aged-faults-checks.py`。默认只读；Linux自检通过不代表七天或真实故障矩阵通过。


Versioned seven-day lineage: `python3 tests/vendor-versioned-aged-preflight-checks.py` checks the separate exact-R78 adapter. Run all eight methods on Linux; Windows skips the POSIX absolute-path case. It reuses the hash-pinned original read-only reader/auditor and never changes the original R57 plan/seal. Tests use synthetic data; actual capture/readiness is separately recorded.


Versioned postflight execution: `python3 tests/vendor-versioned-aged-postflight-checks.py` runs ten contract cases, including preserved runtime method ASTs, original native thresholds, immutable R78/R64 bindings, pending execution refusal, fresh-gate/marker protection, constrained mount consumers and UID cleanup. Windows skips the POSIX containment case; Linux must run all ten. Actual seven-day postflight and the independent short retained-data exercise have separate plans/results; neither synthetic tests nor short data qualify seven-day completion.


精确版本化候选保留数据故障入口和两套分离计划见[实际门禁与演练](../docs/testing-versioned-aged-faults.md)，合成检查命令`python3 tests/vendor-versioned-aged-faults-checks.py`。默认只读，Linux9项不表示真实矩阵或七天通过。


`vendor-versioned-business-reload.py`：精确候选原DBS/HISDBS启动链下的600秒重载及引擎联测；默认只读，执行须固定计划SHA和显式测试marker。范围见[协议](../docs/testing-versioned-business-reload.md)。


`vendor-business-exec-timing.py`/`vendor-engine-timed.py`/`vendor-api-timed.py`：独立测试目标上的exec/容器内请求分段，复用固定R95函数和原业务判据；默认只读。见[诊断协议](../docs/testing-business-exec-timing.md)。


`vendor-business-reload-edges.py`：原DBS/HISDBS600秒协议中的危险内存延后、六秒安全窗口及缺失/目录/FIFO/超大/悬空链接配置。默认只读，显式隔离marker执行；见[固定协议](../docs/testing-business-reload-edges.md)。


`vendor-business-reload-source-recovery.py`：原DBS/HISDBS600秒协议中的危险内存延后、六秒安全窗口及缺失/目录/FIFO/超大/悬空链接配置。默认只读，显式隔离marker执行；见[固定协议](../docs/testing-business-reload-source-recovery.md)。


`vendor-business-memory-pressure.py`：原600秒业务中的精确内存30→20高用量延后/释放/同代次重试；`vendor-memory-pressure-worker.py`及Linux自检仅为有界匿名内存测试工具。见[固定协议](../docs/testing-business-memory-pressure.md)，默认只读，必须有隔离执行标记。


`vendor-memory-pressure-worker-v2.py`与`vendor-memory-pressure-selftest-v2.py`修正厂商Python2的linux2平台名兼容；旧工具/原失败保持。Linux7项和两镜像16项有界释放检查见[实际运行时结果](../docs/testing-memory-pressure-legacy-runtime.md)，不计真实30→20压力或业务通过。


`vendor-business-memory-pressure-legacy.py`绑定实际Python2/linux2验证过的v2内存工具，保留原32项/两角色600秒及全部原SLA；见[新冻结协议](../docs/testing-business-memory-pressure-legacy.md)。原R130失败执行器/计划不修改。


`vendor-thread-observer.py`和`vendor-thread-observer-checks.py`是单目标只读诊断工具；Linux19项资格及DBS/HISDBS各15秒实际线程读取见[工具记录](../docs/testing-thread-observer.md)。不接业务启动、不改产品资源或原压力/业务阈值；后续完整压力联测另待。


R167[完整压力线程诊断](../docs/testing-business-pressure-threads.md)已实现并冻结；新增实际14项生命周期资格通过，首次SSH作用域缺控制文件失败保留。原完整业务方法AST除观察器启动/保存外一致，原32项/两角色各600秒及全部配额、SLA、历史失败不变；此时压力业务尚未执行，52项不宣称完成。


R194[原生请求/PG等待诊断资格](../docs/testing-native-request-pg-diagnostics.md)完成：Linux23项、两厂商镜像各23项+3入口保护+16真实PG检查通过；正常请求通过，受控锁各保留一次原SQL超时，并取得对应后端/等待/阻塞者。三次先前资格失败和旧源码保留，四Pod cgroup/namespace/运行器独立确认消失，原输入/程序保持。仅采集链路资格，不关闭R167/R142/R120、原32项/两角色600秒或长期条件。


R203[完整压力接入原生/PG诊断](../docs/testing-business-pressure-native-diagnostics.md)已冻结并实际启动：12项只读前置和6项实际旧报告采集检查通过，开始快照DBS10局部/8区间、压力辅助仍在工作，各600秒/HIS及终态未接受。原完整业务方法AST仅诊断绑定变化，原32项/全部配额/SLA、旧失败与长期条件保持；不以初始报告零计数证明当前零错误。


R203[原生诊断压力联测终态](../docs/testing-business-pressure-native-diagnostics-failure.md)失败：DBS13局部/11区间通过，但备库停库31.421秒超过原30秒，71个引擎探针另有7次API内部超时；未完成两角色600秒/HIS。提前外部失败导致原生最终诊断未落盘，初始零计数不可当通过。原始185线程样本、日志和输入恢复/进程清理已核对；保留旧失败/原预算/52项和七天任务，不放宽标准。


已完成[提前失败原生负载最终清理资格](../docs/testing-native-final-flush.md)：Linux18项、DBS/HISDBS两原镜像各8项实际通过并退出/清理；精确pidfd仅向本轮worker发TERM，实际部分诊断落盘，原600秒/failed/interrupted保持。首轮长无关参数拒绝及旧源码保留。尚待完整压力工具接入与原业务复测，R203停库和API失败/全部52项/长期标准不因此解除。


已归档[完整压力等待诊断/失败收尾接入](../docs/testing-business-pressure-final-wait.md)：只读采集24项、观察器19项、选取预算10项，两业务API各16个短样本（未见D）及同实例/控制值保持；12项接入与15项只读/拒绝检查实际通过，原生部分PG报告仍拒绝作600秒。新R235完整32项/每角色600秒/11区间原配额SLA未变并已启动，固定启动快照不代表通过；原R203停库/API失败、所有52任务和长期要求保持。
