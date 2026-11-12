#!/usr/bin/env python3
"""Explicit disposable Linux qualification; no database startup or cgroup writes.

Only the supplied frozen plan, a private output directory, and a new labelled
namespace are owned. Source business Pods are read for image identity only.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time


def need(value, reason):
    if not value:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(pid):
    fields = Path('/proc', str(pid), 'stat').read_bytes().rsplit(b')', 1)[1].split()
    return {'pid': pid, 'start_ticks': int(fields[19]), 'state': fields[0].decode()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    raw = Path(args.plan).read_bytes()
    need(len(raw) < 32768 and sha(raw) == args.plan_sha256, 'FROZEN_PLAN')
    plan = json.loads(raw)
    need(plan['schema'] == 'crg-proc-read-error-runtime-plan-v1', 'PLAN_SCHEMA')
    if not args.execute:
        print(json.dumps({'phase': 'inert', 'plan_sha256': sha(raw)}))
        return 0
    need(sys.platform == 'linux' and os.geteuid() == 0 and
         os.environ.get('CRG_PROC_ERROR_RUNTIME') == 'authorized-disposable-test-node-only', 'EXPLICIT_LAB_ONLY')
    ns = plan['namespace']
    need(re.fullmatch(r'crg-vendor-lab-procerr[0-9]+-[0-9]{8}', ns), 'OWN_NAMESPACE')
    source_ns = plan['source_namespace']
    need(re.fullmatch(r'crg-vendor-lab-acceptance[0-9]+-[0-9]{8}', source_ns), 'SOURCE_DISPOSABLE_NAMESPACE')
    root = Path(plan['output_directory'])
    tools = Path(plan['tool_directory'])
    for path, kind in [(root, 'results'), (tools, 'tools')]:
        need(re.fullmatch(r'/var/tmp/crg-procerr[0-9]+-'+kind+r'-[0-9]{8}', str(path)) and path.resolve() == path, 'PRIVATE_PATH')
    need(not root.exists() and tools.is_dir() and not tools.is_symlink(), 'NEW_PRIVATE_RESULTS')
    need(plan['checks_per_runtime'] == 24 and plan['roles'] == ['dbs', 'hisdbs'] and
         plan['run_as'] == {'uid': 999, 'gid': 998}, 'FIXED_SCOPE')
    files = plan['source_sha256']
    need(set(files) == {'vendor-proc-read-error.py', 'vendor-proc-read-error-checks.py',
                        'vendor-proc-read-error-runtime.py'}, 'EXACT_SOURCE_SET')
    for filename, digest in files.items():
        path = tools/filename
        need(not path.is_symlink() and sha(path.read_bytes()) == digest, 'FROZEN_SOURCE:'+filename)
    need(Path(__file__).resolve() == tools/'vendor-proc-read-error-runtime.py', 'EXACT_EXECUTOR')
    os.umask(0o077)
    root.mkdir(mode=0o700)
    report = {'schema': 'crg-proc-read-error-runtime-v1', 'phase': 'running',
              'plan_sha256': sha(raw), 'source_sha256': files, 'roles': {},
              'started_node_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'kernel_release': os.uname().release,
              'scope': 'host Python3 and two native vendor Python2 images; own-process proc reads only; no business or historic errno proof',
              'business_DB_commands_or_business_signals_or_explicit_cgroup_writes': 0, 'namespace': ns}
    namespace_uid = None

    def save():
        candidate = root/'report.candidate'
        candidate.write_text(json.dumps(report, indent=2)+'\n')
        candidate.chmod(0o600)
        candidate.replace(root/'report.json')

    def run(argv, data=None, timeout=30, checked=True):
        result = subprocess.run(argv, input=data, capture_output=True, text=True, timeout=timeout)
        need(len(result.stdout) < 2*1024*1024 and len(result.stderr) < 65536, 'COMMAND_OUTPUT_BOUND')
        if checked:
            need(result.returncode == 0, 'COMMAND_FAILED:'+argv[0])
        return result

    def get(kind, name, namespace=ns):
        argv = ['kubectl', 'get', kind, name, '--ignore-not-found', '-o', 'json']
        if kind != 'namespace':
            argv += ['-n', namespace]
        value = run(argv)
        return json.loads(value.stdout) if value.stdout.strip() else None

    def create(value):
        run(['kubectl', 'create', '-f', '-'], data=json.dumps(value))

    def stop(_signum, _frame):
        raise ValueError('QUALIFICATION_DEADLINE')

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGALRM, stop)
    signal.alarm(plan['whole_deadline_seconds'])
    try:
        need(plan['whole_deadline_seconds'] == 240 and plan['pod_active_deadline_seconds'] == 180, 'FROZEN_DEADLINES')
        need(get('namespace', ns) is None, 'NAMESPACE_ABSENT_BEFORE')
        create({'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': ns,
                'labels': {'managed-by': 'crg-vendor-test', 'crg-purpose': 'proc-error-qualification'}}})
        namespace_uid = get('namespace', ns)['metadata']['uid']
        report['namespace_uid'] = namespace_uid
        save()
        create({'apiVersion': 'networking.k8s.io/v1', 'kind': 'NetworkPolicy', 'metadata': {'name': 'deny-all', 'namespace': ns},
                'spec': {'podSelector': {}, 'policyTypes': ['Ingress', 'Egress']}})
        data = {name: (tools/name).read_text() for name in ['vendor-proc-read-error.py', 'vendor-proc-read-error-checks.py']}
        create({'apiVersion': 'v1', 'kind': 'ConfigMap', 'metadata': {'name': 'frozen-proc-error', 'namespace': ns}, 'data': data})
        env = dict(os.environ, CRG_PROC_ERROR_CHECKS='authorized-disposable-readonly-only', PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run([sys.executable, str(tools/'vendor-proc-read-error-checks.py'), '--work-dir',
                                str(root/'host-checks'), '--helper-sha256', files['vendor-proc-read-error.py']],
                               env=env, capture_output=True, text=True, timeout=20)
        value = json.loads((root/'host-checks/result.json').read_bytes())
        report['host'] = {'exit': result.returncode, 'result': value}
        save()
        need(result.returncode == 0 and value['phase'] == 'passed' and len(value['checks']) == 24 and
             value['python'].startswith('3.') and value['own_identity']['euid'] == 0, 'HOST_CHECKS')
        for role in plan['roles']:
            original = get('pod', role+'-business', source_ns)
            need(original is not None and original['metadata']['labels'].get('managed-by') == 'crg-vendor-test', 'SOURCE_POD_LABEL')
            source_container = next(c for c in original['spec']['containers'] if c['name'] == role)
            source_status = next(c for c in original['status']['containerStatuses'] if c['name'] == role)
            image_digest = re.search(r'sha256:([0-9a-f]{64})$', source_status['imageID'])
            need(image_digest is not None, 'SOURCE_IMAGE_DIGEST')
            item = {'source_pod_uid': original['metadata']['uid'],
                    'source_image_id_sha256': sha(source_status['imageID'].encode()),
                    'source_image_content_digest': image_digest.group(0)}
            report['roles'][role] = item
            name = role+'-proc-error'
            obj = {'apiVersion': 'v1', 'kind': 'Pod', 'metadata': {'name': name, 'namespace': ns,
                   'labels': {'managed-by': 'crg-vendor-test', 'crg-purpose': 'proc-error-qualification'}},
                   'spec': {'nodeName': original['spec']['nodeName'], 'restartPolicy': 'Never',
                            'automountServiceAccountToken': False, 'activeDeadlineSeconds': 180,
                            'securityContext': {'runAsUser': 999, 'runAsGroup': 998, 'fsGroup': 998, 'runAsNonRoot': True},
                            'containers': [{'name': role, 'image': source_container['image'], 'imagePullPolicy': 'Never',
                                            'command': ['/bin/sh', '-c', 'exec sleep 170'],
                                            'resources': {'requests': {'cpu': '100m', 'memory': '32Mi'},
                                                          'limits': {'cpu': '500m', 'memory': '128Mi'}},
                                            'securityContext': {'readOnlyRootFilesystem': True, 'allowPrivilegeEscalation': False,
                                                                'capabilities': {'drop': ['ALL']}},
                                            'volumeMounts': [{'name': 'tmp', 'mountPath': '/tmp'},
                                                             {'name': 'tools', 'mountPath': '/crg-tools', 'readOnly': True}]}],
                            'volumes': [{'name': 'tmp', 'emptyDir': {'sizeLimit': '16Mi'}},
                                        {'name': 'tools', 'configMap': {'name': 'frozen-proc-error', 'defaultMode': 292}}]}}
            create(obj)
            item['pod_uid'] = get('pod', name)['metadata']['uid']
            save()
            run(['kubectl', 'wait', '-n', ns, '--for=condition=Ready', 'pod/'+name, '--timeout=40s'], timeout=45)
            current = get('pod', name)
            status = next(c for c in current['status']['containerStatuses'] if c['name'] == role)
            need(current['metadata']['uid'] == item['pod_uid'] and status['restartCount'] == 0 and
                 status['imageID'] == source_status['imageID'], 'EXACT_IMAGE_AND_NEW_POD')
            cid = status['containerID'].split('://', 1)[1]
            need(re.fullmatch('[0-9a-f]{64}', cid), 'CONTAINER_ID')
            pid = json.loads(run(['crictl', 'inspect', cid]).stdout)['info']['pid']
            instance = identity(pid)
            paths = [s[3:] for s in Path('/proc', str(pid), 'cgroup').read_text().splitlines() if s.startswith('0::')]
            need(len(paths) == 1 and cid in paths[0] and item['pod_uid'].replace('-', '_') in paths[0].replace('-', '_'), 'OWN_CGROUP')
            leaf = Path('/sys/fs/cgroup'+paths[0])
            need(leaf.is_dir() and not leaf.is_symlink(), 'OWN_CGROUP_LIVE')
            selected = current['spec']
            container = next(c for c in selected['containers'] if c['name'] == role)
            item.update(image_id_sha256=sha(status['imageID'].encode()), exact_source_image_match=True,
                        container_id=cid, main=instance, leaf=str(leaf),
                        actual_isolation={'securityContext': selected['securityContext'],
                            'automountServiceAccountToken': selected['automountServiceAccountToken'],
                            'restartPolicy': selected['restartPolicy'], 'volumes': selected['volumes'],
                            'resources': container['resources'], 'command': container['command'],
                            'containerSecurityContext': container['securityContext'],
                            'volumeMounts': container['volumeMounts'],
                            'hostNetwork': selected.get('hostNetwork', False),
                            'hostPID': selected.get('hostPID', False)})
            save()
            command = ['kubectl', 'exec', '-n', ns, name, '-c', role, '--', 'env',
                       'CRG_PROC_ERROR_CHECKS=authorized-disposable-readonly-only', 'PYTHONDONTWRITEBYTECODE=1',
                       'python', '/crg-tools/vendor-proc-read-error-checks.py', '--work-dir', '/tmp/crg-proc-error-checks',
                       '--helper-sha256', files['vendor-proc-read-error.py']]
            result = run(command, timeout=20, checked=False)
            value = json.loads(result.stdout)
            item['checks'] = {'exit': result.returncode, 'result': value}
            save()
            need(result.returncode == 0 and value['phase'] == 'passed' and len(value['checks']) == 24 and
                 value['python'] == '2.7.5' and value['own_identity'] == {'euid': 999, 'egid': 998, 'CAP_SYS_ADMIN_effective': False},
                 'VENDOR_RUNTIME_CHECKS:'+role)
        report['phase'] = 'passed'
    except BaseException as error:
        report.update(phase='failed', reason=str(error) if isinstance(error, ValueError) else type(error).__name__)
    finally:
        signal.alarm(0)
        if namespace_uid is not None:
            try:
                current = get('namespace', ns)
                need(current is not None and current['metadata']['uid'] == namespace_uid and
                     current['metadata']['labels'].get('crg-purpose') == 'proc-error-qualification', 'CLEANUP_NAMESPACE_OWNERSHIP')
                for role, item in report['roles'].items():
                    pod = get('pod', role+'-proc-error')
                    need(pod is None or pod['metadata']['uid'] == item.get('pod_uid'), 'CLEANUP_POD_OWNERSHIP')
                run(['kubectl', 'delete', 'namespace', ns, '--wait=true', '--timeout=45s'], timeout=50)
                report['namespace_absent'] = get('namespace', ns) is None
                deadline = time.monotonic()+15
                while any(Path(v['leaf']).exists() for v in report['roles'].values() if 'leaf' in v) and time.monotonic() < deadline:
                    time.sleep(0.25)
                for item in report['roles'].values():
                    if 'leaf' in item:
                        item['leaf_absent'] = not Path(item['leaf']).exists()
                        try:
                            item['original_main_gone'] = identity(item['main']['pid'])['start_ticks'] != item['main']['start_ticks']
                        except FileNotFoundError:
                            item['original_main_gone'] = True
                        need(item['leaf_absent'] and item['original_main_gone'], 'OWN_PROCESS_AND_CGROUP_GONE')
                need(report['namespace_absent'], 'NAMESPACE_GONE')
            except BaseException as error:
                report.update(phase='failed', cleanup_failure=type(error).__name__)
        report['ended_node_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
    print(json.dumps({'phase': report['phase'], 'reason': report.get('reason'),
                      'roles': list(report['roles']), 'namespace_absent': report.get('namespace_absent')}))
    return 0 if report['phase'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
