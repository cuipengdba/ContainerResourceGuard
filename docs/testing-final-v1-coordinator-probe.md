# 长期验收协调器：失败输出与有界只读查询

## 背景及需求归档

原[1396长期试验](testing-final-v1-long1396-terminal.md)在baseline约4.23小时失败。直接触发点是协调器的`kubectl get pods -A -o json`退出1，旧执行器丢弃了原stderr/stdout；底层API错误原因未知。旧失败、原输入、时长及清理原件保持，不追认24小时通过。

本次开发仅修改验收协调器，不编入CRG，不增加资源控制项，不改变DBS/HISDBS启动链。需求及任务是：保留失败命令原始字节；限制记录容量；在原15秒总查询预算内处理短暂只读查询失败；不重试任何变更命令；为新的从零计时长期试验建立独立身份。原业务标准、资源额度和周期保持。

## 实现

- `tests/coordinator-probe-v1/probe.py`保留失败命令stdout/stderr原始字节，包括非UTF-8与超时前的部分输出；目录0700、文件0600、排他新建，校验归属及符号链接。
- 每次最多保留stdout 4MiB、stderr 64KiB，明确记录原字节数、截断及保留内容SHA256；64MiB/512文件容量不足则拒绝继续。成功命令不持续积累输出。`subprocess.run`仍捕获进程输出，本改动不声称实现流式内存上限。
- 只有全部Pod只读查询允许最多3次尝试，共享原来的15秒总观察时限；每次API超时随剩余预算缩短。超时/非零退出均留原件。
- v1 `List`或`PodList`完整清单、逐Pod身份必须有效。坏JSON、超大输出、缺少身份或出现另一个`crg-vendor-lab-*`命名空间的Pod立即拒绝推进；所有Pod阶段都阻止，不重试到它消失。
- create/delete/exec/nsenter等命令只执行一次。原错误内容留在私有文件，不盲目公开真实集群返回值；公开归档只含已核对的模拟错误。

## 实测与独立复核

在已有amd64/Linux5.14测试节点，运行冻结源码`probe.py` SHA256 `8bbffbf5615800cc53dbfb3ee04f7294cb2121f5de43f0af44aa6b54df211f9e`和`native.py` SHA256 `cbbce5c3f37c774cedcb7806ad8f84106437d1929ddf1b0eacdcd1e18179092a`。24项通过，模拟CLI进程均已结束；另外执行一次真实健康集群的只读查询，没有创建Pod、修改cgroup或运行CRG。

覆盖一次/两次错误后恢复、三次错误拒绝、其他Pod四种阶段立即阻止、6种无效清单、实际15秒挂起和部分输出、慢失败后缩短剩余超时、拒绝放宽预算/次数、4MiB+1输出截断、非UTF-8原字节、变更命令不重试、启动失败、不安全目录及容量耗尽。

114份原始文件均保留在[证据归档](test-evidence-final-v1-coordinator-probe.json.gz)，归档SHA256 `5e7cb24236a64c2fd379c5fc1774a5b799ec33491bc0c7e333b0f1e7160d555d`。独立离线复核程序不执行候选或调用集群：

```sh
python3 tests/coordinator-probe-v1/review.py --evidence docs/test-evidence-final-v1-coordinator-probe.json.gz
```

[复核结果](test-results-final-v1-coordinator-probe.json)。模拟错误不能还原原1396丢失的API错误内容，也不等于业务长期通过；这两项边界保持。

## 后续任务

将已测模块绑定到[全新1728长期方案](testing-final-v1-long1728.md)，入场再次核对旧任务终态、全部进程/cgroup/namespace清理、节点健康、业务前置资格及全部冻结文件。每个阶段均从新时钟计时，原1396与旧78时间不继承。长期结果及老化后验收完成前，不发布稳定1.0。
