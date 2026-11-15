# 当前交付与待办：2026-11-15

当前可下载[v1.0.0-preview.5](https://github.com/cuipengdba/ContainerResourceGuard/releases/tag/v1.0.0-preview.5)，工程预发布，产品源码`ced461705ebc27315a59aefe463f9b4af47130a3`，八项公开附件及标签保持。嵌入正式版本号v1.0.0的候选已固定并通过下述实际验收，但尚未创建稳定标签或发布。源码构建请核对准确产品修订或preview.5标签；main产品实现尚未合入本候选。

## 已交付的用户需求

- 每个DBS/HISDBS容器分别运行一份Agent，只定位/控制当前容器cgroup；容器或Pod ID变化后自动重新发现。
- 仅管理CPU、内存、IO。百分比模式分别使用cpu_percent、memory_percent、io_percent，省略各自默认20%；另有明确的手动绝对额度模式。
- 内存使用memory.high回收/节流，不新增memory.max硬限制；已有Kubernetes硬限制仍有效，不能保证绝无OOM。
- IO默认自动选择容量最大的合格可写本地文件系统并标定/复用，按读写BPS百分比设置；IOPS只在手动配置时管理，外部已有IOPS保留。
- 仅纯cgroup v2校验后写入；v1/混合/未知/权限不足明确日志跳过或降级。辅助失败放行原业务启动和运行。
- 输出运行日志，一天一文件，30天及总量1GB滚动清理；日志失败不作为业务启动门槛。

具体接入与配置见[README](../README.md)、[配置](configuration.md)、[升级](upgrade-preview4-preview5.zh.md)。支持范围为各证据实际验证的环境，不能把通用Linux/ARM资格写成厂商ARM真机通过。

## 固定正式版本号候选的实际结果

- [DBS/HISDBS原路径18/18通过](testing-final-v1-full600-terminal.md)：各实际600秒、SQL/API零错误及原延迟/覆盖要求，真实物理备份、同步、独立恢复和PG拥有者核对；清理已独立确认。
- [原生amd64/ARM64、Linux6/7共284/284通过](testing-final-v1-native-CI-terminal.md)：实际执行ELF均与已固定产物摘要一致，自有夹具完整清理。这不是厂商ARM业务或独立物理多盘证明。
- [候选身份](final-v1-candidate-identity.json)保留构建时点快照、两架构及不同绝对路径重复构建证据。新ELF没有继承preview.5或preview.4长期时长。

## 保留的公开预发布结果与失败

公开preview.4→5默认百分比控制迁移48/48通过，含Pod重建新ID、旧自有IOPS迁移及外部IOPS保留；该套件业务gate关闭，不是默认20%业务性能通过。公开manual维护40/40通过；此前修正PG日志来源后的冲突/正常完整套件44/44通过，首轮失败仍保留。

默认三项20%完整业务测试仍有SQL/API超时及备库停止超时，记录为失败。严格限额会影响具体数据库负载，不能把20%解释成任意业务性能承诺，也不能用manual结果覆盖。旧preview.4约30h后端口冲突失败，不继承计时。

## 剩余发布工作

[固定产物24h observe基线→原容器24h enforce→七天验收执行程序](testing-final-v1-long.md)已开发并完成原生只读预检查。当前旧测试夹具仍在节点，程序按计划拒绝启动；新计时未开始。旧版七天任务实际仍运行，已约4.24天，不能计为本候选时长。长期运行及老化后验证尚未完成。[原52项已逐项审核](current-52-task-audit.md)：10项在限定范围完成，扩展参数取消/部分取消单列，缺硬件、真实时长和其余具体待办分别保留。原定义与历史失败不删除，不能整体勾选完成。最终候选的[三场景30分钟开销补验](testing-final-v1-overhead.md)三场景均实际1800秒/181样本通过，已独立复算CPU/RSS/写入和确认全部登记进程、父叶cgroup与namespace清理，见[终态](testing-final-v1-overhead-terminal.md)。不同有效限额回归和长期老化仍未完成。

[准确已测环境矩阵](tested-environment-matrix.md)逐一列出内核、运行时/runc、架构、存储、挂载权限和结果；当前支持只按实际报告的环境声明；暂无厂商ARM/独立物理多盘节点，不能扩大支持结论。稳定发布和生产部署分别记录，正式交付以本页及最新终态为准。全部需求与任务见[任务登记](current-task-registry.json)。



[固定最终ELF同一Agent业务热重载](testing-final-v1-business-reload.md)已唯一启动，DBS首个实际配置观察通过，完整两角色600秒业务和13种配置观察仍待终态；无旧版计时转记。[当前运维、问题分级和补丁/归档规则](operations-release-policy.md)已补齐，旧RC2不支持重载的过时说明已修正。
