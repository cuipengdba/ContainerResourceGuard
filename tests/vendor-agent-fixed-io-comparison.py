#!/usr/bin/env python3
"""Frozen disposable DBS ABBA: same kernel limits, Agent active or paused.

Default CLI is inert. This static diagnostic does not replace original full32
reload/pressure/two-role acceptance. No product code or released asset changes.
"""
import argparse
import ast
import copy
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import textwrap
import time
import types
import uuid

sys.dont_write_bytecode = True
ROOT = Path('/var/tmp/crg-agent-activity435-20261111')
TOOLS = Path('/var/tmp/crg-agent-activity436-tools-20261111')
ORIGINAL_TOOLS = Path('/var/tmp/crg-memory342-tools-20261111')
HELPER_SHA = '30e92d64f2faede76efa115ebdedb0ec344567587b6c39c28bb1f8b7cc04de3d'
ACTIVITY_SHA = 'bd11d8617637336f6ed30c291764550657158d94db0d1cbff43bb86a982b569f'
QUALIFIED_SOURCE = 'db3b70a2b58f6817877f51af131cc7a328b2f8852ce515419f2b5af917d7ab7c'
QUALIFIED_REPORT = '882816c6f6ab8b12a611ef5cc1f0b3702946856b1fd56b1d2aac1d2db7c82417'
RUN = '20261111435'
ARMS = [('a1',False),('b1',True),('b2',True),('a2',False)]
FIXED = {'cpu.max':'720000 100000','memory.max':'20001980416',
 'io.max':'253:0 rbps=64700080 wbps=37470104 riops=83 wiops=135'}
POLICY = {'resource_mode':'manual','limits':{'cpu_cores':7.2,'memory_max':'20001980416B',
 'io_read_bps':'64700080B','io_write_bps':'37470104B','io_read_iops':83,'io_write_iops':135}}
MARKER = 'authorized-disposable-test-node-only'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def need(value, reason):
    if not value:
        raise ValueError(reason)


def load(path, digest, name):
    need(not path.is_symlink() and sha(path.read_bytes())==digest, 'FROZEN_SOURCE:'+path.name)
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def dependencies():
    helper=load(TOOLS/'vendor-write-iops-comparison.py',HELPER_SHA,'fixed_io_cold_clone_helper')
    module=helper.load_original()
    activity=load(TOOLS/'vendor-agent-activity-session.py',ACTIVITY_SHA,'fixed_io_agent_activity')
    return helper,module,activity


def derive(helper, module):
    """Counted AST removal of reload/pressure; native/engine criteria retained."""
    source=helper.ORIGINAL.read_text()
    cls=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='Execution')
    node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_business_native_original')
    before=textwrap.dedent('\n'.join(source.splitlines()[node.lineno-1:node.end_lineno]))+'\n'
    function=ast.parse(before).body[0]
    removed=[];kept=[];counts={'nested_functions':0,'reload_calls':0,'pressure_calls':0,'reload_overlap_assertions':0}
    for statement in function.body:
        kind=None
        if isinstance(statement,ast.FunctionDef) and statement.name in ['wait_policy','edge_interval','pressure30to20']:
            kind='nested_functions'
        elif isinstance(statement,ast.Expr) and isinstance(statement.value,ast.Call) and isinstance(statement.value.func,ast.Name):
            call=statement.value
            if call.func.id=='wait_policy':kind='reload_calls'
            elif call.func.id=='pressure30to20':kind='pressure_calls'
            elif call.func.id=='require' and len(call.args)>1 and isinstance(call.args[1],ast.Constant) and call.args[1].value=='NO_ENGINE_RELOAD_OVERLAP':kind='reload_overlap_assertions'
        if kind:
            counts[kind]+=1;removed.append({'kind':kind,'AST_sha256':sha(ast.dump(statement,include_attributes=False).encode())})
        else:kept.append(statement)
    need(counts=={'nested_functions':3,'reload_calls':9,'pressure_calls':1,'reload_overlap_assertions':1}, 'STATIC_DERIVATION_COUNTS')
    function.body=kept
    same=next(n for n in function.body if isinstance(n,ast.FunctionDef) and n.name=='same')
    need(len(same.body)==3 and isinstance(same.body[2],ast.If), 'SAME_DERIVATION_SHAPE')
    same.body.insert(2,ast.parse('self.activity_tick(row)').body[0])
    after=ast.unparse(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])))+'\n'
    need(after.count('len(intervals) == 11')==1 and after.count('600s-native-surrounds-reload-backup-stream-restore')==1, 'STATIC_COMPLETION_ASSERTION')
    after=after.replace('len(intervals) == 11','len(intervals) == 0').replace('600s-native-surrounds-reload-backup-stream-restore','600s-native-surrounds-fixed-limits-backup-stream-restore')
    scope=dict(module.__dict__)
    exec(compile(after,str(Path(__file__))+'::static-business','exec'),scope)
    return scope['_business_native_original'], {'original_method_sha256':sha(before.encode()),'derived_method_sha256':sha(after.encode()),
        'removed':removed,'counts':counts,'added':'matched Agent identity/state sample in same(); no resource control writes',
        'changed_completion':'static diagnostic requires zero reload intervals; engine/native600/SLA unchanged',
        'original32_not_executed_or_replaced':True}


def namespace(index):
    return 'crg-vendor-lab-agent-activity435'+str(index+1)+'-20261111'


def plan_value(helper,module):
    qualification=Path('/var/tmp/crg-agent-activity422-20261111/report.json')
    raw=qualification.read_bytes()
    need(sha(raw)==QUALIFIED_REPORT, 'FROZEN_VENDOR_QUALIFICATION_REPORT')
    return {'schema':'crg-agent-fixed-io-comparison-plan-v1','work_root':str(ROOT),'tool_root':str(TOOLS),
        'executor_sha256':sha(Path(__file__).read_bytes()),'clone_helper_sha256':HELPER_SHA,'activity_source_sha256':ACTIVITY_SHA,
        'original_executor_sha256':helper.ORIGINAL_SHA,'original_plan_sha256':sha((ORIGINAL_TOOLS/'pressure-plan.json').read_bytes()),
        'prior_failed_report_sha256':helper.FAILURE_SHA,'source_folder':str(helper.SOURCE),'source_config_sha256':helper.CONFIG_SHA,
        'source_pg_control_sha256':helper.CONTROL_SHA,'pins':module.PINS,'criteria':module.base.CRITERIA,
        'qualification_source_sha256':QUALIFIED_SOURCE,'qualification_report_sha256':sha(raw),
        'run_id_identical_on_separate_clones':RUN,'policy':POLICY,'fixed_numeric':FIXED,'derived_business':derive(helper,module)[1],
        'arms':[{'name':name,'pause_Agent':pause,'namespace':namespace(i)} for i,(name,pause) in enumerate(ARMS)],
        'activity_observation':{'lease_seconds':900,'full_sample_period_seconds':60,'maximum_sample_gap_seconds':120,
            'light_identity_state_check_each_business_loop':True,'same_observer_cost_each_arm':True,
            'whole_native600_coverage_required':True,'lease_or_early_unwind_ineligible':True},
        'native_seconds':600,'payload_bytes':67108864,'engine_content_checks':10,'engine_starts_at_native_second':30,
        'scope':'DBS static fixed-quota Agent activity diagnostic; not original32/reload/pressure/two-role acceptance',
        'preplanned_pattern':'eligible full A1 SQL+API errors>0, B1 zero, B2 zero, A2 errors>0; association with shared backend/cache/order confounds',
        'all_four_structural_and_cleanup_eligibility_before_pattern':True,'stable_release_accepted':False}


def readiness(helper,module,activity):
    need(not os.path.lexists(ROOT), 'FRESH_COMPARISON_ROOT')
    original_plan=json.loads((ORIGINAL_TOOLS/'pressure-plan.json').read_bytes())
    need(sha((ORIGINAL_TOOLS/'pressure-plan.json').read_bytes())=='c6581999c64e84ae9e833fd43117e71374159f388ffeea91aa905de5b2ac4098', 'ORIGINAL_PLAN_CHANGED')
    for name,digest in json.loads((ORIGINAL_TOOLS/'gates.json').read_bytes())['files'].items():
        need(sha((ORIGINAL_TOOLS/name).read_bytes())==digest, 'QUALIFIED_INPUT_CHANGED:'+name)
    module.device_pg_readiness(original_plan);module.diagnostic_readiness(original_plan);module.final_wait_readiness(original_plan)
    failed,digest=module.gate.read_json(Path('/var/tmp/crg-business-pressure342-20261111/report.json'))
    need(digest==helper.FAILURE_SHA and failed['phase']=='failed' and failed['namespace_absent'] and
         failed['original_config_bytes_and_profile_absence_restored'], 'PRIOR_FAILURE_PRESERVATION')
    for name in ['pressure-launch.json','pressure-worker.json']:
        p=json.loads((ORIGINAL_TOOLS/name).read_bytes())
        need(not module.gate.proc(p['pid'],p['entry'],p['start_ticks'])['live'], 'PRIOR_PRESSURE_PROCESS_LIVE')
    qualified=json.loads(Path('/var/tmp/crg-agent-activity422-20261111/report.json').read_bytes())
    need(qualified['job_sha256']==QUALIFIED_SOURCE and qualified['phase']=='passed' and qualified['namespace_absent'] and
         len(qualified['tests'])==32 and all(v['passed'] for v in qualified['tests']), 'VENDOR_LIFECYCLE_QUALIFICATION')
    need(module.gate.namespace('crg-vendor-lab-agent-activity422-20261111') is None, 'QUALIFICATION_NAMESPACE_PRESENT')
    qw=Path('/var/tmp/crg-agent-activity423-tools-20261111')
    for name in ['launch.json','worker.json']:
        p=json.loads((qw/name).read_bytes());need(not module.gate.proc(p['pid'],p['entry'],p['start_ticks'])['live'], 'QUALIFICATION_PROCESS_LIVE')
    for row in qualified['roles'].values():
        cg=Path(row['activity_plan']['cgroup']);need(not cg.exists() and not cg.parent.exists(), 'QUALIFICATION_CGROUP_PRESENT')
    for i,_ in enumerate(ARMS):need(module.gate.namespace(namespace(i)) is None, 'FRESH_ARM_NAMESPACE')
    helper.check_source(module)
    need(shutil.disk_usage('/var/tmp').free>=64*1024**3, 'FOUR_CLONE_DISK_RESERVE')
    available=int(next(v.split()[1] for v in Path('/proc/meminfo').read_text().splitlines() if v.startswith('MemAvailable:')))*1024
    need(available>=module.base.CRITERIA['clone_host_available_bytes'], 'CLONE_MEMORY_RESERVE')
    q=subprocess.run(['xfs_info','/'],capture_output=True,text=True,timeout=10)
    need(q.returncode==0 and 'reflink=1' in q.stdout, 'REFLINK_FILESYSTEM')
    return {'phase':'ready','executed':False,'stable_release_accepted':False}


def save(report):
    path=ROOT/'comparison.next'
    with path.open('w') as stream:
        os.fchmod(stream.fileno(),0o600);json.dump(report,stream,indent=2);stream.flush();os.fsync(stream.fileno())
    path.replace(ROOT/'comparison.json')


def rebind(function,**bindings):
    need(not function.__code__.co_freevars,'FUNCTION_CLOSURE')
    return types.FunctionType(function.__code__,dict(function.__globals__,**bindings),function.__name__,function.__defaults__)


def execute_arm(helper,module,activity,item,plan_digest):
    name=item['name'];folder=ROOT/'clones'/name/'dbs-business'
    arm_plan=copy.deepcopy(json.loads((ORIGINAL_TOOLS/'pressure-plan.json').read_bytes()))
    arm_plan.update(work_root=str(ROOT/'runs'/name),namespace=item['namespace'],run_id=RUN,mode='static-fixed-IO-Agent-activity-diagnostic')
    arm_plan['roles']['dbs']['folder']=str(folder)
    business,derivation=derive(helper,module)
    def adapt(original,role,cloned_folder,namespace,work):
        need(role=='dbs' and cloned_folder==folder,'DIAGNOSTIC_ROLE_FOLDER')
        pod=copy.deepcopy(original)
        for volume in pod['spec']['volumes']:
            if 'hostPath' not in volume or volume['name'] in ['gate','aux']:continue
            path=Path(volume['hostPath']['path']);need(path.is_relative_to(helper.SOURCE),'FOREIGN_SOURCE_MOUNT')
            volume['hostPath']['path']=str(folder/path.relative_to(helper.SOURCE))
        return module.base.adapt_pod(pod,role,cloned_folder,namespace,work)
    proxy=types.SimpleNamespace(**dict(module.base.__dict__,adapt_pod=adapt))
    role_function=module.rebind(module.reload.Execution.role,base=proxy)
    class Execution(module.Execution):
        def __init__(self):
            super().__init__(arm_plan,plan_digest)
            self._business_native_original=types.MethodType(business,self)
            self.report.update(schema='crg-agent-fixed-io-arm-v1',executor_sha256=sha(Path(__file__).read_bytes()),
                arm=name,pause_Agent=item['pause_Agent'],derived_business=derivation,
                scope='static fixed-quota diagnostic; not original32/reload/pressure/two-role acceptance',
                original_release_acceptance_executed=False,release_accepted=False)
            self.activity_session=None;self.activity_record=None;self.activity_next_sample=0

        def role(self,role):
            if role=='hisdbs':self.report['HISDBS_not_run_in_DBS_activity_diagnostic']=True;self.save();return
            return role_function(self,role)

        def activity_tick(self,row,force=False):
            value=self.activity_record;plan=value['plan'];current=activity.fields(plan['pid'])
            need(current['start_ticks']==plan['start_ticks'] and (current['state'] in ['T','t'])==item['pause_Agent'], 'AGENT_ACTIVITY_CHANGED')
            helper_state=activity.fields(value['helper']['pid'])
            need(helper_state['start_ticks']==value['helper']['start_ticks'] and helper_state['state'] not in ['T','t'], 'HELPER_INSTANCE_CHANGED')
            if force or time.monotonic()>=self.activity_next_sample:
                sample=self.activity_session.inspect()
                need(sample['all_threads_stopped']==item['pause_Agent'] and sample['control_values_preserved'], 'ACTIVITY_KERNEL_OR_THREADS')
                if item['pause_Agent']:
                    initial=value['session']['initial']
                    need(sample['user_ticks']==initial['user_ticks'] and sample['system_ticks']==initial['system_ticks'],'PAUSED_AGENT_CPU_CHANGED')
                need(len(value['samples'])<32,'ACTIVITY_SAMPLE_BOUND')
                value['samples'].append(dict(sample,epoch=time.time(),helper_state=helper_state['state']))
                self.activity_next_sample=time.monotonic()+60;self.save()

        def business_native(self,role,folder,group,row):
            # A single equal pre-measurement transition from original startup
            # budget to fixed main values; no configuration change in native600.
            mark=self.write_config(folder,POLICY);status=folder/'resource-state/status.json';deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                self.reserve();state=module.gate.read_json(status)[0];cfg=state.get('configuration',{})
                if status.stat().st_mtime_ns>mark and state.get('state')=='managed' and cfg.get('state')=='accepted' and cfg.get('generation')==2 and state['plan']['resource_mode']=='manual' and all(module.base.controls(group)[k]==v for k,v in FIXED.items()):break
                time.sleep(.25)
            else:raise module.Rejected('STATIC_POLICY_PREPARATION_60S')
            actual_controls=module.base.controls(group)
            need(all(actual_controls[k]==row['runtime_original_controls'][k] for k in module.base.CONTROLS[3:]), 'UNRELATED_CONTROLS_CHANGED_BEFORE_ACTIVITY')
            meta,cid,pid,actual=self.identity(role);need(actual==group,'OWN_ACTIVITY_GROUP')
            agents=self.processes(group,'/opt/crg/crg');need(len(agents)==1 and agents[0][2]==activity.ELF,'ONE_EXACT_AGENT')
            agent,ticks,_=agents[0];helper_pid=activity.fields(agent)['ppid'];helper_state=activity.fields(helper_pid)
            helper_argv=activity.read('/proc/%d/cmdline'%helper_pid,8192).rstrip(b'\0').split(b'\0')
            need(b'/opt/crg/optional-agent.sh' in helper_argv,'ORIGINAL_OPTIONAL_HELPER_PARENT')
            owner={'schema':'crg-agent-activity-owner-v1','kind':'vendor-container','nonce':uuid.uuid4().hex,'namespace':self.ns,
                'pod_uid':meta['metadata']['uid'],'container_id':cid,'container_pid':pid,'container_start_ticks':activity.fields(pid)['start_ticks']}
            proof=self.root/'agent-activity-owner.json'
            with proof.open('x') as stream:os.fchmod(stream.fileno(),0o600);json.dump(owner,stream)
            marker=folder/'crg-config/agent-activity-fixture.json';need(not marker.exists(),'FRESH_ACTIVITY_MARKER')
            marker.write_text(json.dumps({'fixture_root':str(self.root),'nonce':owner['nonce'],'namespace':self.ns}));marker.chmod(0o600)
            plan={k:owner[k] for k in ['kind','nonce','pod_uid','container_id','container_pid','container_start_ticks']}
            plan.update(fixture_root=str(self.root),pid=agent,start_ticks=ticks,argv=['/opt/crg/crg','run','--config','/etc/crg/config.json'],binary_sha256=activity.ELF,cgroup=str(group))
            record={'plan':plan,'helper':{'pid':helper_pid,'start_ticks':helper_state['start_ticks']},'samples':[],
                'fixed_controls':module.base.controls(group),'configuration_generation':cfg['generation'],'session':{},'before_session_epoch':time.time()}
            row['agent_activity']=record;self.activity_record=record;self.save()
            try:
                with activity.Session(plan,name,record['session'],pause=item['pause_Agent'],lease=900) as session:
                    self.activity_session=session;record['effective_activity_started_epoch']=time.time();self.activity_tick(row,True)
                    primary=None
                    try:return super().business_native(role,folder,group,row)
                    except BaseException as error:primary=error;raise
                    finally:
                        try:self.activity_tick(row,True)
                        except BaseException as error:
                            row.setdefault('diagnostic_cleanup_errors',[]).append('activity-final:'+type(error).__name__)
                            if primary is None:raise
                        finally:record['effective_activity_ended_epoch']=time.time();self.save()
            finally:
                record['session_unwind_completed_epoch']=time.time();self.save()

    return Execution().execute({'phase':'ready-for-fixed-quota-Agent-diagnostic','release_accepted':False})


def arm_eligibility(module,activity,result,native):
    """Structural validity is distinct from original SQL/API errors/pass."""
    row=result.get('roles',{}).get('dbs',{});boots=row.get('boots',[]);boot=boots[0] if len(boots)==1 else {}
    record=boot.get('agent_activity',{});session=record.get('session',{});snapshots=record.get('samples',[])
    engine=boot.get('engine',{}).get('roles',{}).get('dbs',{});native_diag=boot.get('native_request_pg',{})
    started=module.gate.audit.timestamp(native['started_utc']) if native.get('started_utc') else None
    finished=module.gate.audit.timestamp(native['measurement_finished_utc']) if native.get('measurement_finished_utc') else None
    errors={k:native.get(k,{}).get('errors') for k in ['sql','api']}
    actual600=native.get('phase') in ['passed','failed'] and native.get('elapsed_seconds',0)>=600 and not native.get('interrupted') and native.get('threads_stopped') is True
    checks={'one_boot':len(boots)==1,'terminal_reason':result.get('reason') in [None,'NATIVE_COMPLETION_EXIT'],
        'actual600':bool(actual600),'original_64MiB_data':native.get('payload_integrity') is True and native.get('primary_not_restarted') is True and native.get('initial_checksum',[None]*3)[2]==67108864,
        'native_error_counts':all(type(v) is int and v>=0 for v in errors.values()),
        'engine_ten_checks':len(engine.get('checks',[]))==10 and all(v['passed'] for v in engine.get('checks',[])) and engine.get('own_fixture_schema_restore_database_snapshot_removed') is True,
        'native_diagnostics':native_diag.get('phase')=='collected' and not native_diag.get('partial_not600s'),
        'thread_device_collected':boot.get('thread_observer',{}).get('phase')=='collected' and boot.get('device_observer',{}).get('phase')=='collected',
        'no_diagnostic_cleanup_errors':not boot.get('diagnostic_cleanup_errors'),
        'session_normal_close':session.get('phase')=='closed' and session.get('watchdog_exit')==0 and session.get('watchdog',{}).get('CONT_count')==0 and session.get('watchdog',{}).get('reason')=='owner-completed' and not any(k in session for k in ['unwind_error','close_error','watchdog_still_running']),
        'original_inputs_restored':result.get('original_config_bytes_and_profile_absence_restored') is True,
        'namespace_absent':result.get('namespace_absent') is True,'cgroups_absent':bool(boots) and all(not Path(v['cgroup']).exists() and not Path(v['cgroup']).parent.exists() for v in boots)}
    pause=result['pause_Agent'];checks['exact_session_signals']=session.get('STOP_count')==session.get('CONT_count')==(1 if pause else 0) and (not pause or session.get('resumed_same_instance') is True)
    checks['original_sampling_and_deadline_criteria']=native.get('criteria')=={'sql_period_seconds':2,'api_period_seconds':5,'maximum_seconds':5,'p95_upper_bound_seconds':1,'maximum_errors':0,'minimum_scheduled_samples_fraction':.98}
    checks['original_request_schedules']=all(type(native.get(k,{}).get('attempts')) is int and native[k]['attempts']>=600/period*.98 and
        native[k]['attempts']==native[k].get('successes',-1)+native[k].get('errors',-1) and len(native[k].get('histogram',[]))==12 and
        sum(native[k]['histogram'])==native[k]['attempts'] for k,period in [('sql',2),('api',5)])
    checks['fixed_original_numeric_controls']=all(record.get('fixed_controls',{}).get(k)==v for k,v in FIXED.items())
    checks['whole600_activity_coverage']=bool(started and finished and record.get('effective_activity_started_epoch',float('inf'))<=started<=finished<=record.get('effective_activity_ended_epoch',0))
    checks['sampled_kernel_and_activity']=len(snapshots)>=10 and all(v['controls']==session['initial']['controls'] and v['control_values_preserved'] and v['all_threads_stopped']==pause for v in snapshots)
    checks['activity_sample_gaps']=len(snapshots)>=2 and all(0<=z['epoch']-a['epoch']<=120 for a,z in zip(snapshots,snapshots[1:]))
    return {'eligible':all(checks.values()),'checks':checks,'SQL_errors':errors['sql'],'API_errors':errors['api'],
        'actual_seconds':native.get('elapsed_seconds'),'release_accepted':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--emit-plan',action='store_true');p.add_argument('--plan',type=Path);p.add_argument('--plan-sha256');p.add_argument('--execute',action='store_true');args=p.parse_args()
    if not args.emit_plan and args.plan is None:
        print(json.dumps({'phase':'inert','executed':False,'stable_release_accepted':False}));return 0
    try:
        need(sys.platform=='linux' and os.geteuid()==0,'LINUX_ROOT_REQUIRED')
        helper,module,activity=dependencies();expected=plan_value(helper,module)
        if args.emit_plan:
            need(not args.execute and args.plan is None,'EMIT_PLAN_READONLY');print(json.dumps(expected,indent=2));return 0
        raw=args.plan.read_bytes();need(sha(raw)==args.plan_sha256 and json.loads(raw)==expected,'FROZEN_PLAN_MISMATCH')
        ready=readiness(helper,module,activity)
        if not args.execute:print(json.dumps(ready));return 0
        need(os.environ.get('CRG_AGENT_ACTIVITY')==MARKER,'EXPLICIT_LAB_MARKER_REQUIRED')
        def interrupted(signum,frame):raise KeyboardInterrupt()
        signal.signal(signal.SIGTERM,interrupted);os.umask(0o077);readiness(helper,module,activity)
        ROOT.mkdir(mode=0o700);(ROOT/'runs').mkdir(mode=0o700)
        report={'schema':'crg-agent-fixed-io-comparison-v1','phase':'cloning','executor_sha256':sha(Path(__file__).read_bytes()),
            'plan_sha256':sha(raw),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'clones':{},'arms':{},'release_accepted':False,'original_release_acceptance_executed':False}
        save(report)
        try:
            rebind(helper.clone_all,ROOT=ROOT,ARMS=ARMS,save=save)(module,report)
            report['baseline_frozen_epoch']=time.time();save(report)
            for item in expected['arms']:
                name=item['name'];report['phase']='running-'+name;save(report)
                result=execute_arm(helper,module,activity,item,sha(raw));path=ROOT/'runs'/name/'report.json'
                nativepath=ROOT/'clones'/name/'dbs-business'/'postgresql/basebackup'/('crg-soak-'+RUN+'0')/'load.json'
                native=json.loads(nativepath.read_bytes()) if nativepath.exists() else {}
                review=arm_eligibility(module,activity,result,native)
                report['arms'][name]={'phase':result['phase'],'reason':result.get('reason'),'report_path':str(path),'report_sha256':sha(path.read_bytes()),
                    'native_report_sha256':sha(nativepath.read_bytes()) if nativepath.exists() else None,'native_phase':native.get('phase'),'eligibility':review}
                save(report);helper.check_source(module)
                need(result.get('namespace_absent') and result.get('original_config_bytes_and_profile_absence_restored'),'ARM_CLEANUP_INCOMPLETE_NO_NEXT_ARM')
                need(all(not Path(v['cgroup']).exists() for r in result['roles'].values() for v in r['boots']),'ARM_CGROUP_REMAINS_NO_NEXT_ARM')
                need(review['eligible'],'ARM_STRUCTURALLY_INELIGIBLE_NO_VALID_CONTRAST')
            values=[report['arms'][name]['eligibility'] for name,_ in ARMS]
            counts=[v['SQL_errors']+v['API_errors'] for v in values]
            pattern=counts[0]>0 and counts[1]==counts[2]==0 and counts[3]>0 and all(report['arms'][name]['native_phase']=='passed' for name in ['b1','b2'])
            report['interpretation']={'all_four_eligible':True,'SQL_plus_API_errors':counts,'preplanned_A_error_B_zero_B_zero_A_error':pattern,
                'conclusion':'fixed-quota-Agent-activity-association-with-confounds' if pattern else 'preplanned-association-not-observed',
                'shared_backend_cache_and_order_confounds_remain':True,'universal_Agent_causality_proven':False,'original32_accepted':False,'stable_release_accepted':False}
            report['phase']='diagnostic-completed'
        except BaseException as error:
            report.update(phase='failed',reason=str(error) if isinstance(error,(ValueError,module.Rejected,activity.Rejected)) else type(error).__name__,
                interpretation={'all_four_eligible':False,'conclusion':'inconclusive','stable_release_accepted':False})
        finally:
            report['ended_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save(report)
        print(json.dumps({'phase':report['phase'],'arms':report['arms'],'interpretation':report['interpretation'],'stable_release_accepted':False}))
        return 0 if report['phase']=='diagnostic-completed' else 1
    except BaseException as error:
        print(json.dumps({'phase':'rejected','reason':str(error) if isinstance(error,ValueError) else type(error).__name__,'executed':False,'stable_release_accepted':False}));return 1


if __name__=='__main__':
    raise SystemExit(main())
