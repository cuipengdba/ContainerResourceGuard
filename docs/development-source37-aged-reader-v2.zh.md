# 源37新长稳的只读老化血缘门禁

## 本轮完成与边界

本轮实现[新只读reader](../tests/live-capacity-aged-v1/lineage.py)、[准确绑定](../tests/live-capacity-aged-v1/binding.json)和[故障检查](../tests/live-capacity-aged-v1/checks.py)。当前只接受门禁代码的13组Windows/13组Linux合成故障测试、真机基线pending和提前采集拒绝；**没有七天封存、没有老化执行器、没有老化业务或稳定版本验收通过**。[完整复核](test-results-source37-aged-reader-v2.json)、[冻结6文件计划](test-plan-source37-aged-reader-v2.json)、[原字节证据及失败](test-evidence-source37-aged-reader-v2.json.gz)归档。

旧vendor-versioned-aged-preflight/postflight仍绑定d370/旧78，不能用于当前源37/新1880。旧capture必须在七天native worker运行时采集原始目录、日志前缀和身份；因此现在先做好新reader，防止等结束后才发现无法补采。新代码复用原base reader/auditor，摘要固定；旧文件不改，不借用旧时长或旧通过。

## 本轮开发任务与实际核验

1. 固定源37准确AMD64 ELF、新1880计划、全部19上传输入、sole launch/worker原始JSON摘要及PID/start。24h observe、同容器24h enforce、新604800秒/28周期均调用原审计器；终态必须原16项协调器检查、4/4/28周期、零错误/原延迟覆盖及完整清理。假时间样本只用于测试，不能授予真实时长。
2. 仅七天阶段且前两段原24h接受后允许采集。完整保留旧capture的Pod UID/容器集合/零重启、独立cgroup、唯一Agent/cache/native、准确ELF、目录inode、私有配置和原日志前缀检查。唯一资源语义差异是用户已要求的memory.high，memory.max外部硬上限及其余五项控制必须原值不变，原恢复保护不取消。旧postflight criteria原文保留在binding，旧memory_max_bytes字段注明历史语义；当前参考为high20001980416/外部max21474836480。
3. 封存必须绑定新计划、唯一launch、已接受baseline/enforce报告和源37；终态继续复用原目录/文件/journal/原日志前缀/至少7日日志/旧cgroup消失和新目标未使用检查。没有自动执行、后台触发或执行开关；即使未来血缘ready也须另行冻结适配后的老化执行器和完整原标准。
4. Windows首次12组有1失败/3错误，源于测试夹具POSIX/Windows路径及Linux根路径检查；修正后12组通过，但不算真机证明。首次Linux12组合成通过，实际reader因错误期待campaign顶层run_id而拒绝。只读诊断记录KeyError；真实ID来自协调器阶段和原生worker。新版本增加“campaign无顶层run_id”的回归，最终两平台各13组通过，原16/24h/24h/7d标准不减。
5. 真机准确源码在独立工具目录运行两个只读调用：当前baseline返回exit2/pending/capture_allowed=false，--capture返回exit1/CAPTURE_ONLY_DURING_FRESH_SEVEN_DAY。未采集虚假seal，未触发旧执行器。19长测输入前后逐字一致；之后独立观察原runner/worker/recorder、两角色八控制/实际Agent保持。

## 后续操作

从匹配且可信的完整仓库检出，在受权测试节点运行：

```bash
python3 -B tests/live-capacity-aged-v1/lineage.py
# 只在实际measuring-acceptance阶段且前两段原24h通过后采集stdout，私下保存并固定摘要：
python3 -B tests/live-capacity-aged-v1/lineage.py --capture
# 终态后，以可信渠道固定的原始seal和摘要核对：
python3 -B tests/live-capacity-aged-v1/lineage.py --seal /private/lineage-seal.json --seal-sha256 "$TRUSTED_SEAL_SHA256"
```

默认调用不写任何文件、不发信号、不启动业务、不改cgroup。封存stdout包含实验身份和配置文件摘要，私下保存；不要将其视为通过。读失败或进程身份丢失时先只读排查，禁止因此重启1880。真实七天开始后尚须实际采集并复核，再适配/冻结/验证老化故障、恢复、维护、升级执行器；旧source/旧78路径不可直接替换为当前路径后运行。

[当前长稳](development-new-long1880.zh.md)、[当前交付](release-readiness-current.md)、[完整需求](requirements.md)、[原52项任务](current-52-task-audit.md)、[源37打包演练](live-capacity-package-rehearsal.zh.md)保持独立资格。当前开发不增加任务完成声明，也不改变每容器一对一、三百分比、high/BPS/v2跳过及滚动日志等产品实现。
