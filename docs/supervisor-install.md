# 已验证 supervisor 的显式接入与卸载

2026-11-10，next/install-upgrade 的 P08.1/P08.4 开发实现，未发布。此工具由用户在目标容器内部显式维护时运行，不在 start.sh 的必经路径执行，不调用 Kubernetes API。它接入已有业务/缓存 supervisor，不替换原 start.sh，也不启动/停止业务或缓存程序。

## 接入范围

先按可信发布流程把静态 CRG、optional-agent.sh 和 CRG 配置放到每容器专属、持久可读的路径。二进制/辅助脚本/原 supervisor 的期望 SHA256 来自已核对的发布包和已审阅的部署源文件；不能只对未知文件现算摘要，就把它称为来源验证。工具要求明确提供三份摘要，检查原 supervisor 的已验证 Bash 结构与唯一锚点，并对原件、候选和 helper 运行有界 `bash -n`，不执行脚本内容。

配置仍可只填 `{"percent":20}`，或采用手动模式；工具比较持久配置与实际传入配置，拒绝仅 CLI 覆盖导致重启语义不同。安装工具的文件摘要参数属于维护核验，日常资源配置无需填写。

```sh
# 以下路径为示例，必须对应本容器已审阅的实际部署路径。
/staging/crg supervisor-plan --config /etc/crg/config.json \
  --supervisor /root/cache-supervisor.sh --supervisor-sha256 TRUSTED_SOURCE_SHA \
  --helper /opt/crg/optional-agent.sh --helper-sha256 TRUSTED_HELPER_SHA \
  --agent-binary /opt/crg/bin/crg --agent-sha256 TRUSTED_BINARY_SHA

# 已有资源 Agent 时先显式暂停，保留限额；首次接入无需预先启动 Agent。
/staging/crg quiesce --config /etc/crg/config.json
# 使用与预览完全相同的参数，另加全新私有备份目录。
/staging/crg supervisor-install --config /etc/crg/config.json \
  --supervisor /root/cache-supervisor.sh --supervisor-sha256 TRUSTED_SOURCE_SHA \
  --helper /opt/crg/optional-agent.sh --helper-sha256 TRUSTED_HELPER_SHA \
  --agent-binary /opt/crg/bin/crg --agent-sha256 TRUSTED_BINARY_SHA \
  --backup-dir /recovery/integration-001
```

预览只输出摘要和拟执行状态，不输出厂商脚本。安装持有当前 cgroup inode 写锁，已有 Agent 未退出时拒绝；备份目录必须全新、0700、与输入和状态目录分离。私有备份包含原 supervisor、候选、配置、helper、计划与 receipt，文件0600，先同步再提交。保持原 supervisor 权限，目标目录内暂存、复核输入与当前身份、原子 rename 并同步父目录。它不修改 binary/helper/config/profile/journal；资源状态备份另用 state-backup。备份含私有部署内容，不能上传 GitHub。

未知结构、摘要不符、已有集成、符号链接、非普通文件、组/其他用户可写文件或目录、特殊权限、硬链接、UID/GID不同、扩展属性均拒绝自动改写。扩展属性包括可能的 SELinux 标签；该场景需要在部署源中保留元数据并单独审阅变更，工具不静默丢失标签。挂载点文件可能拒绝 rename，保持错误可见，改部署源后重建。持锁协调只约束遵循协议的 CRG，不防止外部 root 并发改写；部署维护应串行进行。

新接入块固定本容器的程序/配置/helper 路径，业务与原缓存启动顺序及原退出码逻辑保留；helper 缺失时放行业务，程序/配置不可用及运行错误由可选 helper 处理。接入在下一次计划重启时生效，工具不会为了测试接入自动重启容器。

## 卸载和永久停用

```sh
/opt/crg/bin/crg disable --config /etc/crg/config.json
# 检查 restored、实际控制值与剩余 journal 条目后执行：
/staging/crg supervisor-uninstall --config /etc/crg/config.json \
  --supervisor /root/cache-supervisor.sh --backup-dir /recovery/integration-001
```

卸载必须当前身份已 disable 且资源写锁空闲，journal 无任何未恢复条目；quiesce 仅暂停并保留限额，因此不足以完成卸载。外部冲突/未完成写意图/不兼容日志先解决，工具不删日志或强设 max。核对 receipt、原件与当前候选摘要后，只恢复原 supervisor 字节和权限，保留备份、程序、配置及状态供核对，不停止任何进程。当前 helper 因 disable 标记不能重启资源写入者；下次新容器永久停用依靠持久部署源中已撤除的接入块。

prepared receipt 加实际源/候选摘要用于判断中断点；rename 后 fsync/receipt 失败可能已经替换文件，应检查摘要，不能把报错当作未改动。当前工具没有“清理一切”的递归删除命令，也不自动覆盖外部更改的 supervisor。备份被损坏、当前脚本被他人更改时拒绝自动回退。

只修改运行中容器的临时可写层不会自动进入新镜像。程序、helper、配置、接入入口需由镜像或每容器专用挂载持久化，state_dir 每容器独立；Pod 重建后继续由自身 cgroup 重新发现 ID。旧身份 disable 标记不会永久禁用新容器，永久停用必须修改持久启动入口。镜像构建/现有部署应保留同一业务命令和缓存程序，不需要安装 Operator。

本文归档设计与边界；实际通过/失败证据需另列，不能把代码存在当成完整 P08 验收通过。
