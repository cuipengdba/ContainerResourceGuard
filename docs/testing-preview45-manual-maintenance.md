# preview.4 → preview.5 同预算在线维护验收

计划在启动前冻结：job `e7239815f60ca28a0bb5e59735c3e61bf8bc68458736f47d31d9039355760b6a`，plan `fb6dc754e3c0b260c3ba869ec30f682a94641e3e9217d4c8bd8c2a8e7df5a6a1`。17项结构/真机资格检查通过，尚未启动，不是业务通过。两版公开包各8项下载重新核对，AMD64 tarball中的regular ELF与冻结输入完全相同。发布说明可继续追加，因此程序绑定中的旧body哈希仅为绑定当时快照；启动前另查当前说明，附件与tag保持不可变。

前置的[手动完整600秒业务](testing-manual-reference-full600-terminal.md)已经两角色16/16通过并独立清理54登记实例；本轮另外新建namespace、输出及回环DCS隔离副本，使用DBS/HISDBS原镜像、启动、真实挂载路径和原CCG，只维护各自容器中的CRG。固定7.2核、memory.high20001980416B、读写64MiB/s、可选手动IOPS4096，保留外部20GiB硬上限；不改产品默认百分比，不自动标定。

两个实际程序先在业务gate关闭时用readonly doctor核对相同身份、设备和三项手动高水位计划，并预声明八项原值及journal。启动旧版后，在原600秒SQL/API工作负载内执行quiesce、首次原子安装/立即回退、运行新版后相同快照回退、再次升级、变化快照拒绝，以及使用当前状态和全新收据的显式反向安装。每次resume要求一个准确来源的写者，原PID1、主库、CCG、额度及journal保持。未变化快照允许回退；变化负例仅在quiescent时临时增加interval_seconds=16，不运行Agent、不改资源值，拒绝后恢复准确配置。

每角色20项，共40项；原启动300秒、缓存45秒、native600秒/零SQL及API错误/最大5秒/p95桶1秒/98%覆盖/16384行64MiB保持，所有维护及恢复必须完整位于成功窗口内。最终disable核对全部八原值、空journal和准确配置恢复，独立验证所有登记进程实例、两namespace与父叶消失。任一失败原样保留，不重试或放宽标准。前置十项备份/同步/独立恢复是已完成的另一证据，本轮不重复或混算引擎内容。此测试为公开程序维护，不声称所有安装器、百分比迁移或两个正式次版本已验收。

[冻结计划](test-plan-preview45-manual-maintenance.json)、[17项资格及真机预检](test-results-preview45-manual-maintenance-preflight.json)、[可逆适配记录](test-adapter-preview45-manual-maintenance.json)、[冻结工具](../tests/preview45-manual-maintenance-frozen/README.md)。[原设计](testing-preview45-manual-maintenance-design.md)保持历史身份；原默认20%失败、52项任务及稳定1.0门槛继续，未接受稳定发布。
