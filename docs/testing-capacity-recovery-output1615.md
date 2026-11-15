# 测试容量恢复与输出1615验收

产品源码ced461705ebc27315a59aefe463f9b4af47130a3和AMD64候选9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8保持，未重建。当前17/52，稳定1.0未接受，公开preview.5保持。

## 存储与原镜像

13组明确退役目录的23份终态报告先准确归档：原文2935509字节，压缩314958字节，摘要索引公开；准确压缩包私有保留，未声称它已公开。156份一次性PostgreSQL载荷分13批回收，每批最多12项。每批重新检查目录解析/dev/inode、原报告、所有Pod hostPath/CRI挂载、挂载点、进程cwd/exe/fd；删除逐项原子记账。首次保守检查因node-exporter只读根目录挂载拒绝，未删除；后续只为准确namespace/Pod UID/container、/host/root且只读的已知监控挂载增加例外，不放开其他引用。

实际可用空间增加101025234944字节至155620065280字节；达到预留后停止，另外25份载荷保留。reflink下du表观大小不代表真实释放。原报告、脚本、配置、源fixture和原镜像tar保留，未清理用户其他目录。

原镜像tar1525066752字节，SHA256 f13efd81dcb4364ab6d6f66adb9da8db27fdfe9b2bb91bb6067c84b4a9d49208；manifest两配置摘要与原厂DBS/HISDBS记录严格一致。只导入一次原tar，独立worker有唯一guard及PID/start；实际退出0、CRI原tag对应原digest确认。未换其他镜像或调整kubelet/GC设置。

## 旧78失败后续

准确保存第19周期原报告15284字节，两个角色的10项引擎检查和临时服务器停止/副本移除有记录；随后主库SELECT连接被拒绝，SQL夹具最终清理没有成功，不改写原失败。PG原主日志均有fast shutdown/administrator command后正常关闭；最后采样memory.events各项0只能说明该次采样，不证明之后没有OOM。关闭请求来源仍未确认，相关窗口kubelet/containerd查询无匹配行不能排除其他原因。不能归因于当前memory.high候选。只读独立核对旧namespace、CRI sandbox/container、原Pod UID cgroup及关联进程全部不存在；其原备份文件与报告继续保留，不继承旧时长。

## 新输出1615

1571在原镜像缺失时Ready前失败，其原件不变。本轮13项冻结输入，增加准确摘要绑定的只读节点准入，创建任何夹具前重新检查单节点Ready、三种Pressure=False、空闲至少max(20GiB,文件系统15%)、原镜像digest及原tag，并复核1571原失败/退出摘要与UID/sandbox消失。19项本地检查和原生只读前缀通过；当前发布的是待唯一启动方案，不计业务通过。

同一最终ELF、原厂启动链与路径，每角色原600秒SQL/API、零错误、最大5秒、p95桶上界1秒、98%覆盖率、64MiB内容、26主/28输出检查全部保持。仅更换私有namespace、目录、run-id和增加环境准入；数值断言、警告语义、手动预算、百分比转换/拒绝/冲突恢复不变。正式1396长期任务仍未启动。

[计划](test-plan-final-v1-output1615.json)、[本地检查](test-results-final-v1-output1615-local-preflight.json)、[原生前缀](test-results-final-v1-output1615-native-preflight.json)、[容量回收](test-results-retired-payload-capacity-recovery.json)、[原报告索引](test-index-retired-payload-reports.json)、[镜像校验](test-results-original-image-archive-check.json)、[镜像导入终态](test-results-original-image-recovery.json)、[旧78第19周期准确原件](test-evidence-old78-failed-cycle19.json.gz)、[旧78清理核对](test-results-old78-live-cleanup.json)、[主库关闭日志](test-results-old78-primary-shutdown-events.json)。
