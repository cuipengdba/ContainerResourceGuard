# 实际CPU在线数变更回归：冻结协议

源码检查发现常驻run循环使用启动时Environment，虽然逐周期重新发现并复核身份，却未更新容量信息。这是待原生验证的缺陷假设；当前不以静态代码推断为实测通过或失败。

本方案归入原P06.4/P06.3及P10.3的容量来源与现有外部约束要求：在专用一次性GitHub VM真实将一颗非0 CPU下线/上线，不伪造online文件，不在DBS/HISDBS共享节点操作CPU。每个容器恰好一个原Agent，CPU/memory/IO配置均20%；本CPU专项关闭IO标定、无profile且IO保持未覆盖，不借此声明IO通过。

两格：原CPU预算足够20%的容器，以及外部CPU上限0.1核的容器。每格原启动及两次真实CPU下线/上线，共5次快照；每快照独立核对内核online数、常驻状态容量、实际cpu.max、同Agent/PID1及其余七项原值，同时以新CLI计划交叉核对。live状态必须在原1秒周期下10秒内反映当前基数，不能通过重启Agent替代同进程要求。原值恢复、无OOM、所属容器/cgroup/进程清理也验收，预定56项。任何失败保留false与原件，不延长窗口或把启动快照称为实时容量。

先执行amd64/Linux6.8 pilot，保留准确原输出/方案/源码/状态及新CLI计划后独立复核，再决定后续ARM步骤。失败时也必须恢复原CPU在线mask并清理所属夹具。隔离VM与占位业务不代替厂商业务或整个P06.4完成。

准确输入见[test plan](test-plan-final-v1-live-cpu-capacity.json)，SHA256 `72c051c3667f1d073aa57482cab136a2391c0585c8c504a81efb29465c178b0a`。使用已注册native-cgroup工作流在独立test/live-cpu-capacity分支调度，仅该分支的工作流执行此协议；既有固定来源的历史工作流及证明不改变。原1728长测暂时保持原程序/计时，但本问题闭合前不能据此接受最终稳定候选。

## 首轮测试夹具错误（保留）

冻结源码742c988、run43758083710、artifact14178469670原件[完整归档](test-evidence-live-cpu-capacity-first-fixture-error.json.gz)。初始状态读取后，测试脚本误用不存在的`plan`子命令，实际返回usage_invalid/unknown command并退出1；CPU尚未下线，仅3项所属夹具清理通过，原CPU mask恢复。不是产品容量缺陷的实测证据。v2只将该调用改为现有`doctor`接口，预定56项、10秒窗口、同Agent及实际sysfs操作标准不变，重新冻结后重跑。
