# 正式版本号候选：固定产物与原路径业务验收

本轮固定产品源码`ced461705ebc27315a59aefe463f9b4af47130a3`，嵌入版本号`v1.0.0`。这只是待验收候选，没有创建稳定标签或发布；当前下载仍为preview.5。两次构建和另一绝对路径的全新检出均得到相同的两架构ELF、manifest和SBOM。50个产品源码文件与当前集成版本一致。新ELF与preview.5不同，不能继承旧产物的业务时间或长期结果。

- amd64 SHA256：`9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8`
- arm64 SHA256：`ff1a2c1c599eb38fde6857c2eede70a1deabf0c2c89977ab92e71ec52ec3982b`

[候选身份与构建记录](final-v1-candidate-identity.json)仅证明同主机/工具链重复构建，不能冒充原生ARM或Linux6业务验收。amd64候选已在测试节点执行build-info。14项预检包含13个冻结输入摘要、实际节点资源/旧任务独立清理、28项执行器结构与故障检查；尚未启动业务夹具。

本轮只运行两组正常业务：DBS、HISDBS各全新namespace、Pod/container ID、数据目录，使用原厂镜像、真实挂载路径和原启动链，每容器一份Agent，缓存程序保持原样。每组9项，共18项。原7项启动核对、原生600秒SQL/API零错误、最大5秒/p95桶1秒/98%计划覆盖、64MiB内容校验、实际PG物理备份/同步/独立恢复十项、真实PG端口拥有者八阶段均保持。不重复已完成的预期端口冲突组。

配额沿用已声明manual参考预算：7.2CPU，memory.high=20001980416字节，读写各64MiB/s，手动IOPS=4096；外部8CPU/20GiB保持。PG原命令和300秒启动/30秒停止期限不变，失败保留，不自动重试或放宽。共享节点需启动可用内存至少28GiB、持续至少8GiB、磁盘至少20GiB；每组清理核对通过才进入下一组。

[冻结计划](test-plan-final-v1-full600.json)、[14项预检](test-results-final-v1-full600-preflight.json)、[可逆适配](test-adapter-final-v1-full600.json)、[完整执行器](../tests/final-v1-full600-frozen/business-driver.py)、[协调器](../tests/final-v1-full600-frozen/runner.py)。实际运行只认冻结输入摘要。先前1340套件44/44及其134条登记进程、四组namespace/cgroup清理是本轮前置条件，不作为本轮业务结果。

本轮通过也只代表当前amd64/Linux5.14/单设备manual参考预算；此前默认20%完整业务失败仍保留。新产物原生跨架构验证、独占24h基线+24h限额、至少七天及52项逐项范围审核继续，均不在本轮18项里。稳定1.0尚未接受。
