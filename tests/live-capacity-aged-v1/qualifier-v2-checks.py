#!/usr/bin/env python3
"""Synthetic-only report tampering and real temporary-file read-only audit tests."""
import contextlib,copy,datetime,hashlib,importlib.util,io,json,sys,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('aged_qualifier_v2',HERE/'qualify-v2.py')
q=importlib.util.module_from_spec(spec);sys.modules[spec.name]=q;spec.loader.exec_module(q)
spec=importlib.util.spec_from_file_location('aged_v2_fixtures',HERE/'executor-v2-checks.py')
f=importlib.util.module_from_spec(spec);sys.modules[spec.name]=f;spec.loader.exec_module(f)


def fixture():
    C=q.C;component={'phase':'component-accepted','reports':{n:{'sha256':str(i)*64,'audit':{'phase':'passed'}} for i,n in enumerate(['baseline','enforce','acceptance'],1)}}
    launch={'pid':100,'start_ticks':200,'entry':'original-only'};acceptance={'roles':{}}
    seal={'schema':'crg-aged-lineage-seal-v1','seal_is_not_acceptance':True,'plan_sha256':q.e.lineage.BINDING_SHA256,
        'source_revision':C['source_revision'],'binary_sha256':C['binary_sha256'],'launch':launch,'roles':{},
        'fresh_three_phase_binding':{'binding_sha256':q.e.lineage.BINDING_SHA256,'long_plan_sha256':q.B['long_plan_sha256'],
            'baseline_report_sha256':'1'*64,'enforce_report_sha256':'2'*64}}
    report={'schema':'crg-source37-aged-execution-report-v2','phase':'passed','mode':'seven-day-postflight',
        'source_revision':C['source_revision'],'binary_sha256':C['binary_sha256'],'embedded_version':'v1.0.0',
        'executor_sha256':q.EXECUTOR_SHA,'contract_sha256':q.e.CONTRACT_SHA,'authority_sha256':'a'*64,
        'criteria':C['criteria'],'immutable_template_sha256':C['original_template_sha256'],
        'user_rollback_scope':C['user_rollback_scope'],'maintenance_scope':C['previous']['scope'],
        'original_legacy_managed_resume_accepted':False,'P10_complete':False,'release_accepted':False,
        'postflight_executed':True,'namespace_absent':True,'aged_fixture_retained':True,
        'tests':[{'name':n,'passed':True} for n in q.expected_checks()],
        'readiness':{'component':component,'postflight_allowed':True,'authority_sha256':'a'*64,'contract_sha256':q.e.CONTRACT_SHA},
        'roles':{},'ended_utc':'2026-11-25T06:00:00+00:00'}
    def meta(i,size=20):return {'sha256':hashlib.sha256(str(i).encode()).hexdigest(),'size':size,'device':1,'inode':i,'mode':0o600}
    def journal(identity):return {'version':1,'identity':identity,'target':'/sys/fs/cgroup','mutations':{n:{'file':n} for n in ['cpu.max','memory.high','io.max']}}
    for index,role in enumerate(['dbs','hisdbs']):
        dirs={n:{'device':1,'inode':100+index*100+i} for i,n in enumerate(q.gate.DIRECTORIES)}
        files={n:meta(1000+index*100+i) for i,n in enumerate(q.gate.immutable_files(role))}
        prefixes={f'crg-2026-11-{n:02d}.log':meta(2000+index*100+n) for n in range(18,25)}
        sealed={'directories':dirs,'files':files,'journal_identity':role+'-old','log_prefixes':prefixes};seal['roles'][role]=sealed
        checksum=[16384,134225920,67108864,'1'*32,999];checksum_string='|'.join(map(str,checksum))
        acceptance['roles'][role]={'workload':{'final_checksum':checksum}}
        boots=[];start=datetime.datetime.fromisoformat('2026-11-25T04:00:00+00:00')+datetime.timedelta(minutes=index*20)
        for n,phase in enumerate(['aged-reopen','same-data-new-Pod']):
            uid=str(uuid.UUID(int=index*10+n+1));cid=hashlib.sha256((role+phase).encode()).hexdigest()
            original=dict.fromkeys(q.gate.CONTROLS,'max');original.update({'cpu.max':'800000 100000','memory.max':'21474836480','memory.high':'max','io.max':'','cpu.weight':'100','io.weight':'default 100'})
            active=dict(original);active.update({'cpu.max':'720000 100000','memory.high':'20001980416','io.max':'8:0 rbps=67108864 wbps=67108864 riops=4096 wiops=4096'})
            identity=role+'-'+str(n)
            status={'state':'managed','plan':{'environment':{'identity':identity}},'items':[{'file':x,'state':'applied'} for x in ['cpu.max','memory.high','io.max']]}
            boots.append({'phase':phase,'network_isolated_before_start':True,'ready_seconds':20,'cache_after_ready_seconds':1,
                'runtime_original_controls':original,'active_controls':active,'managed_status':status,'identity':identity,
                'agents':[[100+index*10+n,200+index*10+n,C['binary_sha256']]],'caches':[[300+index*10+n,400+index*10+n,C['cache_sha256']]],
                'pid1_start_ticks':str(500+index*10+n),'container_id':cid,'pod_uid':uid,
                'cgroup':'/sys/fs/cgroup/kubepods.slice/kubepods-pod'+uid.replace('-','_')+'.slice/cri-containerd-'+cid+'.scope',
                'primary_start':(start-datetime.timedelta(minutes=10-n)).isoformat(),'ready_epoch':start.timestamp()-10})
        second=boots[1];native=f.native();native.update(run_id=C['run_id']+str(index),primary_start_time_initial=second['primary_start'],primary_start_time_final=second['primary_start'],started_utc=start.isoformat(),measurement_finished_utc=(start+datetime.timedelta(seconds=600.1)).isoformat())
        for kind,period in [('sql',2),('api',5)]:native[kind]['sample_coverage']=native[kind]['attempts']/(600/period)
        fixed={'controls':second['active_controls'],'journal_sha256':'3'*64,'pid1_start_ticks':second['pid1_start_ticks'],
            'caches':second['caches'],'primary_start':second['primary_start'],'aged_checksum':checksum_string}
        intervals=[]
        for i,(command,state) in enumerate(zip(q.COMMANDS,q.STATES)):
            expected=C['previous']['sha256'] if i in [1,3,4,5] else C['binary_sha256']
            row={k:copy.deepcopy(fixed[k]) for k in ['controls','journal_sha256','pid1_start_ticks','caches']}
            row.update(command=command,started_epoch=start.timestamp()+i*10+1,ended_epoch=start.timestamp()+i*10+2,result={'state':state},program_sha256=expected)
            if i in [4,7]:row['status_stamp_before_enable']=[1,2+i,3]
            intervals.append(row)
        resumes=[]
        for i,expected in zip([4,7],[C['previous']['sha256'],C['binary_sha256']]):
            resumes.append({'expected_sha256':expected,'agents':[[600+i,700+i,expected]],'status_stamp_before_enable':intervals[i]['status_stamp_before_enable'],
                'status_stamp_after_resume':[4,100+i,6],'managed_status':copy.deepcopy(second['managed_status']),
                'controls':copy.deepcopy(fixed['controls']),'journal_sha256':fixed['journal_sha256'],'observed_epoch':intervals[i]['ended_epoch']+1})
        afterlogs=copy.deepcopy(prefixes);afterlogs[next(iter(afterlogs))]['size']+=10
        item={'phase':'postflight-component-passed','boots':boots,'first_previous_journal':journal(sealed['journal_identity']),
            'second_previous_journal':journal(boots[0]['identity']),
            'before':{'directories':dirs,'immutable_files':{k:v for k,v in files.items() if k!='crg/crg'},'log_prefixes':prefixes,'aged_native_final_checksum':checksum},
            'after':{'directories':copy.deepcopy(dirs),'immutable_files':{k:copy.deepcopy(v) for k,v in files.items() if k!='crg/crg'},'program_sha256':C['binary_sha256'],
                'preserved_log_prefixes':copy.deepcopy(prefixes),'log_files':afterlogs},
            'aged_checksum_reopened':checksum_string,'aged_checksum_after_maintenance':checksum_string,
            'restore_evidence':{'database':'crg_aged_restore_'+C['run_id'],'restored_checksum':checksum_string,'source_checksum':checksum_string},
            'logical_backup':{'digest':meta(5000+index,100),'listing':'TABLE DATA crg_soak_'+q.B['seven_day_run_id']+' fixture'},
            'native':native,'maintenance_intervals':intervals,'maintenance_evidence':{'before':fixed,'resumptions':resumes,
                'after':{**{k:copy.deepcopy(fixed[k]) for k in ['controls','journal_sha256','pid1_start_ticks','caches']},'memory_events':{'oom_kill':'0'}}},
            'disable_evidence':{'result':{'state':'restored','mode':'disable','plan':{'environment':{'identity':second['identity']}},
                'items':[{'file':n,'state':'restored'} for n in ['cpu.max','memory.high','io.max']]},'actual_controls':second['runtime_original_controls'],
                'memory_events':{'oom_kill':'0'},'journal':{'version':1,'identity':second['identity'],'target':'/sys/fs/cgroup','mutations':{}}}}
        report['roles'][role]=item
    receipt={'schema':'crg-source37-aged-exit-v2','exit':0,'entry':q.ENTRY,'executor_sha256':q.EXECUTOR_SHA,
        'authority_sha256':'a'*64,'contract_sha256':q.e.CONTRACT_SHA,'report_sha256':'d'*64,
        'pid':900,'start_ticks':901,'elapsed_seconds':1300,'ended_utc':'2026-11-25T06:00:01+00:00'}
    # Real reports/seals are separately parsed JSON objects, not aliased fixtures.
    return json.loads(json.dumps([report,'d'*64,'a'*64,component,({},launch,{},acceptance),seal,receipt]))


class Checks(unittest.TestCase):
    def rejected(self,mutate,reason):
        args=copy.deepcopy(fixture());mutate(args)
        with self.assertRaisesRegex(q.Rejected,reason):q.audit(*args)

    def test_complete_synthetic_report_is_component_only(self):
        value=q.audit(*fixture());self.assertEqual(value['original_named_checks'],36)
        self.assertFalse(value['actual_disk_and_cleanup_verified']);self.assertFalse(value['release_accepted'])

    def test_every_named_result_required_ordered_unique_and_boolean(self):
        for i in range(36):
            with self.subTest(i=i):self.rejected(lambda a:a[0]['tests'][i].update(passed=1),'EXACT_ORIGINAL36_CHECKS')
        self.rejected(lambda a:a[0]['tests'].pop(),'EXACT_ORIGINAL36_CHECKS')
        self.rejected(lambda a:a[0]['tests'].reverse(),'EXACT_ORIGINAL36_CHECKS')

    def test_source_criteria_and_real_exit_binding(self):
        for key in ['source_revision','binary_sha256','executor_sha256','contract_sha256','authority_sha256','embedded_version']:
            with self.subTest(key=key):self.rejected(lambda a:a[0].update({key:'wrong'}),'REPORT_SOURCE_AND_CONTRACT')
        self.rejected(lambda a:a[0].update(criteria={}), 'REPORT_SOURCE_AND_CONTRACT')
        for key,value in [('exit',False),('report_sha256','wrong'),('entry','old-source'),('elapsed_seconds',1199),('start_ticks',True)]:
            with self.subTest(key=key):self.rejected(lambda a:a[6].update({key:value}),'ACTUAL_EXIT_RECEIPT')

    def test_cleanup_or_source_transfer_and_legacy_claim_cannot_be_waived(self):
        self.rejected(lambda a:a[0].update(namespace_absent=False),'TERMINAL_AND_CLEANUP')
        self.rejected(lambda a:a[0].update(original_legacy_managed_resume_accepted=True),'USER_HIGH_ONLY_SCOPE')
        self.rejected(lambda a:a[5]['fresh_three_phase_binding'].update(long_plan_sha256='old'),'ACTUAL_SEAL_BINDING')

    def test_raw_restore_backup_and_aged_counter_checked_even_all_flags_true(self):
        self.rejected(lambda a:a[0]['roles']['dbs']['restore_evidence'].update(restored_checksum='wrong'),'ACTUAL_AGED_RESTORE_AND_COUNTER')
        self.rejected(lambda a:a[0]['roles']['hisdbs'].update(aged_checksum_after_maintenance='wrong'),'ACTUAL_AGED_RESTORE_AND_COUNTER')
        self.rejected(lambda a:a[0]['roles']['dbs']['logical_backup'].update(listing='unrelated'),'ACTUAL_LOGICAL_BACKUP')

    def test_exact_high_and_each_external_control_checked(self):
        for name in q.C['unchanged_external_controls']+['cpu.max','memory.high','io.max']:
            with self.subTest(name=name):self.rejected(lambda a:a[0]['roles']['dbs']['boots'][0]['active_controls'].update({name:'changed'}),'MANAGED_HIGH_EXTERNAL_CONTROLS')
        self.rejected(lambda a:a[0]['roles']['dbs']['second_previous_journal']['mutations'].update({'memory.max':{'file':'memory.max'}}),'ENFORCED_HIGH_JOURNAL')

    def test_startup_cache_and_new_ID_are_real_fields(self):
        self.rejected(lambda a:a[0]['roles']['dbs']['boots'][0].update(ready_seconds=300.01),'STARTUP_CACHE_BUDGETS')
        self.rejected(lambda a:a[0]['roles']['dbs']['boots'][1].update(cache_after_ready_seconds=45.01),'STARTUP_CACHE_BUDGETS')
        self.rejected(lambda a:a[0]['roles']['dbs']['boots'][1].update(container_id=a[0]['roles']['dbs']['boots'][0]['container_id']),'NEW_POD_CONTAINER_GROUP_IDENTITIES')

    def test_original_native600_errors_coverage_histograms_and_checksum(self):
        for key,value,reason in [('elapsed_seconds',599,'NATIVE_COMPLETION'),('payload_integrity',False,'NATIVE_COMPLETION')]:
            self.rejected(lambda a:a[0]['roles']['dbs']['native'].update({key:value}),reason)
        self.rejected(lambda a:a[0]['roles']['dbs']['native']['sql'].update(errors=1),'NATIVE_SAMPLES')
        self.rejected(lambda a:a[0]['roles']['dbs']['native']['api'].update(max_seconds=5.1),'NATIVE_MAXIMUM')
        self.rejected(lambda a:a[0]['roles']['dbs']['native']['api'].update(sample_coverage=.5),'NATIVE_COVERAGE')

    def test_eight_maintenance_commands_states_sources_and_interval_order(self):
        self.rejected(lambda a:a[0]['roles']['dbs']['maintenance_intervals'].pop(),'EXACT_EIGHT_MAINTENANCE_OPERATIONS')
        self.rejected(lambda a:a[0]['roles']['dbs']['maintenance_intervals'][1]['result'].update(state='failed'),'MAINTENANCE_RAW_RESULTS')
        self.rejected(lambda a:a[0]['roles']['dbs']['maintenance_intervals'][1].update(program_sha256=q.C['binary_sha256']),'MAINTENANCE_RAW_RESULTS')
        self.rejected(lambda a:a[0]['roles']['dbs']['maintenance_intervals'][2].update(started_epoch=0),'MAINTENANCE_INTERVAL_ORDER')

    def test_resumed_process_without_fresh_managed_status_fails(self):
        self.rejected(lambda a:a[0]['roles']['dbs']['maintenance_evidence']['resumptions'][0].update(status_stamp_after_resume=[1,2,3]),'FRESH_RESUMPTION_EVIDENCE')
        self.rejected(lambda a:a[0]['roles']['dbs']['maintenance_evidence']['resumptions'][0]['managed_status'].update(state='degraded'),'FRESH_MANAGED_STATUS')
        self.rejected(lambda a:a[0]['roles']['dbs']['maintenance_evidence']['resumptions'][0].update(journal_sha256='wrong'),'FRESH_RESUMPTION_EVIDENCE')

    def test_disabled_controls_empty_journal_OOM_and_logs(self):
        self.rejected(lambda a:a[0]['roles']['dbs']['disable_evidence']['actual_controls'].update({'cpu.max':'changed'}),'DISABLE_ALL8_RESTORED_NO_OOM_EMPTY_JOURNAL')
        self.rejected(lambda a:a[0]['roles']['dbs']['disable_evidence']['journal'].update(mutations={'stale':1}),'DISABLE_ALL8_RESTORED_NO_OOM_EMPTY_JOURNAL')
        self.rejected(lambda a:a[0]['roles']['dbs']['disable_evidence']['memory_events'].update(oom_kill='1'),'DISABLE_ALL8_RESTORED_NO_OOM_EMPTY_JOURNAL')
        self.rejected(lambda a:a[0]['roles']['dbs']['after']['log_files'].clear(),'DAILY_LOG_PRESERVATION')

    def test_pending_returns_before_any_postflight_reads_and_has_no_execute_flag(self):
        with patch.object(q.e.lineage,'component',return_value=({'phase':'pending'},None)),patch.object(q.gate,'read_json',side_effect=AssertionError('late read')),patch.object(q,'retained_disk',side_effect=AssertionError('late inventory')):
            self.assertEqual(q.qualify()['phase'],'pending')
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):q.main(['--execute'])

    def test_no_report_or_no_proofs_is_pending_not_accepted(self):
        args=fixture()
        with patch.object(q.e.lineage,'component',return_value=(args[3],args[4])),patch.object(Path,'exists',return_value=False):
            self.assertEqual(q.qualify()['reason'],'POSTFLIGHT_REPORT_ABSENT')
        with patch.object(q.e.lineage,'component',return_value=(args[3],args[4])),patch.object(Path,'exists',return_value=True),patch.object(q.gate,'read_json',return_value=(args[0],'d'*64)):
            self.assertEqual(q.qualify()['reason'],'TRUSTED_ACTUAL_PROOFS_REQUIRED')

    def test_actual_cleanup_inventory_denies_namespace_and_group(self):
        args=fixture()
        with patch.object(q.gate,'namespace',return_value={'owned':'still here'}),self.assertRaisesRegex(q.Rejected,'ACTUAL_NAMESPACES_ABSENT'):q.retained_disk(args[0],args[5])
        with patch.object(q.gate,'namespace',return_value=None),patch.object(q.e,'no_other_mounts'),patch.object(q.gate,'path_clean',side_effect=Path),patch.object(Path,'exists',return_value=True),self.assertRaisesRegex(q.Rejected,'ACTUAL_NEW_GROUP_AND_PARENT_ABSENT'):q.retained_disk(args[0],args[5])

    def test_original_JSON_loader_rejects_duplicates_and_nonfinite(self):
        with tempfile.TemporaryDirectory(prefix='crg-aged-qualifier-json-') as folder:
            path=Path(folder)/'fixture.json'
            for raw,reason in [(b'{"a":1,"a":2}','DUPLICATE_JSON_KEY'),(b'{"a":NaN}','NONFINITE_JSON')]:
                path.write_bytes(raw)
                with self.assertRaisesRegex(q.Rejected,reason):q.gate.audit.load_report(path)

    @unittest.skipUnless(sys.platform=='linux','real0600 inode/digest test requires Linux; exercised on native node')
    def test_actual_temporary_files_checked_and_tampering_rejected(self):
        args=fixture();report,seal=args[0],args[5]
        with tempfile.TemporaryDirectory(prefix='crg-aged-qualifier-disk-') as temp:
            root=Path(temp);program=b'isolated-fixture-program'
            for role,item in report['roles'].items():
                folder=root/'fixture'/(role+'-business');folder.mkdir(parents=True)
                for name in q.gate.DIRECTORIES:(folder/name).mkdir()
                for name in q.gate.immutable_files(role):
                    p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(program if name=='crg/crg' else b'isolated-fixture');p.chmod(0o600)
                logs=folder/'log/crg';logs.mkdir()
                for name in item['before']['log_prefixes']:
                    p=logs/name;p.write_bytes(b'prefix-appended');p.chmod(0o600)
                prefixes={p.name:q.gate.digest(p,6) for p in logs.iterdir()}
                seal['roles'][role]['log_prefixes']=prefixes;item['before']['log_prefixes']=copy.deepcopy(prefixes)
                seal['roles'][role]['directories']={name:q.gate.directory(folder/name) for name in q.gate.DIRECTORIES}
                item['after']['immutable_files']={name:q.gate.digest(folder/name) for name in q.gate.immutable_files(role) if name!='crg/crg'}
                for name,value in [('journal.json',item['disable_evidence']['journal']),('journal.previous.json',item['second_previous_journal']),('disabled.json',{'version':1,'identity':item['boots'][1]['identity']})]:
                    p=folder/'resource-state'/name;p.write_text(json.dumps(value));p.chmod(0o600)
                backup=folder/'postgresql/basebackup'/('crg-aged-'+q.C['run_id']+'.dump');backup.parent.mkdir(parents=True);backup.write_bytes(b'isolated-backup');backup.chmod(0o600);item['logical_backup']['digest']=q.gate.digest(backup)
                load=backup.parent/('crg-soak-'+q.C['run_id']+('0' if role=='dbs' else '1'))/'load.json'
                load.parent.mkdir();load.write_text(json.dumps(item['native']));load.chmod(0o600)
            with patch.dict(q.B,component_root=str(root)),patch.dict(q.C,binary_sha256=hashlib.sha256(program).hexdigest()),patch.object(q.gate,'namespace',return_value=None),patch.object(q.e,'no_other_mounts'):
                q.retained_disk(report,seal)
                config=root/'fixture/dbs-business/crg-config/config.json';original=config.read_bytes();config.write_bytes(b'tampered')
                with self.assertRaisesRegex(q.Rejected,'ACTUAL_IMMUTABLE_INPUT'):q.retained_disk(report,seal)
                config.write_bytes(original)
                journal=root/'fixture/dbs-business/resource-state/journal.json';saved=journal.read_bytes();changed=json.loads(saved);changed['mutations']={'stale':1};journal.write_text(json.dumps(changed))
                with self.assertRaisesRegex(q.Rejected,'ACTUAL_DISABLED_JOURNAL'):q.retained_disk(report,seal)
                journal.write_bytes(saved)
                log=next((root/'fixture/dbs-business/log/crg').iterdir());log.write_bytes(b'broken-appended')
                with self.assertRaisesRegex(q.Rejected,'ACTUAL_LOG_PREFIX'):q.retained_disk(report,seal)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    print(json.dumps({'schema':'crg-aged-qualifier-v2-checks-v1','phase':'passed' if result.wasSuccessful() else 'failed',
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'synthetic_only':True,
        'actual_postflight_accepted':False,'release_accepted':False},indent=2));sys.exit(0 if result.wasSuccessful() else 1)
