"""Fault-driven, database-free verification of an isolated load-worker fork.

Executes only named AST functions/diagnostic constants, never the worker main.
Writes only its explicitly supplied output and fresh temporary directories.
"""
import argparse
import ast
import builtins
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import tempfile
import threading
import unittest
from unittest import mock

P=Path(__file__).parent
RAW=(P/'worker.py').read_bytes()
TREE=ast.parse(RAW)
FUNCTIONS={n.name:n for n in TREE.body if isinstance(n, ast.FunctionDef)}


def environment():
    ns={'threading':threading,'datetime':datetime,'json':json,'os':os,
        'tempfile':tempfile,'monotonic':lambda:10.,'lock':threading.Lock(),
        'bounds':[.001,.005,.01,.02,.05,.1,.25,.5,1,2,5]}
    names={'stats','failure_event','sample','sql_load','api_load','save'}
    selected=[]
    for node in TREE.body:
        if isinstance(node,ast.FunctionDef) and node.name in names:
            selected.append(node)
        elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id.startswith('DIAGNOSTIC_') for t in node.targets):
            selected.append(node)
    exec(compile(ast.Module(body=selected,type_ignores=[]),'<selected-worker-functions>','exec'),ns)
    ns['report']={'sql':ns['stats'](),'api':ns['stats']()}
    assignment=next(n for n in TREE.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Subscript) and isinstance(t.value,ast.Name) and t.value.id=='report' and isinstance(t.slice,ast.Constant) and t.slice.value=='failure_diagnostics' for t in n.targets))
    exec(compile(ast.Module(body=[assignment],type_ignores=[]),'<selected-diagnostic-init>','exec'),ns)
    return ns


class OneRequest:
    def __init__(self):self.finished=False;self.waits=[]
    def is_set(self):return self.finished
    def wait(self,seconds):self.waits.append(seconds);self.finished=True


class Connection:
    def __init__(self):self.closes=0
    def close(self):self.closes+=1


class Response:
    def __init__(self,code=200,body=b'{"Result":"000"}'):self.code=code;self.body=body;self.closes=0
    def getcode(self):return self.code
    def read(self,size):assert size==1024;return self.body
    def close(self):self.closes+=1


class Diagnostics(unittest.TestCase):
    def setUp(self):self.n=environment()
    def sample(self,success=False,error=None,stage='sql_query',elapsed=.01,kind='sql'):
        self.n['monotonic']=lambda:10.+elapsed
        self.n['sample'](kind,10.,success,stage,error)
        return self.n['report']['failure_diagnostics']
    def test_01_exact_other_functions_and_main(self):
        a=json.loads((P/'adapter.json').read_bytes())
        self.assertEqual(a['new_worker_sha256'],hashlib.sha256(RAW).hexdigest())
        old=(P/'original.py').read_bytes()
        self.assertEqual(a['old_worker_sha256'],hashlib.sha256(old).hexdigest())
        self.assertEqual(a['changed_existing_functions'],['api_load','sample','sql_load'])
        self.assertTrue(a['all_other_functions_and_original_main_exact'])
        def functions(tree):
            return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        before,after=functions(ast.parse(old)),functions(TREE)
        self.assertEqual(sorted(k for k in before if before[k]!=after[k]),['api_load','sample','sql_load'])
        old_text=old.decode().replace('\r\n','\n');new_text=RAW.decode()
        self.assertEqual(new_text[:new_text.index('# Diagnostic-only fork:')],old_text[:old_text.index('def sample(')])
        self.assertEqual(new_text[new_text.index('\n\ndef handle_stop'):],old_text[old_text.index('\n\ndef handle_stop'):])
    def test_02_metrics_remain_original_across_boundaries(self):
        # Independent original acceptance equations, including >5s success.
        values=[(False,.0001),(True,.001),(True,.005),(True,.02),(False,.5),(True,1),(True,2),(True,5),(True,5.0001),(False,8)]*17
        old={'attempts':0,'successes':0,'errors':0,'max_seconds':0,'total_seconds':0,'histogram':[0]*12}
        for success,elapsed in values:
            self.sample(success,elapsed=elapsed)
            e=(10.+elapsed)-10.
            old['attempts']+=1;old['successes' if success and e<=5 else 'errors']+=1
            old['max_seconds']=max(old['max_seconds'],e);old['total_seconds']+=e
            bucket=sum(e>b for b in self.n['bounds']);old['histogram'][bucket]+=1
        self.assertEqual(self.n['report']['sql'],old)
    def test_03_success_has_no_failure_event(self):
        self.assertEqual(self.sample(True)['events'],[])
    def test_04_success_over_sla_is_failure(self):
        d=self.sample(True,elapsed=5.01)
        self.assertEqual(d['events'][0]['reason'],'request_sla_exceeded')
        self.assertEqual(self.n['report']['sql']['errors'],1)
    def test_05_fixed_sql_reasons(self):
        for message,reason in self.n['DIAGNOSTIC_REASONS'].items():
            event=self.sample(error=RuntimeError(message))['events'][-1]
            self.assertEqual(event['reason'],reason)
            self.assertNotIn(message,json.dumps(event))
    def test_06_no_arbitrary_exception_strings(self):
        class Hostile(Exception):
            def __str__(self):raise AssertionError('must not call')
            def __repr__(self):raise AssertionError('must not call')
        for err in [Hostile('private'), RuntimeError('password=private'),RuntimeError('private'*10000),RuntimeError({'private':'value'})]:
            d=self.sample(error=err)
            self.assertEqual(d['events'][-1]['reason'],'request_exception')
        self.assertNotIn('private',json.dumps(d))
    def test_07_stage_and_class_are_fixed(self):
        d=self.sample(error=Exception('secret'),stage='secret')
        self.assertEqual(d['events'][0]['stage'],'unknown')
        self.assertEqual(d['events'][0]['exception_class'],'other')
    def test_08_event_count_cap_keeps_counters(self):
        for i in range(1000):d=self.sample(error=RuntimeError('bounded SQL readiness deadline'))
        self.assertEqual(len(d['events']),128);self.assertEqual(d['dropped_events'],872)
        self.assertEqual(self.n['report']['sql']['errors'],1000)
        self.assertEqual(d['events'][0]['attempt'],1);self.assertEqual(d['events'][-1]['attempt'],128)
    def test_09_byte_cap_drops_without_changing_verdict(self):
        d=self.n['report']['failure_diagnostics'];d['retained_event_bytes']=65535
        self.sample()
        self.assertEqual(d['events'],[]);self.assertEqual(d['dropped_events'],1)
        self.assertEqual(d['retained_event_bytes'],65535)
        self.assertEqual(self.n['report']['sql']['errors'],1)
    def test_10_serialized_size_is_exact_bounded(self):
        for i in range(128):d=self.sample()
        actual=sum(len(json.dumps(e,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')) for e in d['events'])
        self.assertEqual(actual,d['retained_event_bytes']);self.assertLessEqual(actual,65536)
        self.assertLessEqual(len(json.dumps(d).encode()),100000)
    def test_11_collection_serialization_failure(self):
        with mock.patch.object(json,'dumps',side_effect=OSError(28,'no space')):self.sample()
        self.assertEqual(self.n['report']['sql']['errors'],1)
        self.assertEqual(self.n['report']['failure_diagnostics']['collection_errors'],1)
        self.assertEqual(len(self.sample()['events']),1)
    def test_12_collection_clock_failure(self):
        with mock.patch.object(datetime,'datetime') as clock:
            clock.utcnow.side_effect=PermissionError(13,'private path')
            self.sample()
        self.assertEqual(self.n['report']['sql']['errors'],1)
        self.assertEqual(self.n['report']['failure_diagnostics']['collection_errors'],1)
    def test_13_no_sampling_files_network_or_extra_query(self):
        with mock.patch.object(builtins,'open',side_effect=AssertionError('sampling I/O')), mock.patch.object(tempfile,'mkstemp',side_effect=AssertionError('sampling I/O')):
            self.sample()
        self.assertEqual(self.n['report']['sql']['errors'],1)
    def test_14_concurrent_requests_preserve_caps_and_counts(self):
        def work(kind):
            for i in range(1000):self.n['sample'](kind,9.,False,'sql_query',RuntimeError('SQL input failed'))
        threads=[threading.Thread(target=work,args=(k,)) for k in ('sql','api')]
        for t in threads:t.start()
        for t in threads:t.join(5);self.assertFalse(t.is_alive())
        self.assertEqual(self.n['report']['sql']['errors'],1000);self.assertEqual(self.n['report']['api']['errors'],1000)
        d=self.n['report']['failure_diagnostics'];self.assertEqual(len(d['events']),128);self.assertEqual(d['dropped_events'],1872)
    def sql(self,connect_error=None,query_error=None,rows=16):
        c=Connection();stop=OneRequest();calls=[]
        def connect():
            if connect_error:raise connect_error
            return c
        def query(connection,statement):
            self.assertIs(connection,c);calls.append(statement)
            if query_error:raise query_error
            return [[i] for i in range(rows)]
        self.n.update(stop=stop,connect=connect,query=query,schema='crg_soak_20261116')
        self.n['sql_load']()
        return c,stop,calls,self.n['report']['failure_diagnostics']['events']
    def test_15_sql_connect_failure_stage(self):
        c,stop,calls,events=self.sql(connect_error=RuntimeError('SQL connection polling failed'))
        self.assertEqual(calls,[]);self.assertEqual(c.closes,0)
        self.assertEqual(events[0]['stage'],'sql_connect');self.assertEqual(events[0]['reason'],'sql_connection_polling')
        self.assertEqual(stop.waits,[2])
    def test_16_sql_readiness_failure_stage_and_connection_cleanup(self):
        c,stop,calls,events=self.sql(query_error=RuntimeError('bounded SQL readiness deadline'))
        self.assertEqual(c.closes,1);self.assertEqual(len(calls),1)
        self.assertEqual(events[0]['stage'],'sql_query');self.assertEqual(events[0]['reason'],'sql_readiness_deadline')
        self.assertEqual(events[0]['request_started_monotonic_seconds'],10.)
        self.assertTrue(events[0]['observed_utc'].endswith('Z'))
    def test_17_sql_result_mismatch(self):
        c,stop,calls,events=self.sql(rows=15)
        self.assertEqual(c.closes,1);self.assertEqual(events[0]['stage'],'sql_result')
        self.assertEqual(events[0]['reason'],'unexpected_response')
    def test_18_sql_original_statement_success_cleanup_and_period(self):
        c,stop,calls,events=self.sql()
        self.assertEqual(calls,['UPDATE crg_soak_20261116.fixture SET counter=counter+1 WHERE id BETWEEN 1 AND 16 RETURNING id'])
        self.assertEqual(stop.waits,[2]);self.assertEqual(c.closes,1);self.assertEqual(events,[])
    def api(self,response=None,error=None):
        stop=OneRequest();calls=[]
        def request(url,data,headers):
            calls.append((url,data,headers));return 'request'
        def open_url(value,timeout):
            self.assertEqual((value,timeout),('request',4))
            if error:raise error
            return response
        self.n.update(stop=stop,Request=request,urlopen=open_url)
        self.n['api_load']()
        self.assertEqual(calls,[('http://127.0.0.1:8090/test',b'{}',{'Content-Type':'application/json'})])
        self.assertEqual(stop.waits,[5])
        return self.n['report']['failure_diagnostics']['events']
    def test_19_api_exception(self):
        events=self.api(error=TimeoutError('private URL token'))
        self.assertEqual(events[0]['stage'],'api_request');self.assertEqual(events[0]['exception_class'],'TimeoutError')
        self.assertNotIn('private',json.dumps(events))
    def test_20_api_bad_response_and_cleanup(self):
        response=Response(503)
        events=self.api(response=response)
        self.assertEqual(response.closes,1);self.assertEqual(events[0]['stage'],'api_response')
    def test_21_api_malformed_JSON_and_cleanup(self):
        response=Response(body=b'private malformed')
        events=self.api(response=response)
        self.assertEqual(response.closes,1);self.assertEqual(events[0]['exception_class'],'JSONDecodeError')
        self.assertNotIn('private',json.dumps(events))
    def test_22_api_success(self):
        response=Response();self.assertEqual(self.api(response=response),[]);self.assertEqual(response.closes,1)
    def test_23_existing_atomic_snapshot_persists_diagnostics(self):
        self.sample(error=RuntimeError('bounded SQL result deadline'))
        with tempfile.TemporaryDirectory(prefix='crg-load-diagnostic-') as d:
            self.n['root']=d;self.n['save']()
            saved=json.loads(Path(d,'load.json').read_bytes())
            self.assertEqual(saved,self.n['report']);self.assertEqual(list(Path(d).iterdir()),[Path(d,'load.json')])
            if os.name=='posix':self.assertEqual(Path(d,'load.json').stat().st_mode&0o777,0o600)
    def test_24_full_snapshot_disk_full_preserves_prior_file(self):
        with tempfile.TemporaryDirectory(prefix='crg-load-diagnostic-') as d:
            self.n['root']=d;self.n['save']();before=Path(d,'load.json').read_bytes()
            self.sample()
            with mock.patch.object(os,'fsync',side_effect=OSError(28,'no space')):
                with self.assertRaises(OSError):self.n['save']()
            self.assertEqual(Path(d,'load.json').read_bytes(),before)
            self.assertEqual(list(Path(d).iterdir()),[Path(d,'load.json')])
            self.assertEqual(self.n['report']['sql']['errors'],1)
    def test_25_snapshot_permission_failure_does_not_change_metrics(self):
        self.sample()
        with tempfile.TemporaryDirectory(prefix='crg-load-diagnostic-') as d:
            self.n['root']=d
            with mock.patch.object(tempfile,'mkstemp',side_effect=PermissionError(13,'denied')):
                with self.assertRaises(PermissionError):self.n['save']()
        self.assertEqual(self.n['report']['sql']['errors'],1)
        self.assertEqual(len(self.n['report']['failure_diagnostics']['events']),1)
    def test_26_invalid_nonfinite_diagnostic_rejected(self):
        self.sample(elapsed=float('inf'))
        self.assertEqual(self.n['report']['failure_diagnostics']['collection_errors'],1)
        self.assertEqual(self.n['report']['sql']['errors'],1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Diagnostics)
    ids=[t.id() for t in suite]
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'schema':'crg-load-diagnostic-fault-verification-v1','phase':'passed' if result.wasSuccessful() else 'failed',
        'machine':platform.machine(),'kernel':platform.release(),'python':platform.python_version(),'system':platform.system(),
        'executed':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors),
        'test_ids':ids,'worker_sha256':hashlib.sha256(RAW).hexdigest(),
        'verifier_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'adapter_sha256':hashlib.sha256((P/'adapter.json').read_bytes()).hexdigest(),
        'business_database_or_network_access':False,'product_runtime_modified':False,
        'scope':'selected real worker functions with injected faults; not native vendor performance acceptance',
        'failures':[{'test':t.id(),'trace':s[-3000:]} for t,s in result.failures+result.errors]}
    with args.output.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
