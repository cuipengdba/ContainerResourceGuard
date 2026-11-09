# 开发说明

先阅读 docs/requirements.md 与 docs/tasks.md。新增需求补充编号；完成任务必须提供真实测试证据，不能只改状态。

提交前运行 gofmt、go vet、go test -race 和 tests/supervisor.sh，并交叉编译 Linux amd64/arm64。

涉及发现、写入和恢复的变更应包含目标边界、外部改写、权限失败和中断恢复测试。真实 cgroup 测试必须使用独立临时容器，不修改现有业务 workload，不清理全局缓存，不写裸设备。

公共仓库禁止提交内部 IP、SSH 密码、GitHub 令牌、业务日志和客户代码。测试报告区分执行过的场景与未覆盖的场景。
