# 安装升级开发：兼容预检与私有状态备份

2026-11-10，next/install-upgrade 开发分支。尚未合入 main、尚未发布 v0.7.0。此页归档 P08.2/P08.3 的第一部分，不把预检写成完整安装器、在线升级或状态导入已实现。

## 已有入口

```sh
/opt/crg/crg build-info
/opt/crg/crg upgrade-check --config /etc/crg/config.json
# 先显式停用；确认恢复结果，并按原 supervisor 的独立辅助管理方式停止 CRG helper。
/opt/crg/crg disable --config /etc/crg/config.json
/opt/crg/crg state-backup --config /etc/crg/config.json --output /recovery/crg-state-before-upgrade.json
```

均在目标容器内部执行，不接受其他容器、PID 或 cgroup 参数。兼容预检不重建目录、不新建锁、不改控制值、不归档旧 journal。原 Agent 仍持写锁时预检拒绝，不能把两个程序同时运行当成升级。

预检短暂获取当前 cgroup inode 锁和已有 agent.lock，核对当前身份，按与真实写入者相同的严格规则读取 journal、disable marker 和可获得的 IO profile。未知版本/字段、无效控制项、损坏或非普通状态文件拒绝；未知旧身份的无效 journal 也不能先归档再忽略。缺状态目录或缺 agent.lock 明确报错，此入口用于已有安装的状态核对，新安装使用原 preflight。

JSON 只报告本读取器的兼容结果、版本、摘要、控制器类别、条目数及身份是否相符，不返回原值或旧容器路径。build-info 新增锁协议、可读 journal/profile 版本和控制项列表，原 version/revision/os/arch 字段保持不变。读取器接受某快照不代表未运行过的另一候选二进制也接受；候选来源校验和该候选自身预检仍须分别执行。

quiescent_snapshot 仅在读取时禁用标记属于当前身份且两把锁空闲时为 true。命令返回即释放锁，不能把这份 JSON 当作稍后切换二进制的锁凭证。未知旧版本是否遵循同一锁协议必须核对；未经验证的版本不允许假定可直接在线切换。

## 私有备份边界

state-backup 还要求当前身份已停用，全程持有两把锁，输出到显式指定、状态目录外的全新绝对路径，0600、O_EXCL、内容及父目录同步、上限 4MiB。状态目录的符号链接别名、已有文件、IO profile 目的路径均不能作为输出；写入/同步失败如实返回，可能留下私有部分文件，由操作人员检查。

备份保存严格校验过的原始 journal（包含真实原值和未完成写意图）、disable marker、存在时的 profile，不重写其中身份或值。它**包含私有路径和身份，不是脱敏诊断包**，不应上传 GitHub。原配置、可选 helper、原 supervisor 和二进制需另外按安装手册备份；不包含临时 runtime/status/reload、数据库数据或其他容器信息。

当前没有自动迁移/导入命令。备份不是允许对新容器恢复旧限额的凭据，不删除不兼容日志、不用 max 重置、不重写身份以强行升级。新容器重建仍走既有自身发现与旧日志隔离。完整受控二进制切换、失败回退及模板安装工具继续开发，只有完成演练后才能关闭 P08。
