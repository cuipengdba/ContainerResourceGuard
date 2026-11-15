# 安全暂存：目录深度边界修复

2026-11-16 CST。此项修复可选的维护端 `scripts/stage-release.py`，
不改变常驻 Agent、三资源策略、DBS/HISDBS 启动链或正在进行的真机长期验收。

## 问题及实际复现

旧暂存器已经限制包成员数、体积、类型和路径穿越，但没有限制路径层数。
构造包含真实候选 BUILD、SBOM、ELF 及一个 1100 层普通目录的包后，
两个独立原生 VM 均出现 `RecursionError`：同步和失败清理使用递归，
未能完整清理本次私有临时目录。目标目录没有发布，既有安装没有替换。

这份构造包的外层摘要由测试明确提供，用来验证工具边界，不能称为已签名发布包。
原工具 SHA256 为 `1d8faf3c88948cf946559878a4f279e4f68f7ab6ecabaeea5b27f52e02fbd952`，
准确来源为 `258c7c3d19f89df50467cd0c3ab810bfa084e041`。
原错误输出、残留计数和随后测试自身的有界、非递归清理结果均保留；
“缺陷复现成功”不表示旧工具处理通过。

## 修复及验收任务

- 写入任何包成员前，先检查整个目录树的成员名称、类型和深度。
- 每个归档路径最多 64 个组成部分，包含隐式父目录；超过即返回明确的
  `state=rejected`、`published=false`，不写包内文件。
- 验证第 64 层目录及文件均可接受；第 65 层目录/文件和第 1100 层目录均拒绝。
  深目录放在正常文件之前或之后都必须在写成员前拒绝，并且无私有暂存残留。
- 原真实候选包/preview.5 暂存、身份/摘要/架构拒绝、权限、并发、
  逐容器升级/回退/禁用和清理检查继续执行。

新暂存器 SHA256 为 `0ff1bc892957862888d5fbd687d3596e6232addca72654cc8f2c4c105aa1465d`。
该限制不改变独立 `verify-release.py` 只读检查的范围；
校验器通过不等于目录一定能在当前文件系统上暂存，仍需检查暂存命令退出状态。
原工具的 [150 项历史结果](verified-release-staging.md)及首轮屏障失败保留原身份，
不冒充新工具证据。

## 新身份原生结果

冻结工具/测试来源：`68a604af517869d03975301bceca73f8887a623e`。
[计划](test-plan-final-v1-verified-staging-depth.json) SHA256：
`e416793d10490cb3f9c707340b49dfe716f1f47aa807754896ba6395d3abe5b1`。

| 实际环境 | 原有检查 | 新工具深度场景 | 旧缺陷复现 |
| --- | --- | --- | --- |
| amd64 / Linux 6.8.0-1070-azure / Python 3.10.12 | 75/75 | 6/6 | 1 |
| ARM64 / Linux 7.0.0-1017-azure / Python 3.12.3 | 75/75 | 6/6 | 1 |

运行：[amd64 43742522227](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/43742522227)、
[ARM64 43742834468](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/43742834468)。
先独立核对 amd64 全部收据，再派发 ARM64；两次之间工具、计划和判据不变。
合计 150 项原有检查、12 个新工具深度场景通过，另有 2 个准确旧工具缺陷复现。
两套实际候选包升级/回退/禁用均保持占位 PID1 和有界 fsync 任务连续，
最后八项原值、所属容器/cgroup 及登记进程清理核对通过。

[完整原始证据](test-evidence-final-v1-verified-staging-depth.json.gz)包含两个准确 ZIP、
78 个成员、GitHub artifact 完整摘要和选定运行身份；不含临时签名下载地址。
ZIP 原字节不改写。先核对完整 ZIP，再核对每个成员 CRC、大小及摘要，
并按实际工具身份、错误输出和清理记录独立复算。
[离线结果](test-results-final-v1-verified-staging-depth.json)可用下列命令复现，
不执行发布包，也不写 cgroup：

```sh
python3 tests/verified-staging-depth-review.py \
  --evidence docs/test-evidence-final-v1-verified-staging-depth.json.gz \
  --plan docs/test-plan-final-v1-verified-staging-depth.json
```

准确候选归档仍为打包修订 `576e6070b09804017ececf3f82fb2f6517c18316`，
产品源码仍为 `ced461705ebc27315a59aefe463f9b4af47130a3`；
两个最终 ELF 未变化，不继承另一嵌入版本的业务持续时长。
暂存器来自预信任新源码，不声称旧候选包已经包含它。

此轮是独立 VM 上的目录深度修复和临时单容器维护验证，
不代替厂商原路径、实际老化、物理满盘/慢盘、掉电或最终稳定发布身份验收。
97 上原长期任务仅作只读状态核对，没有重启、修改限额或启动额外业务夹具。
P09.2/P10.3 增加对应证据，52 项原定义及已有 18 项范围内完成声明保持，
原开放项不因本次通过而关闭，`v1.0.0` 稳定版尚未获验收。
