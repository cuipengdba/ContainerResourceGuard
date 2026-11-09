# 原镜像数据库与备份短测（2026-11-10）

此项对应 P01.1 的部分验收。DBS、HISDBS 各 9 项，共 18 项通过；结果见 [JSON](test-results-vendor-backup-linux-amd64.json)。当前发布仍为 RC2，此报告不表示 RC3 或稳定版已发布。

## 环境与启动链

使用业务节点只读导出的 DBS `V7.0.12.001.02.56`、HISDBS `V7.0.12.001.02` 原镜像。在测试节点创建全新数据目录、独立 DCS、独立状态目录和临时 Pod，不导入业务数据。各 Pod 非回环网卡关闭，命名空间另设拒绝入站/出站策略。镜像、配置、凭据及原私有 supervisor 不进入公开仓库。

保留镜像 `/root/start.sh`；对原 supervisor 应用仓库已有可选辅助进程补丁。测试配置只调整回环端点、集群标识和全新凭据，数据库保留 `shared_buffers=8960MB`，实际运行 PostgreSQL 14.19。每个主容器的外部保护上限为 CPU 8、内存 20GiB。

CRG 源码 fc2e26d，处于 **observe 20%**，没有施加资源限额。原 ContainerCacheGuard v0.2.0-rc.5 处于 **enforce**，仅针对备份路径，缓存目标 256MiB，排除 PGDATA。二进制摘要见 JSON。本次不能证明限额模式下的业务性能或冷启动通过。

## 预设负载与结果

每个数据库新建专用测试 schema，初始 16,384 行，每行 4KiB 确定性 payload，关闭该列 TOAST 压缩；payload 合计 64MiB。后续追加 2,048 行，达到 72MiB。这是小规模合成业务，不代表生产数据规模或生产峰值。

| 检查 | DBS | HISDBS |
|---|---|---|
| 初始行数、ID 合计、payload 字节与内容摘要 | 通过 | 通过 |
| pg_dump 与 pg_restore 至独立测试库 | 通过 | 通过 |
| pg_basebackup 物理备份 | 4.32s | 3.96s |
| 临时备库追平新增行且摘要一致、处于 recovery | 通过 | 通过 |
| 独立恢复库等于备份时摘要、可写且不改变原主库 | 通过 | 通过 |
| 工作期间 POST /test 与 SQL 探测 | 22 组，全部通过 | 22 组，全部通过 |
| 临时备库和恢复库停止，副本目录移除 | 通过 | 通过 |

预设每步命令期限 300s、复制追平 60s、每次 API/SQL 探测 5s；API 要求 HTTP 200 且 Result=000。API 最大探测耗时为 DBS 3.12s、HISDBS 1.70s；SQL 为 1.27s、2.41s。**耗时包含 kubectl exec 和登录 shell 开销，不能当作接口内部延迟或生产 SLA。** 原始采样、完整 checksum 和各项条件保留在 JSON。

临时备库/恢复库使用独立端口和 128MB shared_buffers，未改变原主库参数。基准备份和逻辑备份留在测试目录，可能包含测试连接信息，不应公开上传。

## 可复现入口与修正记录

[tests/vendor-engine-smoke.py](../tests/vendor-engine-smoke.py) 是本次固定测试夹具的参数化版本，要求 Python 3、kubectl、本地隔离 Pod 及匹配标签；容器内使用原厂 PostgreSQL 与登录环境。它只在 `crg-vendor-lab-*` 命名空间运行，要求 Pod 标签 `managed-by=crg-vendor-test`、关闭 hostNetwork/hostPID。必须先由隔离夹具关闭非回环网络，这些标签并不是权限隔离机制。

```bash
python3 tests/vendor-engine-smoke.py \
  --namespace crg-vendor-lab-<本次隔离测试> \
  --work-dir /var/tmp/crg-<本次私有证据目录>
```

脚本创建全新测试 schema/数据库和备份目录，拒绝复用已存在的本次目录；不删除原主库数据。失败时尝试停止临时实例并保留日志。公开参数化版本在原固定脚本基础上增加输入/范围检查和退出清理，不能把语法检查算成该新入口已实跑；后续限额回归使用该入口另存结果。

早期夹具错误保留：产品类型先误设为 PUC，无法匹配原 db.ini 分节，修正为 PUC-DBS；root 直接执行 pg_isready 未加载厂商库环境，改为 `su - postgres` 后正常；GET /test 返回 405，改用 POST JSON 后返回 000。旧就绪超时不能当成有效冷启动耗时，也没有据此放宽原探针。

## 仍未完成

- 厂商专用备份/同步 API 和真实调度周期。本次为原镜像主库上的 PostgreSQL 引擎流程。
- enforce 20%/30% 下的冷启动、原探针阈值和相同负载对比。
- 原镜像里辅助程序故障组合、完整接入回退。
- 24h observe + 24h enforce、业务高峰及至少 7 天验收。

这些缺口继续保留在 P01/P02/P05/P10，不以本次 18 项短测关闭。
