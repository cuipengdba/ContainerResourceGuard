# 新容量刷新候选：DBS/HISDBS原路径600秒重新验收

当前更新：原节点UTC2026-11-15T20:59:51Z已单次启动，新runner3165983/start171633500。DBS21:06:26Z约300秒快照SQL1错误/max5.004658635s，API0错误，原600秒及两角色协议继续至终态并按原清理；不能算业务通过。工作线程未保存这次异常明细，具体原因未确认。[带日期原生负载快照](test-results-live-capacity-business-live.json)。下文“未启动”为冻结/预检时点。

源37ca44e0e24a0eaa14e52b5c8bbbda54c76364b0，AMD64静态ELF ee4f0a140dd7fc1b0435298cd7ee673eedb0eaea6be9f79971d565f5f181308c。当前为已上传、原生预检ready、未启动；不得将预检当业务通过。

[精确计划](test-plan-live-capacity-business600.json)、[可逆适配及原条件核对](test-plan-live-capacity-business-adapter.json)、[原生预检](test-results-live-capacity-business-preflight.json)。13项输入均核验摘要，旧1728原进程/namespace/cgroup清理再次确认，无其它业务验收夹具运行。节点Ready且三类Pressure为False、可用磁盘约144.6GB；保留原28GiB可用内存启动、8GiB持续内存和20GiB磁盘储备条件。

与旧1366程序逐字可逆比较：仅改变独立测试目录、namespace、guard与日期标识，候选ELF及其来源；原18项/两角色各600秒、manual参考7.2核、memory.high20001980416B和64MiB/s/4096IOPS、原start.sh、同容器挂载、CCG只读、SQL+/test、完整物理备份/同步/独立恢复、PG端口所有者及内容/SLA门槛、删除时限与归属清理均未改变。manual参考通过不代表任意默认20%配置业务性能。

[完整冻结测试输入](../tests/live-capacity-business-v1/)只适用于授权的隔离测试节点，不能在生产直接运行。两个角色顺序执行；前一个namespace、leaf/父组和全部登记进程清理未证明，就不启动下一个。测试用独立目录和namespace，不改现有业务部署，不替换原图像、数据库配置或启动文件。

本次必须以新ELF得到独立结果，不继承旧ced候选18项/600秒或旧1728时钟；不启动长稳计时。成功后仍须完整新原生矩阵、后续24h+24h+7天及老化/最终发布门槛；稳定1.0.0尚未接受。既有原52项定义/18完成声明及所有失败保留。
