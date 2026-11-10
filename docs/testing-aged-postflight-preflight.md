# 七天后置验收：身份采集与只读门禁

R24/P10.2/P10.3/P10.5继续落实为[只读程序](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/tests/vendor-aged-preflight.py)和[正反例自检](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/tests/vendor-aged-preflight-checks.py)。此轮完成的是采集和前置门禁，后置操作执行器尚未实现；没有进行七天后的恢复、重建或升级，也不表示七天已完成。产品仍一容器一Agent，测试读取器不接入原start.sh。

## 采集与使用

[冻结计划](test-plan-aged-postflight.json)固定当前d370程序、原七天计划摘要、测试namespace/目录和门槛。程序默认不执行任何资源/进程/文件写入，只有两个只读入口：`--capture`读取正在测量的自有夹具并将身份记录输出到stdout；`--seal/--seal-sha256`验证同一轮的后置前提。调用方应将完整记录放在0700私有目录、0600文件，不提交GitHub；记录不含配置原文、口令或业务数据。

采集确认原运行器PID/启动ticks/入口、冻结脚本/程序摘要、实际namespace UID，以及每角色一份当前Agent、原缓存和原生负载。记录主业务与DCS的cgroup身份、7个目录inode、8个不可变输入摘要、journal身份/摘要和日志前缀；不复制正在使用的数据库目录。已在97隔离节点完成两角色只读采集，实际journal和8项控制在后续pending检查后不变。

```bash
# 从源码目录运行；完整stdout需由调用方保存到自己的私有记录文件。
python3 tests/vendor-aged-preflight.py \
  --plan docs/test-plan-aged-postflight.json \
  --plan-sha256 58a8fe7c07c7655c13e1b54a83ad8afd63646947de9b8b8929f1d089dbe2a8cb \
  --capture
```

后置前提检查使用相同`--plan/--plan-sha256`，将`--capture`改为`--seal /private/path/lineage.json --seal-sha256 <独立保存的摘要>`。输入计划和记录摘要必须由调用方独立固定；不能临时信任待检查文件的自报摘要。冻结采集计划及旧记录不随开发状态改写，后续执行计划另行引用这两个摘要。

## 只有这些条件满足才允许进入后置

1. 原运行器完整结束、原退出回执为0、同一PID实例已退出；原程序/工具/计划/来源摘要一致。
2. 原生两角色真实604800秒和28周期通过原5秒最大、1秒p95桶、98%覆盖、零错误、完整性/同主库等门槛；外层11项检查及保留老化目录标记完整。
3. 原namespace独立确认不存在，主业务和DCS旧cgroup均已消失；后置namespace和工作目录尚不存在。
4. 实际七天使用的数据目录身份、配置/程序及journal仍对应本次记录，日文件0600、记录前缀保留且总量不超过1GB。不会以重新创建的空数据夹具冒充实际老化状态。

正在运行时只在原运行器真实身份仍存活的情况下返回`pending`/退出2；来源、证据或状态异常则拒绝/退出1。即使未来通过，也只返回`ready-for-postflight`，固定`postflight_executed=false`、`P10_complete=false`、`release_accepted=false`，不能替代实际恢复和升级操作。

## 已执行与仍未完成

[本轮机器结果](test-results-aged-postflight-preflight.json)区分真实采集、真实pending检查与合成报告/临时文件自检。Linux7个unittest方法全部通过；Windows7个方法运行、明确跳过3个POSIX方法，不能替代Linux结果。首次Linux自检的截断日志夹具把正确的FILE_SIZE拒绝误期望为前缀内容变更；已保留失败来源，拆成截断与等长内容变更两类反例，门禁程序本身未变。

实际pending检查返回2，确认后置目录及namespace前后均不存在，两个角色各8个输入摘要、journal和实际8项控制保持。整个门禁没有启动/终止业务、放宽预算或改动长测程序。只有测试工具安装/私有记录保存发生在新建的独立工具目录，未写入业务夹具。

下一步仍是实现并验证实际老化数据备份/独立恢复、新Pod/旧journal隔离、日志追加、原缓存新鲜状态、600秒原生升级回退窗口、辅助故障复验以及真实原值恢复；这些须在完整七天通过之后，使用同一老化数据执行。原24h+24h、最近两个已发布次版本、未测硬件与最终52项/支持审计仍独立保留。该工具是源码测试工具，既有下载预览包没有增加它。
