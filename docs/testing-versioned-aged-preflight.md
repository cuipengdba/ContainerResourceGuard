# 版本化候选实际老化数据的只读门禁

新程序dbc48aa5的R78实际七天有自己独立的[固定计划](test-plan-versioned-aged-postflight.json)和只读采集/门禁，不复用旧3a1/R57的谱系或计时。[实际记录](test-results-versioned-aged-preflight.json)包括Linux8项自检、真实采集和提前执行返回pending；不构成七天通过，也没有实现本轮后置执行器。

程序复用但不修改原b82只读核心与4feb报告核验器，先核对源码摘要。新适配器固定R78计划/作业/程序/内嵌版本/路径/run_id及原门槛；不接受其他容器目标。[源代码](https://github.com/cuipengdba/ContainerResourceGuard/blob/f669f9fd73165b8cff61d332880dccc988a46180/tests/vendor-versioned-aged-preflight.py)和[回归检查](https://github.com/cuipengdba/ContainerResourceGuard/blob/f669f9fd73165b8cff61d332880dccc988a46180/tests/vendor-versioned-aged-preflight-checks.py)随本轮归档。

采集时确认原运行器的PID/启动ticks/精确入口仍在线、两原生worker测量中、每容器唯一正确程序Agent/缓存/负载、实际八项控制和原journal身份。两角色分别封存七个真实目录inode、八个输入文件摘要、每日0600日志前缀、原生起点及PG起点；完整seal仅在私有测试工具目录保存0600。工具本身只读和stdout输出；协调入口才保存私有证据，不修改资源/业务数据，不复制活动PG数据目录。

只有真实604800秒/28周期、原生SQL/API及所有内容/覆盖标准完整通过、外层11项、运行器退出0、原namespace及cgroup消失后，才检查同一老化目录/输入/journal/日志前缀与至少七份每日日志，并确认后置目标全新。当前真实提前执行返回exit2/pending、原运行器身份在线，后置工作目录和namespace均未创建。此门禁只允许下一步，不宣称后置已执行、P10或稳定发布通过。

首次真实采集被拒绝：适配器把只在终态存在的workload字段用于运行中报告。[原冻结计划](test-plan-versioned-aged-postflight-initial.json)、[原适配器文本](fixtures/vendor-versioned-aged-preflight.py.initial.txt)、[原检查文本](fixtures/vendor-versioned-aged-preflight-checks.py.initial.txt)及失败结果保留。修正按实际运行中报告结构读取固定原生文件，并新增真实结构、错误run_id/phase/PG起点反例；没有放宽任何时长、资源、错误数或清理标准，没有停止或重启七天进程。

本轮Windows8项中1项POSIX绝对路径跳过，Linux8项全部运行通过。合成测试与真实采集分列；后续还需本程序自己的备份/独立恢复、新ID重建、升级/回退和辅助故障执行绑定，以及所有原稳定版条件。
