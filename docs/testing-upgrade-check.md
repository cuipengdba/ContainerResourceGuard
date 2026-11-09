# 兼容预检与私有备份实测

2026-11-10，源码 cb7b37fb1de88c18f8de3570f486ce74f59811ed，Linux Go 1.22.5、5.14/cgroup v2/amd64。静态二进制 SHA256：0bed7e8ae27f04d25019aecf7dd009199741fbb903f8947f4969ae579ee2b460。尚未发布 v0.7.0。

Linux race/vet 通过，guard 覆盖率 72.0%；16 个普通文件建模的子进程强杀点、12 个辅助进程/生成 supervisor 场景通过。[CI](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42708349537) 也通过。强杀不是宿主掉电证据，源码新增部分分支仍需继续验收。

真实临时容器内 16 项检查通过：活动写入者拒绝预检/备份；只读器报告锁/格式能力；夹具外部 CPU 改值在 disable 时保留且恢复失败可见；禁用快照仍保留该条真实原值；新备份 0600/不覆盖；状态目录及符号链接别名保护；损坏日志/未知控制项及未知 profile 拒绝；旧身份 disable 标记不构成当前升级许可；整个预检与备份过程没有改写原值日志或外部 CPU 值。夹具显式恢复自己改过的值后，CRG 完整恢复、重新启用，原占位 PID 1 全程存活。临时 namespace 已确认消失。

只公开 [检查名称与结果](test-results-upgrade-check-linux-amd64.json)，不公开真实私有备份、旧值、容器标识或配置内容。它们属于私有恢复材料。

此项未验证厂商业务在线升级、未知旧二进制锁协议、自动导入/迁移、断电、完整安装卸载及二进制失败回退；不能据此关闭全部 P08 或宣布稳定版。语义与操作见 [开发文档](install-upgrade.md)。


## 跨读取器暂停检查

05abe0d 的新 CLI 对仍运行 cb7b37f 的独立占位容器执行 quiesce；20 项检查通过，源摘要、二进制摘要与逐项结果见 [新增报告](test-results-quiesce-linux-amd64.json)。实际 CPU/内存限额和 journal 原字节保留，两把锁空闲，私有备份保留真实原值；enable 后旧 Agent 继续相同预算，PID 1 存活。也重跑了未知 journal/profile、旧身份 marker、外部值冲突和输出覆盖保护。Linux Go1.22.5 race/vet、16 项强杀模型、12 项 shell 故障检查通过，自建 namespace 确认已移除。这证明维护暂停的跨版行为，未替代后续实际二进制切换演练。


## 实际二进制往返

a1327dc、Go1.22.5 Linux amd64 的独立占位容器完成 16 项真实检查：[逐项报告及两轮历史失败](test-results-binary-upgrade-linux-amd64.json)。旧 cb7 程序经原 helper 管理，从可写专属安装目录运行；新候选在另一 staging 路径执行维护。活跃写入者拒绝切换，新旧摘要错误、已有备份目录、配置变化、篡改旧副本和外部改动现有目标均拒绝；合法替换保留内核 CPU/内存限额、journal 原字节与 PID 1。

私有备份保留真实原值；新候选兼容预检通过。即时回退、再安装并只恢复新 Agent、再次暂停并回退旧 Agent、恢复旧 Agent 均完成，最后 disable 恢复运行时真实 CPU/内存原值，自建 namespace 确认已移除。Linux race/vet、原强杀模型与 shell 辅助故障检查通过。此处没有厂商原部署在线升级、真实掉电或完整模板安装证据。

首轮发现提交前复查只解析状态却未携带仍被持有的锁语义，导致合法切换被拒；修正后第二轮即时往返与新 Agent 恢复通过，但重新暂停的标记时间变化使保守快照拒绝回退。现只忽略同身份停用标记的记录时间，版本/身份、journal/pending、profile、有效配置和目标摘要仍核对。两轮失败不改写为通过，备份目录与私有原记录保留；第三轮用新目录完整重测。
