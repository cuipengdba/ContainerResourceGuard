# 已发布预览包的原生控制器验收计划

P06/P09补齐发布物本身的证据。先前6.8/7.0的原生AMD64/ARM64测试使用后续源码构建，不能替代下载页的ARM64发布包。本次固定v0.1.0-rc.3-preview.1原资产，不重打包、不重建CRG、不替换发布附件；仅构建占位PID1和负载夹具。

[手动工作流](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/.github/workflows/released-cgroup.yml)在四个新鲜原生VM分别执行：ubuntu-22.04/22.04-arm要求实际Linux6.*，ubuntu-24.04/24.04-arm要求实际Linux7.*。运行器标签不是结果，内核、架构或cgroup2fs不符时在夹具前拒绝，不放宽环境门槛。相同发布包只需在main执行一次四格，不将两分支重复跑同一发布物计为不同覆盖。

下载release API、tag API、对应架构tar及SHA256SUMS，独立固定release/asset ID、tag/package/source修订、压缩包大小/摘要、校验文件摘要、BUILD.json及静态原生ELF摘要；不以同次下载的校验文件作为自身信任根。[校验器](https://github.com/cuipengdba/ContainerResourceGuard/blob/main/tests/released-package.py)只选取已验证的二进制字节，不extractall、不执行下载的脚本。先在普通用户执行build-info核对版本/源码/架构，然后才运行root测试夹具。

完整沿用冻结的native-cgroup.py 22项、数值预算、测量时长和失败条件：CPU实际节流、内存值和安全分配、直接读写与IOPS硬限额、唯一自身Agent、崩溃保留限额/恢复、原八项值、自动三百分比/后台标定、真实新容器ID/profile及日志复用、只读降级。存储仍为专属新稀疏文件→DIO loop→UUID dm-linear→ext4，不格式化已有设备，所有权核对后正常清理所有夹具。

完整结果前不将发布ARM64资产由“仅构建”改成“已实测”。通过也仅覆盖记录的原生架构/内核/Docker/合成块设备上的占位容器，不证明ARM厂商业务、物理独立多设备、分区映射、默认20%业务性能、OOM耗尽、24h/7d或1.0发布。失败与部分运行保留，禁止用新编译CRG替换失败资产。

首次执行前冻结精确文件摘要及发布物合同，见[test-plan-released-cgroup-ci.json](test-plan-released-cgroup-ci.json)。
