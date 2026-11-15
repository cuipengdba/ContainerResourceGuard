# 最终候选：实际测试环境矩阵

产品源码`ced461705ebc27315a59aefe463f9b4af47130a3`，嵌入v1.0.0；只声明下列准确组合的已测范围，稳定发布尚未接受。构建成功、原生控制测试、厂商业务验收分别记录。

| 场景 | 架构/内核 | 运行时 | 存储/权限 | 已得结果 |
| --- | --- | --- | --- | --- |
| DBS/HISDBS原镜像；AlmaLinux 9.6 | amd64 / 5.14.0-570.22.1.el9_6.x86_64 | Kubernetes 1.26.12；containerd 1.6.27；runc 1.1.11 | cgroup v2；特权、可写cgroup访问、自有叶组；XFS/253:0单设备 | manual参考18/18；各600秒及备份/同步/独立恢复；默认20%完整业务失败保留 |
| 原生VM标签`ubuntu-22.04` | amd64 / 6.8.0-1070-azure | Docker 28.0.4 / containerd v2.4.2 / runc 1.5.2 | cgroup2fs；host cgroupns、自有叶组；单scsi_debug设备真实兄弟分区 | 26原生+45分区通过；自有夹具清理 |
| 原生VM标签`ubuntu-22.04-arm` | arm64 / 6.8.0-1070-azure | Docker 28.0.4 / containerd v2.4.2 / runc 1.5.2 | cgroup2fs；host cgroupns、自有叶组；单scsi_debug设备真实兄弟分区 | 26原生+45分区通过；自有夹具清理 |
| 原生VM标签`ubuntu-24.04` | amd64 / 7.0.0-1014-aws | Docker 28.0.4 / containerd v2.4.2 / runc 1.5.2 | cgroup2fs；host cgroupns、自有叶组；单scsi_debug设备真实兄弟分区 | 26原生+45分区通过；自有夹具清理 |
| 原生VM标签`ubuntu-24.04-arm` | arm64 / 7.0.0-1017-azure | Docker 28.0.4 / containerd v2.4.2 / runc 1.5.2 | cgroup2fs；host cgroupns、自有叶组；单scsi_debug设备真实兄弟分区 | 26原生+45分区通过；自有夹具清理 |

四个CI格均记录Docker API 1.48。runner标签按原件列出；CI未记录`/etc/os-release`，不据标签补造实际发行版版本。强制模式使用privileged与可写cgroup bind；只读反例使用cap-drop ALL和只读bind，并检查私有PID/挂载/网络命名空间。这里的host cgroupns仅暴露cgroup路径，Agent仍定位当前容器叶组，不管理兄弟容器。

单scsi_debug设备上的真实兄弟分区验证共享整盘额度，不能算两块物理盘。真机环境元数据在业务验收后单独只读采集，没有通过改环境重跑业务。[准确环境元数据](test-evidence-final-v1-environment.json.gz)、[逐组合机器矩阵与原件摘要](test-results-final-v1-environment-matrix.json)、[原生CI准确原件](test-evidence-final-v1-native-CI-terminal.json.gz)、[原路径业务终态](testing-final-v1-full600-terminal.md)可交叉核对。

ARM64厂商DBS/HISDBS业务、独立物理多盘、rootless/仅delegation强制、未测内核/运行时、复杂LVM、物理重启/CPU热插拔和最终长期验收仍未资格确认。v1/混合/未知或权限不足的跳过/降级行为不等于这些环境可强制限制。安装前须具备当前容器CPU/IO/memory控制器及可写权限；不修改上层Kubernetes硬限制。

[安装与配置](configuration.md)、[当前交付及剩余验收](release-readiness-current.md)。稳定包和生产部署另记，不能由本矩阵推导所有环境稳定支持。
