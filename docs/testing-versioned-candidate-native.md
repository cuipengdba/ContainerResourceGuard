# 版本化候选的原生控制器复验

[冻结计划](test-plan-versioned-candidate-native.json)与[手动工作流](https://github.com/cuipengdba/ContainerResourceGuard/blob/next/compatibility-contract/.github/workflows/versioned-candidate.yml)只验证未发布v1.0.0的真实产物，当前尚未运行。精确d370源码的50个生产文件和3个原生测试输入逐项核对，Go1.27.3配方保留；四个原生runner分别要求实际6.x/7.x、AMD64/ARM64和cgroup2fs，环境不符在创建夹具前拒绝。

先要求两个ELF、两个包、两个SBOM、清单及SHA256SUMS八项与独立Windows构建逐字节相同，再使用相同摘要的对应目标程序执行既有22项真实自身cgroup测试。每格原程序来源为d370，驱动工作流修订另行记录；计划共88项，必须全部通过并正常清理自有容器、cgroup、存储和临时目录。失败、真实包差异或环境不符均保留，不重命名其他程序的结果。

此工作流不上传GitHub Release资产、不生成或宣称来源证明，也不代表厂商业务、物理多盘或长期验收。它不能将当前开发版本的七天时长计入新v1.0.0摘要；后续真实路径业务及长期阶段仍按实际程序分别归档。
