# R235 完整压力终态：WAL及DBS日志写入等待

[终态与原始结构化结果](test-results-business-pressure-final-wait-failure.json)、[逐请求/线程相关性分析](test-analysis-business-pressure-final-wait.json)已归档。冻结工具与计划保持；本轮 **失败**，不发布稳定1.0，不将13项局部通过或引擎内容检查当作全部32项完成。

## 实际结果

DBS原生负载实际600.292096秒，未被中断：SQL298次/1错，最大5.005027秒；API121次/5错，HTTP超时约4.004秒，API p95桶5秒也超过原1秒标准。SQL p95桶0.005秒、覆盖率99.33%；API覆盖率100.83%来自原周期计数算法，不能抵消错误。原生phase=failed，执行器退出1、原因NATIVE_COMPLETION_EXIT；HISDBS没有执行。

原13项局部/11个切换区间及真实内存30→20 defer、释放、同generation自动重试完成。备份/同步/独立恢复等引擎10项内容检查完成，phase仍为content-passed-native-pending；物理备份120.253550秒。87个引擎探针中另有4次API内部超时/外层超过5秒，外层最大5.497058、内部最大5.005945秒。这组失败与原生5次API错误分别记录，不相加冒充独立错误总量。

## 更具体的等待证据

原生请求序号69为fixture-update/query，后端PID1800，synthetic_first_key=769，在约5.005秒后记录sql-readiness-deadline。对应5个1秒PG样本均为同一backend_start身份、active、LWLock/WALWrite。它不是已证明的普通行锁阻塞；采集器仅在普通Lock等待时查询pg_blocking_pids，因此此处blocking_pids=null且measured=false，不能解释为没有等待或已知WAL持有者。

同一DBS进程线程TID3248986出现36个D样本：两段分别25/11个，跨度约24/10秒；不是连续36秒，更不是连续50秒。全部捕获到native x86_64 syscall write、FD3指向`/opt/dbs/log/DBS.log`；核对前后PID/start、调用和链接一致，线程仍为D。内核栈包含folio_wait_bit_common、__filemap_get_folio、iomap_write_begin、xfs_file_buffered_write、vfs_write等。原生5次API超时各自窗口内有4个这种D样本。

这明确了观察到的文件写入等待路径，仍未证明该线程是请求处理者、日志锁的持有/等待关系或整个因果链。分开的/proc读取不原子；缺少采样之外的瞬时状态不能补造。该线程36个D样本全部出现在内存辅助release之后，SQL超时也在release之后，不能把本轮错误简单称为“辅助分配期间发生”。

两段D覆盖的整体50秒窗口，file_writeback从873906176降至16887808字节；io.max两端均为253:0 rbps64700080/wbps37470104/riops83/wiops135。逻辑设备253:0累计写入增量1220328448字节；下层8:0增量另列，**不把父子设备计数相加**，也不将io.stat累计提交量直接解释为物理完成带宽或证明限流已饱和。CPU throttled_usec增量0、memory.events各项增量0；PSI三个文件不可读，保持unknown。

## 采集与清理

取得600个线程样本，最大间隔1.003007秒、47线程、无task race或截断；observer原计划900秒，在原生结束后按原Session显式停止，报告incomplete/observer-interrupted，不能称跑满900秒。完整线程子进程CPU3.402627秒、RSS峰值78672KiB，采样内部CPU2.994714秒；最大一次采集0.016610秒，停止/落盘0.473635秒。费用按实际保留，不宣称零开销。

取得419条原生请求和601个PG样本，零丢弃/采集错误，601个PG样本最大起始间隔1.000240秒；全部切换/引擎区间处于采样包络内。诊断内部线程CPU总和0.583280秒不包括所有调用边界和服务端成本。最终采集phase=collected与原生业务phase=failed同时保留。

原生worker自行结束，最终收尾Session发现已退出，实际未发TERM/未KILL；本次不冒充“提前外部失败实测”，该路径的实际资格仍由原R220提供。原业务错误继续优先。完整[线程原文](test-evidence/native-pressure235-dbs-threads.json.gz)和[请求/PG原文](test-evidence/native-pressure235-dbs-request-pg.json.gz)按解压SHA256关联。

独立终态核对runner3241593/worker3241597/observer3256794及工作namespace/cgroup均不存在；两角色原配置08ed…、原profile缺省状态及发布ELF dbc48…恢复。未删除历史失败数据或改写旧计划。原始启动快照保留并加终态指针。

## 后续定位与原发布条件

下一步核对同一物理设备映射、原IO标定语义和实际写回/等待：区分DBS日志页等待、PG WAL写入等待、介质/队列竞争与IO限额影响；先以现有原始样本建立每秒读写量和错误窗口关系。若需要控制变量对照，另行冻结相同数据/负载/时限与单一变量的诊断计划，不算原32项通过、不修改原配额或关闭必要日志来取得成功。

正确限额下业务容量不足与Agent缺陷分别判定；当前证据尚未证明其中之一或完整排除Agent影响。R203/R167/R142/R120等历史失败继续保留。原604800秒、正式24h+24h与后置、ARM厂商业务及独立物理多设备仍按原52任务执行。

[本轮期间七天任务固定观察](test-progress-seven-day-during-final-wait.json)：节点14:51:31Z，两条原链路仍为原PID/start实例，SQL/API/OOM均0，约63658秒和49848秒；均未到604800秒，不接受七天通过，不重启长期任务。


已补充[R235实际PGDATA及IO映射只读核对](testing-final-wait-io-map.md)：原Pod明确PGDATA=/opt/postgresql/pgdata，实际WAL/日志/备份均为同一XFS253:0→sda2→sda，原标定profile保持。初次/data猜测路径的不存在和纠正完整保留；失败后队列快照不替代故障时刻或证明因果，不计独立物理多盘/业务通过。
