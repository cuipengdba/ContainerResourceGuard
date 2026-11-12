from pathlib import Path
import hashlib,importlib.util,json,types

t=Path(__file__).parent;p=t/'crg-full-pressure-hook810.py';spec=importlib.util.spec_from_file_location('hook',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);cases=[]
for variant in ['normal','start-permission','finish-error','business-error','business-and-helper-errors','business-baseexception-and-helper-error','save-error','factory-permission']:
    timeline=[];rows=[];managers=[];primary=KeyboardInterrupt('original') if variant=='business-baseexception-and-helper-error' else ValueError('original')
    class Original:
        def save(self):
            if variant=='save-error':raise OSError('save failed')
        def business_native(self,role,folder,group,row):
            timeline.append('work');rows.append(row)
            if variant.startswith('business'):raise primary
            return ('original-return',role)
    original=Original.business_native
    def factory(execution,role,folder,group,row,record):
        timeline.append('factory')
        if variant=='factory-permission':raise PermissionError('factory denied')
        class Manager:
            def start(self):
                timeline.append('start')
                if variant in ['start-permission','business-and-helper-errors']:raise PermissionError('diagnostic denied')
            def finish(self):
                timeline.append('finish')
                if variant in ['finish-error','business-and-helper-errors','business-baseexception-and-helper-error']:raise RuntimeError('diagnostic cleanup failed')
        result=Manager();managers.append(result);return result
    core=types.SimpleNamespace(PressureExecution=Original);assert m.install(core,factory) is original
    row={};caught=None;result=None
    try:result=Original().business_native('dbs','own-folder','own-leaf',row)
    except BaseException as exc:caught=exc
    assert timeline.count('work')==1 and len(rows)==1 and rows[0] is row
    if variant.startswith('business'):assert caught is primary and result is None
    else:assert caught is None and result==('original-return','dbs')
    record=row['full_BPF_diagnostic'];assert record['original_business_method_invoked'] and record['diagnostic_failed']==bool(record['diagnostic_errors'])
    if variant not in ['normal','business-error']:assert record['diagnostic_failed']
    if variant!='factory-permission':assert timeline==['factory','start','work','finish']
    else:assert timeline==['factory','work'] and not managers
    try:m.install(core,factory)
    except ValueError:pass
    else:raise AssertionError('duplicate observer installation accepted')
    cases.append({'variant':variant,'original_work_called_once':True,'original_return_or_exact_exception_preserved':True,'partial_start_cleanup_attempted':variant!='factory-permission','ordinary_diagnostic_failure_does_not_skip_business':True,'duplicate_install_refused':True,'errors':record['diagnostic_errors']})
seen=[]
class TwoRoles:
    def save(self):pass
    def business_native(self,role,*args):return role
def per_call(execution,role,folder,group,row,record):
    manager=types.SimpleNamespace(start=lambda:None,finish=lambda:None);seen.append((role,manager));return manager
m.install(types.SimpleNamespace(PressureExecution=TwoRoles),per_call)
for role in ['dbs','hisdbs']:assert TwoRoles().business_native(role,None,None,{})==role
assert len(seen)==2 and seen[0][1] is not seen[1][1]
cases.append({'variant':'two-role-calls-create-distinct-per-call-controllers','one_distinct_controller_per_invocation':True})
result={'schema':'crg-original-full-pressure-hook-unit-v1','phase':'passed','source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'cases':cases,'synthetic_only_not_vendor_runtime_qualification':True,'collector_factory_not_yet_implemented':True,'original600_workload_or11_intervals_not_executed_by_unit':True};out=t/'crg-r810-hook-unit.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'phase':'passed','cases':len(cases),'synthetic_only_not_vendor_runtime_qualification':True}))
