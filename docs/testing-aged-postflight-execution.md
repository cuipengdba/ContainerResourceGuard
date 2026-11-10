# 老化数据后置验收执行器

新增[独立测试执行器](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/tests/vendor-aged-postflight.py)和[7组自检](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/tests/vendor-aged-postflight-checks.py)，实现实际保留数据的重新挂载、备份/逻辑恢复、新Pod及journal隔离、原缓存新鲜状态、日志追加、维护和最终原值恢复。它是97隔离实验的显式验收程序，产品依然一容器一份Agent，原start.sh不接入该测试执行器。

## 冻结来源及入口

[正式后置执行计划](test-plan-aged-postflight-execution.json)引用原[采集计划](test-plan-aged-postflight.json)和私有身份记录的固定摘要，不改写R59计划、记录或正在运行的七天组件。[短数据演练计划](test-plan-aged-postflight-rehearsal.json)是完全不同的命名空间/工作目录，只复用已完成600秒短业务测试留下的数据；必须显式`--rehearsal`，与正式模式不能互换。

以下从源码仓库运行；既有下载预览包未包含新测试工具。默认只读检查，不创建输出目录、Pod或限额；建议`python3 -B`避免解释器在工具目录生成字节码缓存。

```bash
python3 -B tests/vendor-aged-postflight.py \
  --plan docs/test-plan-aged-postflight-execution.json \
  --plan-sha256 c412ff8d258234fcc05c2f5730f5abcec6940bd163c780f3821fcc170284c44a
```

七天实际604800秒/28周期、完整原生判定、原运行器退出0、旧namespace/cgroup独立消失、同一数据/配置/journal/日志身份等条件均满足才允许后置；运行中返回pending/退出2。即使加`--execute`也不能提前执行，已在真实长测存活时验证，两角色实际8项控制、journal及8个输入摘要保持，后置目录/namespace前后不存在。

实际写操作另需`--execute`及`CRG_AGED_POSTFLIGHT=authorized-disposable-test-node-only`，以独占新建的0700工作目录防止重复启动。这是已授权测试节点的隔离验收标记；不适用于生产部署或自动控制多容器。通过前置不等于执行完成，最终仍固定P10_complete=false和release_accepted=false。

## 实际执行内容

1. 验证原私有Pod配置/镜像/启动链和原CPU8核、内存20GiB的外部预算；继承数据、配置、state、日志目录及原DCS数据。仅改变测试namespace、网络gate，增加独立staging/recovery挂载，并在维护阶段允许替换CRG程序；CCG保留只读，原配置文件不改写。
2. 先将eth0关闭，再释放原业务启动gate。原PG/API/managed300秒、就绪后缓存45秒门槛和既定manual64预算保持。确认各一份来源匹配的Agent/缓存、五个兼容控制原值不变、新容器真实原值先记录。
3. 对实际保留的`crg_soak_<原run-id>.fixture`核对64MiB内容、完整checksum和最终counter，使用pg_dump备份并在独立逻辑数据库中pg_restore核对；源数据不改写，不复制正在运行的PG目录。
4. 删除自己的Pod并确认旧cgroup消失，使用同一目录/配置创建新Pod，再核对新ID、新journal与previous身份、PG冷启动、缓存新进程/状态及实际原值。备份摘要和实际老化数据保持。
5. 运行新的600秒原生SQL/API负载，在完整原生窗口内记录8个安装/回退/启停Agent操作区间。当前d370程序到50671aa开发程序、立即回退、旧Agent运行及回到当前Agent均保留journal原值、实际控制、PID1/PG/原缓存。两程序均为开发构建，不能替代最近两个已发布次版本的维护验证。
6. 新原生负载另建一份64MiB私有schema；实际老化schema在操作前后独立核对内容和counter，不能将新schema说成七天数据。仍按零错误、5秒最大、1秒p95桶、98%覆盖和实际600秒判定。最后disable必须恢复新容器首次记录的全部8项真实原值，确认无OOM、原配置/目录保持、旧日文件前缀保留并有追加、所有CRG日志0600。
7. 按原namespace UID和Pod UID清理自有夹具，保留实际数据及私有0600报告。业务已停止也允许按UID清理，不能依赖业务仍活着；错误不触碰其他namespace或原正式24h基线。

## 当前证据与边界

[机器结果](test-results-aged-postflight-execution.json)记录Linux7组全部通过、Windows明确跳过1组POSIX，以及真实提前执行拒绝。独立短数据演练现已终态通过：两业务四次启动、36项检查、两角色各实际600秒原生负载，分别覆盖8个维护操作区间；退出0，原运行器/执行进程已退出，namespace及四个Pod的主cgroup/所有容器scope均独立确认不存在。实际旧64MiB数据/counter、备份/独立逻辑恢复、新journal、原值恢复和日志追加均按脚本检查通过。原9项开始快照保留原时刻，不覆盖为终态。三个分支来源明确的CI均通过。

独立恢复是同一测试节点的独立逻辑数据库，不是物理独立恢复主机；当前程序、manual64和Linux5.14/AMD64/单设备范围保持。实际七天后置尚未执行，老化状态辅助故障复验、原24h+24h、最近两个已发布次版本、未测硬件及完整52项/支持审计均仍需完成。原七天运行、冻结d6正式切换候选和原发布资产没有替换。
