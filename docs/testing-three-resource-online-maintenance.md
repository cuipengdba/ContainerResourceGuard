# 三资源在线维护：第13轮首次安装失败

2026-11-10，DBS和HISDBS均通过原启动、缓存、旧Agent摘要及quiesce检查，共10项；但**第一次binary-install返回1**，后续安装/回退/恢复Agent与600秒业务验收均未完成。[结果](test-results-three-resource-online-maintenance-initial.json)保留两套程序、预算与失败位置。自有Pod和namespace已删除，随后独立确认namespace不存在。

只读复核：两套安装文件仍为已发布预览7638ee9的原摘要，recovery为空；旧build-info仅含版本/提交/系统/架构，没有lock_protocol或journal_versions。候选d6ea657的checkPreviousProtocol要求旧程序显式声明同一锁协议与journal v1，并在创建备份或替换前检查。该事实与此次拒绝一致；原脚本没有保存失败stdout/stderr，不能把推断写成原始错误输出。

这是首次安装失败，不能计为在线升级/回退通过。原生工作负载刚进入测量就因夹具清理终止，零错误的空样本也不计作600秒通过。保护条件继续保留，不为了通过测试而跳过旧程序协议校验。

已发布main预览到组合开发线的在线保留限额升级目前不列为支持路径；首次迁移应独立规划旧程序disable恢复并校验原值、停止旧辅助入口后再安装新程序，而非绕过检查继续写旧状态。实际部署另按目标容器审核，不在本轮修改原业务。后续协议已声明的开发程序往返测试单独冻结来源和预算，也不能替代最近两个已发布次版本门槛。
