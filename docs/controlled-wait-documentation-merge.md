# 受控SQL等待诊断后的双父历史合并

main历史真实合入集成分支，准确双父保留。当前登记和机器审核使用集成身份，并逐字归档main当前[完整登记](current-task-registry-main-before-controlled-wait-integration.json)及[机器审核](current-52-task-audit-main-before-controlled-wait-integration.json)，含两次失败和第三版受控诊断结果。52项定义/18项既有范围声明一致，CRG产品源37ca44e与全部冻结输入不变。

.gitattributes保留集成全部规则并覆盖main所有非注释规则；[main属性原件](controlled-wait-main-before-merge.attributes.txt)保留。CRLF adapter原生绑定及legacy字节规则不变，外来文件不修改。

[当前诊断结果及限制](development-controlled-sql-wait.zh.md)独立说明。受控120秒负向测试不能替代原18项/600秒，PSI不可用不冒充零压力；旧1761 DBS错误原因未知，后续对照/长稳/老化后维护/稳定发布门槛保留。此合并只整理历史，不合并草稿PR，不发布稳定版本。
