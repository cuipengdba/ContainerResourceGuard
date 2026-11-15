# 打包文档合并记录

本次只处理打包文档同步后的两个冲突，不合并或发布稳定版，不改变正式1396长期任务及其程序、输入或计时。原52项定义和18项完成声明两侧一致，保持不变。

输入为集成提交 `0a639109c93aac9ae6b27e1096523c515f41b508` 与 main 文档提交 `ca1448309c34dda80a39505d4de0b13e4df535e0`。冲突仅在任务登记及本轮安装说明历史副本。当前任务登记保留集成分支的完整状态与历史，main 版[准确完整原件](current-task-registry-main-before-package-integration.json)另行归档，SHA256 `49b3e46446f03b2ba947df1f01cd7a66d39ddaa40261d2d8716803e70d8733dc`；当前登记明确链接该原件，不将分支记录删除或伪装成新验收。

[原集成安装说明](installation-before-package-rehearsal.md)与[原 main 安装说明](installation-main-before-package-rehearsal.md)分别保留；当前[安装说明](installation.md)和[候选打包结果](final-v1-package-rehearsal.md)继续使用本次已核对的来源/完整性流程。历史内容不代表当前安装步骤。

临时索引中逐文件解决文档，提交前验证50份运行时源码与最终候选身份一致，且相对集成输入没有cmd/internal/go.mod/scripts/workflow变化；对提交文档闭包和链接再核对。此合并仅使草稿PR具备可复核的文档历史，main 产品实现仍等待整版验收后合入。
