# 当前d370源码解析器fuzz终态

2026-11-11，Windows AMD64/Go1.27.3，在私有独立目录对固定`d3706f3ea7ad279fea818e5ad1aa62ac5d3f8710`源码运行两个现有fuzz目标。两个目标均请求600秒、750秒墙钟上限、双worker；全程没有修改当前程序源码。[冻结计划及12项附加种子](test-plan-d370-parser-fuzz-windows.json)、[实际结果](test-results-d370-parser-fuzz-windows.json)。旧50671aa源码的[原fuzz结果](https://github.com/cuipengdba/ContainerResourceGuard/blob/7787ffb0abacf2616fb46905457b260da5282ab3/docs/test-results-three-resource-parser-fuzz-windows.json)保留，不混作本轮证据。

| 目标 | Go报告秒数 | 墙钟秒数 | 执行次数 | exit |
|---|---:|---:|---:|---:|
| FuzzDecodeConfig | 601.727 | 646.234 | 10,487,407 | 0 |
| FuzzDecodeProfile | 601.328 | 603.156 | 11,192,784 | 0 |

总计21,680,191次执行，均PASS。真实执行会话退出0；Python运行器和两个Go PID独立确认已不存在。50个生产文件的SHA256在每个目标前后保持固定合同，fuzz目标源码也与固定源码一致。完整日志：[配置](fixtures/fuzz-d370-config-windows.log.txt)、[profile](fixtures/fuzz-d370-profile-windows.log.txt)；日志摘要、原结果摘要和启动器摘要另记于结果JSON。

目标函数调用Decode后，仅在解码成功时调用Validate或ValidateProfile，并丢弃校验错误。因此本轮证明这组探索输入没有触发崩溃/超时，不证明所有非法输入均被正确拒绝。`GOMEMLIMIT=256MiB`为Go软目标，不是进程内存硬上限；本轮不是Linux发布ELF执行、cgroup写入、慢/满文件系统、真实掉电或厂商长期验收。

## 复现要点

从上述固定源码创建独立工作目录，使用Go1.27.3，隔离GOCACHE并设置GOTOOLCHAIN=local、GOPROXY=off、GOSUMDB=off、GOMAXPROCS=2、GOMEMLIMIT=256MiB。根据计划重建12个附加corpus文件后，按顺序运行：

```bash
go test ./internal/guard -run='^$' -fuzz='^FuzzDecodeConfig$' -fuzztime=10m -parallel=2
go test ./internal/guard -run='^$' -fuzz='^FuzzDecodeProfile$' -fuzztime=10m -parallel=2
```

附加种子的文件字节必须与计划中SHA256相同，可在独立源码目录中用下述Python重建；计划路径指向已经下载的本轮冻结计划：

```python
import hashlib, json
from pathlib import Path
plan = json.loads(Path("test-plan-d370-parser-fuzz-windows.json").read_text(encoding="utf-8"))
for row in plan["additional_private_workspace_corpus"]:
    data = ("go test fuzz v1\n[]byte(" + json.dumps(row["input"], ensure_ascii=True) + ")\n").encode()
    assert hashlib.sha256(data).hexdigest() == row["sha256"]
    target = Path("internal/guard/testdata/fuzz") / row["target"] / row["name"]
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(data)
```

每个目标的750秒墙钟上限由本次外部启动器执行，不能以单独Go命令声称也配置了该上限。已有输入大小/格式单测和异常文件系统、持久化中断、真实强杀/掉电证据分别按P09.3核对；不因这两项PASS将整项任务或稳定版标为完成。已发布preview.2的资产保持冻结。
