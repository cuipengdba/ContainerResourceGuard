#!/usr/bin/env python3
"""Disposable shared-file rehearsal of the lab stage fixture, not a daemon.

Reads the original baseline sources only. Creates fresh isolated clones with
one shared program directory and separate data/state/cache for each role.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid

SOURCE = Path('/var/tmp/crg-business-20261110')
BASE = Path('/var/tmp/crg-stage-rehearsal-20-20261110')
OUTPUT = Path('/var/tmp/crg-enforce-stage-20-20261110')
NAMESPACE = 'crg-vendor-lab-stage20-20261110'
SOURCE_RUN = '202611101501'
NEW_RUN = '202611101502'


def main():
    global BASE, OUTPUT, NAMESPACE, SOURCE_RUN, NEW_RUN
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage-sha256', required=True)
    parser.add_argument('--attempt', type=int, choices=range(20, 100), default=20)
    args = parser.parse_args()
    if args.attempt != 20:
        BASE = Path('/var/tmp/crg-stage-rehearsal-'+str(args.attempt)+'-20261110')
        OUTPUT = Path('/var/tmp/crg-enforce-stage-'+str(args.attempt)+'-20261110')
        NAMESPACE = 'crg-vendor-lab-stage'+str(args.attempt)+'-20261110'
        SOURCE_RUN = '20261110'+str(args.attempt)+'01'
        NEW_RUN = '20261110'+str(args.attempt)+'02'
    tools = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location('stage_fixture', tools/'vendor-enforce-stage.py')
    stage = importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)
    stage.require(os.geteuid() == 0 and os.environ.get('CRG_VENDOR_STAGE_TEST') == 'disposable-lab-only', 'explicit private Linux root lab marker required')
    stage.require(stage.digest(tools/'vendor-enforce-stage.py') == args.stage_sha256, 'pinned stage source differs')
    stage.require(not BASE.exists() and not OUTPUT.exists(), 'fresh rehearsal paths required')
    stage.require(not stage.run(['kubectl', 'get', 'namespace', NAMESPACE, '--ignore-not-found', '-o', 'json']).stdout.strip(), 'private namespace already exists')
    stage.require(all(stage.digest(SOURCE/'fixture'/name) == expected for name, expected in stage.FIXTURE_SOURCES.items()), 'original fixture sources changed')
    stage.require(all(stage.digest(tools/name) == expected for name, expected in stage.TOOLS.items()), 'original campaign sources changed')
    BASE.mkdir(mode=0o700)
    report = {'phase': 'preparing', 'scope': 'two disposable original-image clones; shared program, separate per-container Agents',
              'launcher_source_sha256': stage.digest(Path(__file__)), 'stage_source_sha256': args.stage_sha256,
              'roles': {}, 'tests': []}
    created = False
    active = None
    groups = {}
    original = None

    def save():
        target = BASE/'report.candidate'
        target.write_text(json.dumps(report, indent=2)+'\n');target.chmod(0o600);target.replace(BASE/'report.json')

    def record(name, passed):
        report['tests'].append({'name': name, 'passed': bool(passed)});save()
        stage.require(passed, name)

    def reserve(minimum=8):
        memory = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
        stage.require(memory >= minimum*1024**3 and shutil.disk_usage(BASE).free >= 20*1024**3, 'original host reserve threshold')

    def create(value):
        r = subprocess.run(['kubectl', 'create', '-f', '-'], input=json.dumps(value), capture_output=True, text=True, timeout=30)
        stage.require(r.returncode == 0, 'owned fixture creation failed')

    def ex(role, *command, timeout=30):
        return stage.run(['kubectl', 'exec', '-n', NAMESPACE, role+'-business', '-c', role, '--', *command], timeout)

    def formal_snapshot():
        # The existing baseline is read only, even while our own clones run.
        result = {'sources': {name: stage.digest(SOURCE/'fixture'/name) for name in stage.FIXTURE_SOURCES}, 'roles': {}}
        for role in ['dbs', 'hisdbs']:
            pod = json.loads(stage.run(['kubectl', 'get', 'pod', '-n', stage.FORMAL_NAMESPACE, role+'-business', '-o', 'json']).stdout)
            s = next(x for x in pod['status']['containerStatuses'] if x['name'] == role)
            cid = s['containerID'].split('://')[1]
            pid = json.loads(stage.run(['crictl', 'inspect', cid]).stdout)['info']['pid']
            membership = Path('/proc', str(pid), 'cgroup').read_text()
            group = Path('/sys/fs/cgroup'+membership.strip()[3:])
            result['roles'][role] = {'pod_uid': pod['metadata']['uid'], 'container_id': cid, 'restart_count': s['restartCount'],
                                     'main': stage.process(pid), 'membership': membership,
                                     'controls': {name: (group/name).read_text().strip() for name in stage.CONTROLS}}
        return result

    def wait_child(command, log_name, phase):
        nonlocal active
        log = (BASE/log_name).open('xb');os.fchmod(log.fileno(), 0o600)
        active = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        report.update(phase=phase, active_child={'pid': active.pid, 'entry': command[1], 'identity': stage.process(active.pid)})
        save();next_observe = time.monotonic()
        while active.poll() is None:
            reserve()
            if time.monotonic() >= next_observe:
                stage.require(formal_snapshot() == original, 'original formal baseline identity/source/controls changed')
                next_observe = time.monotonic()+60
            time.sleep(2)
        log.close()
        return active

    save()
    try:
        reserve(28);original = formal_snapshot()
        fixture = BASE/'fixture';fixture.mkdir(mode=0o700)
        for name in stage.FIXTURE_SOURCES:
            target = fixture/name;target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            shutil.copyfile(SOURCE/'fixture'/name, target)
            target.chmod(0o755 if name in ['crg', 'containercacheguard'] else 0o600)
        record('copied-shared-sources-exactly', all(stage.digest(fixture/name) == expected for name, expected in stage.FIXTURE_SOURCES.items()))
        profile_stamp = (fixture/'io-profile.json').stat().st_mtime_ns
        gates = BASE/'gates';gates.mkdir(mode=0o700)
        aux = BASE/'aux';aux.mkdir(mode=0o700);shutil.copyfile('/usr/bin/etcd', aux/'etcd');(aux/'etcd').chmod(0o755)
        images = stage.read_json(SOURCE/'vendor-import.json')['images']
        create({'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': NAMESPACE, 'labels': {'managed-by': 'crg-vendor-test'}}});created = True
        create({'apiVersion': 'networking.k8s.io/v1', 'kind': 'NetworkPolicy', 'metadata': {'name': 'deny-all', 'namespace': NAMESPACE},
                'spec': {'podSelector': {}, 'policyTypes': ['Ingress', 'Egress']}})
        for role in ['dbs', 'hisdbs']:
            reserve(28)
            folder = BASE/(role+'-business');folder.mkdir(mode=0o700)
            for name in ['postgresql', 'resource-state', 'cache-state', 'etcd']:(folder/name).mkdir(mode=0o700)
            secret = uuid.uuid4().hex
            env = stage.read_json(SOURCE/'fixture'/role/'env.json')
            env.update(MY_POD_NAMESPACE=NAMESPACE, MY_POD_NAME=role+'-stage20-0', PGPASSWORD=secret,
                       CRG_BIN='/crgfixture/crg', CRG_CONFIG='/crgfixture/'+role+'/resource.json',
                       CRG_HELPER_SCRIPT='/crgfixture/optional-agent.sh', CCG_BIN='/crgfixture/containercacheguard',
                       CCG_CONFIG='/crgfixture/'+role+'/cache.json', YSP_PRODUCT_TYPE='PUC-DBS')
            pg = re.sub(r'(?m)^(\s+password:).*$', r'\1 '+secret, (SOURCE/'fixture'/role/'postgres.yml').read_text())
            (folder/'postgres.yml').write_text(pg);(folder/'postgres.yml').chmod(0o600)
            volumes = [];mounts = []
            for name, host, inside, ro, kind in [
                    ('fixture', fixture, '/crgfixture', True, 'Directory'),
                    ('postgresql', folder/'postgresql', '/opt/postgresql', False, 'Directory'),
                    ('resource-state', folder/'resource-state', '/crgstate', False, 'Directory'),
                    ('cache-state', folder/'cache-state', '/ccgstate', False, 'Directory'),
                    ('pgconfig', folder/'postgres.yml', '/home/config/postgres.yml', True, 'File'),
                    ('gates', gates, '/network-gates', True, 'Directory')]:
                volumes.append({'name': name, 'hostPath': {'path': str(host), 'type': kind}})
                mounts.append({'name': name, 'mountPath': inside, 'readOnly': ro})
            volumes += [{'name': 'aux', 'hostPath': {'path': str(aux), 'type': 'Directory'}},
                        {'name': 'etcd', 'hostPath': {'path': str(folder/'etcd'), 'type': 'Directory'}}]
            start = 'i=0; while [ ! -f "/network-gates/$CRG_TEST_POD_UID" ]; do i=$((i+1)); [ "$i" -lt 120 ] || exit 92; sleep 1; done; exec /bin/bash /crgfixture/'+role+'/supervisor.sh'
            pod = {'apiVersion': 'v1', 'kind': 'Pod', 'metadata': {'name': role+'-business', 'namespace': NAMESPACE, 'labels': {'managed-by': 'crg-vendor-test'}},
                   'spec': {'automountServiceAccountToken': False, 'enableServiceLinks': False, 'restartPolicy': 'Never', 'terminationGracePeriodSeconds': 30,
                            'containers': [{'name': role, 'image': images[role]['tag'], 'imagePullPolicy': 'Never', 'command': ['/bin/bash', '-c', start],
                                            'env': [{'name': k, 'value': v} for k, v in env.items()]+[{'name': 'CRG_TEST_POD_UID', 'valueFrom': {'fieldRef': {'fieldPath': 'metadata.uid'}}}],
                                            'securityContext': {'privileged': True}, 'resources': {'requests': {'cpu': '100m', 'memory': '256Mi'}, 'limits': {'cpu': '8', 'memory': '20Gi'}}, 'volumeMounts': mounts},
                                           {'name': 'isolated-dcs', 'image': images[role]['tag'], 'imagePullPolicy': 'Never',
                                            'command': ['/aux/etcd', '--name', 'isolated', '--data-dir', '/isolated-etcd', '--listen-client-urls', 'http://127.0.0.1:2379', '--advertise-client-urls', 'http://127.0.0.1:2379', '--listen-peer-urls', 'http://127.0.0.1:2380', '--initial-advertise-peer-urls', 'http://127.0.0.1:2380', '--initial-cluster', 'isolated=http://127.0.0.1:2380'],
                                            'resources': {'requests': {'cpu': '10m', 'memory': '32Mi'}, 'limits': {'cpu': '1', 'memory': '256Mi'}},
                                            'volumeMounts': [{'name': 'aux', 'mountPath': '/aux', 'readOnly': True}, {'name': 'etcd', 'mountPath': '/isolated-etcd'}]}], 'volumes': volumes}}
            path = folder/'pod.json';path.write_text(json.dumps(pod));path.chmod(0o600)
            create(pod)
            stage.run(['kubectl', 'wait', '-n', NAMESPACE, '--for=condition=Ready', 'pod/'+role+'-business', '--timeout=90s'], 100)
            meta = json.loads(stage.run(['kubectl', 'get', 'pod', '-n', NAMESPACE, role+'-business', '-o', 'json']).stdout)
            container = next(x for x in meta['status']['containerStatuses'] if x['name'] == role)
            cid = container['containerID'].split('://')[1]
            pid = json.loads(stage.run(['crictl', 'inspect', cid]).stdout)['info']['pid']
            membership = Path('/proc', str(pid), 'cgroup').read_text()
            stage.require(len(membership.splitlines()) == 1 and membership.startswith('0::/'), 'pure v2 fixture required')
            group = Path('/sys/fs/cgroup'+membership.strip()[3:]);groups[role] = group
            stage.require(group.name == 'cri-containerd-'+cid+'.scope' and
                          not any(meta['spec'].get(k) for k in ['hostPID', 'hostIPC', 'hostNetwork']) and
                          all(Path('/proc', str(pid), 'ns', k).stat().st_ino != Path('/proc/1/ns', k).stat().st_ino for k in ['pid', 'mnt', 'net']), 'fresh isolated identity required')
            controls = {name: (group/name).read_text().strip() for name in stage.CONTROLS}
            stage.run(['nsenter', '-t', str(pid), '-n', '--', 'ip', 'link', 'set', 'dev', 'eth0', 'down'])
            stage.require('state DOWN' in stage.run(['nsenter', '-t', str(pid), '-n', '--', 'ip', '-o', 'link', 'show', 'dev', 'eth0']).stdout, 'network isolation failed')
            started = time.monotonic();(gates/meta['metadata']['uid']).write_text('isolated\n')
            status = folder/'resource-state/status.json';cache = folder/'cache-state/status.json'
            while time.monotonic()-started < 300:
                reserve()
                try:
                    ex(role, 'su', '-', 'postgres', '-c', '/opt/postgresql/pgsql/bin/pg_isready -h127.0.0.1 -p5432 -t2', timeout=min(15, max(.01, 300-(time.monotonic()-started))))
                    api = "import urllib2,json;r=urllib2.urlopen(urllib2.Request('http://127.0.0.1:8090/test',data='{}',headers={'Content-Type':'application/json'}),timeout=3);assert r.getcode()==200;assert json.loads(r.read(1024))['Result']=='000'"
                    ex(role, 'python', '-c', api, timeout=min(10, max(.01, 300-(time.monotonic()-started))))
                    if status.exists() and cache.exists() and stage.read_json(status).get('state') == 'observe' and stage.read_json(cache).get('action') == 'enforce' and time.monotonic()-started < 300:break
                except (RuntimeError, subprocess.TimeoutExpired):pass
                time.sleep(2)
            else:raise RuntimeError('original startup deadline300s')
            row = {'pod_uid': meta['metadata']['uid'], 'container_id': cid, 'image_id': container['imageID'], 'main': stage.process(pid),
                   'membership': membership, 'cgroup': str(group), 'controls': controls}
            partial = {'roles': {role: row}}
            probe = object.__new__(stage.Stage);probe.m = partial
            row['actors'] = probe.actors(role)
            stage.require(len(row['actors']['crg']) == len(row['actors']['containercacheguard']) == 1, 'exactly one Agent/cache required')
            row['helper'] = stage.process(row['actors']['crg'][0]['ppid'])
            report['roles'][role] = row
            record(role+'-original-startup-and-eight-controls', {name: (group/name).read_text().strip() for name in stage.CONTROLS} == controls)
        baseline = BASE/'baseline'
        command = ['python3', str(tools/'vendor-soak-campaign.py'), '--namespace', NAMESPACE, '--fixture-root', str(BASE), '--work-dir', str(baseline),
                   '--run-id', SOURCE_RUN, '--test-phase', 'smoke', '--seconds', '600', '--agent-sha256', stage.OLD, '--cache-sha256', stage.CACHE]
        prior = wait_child(command, 'baseline.log', 'old-observe600')
        record('both-full-original-baseline600', prior.returncode == 0 and stage.accepted_campaign(stage.read_json(baseline/'report.json'), 600, 'smoke'))
        namespace_uid = json.loads(stage.run(['kubectl', 'get', 'namespace', NAMESPACE, '-o', 'json']).stdout)['metadata']['uid']
        manifest = {'schema': 'crg-vendor-enforce-stage-v1', 'kind': 'rehearsal', 'namespace': NAMESPACE, 'namespace_uid': namespace_uid,
                    'fixture_root': str(BASE), 'baseline_work_dir': str(baseline), 'tools_root': str(tools),
                    'candidate_binary': '/var/tmp/crg-r30-20261110/binaries/v10/crg-linux-amd64',
                    'source_run_id': SOURCE_RUN, 'new_run_id': NEW_RUN, 'fixture_sources': stage.FIXTURE_SOURCES,
                    'baseline_coordinator': {'pid': prior.pid, 'entry': command[1]}, 'roles': report['roles']}
        stage.validate_manifest(manifest)
        manifest_path = BASE/'manifest.json';manifest_path.write_text(json.dumps(manifest, indent=2)+'\n');manifest_path.chmod(0o600)
        command = ['python3', str(tools/'vendor-enforce-stage.py'), '--manifest', str(manifest_path), '--manifest-sha256', stage.digest(manifest_path)]
        dry = wait_child(command, 'preflight.log', 'stage-preflight')
        record('stage-full-preflight-before-writes', dry.returncode == 0)
        switched = wait_child(command+['--execute', '--output', str(OUTPUT)], 'stage.log', 'candidate-hold-and-enforce600')
        record('candidate-complete-shared-program-stage', switched.returncode == 0 and stage.read_json(OUTPUT/'report.json').get('phase') == 'rehearsal-awaiting-recovery')
        restored = wait_child(command+['--recover', '--output', str(OUTPUT)], 'recovery.log', 'explicit-terminal-recovery')
        record('explicit-old-reference-recovery', restored.returncode == 0 and stage.read_json(OUTPUT/'report.json').get('phase') == 'rehearsal-passed-restored')
        record('shared-original-profile-bytes-and-mtime', stage.digest(fixture/'io-profile.json') == stage.FIXTURE_SOURCES['io-profile.json'] and (fixture/'io-profile.json').stat().st_mtime_ns == profile_stamp)
        record('original-formal-baseline-unchanged', formal_snapshot() == original)
        report['phase'] = 'passed';save()
    except BaseException as error:
        report.update(phase='failed', failure_class=type(error).__name__)
        if type(error) is RuntimeError:report['failure'] = str(error)
        save()
    finally:
        # Never delete a fixture while its original child/campaign still runs.
        # Preserve the private handle/failed receipts for explicit follow-up.
        pending = False
        if OUTPUT.joinpath('report.json').exists():
            result = stage.read_json(OUTPUT/'report.json')
            campaign = result.get('campaign')
            pending = bool(campaign and (stage.entry_live(campaign['pid'], campaign['entry']) or
                           result.get('campaign_result', {}).get('cleanup_errors')))
        if active is not None and active.poll() is None or pending:
            report['cleanup_deferred_live_child'] = True
        elif created:
            cleanup = {'pods': {}, 'namespace_absent': False}
            try:
                meta = json.loads(stage.run(['kubectl', 'get', 'namespace', NAMESPACE, '-o', 'json']).stdout)
                stage.require(meta['metadata'].get('labels', {}).get('managed-by') == 'crg-vendor-test', 'namespace cleanup owner differs')
                for role in ['dbs', 'hisdbs']:
                    raw = stage.run(['kubectl', 'get', 'pod', '-n', NAMESPACE, role+'-business', '--ignore-not-found', '-o', 'json']).stdout
                    if raw:
                        pod = json.loads(raw)
                        stage.require(pod['metadata'].get('labels', {}).get('managed-by') == 'crg-vendor-test', 'Pod cleanup owner differs')
                        stage.run(['kubectl', 'delete', 'pod', '-n', NAMESPACE, role+'-business', '--wait=true', '--timeout=120s'], 130)
                    absent = not stage.run(['kubectl', 'get', 'pod', '-n', NAMESPACE, role+'-business', '--ignore-not-found', '-o', 'json']).stdout.strip()
                    deadline = time.monotonic()+30
                    while role in groups and groups[role].exists() and time.monotonic() < deadline:time.sleep(.5)
                    cleanup['pods'][role] = {'pod_absent': absent, 'cgroup_absent': role in groups and not groups[role].exists()}
                    stage.require(all(cleanup['pods'][role].values()), 'own Pod/cgroup cleanup incomplete')
                stage.run(['kubectl', 'delete', 'namespace', NAMESPACE, '--wait=true', '--timeout=150s'], 160)
                cleanup['namespace_absent'] = not stage.run(['kubectl', 'get', 'namespace', NAMESPACE, '--ignore-not-found', '-o', 'json']).stdout.strip()
                stage.require(cleanup['namespace_absent'], 'own namespace cleanup incomplete')
            except Exception as error:
                cleanup['failure_class'] = type(error).__name__;report['phase'] = 'failed'
            report['fixture_cleanup'] = cleanup
            if OUTPUT.joinpath('report.json').exists():
                result = stage.read_json(OUTPUT/'report.json');result['fixture_cleanup'] = cleanup
                result['rehearsal_launcher_sha256'] = report['launcher_source_sha256']
                target = OUTPUT/'report.cleanup';target.write_text(json.dumps(result, indent=2)+'\n');target.chmod(0o600);target.replace(OUTPUT/'report.json')
        save()
    print(json.dumps({'phase': report['phase'], 'checks': len(report['tests']), 'cleanup': report.get('fixture_cleanup')}))
    return 0 if report['phase'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
