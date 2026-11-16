# 新容量候选：当前证据与历史失败

集成候选源`37ca44e0`已独立完成新一轮DBS/HISDBS各原600秒，**原18项业务检查与另4项辅助检查全部接受**；固定四组对照44/44和同源四格原生284/284分别归档。新19输入长稳已唯一实际启动，当前24h observe基线运行中，初期原启动12/12、首周期内容通过但原生整段验证仍pending；同容器24h enforce、新七天和原老化后/发布门槛尚未接受。公开preview.5未改，稳定1.0未发布。

本页核对到测试节点原生UTC `2026-11-16T02:37:27.650400+00:00`；准确PID/start的runner、worker、只读记录器均仍在运行，两角色八项原控制和实际Agent ELF独立复核保持。日期是该节点时钟，时长验收依原程序单调计时；快照不替代原24h/24h/7d。

当前产品源37ca44e0e24a0eaa14e52b5c8bbbda54c76364b0在集成分支；各项资格按准确来源区分，main及其它分支未因此自动换产品源。

## 原生与CPU容量刷新

同一Agent/PID1在四次实际CPU下线/上线后重算20%配额，4核0.8→3核0.6→4核0.8；ARM64/Linux7的56项、原8控制/CPU掩码和归属清理接受，旧版六项失败保留。AMD64下线EBUSY原因未知不算覆盖。完整59来源绑定下，AMD64/ARM64与Linux6.8/7四格原生284/284接受，见[CPU证据](testing-live-cpu-capacity-refresh.md)、[准确计划](test-plan-capacity-refresh-native-CI-v2.json)、[独立结论](test-results-live-capacity-native-CI-v2.json)及[32准确成员](test-evidence-live-capacity-native-CI-v2.json.gz)。首轮50绑定缺9项的门禁缺口仍保留，不改写成完整通过；不代表厂商ARM、内存热插拔或独立物理双盘。

## 新一轮原18项正式验收与长稳

[新正式复验](development-fresh-formal18.zh.md)在四组原600秒对照之后另行冻结、唯一执行；两角色各原600秒、原18项与4辅助分别全部接受，原生SQL/API零错误、完整备份/同步/独立恢复、原启动/缓存/八控制和准确归属清理保持。30准确原件与旧scope/raw false元数据边界已独立复算，不能把先前对照或改标签当正式接受。

[固定四组对照](development-original600-comparison.zh.md)44/44及56原件分别归档；DBS-enforce API5.3326秒和HISDBS-observe SQL8.2149秒两个单独exec原标志仍false。原native-campaign规则以完整成功原生窗口包含内容周期，标准未改；不是所有请求低于5秒或CRG因果证明。

[新长稳1880](development-new-long1880.zh.md)以源37和19准确输入从零开始，原24h observe→同容器24h enforce→新七天及全部原指标不变。原启动12项与当前只读身份/原控制核对通过；首周期内容通过但整段原生资格pending，当前没有24h或长期接受。后续老化后/维护/发布条件仍待。

## 旧1761失败继续保留

旧轮DBS完整600.336702秒，SQL299次1错误/max5.004658635秒，角色7通过/1失败/1未执行；HISDBS600.367087秒、9/9通过，整体17项记录16通过，原计划18项未接受。[完整原文](live-capacity-before-fresh18-long1880.md)、[独立失败复算](test-results-live-capacity-business600-terminal.json)、[22准确原件](test-evidence-live-capacity-business600-terminal.json.gz)保持failed/exit1和独立清理结论。旧工作线程未保存异常明细，丢失信息无法事后恢复，原因仍unknown，不能认定CRG或此CPU修复导致，也不被新成功抵消。

为后续请求增加的[有界错误诊断](development-sql-failure-diagnostics.zh.md)已完成两平台26项及两个准确原镜像各6项兼容性，后续[受控120秒锁负向诊断](development-controlled-sql-wait.zh.md)各13/13，前两次夹具失败保留。该已知注入锁不能解释旧未知原因，PSI六项实际不可用也不能冒充压力验证。

原52项定义及18项既有任务范围声明不改。所有预算保持原固定手动参考，不能证明任意默认20%业务性能；旧ced/1396/1728/78的来源和时钟不继承。其它压力/状态/权限切换、节点/镜像重建、老化后故障/恢复/升级、稳定源打包和实际安装/发布下载等剩余项见[当前逐项审核](current-52-task-audit.md)。
