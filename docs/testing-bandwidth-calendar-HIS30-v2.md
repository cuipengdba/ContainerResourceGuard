# HISDBS30纳秒时间戳兼容补测v2

HISDBS30纳秒兼容v2独立补测已完成36/36项、三次不同ID受控启动60.51 / 62.66 / 65.85秒，原300秒业务、45秒缓存及原探针/删除门槛保持；日志追加、逻辑备份、独立恢复和八项原值恢复通过，namespace/三组父叶及106个登记实例独立确认消失。[完整终态与准确原件](test-results-bandwidth-calendar-v2-terminal.json)已归档。与原1129的DBS20/HISDBS20/DBS30三个完成组相结合，[四种组合均有各自完整36项通过](testing-bandwidth-current-combinations.md)，跨独立任务共144项完整组检查；原1129的128通过/1失败/15未执行及1170的9通过/27未执行保持，不把原矩阵改判通过。preview.5程序/八项附件不变；完整600秒/物理备份同步、正式迁移与长期稳定门槛继续。

以下保留原时点记录。

纳秒兼容v2完整HISDBS30补测已唯一启动。节点2026-11-13 17:05:31 UTC快照：7项通过、首次PG/API/受控启动28.23/28.49/60.51秒，内存oom_kill=0；runner/driver的PID/start及全部冻结哈希一致。[准确启动原件](test-start-bandwidth-calendar-HIS30-v2.json)已归档，36项/三次启动等待实际终态。程序仍为已发布preview.5，原1129/1170失败、未执行步骤及旧576端口冲突均保持，原300秒及其它业务门槛不变。

以下保留原时点记录。

旧独立补测1170已失败退出：记录9项且全通过，但读取日志时抛出Invalid isoformat string，27项未执行、仅1/3次启动；不能称36项通过。旧节点Python解析器不接受Go的9位纳秒；先前十项合成回归只使用整秒，未覆盖实际格式。这是验收工具缺陷，程序未因本问题修改。namespace、一组父叶、原runner/driver和31个登记实例独立确认消失，[七份49677字节原件](test-evidence-bandwidth-calendar-v1-terminal.json.gz)及[终态](test-results-bandwidth-calendar-v1-terminal.json)保持。

新任务094edb20c6a328c573ef9454814f1ba39b96e601b2c9ee3faa46b715f859a168，计划ddde6280174c70c5c95872c5fc14357a9b5845a71451877f609f740465b2e25a。固定独立新路径/namespace，源码ced4617、实际preview.5程序字节不变；完整HIS30 36项/三次启动。显式解析1至9位RFC3339Nano，验证真实日历及有效时区，匹配本地日志日期。18项正负回归已在节点Python3.9.21执行，涵盖实际9位纳秒、Z/负时区以及无时区/非法日期/非法精度/非法偏移拒绝。

15项资格保留完整驱动反向还原逐字比较；除了新测试身份与两处日历断言，全部驱动与原1129相同。原300秒业务、45秒缓存、原liveness720秒观察、120秒删除/30秒父叶、64MiB/128标记、逻辑备份及独立恢复、同profile跨ID、八项disable恢复不变。16:58:22原31实例清理及旧576终态51实例检查通过，原1129与1170两次失败不改写。

[冻结计划](test-plan-bandwidth-calendar-HIS30-v2.json)、[资格及真机预检原件](test-results-bandwidth-calendar-v2-preflight.json)、[完整冻结工具](../tests/bandwidth-calendar-nano-rerun-frozen/README.md)。此记录是启动前冻结，不是业务终态；稳定1.0及其它门槛未关闭。
