# 当前验收入口

本页与[52项任务索引](current-task-registry.json)说明现有证据和剩余工作，不是1.0完成审计。规划40项、双模式追加6项、自动标定追加2项、日志/独立百分比追加4项均保留，共52项；R29取消扩展资源的新交付，不删除历史记录。[原十版条件](roadmap.md)及[最新三资源语义](independent-percentages.md)继续有效。

| 范围 | 当前证据 | 仍未完成 |
|---|---|---|
| 已发布预览 | 三独立百分比、cgroup门禁、日文件/30天/1GB；原资产四格原生控制验证 | 不是正式RC3/稳定1.0；默认20%四格业务均未接受 |
| 当前组合源码d3706f3 | [原生ARM212个Go pass事件、实际整盘44项](testing-partition-integration.md)、[构建身份9项](testing-partition-build-identity.md)、[自身三场景1800秒开销](testing-partition-steady-overhead.md) | [当前程序真实路径两格600秒/12项通过](testing-partition-realpaths-business.md)，[同程序辅助故障20场景/108项通过且清理](testing-partition-realpaths-faults.md)；当前维护22项、冷重建44项通过，仍未正式发布 |
| 分区IO | [468fe73实际双分区四格164项](testing-partition-cgroup.md)，与组合生产源码逐文件一致合同独立列明 | 单父盘双分区不等于独立物理多设备；未测复杂栈仍未支持 |
| 业务与辅助故障 | 原7638/d6的600秒手动预算、冷重建/故障/维护各报告保持自身来源 | 当前d370已按原manual64预算两格复验及20场景辅助故障通过且清理；原[默认20%失败](testing-three-resource-default20-business.md)及[补测](testing-three-resource-default20-supplement.md)不改为通过 |
| 正式长期 | [旧fc2 observe基线固定22h观察](continuous-acceptance.md)，4周期内容仍待最终原生判定 | 尚未接受完整86400秒；固定d6的等时enforce未开始；[d370独立七天组件已开始](testing-seven-day-current-candidate.md)，仅首300秒观察，未接受 |
| 维护/最终支持 | 已有开发构建往返、共享切换/独立恢复、配置/状态兼容草案 | [当前d370开发程序实际维护22项/两格600秒通过](testing-partition-realpaths-maintenance.md)；最近两个已发布次版本、最终支持矩阵、未测硬件及边界审计未完成 |

每份报告中的源码、实际程序摘要、环境、预算、时长和未测范围决定它能证明什么。文件存在或CI绿色不自动关闭整组业务、硬件或发布条件。当前三资源范围不恢复pids/权重/memory.high/Swap新参数；旧代码仅按兼容和恢复所有权规则处理。


当前d370故障矩阵已有[固定中间观察](test-progress-partition-realpaths-faults.json)，仅9场景checked/49项通过，实际标定中断正测，整轮20场景/108项及清理仍待判定；[故障协调等待快照](test-start-partition-realpaths-faults.json)保留原启动时刻。另[维护协调进程仅等待](test-start-partition-realpaths-maintenance.json)，0个维护Pod/0项通过，不提前宣称升级成功。


上面的固定中间观察保留原时刻；[故障最终20场景/108项通过且清理](testing-partition-realpaths-faults.md)覆盖其后终态。维护按独立报告判断，仍不关闭已发布次版本或长期门槛。


故障通过并清理后，[维护夹具已进入DBS启动阶段](test-start-partition-realpaths-maintenance-execution.json)。这是固定执行开始观察，尚无完整600秒维护结果；上面的0Pod等待观察属于更早时刻。


上文维护协调0个Pod是固定启动时刻；[实际维护终态](testing-partition-realpaths-maintenance.md)另列22项通过及清理，最近两个已发布次版本仍未完成。


当前[开发程序维护22项/两格600秒](testing-partition-realpaths-maintenance.md)与[冷重建44项/四次启动](testing-partition-realpaths-cold-rebuild.md)均通过且清理。七天组件按独立安排继续；最近两个已发布次版本、正式24h+24h、老化状态后置及最终支持审计尚未关闭。


当前d370[七天原生组件已实际开始](testing-seven-day-current-candidate.md)，两业务各原生300秒首观察及6份宿主样本，首次周期在执行；不是604800秒通过。连续组件之后的老化状态后置和最终发布门槛继续。


[报告只读核验器](soak-report-audit.md)已验证真实中间报告保持pending，拒绝错误摘要及短测冒充；这是验收工具检查，不是持续业务通过或运行时清理证明。


当前[环境覆盖索引](environment-coverage.md)区分当前程序、原发布包、分区来源、真实v2与模拟版本门禁；不作为完整1.0支持承诺。正式基线最新固定观察推进到22h，七天首周期内容通过但native-pending。
