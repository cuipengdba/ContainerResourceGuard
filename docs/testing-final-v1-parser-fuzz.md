# 固定源码：配置与标定解析器模糊测试

准确源码 ced461705ebc27315a59aefe463f9b4af47130a3，go version go1.27.3 windows/amd64。418份Go源码/测试及模块输入在执行前后逐字节保持；这次是Windows amd64原生解析器测试，不是Linux内核控制或最终产品ELF运行。既有最终ELF没有重建。

| 目标 | 配置时长秒 | 目标实际秒 | 最后报告执行次数 | 新增interesting / 总数 |
| --- | --- | --- | --- | --- |
| FuzzDecodeConfig | 300 | 301.02 | 3422239 | 480 / 485 |
| FuzzDecodeProfile | 300 | 301.02 | 3092716 | 451 / 453 |

每个目标2个worker，依次执行 go test ./internal/guard -run=^$ -fuzz=^目标名$ -fuzztime=300s -parallel=2 -json -timeout=7m。目标/包pass事件、至少300秒进度、退出0、空stderr、逐字节摘要及执行前后输入均独立复算；中间0/sec进度原样保留。执行次数是Go模糊引擎的尝试计数，不代表不同输入数量或业务测试数量。

既有回调在Decode成功后调用Config.Validate或ValidateProfile，覆盖本次输入空间内的panic/崩溃/Go fuzz失败；不单凭这两项证明全部语义正确、Linux/厂商运行时、持久化中断、持续撤销权限、慢/满文件系统或真实掉电。P09.3仍是部分完成，剩余边界单独验收，不因本轮通过整体勾选。

[冻结计划与全部输入摘要](test-plan-final-v1-parser-fuzz.json)、[独立复算](test-results-final-v1-parser-fuzz.json)、[7份准确原件含完整事件和原执行器](test-evidence-final-v1-parser-fuzz.json.gz)。稳定1.0尚未接受。
