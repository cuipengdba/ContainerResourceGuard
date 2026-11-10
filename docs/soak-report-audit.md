# 持续验收报告的只读核验

源码新增[报告核验器](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/tests/soak-report-audit.py)和[合成反例检查](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/tests/soak-report-audit-checks.py)，落实R24/P10.2/P10.3，未新增资源参数或替换当前d370程序。它只读取指定报告并向stdout输出摘要，不启动/停止进程、创建目录、修改配置或写cgroup；属于测试工具，不是管理多个容器的产品服务。已发布预览包未增加该源码工具。

调用方必须独立固定Agent、缓存、原生worker、campaign、engine五个SHA256，并明确baseline/enforce/acceptance；不能靠报告自报摘要选择信任。baseline/enforce固定86400秒，acceptance固定604800秒；enforce还要求明确前轮source-run-id。报告phase=preparing/measuring返回pending和退出码2，通过返回0，拒绝返回1。

终态会重新验算两业务原生时长、零错误、最大5秒、直方图p95桶上界1秒、98%采样、64MiB完整性、同一主库/线程退出、宿主样本覆盖与最大间隔、Agent/缓存/PID1身份、OOM增量及4或28周期的内容/清理/完整原生时间包围。保留原门槛，不把content-passed-native-pending当通过。重复JSON键、NaN及非法类型拒绝，输入最多256MiB，输出不回显私有原始错误、连接环境或数据路径。

当前七天报告示例（工具从源码目录运行，测试报告路径按该轮实际路径）：

```bash
python3 tests/soak-report-audit.py \
  /var/tmp/crg-seven-day57-20261111/campaign-acceptance/report.json \
  --phase acceptance \
  --agent-sha256 3a1ce7dbf5630f8f1c823005ceb4958653c6c235b2ba5026956ca6597f1926f9 \
  --cache-sha256 757ba385a0ee4bdadc968b96b5c3e69fd44353060e5ab28520fd6f73a59902de \
  --worker-sha256 ba87ef2d646b723eb8419de25ffcd736f7a5b0925716f4b638761dff70bb2461 \
  --campaign-script-sha256 b49d5a73654c5cf7c93b04851f3409eea318b3a9c71c0e8f601f252a3dda07ea \
  --engine-script-sha256 b0d4fe313156743ff1424b46eb58c5ab5b8e1f2c91851420023f5f018dd08e5c
```

自检使用 `python3 tests/soak-report-audit-checks.py`。[本轮结果](test-results-soak-report-audit.json)区分5个unittest方法中的合成正反例与4个节点只读检查：真实七天/24h中间报告均返回pending，错误预期Agent摘要拒绝，已完成600秒短测不能冒充七天。合成七天JSON通过只证明核验算法，不代表墙钟等待或业务运行了七天。

该工具验算报告的一致性，不单凭报告关闭全部运行时条件。运行器真实退出码、namespace精确身份/实际清理、实际老化数据/配置/journal/日志保留和后置操作、最近两个已发布次版本、硬件支持及完整52项仍须独立核对。因此即使报告核验通过，输出固定release_accepted=false、runtime_cleanup_verified=false；未宣布1.0完成。


三个分支该工具提交的build-and-test均完成并通过，组合线[CI42905294675](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42905294675)覆盖Linux/race/vet、辅助链、核验器自检、包完整性和重复构建；完整提交/工作流映射已写入本轮JSON。没有替换正在长测的d370或原fc2/d6程序。
