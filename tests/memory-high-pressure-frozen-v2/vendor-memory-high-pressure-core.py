import datetime,hashlib,importlib.util,json,os,select,shlex,stat,subprocess,time,types
from pathlib import Path
class Rejected(Exception): pass
def require(ok,reason):
    if not ok: raise Rejected(reason)
def read_json(path,maximum=32*1024*1024):
    raw=Path(path).read_bytes();require(len(raw)<=maximum,'JSON_BOUND');return json.loads(raw),hashlib.sha256(raw).hexdigest()
def digest(path): return {'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
def proc(pid,entry,ticks):
    p=Path('/proc',str(pid))
    try: live=int((p/'stat').read_text().rsplit(')',1)[1].split()[19])==ticks and entry.encode() in (p/'cmdline').read_bytes().split(b'\0')
    except (FileNotFoundError,ProcessLookupError):live=False
    return {'live':live}
def timestamp(value):return datetime.datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
def load(name):
    p=Path(__file__).with_name(name);require(digest(p)['sha256']==SOURCE_SHA256[name],'FROZEN_HELPER')
    spec=importlib.util.spec_from_file_location(name.replace('-','_'),p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
CONTROLS=['cpu.max','memory.high','io.max','pids.max','cpu.weight','io.weight','memory.max','memory.swap.max']
def controls(group):return {name:(group/name).read_text().strip() for name in CONTROLS}
gate=types.SimpleNamespace(read_json=read_json,digest=digest,proc=proc,audit=types.SimpleNamespace(timestamp=timestamp,number=lambda v:type(v) in (int,float)))
base=types.SimpleNamespace(controls=controls,CONTROLS=CONTROLS,CRITERIA={'steady_host_available_bytes':8*1024**3})
def validate_native(value, run_id):
    require(value['schema'] == 'crg-vendor-soak-v1' and value['phase'] == 'passed'
            and value['run_id'] == run_id and value['test_phase'] == 'smoke'
            and value['requested_duration_seconds'] == 600
            and gate.audit.number(value['elapsed_seconds']) and value['elapsed_seconds'] >= 600
            and not value['interrupted'] and value['threads_stopped'] is True
            and value['payload_integrity'] is True and value['primary_not_restarted'] is True
            and value['primary_start_time_initial'] == value['primary_start_time_final']
            and len(value['initial_checksum']) == len(value['final_checksum']) == 5
            and value['initial_checksum'][:4] == value['final_checksum'][:4]
            and value['initial_checksum'][0] == 16384 and value['initial_checksum'][2] == 67108864, 'NATIVE_COMPLETION')
    require(value['criteria'] == {'sql_period_seconds': 2, 'api_period_seconds': 5,
            'maximum_seconds': 5, 'p95_upper_bound_seconds': 1, 'maximum_errors': 0,
            'minimum_scheduled_samples_fraction': .98}, 'NATIVE_CRITERIA')
    for kind, period in [('sql', 2), ('api', 5)]:
        item = value[kind]
        require(type(item['attempts']) is int and item['errors'] == 0 and item['attempts'] == item['successes']
                and item['attempts'] >= 600/period*.98
                and gate.audit.number(item['max_seconds']) and 0 <= item['max_seconds'] <= 5
                and value['latency_bucket_upper_seconds'] == [.001, .005, .01, .02, .05, .1, .25, .5, 1, 2, 5, 'over-5']
                and len(item['histogram']) == 12
                and sum(item['histogram']) == item['attempts'], 'NATIVE_SAMPLES')
        bounds = value['latency_bucket_upper_seconds'];total = 0;p95 = None
        for upper, count in zip(bounds, item['histogram']):
            require(type(count) is int and count >= 0, 'NATIVE_HISTOGRAM')
            total += count
            if p95 is None and total >= item['attempts']*.95:p95 = upper
        require(type(p95) in (int, float) and p95 <= 1 and p95 == item['p95_bucket_upper_seconds'], 'NATIVE_P95')
base.validate_native=validate_native
SOURCE_SHA256={'vendor-device-state-observer.py': '0fa377189ded92e2b5a9e182871e0494c8af4bc73920b8eb25d03ba9937995c6', 'vendor-native-diagnostics-v3-checks.py': '83b0c5658c7ecb515fe98d6142d12e95d29b96f900789042b532794f0ab822d1', 'vendor-native-diagnostics-v3-runtime.py': '45655d52a845f56d4a4e858b2d0d46a5d464c4790c3e4ad10d8cb721caba273a', 'vendor-native-diagnostics-v3.py': '29d888b7bd90fcc11a2594753fbe44d4da0e9a6262f7c95d3ceb0508ee459ebd', 'vendor-native-diagnostics.py': '83b3f8894eea96af9dfc2c789ee54b63cd5803e9dd2218a74f6bc100934c31ab', 'vendor-pg-wait-v2.py': '7c97642469f24facbe0d7e6f45c3fbd382ba6a2e7a3d76124753a202b227d275', 'vendor-pg-wait.py': '09c330fb06f5ebedddbf4fca108c3b7d4e0f74ca97d3e565292b41ad5391ed69', 'vendor-proc-read-error.py': 'cd9653252535bbc0d5100599c89073532c0d40a7b1eeabe74eac8c2950c575ab', 'vendor-soak-load-diagnostics-v3.py': 'bbb86c6af6c472674ebf108686052d5676207b8470b69dbf34fdeb5197cff29b', 'vendor-thread-session.py': '35f65518ce56f5b889c82041a1c45c87d9f3284ab6bd59cc39752bf78fdc8bce', 'vendor-thread-wait-observer.py': 'c904c1d13b41f7f5c5b517e0dc1aa8348126665fcf8fe97e232a92f2dedf0c02', 'vendor-thread-wait.py': 'fceb41233f46c869d00f844642b842a35341270cbe37d126ef41685ab1a179f6', 'vendor-native-session.py': 'ae53be88970f343624882cd7a11ffc5945bae469a7ad005b4c760592b08aec63', 'vendor-device-business-session.py': 'a3bad42812e387acd18079df11af49e4c9d2e646c0ca59e3813dd6442a3ed103', 'vendor-device-session.py': '632a93f267bcb8aeee992d00f5fc4f0aaec63e8bbcd5e393ba83bf14b3474444', 'vendor-memory-pressure-worker-v2.py': '741a1aaaecef91bb54a06bdd6af3bf76f5f8e1ad17c25bbdee4c868fddd3daff', 'vendor-engine-timed.py': '5abbc7110ece3383c63e84737c70f8265d7f674ffdca09cff23fdade05fbe42d', 'vendor-api-timed.py': '907a705ddfa55a3635a757c38ee5fcb46e1b0a5c93a2056b15e06488e2b8f2d8'}
session=load('vendor-thread-session.py');native_session=load('vendor-native-session.py');device_business=load('vendor-device-business-session.py')
TOOLS='/var/tmp/crg-high613-tools-20261112'
API='/var/tmp/crg-high613-tools-20261112/vendor-api-timed.py'
API_SHA='907a705ddfa55a3635a757c38ee5fcb46e1b0a5c93a2056b15e06488e2b8f2d8'
ENGINE='/var/tmp/crg-high613-tools-20261112/vendor-engine-timed.py'
PRESSURE_WORKER='/var/tmp/crg-high613-tools-20261112/vendor-memory-pressure-worker-v2.py'
PRESSURE_SHA='741a1aaaecef91bb54a06bdd6af3bf76f5f8e1ad17c25bbdee4c868fddd3daff'
MANUAL={'resource_mode': 'manual', 'limits': {'cpu_cores': 7.2, 'memory_high': '20001980416B', 'io_read_bps': '64MiB', 'io_write_bps': '64MiB', 'io_read_iops': 4096, 'io_write_iops': 4096}, 'data_paths': ['/opt/postgresql']}
POLICIES=[{'cpu_percent': 30, 'memory_percent': 30, 'io_percent': 100}, {'cpu_percent': 25, 'memory_percent': 29, 'io_percent': 80}]
EXPECTED=[{'cpu.max': '720000 100000', 'memory.high': '20001980416', 'io.max': '253:0 rbps=64700080 wbps=37470104 riops=83 wiops=135'}, {'cpu.max': '600000 100000', 'memory.high': '19335249920', 'io.max': '253:0 rbps=51760064 wbps=29976083 riops=66 wiops=108'}]
PINS={'binary': '6088721cd4846f95b3b71c82f9884e1909797a199d962b50519c9e013de98b4e', 'profile': '00e35e91594ed0ad1075a196c20bd8f4c6628c346c4bd6e901ac05d4cc90ef6b'}
THREAD_OBSERVER='/var/tmp/crg-high613-tools-20261112/vendor-thread-wait-observer.py'
DEVICE_OBSERVER='/var/tmp/crg-high613-tools-20261112/vendor-device-state-observer.py'
DIAGNOSTIC_HELPER='/var/tmp/crg-high613-tools-20261112/vendor-native-diagnostics.py'
NATIVE_V2_WORKER='/var/tmp/crg-high613-tools-20261112/vendor-soak-load-diagnostics-v3.py'
NATIVE_V2_CONTRACT={'sources': {'vendor-device-state-observer.py': '0fa377189ded92e2b5a9e182871e0494c8af4bc73920b8eb25d03ba9937995c6', 'vendor-native-diagnostics-v3-checks.py': '83b0c5658c7ecb515fe98d6142d12e95d29b96f900789042b532794f0ab822d1', 'vendor-native-diagnostics-v3-runtime.py': '45655d52a845f56d4a4e858b2d0d46a5d464c4790c3e4ad10d8cb721caba273a', 'vendor-native-diagnostics-v3.py': '29d888b7bd90fcc11a2594753fbe44d4da0e9a6262f7c95d3ceb0508ee459ebd', 'vendor-native-diagnostics.py': '83b3f8894eea96af9dfc2c789ee54b63cd5803e9dd2218a74f6bc100934c31ab', 'vendor-pg-wait-v2.py': '7c97642469f24facbe0d7e6f45c3fbd382ba6a2e7a3d76124753a202b227d275', 'vendor-pg-wait.py': '09c330fb06f5ebedddbf4fca108c3b7d4e0f74ca97d3e565292b41ad5391ed69', 'vendor-proc-read-error.py': 'cd9653252535bbc0d5100599c89073532c0d40a7b1eeabe74eac8c2950c575ab', 'vendor-soak-load-diagnostics-v3.py': 'bbb86c6af6c472674ebf108686052d5676207b8470b69dbf34fdeb5197cff29b', 'vendor-thread-session.py': '35f65518ce56f5b889c82041a1c45c87d9f3284ab6bd59cc39752bf78fdc8bce', 'vendor-thread-wait-observer.py': 'c904c1d13b41f7f5c5b517e0dc1aa8348126665fcf8fe97e232a92f2dedf0c02', 'vendor-thread-wait.py': 'fceb41233f46c869d00f844642b842a35341270cbe37d126ef41685ab1a179f6', 'vendor-native-session.py': 'ae53be88970f343624882cd7a11ffc5945bae469a7ad005b4c760592b08aec63', 'vendor-device-business-session.py': 'a3bad42812e387acd18079df11af49e4c9d2e646c0ca59e3813dd6442a3ed103', 'vendor-device-session.py': '632a93f267bcb8aeee992d00f5fc4f0aaec63e8bbcd5e393ba83bf14b3474444', 'vendor-memory-pressure-worker-v2.py': '741a1aaaecef91bb54a06bdd6af3bf76f5f8e1ad17c25bbdee4c868fddd3daff', 'vendor-engine-timed.py': '5abbc7110ece3383c63e84737c70f8265d7f674ffdca09cff23fdade05fbe42d', 'vendor-api-timed.py': '907a705ddfa55a3635a757c38ee5fcb46e1b0a5c93a2056b15e06488e2b8f2d8'}, 'worker_sha256': 'bbb86c6af6c472674ebf108686052d5676207b8470b69dbf34fdeb5197cff29b', 'maximum_PG_wait_targets': 4}
THREAD_CONTRACT={'schema': 'crg-pressure-thread-session-contract-v1', 'observer_sha256': 'ac5dd6b7293949a6ea25da99fbcc8048b4ef628ddaba2c7be61a8c7536d579f1', 'session_sha256': '35f65518ce56f5b889c82041a1c45c87d9f3284ab6bd59cc39752bf78fdc8bce', 'session_selftest_sha256': '520d790872a095f9762e70775a130bc0cf4a544b1db38d176b796090aa085424', 'session_qualification': '/var/tmp/crg-thread165-tools-20261111/qualification.json', 'session_qualification_sha256': '6e43bfbb71141f3ce264ea36c239c28e670e28620d18d4d8f7d13cd816c10929', 'observer_qualification': '/var/tmp/crg-thread155-tools-20261111/qualification.json', 'observer_qualification_sha256': 'b305850e2a463e206ba0b13ae1ed7273c15c7a7131b95e9dc1361dda1aa14b83', 'prior_failed_report': '/var/tmp/crg-business-pressure142-20261111/report.json', 'prior_failed_report_sha256': '55fe93aef6b6469f6ad107680020cd47af626c844f4f09b9c3dcc51a1ad8fede', 'prior_DBS_short_observation': '/var/tmp/crg-thread157-live-20261111/dbs-threads.json', 'prior_DBS_short_observation_sha256': '2b13ca6b27ebcba7972fc805d0cc033f3ebcf4c223cef74cb682ef441e78cfe7', 'prior_HIS_short_observation': '/var/tmp/crg-thread158-live-20261111/hisdbs-threads.json', 'prior_HIS_short_observation_sha256': '3b3317ed2889985682e8abd0c6092a8cee8cd4756c65c54791d260475711ba0c', 'duration_seconds': 900, 'maximum_report_bytes': 33554432, 'maximum_threads': 64, 'sample_period_seconds': 1, 'listener_port': 8090, 'start_before_engine_and_pressure': True, 'start_handshake_seconds': 15, 'term_wait_seconds': 15, 'kill_wait_seconds': 5, 'whole_child_CPU_source': 'wait4-specific-child', 'business_error_precedence': True, 'business_quotas_and_SLA_unchanged': True}
WAIT_CONTRACT={'schema': 'crg-pressure-wait-diagnostics-contract-v1', 'observer_sha256': 'c904c1d13b41f7f5c5b517e0dc1aa8348126665fcf8fe97e232a92f2dedf0c02', 'helper_sha256': 'fceb41233f46c869d00f844642b842a35341270cbe37d126ef41685ab1a179f6', 'qualifications': {'helper': {'path': '/var/tmp/crg-threadwait229-session-checks-20261111/checks-result.json', 'sha256': '395e977eb799c9560f00b8f0a8b65abe593a90045e00117e0d0521687076988f', 'checks': 24}, 'observer': {'path': '/var/tmp/crg-waitobserver231-session-checks-20261111/checks-result.json', 'sha256': '9d590cd4ff9b57ea099efcf969e1f7dd4103578a7822e88ea3273dc64cc0515a', 'checks': 19}, 'selector': {'path': '/var/tmp/crg-waitselection233-session-checks-20261111/checks-result.json', 'sha256': '7d3afe0a6971db1af03b64de4b2754abeb43726a6b3b49f4f14792c8dccf128a', 'checks': 10}}, 'maximum_D_captures_per_sample': 8, 'maximum_extra_bytes_per_sample': 8192, 'separate_proc_reads_are_not_atomic': True, 'file_or_thread_role_causality_not_proven': True, 'live_observation': {'path': '/var/tmp/crg-wait232-live-20261111/observation-result.json', 'sha256': '478bcb49dbd89c8e4e45746e41033198faf0d97c0c735cf9dc22cd4cc28bcb3b', 'samples_each_role': 16}}
FINAL_CONTRACT={'schema': 'crg-pressure-native-final-flush-contract-v1', 'session_sha256': 'ae53be88970f343624882cd7a11ffc5945bae469a7ad005b4c760592b08aec63', 'maximum_failure_cleanup_seconds': 120, 'host_qualification': {'path': '/var/tmp/crg-native219-session-checks-20261111/checks-result.json', 'sha256': '31542e2b42ee3bddfd5dd5679af99247cf3dd5ffd3f390fe1843d928124efc10', 'checks': 18}, 'real_qualification': {'path': '/var/tmp/crg-native220-qualification-20261111/report.json', 'sha256': '665362fa04f3c9b59e006179d9c01c446a2ba0f7b87b11b0213aa84e7dcfbf0f', 'checks_each_role': 8, 'namespace': 'crg-vendor-lab-native220-20261111', 'launch': '/var/tmp/crg-memory167-tools-20261111/native220-launch.json', 'runner_sha256': 'be91573a80299faa11f76e0c4eb5338d369ca157e91548c4c4d5ff190d947310', 'worker': '/var/tmp/crg-memory167-tools-20261111/native220-worker.json', 'executor_sha256': '5be532493aa19d8af85c4cdfd59d52a35d984ec8fc68804a2136e91c697819f1'}, 'prior_failed_report': '/var/tmp/crg-business-pressure203-20261111/report.json', 'prior_failed_report_sha256': '76b5ed98f37064cf5a6f3e9cf24d8555173fac38d53c239f72f3e897e61e7a0e', 'prior_tools': '/var/tmp/crg-memory203-tools-20261111', 'prior_namespace': 'crg-vendor-lab-pressure203-20261111', 'normal_success_sends_no_TERM': True, 'business_error_object_precedence': True, 'partial_report_does_not_pass_original600s': True}
DIAGNOSTIC_CONTRACT={'schema': 'crg-native-pressure-diagnostics-contract-v1', 'worker_sha256': '50ea0454d17d5412a9d4085472ed89831e4408f60aa0fa0ca2dfd905a2bacb1f', 'helper_sha256': '83b3f8894eea96af9dfc2c789ee54b63cd5803e9dd2218a74f6bc100934c31ab', 'qualification_report': '/var/tmp/crg-native194-qualification-20261111/report.json', 'qualification_report_sha256': 'bc9897ed00032b6a6f33fb20e4631b9ba5dda3a144d9c5d5da775e3a210e4c41', 'qualification_source_sha256': {'vendor-native-diagnostics.py': '83b3f8894eea96af9dfc2c789ee54b63cd5803e9dd2218a74f6bc100934c31ab', 'vendor-native-diagnostics-checks.py': '38106a8c5f13f34e873d65f08f0c813da799e593339cc5c860c7961b3ee4ed42', 'vendor-soak-load-diagnostics.py': '50ea0454d17d5412a9d4085472ed89831e4408f60aa0fa0ca2dfd905a2bacb1f', 'vendor-native-diagnostics-runtime.py': 'ed4040a1864efec8631cc70013da5628a66c76c76cea76134b31d02b7bad2f2d', 'vendor-soak-load.py': 'ba87ef2d646b723eb8419de25ffcd736f7a5b0925716f4b638761dff70bb2461'}, 'qualification_image_ids': {'dbs': 'sha256:25825bc9f1e9635075f97bedcee37bebb409821cc3c0084ec8ee2a07588cd3b5', 'hisdbs': 'sha256:b772e2bcd0c9d5b8b0896c6efe972d92e76280c0c183d317ebca75df2ca8c39f'}, 'qualification_namespace': 'crg-vendor-lab-native194-20261111', 'qualification_launch': '/var/tmp/crg-memory167-tools-20261111/native194-launch.json', 'qualification_executor_sha256': 'b12a8b5ae1f0f2b105fd4c9a53cc3231a006e3ad1fe0eb1e7cfd1299c49b8e80', 'prior_failed_report': '/var/tmp/crg-business-pressure167-20261111/report.json', 'prior_failed_report_sha256': 'eaff819cd53966a6854de60ce5585713180e7202c6bbe0dab1cf54c820cbdcd0', 'prior_native_failed_report': '/var/tmp/crg-realpaths64-20261111/v10-dbs-bw64/dbs-business/postgresql/basebackup/crg-soak-202611111670/load.json', 'prior_native_failed_report_sha256': '564ae4ee6f6357c68e10481ef6e4f5882657bfdec0a5a5f3b42e92bffc49ca52', 'maximum_report_bytes': 8388608, 'maximum_requests': 1024, 'maximum_PG_samples': 901, 'maximum_PG_rows': 16, 'PG_period_seconds': 1, 'minimum_PG_sample_fraction': 0.98, 'maximum_PG_start_gap_seconds': 3, 'maximum_internal_CPU_fraction_one_core': 0.05, 'maximum_errors_in_main_summary': 32, 'collector_failure_does_not_change_original_native_result': True, 'original_business_failure_precedence': True}
DEVICE_CONTRACT={'schema': 'crg-pressure-device-contract-v1', 'sources': {'vendor-device-business-session.py': 'a3bad42812e387acd18079df11af49e4c9d2e646c0ca59e3813dd6442a3ed103', 'vendor-device-session.py': '632a93f267bcb8aeee992d00f5fc4f0aaec63e8bbcd5e393ba83bf14b3474444', 'vendor-device-state-observer.py': '0fa377189ded92e2b5a9e182871e0494c8af4bc73920b8eb25d03ba9937995c6'}, 'devices': [{'identity': [21, 55869], 'major_minor': '253:0', 'sysfs': '/sys/devices/virtual/block/dm-0'}, {'identity': [21, 55779], 'major_minor': '8:2', 'sysfs': '/sys/devices/pci0000:ad/0000:ad:00.0/0000:ae:00.0/host0/target0:0:0/0:0:0:0/block/sda/sda2'}, {'identity': [21, 55604], 'major_minor': '8:0', 'sysfs': '/sys/devices/pci0000:ad/0000:ad:00.0/0000:ae:00.0/host0/target0:0:0/0:0:0:0/block/sda'}], 'qualifications': {'303': {'path': '/var/tmp/crg-device303-session-20261111/qualification.json', 'sha256': '0228e676b5edde9f07ad097f9e6e76b63cdad394cea71e768ba7fe681e15f7ce', 'phase': 'failed', 'checks': 12, 'sources': {'vendor-device-state-observer.py': '0fa377189ded92e2b5a9e182871e0494c8af4bc73920b8eb25d03ba9937995c6', 'vendor-device-session.py': '632a93f267bcb8aeee992d00f5fc4f0aaec63e8bbcd5e393ba83bf14b3474444', 'vendor-device-session-checks.py': 'e730f21d95fff4ee889b3d8565a78df4bcef4808a4ad552956f5ed8bec268a6f'}, 'checker': {'pid': 1419681, 'start_ticks': 135879876}}, '305': {'path': '/var/tmp/crg-device305-session-20261111/qualification.json', 'sha256': 'a25192ef2b7a1622b9e19749cdbad0dbe9e1ade479e5dca7e7f84aa04691ebb2', 'phase': 'passed', 'checks': 26, 'sources': {'vendor-device-state-observer.py': '0fa377189ded92e2b5a9e182871e0494c8af4bc73920b8eb25d03ba9937995c6', 'vendor-device-session.py': '632a93f267bcb8aeee992d00f5fc4f0aaec63e8bbcd5e393ba83bf14b3474444', 'vendor-device-session-checks.py': '4c51fa74eacf9fff5f5178a1dcc931dc2de77aab0cf140f1af9fd7a9becc365d'}, 'checker': {'pid': 1438584, 'start_ticks': 135888789}}, '306': {'path': '/var/tmp/crg-device306-session-20261111/qualification.json', 'sha256': '6ea7ce43874b68fe0feed2b9516ce51fc50eb4430d1f09e39535f267cec9faf9', 'phase': 'passed', 'checks': 20, 'sources': {'vendor-thread-session.py': '35f65518ce56f5b889c82041a1c45c87d9f3284ab6bd59cc39752bf78fdc8bce', 'vendor-thread-wait-observer.py': 'c904c1d13b41f7f5c5b517e0dc1aa8348126665fcf8fe97e232a92f2dedf0c02', 'vendor-thread-wait.py': 'fceb41233f46c869d00f844642b842a35341270cbe37d126ef41685ab1a179f6', 'vendor-device-state-observer.py': '0fa377189ded92e2b5a9e182871e0494c8af4bc73920b8eb25d03ba9937995c6', 'vendor-device-session.py': '632a93f267bcb8aeee992d00f5fc4f0aaec63e8bbcd5e393ba83bf14b3474444', 'vendor-device-business-session.py': 'a3bad42812e387acd18079df11af49e4c9d2e646c0ca59e3813dd6442a3ed103', 'vendor-device-business-session-checks.py': 'd1cca6a5590aab0a63edab4091dc92c48aa2da6fd9c6209548ba2e76a5ff84ad'}, 'checker': {'pid': 1500858, 'start_ticks': 135917508}}}, 'duration_seconds': 900, 'maximum_start_gap_seconds': 3, 'maximum_report_bytes': 8388608, 'layer_counters_not_summed': True, 'observer_failure_does_not_skip_business': True}
class PressureExecution:
    def __init__(self,root,ns,role,folder,group,row,report,save,record,run,ex,reserve):
        self.root,self.ns,self.report=Path(root),ns,report
        self.plan={'run_id':'20261112613'};self.save,self.check,self.run,self.reserve=save,record,run,reserve
        self.ex=lambda role,*args,data=None,**kw: run(['kubectl','exec']+(['-i'] if data is not None else [])+['-n',self.ns,role+'-business','-c',role,'--',*args],input=data,**kw)
        self.worker=self.worker_log=self.engine_job=self.engine_log=None
    def identity(self,role):
        meta=json.loads(self.run(['kubectl','get','pod','-n',self.ns,role+'-business','-o','json']).stdout)
        cid=next(v['containerID'].split('://')[1] for v in meta['status']['containerStatuses'] if v['name']==role)
        pid=json.loads(self.run(['crictl','inspect',cid]).stdout)['info']['pid']
        group=Path('/sys/fs/cgroup')/next(v.split('::',1)[1].lstrip('/') for v in Path('/proc',str(pid),'cgroup').read_text().splitlines() if v.startswith('0::'))
        require(group.name=='cri-containerd-'+cid+'.scope','IDENTITY_LEAF');return meta,cid,pid,group
    def processes(self,group,entry):
        values=[]
        for pid in (group/'cgroup.procs').read_text().splitlines():
            p=Path('/proc',pid)
            try:
                fields=(p/'stat').read_text().rsplit(')',1)[1].split()
                if fields[0]!='Z' and os.readlink(p/'exe')==entry:values.append((int(pid),int(fields[19]),hashlib.sha256((p/'exe').read_bytes()).hexdigest()))
            except (FileNotFoundError,ProcessLookupError):pass
        return sorted(values)
    def sql(self,role,value):
        return self.ex(role,'su','-','postgres','-c','/opt/postgresql/pgsql/bin/psql -XAtw -h127.0.0.1 -p5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c '+shlex.quote(value),timeout=30).stdout.strip()
    def write_config(self,folder,value,symlink=False):
        began=time.time_ns();config=folder/'crg-config/config.json';temp=config.with_name('high613.next')
        require(not temp.exists() and not temp.is_symlink(),'CONFIG_TEMP_FRESH')
        data=value if isinstance(value,bytes) else json.dumps(dict(value,interval_seconds=1,data_paths=['/opt/postgresql'])).encode()
        target=config.with_name('high613.target.json') if symlink else temp
        require(not target.is_symlink(),'CONFIG_TARGET_NOT_LINK')
        with target.open('wb') as stream:os.chmod(target,0o600);stream.write(data);stream.flush();os.fsync(stream.fileno())
        if symlink:temp.symlink_to(target.name)
        temp.replace(config);return began

    def bind_native_worker(self,group,entry,run_id,row):
        record={};row['native_final_flush']=record
        self.native_drain=native_session.Session(group,entry,run_id,600,NATIVE_V2_CONTRACT['worker_sha256'],record)
        self.native_drain.attach();self.save()

    def failed_engine_interval(self,role,row):
        if 'engine_interval' in row:return
        path=self.root/(role+'-engine')/'business-backup.json'
        if not path.exists():return
        value,digest=gate.read_json(path)
        began,ended=value.get('started'),value.get('ended')
        if type(began) in [int,float] and type(ended) in [int,float] and 0<began<=ended:
            row['diagnostic_failed_engine_interval']={'started_epoch':began,'ended_epoch':ended,'engine_report_sha256':digest,
                'engine_phase':value.get('phase'),'diagnostic_only_not_business_acceptance':True}

    def business_native(self, role, folder, group, row):
        record={};row['thread_observer']=record
        self.thread_session=session.Session(THREAD_OBSERVER,WAIT_CONTRACT['observer_sha256'],self.root,role,record)
        self.thread_session=device_business.Session(self.thread_session,DEVICE_OBSERVER,self.root,role,DEVICE_CONTRACT['devices'],row,self.save)
        self.native_drain=None;primary=[None]
        def diagnostic_error(error):
            row.setdefault('diagnostic_cleanup_errors',[]).append(str(error) if isinstance(error,(Rejected,session.Rejected,native_session.Rejected,device_business.device.Rejected)) else type(error).__name__)
            self.save()
        def finish_thread():
            try:
                # A failed engine report is diagnostic evidence, never a passed interval.
                self.failed_engine_interval(role,row)
            finally:
                self.thread_session.stop()
            try:
                if record['phase']=='collected':
                    covered=[*row.get('reload_intervals',[])]
                    for key in ['engine_interval','diagnostic_failed_engine_interval']:
                        if key in row:covered.append(row[key])
                    record['engine_and_reload_interval_envelopes_covered']=bool(covered) and all(
                        record['first_sample_epoch']<=i['started_epoch']<=i['ended_epoch']<=record['last_sample_epoch'] for i in covered)
                    require(record['engine_and_reload_interval_envelopes_covered'],'THREAD_INTERVAL_ENVELOPE')
                    record['sampling_gaps_and_missing_fields_require_separate_review']=True
            finally:self.save()
        def drain():
            if primary[0] is not None and self.native_drain is not None:
                try:
                    self.native_drain.finish_after_failure(primary[0],FINAL_CONTRACT['maximum_failure_cleanup_seconds'])
                    if self.worker is not None:
                        try:self.worker.wait(timeout=5)
                        except subprocess.TimeoutExpired:row['native_final_flush']['exec_client_exit_unknown']=True
                finally:self.save()
        def finish():
            return session.preserve_business_error(drain,
                lambda:session.preserve_business_error(finish_thread,lambda:self.collect_native_diagnostic(role,folder,row),diagnostic_error),diagnostic_error)
        def work():
            try:return self._business_native_original(role,folder,group,row)
            except BaseException as error:primary[0]=error;raise
        def close():
            if self.native_drain is not None:self.native_drain.close()
        try:
            return session.preserve_business_error(lambda:session.preserve_business_error(work,finish,diagnostic_error),close,diagnostic_error)
        except (session.Rejected,native_session.Rejected,device_business.device.Rejected) as error:
            if error is primary[0]:raise
            raise Rejected('DIAGNOSTIC_SESSION_'+str(error)) from error

    def collect_native_diagnostic(self,role,folder,row):
        record={'phase':'collecting'};row['native_request_pg']=record
        try:
            run_id=self.plan['run_id']+('0' if role=='dbs' else '1');output=folder/('postgresql/basebackup/crg-soak-'+run_id)
            native,native_digest=gate.read_json(output/'load.json');record.update(native_phase=native['phase'],native_report_sha256=native_digest)
            require(native['phase'] in ['passed','failed'] and native['run_id']==run_id,'NATIVE_DIAGNOSTIC_NOT_FINAL')
            data,digest=gate.read_json(output/'native-diagnostics.json',DIAGNOSTIC_CONTRACT['maximum_report_bytes'])
            raw=(output/'native-diagnostics.json').read_bytes();require(hashlib.sha256(raw).hexdigest()==digest,'NATIVE_DIAGNOSTIC_CHANGED')
            target=self.root/(role+'-native-diagnostics.json')
            with target.open('xb') as stream:os.chmod(target,0o600);stream.write(raw)
            summary=native['native_diagnostics'];requests=data['requests'];samples=data['pg_samples']
            record.update(raw_report=str(target),raw_report_sha256=digest,raw_report_bytes=len(raw),summary=summary,original_native_SQL=native['sql'],original_native_API=native['api'])
            record.update(native_interrupted=bool(native.get('interrupted')),native_elapsed_seconds=native.get('elapsed_seconds'),partial_not600s=bool(native.get('interrupted')) or native.get('elapsed_seconds',0)<600)
            require(data['schema']=='crg-native-request-pg-diagnostics-v3' and data['run_id']==run_id and data['worker_sha256']==NATIVE_V2_CONTRACT['worker_sha256']
                and data['frozen_base_sha256']==DIAGNOSTIC_CONTRACT['helper_sha256']
                and data['frozen_pg_wait_sha256']==NATIVE_V2_CONTRACT['sources']['vendor-pg-wait-v2.py']
                and data['unique_application_name']=='crg-disposable-soak-'+run_id
                and summary['report_sha256']==digest and summary['report_bytes']==len(raw),'NATIVE_DIAGNOSTIC_IDENTITY')
            require(summary['diagnostic_complete'] and summary['probe_thread_stopped'] and data['summary']['diagnostic_complete']
                and len(requests)<=1024 and len(samples)<=901 and all(len(s.get('rows',[]))<=16 for s in samples),'NATIVE_DIAGNOSTIC_INCOMPLETE')
            errors=[v for v in requests if not v['success'] or not v['within_original_5seconds']]
            record.update(error_count=len(errors),errors=errors[:32],errors_truncated=len(errors)>32)
            require(summary['request_count']==len(requests)==native['sql']['attempts']+native['api']['attempts']
                and summary['request_errors']==len(errors)==native['sql']['errors']+native['api']['errors'],'NATIVE_DIAGNOSTIC_COUNTS')
            for kind in ['sql','api']:
                events=[v for v in requests if v['kind']==kind]
                require(len(events)==native[kind]['attempts'] and sum(not v['success'] or not v['within_original_5seconds'] for v in events)==native[kind]['errors'],'NATIVE_DIAGNOSTIC_KIND_COUNTS')
            gaps=[z['started_epoch']-a['started_epoch'] for a,z in zip(samples,samples[1:])]
            record.update(PG_samples=len(samples),maximum_PG_start_gap_seconds=max(gaps) if gaps else None,
                first_PG_sample_epoch=samples[0]['started_epoch'] if samples else None,last_PG_sample_epoch=samples[-1]['ended_epoch'] if samples else None)
            require(len(samples)>=600*.98 and all(v['available'] and not v['truncated'] for v in samples) and bool(gaps)
                and all(0<=v<=DIAGNOSTIC_CONTRACT['maximum_PG_start_gap_seconds'] for v in gaps),'NATIVE_PG_SAMPLING_COVERAGE')
            covered=[*row.get('reload_intervals',[])]
            if 'engine_interval' in row:covered.append(row['engine_interval'])
            if 'diagnostic_failed_engine_interval' in row:covered.append(row['diagnostic_failed_engine_interval'])
            record['engine_and_reload_envelopes_covered']=bool(covered) and all(samples[0]['started_epoch']<=v['started_epoch']<=v['ended_epoch']<=samples[-1]['ended_epoch'] for v in covered)
            require(record['engine_and_reload_envelopes_covered'],'NATIVE_PG_INTERVAL_ENVELOPE')
            waits=[v['pg_wait'] for v in samples]
            require(summary['pg_wait_samples']==len(waits) and summary['pg_wait_errors']==0
                and all(v['schema']=='crg-pg-wait-snapshot-v2' and v['available'] and v['run_id']==run_id
                    and v['signals_or_control_writes']==0 and v['missing_values_are_unknown'] and v['separate_reads_not_atomic']
                    and len(v['targets'])<=NATIVE_V2_CONTRACT['maximum_PG_wait_targets']
                    and 0<=v['started_monotonic']<=v['ended_monotonic']
                    and v['collection_seconds']>=0 and v['observer_thread_cpu_seconds']>=0 for v in waits),'NATIVE_PG_WAIT_COVERAGE')
            record.update(PG_wait_samples=len(waits),PG_wait_unknown_targets=summary['pg_wait_unknown_targets'],
                maximum_PG_wait_collection_seconds=max(v['collection_seconds'] for v in waits),
                separate_proc_SQL_device_snapshots_are_not_atomic=True,optional_missing_metadata_not_zero=True,
                IO_causality_proven=False)

            cpu=[summary['recorder_cpu_seconds'],summary['probe_thread_cpu_seconds'],summary['final_report_thread_cpu_seconds']]
            require(summary['recorder_cpu_available'] and all(v is not None and v>=0 for v in cpu) and sum(cpu)<=600*.05,'NATIVE_PG_INTERNAL_CPU')
            record.update(phase='collected',internal_thread_CPU_seconds=sum(cpu),internal_CPU_excludes_all_call_boundaries_and_server_overhead=True)
        except BaseException as error:
            record.update(phase='failed',reason=str(error) if isinstance(error,Rejected) else type(error).__name__);raise
        finally:self.save()

    def _business_native_original(self, role, folder, group, row):
        _,cid,_,actual_group=self.identity(role);require(actual_group==group,'EDGE_TIMING_OWN_GROUP')
        api_entry='/tmp/crg-timed-api-'+self.plan['run_id']+('0' if role=='dbs' else '1')+'00.py'
        self.ex(role,'/bin/bash','-c','set -Ce; umask 077; cat > '+api_entry+'; chmod 0444 '+api_entry,data=Path(API).read_text())
        require(self.ex(role,'sha256sum',api_entry).stdout.split()[0]==API_SHA,'EDGE_TIMED_API_COPY')
        context=self.root/(role+'-timing-context.json')
        with context.open('x') as stream:
            os.chmod(context,0o600);json.dump({'cgroup':str(group),'container_id':cid},stream)
        run_id = self.plan['run_id']+('0' if role == 'dbs' else '1')
        entry = '/tmp/crg-business-reload-'+run_id+'.py'
        for name in ['vendor-native-diagnostics-v3.py','vendor-pg-wait-v2.py','vendor-pg-wait.py','vendor-proc-read-error.py','vendor-device-state-observer.py']:
            helper_path='/tmp/'+name
            self.ex(role,'/bin/bash','-c','set -Ce; umask 077; cat > '+helper_path+'; chmod 0444 '+helper_path,data=(here/name).read_text())
            require(self.ex(role,'sha256sum',helper_path).stdout.split()[0]==NATIVE_V2_CONTRACT['sources'][name],'NATIVE_V2_HELPER_COPY')
        helper_entry='/tmp/vendor-native-diagnostics.py'
        self.ex(role,'/bin/bash','-c','set -Ce; umask 077; cat > '+helper_entry+'; chmod 0444 '+helper_entry,data=Path(DIAGNOSTIC_HELPER).read_text())
        require(self.ex(role,'sha256sum',helper_entry).stdout.split()[0]==DIAGNOSTIC_CONTRACT['helper_sha256'],'DIAGNOSTIC_HELPER_COPY')
        self.ex(role, '/bin/bash', '-c', 'set -Ce; umask 077; cat > '+entry+'; chmod 0444 '+entry,
                data=Path(NATIVE_V2_WORKER).read_text())
        require(self.ex(role, 'sha256sum', entry).stdout.split()[0] == NATIVE_V2_CONTRACT['worker_sha256'], 'WORKER_COPY')
        self.worker_log = (self.root/(role+'-native.log')).open('x')
        self.worker = subprocess.Popen(['kubectl', 'exec', '-n', self.ns, role+'-business', '-c', role, '--',
            'su', '-', 'postgres', '-c', 'CRG_VENDOR_SOAK_TEST=disposable-loopback-only CRG_VENDOR_NATIVE_DIAGNOSTICS=qualified-disposable-loopback-only CRG_PG_WAIT=authorized-disposable-readonly-only python '+entry+
            ' --run-id '+run_id+' --seconds 600 --test-phase smoke'], stdin=subprocess.DEVNULL,
            stdout=self.worker_log, stderr=self.worker_log)
        load = folder/('postgresql/basebackup/crg-soak-'+run_id+'/load.json');deadline = time.monotonic()+360
        while time.monotonic() < deadline:
            require(self.worker.poll() is None, 'NATIVE_PREPARATION_EXIT')
            if load.exists() and gate.read_json(load)[0].get('phase') == 'running':break
            self.reserve();time.sleep(1)
        else:raise Rejected('NATIVE_PREPARATION_360S')
        started = gate.audit.timestamp(gate.read_json(load)[0]['started_utc'])
        self.bind_native_worker(group,entry,run_id,row)
        _, _, host_pid, actual_group = self.identity(role);require(actual_group == group, 'OWN_GROUP')
        pid1_ticks = Path('/proc', str(host_pid), 'stat').read_text().rsplit(')',1)[1].split()[19]
        agents = self.processes(group, '/opt/crg/crg');caches = self.processes(group, '/opt/ccg/bin/containercacheguard')
        require(len(agents) == len(caches) == 1 and agents[0][2] == PINS['binary'], 'ONE_AGENT_CACHE')
        profile = folder/'crg-config/io-profile.json';profile_mtime = profile.stat().st_mtime_ns
        fixed = base.controls(group);expected = dict(fixed);intervals = row['reload_intervals']
        status = folder/'resource-state/status.json';samples = row['samples'];next_sample = [0]
        self.thread_session.start(session.listener_owner(group),group,THREAD_CONTRACT['duration_seconds']);self.save()
        def same():
            self.reserve()
            require(self.processes(group, '/opt/crg/crg') == agents and self.processes(group, '/opt/ccg/bin/containercacheguard') == caches
                    and Path('/proc', str(host_pid), 'stat').read_text().rsplit(')',1)[1].split()[19] == pid1_ticks
                    and int(dict(x.split() for x in (group/'memory.events').read_text().splitlines())['oom_kill']) == 0
                    and base.controls(group) == expected, 'PROCESS_OR_KERNEL_CHANGE')
            if time.monotonic() >= next_sample[0]:
                samples.append({'epoch':time.time(), 'actual_kernel_readbacks':base.controls(group), 'same_processes':True})
                next_sample[0]=time.monotonic()+60;self.save()
        def active():
            require(self.worker.poll() is None and time.time() < started+600, 'RELOAD_NATIVE_ENVELOPE')
        def wait_policy(name, policy, numeric, generation, symlink=False, rejected=None):
            nonlocal expected
            active();began = time.time();before = gate.read_json(status)[0];mark = self.write_config(folder, policy, symlink)
            deadline = time.monotonic()+60
            while time.monotonic() < deadline:
                active();self.reserve();d = gate.read_json(status)[0]
                cfg = d.get('configuration', {})
                fresh = status.stat().st_mtime_ns > mark
                if rejected:
                    ok = cfg.get('state') == 'rejected' and rejected in cfg.get('error','') and cfg.get('generation') == generation
                else:
                    ok = d.get('state') == 'managed' and cfg.get('state') == 'accepted' and cfg.get('generation') == generation
                    if 'cpu_percent' in policy:ok = ok and d.get('plan',{}).get('percentages') == policy
                    else:ok = ok and d.get('plan',{}).get('resource_mode') == 'manual'
                if fresh and ok:break
                time.sleep(.25)
            else:raise Rejected('RELOAD_DEADLINE_'+name)
            expected = dict(expected, **numeric);same()
            actual = base.controls(group)
            require(d['plan']['environment']['identity'] == row['identity'], 'STATUS_IDENTITY')
            if rejected:
                require(d['state']=='degraded' and cfg['accepted_hash']==before['configuration']['accepted_hash']
                        and d['plan']['percentages']==POLICIES[1], 'REJECTED_FULL_POLICY_RETENTION')
            interval = {'case':name, 'started_epoch':began, 'ended_epoch':time.time(), 'generation':generation,
                        'configuration_state':cfg['state'], 'requested_policy': policy if isinstance(policy,dict) else 'malformed JSON',
                        'expected_numeric':dict(expected), 'actual_kernel_readbacks':actual,
                        'same_Agent_PID1_cache':True, 'PG_not_restarted':self.sql(role,'SELECT pg_postmaster_start_time();') == row['primary_start']}
            intervals.append(interval)
            self.check(role+'-'+name, interval['PG_not_restarted'] and actual == expected)
        def edge_interval(name, began, d, extra=None):
            actual=base.controls(group)
            require(actual==expected and d['plan']['environment']['identity']==row['identity'],'EDGE_KERNEL_OR_IDENTITY')
            interval={'case':name,'started_epoch':began,'ended_epoch':time.time(),
                'generation':d['configuration']['generation'],'configuration_state':d['configuration']['state'],
                'accepted_hash':d['configuration']['accepted_hash'],'expected_numeric':dict(expected),
                'actual_kernel_readbacks':actual,'same_Agent_PID1_cache':True,
                'PG_not_restarted':self.sql(role,'SELECT pg_postmaster_start_time();')==row['primary_start']}
            if extra:interval.update(extra)
            intervals.append(interval);self.check(role+'-'+name,interval['PG_not_restarted'])

        def pressure30to20():
            nonlocal expected
            active();began=time.time();target=13334654976;policy=dict(POLICIES[0],memory_percent=20)
            old_high=int(EXPECTED[0]['memory.high']);chunk=64<<20;maximum=12<<30;ceiling=old_high-(2<<30)
            entry='/tmp/crg-memory-pressure-'+self.plan['run_id']+('0' if role=='dbs' else '1')+'.py'
            self.ex(role,'/bin/bash','-c','set -Ce; umask 077; cat > '+entry+'; chmod 0444 '+entry,data=Path(PRESSURE_WORKER).read_text())
            require(self.ex(role,'sha256sum',entry).stdout.split()[0]==PRESSURE_SHA,'PRESSURE_HELPER_COPY')
            log=(self.root/(role+'-pressure-helper.log')).open('x');holder=None;owned=None;allocated=0
            record={'started_epoch':began,'target_memory_high_bytes':target,'old_memory_high_bytes':old_high,'events':[],'host_samples':[],
                'worker_sha256':PRESSURE_SHA,'maximum_helper_bytes':maximum,'maximum_group_bytes':ceiling,'host_reserve_bytes':8<<30,
                'direct_control_file_writes':False,'high_is_not_a_hard_cap':True,'external_memory_max':expected['memory.max']}
            row['pressure30to20']=record;self.save()
            def recv(timeout=5):
                ready,_,_=select.select([holder.stdout],[],[],timeout);require(bool(ready),'PRESSURE_HELPER_RESPONSE_5S')
                line=holder.stdout.readline(4097);require(line.endswith('\n') and len(line)<=4096,'PRESSURE_HELPER_BOUNDED_RESPONSE');return json.loads(line)
            def send(op):
                holder.stdin.write(json.dumps({'op':op})+'\n');holder.stdin.flush();reply=recv()
                require(reply.get('phase')=='ack' and reply.get('op')==op,'PRESSURE_HELPER_ACK')
                record['events'].append(dict(reply,observed_epoch=time.time()));return reply
            def safe_snapshot(transition=False):
                active();self.reserve();require(holder.poll() is None and owned is not None and gate.proc(owned['pid'],entry,owned['start_ticks'])['live'],'PRESSURE_HELPER_IDENTITY');send('ping')
                current=int((group/'memory.current').read_text());available=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024
                require(current<ceiling and available>=8<<30,'PRESSURE_BUDGET_OR_RESERVE')
                require(self.processes(group,'/opt/crg/crg')==agents and self.processes(group,'/opt/ccg/bin/containercacheguard')==caches
                    and Path('/proc',str(host_pid),'stat').read_text().rsplit(')',1)[1].split()[19]==pid1_ticks,'PRESSURE_PROCESS_CHANGE')
                events=dict((k,int(v)) for k,v in [s.split() for s in (group/'memory.events').read_text().splitlines()])
                require(events['oom']==0 and events['oom_kill']==0,'PRESSURE_OOM')
                actual=base.controls(group)
                require(all(actual[k]==expected[k] for k in base.CONTROLS if k!='memory.high')
                    and actual['memory.high'] in ([str(old_high),str(target)] if transition else [expected['memory.high']]),'PRESSURE_OTHER_CONTROL_CHANGE')
                sample={'epoch':time.time(),'memory_current':current,'host_available':available,'allocated_bytes':allocated,'memory_events':events,'controls':actual}
                record['host_samples'].append(sample);self.save();return current,available,events
            try:
                holder=subprocess.Popen(['kubectl','exec','-i','-n',self.ns,role+'-business','-c',role,'--','env','CRG_MEMORY_PRESSURE_TEST=authorized-disposable-loopback-only','python','-u',entry],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,bufsize=1)
                hello=recv();record['hello']=hello;self.save();require(hello.get('phase')=='ready' and hello.get('maximum_bytes')==maximum and hello.get('chunk_bytes')==chunk and hello.get('lease_seconds')==10 and hello.get('lifetime_seconds')==240,'PRESSURE_HELPER_CONTRACT')
                found=[]
                for pid in (group/'cgroup.procs').read_text().splitlines():
                    try:
                        p=Path('/proc',pid);fields=(p/'stat').read_text().rsplit(')',1)[1].split()
                        if entry.encode() in (p/'cmdline').read_bytes().split(b'\0') and fields[0]!='Z':found.append({'pid':int(pid),'start_ticks':int(fields[19]),'entry':entry})
                    except (FileNotFoundError,ProcessLookupError):pass
                require(len(found)==1,'ONE_OWN_PRESSURE_HELPER');owned=found[0];record['process']=owned
                deadline=time.monotonic()+60
                while time.monotonic()<deadline:
                    current,available,events=safe_snapshot()
                    if current>target+(256<<20):break
                    require(current+chunk<ceiling and available>=(8<<30)+chunk+(256<<20) and allocated+chunk<=maximum,'PRESSURE_NEXT_CHUNK_UNSAFE')
                    ack=send('allocate');allocated+=chunk;require(ack['allocated_bytes']==allocated,'PRESSURE_ALLOCATION_ACK')
                else:raise Rejected('REAL_20_PERCENT_PRESSURE_PREPARATION_60S')
                require(current>target+(256<<20),'INITIAL_CURRENT_ABOVE_TARGET');events_before=events.copy()
                mark=self.write_config(folder,policy);deadline=time.monotonic()+60;record.update(initial_current=current,mutation_mark_ns=mark,events_before=events_before);self.save()
                while time.monotonic()<deadline:
                    current,available,events=safe_snapshot(True);d=gate.read_json(status)[0];cfg=d.get('configuration',{})
                    memory=next((i for i in d.get('items',[]) if i['file']=='memory.high'),{})
                    if status.stat().st_mtime_ns>mark and cfg.get('state')=='accepted' and cfg.get('generation')==7 and d.get('state')=='managed' and memory.get('state')=='applied' and base.controls(group)['memory.high']==str(target):break
                    time.sleep(.25)
                else:raise Rejected('REAL_MEMORY_HIGH30_TO20_APPLY_60S')
                require(d['plan']['percentages']==policy,'REAL_20_PERCENT_REQUEST_VISIBLE');expected=dict(expected,**{'memory.high':str(target)})
                hold=time.monotonic()+6
                while time.monotonic()<hold:current,available,events=safe_snapshot();time.sleep(.25)
                journal=gate.read_json(folder/'resource-state/journal.json')[0];mutation=journal['mutations']['memory.high:']
                require(mutation['applied']==str(target) and not mutation.get('pending') and not mutation.get('conflict') and 'memory.max:' not in journal['mutations'],'OWNED_HIGH_ONLY_JOURNAL')
                require(events['high']>events_before['high'],'MEMORY_HIGH_RECLAIM_THROTTLE_EVENT_REQUIRED')
                accepted_hash=cfg['accepted_hash'];record.update(accepted_hash=accepted_hash,status_mtime_ns=status.stat().st_mtime_ns,hold_seconds=6,journal_during_pressure=journal);self.save()
                edge_interval('memory-high30-to20-applies-and-reclaims-or-throttles-under-real-pressure',began,d,{'requested_policy':policy,'target_memory_high_bytes':target,'initial_current_above_target':True,'hold_seconds':6,'events_high_delta':events['high']-events_before['high'],'external_memory_max_unchanged':True})
                release_started=time.time();require(send('release')['allocated_bytes']==0,'PRESSURE_RELEASE_ACK');allocated=0
                require(send('exit')['allocated_bytes']==0,'PRESSURE_EXIT_ACK');released=recv()
                require(released['phase']=='released' and released['allocated_bytes']==0 and holder.wait(timeout=5)==0,'PRESSURE_RELEASE_EXIT')
                require(not gate.proc(owned['pid'],entry,owned['start_ticks'])['live'],'PRESSURE_WORKER_NOT_GONE');record.update(released=released,worker_gone_after_release=True)
                deadline=time.monotonic()+60;transition=[]
                while time.monotonic()<deadline:
                    active();same();d=gate.read_json(status)[0];current=int((group/'memory.current').read_text());cfg=d.get('configuration',{})
                    transition.append({'epoch':time.time(),'memory_current':current,'memory_high':base.controls(group)['memory.high']})
                    if current+current//20+(16<<20)<=target and d.get('state')=='managed' and cfg.get('state')=='accepted' and cfg.get('generation')==7:
                        require(cfg['accepted_hash']==accepted_hash and d['plan']['percentages']==policy,'PRESSURE_RELEASE_POLICY_OR_GENERATION');break
                    time.sleep(.25)
                else:raise Rejected('REAL_MEMORY_HIGH20_RELEASE_RECOVERY_60S')
                record['release_observations']=transition;self.save()
                edge_interval('memory-high20-release-recovers-same-generation7-without-config-rewrite',release_started,d,{'target_memory_high_bytes':target,'accepted_hash_before_release':accepted_hash,'no_configuration_rewrite':True,'pressure_worker_gone':True,'external_memory_max_unchanged':True})
            finally:
                if holder is not None:
                    if holder.poll() is None:
                        if holder.stdin and not holder.stdin.closed:holder.stdin.close()
                        try:holder.wait(timeout=15)
                        except subprocess.TimeoutExpired:
                            holder.terminate()
                            try:holder.wait(timeout=5)
                            except subprocess.TimeoutExpired:holder.kill();holder.wait(timeout=5)
                            record['kubectl_cleanup_forced']=True
                    if owned is not None:record['worker_gone_on_final_check']=not gate.proc(owned['pid'],entry,owned['start_ticks'])['live']
                log.close();record['ended_epoch']=time.time();self.save()
                if owned is not None:require(record['worker_gone_on_final_check'],'PRESSURE_MEMORY_RELEASE_NOT_PROVEN')

        # Preserve the smoke campaign's original 30-second engine scheduling.
        while time.time() < started+30:active();same();time.sleep(max(0,min(1, started+30-time.time())))
        engine_dir = self.root/(role+'-engine');self.engine_log = (self.root/(role+'-engine.log')).open('x')
        engine_began = time.time()
        self.engine_job = subprocess.Popen(['python3', ENGINE, '--namespace', self.ns, '--work-dir', str(engine_dir),
            '--run-id', run_id+'00', '--cleanup-fixture', '--native-campaign-probes', '--role', role],
            stdin=subprocess.DEVNULL, stdout=self.engine_log, stderr=self.engine_log)
        wait_policy('manual-to-percent-during-engine', POLICIES[0], EXPECTED[0], 2)
        require(self.engine_job.poll() is None, 'NO_ENGINE_RELOAD_OVERLAP')
        wait_policy('three-independent-percentages-during-native', POLICIES[1], EXPECTED[1], 3)
        wait_policy('invalid-IO-retains-entire-policy', dict(POLICIES[1],io_percent=101), {}, 3, rejected='io_percent')
        wait_policy('partial-JSON-retains-entire-policy', b'{"cpu_percent":', {}, 3, rejected='EOF')
        wait_policy('duplicate-key-retains-entire-policy', b'{"cpu_percent":25,"cpu_percent":30}', {}, 3, rejected='duplicate')
        wait_policy('ConfigMap-style-symlink-accepts-valid-policy', POLICIES[0], EXPECTED[0], 4, symlink=True)
        wait_policy('percent-to-manual-three-resources', MANUAL, {k:fixed[k] for k in base.CONTROLS[:3]}, 5)
        wait_policy('pressure-test-return-to-percent30',POLICIES[0],EXPECTED[0],6)
        pressure30to20()
        wait_policy('released-memory20-returns-to-percent30',POLICIES[0],EXPECTED[0],8)

        end_deadline = time.monotonic()+720
        while self.worker.poll() is None and time.monotonic() < end_deadline:
            same()
            if self.engine_job.poll() is not None and 'engine' not in row:
                self.engine_log.close();self.engine_log=None
                engine, _ = gate.read_json(engine_dir/'business-backup.json');item=engine['roles'][role]
                require(self.engine_job.returncode == 0 and engine['phase'] == 'content-passed-native-pending'
                        and len(item['checks']) == 10 and all(x['passed'] for x in item['checks'])
                        and item.get('own_fixture_schema_restore_database_snapshot_removed') is True, 'ENGINE_CONTENT')
                row['engine']=engine;row['engine_interval']={'started_epoch':engine_began,'ended_epoch':time.time()};self.save()
            require(time.time()-engine_began <= 1800 or self.engine_job.poll() is not None, 'ENGINE_1800S')
            time.sleep(1)
        row['native_exit']=self.worker.poll()
        native, _ = gate.read_json(load);row['native']=native;self.save()
        require(row['native_exit'] == 0, 'NATIVE_COMPLETION_EXIT')
        self.worker_log.close();self.worker_log=None;self.worker=None
        native, _ = gate.read_json(load);row['native']=native;self.save();base.validate_native(native,run_id)
        finish=gate.audit.timestamp(native['measurement_finished_utc'])
        require('engine' in row and self.engine_job.poll() == 0, 'ENGINE_INSIDE_NATIVE_MISSING')
        covered = [*intervals,row['engine_interval']]
        self.check(role+'-600s-native-surrounds-reload-backup-stream-restore',
            len(intervals)==11 and all(started <= x['started_epoch'] <= x['ended_epoch'] <= finish for x in covered)
            and len(samples)>=600/60*.98 and all(b['epoch']-a['epoch']<=120 for a,b in zip(samples,samples[1:]))
            and samples[0]['epoch']-started<=120 and finish-samples[-1]['epoch']<=120)
        row['engine_native_validation']='passed-with-entire-600s-native';self.engine_job=None
        self.check(role+'-same-Agent-PID1-PG-cache-profile-and-zero-OOM',
            self.sql(role,'SELECT pg_postmaster_start_time();')==row['primary_start']
            and gate.digest(profile)['sha256']==PINS['profile'] and profile.stat().st_mtime_ns==profile_mtime)
        same()
