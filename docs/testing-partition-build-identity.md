# 当前分区组合候选的构建身份验证

未发布组合候选d3706f3在独立干净checkout以Go1.27.3构建并打包，两架构程序与完整build-manifest已与Linux CI一致。此次继续验证完整包和程序摘要，而非只读取清单中的哈希：[实际CI](https://github.com/cuipengdba/ContainerResourceGuard/actions/runs/42882251278)为AMD64/ARM64包生成provenance，为两个ELF生成CycloneDX SBOM证明。

本次4项在线验证全部退出0。强制限定仓库、ci.yml签名工作流、源提交d3706f3完整SHA、next/compatibility-contract源ref以及GitHub托管runner；另外从已验证证书核对来源、签名身份和本次run URI，从statement核对目标文件实际SHA256及predicate类型。两套包及两套程序均匹配。

| 目标 | SHA256 |
|---|---|
| AMD64包 | d4d1efd190fc02b206dc3298d23797ab2e2b452c755f3d9bec88a94ff01df6c3 |
| ARM64包 | 3827d7e617a86917624e1af187cc7e3aadb289c6ae9514d2bca12d849a1021a5 |
| AMD64程序 | 3a1ce7dbf5630f8f1c823005ceb4958653c6c235b2ba5026956ca6597f1926f9 |
| ARM64程序 | d26c2336dfa7b98f3d87d0dad8520d6fbb852f40761b70060b455f91f119fc26 |

随后提取本次在线验证成功的同一bundle，以已安装GitHub CLI/TUF引导的信任根检查离线策略。HTTP/HTTPS/ALL代理指向关闭的本机端口、NO_PROXY清空；未声称操作系统防火墙隔离。正常包前后2次离线验证均成功，中间错误源码、错误签名工作流、追加字节篡改包3次均退出1；检查无连接/代理/超时/404等传输失败，因此没有把一次在线下载失败算作策略拒绝。总计9项，详情及原始回执摘要见[独立结果](test-results-partition-build-identity.json)。

离线bundle只能核对签名时记录的仓库身份；本轮4项在线检查另行核对GitHub当前仓库查询。证明只覆盖具体来源和文件身份，不代表DBS/HISDBS性能、稳定1.0或未测硬件已经通过。既有预览资产、正式长测的固定程序和预算均未改变。

一次错误证书身份反例同时传入互斥的signer-workflow与cert-identity，CLI只拒绝参数组合。这次试验不算安全策略验证，已从9项有效检查中剔除，原始回执摘要仍保留。修正后仅替换合法signer-workflow值，使用同一已验证bundle/信任根并由前后正常验证对照，错误工作流被拒绝；CLI用法错误和网络失败均不计通过。
