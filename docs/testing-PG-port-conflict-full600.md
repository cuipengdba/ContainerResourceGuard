# 真实PG端口冲突与新执行器完整600秒：冻结计划

14项结构及节点只读预检通过，计划44项，尚未启动。本轮使用实际公开preview.5程序，产品源码`ced461705ebc27315a59aefe463f9b4af47130a3`不变。job `ea766b49dde53e62daa9a9490168150f9d636efa6061dc8cbb4715177b7570bd`，plan `281a02f8ce0b3af70bc1db09d46a4779c8caec991dec7cf864db6186b110931f`。新的engine/campaign和两诊断模块全部固定摘要并复制到实际执行目录；此前28结构/14Pod资格不是本轮实际PG或业务结果。

## 四个顺序独立克隆

先conflict-DBS、conflict-HISDBS，各13项；再normal-DBS、normal-HISDBS，各9项，共44项。每次新namespace/Pod/container ID和私有数据目录，原镜像、真实挂载路径、原启动链和只读CCG共存，每容器一份Agent。前一夹具进程、namespace、父叶cgroup确认消失才创建下一套；两个冲突组都通过限定资格后才启动正常组，不重试覆盖失败。

冲突组在本轮已确认隔离的容器内部启动唯一Python子进程，显式监听127.0.0.1:55432；先验证实际inode拥有者PID/start及本cgroup。随后执行真实PG物理备份与临时standby启动，要求引擎原样失败，错误指向standby-start.txt，原PG日志出现bind/address-in-use。失败及cleanup采集仍须识别同一占用者，原primary/Agent/cache不变，原API可访问；仅显式本轮管道EOF结束占用者，控制值/配置保持。engine自身phase=failed、退出非零和原日志完整保留；上层expected-failure资格不冒充业务通过。

正常组使用另一套全新私有目录和Pod，保留原7项启动及原完整600秒业务检查，另各增加1项真实PG拥有者/启动停止清理诊断。原native每角色600秒、SQL/API零错、最大5秒、p95桶不超过1秒、至少98%覆盖、64MiB内容/校验、物理备份/同步/独立恢复和原10引擎检查保持；内容周期必须全部位于成功native窗口。实际PG的standby55432、restore55433拥有者需与本cgroup及对应cwd一致，最终临时监听消失。partial/unknown原样保留，不能把诊断缺失当成功。

## 固定预算与门槛

采用此前已单独声明的manual参考预算：CPU7.2核、memory.high20001980416B、读写各64MiB/s及手动IOPS4096；Kubernetes外部8CPU/20GiB硬上限保持。没有新memory.max写入、自动标定或默认值修改。原启动300秒、缓存就绪后45秒、pg_ctl启动60/stop30秒、原外层超时和所有SLA保持。默认20%完整业务失败仍保留，不能用本轮manual结果改判。

节点预检内存38575869952B、磁盘65458835456B，满足启动28GiB/稳态8GiB和磁盘20GiB门槛。此前manual业务、公开维护、百分比迁移及诊断任务的原runner/driver/namespace/父叶/登记进程在节点重新只读核对终结且清理；新四namespace不存在。输入程序buildinfo和全部12份上传文件摘要核对，私有supervisor/CCG保持。未创建业务夹具。

[冻结计划](test-plan-PG-port-conflict-full600.json)、[14项资格](test-results-PG-port-conflict-full600-preflight.json)、[可逆驱动改动](test-adapter-PG-port-conflict-full600.json)、[完整冻结驱动](../tests/PG-port-conflict-full600-frozen/business-driver.py)、[协调器](../tests/PG-port-conflict-full600-frozen/runner.py)。公开源码不包含程序二进制；其摘要绑定实际已发布包，不替换附件。只导出明确白名单报告/日志/config/status/journal/native/engine，逐项原始字节索引，不导出私有Pod/env/数据库配置凭据。

共享amd64/Linux5.14单设备范围，不声称独占、ARM厂商真机、多物理设备、24h+24h或新七天。本轮失败全部保留，原52任务和长期门槛继续，稳定1.0未接受。
