# 校验后安全暂存发布包

`scripts/stage-release.py` 是独立的离线维护工具，不是常驻 Agent。
它把已核验的包发布到**不存在的新目录**，不替换正在运行的 CRG，
不执行包里的程序，不改数据库启动链或 cgroup。CRG 本身仍是静态 Go
程序，运行时不新增 Python 依赖。

从预先信任的源码检出中运行此脚本及同目录 `verify-release.py`，
不要先运行待验证包里的校验脚本。由独立可信渠道取得完整包 SHA-256、
程序源码修订、打包修订和架构；同渠道的 `SHA256SUMS` 本身不建立发布者信任。
本工具检查这些输入和包内二进制/SBOM绑定，签名验证仍单独进行，见
[候选来源验证](final-v1-package-rehearsal.md)。

```sh
mkdir -m 0700 /private-staging
python3 -I /trusted-crg-source/scripts/stage-release.py /downloads/PACKAGE.tar.gz \
  --destination /private-staging/release-001 \
  --sha256 "$CRG_TRUSTED_PACKAGE_SHA256" \
  --source-revision "$CRG_TRUSTED_SOURCE_REVISION" \
  --package-revision "$CRG_TRUSTED_PACKAGE_REVISION" --arch amd64 &&
/private-staging/release-001/crg build-info
```

父目录必须属于当前用户、权限严格为0700，路径中不能有符号链接。
目标可以自定名称，但必须不存在。需要 Linux、Python3.8+、`/proc/self/fd`
及 libc 的 `renameat2` 接口；系统/文件系统不支持不覆盖式原子发布时明确失败，
不退回覆盖现有目录的做法。该可选工具的兼容范围不扩大 Agent 已验证范围。

## 写入与失败行为

1. 使用非阻塞、拒绝符号链接的方式打开普通包文件，将有界内容复制到私有匿名快照，
   校验可信摘要；后续校验与解包使用这同一快照，不重新读取调用者的下载路径。
2. 使用预信任校验器核对路径、成员数/大小、ELF架构、源码修订、内层摘要和SBOM绑定，
   另外核对打包修订。拒绝链接、特殊文件、重复/越界成员及保留的收据名称。
   写入任何包成员前预检完整目录树，每个路径最多64个组成部分；
   [深度修复及新身份实测](verified-release-staging-depth.md)记录旧缺陷与验证结果。
3. 只在父目录下新建的私有临时目录写文件。目录0700，普通文件0600，
   包内原有拥有者执行位映射为0700；不保留其他用户权限、setuid/setgid或归档用户身份。
   工具自身使用077创建掩码，避免调用者的过严umask剥掉程序执行位，退出前恢复本进程原掩码。
   同步文件和目录后，用 `RENAME_NOREPLACE` 发布到目标。并发出现的文件、目录或链接
   都不会被替换。
4. 成功输出 `state=staged`，目录内有 `STAGING-VERIFICATION.json`，
   记录包、程序、源码/打包修订及两个预信任工具的摘要。发布前失败清理仅属于本次的临时目录，
   不更改已有安装；清理失败会报告保留的私有目录名。

如果发布后的父目录同步或身份确认失败，返回非零并报告
`state=published-unconfirmed`、`published=true`。目标可能已存在；先核对目录、
收据和摘要，不要假定完全没写入后盲目重试。强杀/掉电也需核对实际目录状态，
本工具不承诺中断后自动回滚。私有目录防护不把同一可信用户或root的恶意修改视为隔离边界。

暂存完成后，维护者仍需通过当前安装版本 `quiesce`、候选 `upgrade-check`、
候选 `binary-install` 及确认后的 `enable` 完成逐容器替换。
明确的回退收据/状态匹配规则见[升级流程](upgrade-preview4-preview5.zh.md)。
只复制到运行中容器的文件不会自动进入重建后的镜像或持久部署。

## 初版工具验证范围

以下150项属于旧工具1d8faf3c的准确历史结果。当前工具0ff1bc89的相同检查及新增深度边界测试，见[目录深度修复](verified-release-staging-depth.md)。

冻结方案见[机器可读计划](test-plan-final-v1-verified-staging.json)。
使用已完成来源/签名核对的准确候选打包修订
`576e6070b09804017ececf3f82fb2f6517c18316` 的两架构归档，
以及原公开 preview.5 包。不是新稳定包、不是厂商原路径/老化验收。
两者程序源码均为 `ced461705ebc27315a59aefe463f9b4af47130a3`，嵌入版本不同，
不能继承另一二进制的时长。

初版验证状态（2026-11-16 CST）：**两环境150/150检查、52个暂存场景及两套实际升级/回退/禁用流程通过**。

| 实际环境 | 检查 | Python |
| --- | --- | --- |
| amd64 / Linux6.8.0-1070-azure | 75/75 | 3.10.12 |
| ARM64 / Linux7.0.0-1017-azure | 75/75 | 3.12.3 |

实际运行：[amd64 43740167084](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/43740167084)、
[ARM64 43740471640](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/43740471640)。
两次准确工具/测试来源均为 `1cc1e55e23f6ea5c583262b664a46c79c1469cd8`，
通过amd64独立复核后才派发ARM64；暂存器、测试器及v3计划在两次之间没有变化。

两份[完整原始ZIP及46文件](test-evidence-final-v1-verified-staging.json.gz)保留原字节，
包含错误拒绝结果、真实延迟轨迹、准确工具/计划、升级/回退收据和进程清理记录。
每个ZIP都核对GitHub artifact API完整摘要，再逐成员核对CRC/长度/摘要；
公开运行元数据只选身份/结果字段，不含提交作者邮箱，未改变ZIP内容。
[离线复算结果](test-results-final-v1-verified-staging.json)可通过以下命令重现，
不会执行发布包、修改安装或写cgroup：

```sh
python3 tests/verified-staging-review.py \
  --evidence docs/test-evidence-final-v1-verified-staging.json.gz \
  --plan docs/test-plan-final-v1-verified-staging.json
```

实际容器维护使用CPU-only手动策略、占位PID1及有界fsync写盘任务；
验证旧Agent退出、新Agent唯一、准确包内程序替换、保持状态的回退、禁用后八项原值恢复，
并核对原PID1/写盘连续、观测OOM计数不变以及所属容器/cgroup/登记实例清理。
这不是厂商原镜像或真实业务/老化结果；两套暂存工具测试按root执行，
不概括全部非root、旧libc、满盘/掉电或发布后同步失败场景。

本工具可在Linux分发/维护端先执行，再按逐容器维护流程部署已校验内容；
既有DBS/HISDBS容器无需为常驻CRG额外增加Python。暂存工具来自新的预信任源码，
不假称它已包含在旧576候选包里。P09.2得到新的实际候选包安装证据，
最终稳定身份的附件/安装及原长期验收仍待，不新增整项完成声明。
首次派发前的源码审查补齐了过严umask的处理和实测用例；
[初始未派发计划](test-plan-final-v1-verified-staging-before-umask-review.json)保留原件，
该修正使用v2身份，随后进行了首次原生派发。首次[试验失败](test-results-final-v1-verified-staging-first-pilot-failure.json)及[准确原件](test-evidence-final-v1-verified-staging-first-pilot.json.gz)保留：53项局部检查通过，第54项因为测试器错误假定BUILD.json是首个文件，延迟屏障未证明而失败；尚未启动Docker维护夹具，不接受完整75项。

当前v3计划只修正测试器：从准确包中确定实际首个普通文件，观察该文件并要求同名DELAYED fsync轨迹；不改变暂存工具、产品二进制或原并发判据。[v2原计划](test-plan-final-v1-verified-staging-before-first-member-fix.json)保留。
测试覆盖真实包暂存/权限、错误身份/摘要/架构、已有目标、FIFO/链接、恶意包形态、
下载路径替换与目标并发创建，以及单临时容器实际升级/回退/禁用。
并发屏障使用 `strace` 延迟真实 fsync，不注入成功返回值；不当作物理慢盘或掉电实测。
失败和原始收据必须保留，修正测试器后用新的冻结身份，不改判旧失败。

实现依据：[Python目录描述符与文件API](https://docs.python.org/3/library/os.html)、
[私有临时文件](https://docs.python.org/3/library/tempfile.html)、
[renameat2不覆盖语义](https://man7.org/linux/man-pages/man2/rename.2.html)。
