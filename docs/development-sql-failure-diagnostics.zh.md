# DBS SQL失败诊断：开发记录与后续隔离验收

最新状态：[原DBS/HISDBS路径受控诊断各13/13通过，准确原件复算及归属清理完成](development-controlled-sql-wait.zh.md)。这是120秒负向诊断，原1761原因与正常600秒/发布门槛不变。

## 当前结论

v4终态：两个准确原镜像Python2.7各6/6兼容性检查通过，真实libpq空loopback连接失败分类正确、namespace/父组清理和全部输入未变；[结果](test-results-original-image-diagnostics-v4.json)、[原件](test-evidence-original-image-diagnostics-v4.json.gz)。未启动PG/原业务、未访问业务数据库；仍非原600秒或因果验收。后文各“尚未启动”均为对应冻结前历史状态。

为隔离验收负载完成有界SQL/API失败诊断，Windows及测试机原生amd64/Linux5.14各26/26项故障测试通过。此变更属于测试程序，不改变CRG生产源37ca44e0e24a0eaa14e52b5c8bbbda54c76364b0，也未部署到现有业务容器。原1761 DBS SQL一次错误/max5.004658635秒仍失败，原因未知，原异常明细已丢失；HISDBS9/9与本轮整体失败分别保持。

[诊断工作线程及校验器](../tests/bounded-load-diagnostics-v1/)、[准确来源适配证明](../tests/bounded-load-diagnostics-v1/adapter.json)、[独立结果](test-results-bounded-load-diagnostics.json)、[原生回执及故障验证证据](test-evidence-bounded-load-diagnostics.json.gz)。旧原件[继续保留](testing-live-capacity-native-and-business-current.md)，新诊断不能事后还原旧请求，也不能据一次失败认定资源控制是原因。

## 已实现的需求与边界

每个失败记录SQL/API、该类请求序号、UTC记录时刻、请求起止单调时钟和耗时、连接/查询/结果/HTTP阶段、固定错误类别及固定原因。区分正常返回但超过5秒、返回内容不符、连接轮询失败、SQL发送/刷新/输入/服务端/就绪或结果等待超时等。未知异常仅记固定unknown类别，不收集任意异常文本、SQL文本/结果、连接数据、HTTP内容、环境变量或凭据。

最多保留首128条失败，紧凑ASCII JSON事件累计不超过65536字节，超出只累加丢弃计数；采集异常单独计数。所有采样统计继续先按原方程计数，诊断失败不能把业务失败改为成功或让采样线程因此退出。按原锁串行更新，不新增文件写入、网络请求或额外SQL；仅随原有load.json每300秒及终态快照写出。整个带缩进报告不是64KiB硬限额，64KiB是事件紧凑表示的累计字节限额；验证128事件的完整诊断对象小于100000字节。

保留原SQL、2秒/5秒采样、libpq及HTTP超时、最大5秒/零错误/p95桶1秒/98%覆盖、原准备/校验和/600秒、备份窗口和清理行为。旧原始工作线程一字未改；独立分支工作线程只更改sample/sql_load/api_load三函数，并增加诊断常量/辅助函数。校验器在两平台都对原始文件摘要、其他全部函数/类AST和准备段/完整main原字节比较。

原报告save()一字未改。若原报告介质无空间或无写权限，持久化仍可能失败；验证证明先前完整原子文件保留且采样计数不被改写，不宣称不可写介质仍能保存诊断。日志30天/1GiB及一天一文件是CRG现有产品要求，本测试诊断不替代或更改它。

26项覆盖统计边界等价、全部固定SQL原因、正常/慢成功/不符、恶意异常字符串及超长敏感输入、双线程2000错误下的数量/字节上限、序列化/时钟失败、禁止采样文件I/O、SQL连接/查询失败和关闭、API超时/坏JSON/关闭、真实原子快照及权限/磁盘满故障。首次Windows25/26因权限测试未定义root而NameError，原失败及校验器身份保留；补充临时根目录后原权限断言继续执行。产品线程未因该夹具缺陷修改。

原生测试只在新的私有诊断目录执行精选实际函数并注入故障，没有数据库访问、业务Pod创建或资源写入。不是Python2执行资格、厂商业务性能、ARM厂商资格、两独立物理盘、长稳或稳定版验收。

## 后续开发与测试任务

归入原P02.1/P02.2/P10.2/P10.3子任务，仍保留52项定义和18项原范围完成声明。

1. 在新隔离身份上冻结诊断工作线程、准确ELF、原镜像/路径/手动预算与全部输入，不能覆盖1761原件。先验证诊断在原镜像Python环境可执行，并对仅本轮合成schema施加可控锁等待，检验真实libpq超时分类；负向故障须记录为预期失败，不能计入正常18项通过。
2. 增加有界只读时间线并独立验证归属、超时和清理：关联请求事件、物理备份周期、容器CPU节流/IO与内存压力、必要的本轮测试后端等待状态。禁止任意SQL/连接/凭据导出及修改业务配置。该观察器尚未开发，不能宣称原失败已定位。
3. 预先冻结对照设计：同镜像/路径/数据规模/外部上限/缓存程序的observe与enforce新实例，明确顺序、窗口和固定次数，保留全部结果和共享节点压力。observe诊断对照与正式managed九项分开核对，不能把某次通过抵消1761失败；不得重复到绿灯或静默改变7.2核/high20001980416B/64MiB每秒/手动4096IOPS及原SLA。
4. 定位并处理问题后，对准确候选执行两角色原18项、各完整600秒及完整物理备份/同步/独立恢复；独立检查原件和归属清理。若新诊断显示的是不同失败，分别记录原因，不强行合并。
5. 全部门槛满足后从零开始24h observe、同容器24h enforce、新七天及原老化后故障/恢复/升级/稳定包验收。已有旧源/失败/显式停止时钟不继承。稳定v1.0.0仍未发布；preview.5身份/资产不变。

以上第1—5项尚未完成；本轮没有新业务/长稳任务在后台运行。用户最新范围仍为CPU/内存/IO独立百分比、默认各20%，memory.high保留外部硬上限、IO百分比仅带宽/IOPS手动、纯v2设置/v1明确跳过、每容器一对一、无权限不阻断原启动及既定日志保留。

已冻结[原镜像兼容性计划](test-plan-original-image-diagnostics.json)与[Python2/3镜像校验器](../tests/bounded-load-diagnostics-v1/image-check.py)，计划在新的只读Pod检验完整工作线程语法、AST、诊断及真实libpq连接失败；不启动PostgreSQL或原业务启动链，不挂载业务数据，不执行正常600秒；此计划尚未执行。

## 原镜像首轮失败与v2修正计划

冻结后在两个准确原镜像均出现校验器NameError：AST提取误选了main末尾的report赋值，访问尚未定义的interrupted。尚未完成六项检查，不能宣称镜像兼容；两个Pod终态失败、namespace及父cgroup均独立确认消失，冻结输入未改。[完整失败及清理](test-results-original-image-diagnostics-first-failure.json)、[准确回执](test-evidence-original-image-diagnostics-first-failure.json.gz)保留。

先前两个发布/准入问题也保留：Git换行规范化改变adapter元数据摘要，远端逐文件校验失败阻止启动；现通过仅该路径的属性规则保留与原生回执绑定的CRLF字节。首次镜像准入没识别CRI给本地短标签增加docker.io/，在工具目录或Pod创建前失败；按实际同一镜像ID和准确规范标签修正。均未改产品或工作线程、标准、预算。

已证明v2 AST只选中一个report['failure_diagnostics']赋值，保留原六项与冻结工作线程。[新身份v2冻结计划](test-plan-original-image-diagnostics-v2.json)、[v2校验器](../tests/bounded-load-diagnostics-v1/image-check-v2.py)在第二轮前发布，首轮工具目录/输入和结果不覆盖。v2目前尚未启动；新正常业务600秒、受控锁等待、时间线/对照与长稳仍未开始。

## v2镜像依赖缺口与v3冻结

v2完成Python2编译/AST/固定分类/隐私检查后在加载libpq处失败，两镜像均没有裸路径/opt/postgresql/pgsql/lib/libpq.so.5；实际部署是在/opt/postgresql挂载路径中生成PG软件。故本轮仍不是六项通过。[完整v2终态](test-results-original-image-diagnostics-v2-failure.json)与[原件](test-evidence-original-image-diagnostics-v2-failure.json.gz)保留，两个Pod/namespace/父组已清理，工作线程未变。

已只读核对1761原隔离夹具的PG客户端软件：两角色准确libpq.so.5.14均为345576字节，SHA256 a0f6cc8fb39a6f84a150c2b423cc17da8766c06923b1722fbea224579c11fd89，依赖原镜像现有libssl.so.10/libcrypto.so.10等。[v3新身份计划](test-plan-original-image-diagnostics-v3.json)保留原六项，另将这一准确库文件只读挂到原libpq路径；不挂载数据库数据或配置，不启动原业务/PG。节点及镜像内都先校验该软件摘要，[v3校验器](../tests/bounded-load-diagnostics-v1/image-check-v3.py)没有改变工作线程或六项标准。此为补齐测试软件路径，非放宽业务SLA。v3尚未启动；结果不替代原600秒/受控锁/因果对照及稳定发布门槛。

## v3准入拒绝及v4实际软件归属

v3在创建工具目录或Pod前拒绝：校验器计划错误假定PG客户端文件归root；独立只读stat证明既有本轮隔离软件归数据库UID999/GID998、0755、单链接规则文件，摘要及345576字节相符。[原拒绝与stat回执](test-evidence-original-image-diagnostics-v3-admission.json.gz)保留；无v3 Pod执行，不计任何通过。

[v4新身份计划](test-plan-original-image-diagnostics-v4.json)绑定实际UID/GID/mode及原SHA，保留准确路径、规则单链接、只读单文件挂载与六项检查。未chmod/chown原文件，不更改工作线程或镜像。v4尚未启动，前两轮失败及v3拒绝不改写。补齐软件夹具仍不是原启动链或正常600秒业务验收。

## 当前后续任务

两平台26项故障验证与原镜像Python2.7两角色各6项兼容检查已完成。原工作线程三函数之外保持原字节/AST，CRG产品源和所有外部资源预算未变。v4只是只读原镜像加准确PG客户端单文件的代码/连接失败兼容资格，未执行正常600秒、真实SQL锁等待、原启动链或备份。原1761 DBS一次SQL失败原因仍未知，HISDBS9/9及整体失败原件保持；所有测试Pod及namespace已清理，当前无新增业务/长稳任务。

下一步实现并验证有界只读压力/等待时间线，在新隔离身份进行仅本轮合成schema的受控SQL锁超时诊断，然后按预先冻结的observe/enforce对照定位问题；问题闭环后才重做原18项和两角色各600秒。原52项定义/18项完成声明、24h+24h/七天/老化后验收和最终稳定包门槛全部保留，不以兼容性替代。
