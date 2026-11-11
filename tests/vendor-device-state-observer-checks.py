#!/usr/bin/env python
"""Python 2/3 parser, denial and short real-read qualification, on a lab node only."""
from __future__ import division, print_function
import argparse
import copy
import hashlib
import json
import os
import resource
import stat
import subprocess
import sys
import time

sys.dont_write_bytecode = True
here = os.path.dirname(os.path.abspath(__file__))
if sys.version_info[0] >= 3:
    import importlib.util
    spec = importlib.util.spec_from_file_location('crg_device_state_observer', os.path.join(here, 'vendor-device-state-observer.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
else:
    import imp
    m = imp.load_source('crg_device_state_observer', os.path.join(here, 'vendor-device-state-observer.py'))


def raw_json(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'))+'\n').encode('ascii')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-dir', required=True)
    args = parser.parse_args()
    assert sys.platform.startswith('linux') and os.environ.get('CRG_DEVICE_CHECKS') == 'authorized-disposable-readonly-only'
    root = args.work_dir
    assert root.startswith('/var/tmp/crg-') and '..' not in root.split('/') and not os.path.lexists(root)
    assert os.path.dirname(root) == os.path.realpath(os.path.dirname(root))
    os.umask(0o077)
    os.mkdir(root, 0o700)
    source = os.path.join(here, 'vendor-device-state-observer.py')
    source_sha = hashlib.sha256(open(source, 'rb').read()).hexdigest()
    out = {'schema':'crg-device-state-observer-qualification-v1', 'phase':'running', 'python':sys.version.split()[0],
           'observer_source_sha256':source_sha, 'checks_source_sha256':hashlib.sha256(open(__file__,'rb').read()).hexdigest(),
           'checks':[], 'scope':'self process/cgroup, confirmed sysfs device metadata; no database workload or target signals/control writes'}
    def record(name, **fields):
        out['checks'].append(dict(name=name, passed=True, **fields))
    def denied(name, fn, reason):
        try:
            fn()
        except m.Rejected as error:
            assert str(error) == reason, (name, str(error), reason)
        else:
            raise AssertionError('accepted '+name)
        record(name)
    try:
        a, c = m.clock(1), m.clock(2)
        assert m.clock(1) >= a and m.clock(2) >= c
        record('actual-libc-monotonic-and-process-CPU-clocks')
        d = m.device_stat(' '.join(str(i) for i in range(17)))
        assert d['read_sectors_512bytes'] == 2 and d['write_sectors_512bytes'] == 6 and d['in_flight'] == 8 and d['flush_ms'] == 16
        record('synthetic-17-field-stat-names-and-fixed512byte-sector-label')
        assert 'flush_ms' not in m.device_stat('0 '*11) and 'discard_ms' not in m.device_stat('0 '*11)
        record('synthetic-old11-field-layout-does-not-invent-newer-fields')
        denied('unrecognized-stat-layout-refused',lambda:m.device_stat('0 '*16),'DEVICE_STAT_LAYOUT')
        denied('negative-stat-counter-refused',lambda:m.device_stat('-1 '+'0 '*16),'NUMERIC_FIELD')
        denied('oversized-uint64-refused',lambda:m.numeric(str(2**64)),'NUMERIC_FIELD')
        denied('wrong-meminfo-unit-refused',lambda:m.key_values('Dirty: 2 MB',m.MEM_KEYS,'kB'),'COUNTER_UNIT')
        assert m.key_values('Dirty: 2 kB\nSecret: private\n',m.MEM_KEYS,'kB') == {'Dirty':2048}
        record('meminfo-byte-conversion-and-unselected-fields-not-retained')
        io = m.io_values('253:0 rbytes=8 wbytes=16 rios=1 wios=2 dbytes=99\n8:0 rbytes=44', ['253:0'])
        assert io == {'253:0':{'rbytes':8,'wbytes':16,'rios':1,'wios':2}}
        record('cgroup-IO-selected-devices-and-fields-only')
        denied('duplicate-selected-IO-device-refused',lambda:m.io_values('8:0 rbytes=1\n8:0 rbytes=2',['8:0']),'IO_DEVICE_DUPLICATE')
        assert not m.counter_delta({'writes_completed':10},{'writes_completed':1})['available']
        record('synthetic-counter-reset-remains-unknown')
        assert m.counter_delta({'in_flight':9,'writes_completed':10},{'in_flight':1,'writes_completed':11},('in_flight',)) == {
            'available':True,'deltas':{'writes_completed':1},'gauges_at_end':{'in_flight':1}}
        record('inflight-gauge-may-decrease-without-false-reset')
        assert not m.counter_delta({'read_ms':1},{'read_ms':2,'flush_ms':0})['available']
        record('layout-change-remains-unknown')
        values=['S']+['0']*18+['123']
        assert m.process_fields('77 (test (a) b) '+' '.join(values)) == {'pid':77,'state':'S','start_ticks':123}
        record('process-comm-parentheses-and-spaces-do-not-shift-startticks')
        denied('hybrid-membership-refused',lambda:m.membership('0::/\n1:cpu:/x\n'),'PURE_V2_MEMBERSHIP')
        denied('membership-parent-traversal-refused',lambda:m.membership('0::/a/../b\n'),'MEMBERSHIP_PATH')
        pid = os.getpid()
        process = m.process_fields(m.read_path('/proc/'+str(pid)+'/stat',4096))
        group = m.membership(m.read_path('/proc/'+str(pid)+'/cgroup',4096))
        devices=[]
        for name in ['253:0','8:2','8:0']:
            path=os.path.realpath('/sys/dev/block/'+name)
            assert path.startswith('/sys/devices/') and os.path.isdir(path)
            devices.append({'major_minor':name,'sysfs':path,'identity':m.identity(os.stat(path))})
        plan={'schema':m.PLAN_SCHEMA,'observer_sha256':source_sha,'label':'selftest','pid':pid,
              'start_ticks':process['start_ticks'],'cgroup':group,'cgroup_identity':m.identity(os.stat(group)),
              'boot_id':m.read_path('/proc/sys/kernel/random/boot_id',128).strip(),'devices':devices,
              'duration_seconds':3,'output':os.path.join(root,'real-observation.json')}
        original_controls={}
        for name in ['cpu.max','memory.max','io.max','pids.max','cpu.weight','io.weight','memory.high','memory.swap.max']:
            try:original_controls[name]=m.read_path(os.path.join(group,name),4096)
            except (OSError,IOError):original_controls[name]=None
        def invoke(value, name, execute=False, marker=True, raw=None, digest=None):
            path=os.path.join(root,name+'-plan.json')
            data=raw_json(value) if raw is None else raw
            with open(path,'wb') as f:f.write(data)
            command=[sys.executable,source,'--plan',path,'--plan-sha256',digest or hashlib.sha256(data).hexdigest()]
            if execute:command.append('--execute')
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
            env.pop('CRG_DEVICE_OBSERVER',None)
            if marker:env['CRG_DEVICE_OBSERVER']='authorized-disposable-readonly-only'
            p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
            stdout,stderr=p.communicate()
            assert not stderr, (name,stderr[-200:])
            return p.returncode,[json.loads(line) for line in stdout.decode('ascii').splitlines()],data
        code,rows,_=invoke(plan,'preflight')
        assert code==0 and rows==[{'phase':'ready','executed':False,'output_created':False}] and not os.path.exists(plan['output'])
        record('actual-preflight-creates-no-output')
        code,rows,_=invoke(plan,'missing-marker',True,False)
        assert code==1 and rows[-1]['reason']=='EXPLICIT_LAB_MARKER' and not os.path.exists(plan['output'])
        record('execute-marker-missing-refused-before-output')
        cases=[('duration901','PLAN_DURATION',lambda v:v.update(duration_seconds=901)),
               ('source-mismatch','OBSERVER_SOURCE',lambda v:v.update(observer_sha256='0'*64)),
               ('process-start-mismatch','PROCESS_INSTANCE',lambda v:v.update(start_ticks=v['start_ticks']+1)),
               ('group-inode-mismatch','CGROUP_INSTANCE',lambda v:v['cgroup_identity'].__setitem__(1,v['cgroup_identity'][1]+1)),
               ('device-inode-mismatch','DEVICE_INSTANCE',lambda v:v['devices'][0]['identity'].__setitem__(1,v['devices'][0]['identity'][1]+1)),
               ('device-path-outside','DEVICE_PATH',lambda v:v['devices'][0].update(sysfs='/etc')),
               ('duplicate-device','DEVICE_NUMBER',lambda v:v['devices'].append(copy.deepcopy(v['devices'][0]))),
               ('too-many-devices','PLAN_DEVICE_BOUND',lambda v:v.update(devices=v['devices']+[v['devices'][0],v['devices'][1]])),
               ('boot-mismatch','BOOT_CHANGED',lambda v:v.update(boot_id='00000000-0000-0000-0000-000000000000'))]
        for name,reason,edit in cases:
            value=copy.deepcopy(plan);value['output']=os.path.join(root,name+'.json');edit(value)
            code,rows,_=invoke(value,name,True)
            assert code==1 and rows[-1]['reason']==reason and not os.path.lexists(value['output']),(name,rows)
            record('actual-CLI-'+name+'-refused-before-output')
        code,rows,_=invoke(plan,'wrong-digest',True,digest='0'*64)
        assert code==1 and rows[-1]['reason']=='PLAN_DIGEST' and not os.path.exists(plan['output'])
        record('wrong-plan-digest-refused')
        raw=raw_json(plan).decode('ascii').rstrip()[:-1]+',"duration_seconds":3}\n'
        code,rows,_=invoke(plan,'duplicate-json',True,raw=raw.encode('ascii'))
        assert code==1 and rows[-1]['reason']=='JSON_DUPLICATE' and not os.path.exists(plan['output'])
        record('duplicate-JSON-key-refused')
        sentinel=os.path.join(root,'sentinel');open(sentinel,'wb').write(b'preserve')
        linked=os.path.join(root,'linked.json');os.symlink(sentinel,linked)
        value=copy.deepcopy(plan);value['output']=linked
        code,rows,_=invoke(value,'symlink-output',True)
        assert code==1 and rows[-1]['reason']=='FRESH_PRIVATE_OUTPUT' and open(sentinel,'rb').read()==b'preserve'
        record('symlink-output-refused-without-changing-target')
        usage=resource.getrusage(resource.RUSAGE_CHILDREN);started=m.clock(1)
        code,rows,_=invoke(plan,'actual-real',True)
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        report_raw=open(plan['output'],'rb').read();report=json.loads(report_raw)
        assert code==0 and report['phase']=='observed' and report['sample_count']==4 and report['elapsed_seconds']>=3
        assert rows[0]['phase']=='observing' and report['block_device_opens_signals_and_control_writes']==0
        assert stat.S_IMODE(os.stat(plan['output']).st_mode)==0o600 and len(report_raw)<=m.MAX_REPORT
        samples=report['samples'];assert all(s['devices'][d['major_minor']]['available'] for s in samples for d in devices)
        assert all(.5 < y['monotonic']-x['monotonic'] < 2 for x,y in zip(samples,samples[1:]))
        assert all(abs((y['epoch']-x['epoch'])-(y['monotonic']-x['monotonic'])) < .1 for x,y in zip(samples,samples[1:]))
        whole_cpu=after.ru_utime+after.ru_stime-usage.ru_utime-usage.ru_stime
        assert whole_cpu<=1 and report['maximum_collection_seconds']<=.1 and after.ru_maxrss<=131072
        assert m.process_fields(m.read_path('/proc/'+str(pid)+'/stat',4096))['start_ticks']==process['start_ticks']
        controls_after={}
        for name in original_controls:
            try:controls_after[name]=m.read_path(os.path.join(group,name),4096)
            except (OSError,IOError):controls_after[name]=None
        assert original_controls==controls_after
        record('actual-three-second-four-sample-read-only-observation',report_sha256=hashlib.sha256(report_raw).hexdigest(),report_bytes=len(report_raw),
               child_CPU_seconds=whole_cpu,child_high_water_RSS_kib=after.ru_maxrss,maximum_collection_seconds=report['maximum_collection_seconds'],
               whole_wall_seconds=m.clock(1)-started,controls_unchanged=True,same_parent_instance=True,report_mode='0600')
        code,rows,_=invoke(plan,'existing-output',True)
        assert code==1 and rows[-1]['reason']=='FRESH_PRIVATE_OUTPUT' and open(plan['output'],'rb').read()==report_raw
        record('existing-real-report-refused-without-overwrite')
        out.update(phase='passed',actual_plan=plan,real_report=report)
    except BaseException as error:
        out.update(phase='failed',reason_class=type(error).__name__,reason=str(error)[:400])
    finally:
        with open(os.path.join(root,'qualification.json'),'wb') as f:f.write(raw_json(out))
    print(json.dumps({'phase':out['phase'],'checks':len(out['checks']),'reason':out.get('reason'),'python':out['python']}))
    return 0 if out['phase']=='passed' else 1


if __name__=='__main__':
    sys.exit(main())
