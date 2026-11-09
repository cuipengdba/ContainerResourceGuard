# 接入现有容器

## 进程关系

```text
PID 1：原有 supervisor
  ├─ 原 start.sh → DBS/HISDBS、PostgreSQL
  ├─ 原缓存控制程序
  └─ ContainerResourceGuard（新增、可选）
```

原业务独立启动。CRG 初始化、写入、权限检查都不构成启动前置条件；这样存在业务先启动、限额稍后生效的窗口。若要求第一个业务进程开始就受限制，须由容器运行时设置外层上限。

不要把代码直接塞进业务 start.sh，不修改 DBS Python/二进制、数据库参数、备份/同步调用、缓存清理程序，也不要使用失败会杀容器的 postStart 承担 CRG 初始化。

## 在现有 supervisor 中增加可选子进程

复用现有可选程序目录挂载；没有必要新增一个必须存在的配置卷。将 `examples/optional-agent.sh` 放在现有管理目录，按原 supervisor 的语法与信号管理方式接入：

```bash
# 原业务先独立启动，原缓存控制保持原有管理方式。
# 下列逻辑放在不会改变原业务退出码的位置。
if [[ -r /opt/crg/optional-agent.sh ]]; then
  source /opt/crg/optional-agent.sh
  CRG_BIN=/opt/crg/crg
  CRG_CONFIG=/etc/crg/config.json
  crg_start_optional || :
fi
# 原 supervisor 的关闭流程增加：
# [[ -z "$CRG_HELPER_PID" ]] || kill -TERM "$CRG_HELPER_PID" 2>/dev/null || true
# 并 wait 回收该管理子进程。
```

辅助管理循环与业务主循环分离，失败独立退避重试，最高间隔 300 秒。二进制/配置不存在时直接跳过。日志输出错误不应传染业务 shell。现有 supervisor 若启用 `set -e`，可选逻辑必须放在显式条件或 `|| :` 范围内。

停止辅助进程先发送 TERM，最多等待约 2 秒后再发送 KILL，不能因它忽略 TERM 阻塞原业务关闭。内核不可中断 IO 仍可能延迟任务实际消失，容器运行时的最终清理继续有效。

`examples/supervisor.sh` 是完整但简化的进程管理示例，主要用于集成演练。它保留原命令的退出码，并向业务主进程传递停止信号；业务自身的孙进程信号处理仍依赖原启动脚本，不能未经验证直接替换成熟的生产 supervisor。

## 文件与权限

- 程序及 profile 可只读挂载；状态目录必须容器独立且可写，例如 `/tmp/containerresourceguard`。
- 可写临时目录可以使用已有 emptyDir；新增加的必需 volume 若缺失，Pod 可能在程序执行之前就启动失败，因此不能靠 Agent 自身解决。
- 自身 cgroup 的控制文件需确实允许写；普通 root 不等于拥有此权限。CRG 不主动 remount、不自动升权。
- 无权限容器继续业务运行，但资源状态为未管理，不能声称已经限制。
- 不提供 Kubernetes 集群角色、管理其他容器的 socket 或全节点 Agent。

首次永久接入需发布启动管理脚本并在计划内重启时加载；以后 Pod/容器重建自动重新发现。一次临时 `kubectl exec` 启动不能替代持久接入。

## 与缓存控制共存

CRG 只设置资源预算，不主动清理数据库缓存。原缓存控制程序继续独立运行，两者与数据库共同计入本容器资源。过紧内存/IO 额度可能改变缓存回收与数据库延迟，应联合验证。
