#!/usr/bin/env python3
"""Controlled capture plumbing tests. Fake proc/Pod inventory is never real age."""
import contextlib,copy,hashlib,importlib.util,inspect,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('capture_adapter_v3',HERE/'capture-v3.py')
c=importlib.util.module_from_spec(spec);sys.modules[spec.name]=c;spec.loader.exec_module(c)


def acceptance_context():
    state={'phase':'pending','capture_allowed':True,'runner_identity_verified_live':True,
        'reports':{n:{'audit':{'phase':'passed'},'sha256':d*64} for n,d in [('baseline','a'),('enforce','b')]}}
    inputs=({}, {'pid':100,'start_ticks':200,'entry':'fixture'},
        {'namespace_uid':'owned','phases':{n:{'native_accepted':True} for n in ['baseline','enforce']}}, {'phase':'measuring'})
    return state,inputs


@contextlib.contextmanager
def disk_fixture():
    with tempfile.TemporaryDirectory(prefix='crg-capture-v3-fixture-') as temp:
        root=Path(temp);proc=root/'proc';groups=root/'groups';groups.mkdir();proc.mkdir()
        binding=dict(c.BINDING,component_root=str(root),binary_sha256=hashlib.sha256(b'agent').hexdigest(),cache_sha256=hashlib.sha256(b'cache').hexdigest())
        state,inputs=acceptance_context();bridge,launch,outer,campaign=inputs
        bridge.update(helper_sha256={'examples/optional-agent.sh':hashlib.sha256(b'optional').hexdigest()},private_original_fixture_sha256={})
        outer['roles']={};campaign['roles']={};pods={};group_by_pid={};pid_by_cid={};folders={}
        controls={'cpu.max':'720000 100000','memory.max':'21474836480','memory.high':'20001980416',
            'memory.swap.max':'max','pids.max':'max','cpu.weight':'100','io.weight':'default 100',
            'io.max':'8:0 rbps=67108864 wbps=67108864 riops=4096 wiops=4096'}
        for index,role in enumerate(['dbs','hisdbs']):
            folder=root/'fixture'/(role+'-business');folders[role]=folder;folder.mkdir(parents=True)
            for name in c.DIRECTORIES:(folder/name).mkdir()
            supervisor=('supervisor-'+role).encode();bridge['private_original_fixture_sha256']['fixture/'+role+'/supervisor.sh']=hashlib.sha256(supervisor).hexdigest()
            for name in c.immutable_files(role):
                data={'crg/crg':b'agent','crg/optional-agent.sh':b'optional','ccg/bin/containercacheguard':b'cache','ccg/scripts/business-supervisor.sh':supervisor}.get(name,b'isolated-input')
                p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);p.chmod(0o600)
            cid=hashlib.sha256((role+'main').encode()).hexdigest();dcs=hashlib.sha256((role+'aux').encode()).hexdigest()
            main_pid=1000+index*10;aux_pid=main_pid+1
            main=groups/(role+'-main');aux=groups/(role+'-aux');main.mkdir();aux.mkdir();group_by_pid.update({main_pid:main,aux_pid:aux});pid_by_cid.update({cid:main_pid,dcs:aux_pid})
            pids=[101+index*100,102+index*100,103+index*100]
            (main/'cgroup.procs').write_text('\n'.join(map(str,pids)))
            for name,value in controls.items():(main/name).write_text(value+'\n')
            for pid,argv,data in [(pids[0],[b'/opt/crg/crg',b'run'],b'agent'),(pids[1],[b'/opt/ccg/bin/containercacheguard',b'run'],b'cache'),(pids[2],[b'/usr/bin/python',('/tmp/crg-soak-load-'+binding['seven_day_run_id']+'.py').encode()],b'worker')]:
                p=proc/str(pid);p.mkdir();(p/'cmdline').write_bytes(b'\0'.join(argv)+b'\0');(p/'exe').write_bytes(data)
            pods[role]={'metadata':{'uid':'owned-'+role,'labels':{'managed-by':'crg-vendor-test'}},'spec':{},
                'status':{'containerStatuses':[{'name':role,'restartCount':0,'containerID':'containerd://'+cid},{'name':'isolated-dcs','restartCount':0,'containerID':'containerd://'+dcs}]}}
            identity=role+'-identity';status={'state':'managed','plan':{'environment':{'identity':identity}},'items':[{'file':n,'state':'applied'} for n in ['cpu.max','memory.high','io.max']]}
            for name,value in [('status.json',status),('journal.json',{'version':1,'identity':identity})]:
                p=folder/'resource-state'/name;p.write_text(json.dumps(value));p.chmod(0o600)
            load=folder/'postgresql/basebackup'/('crg-soak-'+binding['seven_day_run_id'])/'load.json';load.parent.mkdir(parents=True)
            load.write_text(json.dumps({'phase':'running','requested_duration_seconds':604800,'run_id':binding['seven_day_run_id'],
                'started_utc':'2026-11-18T05:00:00+00:00','primary_start_time_initial':'same-primary'}))
            log=folder/'log/crg/crg-2026-11-18.log';log.parent.mkdir();log.write_text('fixture\n');log.chmod(0o600)
            original=dict(controls);original.update({'cpu.max':'800000 100000','memory.high':'max','io.max':''})
            outer['roles']['candidate1-'+role+'-bw64']={'enforce_controls':dict(controls),'original_controls':original}
            campaign['roles'][role]={'fixed_controls':dict(controls)}
        def command(args):
            if args[0]=='kubectl' and args[1:3]==['get','pod']:return json.dumps(pods[args[5].removesuffix('-business')])
            if args[:2]==['crictl','inspect']:return json.dumps({'info':{'pid':pid_by_cid[args[2]]}})
            raise AssertionError('unexpected inventory '+repr(args))
        def group(pid,cid):
            assert pid_by_cid[cid]==pid;return group_by_pid[pid]
        def path(*parts):return Path(proc,*parts[1:]) if str(parts[0])=='/proc' else Path(*parts)
        with patch.object(c,'BINDING',binding),patch.object(c,'Path',side_effect=path),patch.object(c,'namespace',return_value={'metadata':{'uid':'owned','labels':{'managed-by':'crg-vendor-test'}}}),patch.object(c,'command',side_effect=command),patch.object(c,'group',side_effect=group):
            yield state,inputs,{'root':root,'folders':folders,'pods':pods,'groups':group_by_pid,'proc':proc}


class Checks(unittest.TestCase):
    def test_frozen_old_roles_failure_reproduced_without_real_inventory(self):
        state,inputs=acceptance_context()
        meta={'metadata':{'uid':'owned','labels':{'managed-by':'crg-vendor-test'}}}
        with patch.object(c.g,'namespace',return_value=meta),self.assertRaisesRegex(KeyError,'roles'):c.g.capture(state,inputs)

    def test_frozen_old_missing_path_clean_failure_reproduced(self):
        state,inputs=acceptance_context();p=dict(c.BINDING,run_id=c.BINDING['seven_day_run_id'],roles=['dbs','hisdbs'])
        meta={'metadata':{'uid':'owned','labels':{'managed-by':'crg-vendor-test'}}}
        with patch.object(c.g,'namespace',return_value=meta),self.assertRaisesRegex(NameError,'path_clean'):c.g.capture_core(p,c.BINDING_SHA256,state,inputs)

    def test_original_capture_body_and_single_plan_repair_preserved(self):
        self.assertEqual(inspect.getsource(c.capture_core).strip(),inspect.getsource(c.g.capture_core).strip())
        original=inspect.getsource(c.g.capture).replace('def capture(','def capture_exact(',1).replace("p = dict(BINDING, run_id=BINDING['seven_day_run_id'])","p = dict(BINDING, run_id=BINDING['seven_day_run_id'], roles=['dbs', 'hisdbs'])")
        self.assertEqual(inspect.getsource(c.capture_exact).strip(),original.strip())
        self.assertIs(c.path_clean,c.g.base.path_clean)

    def test_neither_baseline_nor_enforce_can_capture(self):
        state,inputs=acceptance_context();state['capture_allowed']=False
        with patch.object(c,'capture_core',side_effect=AssertionError('late capture')),self.assertRaisesRegex(c.Rejected,'CAPTURE_ONLY_DURING_FRESH_SEVEN_DAY'):c.capture_exact(state,inputs)

    def test_both_original24h_must_be_accepted(self):
        for phase in ['baseline','enforce']:
            state,inputs=acceptance_context();inputs[2]['phases'][phase]['native_accepted']=False
            with self.subTest(phase=phase),patch.object(c,'capture_core',side_effect=AssertionError('late capture')),self.assertRaisesRegex(c.Rejected,'CAPTURE_REQUIRES_BOTH_ORIGINAL24H'):c.capture_exact(state,inputs)

    @unittest.skipUnless(sys.platform=='linux','real0600 complete fixture is executed on native Linux')
    def test_full_controlled_capture_keeps_original_schema_and_checks_all_actual_files(self):
        with disk_fixture() as (state,inputs,fixture):
            value=c.capture_exact(state,inputs)
            self.assertEqual(value['schema'],'crg-aged-lineage-seal-v1');self.assertEqual(value['plan_sha256'],c.BINDING_SHA256)
            self.assertEqual(value['phase'],'lineage-captured-not-accepted');self.assertFalse(value['postflight_allowed'])
            self.assertEqual(set(value['roles']),{'dbs','hisdbs'});self.assertTrue(value['seal_is_not_acceptance'])
            for role,row in value['roles'].items():
                self.assertEqual(set(row['files']),set(c.immutable_files(role)));self.assertEqual(set(row['directories']),set(c.DIRECTORIES))
                self.assertEqual(row['controls']['memory.high'],'20001980416');self.assertEqual(row['controls']['memory.max'],'21474836480')

    @unittest.skipUnless(sys.platform=='linux','real0600 full guarded fault fixtures are executed on native Linux')
    def test_controlled_capture_still_rejects_original_faults(self):
        def bad_native(f):
            path=next((f['folders']['dbs']/'postgresql/basebackup').glob('*/load.json'));value=json.loads(path.read_bytes());value['phase']='passed';path.write_text(json.dumps(value))
        faults=[(lambda f:f['pods']['dbs']['status']['containerStatuses'][0].update(restartCount=1),'CONTAINER_SET_OR_RESTART'),
            (lambda f:(f['proc']/'101/exe').write_bytes(b'wrong'),'ONE_SOURCE_QUALIFIED_PROCESS_EACH'),
            (lambda f:(f['folders']['dbs']/'resource-state/journal.json').chmod(0o644),'AGED_RESOURCE_STATE'),
            (lambda f:(f['folders']['dbs']/'ccg/bin/containercacheguard').write_bytes(b'wrong'),'AGED_PROGRAM_SOURCE'),
            (bad_native,'NATIVE_RUNNING')]
        for fault,reason in faults:
            with self.subTest(reason=reason),disk_fixture() as (state,inputs,fixture):
                fault(fixture)
                with self.assertRaisesRegex(c.Rejected,reason):c.capture_exact(state,inputs)

    def test_default_pending_and_no_execute_argument(self):
        with patch.object(c.g,'component',return_value=({'phase':'pending'},None)),patch.object(c.sys,'platform','linux'),patch.object(c.os,'geteuid',return_value=0,create=True),contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(c.main([]),2)
        self.assertEqual(json.loads(out.getvalue())['phase'],'pending')
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):c.main(['--execute'])


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    print(json.dumps({'schema':'crg-capture-v3-checks-v1','phase':'passed' if result.wasSuccessful() else 'failed','tests_run':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'synthetic_only':True,
        'real_seven_day_seal_created':False,'release_accepted':False},indent=2));sys.exit(0 if result.wasSuccessful() else 1)
