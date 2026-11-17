# 老化回退输入准备与本轮测试

## 真机进展

原1880长测没有重启。节点原生UTC 2026-11-17T05:44:40.869995+00:00，原24h observe基线已经通过，DBS/HISDBS各完整86400秒，SQL/API零错误、4轮备份恢复内容和整段原生验证均通过。下载原3278970字节报告后，本地原始审计程序再次重算通过。[独立结果](test-results-original1880-baseline-independent.json)与[准确原报告压缩件](test-evidence-original1880-baseline-report.json.gz)保留；解压SHA256为276c5ae3e3ccf3a4267cc7b302be65ec4ad948a9c621b1f09621d413b302eceb。

目前是同容器24h enforce，八项实际控制、原PID1/Agent/Cache进程身份及运行ELF已独立复核。正式固定预算是CPU7.2核、memory.high=20001980416、读写各64MiB/s、手动IOPS4096；原外部memory.max=20GiB保留。这是既定手动预算对照，不是默认20%任意业务性能证明。新七天尚未开始；两段24h、新604800秒、老化后验收和发布整体仍未接受，不把基线通过当作完整稳定性结论。原历史失败和unknown均保留。

## high兼容回退程序的准确内容

[内容与暂存结果](test-results-source37-high-previous-content.json)核对当前preview.5的8项附件元数据和正文摘要。缓存AMD64包25354382字节，SHA570dc4092763965ec45f7c465a56bfbaa4abfef0e8daa7cc05d8fe4545a2cdca；manifest SHAfc8dc4c889bfce69457ca86725d908df2ccd65d98c80dcb0cd1fe6b54e26407c。准确成员是根目录crg，4026528字节，ELF SHAbe6b0aa9f9bf932d8b02872e86a9cffcfea6d7199e39c274694dce904af07333，source ced461705ebc27315a59aefe463f9b4af47130a3、release444410114。没有使用旧1728同大小但不同摘要的ELF，也不执行旧max-only版本。

该ELF仅以0600单次暂存于/var/tmp/crg-previous1994-tools-20261116/previous，独占目录、准确摘要/架构复核、fsync及noreplace发布；没有执行、没有安装、没有真实managed resume资格。第一次本地提取因猜测错误成员路径而退出，原失败保存，后按实际成员纠正；不能将第一次失败改写成成功。

## 一次准备工具

[prepare-aged.py](../tests/live-capacity-aged-v1/prepare-aged.py)和[固定契约](../tests/live-capacity-aged-v1/prepare-contract.json)核对原执行器、保存器、采集器及所有冻结源。节点入口为/var/tmp/crg-prepare1996-tools-20261116/tests/live-capacity-aged-v1/prepare-aged.py。默认只读，原三段未终态时--prepare同样exit2/pending，先返回且不创建正式input/launch/runner/postflight。

原三段审计全部接受后，必须提供来自真实capture-save的准确seal与receipt两个可信SHA256；采集必须在两段24h接受后且原新七天仍运行的窗口内完成，终态不能补采。工具复核已有0700 input根、0600 seal/intent/receipt、源摘要/绑定/时间顺序、原实际lineage、inode/日志前缀/清理及无其它挂载，核对准确暂存previous。不能用合成摘要或受控测试记录替代真实采集。

只在全部条件满足且明确--prepare时，以独占.authority-v2目录一次发布准确previous及execution-authority-v2.json。authority字段必须与原executor-v2完全一致，时间等元数据另存私有receipt。使用原checked_authority及readiness再次验证后，只返回prepared-not-executed。失败保留guard/已发布部分/error，不覆盖、不自动重试或删除。不创建业务Pod，不启动回退，不改变任何资源控制。

```bash
python3 -B tests/live-capacity-aged-v1/prepare-aged.py
```

## 保护检查与剩余工作

[13组受控检查](../tests/live-capacity-aged-v1/prepare-aged-checks.py)在Linux全部通过，Windows4通过/9跳过：pending无写入、可信摘要成对要求、错误源/损坏previous/legacy拒绝、真实私有文件和noreplace、重复拒绝、部分发布失败保留，以及未替换的原authority精确schema检查。terminal、lineage、挂载和previous内容在受控夹具中替换，不是实际老化或回退验收。

真机默认、--prepare、成对受控摘要的--prepare三次均pending，四类真实目标仍不存在；旧七组冻结与原19长测输入保持。[结果](test-results-source37-aged-input-prepare.json)、[计划](test-plan-source37-aged-input-prepare.json)和[准确证据](test-evidence-source37-aged-input-prepare.json.gz)归档。

后续仍需同容器24h限制对照、新七天/28周期、真实窗口seal、准确authority准备、[一次后台启动](development-source37-detached-launch.zh.md)、实际两角色600秒及原36检查、真实退出与独立审计，最后重新核对最终发布身份。用户high-only回退范围保持，52原定义/18完成声明保持，preview.5附件不变，正式1.0未发布。
