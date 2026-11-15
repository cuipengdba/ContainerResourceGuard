# 固定1.0候选：受控二进制升级与回退验收

本轮已完成40/40，DBS/HISDBS各自新600秒SQL/API通过，全部自有对象清理已独立确认。[准确终态](testing-final-v1-binary-maintenance-terminal.md)。冻结输入及旧草案拒绝原件保持，旧轮运行时长不转记。

previous为实际公开v1.0.0-preview.5，ELF be6b0aa9f9bf932d8b02872e86a9cffcfea6d7199e39c274694dce904af07333；candidate为固定v1.0.0 ELF 9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8。两者产品源码均为ced461705ebc27315a59aefe463f9b4af47130a3，嵌入版本/ELF不同。候选不冒充已公开稳定版，没有重建程序或覆盖旧附件。

两角色分别新namespace、真实DBS/HISDBS镜像/原启动链/挂载路径及原CCG，每容器只维护自己的一个Agent。manual固定CPU7.2核、memory.high20001980416B、双向64MiB/s及手动4096IOPS；外部8CPU/20GiB硬限制保持，百分比默认值不变，不自动标定。

沿用已通过的preview4到5维护框架和完整回读契约，预算、worker、全部600秒/零错误/最大5秒/p95桶上界1秒/98%采样覆盖、64MiB/PG/PID1/缓存保持及退出条件不变。每角色20项主检查，总40；汇总显式绑定冻结planned_checks_each_role，不能因末尾常量遗漏新增检查。原前置1465两角色新600秒及实际备份/同步/独立恢复已经独立接受，本轮只检查SQL/API与在线维护，不把前轮引擎或时长重复累计。

每角色执行quiesce、安装立即回退、候选运行后未变快照回退、再次升级、变化配置拒绝旧收据、准确恢复配置及全新收据显式反向安装，再恢复旧版。16条命令含末尾disable；15条在线命令和4次resume须全部位于本轮成功600秒窗口，只有一个写入者，所有8项实际控制和journal原值保持，末尾disable恢复8项运行时原值/空自有journal。

启动前实际要求新1465整体passed/20项主检查和71登记记录清理；同ELF1461两档1800秒整体passed、runner/worker/四个PID/start/两对父叶及namespace消失；拒绝与其他新final业务执行器并行，旧78任务保持不动。新1501自身的namespace、输出、launch/guard必须全新；资源余量需满足创建28GiB/运行8GiB内存和20GiB磁盘。

这是最终候选的二进制维护范围。supervisor安装工具/未知模板拒绝、CLI human/JSON过期与锁语义、未来格式/镜像持久化、压力与老化仍分项验收。不是默认20%业务通过、不是两次正式minor兼容、不是厂商ARM或独立物理多盘、不是七天稳定接受。P08.2在显式受控切换/回退范围补齐，当前16/52项完成；其余边界分项保留。

[冻结计划](test-plan-final-v1-binary-maintenance.json)、[准确工具](../tests/final-v1-binary-maintenance-frozen/README.md)、[可逆适配](test-adapter-final-v1-binary-maintenance.json)、[本地核对](test-results-final-v1-binary-maintenance-local-preflight.json)、[原生准入](test-results-final-v1-binary-maintenance-native-preflight.json)、[前置诊断业务终态](testing-final-v1-diagnostics-counter-fixed-terminal.md)、[前置开销终态](testing-final-v1-budget-overhead-terminal.md)。

历史启动过程和记录错误见[启动快照](test-start-final-v1-binary-maintenance.json)、[准确原件](test-evidence-final-v1-binary-maintenance-start.json.gz)；只补记已有进程身份，未重跑。额外观察程序不改变12项冻结测量输入。
