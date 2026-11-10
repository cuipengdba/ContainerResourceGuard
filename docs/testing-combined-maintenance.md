# 组合候选维护与命令契约实测

2026-11-10，源码1bc9bcb0a6d5c446f6e36220b5ad4db1bdef8bb7，组合固定工具链/可信包、安装接入及命令原因码。实际Linux程序为Go1.27.3构建，SHA256为41713d40f380046ef2489cb2f978ce959984d73df767f8ca552b7f0ac287ee42，版本字符串next-compatibility-contract。不是正式1.0或v0.8发布。

Linux5.14/amd64/cgroupv2独立容器完成[31项真实检查](test-results-combined-maintenance-linux-amd64.json)，包含之前29项接入/故障/真实原值恢复/持久重建/永久卸载，以及typed-lock-error-JSON-contract和typed-maintenance-error-JSON-contract。前者实际竞争当前写入者返回schema=crg-command-error-v1/reason_code=lock_unavailable；后者重复接入明确返回supervisor_maintenance_failed，未解析错误文案。业务PID1保留、各容器独立状态，命名空间已核对移除。

该候选包含state_dir别名拒绝与对应Linux单元检查。测试节点Go1.22.5的vet/race、既有16个持久化中断建模检查点、6个helper与6个生成补丁故障场景通过，保留最低源码工具链兼容证据；实际cgroup运行的候选另为固定Go1.27.3二进制，不能混用这两种编译产物摘要。Linux CI的Go1.27.3完整测试、包/14项完整性/另路径复现/来源与SBOM生成通过，见[CI42727697085](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42727697085)。

命令单元回归用真实子进程核对错误退出1、stdout只有一个结构化JSON、既有build-info字段保留；类型化底层原因与英文错误文本假冒反例分别验证。恢复未完成继续只输出完整资源结果并增加restore_incomplete，不改变私有Status/journal格式。

这一结果只证明该组合候选在上述隔离环境的维护路径，不代表厂商数据库在线升级、真实掉电、所有架构/内核、后续已发布次版本兼容或至少七天业务验收。相同二进制的三组30分钟低IO/持续导出错误/只读测试，以及两个解析器各10分钟fuzz已完成通过；含R26的74693候选两项fuzz另列，见[实际结果](testing-combined-long.md)。
