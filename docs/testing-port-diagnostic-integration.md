# 临时备库端口诊断接入engine/campaign

已在当前测试源码接入只读采集。产品CRG程序、preview.5标签和八项附件不变；本轮是长期验收执行器的工程改进。

## 接入行为

engine为每个角色建立独立会话，验证隔离namespace标签、Pod UID/name/角色/CID、运行状态、实际runtime PID/start、纯v2自身leaf及net/pid/mnt与宿主隔离。采集前再次核对Pod UID、CID、runtime PID/start/cgroup/netns；不接受旧身份扫描。只读模块仍不更改配额、发送信号或停止端口拥有者。

在standby/restore启动前、启动成功后、启动失败时，以及stop失败、每次stop成功和cleanup之后采集55432/55433。只记录观察，不把空表当作端口可用保证。普通模块加载、入场检查、采集或诊断保存失败保留partial/unknown并继续原业务路径；标记的执行器停止异常继续传递，避免被通用诊断异常处理吞掉。辅助模块由闭包保留引用。campaign在每个原引擎周期摘要中附加样本数及complete/partial计数，完整事件仍在原business-backup.json内。

原PG命令、数据量、配额及启动60秒/stop30秒/外层90和45秒、原生零错误/最大5秒/p95桶不超过1秒/98%覆盖等门槛未放宽。元数据调用各有4秒外层上限、kubectl请求3秒、采集默认2秒，诊断自身消耗计入实际测量窗口。绝不据端口归属自动终止未知进程。

## 验证与局限

28项结构/故障检查通过：执行实际插入的engine AST块，模拟PG启动失败，在诊断成功/失败两种情况下原业务异常对象保持；普通采集错误与保存失败放行；停止请求原样传递；错误Pod、宿主namespace、角色重复、非运行状态等拒绝。业务命令为明确stub，这部分不是实际PG启动冲突。

现有amd64/Linux5.14节点，以DBS和HISDBS原镜像各一个隔离Pod、顺序运行，共14项真机检查通过。只运行sleep及本轮Python socket子进程，没有启动CRG、原DB/缓存或业务。eth0关闭、独立NetworkPolicy，真实TCP55432及PG风格Unix socket取得实际拥有者PID/start/cgroup/netns；EOF仅结束本轮子进程。runtime/Pod UID变化测试是显式注入，不声称真实PID复用。两角色前/持有/后实际快照各自保留complete/partial/unknown状态，不改判。

终态13项独立复核通过；原始报告UTF8摘要`8be9deee8dbc439bdfb22e6d6f4cd40054c6ddece4a0bb5b52b369f0cf06387e`与退出记录一致。原driver已退出，一个namespace、两组cgroup父叶、8条登记记录对应6个去重PID/start实例独立确认消失；TCP/Unix共享同一拥有者，所以分别列明登记数与去重数。

[指标](test-results-port-diagnostic-integration.json)、[准确原始回执及报告UTF8](test-evidence-port-diagnostic-integration.json.gz)、[冻结计划](test-plan-port-diagnostic-integration.json)、[可逆接入变更](test-adapter-port-diagnostic-integration.json)、[冻结源码](../tests/port-live-diagnostic-frozen/plan.json)。运行结构/故障资格：`python3 tests/port-integration-checks.py tests`；只读模块原生27项资格见[前一记录](testing-port-owner-observer.md)。

下一步必须另行冻结并运行真实PG端口冲突和完整engine/campaign验证，再启动当前源码24h+24h和七天。本轮尚不接受真实PG冲突、完整600秒或新的长期时长。原默认20%完整业务失败、48/48控制层迁移、52项逐项条件和已声明硬件范围分别保留，稳定1.0未接受。
