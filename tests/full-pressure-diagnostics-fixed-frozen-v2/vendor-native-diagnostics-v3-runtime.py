from __future__ import division, print_function
"""Qualify diagnostics against a NEW PostgreSQL instance in a disposable pod.

The caller supplies read-only vendor bin/lib/share and fresh emptyDir volumes.
This test never connects to a deployed database or starts vendor business code.
"""
import ast
import ctypes
import hashlib
import json
import os
import select
import subprocess
import sys
import threading
import time
try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

assert os.environ.get('CRG_NATIVE_RUNTIME_QUALIFICATION') == 'new-emptydir-postgres-only'
assert sys.platform.startswith('linux') and os.geteuid() != 0
assert len(sys.argv) == 2 and sys.argv[1] in ['dbs', 'hisdbs']
role = sys.argv[1]
root = '/var/tmp/crg-native600-runtime'
assert not os.path.lexists(root)
os.mkdir(root, 0o700)
pgdata = '/opt/postgresql/pgdata'
bin_dir = '/opt/postgresql/pgsql/bin/'
source_dir = os.path.dirname(os.path.abspath(__file__))
worker = source_dir + '/vendor-soak-load-diagnostics-v3.py'
report = {'schema': 'crg-native-diagnostics-v3-real-pg-qualification-v1', 'phase': 'running',
          'role': role, 'checks': [], 'cases': {}, 'scope': 'fresh PG and mock HTTP only; not vendor business acceptance'}


def save():
    path = root + '/report.candidate'
    with open(path, 'w') as stream:
        stream.write(json.dumps(report, indent=2) + '\n')
    os.chmod(path, 0o600)
    os.rename(path, root + '/report.json')


def check(name, value):
    report['checks'].append({'name': name, 'passed': bool(value)})
    save()
    assert value, name


def command(argv, timeout=60, env=None):
    # Each child belongs to this fresh pod. On timeout only that Popen child is
    # killed; the caller then deletes the pod using its recorded UID.
    out = open(root + '/command-%d.log' % len(report['checks']), 'ab')
    process = subprocess.Popen(argv, stdout=out, stderr=out, env=env)
    began = time.time()
    while process.poll() is None and time.time() - began < timeout:
        time.sleep(.05)
    if process.poll() is None:
        process.kill()
        process.wait()
        out.close()
        raise RuntimeError('own qualification command timeout')
    out.close()
    assert process.returncode == 0, ('own command failed', argv[0], process.returncode)


def connection_functions():
    # Execute only the exact libpq declarations/functions from the frozen fork;
    # no argument parsing, schema creation, workload threads or signal handlers.
    with open(worker, 'rb') as stream:
        tree = ast.parse(stream.read(), worker)
    selected = []
    wanted = ['Connection', 'ready', 'connect', 'query', '_diagnostic_connect', '_diagnostic_backend_pid']
    for node in tree.body:
        if isinstance(node, ast.If) and isinstance(node.test, ast.Call) and isinstance(node.test.func, ast.Name) and node.test.func.id == 'hasattr':
            selected.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(n, ast.Name) and n.id == 'pq' for n in node.targets):
            selected.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(n, ast.Tuple) and [v.id for v in n.elts] == ['pointer', 'integer', 'string'] for n in node.targets):
            selected.append(node)
        elif isinstance(node, ast.For) and isinstance(node.target, ast.Tuple) and [n.id for n in node.target.elts] == ['name', 'returns', 'parameters']:
            selected.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in wanted:
            selected.append(node)
    assert len(selected) == 10
    tree.body = selected
    scope = {'ctypes': ctypes, 'time': time, 'select': select, 'args': type('Run', (), {'run_id': '20261112600000'})()}
    # eval accepts an exec-mode code object on both runtimes. A Python 2 exec
    # statement in this function is invalid with its generator expressions.
    eval(compile(tree, worker, 'exec'), scope, scope)
    return scope


class MockAPI(BaseHTTPRequestHandler):
    def do_POST(self):
        assert self.path == '/test'
        length = int(self.headers.get('Content-Length', '0'))
        assert 0 <= length <= 1024
        self.rfile.read(length)
        body = b'{"Result":"000"}'
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


server = None
pg_started = False
try:
    check('own-nonroot-empty-data-and-output', os.path.isdir(pgdata) and not os.listdir(pgdata) and os.path.isdir('/opt/postgresql/basebackup') and not os.listdir('/opt/postgresql/basebackup'))
    command([bin_dir + 'initdb', '-D', pgdata, '-L', '/opt/postgresql/pgsql/share/postgresql', '-A', 'trust', '-U', 'postgres', '--no-locale', '-E', 'UTF8'])
    command([bin_dir + 'pg_ctl', '-D', pgdata, '-l', root + '/postgres.log', '-o', '-h 127.0.0.1 -p 5432 -k ' + root + ' -c shared_buffers=32MB -c max_connections=20', '-w', '-t', '30', 'start'], 40)
    pg_started = True
    pg = connection_functions()
    readonly = pg['_diagnostic_connect']()
    try:
        values = pg['query'](readonly, 'SELECT current_setting(\'transaction_read_only\'),current_setting(\'statement_timeout\'),current_setting(\'application_name\')')
        report['observer_connection'] = {'transaction_read_only': values[0][0], 'statement_timeout': values[0][1], 'application_name': values[0][2], 'backend_pid': pg['_diagnostic_backend_pid'](readonly)}
        check('actual-observer-read-only-one-second-timeout', values == [['on', '1s', 'crg-disposable-observer']] and report['observer_connection']['backend_pid'] > 1)
    finally:
        readonly.close()
    server = HTTPServer(('127.0.0.1', 8090), MockAPI)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    for case_index, (case, seconds) in enumerate([('normal', 12), ('own-table-lock', 16), ('missing-pg-marker', 12)]):
        run_id = '20261112600' + ('0' if role == 'dbs' else '1') + str(case_index)
        output = '/opt/postgresql/basebackup/crg-soak-' + run_id
        env = dict(os.environ, CRG_VENDOR_SOAK_TEST='disposable-loopback-only', CRG_VENDOR_NATIVE_DIAGNOSTICS='qualified-disposable-loopback-only', CRG_PG_WAIT='authorized-disposable-readonly-only')
        if case == 'missing-pg-marker':
            env.pop('CRG_PG_WAIT')
        stream = open(root + '/' + case + '.log', 'wb')
        process = subprocess.Popen(['python', worker, '--run-id', run_id, '--seconds', str(seconds)], stdout=stream, stderr=stream, env=env)
        began = time.time()
        blocker = None
        blocker_file = None
        item = {'run_id': run_id, 'requested_seconds': seconds, 'worker_pid': process.pid}
        report['cases'][case] = item
        try:
            value = None
            while process.poll() is None and time.time()-began < 120:
                if os.path.exists(output + '/load.json'):
                    with open(output + '/load.json') as saved:
                        value = json.load(saved)
                    if value['phase'] == 'running':
                        break
                time.sleep(.05)
            assert value and value['phase'] == 'running', 'own worker did not enter running'
            if case == 'own-table-lock':
                blocker_file = open(root + '/blocker.log', 'wb')
                statement = 'BEGIN; LOCK TABLE crg_soak_' + run_id + '.fixture IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(8); ROLLBACK;'
                item['fault_started_epoch'] = time.time()
                blocker = subprocess.Popen([bin_dir + 'psql', '-X', '-h', '127.0.0.1', '-U', 'postgres', '-d', 'postgres', '-v', 'ON_ERROR_STOP=1', '-c', statement],
                                           stdout=blocker_file, stderr=blocker_file, env=dict(os.environ, PGAPPNAME='crg-disposable-qualification-blocker'))
                control = pg['connect']()
                try:
                    rows = []
                    for unused in range(40):
                        rows = pg['query'](control, "SELECT pid::text FROM pg_stat_activity WHERE application_name='crg-disposable-qualification-blocker' AND wait_event='PgSleep' LIMIT 2")
                        if rows:
                            break
                        time.sleep(.05)
                    assert len(rows) == 1
                    item['actual_blocker_backend_pid'] = int(rows[0][0])
                finally:
                    control.close()
            while process.poll() is None and time.time()-began < 160:
                time.sleep(.1)
            assert process.poll() is not None, 'own worker exceeded qualification deadline'
            stream.close()
            if blocker is not None:
                assert blocker.wait() == 0
                blocker_file.close()
                item['fault_finished_observed_epoch'] = time.time()
            with open(output + '/load.json', 'rb') as saved:
                load_raw = saved.read()
            with open(output + '/native-diagnostics.json', 'rb') as saved:
                diagnostic_raw = saved.read()
            native, diagnostic = json.loads(load_raw), json.loads(diagnostic_raw)
            item.update(exit=process.returncode, load=native, load_sha256=hashlib.sha256(load_raw).hexdigest(), diagnostics=diagnostic, diagnostics_sha256=hashlib.sha256(diagnostic_raw).hexdigest())
            summary = native['native_diagnostics']
            cpu = [summary['recorder_cpu_seconds'], summary['probe_thread_cpu_seconds'], summary['final_report_thread_cpu_seconds']]
            check(case + '-complete-bounded-identity-linked-artifact', (summary['diagnostic_complete'] if case != 'missing-pg-marker' else not summary['diagnostic_complete']) and summary['probe_thread_stopped'] and summary['report_sha256'] == item['diagnostics_sha256'] and diagnostic['worker_sha256'] == hashlib.sha256(open(worker, 'rb').read()).hexdigest() and len(diagnostic_raw) <= 8*1024*1024)
            check(case + '-native-and-diagnostic-request-counts-match', summary['request_count'] == native['sql']['attempts']+native['api']['attempts'] and summary['request_errors'] == native['sql']['errors']+native['api']['errors'])
            check(case + '-CPU-under-five-percent-one-core', all(v is not None for v in cpu) and sum(cpu) <= seconds * .05)
            check(case + '-original-integrity-time-and-process-criteria', native['payload_integrity'] and native['primary_not_restarted'] and native['threads_stopped'] and not native['interrupted'] and native['elapsed_seconds'] >= seconds and native['criteria']['maximum_seconds'] == 5 and native['criteria']['maximum_errors'] == 0)
            samples = diagnostic['pg_samples']
            check(case + '-PG-samples-have-real-session-identity', len(samples) >= seconds-1 and all(s['available'] for s in samples) and any(r['identity_available'] and r['activity_fields_available'] for s in samples for r in s['rows']))
            waits = [s['pg_wait'] for s in samples]
            if case == 'missing-pg-marker':
                check('actual-missing-marker-keeps-native-running-and-diagnostic-failure-visible', summary['pg_wait_samples'] == 0
                      and summary['pg_wait_errors'] == len(samples) and all(not w['available'] and w['targets'] == [] for w in waits)
                      and all(s['available'] for s in samples))
            else:
                targets = [r for w in waits for r in w['targets'] if r['kernel_wait']['available']]
                check(case+'-qualified-wait-identity-and-run-context', len(waits) == summary['pg_wait_samples'] and summary['pg_wait_errors'] == 0
                      and all(w['available'] and w['run_id'] == run_id for w in waits) and bool(targets)
                      and all(r['kernel_wait']['identity_rechecked_after_SQL'] for r in targets)
                      and diagnostic['unique_application_name'] == 'crg-disposable-soak-'+run_id)
                check(case+'-v2-stack-errors-retain-stage-errno-without-private-text', bool(targets) and all(r['kernel_wait']['kernel_stack'] == {'available':False,'reason':'OSError','stage':'read','errno':13,'errno_name':'EACCES','exception_messages_filenames_or_stack_contents_recorded':False} for r in targets))
            if case in ['normal', 'missing-pg-marker']:
                check(case+'-original-native-gate-passes', process.returncode == 0 and native['phase'] == 'passed' and native['sql']['errors'] == native['api']['errors'] == 0)
            else:
                errors = [e for e in diagnostic['requests'] if e['kind'] == 'sql' and not e['success']]
                lock_rows = [r for s in samples for r in s['rows'] if r['wait_event_type'] == 'Lock' and r['query_class'] == 'fixture-update' and item['actual_blocker_backend_pid'] in (r['blocking_pids'] or [])]
                check('controlled-lock-retains-original-native-failure', process.returncode == 1 and native['phase'] == 'failed' and native['sql']['errors'] >= 1 and native['api']['errors'] == 0)
                check('real-SQL-deadline-error-captured-with-PID-stage-time', len(errors) == native['sql']['errors'] and all(e['backend_pid'] > 1 and e['stage'] == 'query' and e['elapsed_seconds'] >= 5 and e['error']['code'] in ['sql-readiness-deadline', 'sql-result-deadline', 'sql-socket-deadline'] for e in errors))
                check('actual-lock-wait-and-blocker-correlate-to-client-PID', bool(lock_rows) and any(r['pid'] == e['backend_pid'] for r in lock_rows for e in errors))
                check('actual-qualified-PG-proc-lock-wait-links-client-PID', any(r['wait_event_type'] == 'Lock' and r['pid'] == e['backend_pid'] for r in targets for e in errors))
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            stream.close()
            if blocker is not None and blocker.poll() is None:
                blocker.kill()
                blocker.wait()
            if blocker_file is not None:
                blocker_file.close()
    report['phase'] = 'passed'
except BaseException as error:
    report.update(phase='failed', reason=type(error).__name__ + ':' + str(error)[:800])
finally:
    if server is not None:
        server.shutdown()
        server.server_close()
    if pg_started:
        try:
            command([bin_dir + 'pg_ctl', '-D', pgdata, '-m', 'fast', '-w', '-t', '30', 'stop'], 40)
            report['own_postgres_stopped'] = True
        except BaseException as error:
            report.update(phase='failed', cleanup_error=type(error).__name__)
    save()
print(json.dumps({'phase': report['phase'], 'checks': len(report['checks']), 'reason': report.get('reason')}))
raise SystemExit(0 if report['phase'] == 'passed' else 1)
