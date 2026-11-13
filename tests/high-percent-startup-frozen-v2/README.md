# 冻结的PSI兼容启动矩阵

见[本轮计划](../../docs/testing-high-percent-startup-psi-compatible.md)；这是授权隔离测试工具，固定临时目录，不能直接作生产入口。preview.4程序摘要不变，二进制不重复入库。

在v1冻结工具基础上，仅显式处理可选PSI缺失/无读权限、在探针等待前保存业务错误，并新增首轮终态/精确清理前置校验；另换唯一隔离目录及身份。`startup-sample.py`的io.stat/cpu.stat/memory.current仍必须可读，PSI其他错误继续失败。资源、原业务、预算、探针、检查数量与标定逻辑不变。

38项离线资格检查为21原门槛/解析、9采样兼容、8前轮终态/清理；绑定最终源摘要，不是任何真机或业务接受。原失败不可覆盖，重测前再次验证首轮runner/四驱动/四namespace/各父叶及登记PID/start全部消失。
