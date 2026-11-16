from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
T=Path(__file__).parent;B=T.parent;repo=B/'ContainerResourceGuard-integration';sha=lambda b:hashlib.sha256(b).hexdigest();enc=lambda v:(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode();build=json.loads((T/'crg-r1751-fixed-candidate-build.json').read_bytes());previous=json.loads((T/'crg-r1915-final-verification.json').read_bytes());assert build['source_revision']=='37ca44e0e24a0eaa14e52b5c8bbbda54c76364b0' and len(build['production_source_sha256'])==50
assert all(sha((repo/n).read_bytes())==h for n,h in build['production_source_sha256'].items());S=T/'crg-r1917-prepared';S.mkdir(exist_ok=False);files={}
def keep(n,raw):
 p=S/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);files[n]=sha(raw)
recipe_names=['scripts/build.sh','scripts/release-metadata.py','scripts/toolchain.json','go.mod','scripts/package.py','scripts/package_public.py','scripts/check-package.py','scripts/check-reproducible.py','scripts/verify-release.py','scripts/validate-sbom.py','scripts/sbom-schema-lock.json','tests/release-integrity.py'];recipe={n:sha((repo/n).read_bytes()) for n in recipe_names}
identity={'schema':'crg-source37-package-candidate-identity-v1','phase':'frozen-before-this-package-rehearsal','source_revision':build['source_revision'],'embedded_version':'v1.0.0','toolchain':build['toolchain'],'production_source_sha256':build['production_source_sha256'],'binaries':build['binaries'],'build_recipe_source_sha256':build['build_recipe_source_sha256'],'metadata_sha256':build['metadata_sha256'],'packaging_recipe_sha256':recipe,'package_revision':'the exact CI run head, separately bound after sole dispatch','oldced_package_evidence_transferred':False,'stable_release_accepted':False};identity_raw=enc(identity);keep('docs/live-capacity-candidate-identity.json',identity_raw)
old=(repo/'.github/workflows/final-package.yml').read_text();workflow=old.replace('fixed-final-candidate-package','capacity-fixed-source37-package').replace('ced461705ebc27315a59aefe463f9b4af47130a3',build['source_revision']).replace('docs/final-v1-candidate-identity.json','docs/live-capacity-candidate-identity.json').replace('9b61fcf566087533e2528016073c795b6fa63d15ee5275e6f7c76c1cbcd235e8',build['binaries']['amd64']['sha256']).replace('ff1a2c1c599eb38fde6857c2eede70a1deabf0c2c89977ab92e71ec52ec3982b',build['binaries']['arm64']['sha256']).replace('crg-fixed-final-package-${{ github.sha }}','crg-capacity-fixed-package-${{ github.sha }}')
needle="          identity=json.loads(Path('docs/live-capacity-candidate-identity.json').read_bytes())";assert needle in workflow;workflow=workflow.replace(needle,"          identity_raw=Path('docs/live-capacity-candidate-identity.json').read_bytes()\n          assert hashlib.sha256(identity_raw).hexdigest()=='"+sha(identity_raw)+"'\n          identity=json.loads(identity_raw)\n          assert identity['schema']=='crg-source37-package-candidate-identity-v1'\n          for name,digest in identity['packaging_recipe_sha256'].items():\n              assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest")
needle="          source=Path('candidate')";assert needle in workflow;workflow=workflow.replace(needle,needle+"\n          for name,digest in identity['build_recipe_source_sha256'].items():\n              assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest\n          for name,digest in identity['metadata_sha256'].items():\n              assert hashlib.sha256((source/'dist'/name).read_bytes()).hexdigest()==digest")
assert 'on: workflow_dispatch' in workflow and 'ced461' not in workflow and 'final-v1-candidate-identity' not in workflow and workflow.count(build['source_revision'])==2
for inline in workflow.split("python3 - <<'PY'\n")[1:]:
 source=inline.split('\n          PY',1)[0];source='\n'.join(line[10:] if line.startswith('          ') else line for line in source.splitlines());ast.parse(source)
keep('.github/workflows/capacity-fixed-package.yml',workflow.encode())
plan={'schema':'crg-source37-fixed-package-rehearsal-plan-v1','phase':'frozen-before-sole-CI-dispatch','program_source_revision':build['source_revision'],'branch':'release/integration-v1','workflow_path':'.github/workflows/capacity-fixed-package.yml','workflow_sha256':sha(workflow.encode()),'candidate_identity':'docs/live-capacity-candidate-identity.json','identity_sha256':sha(identity_raw),'recipe_sha256':recipe,'source50':build['production_source_sha256'],'expected_binaries':build['binaries'],'expected_metadata_sha256':build['metadata_sha256'],'builds_from_two_distinct_absolute_checkouts':True,'expected_checks':{'package_architectures':2,'offline_integrity_cases':14,'independent_downloaded_archive_positive_checks':2,'independent_local_pinned_SBOM_schema_checks':2,'online_attestation_positive':4,'offline_attestation_positive':3,'offline_attestation_negative':3},'signing_identity':{'repo':'cuipengdba/ContainerResourceGuard','ref':'refs/heads/release/integration-v1','workflow':'cuipengdba/ContainerResourceGuard/.github/workflows/capacity-fixed-package.yml','runner':'github-hosted','signer_and_source_digest':'exact immutable CI packaging-head commit, not program source37','predicate_types':['https://slsa.dev/provenance/v1','https://cyclonedx.org/bom']},'artifact_allowlist':['build-manifest.json','containerresourceguard-v1.0.0-linux-amd64.tar.gz','containerresourceguard-v1.0.0-linux-arm64.tar.gz','crg-linux-amd64','crg-linux-arm64','integrity-check.json','package-check.json','reproducibility-check.json','sbom-linux-amd64.cdx.json','sbom-linux-arm64.cdx.json','SHA256SUMS'],'test_node97_modified':False,'existing_long_inputs_or_clocks_changed':False,'old_workflow_and_old_identity_preserved':True,'oldced_package_qualification_transferred':False,'stable_release_accepted':False};keep('docs/test-plan-live-capacity-package-v1.json',enc(plan));keep('tests/live-capacity-package-v1/prepare-frozen-workflow.py',Path(__file__).read_bytes())
guide='''# 源37新候选的打包、SBOM与来源演练

## 当前阶段

本轮先冻结[准确计划](test-plan-live-capacity-package-v1.json)、[候选身份](live-capacity-candidate-identity.json)与[单独workflow](../.github/workflows/capacity-fixed-package.yml)，尚未调度，不代表构建或验收通过。产品源37ca44e0/两个准确ELF与当前新长稳一致；此工作仅在GitHub临时runner进行，不连接测试节点、不修改长稳19输入、资源预算、时钟或业务。源37的[正式18项/另4辅助](development-fresh-formal18.zh.md)和[当前长稳](development-new-long1880.zh.md)保持各自资格。

旧ced/576打包演练和原final-package.yml/final-v1-candidate-identity.json逐字保留，不能借用其结果。其它分支保留其产品源，本轮仅从集成分支调度；误从旧产品源分支调度时，50文件/ELF绑定必须拒绝，不以文档相同假装程序相同。新workflow只手动触发，不改变原CI或发布附件。

## 准确源与产物绑定

固定Go1.27.3和原四个构建输入，从source37单独checkout重建Linux AMD64/ARM64静态ELF，分别必须等于ee4f0a14…和865459b0…；完整摘要、长度、两份SBOM及build-manifest原摘要在计划列出。检查当前打包树及独立源码树全部50生产文件、12个打包/校验依赖和准确metadata；任一不符停止，不重建一个较易通过的程序。候选身份本身的摘要在workflow常量绑定，workflow及身份全部字节由CI run head/API绑定。

程序源固定为37ca44e0完整40位SHA；打包/文档源为实际唯一CI run的另一个完整head SHA。SOURCE、BUILD.json、SBOM、PACKAGE-DOCUMENTATION和签名分别核对，不把二者混为一个版本。原脚本从committed Git archive收集公开文档，60MiB/4000成员上限不放宽，不加入工作区文件、私有profile、凭据、数据库数据或测试机回执目录。

## 必须实际执行的检查

1. 两架构实际build/package、包内准确ELF/BUILD/SBOM及文档链接检查，原14个离线完整性正常/拒绝场景均保持；校验不解压或执行任意未受信文件。
2. 在不同绝对路径的独立源码/打包checkout，原两架构ELF、SBOM、manifest、归档和SHA256SUMS重复构建逐字相等；不宣称不同平台/第三方复现。
3. 从准确成功run下载完整artifact ZIP，按GitHub digest和长度复算并核对精确11文件白名单/CRC；客户端独立校验两份下载归档，并用原本地官方三schema锁与jsonschema4.26.0验证两个实际SBOM。
4. 四个在线签名正向：两归档SLSA provenance与两ELF的CycloneDX SBOM，证书必须命中本仓库/owner ID、集成ref、准确workflow、打包commit、GitHub-hosted及准确run/attempt/subject SHA。禁止自托管身份替代。
5. 将成功验证出的bundle与预先获取的可信根留存，用原关闭loopback代理/空NO_PROXY条件做三个离线正向和错误源/错误workflow/篡改归档三个负向，共10个签名场景；网络错误、参数错误不算预期拒绝。此条件不是OS防火墙隔离；信任根引导与CLI版本公开记录。

原脚本及CLI/Schema工具按准确摘要/版本绑定。失败保留原步骤、输入、错误和下载资格，不自动重复dispatch/更改阈值。计划中的数字是待执行条件，只有实际原件/签名校验可授予本次演练通过。

## 完成边界

本次是新候选打包/离线/来源演练，不是稳定v1.0.0附件、生产安装或老化后验收。完整24h基线/同容器24h限制/新七天、原后置故障/恢复/维护/升级、缺失厂商ARM与独立物理多盘范围及最终稳定身份仍按原条件处理。preview.5八资产/正文/tag不改，52原任务定义/18既有完成声明不增加；开发任务和结果按P09.1/P09.2独立归档。
''';keep('docs/live-capacity-package-rehearsal.zh.md',guide.encode());spec=importlib.util.spec_from_file_location('render',repo/'scripts/render-task-audit.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);prepared={'common_files':files,'branches':{}}
status={'phase':'frozen-before-sole-CI-dispatch','source_revision':build['source_revision'],'plan':'test-plan-live-capacity-package-v1.json','guide':'live-capacity-package-rehearsal.zh.md','stable_release_accepted':False,'long_source_or_clock_changed':False}
for name,row in previous['branches'].items():
 r=B/name;out=S/'branch-specific'/name/'docs';out.mkdir(parents=True);reg=json.loads((r/'docs/current-task-registry.json').read_bytes());audit=json.loads((r/'docs/current-52-task-audit.json').read_bytes());reg['source37_package_rehearsal']=status;audit['source37_package_rehearsal']=status
 for task in reg['tasks']:
  if task['id'] not in ['P09.1','P09.2']:continue
  task['before_source37_package_rehearsal']=dict(task['current_acceptance']);a=dict(task['current_acceptance']);a['verified_scope']+=' 源37新独立打包/来源计划与精确输入已冻结，当前尚未调度；旧ced/576演练原资格不转移。';a['remaining_or_boundary']+=' 本轮需实际build/package、14离线场景、双架构逐字重建、下载内容/Schema和10签名条件通过；最终稳定附件、安装/发布身份仍待。';a['evidence']='live-capacity-package-rehearsal.zh.md';task['current_acceptance']=a;task['source37_package_rehearsal']=status;arow=next(v for v in audit['tasks'] if v['id']==task['id']);arow['source37_package_rehearsal']=status
  for k in ['verified_scope','remaining_or_boundary','evidence']:arow[k]=a[k]
 for n,v in [('current-task-registry.json',reg),('current-52-task-audit.json',audit)]:(out/n).write_bytes(enc(v))
 for task in audit['tasks']:
  target=out/task['evidence']
  if not target.exists():
   src=S/'docs'/task['evidence'] if (S/'docs'/task['evidence']).exists() else r/'docs'/task['evidence'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(src.read_bytes())
 (out/'current-52-task-audit.md').write_bytes(m.render(out));prepared['branches'][name]={'branch':row['branch'],'parent':subprocess.check_output(['git','-C',str(r),'rev-parse','HEAD'],text=True).strip(),'files':{'docs/'+n:sha((out/n).read_bytes()) for n in ['current-task-registry.json','current-52-task-audit.json','current-52-task-audit.md']}}
(T/'crg-r1917-prepared.json').write_bytes(enc(prepared));s=(T/'crg-r1850-publish.py').read_text().replace('crg-r1850','crg-r1917').replace('test: freeze original600 four-cell comparison before sole launch [skip ci]','build: freeze new source37 exact-binary package and attestation rehearsal [skip ci]');(T/'crg-r1917-publish.py').write_bytes(s.encode());(T/'crg-r1917-package-frozen.json').write_bytes(enc(plan));print(json.dumps({'common_files':len(files),'recipe_files':len(recipe),'phase':status['phase'],'workflow_sha256':plan['workflow_sha256']}))
