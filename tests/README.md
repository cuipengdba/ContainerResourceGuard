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
