#!/usr/bin/env python3
"""Short controlled children only; never the actual aged wrapper execution."""
import contextlib,importlib.util,io,json,os,signal,subprocess,sys,tempfile,time,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
l=load('detached_launcher_under_test',HERE/'launch-aged.py');w=load('qualified_wrapper_helpers',HERE/'runner-v3.py')
LINUX=sys.platform=='linux' and os.path.isdir('/proc')


@contextlib.contextmanager
def fixture(body=None):
    with tempfile.TemporaryDirectory(prefix='crg-detach-unit-',dir='/var/tmp') as temp:
        base=Path(temp);root=base/'launch';entry=base/'child.py';output=base/'identity.json'
        code=body or ('import json,os,time\nfrom pathlib import Path\n'
            'Path('+repr(str(output))+').write_text(json.dumps({"pid":os.getpid(),"sid":os.getsid(0),"stdin":os.readlink("/proc/self/fd/0")}))\ntime.sleep(.2)\n')
        entry.write_text(code);cfg={'entry':str(entry),'launch_root':str(root),'wrapper_tools':str(base),
            'files_sha256':{'tests/live-capacity-aged-v1/runner-v3.py':l.sha(entry.read_bytes())}}
        e=types.SimpleNamespace(readiness=lambda *a:({'phase':'ready','postflight_allowed':True},{'controlled':True}))
        with patch.object(l,'ENTRY',entry),patch.object(l,'ROOT',root),patch.object(l,'PARENT',base),patch.object(w,'ROOT',base/'runner'),patch.object(l,'checked_sources'):
            yield root,entry,output,e,cfg


class Checks(unittest.TestCase):
    def test_default_and_launch_pending_have_no_spawn(self):
        e=types.SimpleNamespace(readiness=lambda *a:({'phase':'pending'},None))
        for args in [[],['--launch']]:
            with patch.object(l,'load_runtime',return_value=(w,e,{})),patch.object(l.sys,'platform','linux'),patch.object(l.os,'geteuid',return_value=0,create=True),patch.object(l,'launch_once') as launch,contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(l.main(args),2);launch.assert_not_called()
            self.assertEqual(json.loads(out.getvalue())['phase'],'pending')

    def test_default_ready_has_no_spawn(self):
        e=types.SimpleNamespace(readiness=lambda *a:({'phase':'ready','postflight_allowed':True},{}))
        with patch.object(l,'load_runtime',return_value=(w,e,{})),patch.object(l.sys,'platform','linux'),patch.object(l.os,'geteuid',return_value=0,create=True),patch.object(l,'launch_once') as launch,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(l.main([]),0);launch.assert_not_called()

    def test_marker_and_trusted_pair_required(self):
        e=types.SimpleNamespace(readiness=lambda *a:({'phase':'ready','postflight_allowed':True},{}))
        for env in [{},{'CRG_AGED_POSTFLIGHT':'authorized-disposable-test-node-only'}]:
            with patch.object(l,'load_runtime',return_value=(w,e,{})),patch.object(l.sys,'platform','linux'),patch.object(l.os,'geteuid',return_value=0,create=True),patch.dict(os.environ,env,clear=True),patch.object(l,'launch_once') as launch,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(l.main(['--launch']),1);launch.assert_not_called()

    def test_no_partial_authority_or_root_override(self):
        for args in [['--authority-sha256','b'*64],['--directory','/var/tmp'],['--execute']]:
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):l.main(args)

    @unittest.skipUnless(LINUX,'Linux actual setsid/DEVNULL and PID/start')
    def test_actual_handoff_identity_session_stdin_private_files(self):
        with fixture() as (root,entry,output,e,cfg):
            result,child=l.launch_once(w,e,cfg,None,'b'*64)
            try:
                self.assertEqual(result['phase'],'handed-off-not-qualified');self.assertFalse(result['qualification_accepted'])
                self.assertEqual(result['pid'],child.pid);self.assertGreater(result['start_ticks'],0)
                self.assertEqual(root.stat().st_mode&0o777,0o700)
                self.assertTrue(all(p.stat().st_mode&0o777==0o600 for p in root.iterdir()))
                self.assertFalse(w.ROOT.exists());self.assertEqual(child.wait(timeout=5),0)
                value=json.loads(output.read_bytes());self.assertEqual(value,{'pid':child.pid,'sid':child.pid,'stdin':'/dev/null'})
            finally:
                if child.poll() is None:child.wait(timeout=5)

    @unittest.skipUnless(LINUX,'Linux actual immutable attempt')
    def test_duplicate_never_spawns_another_child(self):
        with fixture() as (root,entry,output,e,cfg):
            _,child=l.launch_once(w,e,cfg,None,'b'*64);child.wait(timeout=5)
            before={p.name:p.read_bytes() for p in root.iterdir()}
            with patch.object(l.subprocess,'Popen') as spawn,self.assertRaises(FileExistsError):l.launch_once(w,e,cfg,None,'b'*64)
            spawn.assert_not_called();self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})

    @unittest.skipUnless(LINUX,'Linux actual pre-release EOF')
    def test_failed_start_record_prevents_child_execution(self):
        with fixture() as (root,entry,output,e,cfg):
            actual=w.save
            def fail(path,value):
                if path.name=='start.json':raise OSError('controlled persistence failure')
                actual(path,value)
            with patch.object(w,'save',side_effect=fail),self.assertRaises(OSError):l.launch_once(w,e,cfg,None,'b'*64)
            self.assertFalse(output.exists());error=json.loads((root/'error.json').read_bytes());self.assertFalse(error['release_attempted'])
            self.assertFalse(Path('/proc',str(error['pid'])).exists())

    @unittest.skipUnless(LINUX,'Linux actual child source recheck')
    def test_changed_wrapper_exits126_without_running(self):
        with fixture() as (root,entry,output,e,cfg):
            cfg['files_sha256']['tests/live-capacity-aged-v1/runner-v3.py']='0'*64
            result,child=l.launch_once(w,e,cfg,None,'b'*64)
            self.assertEqual(child.wait(timeout=5),126);self.assertFalse(output.exists());self.assertFalse(result['qualification_accepted'])

    @unittest.skipUnless(LINUX,'Linux real post-release ambiguity')
    def test_receipt_write_failure_retains_running_attempt_no_retry(self):
        with fixture() as (root,entry,output,e,cfg):
            actual=w.save
            def fail(path,value):
                if path.name=='launch.json':raise OSError('controlled launch receipt failure')
                actual(path,value)
            with patch.object(w,'save',side_effect=fail),self.assertRaises(OSError):l.launch_once(w,e,cfg,None,'b'*64)
            error=json.loads((root/'error.json').read_bytes());self.assertTrue(error['release_attempted']);self.assertTrue(error['release_flushed'])
            child=l.HANDOFFS[-1];self.assertEqual(child.wait(timeout=5),0);self.assertTrue(output.exists())
            with patch.object(l.subprocess,'Popen') as spawn,self.assertRaises(FileExistsError):l.launch_once(w,e,cfg,None,'b'*64)
            spawn.assert_not_called()

    @unittest.skipUnless(LINUX,'Linux actual wrapper guard/readiness')
    def test_existing_wrapper_or_changed_readiness_creates_no_launch(self):
        with fixture() as (root,entry,output,e,cfg):
            w.ROOT.mkdir()
            with self.assertRaisesRegex(ValueError,'WRAPPER_ATTEMPT_ALREADY_EXISTS'):l.launch_once(w,e,cfg,None,'b'*64)
            self.assertFalse(root.exists())
        with fixture() as (root,entry,output,e,cfg):
            e.readiness=lambda *a:({'phase':'pending'},None)
            with self.assertRaisesRegex(ValueError,'READINESS_CHANGED'):l.launch_once(w,e,cfg,None,'b'*64)
            self.assertFalse(root.exists())

    @unittest.skipUnless(LINUX,'Linux actual signal at release commit')
    def test_signal_at_commit_is_recorded_without_claiming_cancellation(self):
        original=l.subprocess.Popen
        class Pipe:
            def __init__(self,p):self.p=p
            def __getattr__(self,n):return getattr(self.p,n)
            def flush(self):self.p.flush();os.kill(os.getpid(),signal.SIGTERM)
        def spawn(*args,**kw):
            child=original(*args,**kw);child.stdin=Pipe(child.stdin);return child
        with fixture() as (root,entry,output,e,cfg),patch.object(l.subprocess,'Popen',side_effect=spawn):
            result,child=l.launch_once(w,e,cfg,None,'b'*64)
            self.assertEqual(result['launcher_signals'],[signal.SIGTERM]);self.assertEqual(child.wait(timeout=5),0)

    @unittest.skipUnless(LINUX,'Linux real parent exit with detached child')
    def test_child_survives_real_launcher_parent_exit(self):
        with fixture() as (root,entry,output,e,cfg):
            done=entry.parent/'done';entry.write_text('import time\nfrom pathlib import Path\ntime.sleep(2)\nPath('+repr(str(done))+').write_text("done")\n')
            cfg['files_sha256']['tests/live-capacity-aged-v1/runner-v3.py']=l.sha(entry.read_bytes())
            script='''import importlib.util,json,sys,types
from pathlib import Path
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
l=load('probe_launch',@LAUNCH@);w=load('probe_wrapper',@WRAPPER@)
l.ROOT=Path(@ROOT@);l.PARENT=l.ROOT.parent;l.ENTRY=Path(@ENTRY@);w.ROOT=l.ROOT.parent/'runner';l.checked_sources=lambda c:None
e=types.SimpleNamespace(readiness=lambda *a:({'postflight_allowed':True},{}))
value,child=l.launch_once(w,e,@CFG@,None,'b'*64);print(json.dumps(value))
'''
            for token,value in {'@LAUNCH@':str(HERE/'launch-aged.py'),'@WRAPPER@':str(HERE/'runner-v3.py'),'@ROOT@':str(root),'@ENTRY@':str(entry)}.items():script=script.replace(token,repr(value))
            script=script.replace('@CFG@',repr(cfg));p=subprocess.run([sys.executable,'-B','-c',script],capture_output=True,timeout=5)
            self.assertEqual(p.returncode,0,p.stderr.decode());value=json.loads(p.stdout)
            self.assertFalse(done.exists());self.assertEqual(w.start_ticks(value['pid']),value['start_ticks'])
            deadline=time.monotonic()+5
            while not done.exists() and time.monotonic()<deadline:time.sleep(.05)
            self.assertTrue(done.exists());self.assertEqual(done.read_text(),'done')


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    print(json.dumps({'schema':'crg-aged-detached-checks-v1','phase':'passed' if result.wasSuccessful() else 'failed',
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
        'scope':'real short controlled children/proc/files/setsid/DEVNULL/parent exit; readiness and wrapper replaced, no actual aged execution',
        'actual_postflight_executed':False,'actual_executor_receipt_available':False,'release_accepted':False},indent=2));sys.exit(0 if result.wasSuccessful() else 1)
