#!/usr/bin/env python3
"""Verify original1396 failed terminal receipts without executing the candidate."""
from pathlib import Path, PurePosixPath
import argparse, base64, gzip, hashlib, json

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--evidence', type=Path, required=True)
a = p.parse_args()
assert a.evidence.stat().st_size <= 4 * 1024**2
with gzip.open(a.evidence, 'rb') as stream:
    raw = stream.read(16 * 1024**2 + 1)
assert len(raw) <= 16 * 1024**2
e = json.loads(raw)
assert e['schema'] == 'crg-exact-original1396-terminal-v1'
files = {}
total = 0
for row in e['files']:
    name = PurePosixPath(row['name'])
    assert not name.is_absolute() and '..' not in name.parts
    assert name.as_posix() == row['name'] and row['name'] not in files
    data = base64.b64decode(row['base64'], validate=True)
    total += len(data)
    assert len(data) == row['bytes'] <= 3 * 1024**2 and total <= 6 * 1024**2
    assert hashlib.sha256(data).hexdigest() == row['sha256']
    files[row['name']] = data

read = lambda name: json.loads(files[name])
main = read('results/report.json')
campaign = read('results/campaign-baseline/report.json')
terminal = read('tools/exit.json')
assert hashlib.sha256(files['inputs/plan.json']).hexdigest() == terminal['plan_sha256'] == main['plan_sha256'] == '9018ae5400591afd4ce04b5fd379be59e892172cb193cf5a06fe9995d5d800a4'
assert hashlib.sha256(files['inputs/job.py']).hexdigest() == terminal['job_sha256'] == main['job_sha256'] == '4b2789bca4a30bbf0e2181f74422825a31896384fe6e6f546c2ea240a1a759ac'
assert terminal['exit'] == 1 and main['phase'] == 'failed'
assert not main['stable_release_accepted'] and not main['runtime_inherited']
assert len(main['tests']) == 12 and all(t['passed'] for t in main['tests'])
assert 'run_campaign' in main['traceback'] and 'exclusive' in main['traceback']
assert "run(['kubectl','get','pods','-A','-o','json','--request-timeout=10s']" in main['traceback']
assert main['error'] == 'test command failed, exit=1' and main['failure_class'] == 'RuntimeError'
assert set(main['phases']) == {'baseline'} and not main['phases']['baseline']['native_accepted']
assert campaign['phase'] == 'failed' and campaign['failure_class'] == 'KeyboardInterrupt'
assert campaign['requested_seconds'] == 86400 and len(campaign['backups']) == 1
assert campaign['backups'][0]['phase'] == 'content-passed-native-pending'
assert main['namespace_absent'] and main['namespace_delete_exit'] == 0 and not main.get('cleanup_errors')
assert len(main['cleanup']) == 2
assert all(c['leaf_absent'] and c['parent_absent'] and c['all_registered_absent'] for c in main['cleanup'].values())
obs = e['postfailure_cleanup_observation']
assert obs['read_only'] and obs['cluster']['namespace_query_exit'] == 0 and obs['cluster']['namespace_absent']
assert len(obs['cleanup']) == 2
assert all(c['leaf_absent'] and c['parent_absent'] and c['all_registered_absent'] for c in obs['cleanup'].values())
roles = {}
for role in ['dbs', 'hisdbs']:
    load = read('results/fixture/' + role + '-business/postgresql/basebackup/crg-soak-202611151396/load.json')
    assert load['phase'] == 'failed' and load['interrupted'] and load['threads_stopped']
    assert load['payload_integrity'] and load['primary_not_restarted']
    assert load['requested_duration_seconds'] == 86400 and 15000 < load['elapsed_seconds'] < 16000
    assert load['criteria']['minimum_scheduled_samples_fraction'] == .98
    samples = campaign['roles'][role]['samples']
    assert len(samples) == 254
    assert all(s[k] for s in samples for k in ['agent_same_process', 'cache_same_process', 'PID1_same_process'])
    assert all(s['memory_events']['oom_kill'] == 0 for s in samples)
    for axis in ['sql', 'api']:
        result = load[axis]
        assert result['errors'] == 0 and result['attempts'] == result['successes']
        assert sum(result['histogram']) == result['successes']
        assert result['max_seconds'] <= 5 and result['p95_bucket_upper_seconds'] <= 1
        assert result['sample_coverage'] < .98
    roles[role] = {k: load[k] for k in ['elapsed_seconds', 'sql', 'api', 'payload_integrity', 'primary_not_restarted']}
    roles[role]['host_samples'] = len(samples)
recorder = [json.loads(line) for name, data in files.items() if name.startswith('recorder/') for line in data.splitlines()]
assert recorder and all(not r.get(k) for r in recorder for k in ['node_query_error', 'pod_query_error', 'event_query_error'])
print(json.dumps({'schema': 'crg-original1396-terminal-review-v1', 'native_phase': 'failed',
    'direct_failure': 'coordinator exclusive() kubectl get pods -A returned1; original stderr not retained',
    'underlying_API_error_cause_known': False, 'baseline_accepted': False, 'enforce_started': False,
    'seven_day_started': False, 'startup_checks_passed': 12, 'content_cycles_native_pending': 1,
    'roles': roles, 'owned_cleanup_verified_again': True, 'original_files': len(files),
    'observer_samples': len(recorder), 'stable_release_accepted': False}, indent=2))
