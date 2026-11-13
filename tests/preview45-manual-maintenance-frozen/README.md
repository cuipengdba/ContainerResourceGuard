# 已发布 preview.4 → preview.5：同预算在线维护冻结工具

两版实际公开AMD64包内的regular ELF逐字节提取核对，不重编译；公开程序绑定与计划记录来源、哈希、下载地址。本目录不提交二进制，执行前按计划放入匹配binaries/previous、binaries/candidate。完整源文件哈希包含在plan.json。

两角色顺序使用原镜像/启动/真实路径/CCG的全新隔离副本，每容器一个Agent。原成功1240手动完整600秒业务16项及54实例清理是独立前置条件，不继承其时间或改称默认20%通过。固定CPU7.2核、memory.high20001980416B、读写64MiB/s、IOPS4096；保留外部20GiB硬上限，不测速。

每角色20项，共40项。先在未开放业务gate时用两个实际程序的readonly doctor预声明同一cgroup/设备身份、三项计划及八项运行时原值；再启动旧版与原CCG。在原600秒native SQL/API测量内，验证quiesce、首次安装立即回退、新版运行后未变化快照回退、再次升级、变化配置拒绝、按当前状态新收据显式反向安装、旧版单写者恢复。负例只在quiescent时临时改interval_seconds=16，不运行Agent、不改资源值，随后准确恢复原配置。最终disable恢复八原值和空journal，独立清理全部本轮对象。

原启动300秒、缓存45秒、native600秒、零SQL/API错误、请求最大5秒、p95桶上界1秒、98%计划覆盖、64MiB和主库/PID1/CCG身份保持。原native worker逐字节不变，所有维护及resume必须完整落在成功600秒窗口内，不重试、调额或放宽时限。17项结构及真机预检通过，目前尚未启动或取得业务终态。共享节点，无Kubelet liveness；不代表全部安装路径、百分比迁移、两个正式次版本、24h+24h或七天通过。

- [maintenance-business.py](maintenance-business.py)
- [runner.py](runner.py)
- [artifact-transfer.py](artifact-transfer.py)
- [tests/manual-maintenance-contract.py](tests/manual-maintenance-contract.py)
- [public-artifact-binding.json](public-artifact-binding.json)
- [tests/vendor-soak-load.py](tests/vendor-soak-load.py)
- [tests/vendor-soak-campaign.py](tests/vendor-soak-campaign.py)
- [tests/vendor-engine-smoke.py](tests/vendor-engine-smoke.py)
- [examples/optional-agent.sh](examples/optional-agent.sh)
- [plan.json](plan.json)
