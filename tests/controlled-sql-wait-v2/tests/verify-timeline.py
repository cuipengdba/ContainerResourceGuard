"""Fault checks for privacy, bounds and own-cgroup attribution; no DB access."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import stat
import tempfile
import unittest
from unittest import mock

P=Path(__file__).parent
spec=importlib.util.spec_from_file_location('wait_timeline',P/'timeline.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
CID='a'*64
CG='0::/kubepods.slice/kubepods-pod123.slice/cri-containerd-'+CID+'.scope\n'
PSI='some avg10=0.00 avg60=1.25 avg300=0.22 total=100\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=3\n'


class Timeline(unittest.TestCase):
    def test_01_counter_format_and_unknown_field_privacy(self):
        self.assertEqual(m.counters('usage_usec 42\nprivate_token private-value\n',m.CPU_KEYS),{'usage_usec':42})
        for value in ['-1','NaN','1.2','1e5','0x123','private','1'*23]:
            with self.assertRaises(ValueError):m.integer(value)
        for value in ['usage_usec 1\nusage_usec 2','usage_usec 1 private']:
            with self.assertRaises(ValueError):m.counters(value,m.CPU_KEYS)
    def test_02_pressure_exact_numeric_shape(self):
        result=m.pressure(PSI);self.assertEqual(result['some']['total'],100);self.assertEqual(result['some']['avg60'],1.25)
        self.assertEqual(set(result['some']),{'avg10','avg60','avg300','total'})
    def test_03_pressure_rejects_arbitrary_or_ambiguous_data(self):
        for value in ['',PSI+PSI,PSI.replace('avg10=0.00','password=private'),PSI.replace('avg10=0.00','avg10=NaN'),PSI.replace('avg10=0.00','avg10=101.00'),PSI.replace('total=100','total=-1')]:
            with self.assertRaises(ValueError):m.pressure(value)
    def test_04_io_counts_and_device_bound(self):
        self.assertEqual(m.io_counters('8:0 rbytes=12 wbytes=24 rios=1 private=secret\n'),{'8:0':{'rbytes':12,'wbytes':24,'rios':1}})
        with self.assertRaises(ValueError):m.io_counters(''.join('8:%d rbytes=1\n'%i for i in range(33)))
        for bad in ['secret rbytes=1','8:0 rbytes=-1','8:0 rbytes=1 rbytes=2','8:0 rbytes=1\n8:0 wbytes=2']:
            with self.assertRaises(ValueError):m.io_counters(bad)
    def test_05_lock_backend_attribution(self):
        rows=[['101','active','Lock','relation','5.1','{202}']]
        result=m.backends(rows)
        self.assertEqual(result,[{'pid':101,'state':'active','wait_type':'Lock','wait_event':'relation','query_age_seconds':5.1,'blocking_pids':[202]}])
    def test_06_unknown_backend_strings_never_exported(self):
        result=m.backends([['123','private-state','private-type','private-wait','0.5','{}']])
        self.assertNotIn('private',json.dumps(result));self.assertEqual(result[0]['wait_event'],'other')
    def test_07_backend_identity_bounds(self):
        for rows in [[['0','active','Lock','relation','1','{}']], [['1','active','Lock','relation','1','{}']]*2, [['1','active','Lock','relation','NaN','{}']], [['1','active','Lock','relation','-1','{}']], [['1','active','Lock','relation','1','{secret}']], [['1','active','Lock','relation','1','{'+','.join(str(i) for i in range(33))+'}']], [['1','active','Lock','relation','1','{}','private']], [['1','active','Lock','relation','1','{}']]*33]:
            with self.assertRaises(ValueError):m.backends(rows)
    def pin(self):
        values={'/proc/self/cgroup':CG,'/proc/1/cgroup':CG}
        info=mock.Mock(st_dev=42,st_ino=123)
        reader=mock.patch.object(m,'read_text',side_effect=lambda p:values[p]);clock=mock.patch.object(m,'start_ticks',return_value=1234);st=mock.patch.object(m.os,'stat',return_value=info);path=mock.patch.object(m.os.path,'realpath',side_effect=lambda p:p)
        for patch in [reader,clock,st,path]:patch.start();self.addCleanup(patch.stop)
        return m.PinnedGroup(CID,1234,hashlib.sha256(CG.encode()).hexdigest()),values,info
    def test_08_own_identity_passes_without_any_writes(self):
        with mock.patch.object(m.os,'open',side_effect=AssertionError('no write or raw open in pinned reads')):
            pin,values,info=self.pin();pin.verify()
        self.assertEqual(pin.identity,(42,123))
    def test_09_pid1_reuse_stops_attribution(self):
        pin,values,info=self.pin()
        with mock.patch.object(m,'start_ticks',return_value=9999):
            with self.assertRaises(RuntimeError):pin.verify()
    def test_10_moved_membership_stops_attribution(self):
        pin,values,info=self.pin();values['/proc/self/cgroup']=CG.replace(CID,'b'*64)
        with self.assertRaises(RuntimeError):pin.verify()
    def test_11_reused_group_inode_stops_attribution(self):
        pin,values,info=self.pin();info.st_ino=124
        with self.assertRaises(RuntimeError):pin.verify()
    def test_12_namespace_root_or_other_container_refused(self):
        pin,values,info=self.pin()
        for cg in ['0::/\n',CG.replace(CID,'b'*64),'1:memory:/other\n',CG+'1:cpu:/other\n']:
            values['/proc/self/cgroup']=values['/proc/1/cgroup']=cg
            with self.assertRaises(RuntimeError):m.PinnedGroup(CID,1234,hashlib.sha256(cg.encode()).hexdigest())
    def test_13_source_hash_failure_precedes_libpq_load(self):
        with tempfile.TemporaryDirectory(prefix='crg-wait-verify-') as d:
            p=Path(d,'worker.py');p.write_bytes(b'raise RuntimeError("never execute")')
            with mock.patch.object(m.ctypes,'CDLL',side_effect=AssertionError('must not load library')):
                with self.assertRaises(RuntimeError):m.load_client(str(p),'0'*64)
    def test_14_bounded_reader_and_no_symlink(self):
        with tempfile.TemporaryDirectory(prefix='crg-wait-verify-') as d:
            p=Path(d,'sample');p.write_bytes(b'x'*(m.MAX_READ+1))
            with self.assertRaises(RuntimeError):m.read_text(str(p))
            p.write_bytes(b'abc');self.assertEqual(m.read_text(str(p)),'abc')
            if os.name=='posix':
                link=Path(d,'link');link.symlink_to(p)
                with self.assertRaises(OSError):m.read_text(str(link))
    def test_15_frames_reserve_terminal_and_reject_nan(self):
        with self.assertRaises(RuntimeError):m.encode_frame({'kind':'sample'},m.MAX_BYTES-2048)
        terminal=m.encode_frame({'kind':'terminal'},m.MAX_BYTES-100,terminal=True)
        self.assertTrue(terminal.endswith(b'\n'))
        with self.assertRaises(RuntimeError):m.encode_frame({'x':'y'*m.MAX_LINE},0)
        with self.assertRaises(ValueError):m.encode_frame({'elapsed':float('nan')},0)
    def test_16_fixed_query_scope_no_query_text_or_mutations(self):
        text=m.ACTIVITY_SQL
        self.assertTrue(text.startswith('SELECT pid,state,'));self.assertNotIn('SELECT *',text)
        self.assertNotIn('query,',text);self.assertNotIn('client_addr',text);self.assertNotIn('ALTER ',text)
        self.assertIn("application_name IN ('crg-disposable-soak','crg-disposable-lock')",text)
        self.assertIn('pid<>pg_backend_pid()',text);self.assertTrue(text.endswith('LIMIT 32'))
    def test_17_stop_file_requires_exact_identity_and_current_window(self):
        with tempfile.TemporaryDirectory(prefix='crg-wait-verify-') as d:
            self.assertFalse(m.stop_requested(d,'20261116',1234,'a'*64,1))
            value={'schema':'crg-owned-wait-stop-v1','run_id':'20261116','pid1_start_ticks':1234,'membership_sha256':'a'*64,'requested_monotonic':2}
            p=Path(d,'stop.json');p.write_text(json.dumps(value))
            self.assertTrue(m.stop_requested(d,'20261116',1234,'a'*64,1))
            for key,wrong in [('run_id','20261117'),('pid1_start_ticks',999),('membership_sha256','b'*64),('requested_monotonic',float('nan')),('requested_monotonic',0)]:
                changed=dict(value);changed[key]=wrong;p.write_text(json.dumps(changed))
                with self.assertRaises(RuntimeError):m.stop_requested(d,'20261116',1234,'a'*64,1)
    @unittest.skipUnless(os.name=='posix','O_NOFOLLOW Linux check')
    def test_18_symlink_stop_file_refused(self):
        with tempfile.TemporaryDirectory(prefix='crg-wait-verify-') as d:
            p=Path(d,'source');p.write_text('{}');Path(d,'stop.json').symlink_to(p)
            with self.assertRaises(OSError):m.stop_requested(d,'20261116',1234,'a'*64,1)

    def test_19_missing_pressure_is_explicit_and_never_zero(self):
        with mock.patch.object(m, 'read_text', side_effect=FileNotFoundError(2, 'private secret')):
            value=m.read_metric('host_cpu_pressure','ignored',m.pressure,optional_pressure=True)
            self.assertEqual(value,{'phase':'unavailable','reason':'kernel_interface_absent','errno':2})
            with self.assertRaises(m.MetricFailure) as caught:
                m.read_metric('cgroup_memory_events','ignored',lambda v:m.counters(v,m.EVENT_KEYS))
            self.assertEqual(caught.exception.detail['stage'],'cgroup_memory_events')
            self.assertEqual(caught.exception.detail['errno'],2)
    def test_20_pressure_permission_or_malformed_is_failure(self):
        for error in [PermissionError(13,'private secret'),OSError(5,'private secret')]:
            with mock.patch.object(m,'read_text',side_effect=error):
                with self.assertRaises(m.MetricFailure):m.read_metric('host_io_pressure','ignored',m.pressure,True)
        with mock.patch.object(m,'read_text',return_value='private secret'):
            with self.assertRaises(m.MetricFailure):m.read_metric('host_io_pressure','ignored',m.pressure,True)
        with mock.patch.object(m,'read_text',return_value=PSI):
            self.assertEqual(m.read_metric('host_io_pressure','ignored',m.pressure,True)['phase'],'available')
    def test_21_failure_record_never_exports_arbitrary_text(self):
        value=m.failure_record('private secret',RuntimeError('password private secret'))
        self.assertEqual(value,{'stage':'other','class':'runtime_error','errno':0,'reason':'bounded_observer_failure'})
    def test_22_entry_argument_does_not_select_observer(self):
        spec=importlib.util.spec_from_file_location('lock_case',P/'controlled-lock-case.py')
        case=importlib.util.module_from_spec(spec);spec.loader.exec_module(case)
        entry='/tmp/crg-soak-load-202611161824.py';observer=b'/tmp/crg-wait-timeline-202611161824.py'
        self.assertFalse(case.python_entry_matches([b'python',observer,b'--worker',entry.encode()],entry))
        for executable in [b'python',b'/usr/bin/python2.7',b'/usr/bin/python3.11']:
            self.assertTrue(case.python_entry_matches([executable,entry.encode(),b'--run-id',b'123'],entry))
        for args in [[],[b'python'],[b'python-malware',entry.encode()],[b'python',b'-B',entry.encode()],[b'psql',entry.encode()]]:
            self.assertFalse(case.python_entry_matches(args,entry))
    def test_23_normal_arm_exports_diagnostic_originals(self):
        import ast
        tree=ast.parse((P/'runner.py').read_bytes())
        branches=[n for n in ast.walk(tree) if isinstance(n,ast.If) and isinstance(n.test,ast.Compare) and ast.dump(n.test)==ast.dump(ast.parse("arm=='normal'",mode='eval').body)]
        matches=[n for n in branches if any(isinstance(v,ast.Constant) and v.value=='controlled-lock.json' for v in ast.walk(n))]
        self.assertEqual(len(matches),1)
        literals=[v.value for v in ast.walk(matches[0]) if isinstance(v,ast.Constant) and isinstance(v.value,str)]
        for name in ['controlled-lock.json','load.json','timeline.jsonl','stop.json','lock-native-worker.log','wait-observer.log']:
            self.assertIn(name,literals)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Timeline);ids=[t.id() for t in suite];result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'schema':'crg-wait-timeline-fault-tests-v1','phase':'passed' if result.wasSuccessful() else 'failed','system':platform.system(),'kernel':platform.release(),'machine':platform.machine(),'python':platform.python_version(),'executed':result.testsRun,'passed':result.testsRun-len(result.errors)-len(result.failures)-len(result.skipped),'skipped':[{'test':t.id(),'reason':reason} for t,reason in result.skipped],'test_ids':ids,'timeline_sha256':hashlib.sha256((P/'timeline.py').read_bytes()).hexdigest(),'verifier_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'database_network_or_cgroup_writes':False,'failures':[{'test':t.id(),'trace':s[-3000:]} for t,s in result.errors+result.failures]}
    with args.output.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
