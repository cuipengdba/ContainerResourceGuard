# 当前组合候选 Linux 6.x 控制器补测

原[Linux 6.8 四格报告](testing-linux6-cgroup-ci.md)分别属于5226217和07e75d3，不能改写成当前组合候选的二进制记录。主线cmd/internal/scripts/模块及工作流和驱动至今未变，本次保留原证据，不重跑主线。组合线接入分区实现后，已有[接入回归](testing-partition-integration.md)与[分区核心实测](testing-partition-io-core.md)，本次补当前组合提交在Linux6上的精确二进制来源。

[执行前冻结合同](test-plan-linux6-current-integration.json)固定50份生产源码及四份工作流/驱动源码、原22项次序和全部数字条件。只对组合线手动触发现有linux6-cgroup工作流；冻结文档提交后再记录实际dispatch head_sha。AMD64、ARM64两格各22项，实际6.*内核与cgroup2fs必须在任何夹具前成立；标签不等于内核版本。保留首轮失败，不改标签、预算、错误界限或原测试驱动获取通过。

实际测量仍为0.5核、128MiB、4MiB/s、256IOPS，另验证CPU10%/内存1%/IO20%的独立换算、真实自动标定、容器新ID/profile复用、日志与只读降级。实际值、原生race事件、程序ELF及build-info、八项原值恢复和所有权限定清理按原合同复核。

仅在GitHub新建临时VM的专属稀疏文件/loop/dm-linear/ext4上执行，不访问现有业务节点或数据库。该结果不代替ARM厂商业务、真实双分区、独立物理多设备、原32项双角色业务、24h配对、实际七天及后置、两个已发布旧次版本迁移，也不替换已发布preview.3资产。
