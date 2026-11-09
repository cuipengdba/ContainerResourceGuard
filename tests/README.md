# 测试说明

## 自动检查

```bash
go test -race -cover ./...
go vet ./...
bash tests/supervisor.sh
```

单元测试覆盖配置、cgroup namespace 路径解析、目标越界拒绝、百分比与既有限额、IO 取整、写入前持久化、幂等、只读/权限失败、内存下调保护、外部冲突、pending 恢复和正常恢复。

`supervisor.sh` 启动真实模拟业务进程和异常辅助进程，检查业务启动/完成标记、原退出码 37 与有界退出时间。模拟返回错误不等价于所有业务集成已经验收。

## 真实 cgroup 验证方法

只在专用临时 namespace、容器和测试目录执行。测试节点应已有 Linux cgroup v2 与可用容器运行时，不要以真实业务容器承担故障演练。

1. 将 Linux 静态 CRG 和 `tests/load` 构建物、示例 supervisor 放入只读工具挂载；提供独立可写测试数据目录和临时状态目录。
2. 显式对测试数据设备标定，并只给临时容器分发 profile。先 observe 检查容量与 cgroup 目标。
3. 两个临时容器分别使用 20%、30%，先只启用第一个，确认第二个的控制文件未变，再启用第二个。
4. 读回各自 `cpu.max`、`memory.max`、`io.max`，与换算结果比较，检查目标不同。
5. 在容器内部运行 `crg-load --mode cpu --seconds 4 --workers 12`，比较该组 `cpu.stat` 前后增量与壁钟时间。
6. 运行 `crg-load --mode read/write --seconds 5 --directory /crgdata`，核对速率。该负载只新建临时文件，不允许指向既有业务文件。
7. 在只读 cgroup 容器启用 enforce，确认逐项 skipped 且业务主进程仍存活。
8. 在临时组内模拟外部修改，确认 CRG 不覆盖，停用恢复时也保留外部值。
9. 对正常持有的配置执行 restore，确认回到原值；删除/重建测试 Pod，确认 ID 和路径变化后自动重新应用。
10. 另建带运行时内存保护的临时容器，先确认其实际内存上限足够小，再用有界 memory 负载验证 cgroup OOM 计数，不对节点实施内存压力。
11. 测试后删除本次创建的临时容器/namespace，保留去标识报告。

真实测量值及未覆盖范围见 [测试报告](../docs/testing.md)。源码中的测试负载不是产品命令，不包含跨容器资源管理功能。
