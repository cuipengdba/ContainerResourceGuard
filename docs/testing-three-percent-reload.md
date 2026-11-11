# 三项百分比持续热重载实测

2026-11-10，针对R29/R30后的未发布组合线。程序源码`d6ea6572dc423397ca496a5277d2af4496c6970c`，Linux amd64二进制SHA256 `0a0799f5c992b8b4ddb983bec12a8061965a4fbed4c419d47cd7c7607dbecf15`。[完整15项结果](test-results-three-percent-reload.json)。测试结束后自有Pod及namespace核对已删除，原持续基线未修改。

同一Agent持续运行，使用当前设备的有效持久profile；修改配置不重启业务或Agent。15项检查全部通过：

1. 首次CPU25（CLI覆盖文件10）、内存20、IO30，代次1，其他五项资源未改。
2. 配置CPU35/内存25/IO40后，CPU仍CLI25，内存及IO按新值，代次2。
3. IO101坏配置拒绝，上一整份策略、代次和内核值保留；状态降级明确说明。
4. 修复为只填IO50：内存独立回默认20、CPU仍25，恢复accepted，代次3。
5. 省略全部资源字段：内存和IO各20，CPU CLI25，代次4。
6. 上述Agent/PID1身份保持；CLI日志目录跨文件中log_dir变更保持优先，未创建被覆盖的目录。
7. profile内容和mtime保持，无重复标定；停用持续Agent恢复三项真正原值。
8. 重新启动manual仅CPU1核/内存1GiB，确认只接管显式两项；随后同一Agent切三百分比，使用已有profile增加IO。
9. 改manual仅CPU，先前接管的内存和IO恢复原值，不写max冒充原值。
10. 夹具外部将自己的CPU配额改为0.5核：Agent报告conflict且不覆盖；disable返回未完整恢复并保留外部CPU值，其他资源仍符合原值。
11. 全程PID1保持且OOM kill为0；额外资源控制均未变化。

新增文件监测回归覆盖CLI比例/日志优先、坏配置保持hash/代次、未填回20、manual与CLI比例混用拒绝。该回归补充旧单percent测试，不改变以上实测程序的运行时代码。

本轮不是原DBS/HISDBS业务/性能验收，也没有证明从manual启动且缺profile时热重载会自动标定。该场景当前会明确IO降级，需要受控重启辅助Agent以进入首次自动标定流程；业务独立运行。该行为在[1.0契约草案](https://github.com/cuipengdba/ContainerResourceGuard/blob/7787ffb0abacf2616fb46905457b260da5282ab3/docs/compatibility-contract.md)中列明。


2026-11-11补充：已发布候选自身另做[15项新ELF工程重载补测](testing-versioned-candidate-reload.md)，来源与旧d6结果分开；旧报告保持。
