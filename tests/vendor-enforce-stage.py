#!/usr/bin/env python3
"""One-off lab acceptance fixture, never a production multi-container controller.

Default is read-only. Formal execution requires full accepted baseline receipts,
frozen source hashes and the same pinned Pods/processes. No cgroup writes here:
only each container's own source-qualified CRG CLI may apply/restore its limits.
"""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shlex
import shutil
import stat
import subprocess
import time
import uuid
from functools import wraps

OLD = 'dcebdc56f8e1fdd3c58a4a67abe58d3cc4e6b0d4e486a28c7e80fa8671f45eec'
NEW = '0a0799f5c992b8b4ddb983bec12a8061965a4fbed4c419d47cd7c7607dbecf15'
CACHE = '757ba385a0ee4bdadc968b96b5c3e69fd44353060e5ab28520fd6f73a59902de'
FIXTURE_SOURCES = {
    'crg': OLD, 'containercacheguard': CACHE,
    'optional-agent.sh': 'f7e7208f58bac7066d75d49cb17199b720e3d05bb5953e2a7a7800f881b54b79',
    'io-profile.json': '33eb53703bb6eb28ef2964ec5514e40cdef92c5bba48741245ecc27c185743e0',
}
for _role in ['dbs', 'hisdbs']:
    FIXTURE_SOURCES[_role+'/resource.json'] = 'f75499b429c2272a2d6df8af9c568199fd64391eff64763ac2588dec2250c90a'
    FIXTURE_SOURCES[_role+'/cache.json'] = 'f28014fa669e5e500ff12a0fc904273a7bd1a2a0b97f7384d045c75e30436a6f'
    FIXTURE_SOURCES[_role+'/supervisor.sh'] = '4dce0b38e6c01a9effe08457dc31206a0abaf7ff14eb9ec59dace97a6f1c0211'
TOOLS = {
    'vendor-soak-campaign.py': '8932874640816c365963513872567afd0c5b75247102d9866f511b0fb6440aa5',
    'vendor-soak-load.py': 'ba87ef2d646b723eb8419de25ffcd736f7a5b0925716f4b638761dff70bb2461',
    'vendor-engine-smoke.py': '13f25d2282c648d52f3234e86145d8200a4381a26f5246fc6304f3e32ced6b3b',
}
CONTROLS = ['cpu.max', 'memory.max', 'io.max', 'pids.max', 'cpu.weight', 'io.weight', 'memory.high', 'memory.swap.max']
FORMAL_NAMESPACE = 'crg-vendor-lab-20261110'
REHEARSAL_LAUNCHER = '107df85230089863615ec3312ab4db96a8a9da6bbe1a19cb0c66d7bf9c373a80'


def candidate_config():
    return {'resource_mode': 'manual', 'mode': 'enforce',
            'limits': {'cpu_cores': 7.2, 'memory_max': '20001980416B', 'io_read_bps': '64MiB',
                       'io_write_bps': '64MiB', 'io_read_iops': 4096, 'io_write_iops': 4096},
            'data_paths': ['/opt/postgresql'], 'state_dir': '/crgstate',
            'interval_seconds': 15, 'log_dir': '/crgstate/logs'}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def observe_for(seconds, interval, observe, now=time.monotonic, sleep=time.sleep):
    """Anchor samples to scheduled times; slow checks cannot create bursts."""
    started = now();deadline = started+seconds;due = started;count = 0
    while now() < deadline:
        observe();count += 1
        due += interval
        current = now()
        if current >= due:
            due = started+(math.floor((current-started)/interval)+1)*interval
        sleep(max(0, min(deadline, due)-current))
    return now()-started, count


def bounded(path, maximum=8*1024**2):
    path = Path(path)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= maximum,
            'input is not a bounded single-linked regular file')
    return path.read_bytes()


def read_json(path):
    return json.loads(bounded(path))


def digest(path):
    return hashlib.sha256(bounded(path, 32*1024**2)).hexdigest()


def safe_directory(path):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts and path.resolve() == path,
            'directory resolves through a symlink or is not absolute')
    require(path.is_dir() and path.stat().st_uid == os.geteuid(), 'directory owner differs')
    return path


def validate_manifest(m):
    require(m.get('schema') == 'crg-vendor-enforce-stage-v1', 'manifest schema differs')
    require(m.get('kind') in ['formal', 'rehearsal'], 'unknown stage kind')
    for key in ['fixture_root', 'baseline_work_dir', 'tools_root', 'candidate_binary']:
        p = PurePosixPath(m[key])
        require(p.is_absolute() and '..' not in p.parts and str(p).startswith('/var/tmp/crg-'),
                'only explicit private lab paths accepted')
    require(re.fullmatch(r'[0-9]{8,12}', m['source_run_id']) is not None and
            re.fullmatch(r'[0-9]{8,12}', m['new_run_id']) is not None and
            m['source_run_id'] != m['new_run_id'], 'invalid or reused run ID')
    if m['kind'] == 'formal':
        require(m['namespace'] == FORMAL_NAMESPACE and
                m['fixture_root'] == '/var/tmp/crg-business-20261110' and
                m['baseline_work_dir'] == '/var/tmp/crg-baseline24h-20261110' and
                m['tools_root'] == '/var/tmp/crg-baseline-tools-20261110' and
                m['source_run_id'] == '202611100705', 'formal baseline identity differs')
    else:
        require(re.fullmatch(r'crg-vendor-lab-stage[a-z0-9-]+', m['namespace']) is not None and
                m['namespace'] != FORMAL_NAMESPACE and
                str(m['fixture_root']).startswith('/var/tmp/crg-stage-rehearsal-') and
                str(m['baseline_work_dir']).startswith('/var/tmp/crg-stage-rehearsal-'),
                'rehearsal cannot target the formal baseline')
    require(re.fullmatch(r'[0-9a-f-]{36}', m['namespace_uid']) is not None, 'namespace UID missing')
    require(set(m['roles']) == {'dbs', 'hisdbs'}, 'both roles must be pinned')
    require(m['fixture_sources'] == FIXTURE_SOURCES, 'fixture source contract differs')
    for role, row in m['roles'].items():
        require(re.fullmatch(r'[0-9a-f]{64}', row['container_id']) is not None and
                re.fullmatch(r'[0-9a-f-]{36}', row['pod_uid']) is not None, 'Pod/container IDs missing')
        require(set(row['controls']) == set(CONTROLS) and
                row['controls']['cpu.max'] == '800000 100000' and
                row['controls']['memory.max'] == '21474836480' and row['controls']['io.max'] == '',
                'original eight control values or original budget differ')
        for key in ['main', 'helper']:
            require(row[key]['pid'] > 1 and row[key]['start_ticks'] > 0, 'process identity missing')
        require(row['helper']['ppid'] == row['main']['pid'], 'helper is not the original PID1 child')
        membership = row['membership'].splitlines()
        require(len(membership) == 1 and membership[0].startswith('0::/') and
                '..' not in Path(membership[0][3:]).parts and
                row['cgroup'] == '/sys/fs/cgroup'+membership[0][3:], 'pure v2 leaf membership required')
        require(len(row['actors']['crg']) == len(row['actors']['containercacheguard']) == 1,
                'one original resource and cache Agent required')
        require(row['actors']['crg'][0]['sha256'] == OLD and
                row['actors']['crg'][0]['ppid'] == row['helper']['pid'] and
                row['actors']['containercacheguard'][0]['sha256'] == CACHE,
                'original Agent/helper source differs')


def evidence_gate(function):
    """Malformed private receipts are a closed gate, never an exception bypass."""
    @wraps(function)
    def checked(*args, **kwargs):
        try:
            return bool(function(*args, **kwargs))
        except (AttributeError, KeyError, TypeError, ValueError, OverflowError):
            return False
    return checked


@evidence_gate
def accepted_native(n, duration):
    if not (n.get('phase') == 'passed' and n.get('requested_duration_seconds') == duration and
            math.isfinite(n.get('elapsed_seconds', 0)) and n.get('elapsed_seconds', 0) >= duration and n.get('payload_integrity') is True and
            n.get('primary_not_restarted') is True and n.get('threads_stopped') is True and
            n.get('interrupted') is False and len(n.get('final_checksum', [])) == 5 and
            len(n.get('initial_checksum', [])) == 5 and n['initial_checksum'][:4] == n['final_checksum'][:4] and
            n['final_checksum'][0] == 16384 and n['final_checksum'][2] == 67108864):
        return False
    for kind, period in [('sql', 2), ('api', 5)]:
        item = n.get(kind, {});histogram = item.get('histogram', []);count = item.get('attempts', 0)
        if not (type(count) is int and count > 0 and count >= duration/period*.98 and item.get('successes') == count and
                item.get('errors') == 0 and len(histogram) == 12 and
                all(type(x) is int and x >= 0 for x in histogram) and sum(histogram) == count and
                sum(histogram[:9]) >= count*.95 and 0 <= item.get('max_seconds', math.inf) <= 5 and
                0 <= item.get('p95_bucket_upper_seconds', math.inf) <= 1 and
                math.isfinite(item.get('sample_coverage', 0)) and item.get('sample_coverage', 0) >= .98):
            return False
    return True


def epoch(text):
    return datetime.datetime.fromisoformat(text.replace('Z', '+00:00')).timestamp()


@evidence_gate
def accepted_campaign(report, duration, phase, agent_sha256=OLD):
    if not (report.get('phase') == 'passed' and report.get('test_phase') == phase and
            report.get('requested_seconds') == duration and not report.get('cleanup_errors') and
            report.get('agent_sha256') == agent_sha256 and report.get('cache_sha256') == CACHE and
            report.get('campaign_script_sha256') == TOOLS['vendor-soak-campaign.py'] and
            report.get('worker_sha256') == TOOLS['vendor-soak-load.py'] and
            report.get('engine_script_sha256') == TOOLS['vendor-engine-smoke.py'] and
            set(report.get('roles', {})) == {'dbs', 'hisdbs'}):
        return False
    offsets = [300, 21600, 43200, 64800] if phase == 'baseline' else [30]
    if report.get('criteria', {}).get('backup_offsets_seconds') != offsets:
        return False
    cycles = report.get('backups', [])
    if len(cycles) != len(offsets):
        return False
    for role, row in report['roles'].items():
        native = row.get('workload', {});samples = row.get('samples', [])
        if not accepted_native(native, duration) or len(samples) < math.ceil(duration/60*.98):
            return False
        times = [x['elapsed_seconds'] for x in samples]
        if not (all(math.isfinite(x) for x in times) and 0 <= times[0] <= 60 and
                duration-120 <= times[-1] <= duration+120 and
                all(0 < b-a <= 120 for a, b in zip(times, times[1:]))):
            return False
        if not all(x.get('agent_same_process') and x.get('cache_same_process') and x.get('PID1_same_process') for x in samples):
            return False
        for index, cycle in enumerate(cycles):
            if not (cycle.get('phase') == 'passed' and
                    cycle.get('native_workload_validation') == 'passed-with-entire-campaign' and
                    cycle.get('offset_seconds', -1) >= offsets[index] and
                    epoch(native['started_utc']) <= cycle['content_started_epoch'] <= cycle['content_ended_epoch'] <= epoch(native['measurement_finished_utc']) and
                    set(cycle.get('roles', {})) == {'dbs', 'hisdbs'}):
                return False
            item = cycle['roles'][role]
            if not (item.get('checks') == 10 and item.get('cleanup') is True and item.get('native_pending') is True):
                return False
    return True


def process(pid):
    p = Path('/proc', str(pid));text = p.joinpath('stat').read_text();v = text[text.rfind(')')+2:].split()
    require(v[0] != 'Z', 'process is terminal')
    return {'pid': int(pid), 'ppid': int(v[1]), 'start_ticks': int(v[19])}


def entry_live(pid, entry):
    try:
        return entry.encode() in Path('/proc', str(pid), 'cmdline').read_bytes().split(b'\0')
    except FileNotFoundError:
        return False


def run(command, timeout=30):
    result = subprocess.run([str(x) for x in command], capture_output=True, text=True, timeout=timeout)
    require(result.returncode == 0, 'owned lab command failed; inspect private receipt')
    return result


class Stage:
    def __init__(self, manifest):
        validate_manifest(manifest)
        self.m = manifest
        self.base = Path(manifest['fixture_root'])
        self.fixture = self.base/'fixture'
        self.tools = Path(manifest['tools_root'])
        self.report = {'schema': 'crg-vendor-enforce-stage-report-v1', 'phase': 'checking',
                       'kind': manifest['kind'], 'checks': {}, 'operations': [],
                       'stage_source_sha256': digest(Path(__file__)),
                       'scope': 'lab fixture only; not a production multi-container controller'}
        self.output = None
        self.disabled = []
        self.old_configs = {}
        self.expected = {}
        self.oom = {}
        self.fixed_agent = {}
        self.changed_sources = dict(FIXTURE_SOURCES)

    def check(self, name, function):
        try:
            passed = bool(function())
            row = {'passed': passed}
        except Exception as error:
            row = {'passed': False, 'failure_class': type(error).__name__}
            if type(error) is RuntimeError:
                row['detail'] = str(error)
        self.report['checks'][name] = row
        return row['passed']

    def snapshot_controls(self, role):
        group = Path(self.m['roles'][role]['cgroup'])
        return {name: (group/name).read_text().strip() for name in CONTROLS}

    def actors(self, role):
        row = self.m['roles'][role];found = {'crg': [], 'containercacheguard': []}
        for pid in Path(row['cgroup'], 'cgroup.procs').read_text().splitlines():
            try:
                p = Path('/proc', pid);argv = p.joinpath('cmdline').read_bytes().split(b'\0')
                name = Path(os.fsdecode(argv[0])).name
                if name in found and (name != 'crg' or len(argv) > 1 and argv[1] == b'run'):
                    found[name].append({**process(pid), 'sha256': hashlib.sha256(p.joinpath('exe').read_bytes()).hexdigest()})
            except (FileNotFoundError, ProcessLookupError):
                pass
        return found

    def live(self, role, api=False, exact_old=False):
        row = self.m['roles'][role]
        for key in ['main', 'helper']:
            require(process(row[key]['pid']) == row[key], 'original business/helper identity changed')
            require(Path('/proc', str(row[key]['pid']), 'cgroup').read_text() == row['membership'], 'process cgroup changed')
        group = Path(row['cgroup'])
        require(group.resolve() == group and group.name == 'cri-containerd-'+row['container_id']+'.scope' and
                '/kubepods.slice/' in str(group), 'not the pinned own leaf')
        actors = self.actors(role)
        require(actors['containercacheguard'] == row['actors']['containercacheguard'], 'original cache process changed')
        require(len(actors['crg']) <= 1 and all(a['sha256'] in [OLD, NEW] and a['ppid'] == row['helper']['pid'] for a in actors['crg']), 'unexpected Agent writer')
        if exact_old:
            require(actors['crg'] == row['actors']['crg'], 'original resource process changed')
        cache = read_json(self.base/(role+'-business/cache-state/status.json'))
        require(cache.get('action') == 'enforce', 'original cache no longer enforcing')
        if api:
            pod = json.loads(run(['kubectl', 'get', 'pod', '-n', self.m['namespace'], role+'-business', '-o', 'json']).stdout)
            require(pod['metadata']['uid'] == row['pod_uid'] and pod['metadata'].get('labels', {}).get('managed-by') == 'crg-vendor-test' and
                    not any(pod['spec'].get(f) for f in ['hostPID', 'hostIPC', 'hostNetwork']), 'lab Pod identity differs')
            container = next(x for x in pod['status']['containerStatuses'] if x['name'] == role)
            require(container['containerID'] == 'containerd://'+row['container_id'] and container['restartCount'] == 0, 'container incarnation changed')
            require(container['imageID'] == row['image_id'], 'original image identity changed')
            runtime = json.loads(run(['crictl', 'inspect', row['container_id']]).stdout)
            require(runtime['info']['pid'] == row['main']['pid'], 'runtime PID differs')
            spec = next(x for x in pod['spec']['containers'] if x['name'] == role)
            mounts = {x['mountPath']: x for x in spec['volumeMounts']}
            volumes = {x['name']: x for x in pod['spec']['volumes']}
            for inside, host in [('/crgfixture', self.fixture), ('/opt/postgresql', self.base/(role+'-business/postgresql')),
                                 ('/crgstate', self.base/(role+'-business/resource-state')), ('/ccgstate', self.base/(role+'-business/cache-state'))]:
                mount = mounts[inside]
                require(Path(volumes[mount['name']]['hostPath']['path']) == host and host.resolve() == host, 'host fixture mount differs')
                actual = Path('/proc', str(row['main']['pid']), 'root')/inside.lstrip('/')
                left, right = host.stat(), actual.stat()
                require((left.st_dev, left.st_ino) == (right.st_dev, right.st_ino), 'actual mounted directory inode differs')
                if inside == '/crgfixture':
                    require(mount.get('readOnly') is True, 'original fixture mount is not read-only')
                    entries = [line.split(' - ', 1)[0].split() for line in Path('/proc', str(row['main']['pid']), 'mountinfo').read_text().splitlines()]
                    require(any(len(x) >= 6 and x[4] == inside and 'ro' in x[5].split(',') for x in entries), 'actual fixture mount is not read-only')
            for kind in ['pid', 'mnt', 'net']:
                require(Path('/proc', str(row['main']['pid']), 'ns', kind).stat().st_ino != Path('/proc/1/ns', kind).stat().st_ino,
                        'host namespace is not an isolated lab fixture')
            require('state DOWN' in run(['nsenter', '-t', str(row['main']['pid']), '-n', '--', 'ip', '-o', 'link', 'show', 'dev', 'eth0']).stdout,
                    'non-loopback network isolation differs')
        return True

    def reserve(self):
        available = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
        require(available >= 8*1024**3 and shutil.disk_usage(self.base).free >= 20*1024**3, 'original host reserve threshold reached')
        return True

    def receipts(self):
        duration = 86400 if self.m['kind'] == 'formal' else 600
        phase = 'baseline' if self.m['kind'] == 'formal' else 'smoke'
        baseline = read_json(Path(self.m['baseline_work_dir'])/'report.json')
        require(accepted_campaign(baseline, duration, phase), 'entire prior campaign not accepted')
        coordinator = self.m['baseline_coordinator']
        require(not entry_live(coordinator['pid'], coordinator['entry']), 'baseline coordinator still live')
        for role in ['dbs', 'hisdbs']:
            native = read_json(self.base/(role+'-business/postgresql/basebackup/crg-soak-'+self.m['source_run_id']+'/load.json'))
            require(accepted_native(native, duration) and native == baseline['roles'][role]['workload'], 'native terminal receipt differs')
            require(baseline['roles'][role]['fixed_controls'] == self.m['roles'][role]['controls'], 'original recorded controls differ')
            group = Path(self.m['roles'][role]['cgroup'])
            for pid in group.joinpath('cgroup.procs').read_text().splitlines():
                require(not entry_live(int(pid), '/tmp/crg-soak-load-'+self.m['source_run_id']+'.py'), 'prior native worker still live')
        if self.m['kind'] == 'formal':
            adoption = read_json('/var/tmp/crg-adoption19-20261110/report.json')
            require(adoption.get('phase') == 'passed' and len(adoption['tests']) == 68 and all(x['passed'] for x in adoption['tests']) and
                    set(adoption['roles']) == {'baseline-dbs', 'baseline-hisdbs', 'realpath-dbs', 'realpath-hisdbs'} and
                    adoption['sources']['previous']['binary_sha256'] == OLD and adoption['sources']['candidate']['binary_sha256'] == NEW,
                    'first adoption rehearsal not accepted')
            for row in adoption['roles'].values():
                require(accepted_native(row['native'], 600) and row['candidate_hold_seconds'] >= 120 and
                        row['own_pod_removed'] and row['own_cgroup_removed'], 'adoption cell incomplete')
            require(not entry_live(3180148, '/var/tmp/crg-realpath-tools-20261110/adoption19-job.py'), 'adoption still live')
            overhead = read_json('/var/tmp/crg-overhead-r35-20261110/report.json')
            require(overhead.get('phase') == 'passed' and overhead.get('measurement_elapsed_seconds', 0) >= 1800 and overhead.get('namespace_absent'), 'overhead prerequisite incomplete')
            require(not entry_live(2602146, '/var/tmp/crg-realpath-tools-20261110/overhead-r35-job.py'), 'overhead still live')
            for namespace in ['crg-vendor-lab-adoption19-20261110', 'crg-overhead-r35-20261110']:
                require(not run(['kubectl', 'get', 'namespace', namespace, '--ignore-not-found', '-o', 'json']).stdout.strip(), 'prior private fixture not cleaned')
            require(read_json('/var/tmp/crg-r30-20261110/actual/report.json').get('phase') == 'passed', 'engineering prerequisite failed')
        return True

    def shared_rehearsal(self):
        if self.m['kind'] == 'rehearsal':
            return True
        path = self.m.get('shared_stage_rehearsal_report', '')
        require(str(path).startswith('/var/tmp/crg-enforce-stage-'), 'shared-program rehearsal receipt missing')
        result = read_json(path)
        require(result.get('phase') == 'rehearsal-passed-restored' and result.get('kind') == 'rehearsal' and
                result.get('stage_source_sha256') == self.report['stage_source_sha256'] and
                result.get('candidate_sha256') == NEW and result.get('previous_sha256') == OLD and
                result.get('candidate_hold_seconds', 0) >= 120 and result.get('backout', {}).get('restored') is True,
                'this exact shared-program stage has no accepted rehearsal')
        cleanup = result.get('fixture_cleanup', {})
        require(result.get('rehearsal_launcher_sha256') == REHEARSAL_LAUNCHER and cleanup.get('namespace_absent') is True and
                set(cleanup.get('pods', {})) == {'dbs', 'hisdbs'} and
                all(x.get('pod_absent') is True and x.get('cgroup_absent') is True for x in cleanup['pods'].values()),
                'exact rehearsal launcher or complete fixture cleanup missing')
        campaign = result['campaign_result']
        require(accepted_campaign(campaign, 600, 'smoke', agent_sha256=NEW),
                'full shared-program enforced600s not accepted')
        namespace = result['namespace']
        require(re.fullmatch(r'crg-vendor-lab-stage[a-z0-9-]+', namespace) is not None and
                not run(['kubectl', 'get', 'namespace', namespace, '--ignore-not-found', '-o', 'json']).stdout.strip(),
                'shared-program rehearsal namespace still present')
        return True

    def no_other_business_fixtures(self):
        pods = json.loads(run(['kubectl', 'get', 'pods', '-A', '-l', 'managed-by=crg-vendor-test', '-o', 'json']).stdout)
        allowed = {self.m['namespace']}
        if self.m['kind'] == 'rehearsal':
            allowed.add(FORMAL_NAMESPACE)  # The original baseline stays live.
        require(all(x['metadata']['namespace'] in allowed for x in pods['items']), 'other disposable business fixtures remain')
        return True

    def preflight(self):
        self.check('private-directories', lambda: all(safe_directory(p) for p in [self.base, self.fixture, self.tools, Path(self.m['baseline_work_dir'])]))
        self.check('original-fixture-sources', lambda: all(digest(self.fixture/name) == expected for name, expected in FIXTURE_SOURCES.items()))
        self.check('exact-candidate', lambda: digest(self.m['candidate_binary']) == NEW)
        self.check('unchanged-workload-tools', lambda: all(digest(self.tools/name) == expected for name, expected in TOOLS.items()))
        self.check('namespace-identity', lambda: json.loads(run(['kubectl', 'get', 'namespace', self.m['namespace'], '-o', 'json']).stdout)['metadata']['uid'] == self.m['namespace_uid'])
        self.check('original-reserve', self.reserve)
        self.check('other-business-fixtures', self.no_other_business_fixtures)
        for role in ['dbs', 'hisdbs']:
            self.check(role+'-same-original-processes-and-mounts', lambda role=role: self.live(role, api=True, exact_old=True))
            self.check(role+'-original-controls-and-observe', lambda role=role: self.snapshot_controls(role) == self.m['roles'][role]['controls'] and
                       read_json(self.base/(role+'-business/resource-state/status.json')).get('state') == 'observe')
        self.check('full-prior-acceptance-and-cleanup', self.receipts)
        self.check('exact-shared-program-rehearsal', self.shared_rehearsal)
        ready = all(x['passed'] for x in self.report['checks'].values())
        self.report['phase'] = 'preflight-ready' if ready else 'not-ready'
        return ready

    def save(self):
        require(self.output is not None, 'no owned output directory')
        path = self.output/'report.candidate'
        with path.open('w', encoding='utf-8') as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(json.dumps(self.report, indent=2)+'\n')
            stream.flush();os.fsync(stream.fileno())
        path.replace(self.output/'report.json')
        directory = os.open(self.output, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def invariant(self, api=False):
        self.reserve()
        for name, expected in self.changed_sources.items():
            require(digest(self.fixture/name) == expected, 'fixture source changed outside this stage')
        profile = self.fixture/'io-profile.json'
        if hasattr(self, 'profile_stamp'):
            require(profile.stat().st_mtime_ns == self.profile_stamp, 'existing IO profile mtime changed')
        if hasattr(self, 'recovery'):
            require(all(digest(self.recovery/name) == expected for name, expected in self.reference_digests.items()), 'old recovery reference changed')
        for role in ['dbs', 'hisdbs']:
            self.live(role, api=api)
            events = dict(x.split() for x in Path(self.m['roles'][role]['cgroup'], 'memory.events').read_text().splitlines())
            require(int(events['oom_kill']) == self.oom[role], 'container OOM changed')

    def ex(self, role, *command, timeout=30):
        self.live(role, api=True)
        return run(['kubectl', 'exec', '-n', self.m['namespace'], role+'-business', '-c', role, '--', *command], timeout)

    def cli(self, role, command, reference=False):
        binary = self.reference_inside if reference else '/crgfixture/crg'
        config = self.recovery_inside+'/'+role+'.json' if reference else '/crgfixture/'+role+'/resource.json'
        started = time.time()
        result = self.ex(role, binary, command, '--config', config)
        response = json.loads(result.stdout)
        self.report['operations'].append({'role': role, 'command': command, 'old_reference': reference,
                                          'started_epoch': started, 'ended_epoch': time.time(), 'state': response.get('state')})
        self.save()
        return response

    def wait_writer(self, role, expected_sha, expected_state, seconds=90):
        deadline = time.monotonic()+seconds
        while time.monotonic() < deadline:
            self.invariant()
            actors = self.actors(role)['crg']
            state = read_json(self.base/(role+'-business/resource-state/status.json'))
            if len(actors) == 1 and actors[0]['sha256'] == expected_sha and state.get('state') == expected_state:
                return actors[0]
            time.sleep(.5)
        raise RuntimeError('original helper Agent readiness deadline90s')

    def stopped_and_original(self, role):
        deadline = time.monotonic()+20
        while self.actors(role)['crg'] and time.monotonic() < deadline:
            self.invariant();time.sleep(.1)
        require(not self.actors(role)['crg'] and self.snapshot_controls(role) == self.m['roles'][role]['controls'] and
                read_json(self.base/(role+'-business/resource-state/journal.json'))['mutations'] == {},
                'writer still present or actual originals not restored')

    def atomic_source(self, name, data, mode):
        self.invariant(api=True)
        path = self.fixture/name
        require(digest(path) == self.changed_sources[name], 'atomic source precondition changed')
        temporary = path.with_name(path.name+'.stage-'+uuid.uuid4().hex)
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
            with os.fdopen(fd, 'wb') as stream:
                os.fchmod(stream.fileno(), mode)
                stream.write(data);stream.flush();os.fsync(stream.fileno())
            require(digest(path) == self.changed_sources[name], 'source changed before atomic replacement')
            os.replace(temporary, path)
            self.changed_sources[name] = hashlib.sha256(data).hexdigest()
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if temporary.exists():
                temporary.unlink()

    def verify_database(self, role, native):
        schema = 'crg_soak_'+self.m['source_run_id']
        sql = "SELECT count(*),sum(id),sum(octet_length(payload)),md5(string_agg(md5(payload),'' ORDER BY id)),sum(counter) FROM "+schema+'.fixture'
        client = '/opt/postgresql/pgsql/bin/psql'
        def query(statement):
            command = shlex.join([client, '-XAtw', '-h127.0.0.1', '-p5432', '-U', 'postgres', '-d', 'postgres', '-c', statement])
            return self.ex(role, 'su', '-', 'postgres', '-c', command, timeout=60).stdout.strip()
        require(query('SHOW shared_buffers;') == '8960MB', 'original PG memory parameter changed')
        require(query('SELECT pg_postmaster_start_time();') == native['primary_start_time_final'], 'original PG restarted after baseline')
        values = query(sql).split('|')
        actual = [int(values[0]), int(values[1]), int(values[2]), values[3], int(values[4])]
        require(actual == native['final_checksum'], 'same baseline data no longer matches')

    def backup_private(self):
        for role in ['dbs', 'hisdbs']:
            directory = self.output/('before-'+role)
            directory.mkdir(mode=0o700)
            state = safe_directory(self.base/(role+'-business/resource-state'))
            for path in state.iterdir():
                info = path.lstat()
                require(stat.S_ISREG(info.st_mode) and not path.is_symlink(), 'unexpected original state entry')
                data = bounded(path)
                target = directory/path.name
                with target.open('xb') as stream:
                    os.fchmod(stream.fileno(), 0o600);stream.write(data);stream.flush();os.fsync(stream.fileno())
            require(read_json(directory/'journal.json')['mutations'] == {}, 'backup journal is not empty after disable')
        self.backup_digests = {str(p.relative_to(self.output)): digest(p) for d in self.output.glob('before-*') for p in d.iterdir()}
        self.report['backup_manifest'] = self.backup_digests
        self.save()

    def backout(self):
        self.report['backout'] = {'restored': False}
        self.save();self.invariant(api=True)
        # Known old reference and known compatible three-control journal only.
        for role in self.disabled:
            require(self.cli(role, 'disable', reference=True).get('state') == 'restored', 'old-reference disable failed')
            self.stopped_and_original(role)
        for role in ['dbs', 'hisdbs']:
            name = role+'/resource.json'
            if self.changed_sources[name] != FIXTURE_SOURCES[name]:
                self.atomic_source(name, self.old_configs[role], 0o600)
        if self.changed_sources['crg'] != OLD:
            self.atomic_source('crg', self.old_binary, 0o755)
        for role in self.disabled:
            self.cli(role, 'enable', reference=True)
            self.wait_writer(role, OLD, 'observe')
            require(self.snapshot_controls(role) == self.m['roles'][role]['controls'], 'backout actual originals differ')
        require(all(digest(self.output/name) == expected for name, expected in self.backup_digests.items()), 'private backup changed')
        self.invariant(api=True)
        self.report['backout']['restored'] = True
        self.save()

    def start_campaign(self):
        self.invariant(api=True)
        for role in ['dbs', 'hisdbs']:
            require(self.actors(role)['crg'] == [self.fixed_agent[role]] and self.snapshot_controls(role) == self.expected[role], 'candidate changed before workload launch')
        work = Path('/var/tmp/crg-enforce24h-'+self.m['new_run_id']) if self.m['kind'] == 'formal' else self.output/'enforce600'
        require(not work.exists(), 'new campaign output already exists')
        command = ['python3', str(self.tools/'vendor-soak-campaign.py'), '--namespace', self.m['namespace'],
                   '--fixture-root', str(self.base), '--work-dir', str(work), '--run-id', self.m['new_run_id'],
                   '--source-run-id', self.m['source_run_id'], '--test-phase', 'enforce' if self.m['kind'] == 'formal' else 'smoke',
                   '--seconds', '86400' if self.m['kind'] == 'formal' else '600', '--agent-sha256', NEW, '--cache-sha256', CACHE]
        if self.m['kind'] == 'rehearsal':
            command.append('--smoke-enforce')
        log = (self.output/'campaign.log').open('xb')
        os.fchmod(log.fileno(), 0o600)
        job = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        log.close()
        self.report['campaign'] = {'pid': job.pid, 'entry': str(self.tools/'vendor-soak-campaign.py'),
                                    'work_dir': str(work), 'requested_seconds': 86400 if self.m['kind'] == 'formal' else 600,
                                    'source_run_id': self.m['source_run_id'], 'new_run_id': self.m['new_run_id']}
        self.campaign_job = job
        self.report['campaign']['process'] = process(job.pid)
        self.save()
        return job, work

    def new_native_workers_absent(self):
        entry = '/tmp/crg-soak-load-'+self.m['new_run_id']+'.py'
        return all(not entry_live(int(pid), entry) for role in ['dbs', 'hisdbs']
                   for pid in Path(self.m['roles'][role]['cgroup'], 'cgroup.procs').read_text().splitlines())

    def recover(self, output, manifest_sha256):
        """Explicit guarded recovery after the original campaign is terminal.

        It never imports/deletes a journal, changes a live campaign's budget,
        kills a business/helper process, or creates a replacement helper.
        """
        require(os.environ.get('CRG_VENDOR_STAGE_TEST') == 'disposable-lab-only', 'explicit lab stage marker missing')
        output = Path(output)
        require(output.parent == Path('/var/tmp') and str(output).startswith('/var/tmp/crg-enforce-stage-'), 'private stage output required')
        safe_directory(output)
        import fcntl
        # An existing lock is mandatory: recovery must not initialize a stage.
        fd = os.open(self.base/'.enforce-stage.lock', os.O_RDWR | os.O_NOFOLLOW)
        with os.fdopen(fd, 'r+b') as lock:
            info = os.fstat(lock.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.geteuid(), 'lab maintenance lock owner differs')
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            report = read_json(output/'report.json')
            require(report.get('manifest_sha256') == manifest_sha256 and
                    report.get('stage_source_sha256') == self.report['stage_source_sha256'] and
                    report.get('kind') == self.m['kind'] and report.get('namespace') == self.m['namespace'] and
                    report.get('previous_sha256') == OLD and report.get('candidate_sha256') == NEW and
                    report.get('phase') in ['rehearsal-awaiting-recovery', 'campaign-launch-requested-not-accepted', 'failed'],
                    'recovery receipt is not this exact pending stage')
            require(report.get('disabled_roles') == ['dbs', 'hisdbs'], 'partial preparation needs separate inspection')
            context = report['recovery_context']
            recovery = safe_directory(self.fixture/('.enforce-stage-'+self.m['new_run_id']))
            reference_digests = {'crg-reference': OLD, **{r+'.json': FIXTURE_SOURCES[r+'/resource.json'] for r in ['dbs', 'hisdbs']}}
            require(report.get('recovery_manifest') == reference_digests and
                    all(digest(recovery/name) == expected for name, expected in reference_digests.items()), 'recovery references changed')
            backups = report['backup_manifest']
            require(backups and all(PurePosixPath(name).parts[0] in ['before-dbs', 'before-hisdbs'] and
                    len(PurePosixPath(name).parts) == 2 and '..' not in PurePosixPath(name).parts and
                    digest(output/name) == expected for name, expected in backups.items()), 'private backups changed')
            require(self.new_native_workers_absent(), 'new native workers still live')
            campaign = report.get('campaign')
            if campaign:
                expected_work = Path('/var/tmp/crg-enforce24h-'+self.m['new_run_id']) if self.m['kind'] == 'formal' else output/'enforce600'
                require(campaign['work_dir'] == str(expected_work) and
                        campaign['entry'] == str(self.tools/'vendor-soak-campaign.py') and
                        campaign['new_run_id'] == self.m['new_run_id'] and campaign['source_run_id'] == self.m['source_run_id'] and
                        not entry_live(campaign['pid'], campaign['entry']), 'original campaign still live or identity differs')
                result = read_json(expected_work/'report.json')
                require(result.get('phase') in ['passed', 'failed'] and not result.get('cleanup_errors') and
                        math.isfinite(result.get('ended_epoch', math.inf)) and
                        result.get('agent_sha256') == NEW and result.get('cache_sha256') == CACHE and
                        result.get('campaign_script_sha256') == TOOLS['vendor-soak-campaign.py'] and
                        result.get('worker_sha256') == TOOLS['vendor-soak-load.py'] and
                        result.get('engine_script_sha256') == TOOLS['vendor-engine-smoke.py'] and
                        result.get('source_run_id') == self.m['source_run_id'], 'terminal original campaign cleanup not verified')
                report['campaign_result'] = result
            require(all(safe_directory(p) for p in [self.base, self.fixture, self.tools]), 'private directory check failed')
            require(all(digest(self.tools/name) == expected for name, expected in TOOLS.items()), 'original workload tools changed')
            require(json.loads(run(['kubectl', 'get', 'namespace', self.m['namespace'], '-o', 'json']).stdout)['metadata']['uid'] == self.m['namespace_uid'], 'namespace incarnation changed')
            self.no_other_business_fixtures()
            # Rehydrate only known source/config bytes, never stored journal state.
            self.changed_sources = {name: digest(self.fixture/name) for name in FIXTURE_SOURCES}
            config_sha = hashlib.sha256(json.dumps(candidate_config()).encode()).hexdigest()
            for name, actual in self.changed_sources.items():
                allowed = {FIXTURE_SOURCES[name]}
                if name == 'crg':allowed.add(NEW)
                if name in ['dbs/resource.json', 'hisdbs/resource.json']:allowed.add(config_sha)
                require(actual in allowed, 'current source is not an exact stage source')
            self.recovery = recovery
            self.reference_digests = reference_digests
            self.recovery_inside = '/crgfixture/'+recovery.name
            self.reference_inside = self.recovery_inside+'/crg-reference'
            self.old_binary = bounded(recovery/'crg-reference', 32*1024**2)
            self.old_configs = {r: bounded(recovery/(r+'.json')) for r in ['dbs', 'hisdbs']}
            self.oom = context['oom_kills']
            self.profile_stamp = context['profile_mtime_ns']
            self.backup_digests = backups
            self.disabled = ['dbs', 'hisdbs']
            self.invariant(api=True)
            # No CLI/source/control writes before all recovery gates pass.
            self.report = report
            self.output = output
            self.backout()
            if self.m['kind'] == 'rehearsal':
                require(accepted_campaign(self.report.get('campaign_result', {}), 600, 'smoke', agent_sha256=NEW), 'recovery succeeded; enforced600s evidence failed')
                self.report['phase'] = 'rehearsal-passed-restored'
            else:
                self.report['phase'] = 'campaign-terminal-restored'
            self.save()

    def perform(self, output):
        require(self.preflight(), 'read-only preflight not ready; no stage performed')
        require(os.environ.get('CRG_VENDOR_STAGE_TEST') == 'disposable-lab-only', 'explicit lab stage marker missing')
        output = Path(output)
        require(str(output).startswith('/var/tmp/crg-enforce-stage-') and output.parent == Path('/var/tmp') and
                output.resolve() == output and not output.exists(), 'fresh private stage output required')
        import fcntl
        # Lock and all writes occur only after the complete read-only gate.
        fd = os.open(self.base/'.enforce-stage.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'r+b') as lock:
            info = os.fstat(lock.fileno())
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.geteuid(), 'lab maintenance lock owner differs')
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            require(self.preflight(), 'preconditions changed after maintenance lock')
            output.mkdir(mode=0o700)
            self.output = output
            self.report.update(phase='preparing-stage', namespace=self.m['namespace'], previous_sha256=OLD, candidate_sha256=NEW)
            self.save()
            self.old_binary = bounded(self.fixture/'crg', 32*1024**2)
            self.old_configs = {r: bounded(self.fixture/r/'resource.json') for r in ['dbs', 'hisdbs']}
            self.profile_stamp = (self.fixture/'io-profile.json').stat().st_mtime_ns
            baseline = read_json(Path(self.m['baseline_work_dir'])/'report.json')
            for role in ['dbs', 'hisdbs']:
                self.verify_database(role, baseline['roles'][role]['workload'])
                self.oom[role] = int(dict(x.split() for x in Path(self.m['roles'][role]['cgroup'], 'memory.events').read_text().splitlines())['oom_kill'])
            recovery = self.fixture/('.enforce-stage-'+self.m['new_run_id'])
            recovery.mkdir(mode=0o700)
            self.recovery_inside = '/crgfixture/'+recovery.name
            self.reference_inside = self.recovery_inside+'/crg-reference'
            for name, data, mode in [('crg-reference', self.old_binary, 0o755)]+[(r+'.json', self.old_configs[r], 0o600) for r in ['dbs', 'hisdbs']]:
                with (recovery/name).open('xb') as stream:
                    os.fchmod(stream.fileno(), mode);stream.write(data);stream.flush();os.fsync(stream.fileno())
            self.reference_digests = {p.name: digest(p) for p in recovery.iterdir()}
            require(self.reference_digests == {'crg-reference': OLD, **{r+'.json': FIXTURE_SOURCES[r+'/resource.json'] for r in ['dbs', 'hisdbs']}}, 'recovery copy digest differs')
            self.recovery = recovery
            self.report['recovery_manifest'] = self.reference_digests
            self.report['recovery_context'] = {'oom_kills': self.oom, 'profile_mtime_ns': self.profile_stamp}
            for directory in [recovery, self.fixture]:
                handle = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(handle)
                finally:
                    os.close(handle)
            self.backup_digests = {}
            try:
                for role in ['dbs', 'hisdbs']:
                    self.disabled.append(role)  # Includes an uncertain/failed disable for guarded recovery.
                    self.report['disabled_roles'] = list(self.disabled);self.save()
                    require(self.cli(role, 'disable', reference=True).get('state') == 'restored', 'original disable failed')
                    self.stopped_and_original(role)
                self.backup_private()
                for role in ['dbs', 'hisdbs']:
                    self.atomic_source(role+'/resource.json', json.dumps(candidate_config()).encode(), 0o600)
                self.atomic_source('crg', bounded(self.m['candidate_binary'], 32*1024**2), 0o755)
                for role in ['dbs', 'hisdbs']:
                    self.cli(role, 'enable')
                    self.fixed_agent[role] = self.wait_writer(role, NEW, 'managed')
                    device = (self.base/(role+'-business/postgresql')).stat().st_dev
                    self.expected[role] = {**self.m['roles'][role]['controls'], 'cpu.max': '720000 100000', 'memory.max': '20001980416',
                                           'io.max': str(os.major(device))+':'+str(os.minor(device))+' rbps=67108864 wbps=67108864 riops=4096 wiops=4096'}
                    state = read_json(self.base/(role+'-business/resource-state/status.json'))
                    require(set(x['file'] for x in state['items']) == {'cpu.max', 'memory.max', 'io.max'} and all(x['state'] == 'applied' for x in state['items']) and not state.get('automatic_io'), 'candidate three-control status differs')
                    logs = list((self.base/(role+'-business/resource-state/logs')).glob('crg-*.log'))
                    require(logs and all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in logs), 'persistent daily0600 logs missing')
                    events = [json.loads(line) for p in logs for line in bounded(p).decode().splitlines()]
                    require(any(x.get('event') == 'cgroup_detected' and x.get('fields', {}).get('check', {}).get('cgroup_version') == 'v2' for x in events), 'v2 event missing')
                def hold_sample():
                    self.invariant()
                    for role in ['dbs', 'hisdbs']:
                        require(self.actors(role)['crg'] == [self.fixed_agent[role]] and self.snapshot_controls(role) == self.expected[role], 'candidate hold identity/control changed')
                elapsed, observations = observe_for(120, 2, hold_sample)
                self.report.update(candidate_hold_seconds=elapsed, candidate_hold_observations=observations)
                require(observations >= 59, 'candidate observation coverage insufficient')
                require(all(digest(self.output/name) == expected for name, expected in self.backup_digests.items()), 'private backup changed')
                self.report['phase'] = 'candidate-held-ready';self.save()
                job, work = self.start_campaign()
                if self.m['kind'] == 'formal':
                    self.report['phase'] = 'campaign-launch-requested-not-accepted';self.save()
                    return
                # Rehearsal owns this foreground client; the original campaign
                # retains its own fixed deadlines and worker/engine cleanup.
                while job.poll() is None:
                    self.invariant()
                    time.sleep(2)
                result = read_json(work/'report.json')
                self.report['campaign_result'] = result
                accepted = job.returncode == 0 and accepted_campaign(result, 600, 'smoke', agent_sha256=NEW)
                require(not result.get('cleanup_errors') and self.new_native_workers_absent(), 'campaign temporary cleanup still pending')
                require(accepted, 'shared-program enforced600s campaign failed')
                self.report['phase'] = 'rehearsal-awaiting-recovery';self.save()
            except BaseException as error:
                self.report.update(phase='failed', failure_class=type(error).__name__)
                if type(error) is RuntimeError:self.report['failure'] = str(error)
                # Do not relax controls or interrupt a still-live campaign.
                # Its original worker/engine cleanup must first become terminal.
                if self.report.get('backout', {}).get('restored'):
                    pass
                elif getattr(self, 'campaign_job', None) is None or (self.campaign_job.poll() is not None and self.new_native_workers_absent() and not self.report.get('campaign_result', {}).get('cleanup_errors')):
                    try:
                        self.backout()
                    except Exception as recovery_error:
                        self.report['recovery_failure_class'] = type(recovery_error).__name__
                else:
                    self.report['recovery_deferred_live_campaign'] = True
                self.save()
                raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--execute', action='store_true', help='lab only; all unchanged acceptance gates must first pass')
    action.add_argument('--recover', action='store_true', help='lab only; requires exact private recovery receipt and terminal original campaign')
    parser.add_argument('--output', type=Path, help='fresh private output; required for execute')
    args = parser.parse_args()
    require(platform.system() == 'Linux' and os.geteuid() == 0, 'Linux root required for private /proc inventory')
    require(re.fullmatch(r'[0-9a-f]{64}', args.manifest_sha256) is not None and digest(args.manifest) == args.manifest_sha256, 'pinned manifest digest differs')
    stage = Stage(read_json(args.manifest))
    stage.report['manifest_sha256'] = args.manifest_sha256
    if args.execute or args.recover:
        require(args.output is not None, 'execute requires a fresh output directory')
        try:
            if args.recover:
                stage.recover(args.output, args.manifest_sha256)
            else:
                stage.perform(args.output)
        except BaseException as error:
            stage.report['failure_class'] = type(error).__name__
            if stage.output is None:
                stage.report['refused_before_stage_writes'] = True
            else:
                stage.report['phase'] = 'failed'
                stage.save()
            print(json.dumps(stage.report, indent=2))
            return 2 if stage.output is None and stage.report['phase'] == 'not-ready' else 1
        print(json.dumps(stage.report, indent=2))
        return 0
    ready = stage.preflight()
    print(json.dumps(stage.report, indent=2))
    return 0 if ready else 2


if __name__ == '__main__':
    raise SystemExit(main())
