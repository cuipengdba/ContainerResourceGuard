# 固定最终候选：完整CLI输出组合的冻结输入

11份非二进制输入和1份固定最终ELF，不重建或重复打包ELF。本目录是隔离真机验收程序，不是生产多容器管理器。

| 输入 | SHA256 |
| --- | --- |
| maintenance-business.py | d3f6a28570767e629d7a1fb405c96558375258cdef538bea45d8b9c1f6ff101e |
| runner.py | 2b80aaac45de0e069e629a565c716b791f623093cc76a3d8f2d9b65ad84a5ea5 |
| artifact-transfer.py | 35aa6dd905d61602d29ba4cd720d320b9a8c9b450d3ff7cd413aceaeb93c6d13 |
| tests/manual-maintenance-contract.py | 42edbdfb1b727f02c70a8e45d362748d78aeb3bc43f586263bd811660b743985 |
| binaries/candidate | 9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8 |
| tests/vendor-soak-load.py | ba87ef2d646b723eb8419de25ffcd736f7a5b0925716f4b638761dff70bb2461 |
| tests/vendor-soak-campaign.py | b49d5a73654c5cf7c93b04851f3409eea318b3a9c71c0e8f601f252a3dda07ea |
| tests/vendor-engine-smoke.py | b0d4fe313156743ff1424b46eb58c5ab5b8e1f2c91851420023f5f018dd08e5c |
| examples/optional-agent.sh | f7e7208f58bac7066d75d49cb17199b720e3d05bb5953e2a7a7800f881b54b79 |
| tests/output-matrix-checks.py | f4afc5f6ff855eb08f576071105b5880712a33a1939b3bde5b7bee1af74096a2 |
| tests/output-profile.json | 00e35e91594ed0ad1075a196c20bd8f4c6628c346c4bd6e901ac05d4cc90ef6b |
| plan.json | f3228ea48660a2c8df85a1937a8472da18ab12ed4d47194399ee6e3d3fd9f276 |

[完整协议](../../docs/testing-final-v1-output-matrix.md)、[计划](../../docs/test-plan-final-v1-output-matrix.json)、[19项本地核对](../../docs/test-results-final-v1-output-local-preflight.json)、[原生准入](../../docs/test-results-final-v1-output-native-preflight.json)。
