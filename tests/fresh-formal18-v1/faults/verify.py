"""Fault/invariance checks for the actual comparison sources; no DB/K8s calls."""
from pathlib import Path
import argparse,ast,hashlib,importlib.util,json,os,platform,tempfile,types,unittest
from unittest import mock
P=Path(__file__).parent
spec=importlib.util.spec_from_file_location('observer',P/'business-observer.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
SHA=lambda raw:hashlib.sha256(raw).hexdigest()
CG='0::/kubepods.slice/kubepods-pod123.slice/cri-containerd-'+('a'*64)+'.scope\n'
ENTRY='/tmp/crg-soak-load-202611161843.py';OTHER='/tmp/crg-wait-timeline-202611161843.py'

class Compare(unittest.TestCase):
    def proc_fixture(self):
        temp=tempfile.TemporaryDirectory(prefix='crg-compare-fault-');self.addCleanup(temp.cleanup);root=Path(temp.name);group=root/'group';group.mkdir();(group/'cgroup.procs').write_text('101\n102\n')
        for pid,entry in [(101,OTHER),(102,ENTRY)]:
            p=root/'proc'/str(pid);p.mkdir(parents=True);(p/'cgroup').write_text(CG);(p/'stat').write_text(str(pid)+' (python) S '+'0 '*18+str(pid*10));(p/'cmdline').write_bytes(b'/usr/bin/python2.7\0'+entry.encode()+b'\0--worker\0'+ENTRY.encode()+b'\0')
        original=m.Path
        patch=mock.patch.object(m,'Path',side_effect=lambda *a:(root/'proc'/str(a[1])).joinpath(*a[2:]) if a and str(a[0])=='/proc' else original(*a));patch.start();self.addCleanup(patch.stop)
        return root,group
    def campaign_stop(self,group,expected=None):
        tree=ast.parse((P/'vendor-soak-campaign.py').read_bytes());names={'ticks','stop_worker'};nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names];assert len(nodes)==2
        module=ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[]));scope={'Path':m.Path,'os':m.os,'signal':m.signal,'re':m.re,'args':types.SimpleNamespace(wait_timeline_sha256='a'*64),'roles':{'dbs':{'group':group,'membership':CG,'entry':ENTRY}},'observers':{'dbs':types.SimpleNamespace(worker_identity=expected)}};exec(compile(module,'<actual-campaign-stop>','exec'),scope);return scope['stop_worker']
    def test_01_exact_entry_never_matches_observer_worker_argument(self):
        self.assertFalse(m.entry_matches([b'python',OTHER.encode(),b'--worker',ENTRY.encode()],ENTRY))
        self.assertTrue(m.entry_matches([b'/usr/bin/python2.7',ENTRY.encode(),b'--run-id',b'123'],ENTRY))
        for value in [[],[b'python'],[b'python-malware',ENTRY.encode()],[b'python',b'-B',ENTRY.encode()],[b'psql',ENTRY.encode()]]:self.assertFalse(m.entry_matches(value,ENTRY))
    def test_02_find_only_real_entry_and_original_start(self):
        root,group=self.proc_fixture();self.assertEqual(m.find_entry(group,CG,ENTRY),{'pid':102,'start_ticks':1020,'entry':ENTRY})
    def test_03_ambiguous_entry_refused(self):
        root,group=self.proc_fixture();(root/'proc/101/cmdline').write_bytes(b'python\0'+ENTRY.encode()+b'\0')
        with self.assertRaises(AssertionError):m.find_entry(group,CG,ENTRY)
    def test_04_moved_or_reused_entry_not_attributed(self):
        root,group=self.proc_fixture();(root/'proc/102/cgroup').write_text(CG.replace('a'*64,'b'*64));self.assertIsNone(m.find_entry(group,CG,ENTRY))
        (root/'proc/102/cgroup').write_text(CG)
        with mock.patch.object(m,'ticks',side_effect=[1010,1020,9999]):self.assertIsNone(m.find_entry(group,CG,ENTRY))
    def test_05_campaign_cleanup_signals_only_admitted_worker(self):
        root,group=self.proc_fixture();stop=self.campaign_stop(group,{'pid':102,'start_ticks':1020,'entry':ENTRY})
        with mock.patch.object(m.os,'pidfd_open',return_value=44,create=True) as opened,mock.patch.object(m.os,'close') as closed,mock.patch.object(m.signal,'pidfd_send_signal',create=True) as signaled:
            stop('dbs');opened.assert_called_once_with(102);signaled.assert_called_once_with(44,m.signal.SIGTERM);closed.assert_called_once_with(44)
    def test_06_campaign_reused_original_instance_refused_before_signal(self):
        root,group=self.proc_fixture();stop=self.campaign_stop(group,{'pid':102,'start_ticks':999,'entry':ENTRY})
        with mock.patch.object(m.os,'pidfd_open',side_effect=AssertionError('must not open'),create=True),mock.patch.object(m.signal,'pidfd_send_signal',create=True) as signaled:
            with self.assertRaises(RuntimeError):stop('dbs')
            signaled.assert_not_called()
    def test_07_emergency_stop_rechecks_script_and_membership(self):
        root,group=self.proc_fixture();p={'pid':101,'start_ticks':1010,'entry':ENTRY}
        with mock.patch.object(m.os,'pidfd_open',return_value=44,create=True),mock.patch.object(m.os,'close'),mock.patch.object(m.signal,'pidfd_send_signal',create=True) as signaled:
            with self.assertRaises(AssertionError):m.exact_stop(p,CG)
            signaled.assert_not_called()
        p={'pid':102,'start_ticks':1020,'entry':ENTRY};(root/'proc/102/cgroup').write_text('0::/other\n')
        with mock.patch.object(m.os,'pidfd_open',return_value=44,create=True),mock.patch.object(m.os,'close'),mock.patch.object(m.signal,'pidfd_send_signal',create=True) as signaled:
            with self.assertRaises(AssertionError):m.exact_stop(p,CG)
            signaled.assert_not_called()
    def test_08_emergency_stop_reused_PID_does_nothing(self):
        root,group=self.proc_fixture()
        with mock.patch.object(m.os,'pidfd_open',side_effect=AssertionError('must not open'),create=True):m.exact_stop({'pid':102,'start_ticks':999,'entry':ENTRY},CG)
    def test_09_timeline_bounds_partial_final_and_invalid_json(self):
        if not hasattr(m.os,'O_NOFOLLOW'):
            patch=mock.patch.object(m.os,'O_NOFOLLOW',0,create=True);patch.start();self.addCleanup(patch.stop)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,'timeline');p.write_bytes(b'{"kind":"header"}\n{"kind":')
            self.assertEqual(m.timeline(p,True)[1],[{'kind':'header'}])
            with self.assertRaises(AssertionError):m.timeline(p)
            p.write_bytes(b'not-json\n')
            with self.assertRaises(ValueError):m.timeline(p)
            p.write_bytes(b' '*(16385)+b'\n')
            with self.assertRaises(AssertionError):m.timeline(p)
            p.write_bytes(b'x'*4194305)
            with self.assertRaises(AssertionError):m.timeline(p,True)
    @unittest.skipUnless(os.name=='posix','Linux O_NOFOLLOW')
    def test_10_timeline_and_JSON_symlinks_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,'source');p.write_text('{}\n');link=Path(d,'link');link.symlink_to(p)
            for reader in [m.timeline,m.read_json]:
                with self.assertRaises(AssertionError):reader(link)
    def test_11_observer_rejects_other_duration_phase_or_unbounded_identity(self):
        for run,seconds,phase in [('private',600,'smoke'),('202611161843',599,'smoke'),('202611161843',600,'baseline')]:
            args=types.SimpleNamespace(run_id=run,seconds=seconds,test_phase=phase)
            with self.assertRaises(AssertionError):m.Observer('dbs',args,{},'a'*64,None)
    def test_12_exact_qualified_worker_and_timeline(self):
        self.assertEqual(SHA((P/'vendor-soak-load.py').read_bytes()),'52517a96032305ff3cbcd9f58be8dd8331d9975037ee81f7380400ed370275be')
        self.assertEqual(SHA((P/'wait-timeline.py').read_bytes()),'230fac774cc130e1bffc56e9f0076afaf13ea3260067880aeca9fc71793fe2e9')
    def test_13_original_campaign_measurement_entire_block_exact(self):
        old=(P/'original-campaign.py').read_text();new=(P/'vendor-soak-campaign.py').read_text();a='    deadline = time.monotonic() + 360';b='except BaseException as error:'
        before=old[old.index(a):old.index(b)];after=new[new.index(a):new.index(b)].replace('        for observer in observers.values():observer.check_alive()\n','')
        self.assertEqual(before,after)
    def test_14_original_campaign_helpers_except_stop_exact_AST(self):
        def functions(p):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_bytes()).body if isinstance(n,ast.FunctionDef)}
        old=functions(P/'original-campaign.py');new=functions(P/'vendor-soak-campaign.py');self.assertEqual({k for k,v in old.items() if new.get(k)!=v},{'stop_worker'})
    def test_15_observer_first_sample_before_worker_Popen(self):
        source=(P/'vendor-soak-campaign.py').read_text();a=source.index('        observer.start()');b=source.index("        command = 'CRG_VENDOR_SOAK_TEST",a);c=source.index('        job = subprocess.Popen(',b);self.assertLess(a,b);self.assertLess(b,c)
        self.assertIn("values[1]['kind']=='sample'",(P/'business-observer.py').read_text())
    def test_16_fresh_two_enforce_cells_original_budget_preserved(self):
        plan=json.loads((P/'plan-unfrozen.json').read_bytes());self.assertEqual(plan['matrix'],[{'role':r,'mode':mode,'seconds':600,'repeats':1} for r in ['dbs','hisdbs'] for mode in ['enforce']])
        a=dict(plan['configurations']['observe']);b=dict(plan['configurations']['enforce']);self.assertEqual(a.pop('mode'),'observe');self.assertEqual(b.pop('mode'),'enforce');self.assertEqual(a,b)
        old=json.loads((P/'original-plan.json').read_bytes());self.assertEqual(a,old['configuration'])
        for key,value in old['criteria'].items():self.assertEqual(plan['criteria'][key],value)
    def test_17_original_driver_helpers_after_only_path_adapter_exact_AST(self):
        before=(P/'original-driver.py').read_bytes().replace(b'capacity1761',b'business1856').replace(b'CAPACITY1761',b'BUSINESS1856');after=(P/'business-driver.py').read_bytes()
        def functions(raw):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
        self.assertEqual(functions(before),functions(after))
    def test_18_original600_no_shorter_or_relaxed_SQL_or_backup(self):
        campaign=(P/'vendor-soak-campaign.py').read_text();driver=(P/'business-driver.py').read_text()
        self.assertIn("'--seconds','600'",driver);self.assertNotIn("'--seconds','120'",driver)
        self.assertIn('args.seconds + 120',campaign);self.assertIn("[30] if args.test_phase == 'smoke'",campaign);self.assertIn("cycle['content_ended_epoch'] <= native_ended",campaign)
        plan=json.loads((P/'plan-unfrozen.json').read_bytes());self.assertEqual(plan['criteria']['SQL_API_errors'],0);self.assertEqual(plan['criteria']['request_max_seconds'],5);self.assertEqual(plan['criteria']['p95_bucket_upper_seconds'],1);self.assertEqual(plan['criteria']['minimum_scheduled_sample_coverage'],.98)
    def test_19_observe_absence_and_failure_originals_exported(self):
        source=(P/'runner.py').read_text();self.assertIn("'expected_absent_observe_journals'",source);self.assertIn("if arm=='enforce' or (folder/'resource-state/journal.json').exists()",source)
        for value in ['wait-session.json','wait-observer.log','timeline.jsonl','stop.json','load.json','business-backup.json']:self.assertIn(value,source)
        self.assertIn('MAX_FILES=96',(P/'artifact-transfer.py').read_text())
    def test_20_new_observer_never_writes_cgroup_or_executes_SQL(self):
        source=(P/'business-observer.py').read_text();self.assertNotIn('pg_reclaim',source);self.assertNotIn('PQsendQuery',source);self.assertNotIn('UPDATE ',source);self.assertNotIn('LOCK TABLE',source)
        tree=ast.parse(source)
        for n in ast.walk(tree):
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ['write_text','write_bytes']:
                self.fail('use only private output APIs; no implicit arbitrary text writes')
    def test_21_full_window_partial_timeline_cannot_be_qualified(self):
        source=(P/'business-observer.py').read_text();self.assertIn('span>=600',source);self.assertIn("terminal['backend_query_errors']==0",source);self.assertIn("terminal['reason']=='explicit_own_stop_file'",source);self.assertIn("absent(self.identity) and absent(self.worker_identity)",source)
    def test_22_source_privacy_and_no_credentials(self):
        raw=(P/'business-observer.py').read_bytes();self.assertNotIn(b'PGPASSWORD',raw);self.assertNotIn(b'PQerrorMessage',raw);self.assertNotIn(b'str(error)',raw)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();suite=unittest.defaultTestLoader.loadTestsFromTestCase(Compare);ids=[v.id() for v in suite];r=unittest.TextTestRunner(verbosity=2).run(suite)
    result={'schema':'crg-formal18-source-faults-v1','phase':'passed' if r.wasSuccessful() else 'failed','executed':r.testsRun,'passed':r.testsRun-len(r.failures)-len(r.errors)-len(r.skipped),'skipped':[{'test':t.id(),'reason':reason} for t,reason in r.skipped],'system':platform.system(),'kernel':platform.release(),'machine':platform.machine(),'python':platform.python_version(),'source_sha256':{p.name:SHA(p.read_bytes()) for p in P.iterdir() if p.is_file() and p.name not in ['verification.json']},'test_ids':ids,'failures':[{'test':t.id(),'trace':trace[-3000:]} for t,trace in r.failures+r.errors],'database_Kubernetes_or_cgroup_writes':False}
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    raise SystemExit(0 if r.wasSuccessful() else 1)
