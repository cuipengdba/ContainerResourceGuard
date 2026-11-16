# DBS/HISDBS新候选原18项复验终态

两组各一次、各全新原600秒的enforce复验已经结束。原9项与辅助2项分别复算，整体是否接受原18项见下表和准确JSON；这不是稳定1.0发布或长稳完成。

|角色|终态|原检查通过/记录|辅助通过/记录|原负载秒|SQL错误|API错误|
|---|---|---:|---:|---:|---:|---:|---:|
|enforce-dbs|passed|9/9|2/2|600.2707152408548|0|0|
|enforce-hisdbs|passed|9/9|2/2|600.2469101999886|0|0|

[逐原件复算结果](test-results-fresh-formal18-v1-terminal.json)、[选定准确原件和原生终态](test-evidence-fresh-formal18-v1-terminal.json.gz)、[15输入启动前冻结](test-plan-fresh-formal18-v1.json)、[准确文本来源](../tests/fresh-formal18-v1/)、[独立复算v2](../tests/fresh-formal18-v1/qualify-selected-originals-v2.py)。选定原件30个/1646028字节逐长度/摘要核验，全部缺失项显式列出；本轮namespace、Pod、父叶cgroup和准确PID/start登记的消失另行确认。每角色新原9项准确名称及独立2项auxiliary-diagnostic标签明确分开，不能以22替代18或漏掉辅助失败。

## 原参数与完整范围保持

CRG产品源37ca44e0/准确ELF未改，原镜像/start.sh/软件与数据路径/只读CCG和缓存enforce不变。外部8核/20GiB，手动7.2核、memory.high20001980416、读写64MiB/s及手动4096IOPS与冻结相同。原600秒、SQL/API零错误/max5秒/p95桶1秒/98%覆盖、备份/同步/独立恢复十项内容及成功原生窗口包围完整周期、真实PG归属全部原标准保留。没有重复运行覆盖失败、资源放宽或PG参数修改。

只读观察器完整覆盖本轮原生窗口，八控制/原PID1/Agent/cache不变；按绑定身份正常停止，最大1800秒/900样本/4MiB。PSI若unavailable仍明确缺失，不冒充压力测试。准确控制、计数、原生错误事件和辅助终态在独立结果及原件保留。

## 元数据和单独exec诊断的边界

复用per-role驱动的旧scope仍写“fixed one-pair…not formal original18 acceptance”，raw formal_original18_acceptance仍false；每个驱动本身不能授予两角色整体18项资格，原字段没有被修改。新复验的独立身份/两个enforce矩阵/原600秒/原18+4由启动前正式plan和coordinator明确。运行时发现的[元数据修正说明](test-results-fresh-formal18-metadata-amendment.json)在独立结论前归档，v2除既有全部业务条件还强制核对原9个名称及另2个辅助标签，整体结论来自新实际结果，不是改写旧报告标签或借用四组对照。[启动前和元数据说明原件](development-fresh-formal18-frozen-v1.zh.md)保留。

单独kubectl exec探针计时包括远程命令/进程启动，原5秒标志完整保留。既有native-campaign规则以成功原生窗口覆盖内容周期，这一规则本轮未改；false不变成true，不据此声称全部请求低于5秒或确定CRG因果。

|角色|单独exec原5秒标志|API最大秒|SQL最大秒|
|---|---|---:|---:|
|enforce-dbs|True|3.8593586299102753|1.2690246689599007|
|enforce-hisdbs|True|1.260540173156187|1.4578655678778887|


## 后续门槛

[前次固定四组对照及两个exec超5秒标志](development-original600-comparison.zh.md)、旧1761 DBS原生失败及unknown原因、旧1396失败和1728为源修复而停止的长测都保留。原来源/已运行时间不能转入本次或后续长稳。

本轮若原18+辅助4全部实际接受，才允许生成新的从零24h observe、同容器24h enforce、新七天计划，之后仍有原老化后故障/恢复/升级/稳定包门槛。[下一次长稳准备程序](../tests/fresh-formal18-v1/prepare-new-zero-clock-long.py)带本轮准确独立结论、18个准确原检查名称、4辅助及CI284的强制前置，归档不代表已经运行、上传或启动。当前新长稳未开始，稳定1.0未接受，preview.5未改，52项定义/18项既有范围声明不增加。产品仍仅CPU/内存/IO各百分比默认20，memory.high、百分比IO仅带宽、纯v2设置/v1跳过、每容器一对一、辅助失败不阻断原启动及每日30天/1GiB日志。
