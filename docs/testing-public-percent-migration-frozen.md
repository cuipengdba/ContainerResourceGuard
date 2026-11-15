# 公开程序默认百分比迁移：冻结与预检

实际公开preview.4→preview.5，源码/程序不变。job `eb067f58a193e22740938ffdd6cea9e9a86d45fbab54d168bb1ff98de9f1d537`，plan `e01b628b45cf910fc64f825bc9ae868149e49d6e5c569340b3cf70d0608ba781`。15项结构与真机预检通过，尚未启动迁移测试，不是48项通过。先前20项历史快照回放仅用于断言资格，另补合法格式下仅IOPS值错误的负例，原回放保留。

DBS/HISDBS各两个顺序创建的不同Pod/container ID，复用各自原镜像、真实挂载路径和私有持久目录。全程业务gate关闭，原业务及缓存helper不启动；测试只验证控制层迁移，不声称SQL/API性能或原300秒启动。每容器只运行本容器程序，CLI run --once前后没有其他写者。

固定空配置{}，三个百分比各默认20。旧4真实自动选盘/三样本标定，真实写四轴IO journal；quiesce→新5按明确摘要原子安装→enable/run，核对BPS换算及旧CRG自有IOPS恢复基线。disable核对八项runtime原值后再次run，保留active journal删除本Pod。第二Pod仍挂载同一目录，在已核实自身leaf建立外部IOPS197/149基线；新5应识别新身份、归档旧active journal、复用profile并保留外部IOPS，disable恢复当前基线。不得人工构造或修改profile/journal。

每角色24项、共48项record检查点，原额度/新runtime原值、设备身份、日志前缀、profile字节及mtime、PID1不变、独立清理均按冻结断言。CPU/MemTotal/页大小由宿主可信来源读取并独立换算，祖先约束在测试前确认；不是从产品计划反推预期。上一维护任务40/40及61登记记录/59去重实例、两namespace/父叶消失为硬前置；节点预检内存38497116160B、磁盘66023227392B，满足28GiB/20GiB。脚本有界900秒等待业务gate，与业务启动SLA无关。任何失败原样保留，不调额或重试覆盖。

[完整计划](test-plan-public-percent-migration.json)、[15项资格](test-results-public-percent-migration-preflight.json)、[补充负例回放](test-results-public-percent-migration-clean-negative.json)、[冻结驱动](../tests/public-percent-migration-frozen/percent-driver.py)、[协调器](../tests/public-percent-migration-frozen/runner.py)、[只读断言](../tests/public-percent-migration-frozen/tests/percent-contract.py)、[原设计](testing-public-percent-migration-design.md)。二进制从准确公开包取用，计划绑定全部哈希；不提交到仓库。原default20业务失败、52项任务、24h+24h/7天及未测硬件范围保持，稳定1.0未接受。
