#!/usr/bin/env python3
"""Controlled capture/native records and real private preparation files only."""
import contextlib,copy,importlib.util,io,json,os,struct,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
a=load('authority_under_test',HERE/'prepare-aged.py');e=load('original_authority_checker',HERE/'executor-v2.py')
s=load('private_file_helpers',HERE/'capture-save.py');f=load('complete_capture_fixture',HERE/'capture-v3-checks.py');c=f.c
LINUX=sys.platform=='linux';actual_sources=a.checked_sources


@contextlib.contextmanager
def fixture():
    with f.disk_fixture() as (state,inputs,files):
        base=files['root'];root=base/'inputs';root.mkdir(mode=0o700);capture=root/'.capture-v1';capture.mkdir(mode=0o700)
        cfg=json.loads((HERE/'prepare-contract.json').read_bytes());cfg['execution_targets']=[str(base/n) for n in ['postflight','runner','launch']]
        cfg['previous_staging']=str(base/'previous-staging')
        binary=b'\x7fELF\x02\x01'+b'\x00'*12+struct.pack('<H',62)+b'\x00'*44
        p=Path(cfg['previous_staging']);p.write_bytes(binary);p.chmod(0o600)
        contract=copy.deepcopy(e.CONTRACT);contract['authority_path']=str(root/'execution-authority-v2.json');contract['seal_path']=str(root/'lineage-seal.json')
        contract['previous']['path']=str(root/'previous');contract['previous']['size']=len(binary)
        pins=dict(e.PINS,previous=a.sha(binary))
        started=s.utc();seal=c.capture_exact(state,inputs);seal.update(P10_complete=False,release_accepted=False)
        raw=(json.dumps(seal,indent=2)+'\n').encode();seal_sha=a.sha(raw);s.exclusive(Path(contract['seal_path']),raw)
        intent={'schema':'crg-capture-save-intent-v1','entry':cfg['capture_entry'],'adapter_sha256':cfg['capture_sha256'],
            'saver_sha256':cfg['saver_sha256'],'contract_sha256':cfg['saver_contract_sha256'],'started_utc':started,'automatic_retry_allowed':False}
        receipt={'schema':'crg-capture-save-receipt-v1','phase':'saved-lineage-not-accepted','seal_path':contract['seal_path'],
            'seal_sha256':seal_sha,'seal_bytes':len(raw),'adapter_sha256':cfg['capture_sha256'],'capture_saved':True,
            'actual_duration_accepted':False,'postflight_allowed':False,'P10_complete':False,'release_accepted':False,'automatic_retry_allowed':False,
            'capture_utc':seal['capture_utc'],'saved_utc':s.utc()}
        s.save_json(capture/'intent.json',intent);s.save_json(capture/'receipt.json',receipt);receipt_sha=a.sha((capture/'receipt.json').read_bytes())
        state['phase']='component-accepted'
        with patch.object(e,'CONTRACT',contract),patch.object(e,'PINS',pins),patch.object(e,'checked_contract'),patch.object(e.lineage,'component',return_value=(state,inputs)),patch.object(e.lineage,'readiness',return_value={'postflight_allowed':True}),patch.object(e,'no_other_mounts'),patch.object(e,'readiness',return_value=({'postflight_allowed':True},{'controlled':True})),patch.object(a,'checked_sources'):
            yield root,cfg,seal_sha,receipt_sha


class Checks(unittest.TestCase):
    def test_original_pending_default_and_prepare_touch_no_input(self):
        dummy=types.SimpleNamespace(checked_contract=lambda:None,lineage=types.SimpleNamespace(component=lambda:({'phase':'pending'},None)))
        for args in [[],['--prepare']]:
            with patch.object(a,'load_runtime',return_value=(dummy,None,None,{})),patch.object(a.sys,'platform','linux'),patch.object(a.os,'geteuid',return_value=0,create=True),patch.object(a,'prepare_once') as prepare,contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(a.main(args),2);prepare.assert_not_called()
            self.assertFalse(json.loads(out.getvalue())['prepared'])

    def test_terminal_without_both_trusted_digests_stays_readonly_pending(self):
        dummy=types.SimpleNamespace(checked_contract=lambda:None,lineage=types.SimpleNamespace(component=lambda:({'phase':'component-accepted'},None)))
        result,proof=a.inspect(dummy,None,None,{})
        self.assertEqual(result['phase'],'pending');self.assertIsNone(proof)

    def test_partial_or_execute_cli_rejected(self):
        for args in [['--seal-sha256','a'*64],['--execute'],['--directory','/var/tmp']]:
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):a.main(args)

    def test_ready_default_is_readonly(self):
        with patch.object(a,'load_runtime',return_value=(None,None,None,{})),patch.object(a,'inspect',return_value=({'phase':'ready-to-prepare'},{})),patch.object(a.sys,'platform','linux'),patch.object(a.os,'geteuid',return_value=0,create=True),patch.object(a,'prepare_once') as prepare,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(a.main([]),0);prepare.assert_not_called()

    @unittest.skipUnless(LINUX,'Linux original authority reader and real0600/atomic publication')
    def test_prepared_exact_original_authority_checker_no_extra_metadata(self):
        with fixture() as (root,cfg,seal,receipt):
            result=a.prepare_once(e,s,c,cfg,seal,receipt)
            self.assertEqual(result['phase'],'prepared-not-executed');self.assertFalse(result['actual_postflight_executed'])
            value=e.checked_authority(Path(result['authority_path']),result['authority_sha256'])
            self.assertEqual(value,a.authority_value(e,seal));self.assertNotIn('ended_utc',value)
            self.assertEqual((root/'previous').stat().st_mode&0o777,0o600)
            self.assertEqual(Path(result['authority_path']).stat().st_mode&0o777,0o600)
            self.assertEqual((root/a.ATTEMPT).stat().st_mode&0o777,0o700)

    @unittest.skipUnless(LINUX,'Linux real no-replace preparation')
    def test_duplicate_keeps_original_files(self):
        with fixture() as (root,cfg,seal,receipt):
            a.prepare_once(e,s,c,cfg,seal,receipt);before={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with self.assertRaisesRegex(ValueError,'PREPARATION_INPUT_ALREADY_EXISTS'):a.prepare_once(e,s,c,cfg,seal,receipt)
            self.assertEqual(before,{p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()})

    @unittest.skipUnless(LINUX,'Linux actual private capture files')
    def test_separately_trusted_seal_and_receipt_hashes_required(self):
        with fixture() as (root,cfg,seal,receipt):
            for x,y,reason in [('0'*64,receipt,'TRUSTED_SEAL_SHA'),(seal,'0'*64,'TRUSTED_CAPTURE_RECEIPT_SHA')]:
                with self.assertRaisesRegex(ValueError,reason):a.prepare_once(e,s,c,cfg,x,y)
            self.assertFalse((root/a.ATTEMPT).exists())

    @unittest.skipUnless(LINUX,'Linux actual capture origin binding')
    def test_wrong_capture_origin_never_creates_attempt(self):
        with fixture() as (root,cfg,seal,receipt):
            path=root/'.capture-v1/intent.json';value=json.loads(path.read_bytes());value['saver_sha256']='0'*64;path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,'CAPTURE_INTENT_SOURCE'):a.prepare_once(e,s,c,cfg,seal,receipt)
            self.assertFalse((root/a.ATTEMPT).exists())

    @unittest.skipUnless(LINUX,'Linux actual previous file corruption and legacy exclusion')
    def test_corrupt_or_legacy_previous_is_rejected_before_writes(self):
        with fixture() as (root,cfg,seal,receipt):
            Path(cfg['previous_staging']).write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'HIGH_COMPATIBLE_PREVIOUS_CONTENT'):a.prepare_once(e,s,c,cfg,seal,receipt)
            self.assertFalse((root/a.ATTEMPT).exists())
        with fixture() as (root,cfg,seal,receipt):
            e.CONTRACT['original_legacy_previous']['sha256']=e.PINS['previous']
            with self.assertRaisesRegex(ValueError,'HIGH_COMPATIBLE_PREVIOUS_CONTENT'):a.prepare_once(e,s,c,cfg,seal,receipt)
            self.assertFalse((root/a.ATTEMPT).exists())

    @unittest.skipUnless(LINUX,'Linux original lineage admission boundary')
    def test_retained_lineage_failure_prevents_preparation(self):
        with fixture() as (root,cfg,seal,receipt),patch.object(e.lineage,'readiness',return_value={'postflight_allowed':False}):
            with self.assertRaisesRegex(ValueError,'REAL_RETAINED_LINEAGE_NOT_READY'):a.prepare_once(e,s,c,cfg,seal,receipt)
            self.assertFalse((root/a.ATTEMPT).exists())

    @unittest.skipUnless(LINUX,'Linux actual partial publication retained')
    def test_authority_publication_failure_retains_previous_guard_and_error(self):
        with fixture() as (root,cfg,seal,receipt):
            actual=s.publish_noreplace
            def fail(source,dest):
                if dest.name=='execution-authority-v2.json':raise OSError('controlled authority publication failure')
                actual(source,dest)
            with patch.object(s,'publish_noreplace',side_effect=fail),self.assertRaises(OSError):a.prepare_once(e,s,c,cfg,seal,receipt)
            self.assertTrue((root/'previous').exists());self.assertTrue((root/a.ATTEMPT/'error.json').exists())
            self.assertFalse((root/'execution-authority-v2.json').exists())
            with self.assertRaisesRegex(ValueError,'PREPARATION_INPUT_ALREADY_EXISTS'):a.prepare_once(e,s,c,cfg,seal,receipt)

    @unittest.skipUnless(LINUX,'Linux exact original authority schema')
    def test_original_checker_rejects_extra_authority_metadata(self):
        with fixture() as (root,cfg,seal,receipt):
            value=a.authority_value(e,seal);value['ended_utc']=s.utc();path=Path(e.CONTRACT['authority_path']);s.save_json(path,value)
            with self.assertRaisesRegex(e.Rejected,'AUTHORITY_EXACT_BINDINGS'):e.checked_authority(path,a.sha(path.read_bytes()))

    @unittest.skipUnless(LINUX,'Linux real source pins')
    def test_actual_dependency_source_hash_guard(self):
        with fixture() as (root,cfg,seal,receipt):
            path=root/'source.py';path.write_bytes(b'pinned');check={'source_sets':{str(root):{'source.py':a.sha(b'pinned')}}}
            actual_sources(check);path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'FROZEN_PREPARATION_SOURCE'):actual_sources(check)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    print(json.dumps({'schema':'crg-aged-prepare-checks-v1','phase':'passed' if result.wasSuccessful() else 'failed',
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
        'scope':'controlled capture/terminal/lineage/previous ELF fixtures and real private files/noreplace plus original checked_authority; not actual aged data or managed resume',
        'actual_authority_created':False,'actual_managed_resume_accepted':False,'actual_postflight_executed':False,'release_accepted':False},indent=2));sys.exit(0 if result.wasSuccessful() else 1)
