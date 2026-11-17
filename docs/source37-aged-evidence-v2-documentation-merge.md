# 老化恢复证据v2与用户回退范围的双父历史合并

本次main真实合入集成历史，两个准确父提交均保留。集成候选产品源37ca44e和全部19项长测输入不变。当前52项定义/18项完成声明与main一致；机器登记采用集成身份。

main原始登记和审核保留为本次第二父Git对象，不再重复压缩整份巨大登记。逐字摘要与Git blob ID在当前机器登记的source37_aged_evidence_v2_documentation_merge中固定；历史已发布压缩件全部保留。这种保存方式不改原60MiB/4000文件边界。

main准确父提交：`c3d3a7ab2cddc20a42f5a9c0d9617c985fa9c190`，原件可查看[完整登记](https://github.com/cuipengdba/ContainerResourceGuard/blob/c3d3a7ab2cddc20a42f5a9c0d9617c985fa9c190/docs/current-task-registry.json)和[机器审核](https://github.com/cuipengdba/ContainerResourceGuard/blob/c3d3a7ab2cddc20a42f5a9c0d9617c985fa9c190/docs/current-52-task-audit.json)。.gitattributes保留全部集成规则和main非注释规则，原逐字CRLF冻结规则不变。

[新执行器保护检查](development-source37-aged-evidence-v2.zh.md)只接受Linux执行保护14/独立审核16组，Windows14+15/1跳过及三个实际pending入口。用户已明确回退仅支持high、旧max应拒绝并留不兼容；旧max managed-resume排除当前支持范围，原历史定义与未通过事实保留。high目标仍待实际恢复，其余原门槛保持，不冒充两个minor。真实七天seal、原老化执行和稳定发布均待。[当前交付](release-readiness-current.md)、[原长稳](development-new-long1880.zh.md)继续独立验收。旧失败及unknown原因保持，无时钟转移，preview八资产不变，PR仍草稿。
