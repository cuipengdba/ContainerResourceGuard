# 固定最终ELF受控二进制维护协议

10份非二进制输入逐字节冻结；两个ELF只记录摘要，不将源码重新构建为替代程序。previous来自实际公开preview.5包，candidate为已固定但未发布的v1.0.0 ELF。

该目录为隔离真机验收工具，不是生产安装脚本。只建立自己命名空间/目录，前轮终态与清理未证明则在创建前拒绝；每容器一份Agent，原业务路径/镜像和只读CCG保持。

| 输入 | SHA256 |
| --- | --- |
| maintenance-business.py | 5375499dbe57e65265210d52dfe6f71167c1c0a833127eefd36409920a7e3574 |
| runner.py | 4bc4218f6de97919d6137a721e0c67a47e93cd82d6291321a40fe9c39ca8cec3 |
| artifact-transfer.py | cb4acbc1507082b818ba761ab183aba0415e4c939687bf90c06567031e13b66b |
| tests/manual-maintenance-contract.py | 42edbdfb1b727f02c70a8e45d362748d78aeb3bc43f586263bd811660b743985 |
| public-artifact-binding.json | 807ee84ac8692dd8ab3ba882d3efda594691c8d0bcafc96d475ae15ab8e0eaa9 |
| binaries/previous | be6b0aa9f9bf932d8b02872e86a9cffcfea6d7199e39c274694dce904af07333 |
| binaries/candidate | 9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8 |
| tests/vendor-soak-load.py | ba87ef2d646b723eb8419de25ffcd736f7a5b0925716f4b638761dff70bb2461 |
| tests/vendor-soak-campaign.py | b49d5a73654c5cf7c93b04851f3409eea318b3a9c71c0e8f601f252a3dda07ea |
| tests/vendor-engine-smoke.py | b0d4fe313156743ff1424b46eb58c5ab5b8e1f2c91851420023f5f018dd08e5c |
| examples/optional-agent.sh | f7e7208f58bac7066d75d49cb17199b720e3d05bb5953e2a7a7800f881b54b79 |
| plan.json | 62d781dd81addd02ff809dac13ab17ae006ed75711112e2010659d2ae9e5eacf |

[计划与范围](../../docs/testing-final-v1-binary-maintenance.md)、[完整计划](../../docs/test-plan-final-v1-binary-maintenance.json)、[本地17项核对](../../docs/test-results-final-v1-binary-maintenance-local-preflight.json)、[原生准入](../../docs/test-results-final-v1-binary-maintenance-native-preflight.json)。
