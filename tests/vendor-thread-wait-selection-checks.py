#!/usr/bin/env python3
"""Qualify D-selector bounds with explicitly synthetic selector inputs.

The actual own child remains S in a pipe read; this is not actual D/vendor proof.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time

sys.dont_write_bytecode=True
here=Path(__file__).parent
spec=importlib.util.spec_from_file_location('wait_observer_selection',here/'vendor-thread-wait-observer.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--work-dir',type=Path,required=True);args=parser.parse_args();root=args.work_dir
    assert sys.platform=='linux' and os.environ.get('CRG_THREAD_WAIT_SELECTION')=='authorized-disposable-test-node-only'
    assert str(root).startswith('/var/tmp/crg-') and '..' not in root.parts and not root.exists();root.mkdir(mode=0o700)
    p=subprocess.Popen([sys.executable,'-c',"import os,sys;sys.stdout.write('ready\\n');sys.stdout.flush();assert os.read(0,1)==b'x'"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    checks=[];observer=None;examples={}
    def check(name,value):checks.append({'name':name,'passed':bool(value)});assert value,name
    assert select.select([p.stdout],[],[],5)[0] and p.stdout.readline()==b'ready\n';time.sleep(.05)
    proc=Path('/proc',str(p.pid));fields=m.stat_fields((proc/'stat').read_text());group=Path('/sys/fs/cgroup')/m.pure_v2_path((proc/'cgroup').read_text()).lstrip('/')
    def controls():return {name:(group/name).read_text() if (group/name).exists() else None for name in ['cpu.max','memory.max','io.max']}
    before=controls()
    plan={'schema':m.SCHEMA,'observer_sha256':hashlib.sha256((here/'vendor-thread-wait-observer.py').read_bytes()).hexdigest(),'label':'selftest','pid':p.pid,'start_ticks':fields['start_ticks'],'executable_sha256':hashlib.sha256((proc/'exe').read_bytes()).hexdigest(),'cgroup':str(group),'duration_seconds':1,'output':str(root/'unused.json')}
    try:
        observer=m.Observer(plan);base=observer.snapshot();examples['actual_S']=base
        check('actual-S-wait-is-not-selected-as-D',base['wait_sampling']['D_tasks']==base['wait_sampling']['attempted']==0 and all('wait_detail' not in v for v in base['tasks']))
        row=copy.deepcopy(base);row['tasks'][0]['stat']['state']='D';observer.add_wait_details(row);examples['synthetic_D_selector_actual_S']=row
        detail=row['tasks'][0]['wait_detail']
        check('synthetic-D-selector-exercises-real-proc-capture',row['wait_sampling']['recorded']==1 and detail['available'] and detail['state_before']=='S')
        check('selector-retains-real-S-read-and-pipe-facts',detail['syscall']['operation']=='read' and detail['descriptor']['kind']=='pipe')
        row=copy.deepcopy(base);row['tasks'][0]['stat'].update(state='D',start_ticks=fields['start_ticks']+1);observer.add_wait_details(row)
        check('raced-task-start-stays-explicit-unknown',row['wait_sampling']['unknown']==1 and row['tasks'][0]['wait_detail']['reason']=='TASK_CHANGED')
        row=copy.deepcopy(base);template=copy.deepcopy(row['tasks'][0]);template['stat']['state']='D';row['tasks']=[copy.deepcopy(template) for _ in range(64)];observer.add_wait_details(row);examples['synthetic_64_selector_summary']=row['wait_sampling']
        check('synthetic64-tasks-at-most8-proc-captures',row['wait_sampling']['D_tasks']==64 and row['wait_sampling']['attempted']==8 and row['wait_sampling']['recorded']<=8 and row['wait_sampling']['omitted']>=56)
        check('extra-metadata-retains-original32KiB-row-bound',len(json.dumps(row).encode())<=m.MAX_RECORD and sum(len(json.dumps(v['wait_detail']).encode()) for v in row['tasks'] if 'wait_detail' in v)<=8192)
        row=copy.deepcopy(base);row['tasks'][0]['stat']['state']='D';row['padding']='x'*max(0,m.MAX_RECORD-len(json.dumps(row).encode())-1100);observer.add_wait_details(row)
        check('near-full-row-omits-wait-details-explicitly',row['wait_sampling']['omitted']==1 and 'wait_detail' not in row['tasks'][0] and len(json.dumps(row).encode())<=m.MAX_RECORD)
        check('bound-process-and-controls-stay-unchanged',p.poll() is None and m.stat_fields((proc/'stat').read_text())['start_ticks']==fields['start_ticks'] and controls()==before)
        check('metadata-only-path-creates-no-observer-report',not Path(plan['output']).exists())
        observer.close();observer=None;p.stdin.write(b'x');p.stdin.flush();p.stdin.close();p.wait(timeout=5)
        check('own-fixture-exits-without-signals',p.returncode==0 and not p.stderr.read())
    finally:
        if observer is not None:observer.close()
        if p.poll() is None:
            p.stdin.close()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
        result={'schema':'crg-thread-wait-selector-checks-v1','phase':'passed' if len(checks)==10 and all(v['passed'] for v in checks) else 'failed','checks':checks,'examples':examples,
                'actual_D_or_vendor_acceptance':False,'actual_fixture_state':'S pipe wait; D selector inputs are synthetic','own_child_reaped':p.returncode is not None,'original_controls_unchanged':controls()==before,
                'source_sha256':{n:hashlib.sha256((here/n).read_bytes()).hexdigest() for n in ['vendor-thread-wait.py','vendor-thread-wait-observer.py','vendor-thread-wait-selection-checks.py']}}
        path=root/'checks-result.json';path.write_text(json.dumps(result,indent=2)+'\n');path.chmod(0o600)
    print(json.dumps({'phase':result['phase'],'checks':len(checks)}))
    return 0 if result['phase']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
