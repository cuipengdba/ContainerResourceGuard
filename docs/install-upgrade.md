# 安装升级开发：兼容预检与私有状态备份

当前公开preview.3→preview.4的受测步骤见[专用升级文档](upgrade-preview3-preview4.zh.md)，[实际26项](testing-public-preview-memory-high-maintenance.md)已通过；下面是原2026-11-10开发归档，不改写当时未发布状态。

2026-11-10，next/install-upgrade 开发分支。尚未合入 main、尚未发布 v0.7.0。此页归档 P08.2/P08.3 的第一部分，不把预检写成完整安装器、在线升级或状态导入已实现。

## 已有入口

```sh
/opt/crg/crg build-info
/opt/crg/crg upgrade-check --config /etc/crg/config.json
# 升级维护：暂停自身资源 Agent，内核限额与原值日志保留，不执行恢复。
/opt/crg/crg quiesce --config /etc/crg/config.json
# 先显式停用；确认恢复结果，并按原 supervisor 的独立辅助管理方式停止 CRG helper。
/opt/crg/crg disable --config /etc/crg/config.json
/opt/crg/crg state-backup --config /etc/crg/config.json --output /recovery/crg-state-before-upgrade.json
```

均在目标容器内部执行，不接受其他容器、PID 或 cgroup 参数。兼容预检不重建目录、不新建锁、不改控制值、不归档旧 journal。原 Agent 仍持写锁时预检拒绝，不能把两个程序同时运行当成升级。

预检短暂获取当前 cgroup inode 锁和已有 agent.lock，核对当前身份，按与真实写入者相同的严格规则读取 journal、disable marker 和可获得的 IO profile。未知版本/字段、无效控制项、损坏或非普通状态文件拒绝；未知旧身份的无效 journal 也不能先归档再忽略。缺状态目录或缺 agent.lock 明确报错，此入口用于已有安装的状态核对，新安装使用原 preflight。

JSON 只报告本读取器的兼容结果、版本、摘要、控制器类别、条目数及身份是否相符，不返回原值或旧容器路径。build-info 新增锁协议、可读 journal/profile 版本和控制项列表，原 version/revision/os/arch 字段保持不变。读取器接受某快照不代表未运行过的另一候选二进制也接受；候选来源校验和该候选自身预检仍须分别执行。

quiescent_snapshot 仅在读取时禁用标记属于当前身份且两把锁空闲时为 true。命令返回即释放锁，不能把这份 JSON 当作稍后切换二进制的锁凭证。未知旧版本是否遵循同一锁协议必须核对；未经验证的版本不允许假定可直接在线切换。

quiesce 是显式维护操作：持久化与既有格式一致的当前身份禁用标记，至多等待 5s 获取两把写锁，验证自身身份后返回；不调用恢复、不改控制值、不重写当前 journal/pending 或最后一次 status。当前 Agent 退出后内核限额继续生效，optional helper 重试读取该标记时继续退出；之后 enable 才允许按既有重试策略重启 Agent。

disable 仍表示停用并尝试恢复真实原值。quiesce 与 disable 都不能接入业务启动必经路径；维护失败不退出业务，若标记已持久化但后续拿锁/校验失败，会明确返回错误，限额仍应按内核实际值检查。status 保留最后资源结果，需结合 writer_lock_held、snapshot_age_seconds 和 upgrade-check 的 disabled_for_current_container 判断，不能把旧 managed 快照当成写入者仍运行。

## 私有备份边界

state-backup 还要求当前身份已停用，全程持有两把锁，输出到显式指定、状态目录外的全新绝对路径，0600、O_EXCL、内容及父目录同步、上限 4MiB。状态目录的符号链接别名、已有文件、IO profile 目的路径均不能作为输出；写入/同步失败如实返回，可能留下私有部分文件，由操作人员检查。

备份保存严格校验过的原始 journal（包含真实原值和未完成写意图）、disable marker、存在时的 profile，不重写其中身份或值。它**包含私有路径和身份，不是脱敏诊断包**，不应上传 GitHub。原配置、可选 helper、原 supervisor 和二进制需另外按安装手册备份；不包含临时 runtime/status/reload、数据库数据或其他容器信息。

当前没有自动迁移/导入命令。备份不是允许对新容器恢复旧限额的凭据，不删除不兼容日志、不用 max 重置、不重写身份以强行升级。新容器重建仍走既有自身发现与旧日志隔离。模板接入工具见下文；只有完成真实演练与持久化检查后才能关闭 P08。

## 受控二进制替换开发

`binary-install` / `binary-rollback` 是显式维护命令，不在启动路径执行。当前实现仍在开发验证，未发布：

```sh
# 安装目录必须是此容器专属的可写目录，crg 是原 helper 已配置的程序路径。
# /staging/crg 必须先按可信发布摘要核验；该候选从安装目录之外运行。
/staging/crg quiesce --config /etc/crg/config.json
/staging/crg binary-install --config /etc/crg/config.json \
  --install-dir /opt/crg/bin --backup-dir /recovery/upgrade-001 \
  --previous-sha256 EXPECTED_OLD_SHA --candidate-sha256 EXPECTED_NEW_SHA
/opt/crg/bin/crg upgrade-check --config /etc/crg/config.json
# 保持暂停时的即时回退；不导入 state.json、不恢复内核限额。
/staging/crg binary-rollback --config /etc/crg/config.json \
  --install-dir /opt/crg/bin --backup-dir /recovery/upgrade-001
# 核对后再 enable，原 optional helper 在下次重试时启动程序。
```

源文件为正在运行的候选 `/proc/self/exe`，按 32KiB 缓冲复制，上限 64MiB；显式新旧 SHA256 均匹配才继续。原程序必须报告已知锁协议和 journal v1。摘要来自用户信任的发布渠道；本命令不建立签名信任、不下载远程安装脚本。安装目录不得是符号链接或组/其他用户可写目录，不得与 state_dir 重叠；备份目录必须全新，与安装和状态目录分离，位于真实受保护父目录。挂载需由部署保证为每容器专用，禁止多个容器共用可写安装目录。

全程持有自身两把锁，要求当前身份禁用且 journal 属于当前身份。备份 0700 目录内保存旧程序、0600 私有状态副本和 receipt，先同步，再在原安装目录暂存并以 rename 替换单个 crg，随后同步父目录。原 supervisor、start.sh、数据库和缓存程序不改。提交前复核身份、状态和目标摘要；外部变更则拒绝。

回退只替换程序文件，不导入旧 journal。必须仍是同一身份，目标为记录的候选摘要，旧程序副本摘要正确，配置、journal、profile 与安装前一致；再次 quiesce 的同身份停用标记只忽略记录时间，版本和身份仍核对。enable 后产生新资源写意图或更改配置时保守拒绝自动回退，需保持暂停并分别检查旧读取器兼容性和当前原值所有权。receipt 的 prepared/installed/rolled_back 记录与目标实际摘要共同用于判断中断位置；rename 后同步或 receipt 更新失败会报错，不能把错误等同于文件未替换。成功后也保持暂停，需显式 enable。

## 已发布预览的首次迁移边界

main的v0.1.0-rc.3-preview.1没有声明本开发维护命令要求的lock_protocol和journal_versions，因此不能直接按上述保留限额的binary-install流程升级到组合线。[第13轮](testing-three-resource-online-maintenance.md)在两套业务中均首次安装失败，旧程序摘要保持且没有创建recovery内容；保护条件继续保留。首次接入组合线需单独按旧程序disable恢复并核对原值、停止旧辅助入口、备份及安装新程序的迁移流程审核，不用新state_dir或删journal绕过旧所有权。

[第15轮计划](test-plan-three-resource-protocol-maintenance.json)只测试明确声明同一协议的两套未发布组合程序，不能扩成已发布预览在线迁移成功，也不能替代最近两个已发布次版本验收。
