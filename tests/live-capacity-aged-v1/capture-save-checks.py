#!/usr/bin/env python3
"""Controlled proc/Pod capture and real atomic-file tests; not actual lineage."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
s=load('capture_saver_under_test',HERE/'capture-save.py')
f=load('original_complete_capture_fixture',HERE/'capture-v3-checks.py');c=f.c
LINUX=sys.platform=='linux'


@contextlib.contextmanager
def fixture():
    with f.disk_fixture() as (state,inputs,files):
        base=files['root'];root=base/'inputs';cfg={'entry':str(s.ENTRY),'input_root':str(root),
            'files_sha256':{'tests/live-capacity-aged-v1/capture-v3.py':s.sha((HERE/'capture-v3.py').read_bytes())}}
        def capture():
            value=c.capture_exact(state,inputs);value.update(P10_complete=False,release_accepted=False)
            return 0,(json.dumps(value,indent=4)+'\n').encode(),b''
        with patch.object(s,'ROOT',root),patch.object(s,'PARENT',base),patch.object(s,'checked_sources'),patch.object(c.g,'component',side_effect=lambda:(state,inputs)),patch.object(s,'collect',side_effect=capture):
            yield root,state,inputs,cfg,capture


class Checks(unittest.TestCase):
    def test_pending_default_and_save_never_write(self):
        for args in [[],['--save']]:
            mocked=types.SimpleNamespace(g=types.SimpleNamespace(component=lambda:({'phase':'pending'},None)))
            with patch.object(s,'load_capture',return_value=(mocked,{})),patch.object(s.sys,'platform','linux'),patch.object(s.os,'geteuid',return_value=0,create=True),patch.object(s,'save_once') as save,contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(s.main(args),2);save.assert_not_called()
            self.assertFalse(json.loads(out.getvalue())['capture_saved'])

    def test_ready_default_is_readonly(self):
        state,inputs=f.acceptance_context()
        with patch.object(c.g,'component',return_value=(state,inputs)),patch.object(s,'load_capture',return_value=(c,{})),patch.object(s.sys,'platform','linux'),patch.object(s.os,'geteuid',return_value=0,create=True),patch.object(s,'save_once') as save,contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(s.main([]),0);save.assert_not_called()
        self.assertEqual(json.loads(out.getvalue())['phase'],'ready-to-save')

    def test_closed_and_nonlive_capture_windows_rejected(self):
        for state in [{'phase':'component-accepted'},{'phase':'pending','capture_allowed':True,'runner_identity_verified_live':False}]:
            with patch.object(c.g,'component',return_value=(state,None)),self.assertRaisesRegex(ValueError,'REAL_CAPTURE_WINDOW'):s.window(c)

    def test_both_original24h_native_acceptance_required(self):
        for stage in ['baseline','enforce']:
            state,inputs=f.acceptance_context();inputs[2]['phases'][stage]['native_accepted']=False
            with patch.object(c.g,'component',return_value=(state,inputs)),self.assertRaisesRegex(ValueError,'BOTH_ORIGINAL24H'):s.window(c)

    def test_no_execute_or_directory_override(self):
        for arg in ['--execute','--directory']:
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):s.main([arg])

    @unittest.skipUnless(LINUX,'Linux original controlled capture/0600 and real renameat2')
    def test_full_controlled_capture_exact_stdout_private_and_not_acceptance(self):
        with fixture() as (root,state,inputs,cfg,capture):
            result=s.save_once(c,cfg);raw=(root/s.SEAL).read_bytes()
            self.assertTrue(raw.startswith(b'{\n    "schema"')) # preserved four-space child stdout
            self.assertEqual(result['seal_sha256'],s.sha(raw));self.assertEqual(result['seal_bytes'],len(raw))
            self.assertEqual(result['phase'],'saved-lineage-not-accepted');self.assertFalse(result['actual_duration_accepted'])
            self.assertFalse(result['release_accepted']);self.assertFalse(result['postflight_allowed'])
            self.assertEqual((root/s.SEAL).stat().st_nlink,1);self.assertEqual((root/s.SEAL).stat().st_mode&0o777,0o600)
            self.assertEqual(root.stat().st_mode&0o777,0o700);self.assertFalse((root/s.ATTEMPT/'stdout.candidate').exists())
            self.assertEqual(json.loads((root/s.ATTEMPT/'receipt.json').read_bytes()),result)

    @unittest.skipUnless(LINUX,'Linux real duplicate guard')
    def test_duplicate_preserves_all_original_bytes(self):
        with fixture() as (root,state,inputs,cfg,capture):
            s.save_once(c,cfg);before={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with patch.object(s,'collect') as child,self.assertRaisesRegex(ValueError,'SEAL_ALREADY_EXISTS'):s.save_once(c,cfg)
            child.assert_not_called();self.assertEqual(before,{p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()})

    @unittest.skipUnless(LINUX,'Linux real exclusive attempt')
    def test_existing_attempt_is_never_reused(self):
        with fixture() as (root,state,inputs,cfg,capture):
            root.mkdir(mode=0o700);(root/s.ATTEMPT).mkdir();(root/s.ATTEMPT/'old').write_bytes(b'old')
            with patch.object(s,'collect') as child,self.assertRaises(FileExistsError):s.save_once(c,cfg)
            child.assert_not_called();self.assertEqual((root/s.ATTEMPT/'old').read_bytes(),b'old')
            self.assertFalse((root/s.ATTEMPT/'error.json').exists())

    @unittest.skipUnless(LINUX,'Linux actual atomic no-replace')
    def test_publish_collision_keeps_source_and_existing_destination(self):
        with fixture() as (root,state,inputs,cfg,capture):
            root.mkdir(mode=0o700);source=root/'candidate';destination=root/s.SEAL
            source.write_bytes(b'new');destination.write_bytes(b'old')
            with self.assertRaises(FileExistsError):s.publish_noreplace(source,destination)
            self.assertEqual(source.read_bytes(),b'new');self.assertEqual(destination.read_bytes(),b'old')

    @unittest.skipUnless(LINUX,'Linux real failed capture evidence')
    def test_child_failure_retained_without_seal(self):
        with fixture() as (root,state,inputs,cfg,capture),patch.object(s,'collect',return_value=(1,b'failed child stdout',b'controlled error')):
            with self.assertRaisesRegex(ValueError,'CAPTURE_SUBPROCESS_EXIT'):s.save_once(c,cfg)
            self.assertFalse((root/s.SEAL).exists());self.assertEqual((root/s.ATTEMPT/'stdout.candidate').read_bytes(),b'failed child stdout')
            self.assertTrue((root/s.ATTEMPT/'error.json').exists())

    @unittest.skipUnless(LINUX,'Linux real window change protects publication')
    def test_window_closing_after_capture_retains_candidate_only(self):
        with fixture() as (root,state,inputs,cfg,capture):
            def close():
                result=capture();state['capture_allowed']=False;return result
            with patch.object(s,'collect',side_effect=close),self.assertRaisesRegex(ValueError,'CAPTURE_WINDOW_CHANGED'):s.save_once(c,cfg)
            self.assertFalse((root/s.SEAL).exists());self.assertTrue((root/s.ATTEMPT/'stdout.candidate').exists())

    @unittest.skipUnless(LINUX,'Linux original complete controlled capture shape')
    def test_seal_wrong_binding_role_or_permission_is_rejected(self):
        with fixture() as (root,state,inputs,cfg,capture):
            _,raw,_=capture();original=json.loads(raw)
            for mutate in [lambda v:v.update(release_accepted=True),lambda v:v['fresh_three_phase_binding'].update(baseline_report_sha256='0'*64),lambda v:v['roles'].pop('hisdbs')]:
                value=copy.deepcopy(original);mutate(value)
                with self.assertRaises(ValueError):s.validate(json.dumps(value).encode(),c,state,inputs)

    @unittest.skipUnless(LINUX,'Linux real source digest pin')
    def test_source_pin_and_symlink_rejection(self):
        with fixture() as (root,state,inputs,cfg,capture):
            base=root.parent;source=base/'source.py';source.write_bytes(b'source')
            cfg.update(capture_tools=str(base),files_sha256={'source.py':s.sha(b'source')})
            # The outer fixture mocks production inventory only; exercise actual checker here.
            with patch.object(s,'ROOT',root):actual_checked_sources(cfg)
            source.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'FROZEN_CAPTURE_SOURCE'):actual_checked_sources(cfg)
            link=base/'alias';link.symlink_to(source)
            with self.assertRaisesRegex(ValueError,'SYMLINK_PATH'):s.regular(link)


actual_checked_sources=s.checked_sources
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    print(json.dumps({'schema':'crg-capture-save-checks-v1','phase':'passed' if result.wasSuccessful() else 'failed',
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
        'scope':'controlled proc/Pod/native records and real temp files/renameat2; never actual lineage or durations',
        'actual_seven_day_seal_created':False,'actual_postflight_executed':False,'release_accepted':False},indent=2));sys.exit(0 if result.wasSuccessful() else 1)
