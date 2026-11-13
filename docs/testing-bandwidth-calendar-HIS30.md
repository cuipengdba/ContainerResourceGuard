# 独立HISDBS30完整补测计划

最新终态：独立HIS30补测1170在9项通过后因旧节点Python不接受9位纳秒而退出，27项未执行；31登记实例及namespace/父叶独立清理。原报告保留。[纳秒兼容v2完整补测](testing-bandwidth-calendar-HIS30-v2.md)已另行冻结，18项真实纳秒正负回归在节点通过，15项预检通过；同一发布程序、原业务门槛不变，尚未接受为业务通过。

以下保留原时点记录。

独立HISDBS30补测已经唯一启动，节点16:49:01快照为7项通过、首次PG/API/受控就绪29.35/29.62/59.25秒，尚待两次冷重建、备份/独立恢复及原探针；[启动原件](test-start-bandwidth-calendar-HIS30.json)记录准确PID/start及全部冻结哈希，不能算36项终态。旧preview.4七天任务中断的直接原因也已从PID295208的CSV确认：23:56:21备用库无法绑定127.0.0.1:55432（Address already in use），随后FATAL无法创建TCP套接字；[两份1380字节准确原件](test-evidence-memory-high-seven-day-port-conflict.json.gz)及[分析](test-results-memory-high-seven-day-port-conflict.json)已归档。当时端口占用者未捕获，不推断资源限制因果，旧任务仍为失败。

以下按原时点保留。

任务4d932a57b2dd9c0af045e11cfac2187f9856edf7db462a61640b74edf56b31a4；计划1548f836ae7478a59ccc0860cba69b5714f04868dbcb0cb191518ad6be8795b1。本记录为启动前冻结状态，不是业务通过。

[原129项记录/128通过/1失败/15未执行](testing-bandwidth-percent-terminal.md)和原报告保持。只修正验收脚本跨日期的两处追加断言，使用同一个preview.5程序独立跑HISDBS30完整36项/三次启动；CPU/IO/内存30%、自动最大合格文件系统三样本标定、同profile跨ID、64MiB/128标记、逻辑备份/独立恢复及disable恢复全部保留。原300秒PG/API/managed、45秒缓存、原liveness720秒观察、120秒删除/30秒父叶消失门槛不改。

15项结构/原件重放/真机预检通过，其中完整驱动反向还原后与旧文件逐字符相等，差异仅新测试身份与两处日历日志断言；十项正负日历/源码/历史完整性回归已在Linux实际执行。真实Nov13/14日志重放证明新断言允许已关闭日期不增长，同时要求新Agent追加，原断言确会拒绝该有效记录。此重放不是把缺少的业务步骤算通过。

预检节点16:40:05确认旧矩阵369登记实例及四namespace已清理；旧576已失败退出，51个初始实例清理与原准确报告再核对。原活跃长任务等待门槛仅归档，改为终态检查；不继承旧七天时间，不证明独占24h。新工具、路径、job/plan及版本均独立，冻结后不在原任务中热修。

[冻结计划](test-plan-bandwidth-calendar-HIS30.json)、[15项资格及真机原件](test-results-bandwidth-calendar-preflight.json)、[完整冻结工具](../tests/bandwidth-calendar-rerun-frozen/README.md)。[preview.5发布后验收说明更新](test-results-preview5-terminal-followup.json)已观察到，八项附件及标签不变。业务结果待实际执行，原52项/稳定1.0不据此关闭。
