# 采集适配器v3的双父历史合并

本次main真实合入集成历史，两个准确父提交均保留。集成候选产品源37ca44e和全部19项长测输入不变。当前52项定义/18项完成声明与main一致；机器登记采用集成身份。

main原始登记和审核保留为本次第二父Git对象，不再重复压缩整份巨大登记。逐字摘要与Git blob ID在当前机器登记的source37_capture_v3_documentation_merge中固定；历史已发布压缩件全部保留。这种保存方式不改原60MiB/4000文件边界。

main准确父提交：`be85a1e435c17115abc2d15865b17d9a5d0d41da`，原件可查看[完整登记](https://github.com/cuipengdba/ContainerResourceGuard/blob/be85a1e435c17115abc2d15865b17d9a5d0d41da/docs/current-task-registry.json)和[机器审核](https://github.com/cuipengdba/ContainerResourceGuard/blob/be85a1e435c17115abc2d15865b17d9a5d0d41da/docs/current-52-task-audit.json)。.gitattributes保留全部集成规则和main非注释规则，原逐字CRLF冻结规则不变。

[新执行器保护检查](development-source37-capture-v3.zh.md)只接受新采集Linux8组、Windows6通过/2跳过及实际pending/提前采集拒绝；完整受控夹具复现并修复旧roles/path_clean采集缺陷，冻结旧件不改。用户已明确回退仅支持high、旧max应拒绝并留不兼容；旧max managed-resume排除当前支持范围，原历史定义与未通过事实保留。high目标仍待实际恢复，其余原门槛保持，不冒充两个minor。真实七天seal、原老化执行和稳定发布均待。[当前交付](release-readiness-current.md)、[原长稳](development-new-long1880.zh.md)继续独立验收。旧失败及unknown原因保持，无时钟转移，preview八资产不变，PR仍草稿。
