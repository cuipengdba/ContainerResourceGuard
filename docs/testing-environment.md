# 容量来源与重建分阶段实测（未发布）

2026-11-10，源码 ff753f0，二进制 SHA256 `976fffaa2ab9f9d075e43fa9e7ba9e8b5a57f93fc99b7f79e7c5804e3737fed8`。测试节点 Linux 5.14、amd64、containerd、Kubernetes、cgroup v2。仅操作本次临时容器和目录。详见 [JSON](test-results-environment-linux-amd64.json)。

## 结果

共 37 条通过的检查记录，按两个阶段归档；不能描述为一次无故障的完整六周期测试。

第一阶段在同一状态目录上完成五次连续 Pod 重建，交替使用原生宿主容量与普通文件伪造的 `/host/proc/meminfo`、`/host/sys/.../online`。每次重新发现自身身份，新 journal 不串用旧身份，旧 journal 归档；可信来源识别到 24 CPU 与 66,673,278,976B 内存。不可信文件即使内容合法也不作为宿主总量，percent 对应维度跳过；manual CPU 0.5、内存 256MiB 仍可写入、回读并恢复真实原值。

第六次创建只读容器时，夹具错误地要求容器内 cgroup 路径等于宿主完整路径，保护检查拒绝继续。该容器采用私有 cgroup namespace，自身路径是 `/sys/fs/cgroup`，并非外来目标。保留此失败和之前 32 条成功记录，清理命名空间后另建只读夹具，用运行时容器 PID 的宿主路径核对身份。

第二阶段 5 条通过：私有命名空间身份核对、两类宿主容量拒用、percent 不写假总量、manual 控制写入被拒绝而 PID1 仍存活、journal 仍绑定本次身份。夹具只读核对宿主控制文件，没有为通过测试开放控制器或改父组。测试命名空间已全部删除。

## 自动检查与保留问题

Go 1.22.5 的 Linux vet、race、16 个建模 SIGKILL 检查点及 12 个辅助启动故障检查通过，guard 语句覆盖率 67.5%。[CI](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42684563608) 通过。交叉编译与真机实测分开。

早期夹具误用字段名 online_cpus，修正为 host_online_cpus；另一次重复运行在 Pod 删除等待超时后停止，随后确认命名空间不存在。没有把这些失败记录改成通过，也没有强删其他容器或删除旧原值日志。

未测 Linux 6.x、ARM64 真机、节点重启、CPU 热插拔和所有只读/委派组合。已有证据仅支持上面的具体组合，不代表 v0.5 发布条件全部完成。
