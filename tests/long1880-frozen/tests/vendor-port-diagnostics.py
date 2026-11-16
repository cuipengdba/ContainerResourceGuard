"""Fail-soft, read-only port diagnostics for disposable vendor test Pods.

This is a host test helper, never part of the resource-control daemon.
"""
import datetime
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import time


def _json(command):
    result = subprocess.run(command, capture_output=True, timeout=4, check=True)
    if len(result.stdout) > 2 * 1024**2:
        raise ValueError('metadata-size-limit')
    return json.loads(result.stdout)


def _get(kind, name, namespace=None):
    command = ['kubectl', 'get', kind, name, '--request-timeout=3s', '-o', 'json']
    if namespace is not None:
        command.extend(['-n', namespace])
    return _json(command)


def _pod_identity(meta, namespace, role):
    m = meta['metadata']
    spec = meta['spec']
    if (not re.fullmatch(r'crg-vendor-lab-[a-z0-9-]+', namespace)
            or role not in ['dbs', 'hisdbs']
            or m['namespace'] != namespace or m['name'] != role + '-business'
            or m.get('labels', {}).get('managed-by') != 'crg-vendor-test'
            or any(spec.get(k, False) for k in ['hostNetwork', 'hostPID', 'hostIPC'])
            or not re.fullmatch(r'[0-9a-f-]{36}', m['uid'])):
        raise ValueError('not-isolated-lab-Pod')
    rows = [v for v in meta['status']['containerStatuses'] if v['name'] == role]
    if len(rows) != 1 or not rows[0].get('state', {}).get('running'):
        raise ValueError('not-one-running-role-container')
    cid = rows[0]['containerID']
    if not re.fullmatch(r'containerd://[0-9a-f]{64}', cid):
        raise ValueError('unsupported-runtime-identity')
    return {'pod_uid': m['uid'], 'container_id': cid.split('://', 1)[1]}


class Session:
    def __init__(self, namespace, role, meta):
        self.namespace, self.role = namespace, role
        self.fixture = _pod_identity(meta, namespace, role)
        namespace_meta = _get('namespace', namespace)['metadata']
        if (namespace_meta['name'] != namespace
                or namespace_meta.get('labels', {}).get('managed-by') != 'crg-vendor-test'):
            raise ValueError('namespace-ownership-mismatch')
        self.namespace_uid = namespace_meta['uid']
        path = Path(__file__).resolve().parent / 'port-owner-observer.py'
        spec = importlib.util.spec_from_file_location('vendor_port_owner_observer', path)
        self.collector = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.collector)
        pid = self._runtime_pid()
        if type(pid) is not int or pid <= 1:
            raise ValueError('invalid-runtime-PID')
        self.target = self.collector.identity(pid)
        membership = self.target['cgroup_membership'].splitlines()
        if len(membership) != 1 or not membership[0].startswith('0::/'):
            raise ValueError('not-v2-runtime-membership')
        group = Path('/sys/fs/cgroup') / membership[0].split('::', 1)[1].lstrip('/')
        if ('..' in group.parts or '/kubepods.slice/' not in str(group)
                or group.name != 'cri-containerd-' + self.fixture['container_id'] + '.scope'
                or not group.is_dir() or group.resolve() != group):
            raise ValueError('not-own-runtime-leaf')
        for kind in ['net', 'pid', 'mnt']:
            if Path('/proc', str(pid), 'ns', kind).stat().st_ino == Path('/proc/1/ns', kind).stat().st_ino:
                raise ValueError('host-namespace-shared')
        self.group = str(group)
        if not self._matches():
            raise ValueError('fixture-changed-during-admission')

    def _runtime_pid(self):
        return _json(['crictl', 'inspect', self.fixture['container_id']])['info']['pid']

    def _matches(self):
        current = _pod_identity(_get('pod', self.role + '-business', self.namespace), self.namespace, self.role)
        # Pod UID/CID cannot survive deletion and namespace recreation. Runtime
        # PID, start, membership and net inode are checked again before scanning.
        return (current == self.fixture and self._runtime_pid() == self.target['pid']
                and self.collector.identity(self.target['pid']) == self.target)

    def snapshot(self, stage):
        started = time.monotonic()
        result = {'stage': stage, 'phase': 'partial', 'started_utc': _utc(),
                  'fixture': dict(self.fixture, namespace=self.namespace, role=self.role,
                                  namespace_uid=self.namespace_uid), 'issues': []}
        try:
            if not self._matches():
                result['issues'].append('fixture-identity-changed-no-scan')
            else:
                sample = self.collector.collect(self.target, [55432, 55433])
                result.update(phase=sample['phase'], sample=sample)
        except Exception as error:
            if getattr(error, '_crg_engine_interrupted', False):
                raise
            result['issues'].append('diagnostic-unavailable-' + type(error).__name__)
        result['elapsed_seconds'] = time.monotonic() - started
        return result


def _utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class Unavailable:
    def __init__(self, error):
        self.issue = 'diagnostic-admission-unavailable-' + type(error).__name__

    def snapshot(self, stage):
        return {'stage': stage, 'phase': 'partial', 'started_utc': _utc(),
                'issues': [self.issue], 'elapsed_seconds': 0}


def begin(namespace, role, meta):
    try:
        return Session(namespace, role, meta)
    except Exception as error:
        if getattr(error, '_crg_engine_interrupted', False):
            raise
        return Unavailable(error)
