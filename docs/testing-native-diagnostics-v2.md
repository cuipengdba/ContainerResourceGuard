# 唯一轮次 PG 等待接入 worker 资格

本阶段把[已资格PG等待库](testing-pg-wait.md)接入独立版本的测试worker，同时保留原请求/PG锁诊断。生产Agent、启动链、三项配额与preview.2包不变；旧worker、旧API线程观察器、原压力执行器及全部历史失败没有改写。

[结构结果](test-results-native-diagnostics-v2.json)及[完整证据包](test-evidence/native324-334-v2-qualification.json.gz)保留三轮实际资格，包括前两轮失败、最终通过、独立清理复查、15份固定源码版本和两次仅内存加载的只读诊断结果。节点协调报告及独立收据保留原始字节与摘要；容器报告为协调器解析后的结构，不声称保留其原文件字节。

## 最终实际结果

| 环境 | 范围 | 结果 |
|---|---|---|
| 宿主Python3.9.21 | 真实探测线程配合明确替身：初始化/采集异常、缺失、连接关闭、容量、源码与模块生命周期 | 15项通过 |
| DBS原镜像Python2.7.5 | 同一资格源码 | 15项通过 |
| HISDBS原镜像Python2.7.5 | 同一资格源码 | 15项通过 |
| DBS原镜像/PG二进制，新emptyDir空库 | 12秒正常、16秒受控锁、12秒缺少PG采集授权标记 | 26项通过 |
| HISDBS原镜像/PG二进制，新emptyDir空库 | 同上 | 26项通过 |

最终97项全部通过、资格执行器exit0。两空库均采用实际`/opt/postgresql/pgdata`，非root、drop ALL、只读根文件系统，无服务账号令牌；原库和产品目录没有挂载。PG bin/lib/share只读，PG数据1GiB和输出64MiB为本轮临时emptyDir。mock HTTP只返回固定测试响应，不能冒称DBS原API通过。原32项、两角色各600秒、64MiB和11重载/压力区间仍未重跑。

正常场景原SQL/API门槛通过，PG等待快照绑定本轮标记和真实后端/proc身份。受控场景只锁本次新schema表8秒，原5秒SQL截止产生预期错误，worker保持失败退出；诊断保留真实Lock及blocking PID，并关联到请求后端。资格通过不意味着受控SQL失败被豁免，也不关闭旧业务失败。缺少PG采集授权标记的场景中，PG采集明确失败、最终diagnostic_complete=false，但原SQL/API、完整性、原进程及时长检查仍通过，worker正常完成。三场景均核对请求计数、报告摘要/8MiB边界、探测线程退出和观察线程CPU总和不超过5%单核；这是12/16秒短资格，不是600/900秒开销验收。

## 前两轮失败及修复

前两轮均在DBS正常场景的第3项诊断完整性检查失败并exit1，没有进入HISDBS。宿主和DBS各14项替身检查通过；原短SQL/API业务通过，但所有PG等待样本初始化失败，不能因此声称接入成功。第二轮加入经过过滤的异常类别、数字errno及固定源码文件/行号，仍按同一完整性断言失败。两轮实际结果、源码和清理证据保留，没有覆盖成最终成功。

仅内存加载的Python2.7只读复现显示：直接持有模块时授权标记缺失产生正确Rejected；经过工厂表达式构造时，却得到NoneType没有environ的AttributeError。原因是Python2释放临时ModuleType会清空其全局字典；只保存其中的类/函数不足以保证模块存活。该机制与[CPython 2.7.5 module_dealloc/_PyModule_Clear源码](https://github.com/python/cpython/blob/v2.7.5/Objects/moduleobject.c#L159)一致。修复在构造期间保留局部模块引用，并由采样器持有该模块直到采样器释放。新增回归检查在构造后执行gc.collect再调用方法；真实缺少标记检查也要求错误确为Rejected，避免把其他初始化缺陷误当成预期拒绝。最后两个原镜像三场景均实际通过，证实修复适用于原Python2环境。原已资格PG库没有修改。

两次只读复现只在原有隔离测试Pod内启动短暂Python进程，用内存映射代替源码文件读取，不连接数据库、不写源码或数据文件；Pod UID及容器状态保持。它们不是额外长期业务轮次。三轮资格父进程和实际创建的Pod/cgroup/namespace均由独立SSH复查退出；原只读PG组件摘要保持。

## 接入设计

[新版worker](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-soak-load-diagnostics-v2.py)与固定旧worker的AST差异严格只有helper文件名、helper摘要及客户端应用名。应用名为crg-disposable-soak加轮次后缀；原64MiB载荷、请求周期、SQL/API截止、零错误及延迟标准没有修改。

[新版诊断](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/vendor-native-diagnostics-v2.py)复用摘要固定的旧请求记录器，在同一独立只读连接上先取得原PG锁样本，再取得已资格PG等待快照。两者有各自时间区间，PG backend_start另保留精确文本；不把不同读取拼成原子或IO因果证明。PG采集失败只关闭诊断自己的连接，继续原请求；可选内核字段不可读仍保留unknown。采样最多901次、单样本16KiB、最终报告8MiB，容量超限仅停止探测线程，不设置原工作负载停止事件。初始化或采集失败对完整诊断的否决保持可见；不重试、取消或延长原请求。

下一步将本worker及[已资格设备/线程并行会话](testing-device-sessions.md)接入新版本完整压力执行器；固定本阶段源码和资格结果，保持旧执行器及全部历史原件。只有新的原32项、两个角色各600秒、原配额/载荷/11区间和SQL/API门槛实际满足，才能声明该业务门槛通过。七天原handle、正式24h及后置、ARM厂商业务/独立物理多盘、52任务和稳定版条件继续，未测保持未测。
