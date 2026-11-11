from __future__ import division, print_function
"""Fresh emptyDir PG at the vendor data path; never mounts original DB data."""
import ast
import ctypes
import hashlib
import json
import os
import resource
import select
import subprocess
import sys
import threading
import time
import types

assert os.environ.get('CRG_PG_WAIT_RUNTIME') == 'new-emptydir-postgres-only'
assert len(sys.argv) == 2 and sys.argv[1] in ['dbs', 'hisdbs'] and os.geteuid() != 0
role = sys.argv[1]
root, data, bindir = '/var/tmp/crg-pgwait314-runtime', '/opt/postgresql/pgdata', '/opt/postgresql/pgsql/bin/'
assert not os.path.lexists(root) and os.path.isdir(data) and not os.listdir(data)
os.umask(0o077)
os.mkdir(root, 0o700)
here = os.path.dirname(os.path.abspath(__file__))
helper = here+'/vendor-pg-wait.py'
worker = here+'/vendor-soak-load-diagnostics.py'
assert hashlib.sha256(open(worker, 'rb').read()).hexdigest() == '50ea0454d17d5412a9d4085472ed89831e4408f60aa0fa0ca2dfd905a2bacb1f'
m = types.ModuleType('real_pg_wait_target')
m.__file__ = helper
exec(compile(open(helper, 'rb').read(), helper, 'exec'), m.__dict__)
run = '20261111314'+('0' if role == 'dbs' else '1')
report = {'schema': 'crg-pg-wait-real-runtime-v1', 'phase': 'running', 'role': role, 'checks': [], 'samples': {},
          'source_sha256': {os.path.basename(p): hashlib.sha256(open(p, 'rb').read()).hexdigest() for p in [helper, __file__, worker]},
          'helper_signals_or_control_writes': 0, 'own_fresh_PG_standard_start_stop': True,
          'original_data_mounted': False, 'business_acceptance': False}
def save():
    path = root+'/report.candidate'
    with open(path, 'w') as stream:
        stream.write(json.dumps(report, indent=2)+'\n')
    os.chmod(path, 0o600)
    os.rename(path, root+'/report.json')
def check(name, value):
    report['checks'].append({'name': name, 'passed': bool(value)})
    save()
    assert value, name
def command(argv, seconds=40):
    stream = open(root+'/own-command.log', 'ab')
    child = subprocess.Popen(argv, stdout=stream, stderr=stream)
    began = time.time()
    while child.poll() is None and time.time()-began < seconds:
        time.sleep(.05)
    if child.poll() is None:
        child.kill()
        child.wait()
        raise RuntimeError('OWN_COMMAND_DEADLINE')
    stream.close()
    assert child.returncode == 0, 'OWN_COMMAND_EXIT'
def connections():
    # Only frozen libpq declarations/functions; no CLI, worker threads or schema.
    tree = ast.parse(open(worker, 'rb').read(), worker)
    nodes = []
    wanted = ['Connection', 'ready', 'connect', 'query', '_diagnostic_connect', '_diagnostic_backend_pid']
    for node in tree.body:
        if isinstance(node, ast.If) and isinstance(node.test, ast.Call) and isinstance(node.test.func, ast.Name) and node.test.func.id == 'hasattr':
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(n, ast.Name) and n.id == 'pq' for n in node.targets):
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(n, ast.Tuple) and [v.id for v in n.elts] == ['pointer', 'integer', 'string'] for n in node.targets):
            nodes.append(node)
        elif isinstance(node, ast.For) and isinstance(node.target, ast.Tuple) and [v.id for v in node.target.elts] == ['name', 'returns', 'parameters']:
            nodes.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in wanted:
            nodes.append(node)
    assert len(nodes) == 10
    tree.body = nodes
    scope = {'ctypes': ctypes, 'time': time, 'select': select}
    eval(compile(tree, worker, 'exec'), scope, scope)
    return scope

started, opened, sleeper, otherdb = False, [], None, None
try:
    command([bindir+'initdb', '-D', data, '-L', '/opt/postgresql/pgsql/share/postgresql', '-A', 'trust', '-U', 'postgres', '--no-locale', '-E', 'UTF8'], 60)
    command([bindir+'pg_ctl', '-D', data, '-l', root+'/postgres.log', '-o', '-h 127.0.0.1 -p 5432 -k '+root+' -c shared_buffers=32MB -c max_connections=20', '-w', '-t', '30', 'start'])
    started = True
    pg = connections()
    query = pg['query']
    observer, target, decoy = pg['_diagnostic_connect'](), pg['connect'](), pg['connect']()
    opened.extend([observer, target, decoy])
    settings = query(observer, "SELECT current_setting('transaction_read_only'),current_setting('statement_timeout'),current_setting('data_directory'),current_database()", 1)
    report['observer_settings'] = settings
    check('actual-readonly-one-second-and-vendor-data-directory', settings == [['on', '1s', data, 'postgres']])
    query(target, "SET application_name='"+m.app_name(run)+"'")
    query(decoy, "SET application_name='"+m.app_name('20261111000')+"'")
    target_pid = pg['_diagnostic_backend_pid'](target)
    report['target_pid'] = target_pid
    check('actual-correct-run-unique-backend-selected', [r['pid'] for r in m.selected(query(observer, m.selection_sql(run), 1), run)] == [target_pid])
    query(target, 'CREATE TABLE crg_pgwait_fixture(id int PRIMARY KEY,payload text)')
    query(target, "INSERT INTO crg_pgwait_fixture SELECT i,repeat('x',128) FROM generate_series(1,64) AS i")
    allowed = []
    fdpath = '/proc/%d/fd' % target_pid
    names = os.listdir(fdpath)
    assert len(names) <= 256
    for name in names:
        try:
            link = os.readlink(fdpath+'/'+name)
            metadata = m.fd_metadata(link, run)
            if metadata['kind'] == 'allowlisted-path':
                allowed.append(metadata)
        except OSError:
            pass
    report['actual_allowlisted_backend_FD_metadata'] = allowed[:8]
    check('actual-backend-open-file-under-real-PGDATA-whitelist', bool(allowed) and all(v['path'].startswith(data+'/') for v in allowed))
    sampler = m.Sampler(run)
    def callback(sql, seconds):
        assert sql == sampler.sql and seconds == 1
        return query(observer, sql, seconds)
    value = sampler.sample(callback)
    report['samples']['idle'] = value
    target_metadata = value['targets'][0]['kernel_wait'] if value['targets'] else {}
    check('actual-PG-and-proc-identity-bound-and-rechecked', value['available'] and len(value['targets']) == 1 and target_metadata.get('available')
          and target_metadata['process']['pid'] == target_pid and target_metadata['identity_rechecked_after_SQL'])
    costs = []
    for unused in range(3):
        value = sampler.sample(callback)
        costs.append({'seconds': value['collection_seconds'], 'thread_CPU_seconds': value['observer_thread_cpu_seconds']})
        assert value['available'] and value['targets'][0]['kernel_wait']['available']
    report['three_sample_costs'] = costs
    check('three-real-samples-within-prespecified-cost', max(v['seconds'] for v in costs) <= .25 and max(v['thread_CPU_seconds'] for v in costs) <= .1)
    sleep_errors = []
    def own_sleep():
        try:
            query(target, 'SELECT pg_sleep(3)', 5)
        except Exception as error:
            sleep_errors.append(type(error).__name__)
    sleeper = threading.Thread(target=own_sleep)
    sleeper.start()
    for unused in range(40):
        value = sampler.sample(callback)
        rows = value['targets']
        if rows and rows[0]['wait_event'] == 'PgSleep':
            break
        time.sleep(.05)
    report['samples']['actual-pg-sleep'] = value
    check('actual-PG-wait-context-captured-without-query-body', value['available'] and len(rows) == 1 and rows[0]['wait_event'] == 'PgSleep'
          and rows[0]['kernel_wait']['available'] and 'SELECT pg_sleep' not in json.dumps(value))
    sleeper.join(6)
    check('original-test-query-completes-without-cancel-or-signal', not sleeper.is_alive() and not sleep_errors)
    sleeper = None
    # Same app in another database must not become a proc target.
    out = open(root+'/otherdb.log', 'wb')
    otherdb = subprocess.Popen([bindir+'psql', '-X', '-h', '127.0.0.1', '-U', 'postgres', '-d', 'template1', '-v', 'ON_ERROR_STOP=1', '-c', 'SELECT pg_sleep(2)'],
                               stdout=out, stderr=out, env=dict(os.environ, PGAPPNAME=m.app_name(run)))
    for unused in range(40):
        other = query(observer, "SELECT pid::text FROM pg_stat_activity WHERE datname='template1' AND application_name='"+m.app_name(run)+"'", 1)
        if other:
            break
        time.sleep(.05)
    value = sampler.sample(callback)
    report['samples']['other-database-filtered'] = value
    check('actual-other-database-and-other-run-excluded', bool(other) and value['available'] and [r['pid'] for r in value['targets']] == [target_pid])
    assert otherdb.wait() == 0
    otherdb = None
    out.close()
    key = (target_pid, value['targets'][0]['backend_start_epoch_text'])
    sampler.pins[key] += 1
    value = sampler.sample(callback)
    report['samples']['wrong-cached-start-ticks'] = value
    check('actual-proc-start-mismatch-discards-metadata', value['available'] and not value['targets'][0]['kernel_wait']['available']
          and value['targets'][0]['kernel_wait']['reason'] == 'PG_WAIT_PROCESS_CHANGED')
    # A real marker change between the SELECTs invalidates captured metadata.
    calls = [0]
    def changed(sql, seconds):
        rows = callback(sql, seconds)
        calls[0] += 1
        if calls[0] == 1:
            query(target, "SET application_name='"+m.app_name('20261111000')+"'")
        return rows
    value = sampler.sample(changed)
    report['samples']['real-marker-changed'] = value
    check('actual-marker-change-after-selection-discards-metadata', value['available'] and calls[0] == 2
          and value['targets'][0]['kernel_wait']['reason'] == 'PG_WAIT_BACKEND_CHANGED')
    query(target, "SET application_name='"+m.app_name(run)+"'")
    extras = []
    for unused in range(4):
        connection = pg['connect']()
        extras.append(connection)
        opened.append(connection)
        query(connection, "SET application_name='"+m.app_name(run)+"'")
    value = sampler.sample(callback)
    report['samples']['five-real-backends'] = value
    check('five-real-backends-explicitly-unknown-not-silently-truncated', not value['available']
          and value['reason'] == 'PG_WAIT_ROW_BOUND_OR_TRUNCATED' and value['targets'] == [])
    for connection in extras:
        connection.close()
        opened.remove(connection)
    for unused in range(40):
        value = sampler.sample(callback)
        if value['available'] and len(value['targets']) == 1:
            break
        time.sleep(.05)
    report['samples']['final'] = value
    check('recovers-with-same-original-backend-after-selection-faults', value['available'] and value['targets'][0]['pid'] == target_pid
          and value['targets'][0]['kernel_wait']['available'] and len(sampler.pins) <= 4)
    check('all-records-bounded-and-no-helper-control-actions', all(len(json.dumps(v).encode()) <= 8192 for v in report['samples'].values())
          and all(v['signals_or_control_writes'] == 0 for v in report['samples'].values()))
    report['self_maximum_RSS_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    check('qualification-Python-RSS-within-128MiB', report['self_maximum_RSS_kib'] <= 131072)
    report['phase'] = 'passed' if len(report['checks']) == 14 else 'failed'
except BaseException as error:
    report.update(phase='failed', reason_class=type(error).__name__, reason=str(error)[:180])
finally:
    if sleeper is not None:
        sleeper.join(7)
    if otherdb is not None:
        otherdb.wait()
    for connection in opened:
        try:
            connection.close()
        except Exception:
            pass
    if started:
        try:
            command([bindir+'pg_ctl', '-D', data, '-m', 'fast', '-w', '-t', '30', 'stop'])
            report['own_fresh_postgres_stopped'] = True
        except BaseException as error:
            report.update(phase='failed', cleanup_error=type(error).__name__)
    save()
print(json.dumps({'phase': report['phase'], 'checks': len(report['checks']), 'reason': report.get('reason')}))
sys.exit(0 if report['phase'] == 'passed' else 1)
