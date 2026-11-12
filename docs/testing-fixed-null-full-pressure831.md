# 修复null预检后的完整压力结果

用户选定的内存策略继续为 `memory.high`，不下发新的 `memory.max`；Kubernetes/运行时已有硬上限保留。CPU、内存、IO各自百分比、各默认20%，每容器一个Agent，无权限时记录并继续原启动，v1不写控制值，每日日志/30天/1GB策略均保持。产品及[preview.4发布附件](releases/v1.0.0-preview.4.md)未改变。

## 实际业务范围

[结果](test-results-fixed-null-full-pressure831.json)、[完整原件](test-evidence/fixed-null-full-pressure831.json.gz)和[精确冻结源码](../tests/full-pressure-diagnostics-fixed-frozen-v2/full-pressure-integration.py)归档。本轮先在实际Linux运行Go单元、17个工厂用例和12个原件传输用例，随后在97节点的新隔离DBS/HISDBS副本执行原启动链、每角色600秒、全部11个配置/压力/释放区间及原32项业务检查；标准、配额、64MiB负载、SQL/API期限、覆盖率和零错误要求未改。

本轮32项业务检查全部通过，两角色SQL/API均零错误，显式disable恢复和同一业务/Agent身份等后置检查也完成。它仅证明本轮指定负载通过，不能证明默认20%全部业务、消除历史超时或完成七天/稳定版验收。上轮实际DBS API两次超时和[原诊断启动TypeError](testing-full-pressure-diagnostic-integration.md)均保留，未重评。

| 角色 | 原业务秒 | SQL/API错误 | BPF事件 | 函数配对 | 配对问题 | 最长日志write ns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| v10-dbs-bw64 | 600.456242 | 0/0 | 17386 | 6491 | 12 | 770691 |
| v10-hisdbs-bw64 | 600.284526 | 0/0 | 15450 | 5768 | 0 | 569374 |

## 诊断资格仍失败

实际40 hooks/5 maps已分别挂接，null字段投影不再失败；完整报告分别为7333871字节及6534584字节，均在原32MiB上界内，terminal确认完整写入、sync与close成功。两角色perf丢失和BPF输出失败均0，scope错误/残留均0，前后实测perf映射均3244032字节、预算上界16MiB。该预算只约束perf mmap，不是诊断器整体RSS上限；MaxRSS为序列化前观测值，诊断器CPU开销不属于容器Agent的既有开销资格。

DBS仍有12条函数配对问题（3次不匹配及9次后续孤立返回），incomplete为true，七阶段完整性失败；HISDBS无配对问题、incomplete为false，阶段计时检查通过。两角色请求注解均为0/121，完整请求端口关联失败。独立离线25项检查实际17项通过，诊断资格整体未通过，不能以业务32项通过抵消。

原件显示，DBS三次不匹配返回时间为1461576794458198, 1461576805624566, 1461576805871375，均早于就绪时间1461576815035259。按函数分别核对，__iomap_write_begin为596次进入、593次返回，其他已观测函数进入/返回计数相等。当前源码在安装全部hooks前已向target map填入目标，这与安装期间形成部分调用帧相符；具体修复须先经过受控复现。原12条问题、就绪前事件和严格配对结论全部保留，未删除事件或把缺失返回补造为成功。

请求注解缺失还需验证实际解释器启动链。CPython2.7.5的[main.c](https://github.com/python/cpython/blob/v2.7.5/Modules/main.c)先调用Py_Initialize，后调用PySys_SetArgv；[pythonrun.c](https://github.com/python/cpython/blob/v2.7.5/Python/pythonrun.c)在初始化期间导入site。这支持“sitecustomize过早读取sys.argv可能退出激活”的推断，尚需原镜像启动复现和回归。旧九个传输用例覆盖安装后行为和非阻塞FIFO，但没有覆盖真实解释器自动加载阶段，不能把其通过扩展为自动激活已验证。

本轮最长日志write不足1ms，未复现历史数秒长write/API超时，不能给出历史内核等待根因或产品性能修复结论。诊断的响应头完成仍不能替代原native完整响应结果；迟到同端口事件也不能单独证明同一socket或因果关系。

## 结束与后续

同一任务自然结束后，57个记录的原进程实例、90个BPF对象、namespace和两角色叶/父cgroup均独立核对消失。33份原件共41839701字节，经真实SFTP逐份核对长度、EOF、SHA256后下载，完整UTF-8字节归档。观察、下载与只读分析未重启任务或热改冻结文件。

下一步先独立复现和修复采集就绪前的目标激活边界、原镜像Python2自动加载及stdout注解通道，再按原自有资格和故障条件验证；不放宽事件20000、报告32MiB、perf16MiB、四秒socket或业务零错误标准。实际默认20%业务、正式24小时、真实memory.high七天604800秒/28周期及老化后置、ARM64业务/指定内核/多独立块设备和已发布次版本迁移等条件继续开放，52项原任务定义和未完成声明保持。稳定1.0未接受。
