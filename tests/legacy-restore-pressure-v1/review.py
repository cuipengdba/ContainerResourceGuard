#!/usr/bin/env python3
"""Offline recomputation of archived CI receipts; never executes CRG or writes cgroups."""
import argparse
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--evidence', type=Path, required=True)
p.add_argument('--plan', type=Path, required=True)
a = p.parse_args()
sha = lambda raw: hashlib.sha256(raw).hexdigest()
planraw = a.plan.read_bytes()
assert sha(planraw) == '4c3ec3d5fcd92cbfae4a4b175958641c71013e32cf6e8b87b0c18a316e3aad85'
plan = json.loads(planraw)
assert a.evidence.stat().st_size <= 4 * 1024**2
with gzip.open(a.evidence, 'rb') as stream:
    raw = stream.read(16 * 1024**2 + 1)
assert len(raw) <= 16 * 1024**2
evidence = json.loads(raw)
assert evidence['schema'] == 'crg-exact-legacy-restore-CI-artifacts-v1'
assert len(evidence['artifacts']) == 4 and len(evidence['runs']) == 2
runs = {int(r['id']): r for r in evidence['runs']}
for r in runs.values():
    assert r['head_sha'] == '09550dde8034171dedc36b2ece80d45742095ba7'
    assert r['status'] == 'completed' and r['conclusion'] == 'success' and r['run_attempt'] == 1
    assert r['event'] == 'workflow_dispatch' and r['path'] == '.github/workflows/legacy-restore-pressure.yml'
    assert r['repository']['full_name'] == 'cuipengdba/ContainerResourceGuard'
rows = []
low, high, external = str(128 << 20), str(512 << 20), str(384 << 20)
for entry in evidence['artifacts']:
    receipt, runid = entry['download'], entry['download']['run_id']
    assert runid in runs and receipt['full_zip_digest_verified']
    raw = base64.b64decode(entry['ZIP_base64'], validate=True)
    assert len(raw) <= 4 * 1024**2
    assert receipt['artifact']['digest'] == 'sha256:' + sha(raw)
    files = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        assert len(infos) == len({i.filename for i in infos}) <= 200
        assert sum(i.file_size for i in infos) <= 16 * 1024**2
        for info in infos:
            n = PurePosixPath(info.filename)
            assert not n.is_absolute() and '..' not in n.parts and '\\' not in info.filename
            if not info.is_dir():
                assert info.file_size <= 2 * 1024**2
                files[info.filename] = archive.read(info)
    assert set(files) == set(receipt['members'])
    for n, meta in receipt['members'].items():
        assert sha(files[n]) == meta['sha256'] and len(files[n]) == meta['bytes']
    get = lambda n: json.loads(files[n])
    r, env = get('results/report.json'), get('environment.json')
    assert files['plan.json'] == planraw and r['plan_sha256'] == sha(planraw)
    assert sha(files['driver.py']) == r['driver_sha256'] == plan['test_inputs_sha256']['tests/legacy-restore-pressure-v1/driver.py']
    assert sha(files['workload.go']) == plan['test_inputs_sha256']['tests/legacy-restore-pressure-v1/workload.go']
    environment = next(v for v in plan['environments'] if v['runner'] == env['runner'])
    assert env['workflow_revision'] == runs[runid]['head_sha'] and int(env['run_id']) == runid and int(env['attempt']) == 1
    assert env['source50_verified'] and r['source_revision'] == plan['source_revision']
    assert r['kernel'] == env['kernel'] and r['kernel'].startswith(environment['kernel_prefix'])
    assert r['arch'] == environment['arch'] and r['binary_sha256'] == plan['binary_sha256'][r['arch']]
    assert r['phase'] == 'passed' and len(r['tests']) == 29 and all(v['passed'] for v in r['tests'])
    assert len({v['name'] for v in r['tests']}) == 29
    assert not r['cleanup']['errors'] and r['cleanup']['all_owned_containers_removed']
    assert [v['name'] for v in r['cases']] == plan['cases']
    for c in r['cases']:
        assert c['synthetic_legacy_journal'] and c['original_controls']['memory.max'] == low
        assert len(c['original_controls']) == 8 and c['main']['pid'] > 1 and c['main']['start_ticks'] > 0
        cleanup = c['cleanup']
        assert cleanup['container_absent'] and cleanup['cgroup_absent'] and cleanup['all_observed_dead']
        assert c['main'] in cleanup['observed_identities']
        ack = c['worker_acks']
        assert len(ack) >= 4 and not any(v['fsync_failed'] for v in ack)
        assert max(v['fsync_count'] for v in ack) > ack[0]['fsync_count']
        oom = next(v for v in r['tests'] if v['name'] == c['name'] + ': no observed cgroup OOM events')
        assert all(oom['before'][k] == oom['after'][k]
                   for k in ['oom', 'oom_kill', 'oom_group_kill'] if k in oom['after'])
        if c['name'] in ['allocate-during', 'external-during']:
            b = c['delay_barrier']
            assert b['published_journal_unchanged_before'] and b['published_journal_unchanged_after']
            assert b['temporary_still_present'] and b['start_monotonic_ns'] < b['end_monotonic_ns']
            assert b['trace_proves_delayed_named_temp']
            trace = files['results/' + c['name'] + '/restore.strace'].decode()
            assert any(b['temporary_name'] in line and 'fsync(' in line and 'DELAYED' in line
                       for line in trace.splitlines())
            assert get('results/' + c['name'] + '/restore.stdout') == c['delayed_restore']['status']
            assert c['delayed_restore']['exit'] != 0
        if c['name'] == 'unsafe-before':
            assert c['unsafe_restore']['exit'] != 0 and c['unsafe_restore']['controls']['memory.max'] == high
            item = next(v for v in c['unsafe_restore']['status']['items'] if v['file'] == 'memory.max')
            assert item['state'] == 'skipped' and item['reason_code'] == 'memory_safety'
            assert c['final_restore']['exit'] == 0 and c['final_restore']['controls'] == c['original_controls']
        elif c['name'] == 'allocate-during':
            assert c['delay_barrier']['current_after'] > 128 << 20
            assert c['delayed_restore']['controls']['memory.max'] == high
            item = next(v for v in c['delayed_restore']['status']['items'] if v['file'] == 'memory.max')
            assert item['state'] == 'skipped' and item['reason_code'] == 'memory_safety'
            assert c['delayed_restore']['journal']['mutations']['memory.max:']['pending'] == low
            assert c['final_restore']['exit'] == 0 and c['final_restore']['controls'] == c['original_controls']
        elif c['name'] == 'external-during':
            assert c['delayed_restore']['controls']['memory.max'] == external
            assert c['delayed_restore']['journal']['mutations']['memory.max:']['conflict']
            assert c['conflict_retry']['exit'] != 0 and c['conflict_retry']['controls']['memory.max'] == external
            item = next(v for v in c['conflict_retry']['status']['items'] if v['file'] == 'memory.max')
            assert item['state'] == 'conflict' and item['reason_code'] == 'external_conflict'
            assert c['external_returned_original']['exit'] == 0
            assert c['external_returned_original']['controls'] == c['original_controls']
        else:
            assert c['disable']['state'] == 'restored'
            assert any(v['memory_item'].get('reason_code') == 'memory_window' for v in c['stable_samples'])
            assert c['stable_samples'][-1]['actual_memory_max'] == low
            elapsed = next(v['elapsed_seconds'] for v in r['tests']
                           if v['name'] == 'live-agent: same process waits for stable window then restores')
            assert elapsed >= 5
        assert not get('results/' + c['name'] + '/journal.json')['mutations']
    rows.append({'runner': env['runner'], 'arch': r['arch'], 'kernel': r['kernel'],
                 'run_id': runid, 'artifact_id': receipt['artifact']['id'],
                 'ZIP_sha256': sha(raw), 'checks': 29, 'cases': 4,
                 'exact_final_ELF': r['binary_sha256'], 'all_checks_and_cleanup_passed': True})
assert {v['runner'] for v in rows} == {v['runner'] for v in plan['environments']}
assert len({v['artifact_id'] for v in rows}) == 4
print(json.dumps({'schema': 'crg-offline-legacy-restore-pressure-review-v1',
                  'scope': plan['scope'], 'plan_sha256': sha(planraw),
                  'environments': rows, 'total_checks': 116, 'cases': 16,
                  'whole_original_task_completed': False, 'stable_release_accepted': False}, indent=2))
