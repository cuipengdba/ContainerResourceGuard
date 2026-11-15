# 固定最终ELF：CLI与可选启动安装验收协议

10份非二进制输入及1份固定最终ELF逐字节冻结。ELF不重建；仅将摘要存档，不纳入此目录。此目录为隔离真机测试程序，不是生产安装脚本。

实际DBS/HISDBS启动/路径/只读CCG保持，副本只在各容器私有 /recovery 中安装/卸载，永不执行副本或额外启动厂商进程。原600秒SQL/API门槛及manual参考配额保持；不新算备份/同步/恢复或长期时长。

| 输入 | SHA256 |
| --- | --- |
| maintenance-business.py | d89b41e3646832724c0007cff6a3ac8055bd244356b79d56557b2fd6b79b06c0 |
| runner.py | 811d391a42149830a3f01516d0baebdd486c49c11fbac1bfef5ed89e7c19187d |
| artifact-transfer.py | 8a89dc7df6af1286c4b9b6c7837fdc969b9c746063c877403d716bbe4496bfb8 |
| tests/manual-maintenance-contract.py | 42edbdfb1b727f02c70a8e45d362748d78aeb3bc43f586263bd811660b743985 |
| binaries/candidate | 9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8 |
| tests/vendor-soak-load.py | ba87ef2d646b723eb8419de25ffcd736f7a5b0925716f4b638761dff70bb2461 |
| tests/vendor-soak-campaign.py | b49d5a73654c5cf7c93b04851f3409eea318b3a9c71c0e8f601f252a3dda07ea |
| tests/vendor-engine-smoke.py | b0d4fe313156743ff1424b46eb58c5ab5b8e1f2c91851420023f5f018dd08e5c |
| examples/optional-agent.sh | f7e7208f58bac7066d75d49cb17199b720e3d05bb5953e2a7a7800f881b54b79 |
| tests/cli-supervisor-checks.py | 0e27567c2c5a8b96664c36176d60d73a9ae2660306e03b8c8c4a1c7b6df1edc9 |
| plan.json | 6b2a9f475eb68f1d8f64e6a949e96fa489ee7293029863c35d9fbbf8dae52759 |

[计划与范围](../../docs/testing-final-v1-cli-supervisor.md)、[完整计划](../../docs/test-plan-final-v1-cli-supervisor.json)、[17项本地核对](../../docs/test-results-final-v1-cli-supervisor-local-preflight.json)、[原生准入](../../docs/test-results-final-v1-cli-supervisor-native-preflight.json)。
