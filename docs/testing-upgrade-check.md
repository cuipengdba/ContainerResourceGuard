# 兼容预检与私有备份实测

2026-11-10，源码 cb7b37fb1de88c18f8de3570f486ce74f59811ed，Linux Go 1.22.5、5.14/cgroup v2/amd64。静态二进制 SHA256：0bed7e8ae27f04d25019aecf7dd009199741fbb903f8947f4969ae579ee2b460。尚未发布 v0.7.0。

Linux race/vet 通过，guard 覆盖率 72.0%；16 个普通文件建模的子进程强杀点、12 个辅助进程/生成 supervisor 场景通过。[CI](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42708349537) 也通过。强杀不是宿主掉电证据，源码新增部分分支仍需继续验收。

真实临时容器内 16 项检查通过：活动写入者拒绝预检/备份；只读器报告锁/格式能力；夹具外部 CPU 改值在 disable 时保留且恢复失败可见；禁用快照仍保留该条真实原值；新备份 0600/不覆盖；状态目录及符号链接别名保护；损坏日志/未知控制项及未知 profile 拒绝；旧身份 disable 标记不构成当前升级许可；整个预检与备份过程没有改写原值日志或外部 CPU 值。夹具显式恢复自己改过的值后，CRG 完整恢复、重新启用，原占位 PID 1 全程存活。临时 namespace 已确认消失。

只公开 [检查名称与结果](test-results-upgrade-check-linux-amd64.json)，不公开真实私有备份、旧值、容器标识或配置内容。它们属于私有恢复材料。

此项未验证厂商业务在线升级、未知旧二进制锁协议、自动导入/迁移、断电、完整安装卸载及二进制失败回退；不能据此关闭全部 P08 或宣布稳定版。语义与操作见 [开发文档](install-upgrade.md)。
