# 内存压力测试工具的Python2兼容修正

[原R130失败](test-results-business-memory-pressure-failure.json)保留：原执行器/计划/辅助工具不变。DBS完成8个配置区间/10项局部主检查，在辅助工具握手时退出；未发送分配命令，实际30→20高用量、完整600秒及HISDBS业务均未执行。原运行器/worker/Pod/cgroup独立确认消失，原配置/profile缺失状态及发布ELF保持。

只读查询实测两种厂商镜像均为Python2.7.5、64位、sys.platform=linux2。旧辅助工具仅允许linux，故在申请内存前拒绝。原握手stdout未保存，不能声称重建其原始字节；[独立运行时结果](test-results-memory-pressure-legacy-runtime.json)在相同缓存镜像的新临时Pod中实际重现旧工具rejected/0字节，并验证修正工具。

新`vendor-memory-pressure-worker-v2.py`只将平台判断改为接受Linux平台名前缀，12GiB容量/64MiB步长/自身14GiB地址空间/十秒租约/240秒单调寿命及释放逻辑完全保持。旧文件与失败不覆盖；`vendor-memory-pressure-selftest-v2.py`仅改绑定的新文件名。产品主程序和已发布包没有修改。

实际结果：Linux主机7项工具检查通过；两种镜像各8项、共16项通过，包含旧拒绝重现、新无标记拒绝、空EOF、正常64MiB分配/释放、已分配EOF、非法输入、TERM及十秒空闲释放。每个进程最多实际64MiB，未据此宣称12GiB实测或真实30→20压力通过。临时Pod仅执行sleep及协议测试，无原业务启动、数据或hostPath挂载，根文件系统只读；namespace独立确认消失，crictl无该namespace运行容器，测试入口进程已消失。冻结执行器源码及摘要与原报告一起归档。

后续真实压力补测必须使用新的计划/执行根/namespace，绑定v2工具并重新核对全部前置；保留原32项/两角色各600秒、8个实际控制文件、30秒临时备库停止和全部原SLA。当前仅解决测试工具的实际Python2平台兼容，R120关闭超时、原高用量/完整并发/正式对照/七天及硬件范围仍待。
