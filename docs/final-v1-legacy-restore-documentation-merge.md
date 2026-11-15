# 内存恢复并发验证的文档合并记录

本次只解决当前任务登记的一个文档冲突。集成输入为 `1145673b3c6353e1000aaf56677ec2109140936c`，main 输入为 `fdd69a642719674ca8ad4dc55b77624cee4adbc5`。两侧原52项定义和18项完成声明一致，保持不变。新增[并发恢复验证](testing-final-v1-legacy-restore-pressure.md)为四个原生VM116/116及16夹具清理，真实旧二进制升级、厂商压力/老化和长期范围继续保留。

集成当前登记保留完整历史；main 的[准确完整登记原件](current-task-registry-main-before-legacy-restore-integration.json)另行归档，SHA256 `68221689ad36a1094f24a9bad5e78af9d3ab1d03192076be730f273099faacba`。本次没有丢弃或替换已有历史副本，也不将 main 的旧产品实现合入候选。

提交前确认相对集成输入没有 cmd/internal/go.mod/scripts/workflow 变化，50份产品源码仍与固定最终候选一致，公开文档链接闭包通过。正式1396任务的原16输入、二进制、配额、进程和时长不受影响。此提交不合并草稿PR或发布稳定版；main产品实现仍待原版发布门槛完成。
