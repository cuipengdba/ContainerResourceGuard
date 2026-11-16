#!/usr/bin/env python3
"""Controlled direct-child/real-file tests; never a real aged execution."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('runner_under_test',Path(__file__).with_name('runner-v3.py'))
r=importlib.util.module_from_spec(spec);sys.modules[spec.name]=r;spec.loader.exec_module(r)
NATIVE=sys.platform=='linux' and os.path.isdir('/proc')


@contextlib.contextmanager
def fixture(body=None,bad_hash=False):
    with tempfile.TemporaryDirectory(prefix='crg-runner-unit-',dir='/var/tmp') as temp:
        base=Path(temp);entry=base/'child.py';root=base/'attempt';report=base/'output';report.mkdir()
        code=body or ('from pathlib import Path\nimport json\nPath('+repr(str(report/'report.json'))+
            ').write_text(json.dumps({"phase":"controlled-short-child-only"}))\n')
        entry.write_text(code);contract={'files_sha256':{'tests/live-capacity-aged-v1/executor-v2.py':'0'*64 if bad_hash else r.digest(entry.read_bytes())}}
        e=types.SimpleNamespace(CONTRACT_SHA='a'*64,CONTRACT={'work_root':str(report)},
            readiness=lambda *a:({'phase':'ready','postflight_allowed':True},{'fixture':True}))
        with patch.object(r,'ROOT',root),patch.object(r,'PARENT',base),patch.object(r,'ENTRY',entry):yield root,report,e,contract


class Checks(unittest.TestCase):
    def test_pending_default_and_execute_write_nothing(self):
        for args in [[],['--execute']]:
            e=types.SimpleNamespace(readiness=lambda *a:({'phase':'pending'},None))
            with patch.object(r,'load_executor',return_value=(e,{})),patch.object(r.sys,'platform','linux'),patch.object(r.os,'geteuid',return_value=0,create=True),patch.object(r,'run_once') as execute,contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(r.main(args),2);execute.assert_not_called()
            self.assertEqual(json.loads(out.getvalue())['phase'],'pending')

    def test_default_ready_never_executes(self):
        e=types.SimpleNamespace(readiness=lambda *a:({'phase':'ready','postflight_allowed':True},{}))
        with patch.object(r,'load_executor',return_value=(e,{})),patch.object(r.sys,'platform','linux'),patch.object(r.os,'geteuid',return_value=0,create=True),patch.object(r,'run_once') as execute,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(r.main([]),0);execute.assert_not_called()

    def test_marker_and_authority_required_before_run(self):
        e=types.SimpleNamespace(readiness=lambda *a:({'phase':'ready','postflight_allowed':True},{}))
        for env,args in [({},['--execute']),({'CRG_AGED_POSTFLIGHT':'authorized-disposable-test-node-only'},['--execute'])]:
            with patch.object(r,'load_executor',return_value=(e,{})),patch.object(r.sys,'platform','linux'),patch.object(r.os,'geteuid',return_value=0,create=True),patch.dict(os.environ,env,clear=True),patch.object(r,'run_once') as execute,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(r.main(args),1);execute.assert_not_called()

    def test_partial_authority_cli_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):r.main(['--authority-sha256','a'*64])

    @unittest.skipUnless(NATIVE,'Linux actual proc/files/child')
    def test_actual_short_child_exit_receipt_not_qualification(self):
        with fixture() as (root,report,e,c):
            value=r.run_once(e,c,Path('/private/authority'),'b'*64)
            receipt=json.loads((root/'exit.json').read_bytes());start=json.loads((root/'start.json').read_bytes())
            self.assertEqual(value['exit'],0);self.assertFalse(value['qualification_accepted'])
            self.assertLess(receipt['elapsed_seconds'],1200);self.assertGreater(receipt['elapsed_seconds'],0)
            self.assertEqual(receipt['report_sha256'],r.digest((report/'report.json').read_bytes()))
            self.assertEqual((receipt['pid'],receipt['start_ticks']),(start['pid'],start['start_ticks']))
            self.assertFalse(Path('/proc',str(receipt['pid'])).exists())
            self.assertEqual(root.stat().st_mode&0o777,0o700)
            self.assertTrue(all(p.stat().st_mode&0o777==0o600 for p in root.iterdir()))
            self.assertEqual(value['receipt_sha256'],r.digest((root/'exit.json').read_bytes()))

    @unittest.skipUnless(NATIVE,'Linux actual exclusive guard')
    def test_duplicate_preserves_original_bytes(self):
        with fixture() as (root,report,e,c):
            r.run_once(e,c,None,'b'*64);before={p.name:p.read_bytes() for p in root.iterdir()}
            with self.assertRaises(FileExistsError):r.run_once(e,c,None,'b'*64)
            self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})

    @unittest.skipUnless(NATIVE,'Linux actual child digest rejection')
    def test_child_rechecks_entry_before_exec(self):
        with fixture(bad_hash=True) as (root,report,e,c):
            self.assertEqual(r.run_once(e,c,None,'b'*64)['exit'],126)
            receipt=json.loads((root/'exit.json').read_bytes());self.assertIsNone(receipt['report_sha256'])
            self.assertFalse((report/'report.json').exists())

    @unittest.skipUnless(NATIVE,'Linux actual pre-release EOF')
    def test_uncommitted_identity_never_releases_workload(self):
        with fixture() as (root,report,e,c):
            actual=r.save
            def fail_start(path,value):
                if path.name=='start.json':raise OSError('controlled identity persistence failure')
                actual(path,value)
            with patch.object(r,'save',side_effect=fail_start),self.assertRaises(OSError):r.run_once(e,c,None,'b'*64)
            self.assertFalse((report/'report.json').exists());self.assertFalse((root/'exit.json').exists())
            error=json.loads((root/'supervisor-error.json').read_bytes())
            self.assertFalse(error['workload_released']);self.assertFalse(Path('/proc',str(error['child_pid'])).exists())

    @unittest.skipUnless(NATIVE,'Linux real owned-child signal')
    def test_signal_forwarded_to_owned_child_and_actual_negative_exit(self):
        body='import os,signal,time\ntime.sleep(.1)\nos.kill(os.getppid(),signal.SIGTERM)\ntime.sleep(20)\n'
        with fixture(body) as (root,report,e,c):
            value=r.run_once(e,c,None,'b'*64);receipt=json.loads((root/'exit.json').read_bytes())
            self.assertEqual(value['exit'],-signal.SIGTERM);self.assertEqual(receipt['interrupted'],[signal.SIGTERM])
            self.assertFalse(Path('/proc',str(receipt['pid'])).exists())

    def release_race(self,module):
        # Real signal delivered at the old vulnerable flush point; no clocks mocked.
        original=module.subprocess.Popen
        class Pipe:
            def __init__(self,pipe):self.pipe=pipe
            def __getattr__(self,name):return getattr(self.pipe,name)
            def flush(self):
                self.pipe.flush();os.kill(os.getpid(),signal.SIGTERM)
        def spawn(*a,**kw):
            child=original(*a,**kw);child.stdin=Pipe(child.stdin);return child
        with patch.dict(globals(),r=module),fixture('import time\ntime.sleep(2)\n') as (root,report,e,c),patch.object(module.subprocess,'Popen',side_effect=spawn):
            value=module.run_once(e,c,None,'b'*64);receipt=json.loads((root/'exit.json').read_bytes())
            self.assertEqual(receipt['interrupted'],[signal.SIGTERM]);self.assertFalse(Path('/proc',str(receipt['pid'])).exists())
            return value['exit']

    @unittest.skipUnless(NATIVE,'Linux real signal release race')
    def test_old_release_signal_race_reproduced(self):
        path=Path(__file__).with_name('runner-v2.py')
        self.assertEqual(r.digest(path.read_bytes()),'716e4da18aa14c7654298d2da059034709975a39a3af14c794ce67518df8fbb8')
        spec=importlib.util.spec_from_file_location('old_runner_race_witness',path)
        old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        self.assertEqual(self.release_race(old),0) # known unsafe old outcome

    @unittest.skipUnless(NATIVE,'Linux real signal release race')
    def test_new_release_signal_is_forwarded(self):
        self.assertEqual(self.release_race(r),-signal.SIGTERM)

    @unittest.skipUnless(NATIVE,'Linux real inode guards')
    def test_symlink_and_hardlink_rejected(self):
        with fixture() as (root,report,e,c):
            target=report/'target';target.write_bytes(b'private');link=report/'link';link.symlink_to(target)
            with self.assertRaisesRegex(ValueError,'SYMLINK_INPUT'):r.regular(link)
            os.link(target,report/'hard')
            with self.assertRaisesRegex(ValueError,'REGULAR_BOUNDED_INPUT'):r.regular(target)

    @unittest.skipUnless(NATIVE,'Linux actual revalidation')
    def test_changed_readiness_creates_nothing(self):
        with fixture() as (root,report,e,c):
            e.readiness=lambda *a:({'phase':'pending'},None)
            with self.assertRaisesRegex(ValueError,'READINESS_CHANGED'):r.run_once(e,c,None,'b'*64)
            self.assertFalse(root.exists())


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    print(json.dumps({'schema':'crg-aged-runner-v3-checks-v1','phase':'passed' if result.wasSuccessful() else 'failed',
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
        'scope':'controlled short real child/file tests, never actual aged execution or 1200s qualification',
        'actual_postflight_executed':False,'release_accepted':False},indent=2));sys.exit(0 if result.wasSuccessful() else 1)
