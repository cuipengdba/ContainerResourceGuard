# 旧preview.4七天任务终态

原任务5605b847…、源码180c86ad7986a76526a41575cc1c176d5da98a9c已经失败退出，未完成请求的604800秒。DBS/HISDBS分别运行108021.099/108018.451秒，SQL成功54007/54005且零错误，API各21604次成功且零错误；这段约30小时的部分数据不能计为七天通过，也不转移给preview.5源码。

第六轮周期检查run_id=2026111257605：DBS的初始数据及物理备份完成两项通过，随后standby的pg_ctl启动退出1；HISDBS第六轮未执行，engine cleanup未接受。不是把此次物理备份计成超时。standby.log将实际服务日志转向/opt/postgresql/pg_log，根因仍需独立读取服务日志确认，不推断OOM或IO因果。第五轮DBS执行接口6.431522秒超过原5秒门槛的既有失败仍保留。

节点16:08:28独立只读确认：原runner/worker/campaign的PID/start消失、namespace及两组父叶消失、51个初始登记进程实例消失。此范围不能改写第六轮engine的cleanup=false。没有重启任务或借用其它老任务时间。

[终态分析](test-results-memory-high-seven-day-terminal.json)和[九份4123389字节精确原件](test-evidence-memory-high-seven-day-terminal.json.gz)包含原总报告、完整campaign报告、两份native统计、第六轮engine报告、wrapper/standby/物理备份日志。原冻结计划和初始报告保持；新来源需要另行符合原长期标准，稳定1.0未接受。
