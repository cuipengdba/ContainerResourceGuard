# 实际CPU在线数变更回归：冻结协议

源码检查发现常驻run循环使用启动时Environment，虽然逐周期重新发现并复核身份，却未更新容量信息。这是待原生验证的缺陷假设；当前不以静态代码推断为实测通过或失败。

本方案归入原P06.4/P06.3及P10.3的容量来源与现有外部约束要求：在专用一次性GitHub VM真实将一颗非0 CPU下线/上线，不伪造online文件，不在DBS/HISDBS共享节点操作CPU。每个容器恰好一个原Agent，CPU/memory/IO配置均20%；本CPU专项关闭IO标定、无profile且IO保持未覆盖，不借此声明IO通过。

两格：原CPU预算足够20%的容器，以及外部CPU上限0.1核的容器。每格原启动及两次真实CPU下线/上线，共5次快照；每快照独立核对内核online数、常驻状态容量、实际cpu.max、同Agent/PID1及其余七项原值，同时以新CLI计划交叉核对。live状态必须在原1秒周期下10秒内反映当前基数，不能通过重启Agent替代同进程要求。原值恢复、无OOM、所属容器/cgroup/进程清理也验收，预定56项。任何失败保留false与原件，不延长窗口或把启动快照称为实时容量。

先执行amd64/Linux6.8 pilot，保留准确原输出/方案/源码/状态及新CLI计划后独立复核，再决定后续ARM步骤。失败时也必须恢复原CPU在线mask并清理所属夹具。隔离VM与占位业务不代替厂商业务或整个P06.4完成。

准确输入见[test plan](test-plan-final-v1-live-cpu-capacity.json)，SHA256 `1e5a7be4fedab53d42fb086b5faf8fb89fe90df4ffd91b86e15719fdb6e985e4`。使用已注册native-cgroup工作流在独立test/live-cpu-capacity分支调度，仅该分支的工作流执行此协议；既有固定来源的历史工作流及证明不改变。原1728长测暂时保持原程序/计时，但本问题闭合前不能据此接受最终稳定候选。

## 首轮测试夹具错误（保留）

冻结源码742c988、run43758083710、artifact14178469670原件[完整归档](test-evidence-live-cpu-capacity-first-fixture-error.json.gz)。初始状态读取后，测试脚本误用不存在的`plan`子命令，实际返回usage_invalid/unknown command并退出1；CPU尚未下线，仅3项所属夹具清理通过，原CPU mask恢复。不是产品容量缺陷的实测证据。v2只将该调用改为现有`doctor`接口，预定56项、10秒窗口、同Agent及实际sysfs操作标准不变，重新冻结后重跑。

## v2原件与v3清理规则

v2 amd64/Linux6.8 run43758489795的CPU3下线写入被内核EBUSY拒绝，8项启动/清理通过但没有实际下线，不计热插拔通过。ARM64/Linux7 run43758860709实际完成4次CPU下线；4→3时常驻容量仍为4，未受紧cap的20%实际仍80000/100000，独立doctor为60000/100000，六项明确失败。另有夹具清理缺陷：紧cap容器所有控制原本已等于目标，无资源写入就不会生成journal，但脚本错误要求journal必存在。该原试验55项/6失败及清理不全保持，[两份准确ZIP原件](test-evidence-live-cpu-capacity-v2-failures.json.gz)完整归档，不接受为全矩阵通过。

v3只修正清理条件：仅紧cap格五份快照都证明journal不存在且八项控制始终等于原值时，允许恢复后journal不存在；发生过变更的格仍要求准确存在且为空。增加journal存在性原始字段，CPU同进程/真实online/20%/10秒/56项标准均未降低。重新冻结并重跑baseline，之后修复程序须使用同一v3测试协议。

## 冻结 v3 对照与修复候选

旧ELF实际ARM64复测 run43759787440：56项中50通过，六项容量/配额失败，四次真实CPU下线，原CPU掩码、八项控制与容器/进程/cgroup清理均通过。原始ZIP及API摘要归档于 test-evidence-live-cpu-capacity-v3-old.json.gz。

修复候选源 37ca44e0e24a0eaa14e52b5c8bbbda54c76364b0，计划摘要 b89326a62840c6429ed9de41752599ee4cd30d28c77b93f1af5a102d58b7f250；驱动、56项条件、10秒观测、两种外部上限、同一Agent/PID1和清理门槛逐字不变，仅更新候选来源、50个生产文件摘要、ELF身份及对照证据。独立ARM64复测尚未完成；不是DBS/HISDBS业务或完整P06.4验收。
