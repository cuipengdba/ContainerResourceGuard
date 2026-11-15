"""One original-path, negative lock diagnostic; not full600 business acceptance.

Host Python3; receives only an already verified disposable fixture context.
Uses original worker/SLA unchanged, 120s separate diagnostic window and exactly
one 8s lock on this run's synthetic table. No resource or business config writes.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import re
import shlex
import signal
import stat
import subprocess
import time


def python_entry_matches(argv, entry):
    # An observer's --worker argument is never its own script identity.
    return (len(argv) >= 2 and argv[1] == entry.encode() and
            re.fullmatch(rb'python(?:[23](?:\.[0-9]+)?)?', argv[0].rsplit(b'/', 1)[-1]) is not None)


def lock_command(run_id):
    assert re.fullmatch(r'[0-9]{12}', run_id)
    transaction = ('BEGIN; LOCK TABLE crg_soak_' + run_id +
                   '.fixture IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(8); ROLLBACK;')
    # psql -c only prints the last SQL result in one string. Separate -c
    # requests on the same connection preserve the holder PID before ROLLBACK.
    return ("PGAPPNAME=crg-disposable-lock PGOPTIONS='-c statement_timeout=15000 -c lock_timeout=2000' "
            "/opt/postgresql/pgsql/bin/psql -XAtqw -h127.0.0.1 -p5432 -U postgres -d postgres "
            "-v ON_ERROR_STOP=1 -c " + shlex.quote('SELECT pg_backend_pid();') +
            ' -c ' + shlex.quote(transaction))


def run_case(context):
    folder=context['folder'];case_root=context['case_root'];group=context['group'];item=context['item']
    role=context['role'];ns=context['namespace'];plan=context['plan'];run_id=plan['run_ids']['normal'][role]
    save=context['save'];record=context['record'];reserve=context['reserve'];key=context['key'];tools=context['tools']
    assert re.fullmatch(r'[0-9]{12}',run_id) and ns=='crg-vendor-lab-wait1830-normal-'+role+'-20261116'
    identity=item['fixture_identity'];membership=Path('/proc',str(identity['init_pid']),'cgroup').read_bytes();member_sha=hashlib.sha256(membership).hexdigest()
    expected_controls=item['initial_controls'];original_inode=(group.stat().st_dev,group.stat().st_ino)
    entry='/tmp/crg-soak-load-'+run_id+'.py';observer_entry='/tmp/crg-wait-timeline-'+run_id+'.py'
    native_path=folder/'postgresql/basebackup'/('crg-soak-'+run_id)/'load.json'
    wait_root=folder/'postgresql/basebackup'/('crg-wait-'+run_id);timeline_path=wait_root/'timeline.jsonl'
    native_job=observer_job=holder_job=None;native_identity=observer_identity=None;logs=[]
    result={'schema':'crg-controlled-own-table-lock-diagnostic-v1','phase':'preparing','run_id':run_id,
            'worker_seconds':120,'lock_seconds':8,'negative_workload_expected':True,'formal_full600_acceptance':False,
            'worker_sha256':plan['source_sha256']['tests/vendor-soak-load.py'],
            'timeline_sha256':plan['source_sha256']['tests/wait-timeline.py'],'fixture_identity':dict(identity),'observations':{}}
    result_path=case_root/'controlled-lock.json'
    assert not result_path.exists() and not wait_root.exists()
    def persist():
        result_path.write_text(json.dumps(result,indent=2)+'\n');result_path.chmod(0o600);item['controlled_lock']=result;save()
    def ticks(pid):return int(Path('/proc',str(pid),'stat').read_bytes().rsplit(b')',1)[1].split()[19])
    def absent(p):
        try:return ticks(p['pid'])!=p['start_ticks']
        except (FileNotFoundError,ProcessLookupError):return True
    def controls_ok():
        assert (group.stat().st_dev,group.stat().st_ino)==original_inode and Path('/proc',str(identity['init_pid']),'cgroup').read_bytes()==membership
        assert ticks(identity['init_pid'])==identity['init_start_ticks'] and all((group/n).read_text().strip()==v for n,v in expected_controls.items())
        for p in identity['processes']:
            if p.get('executable') in ['/opt/crg/crg','/opt/ccg/bin/containercacheguard']:
                assert not absent(p) and Path('/proc',str(p['pid']),'cgroup').read_bytes()==membership
    def own_entry(name,job):
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            members=(group/'cgroup.procs').read_text().splitlines();assert len(members)<=128
            found=[]
            for value in members:
                p=Path('/proc',value)
                try:
                    before=ticks(value);argv=(p/'cmdline').read_bytes().split(b'\0')
                    if python_entry_matches(argv, name) and (p/'cgroup').read_bytes()==membership and ticks(value)==before:
                        found.append({'pid':int(value),'start_ticks':before,'entry':name})
                except (FileNotFoundError,ProcessLookupError):pass
            if found:
                assert len(found)==1;identity['processes'].append(found[0]);return found[0]
            if job.poll() is not None:raise RuntimeError('diagnostic entry exited before identity capture')
            time.sleep(.1)
        raise RuntimeError('diagnostic own-entry identity deadline')
    def stop_exact(p):
        if p is None or absent(p):return
        process=Path('/proc',str(p['pid']));handle=os.pidfd_open(p['pid'])
        try:
            if absent(p):return
            assert process.joinpath('cgroup').read_bytes()==membership and python_entry_matches(process.joinpath('cmdline').read_bytes().split(b'\0'), p['entry'])
            signal.pidfd_send_signal(handle,signal.SIGTERM)
        finally:os.close(handle)
    def copy_entry(name,source):
        raw=source.read_bytes();q=shlex.quote(name)
        r=subprocess.run(['kubectl','exec','-i','-n',ns,role+'-business','-c',role,'--','/bin/bash','-c','set -Ce; umask 077; cat > '+q+'; chmod 0444 '+q],input=raw,capture_output=True,timeout=15)
        assert r.returncode==0
        actual=context['ex'](role,'sha256sum',name,timeout=10).stdout.split()[0]
        assert actual==hashlib.sha256(raw).hexdigest()
    def spawn(name,command):
        log=(case_root/name).open('xb');os.fchmod(log.fileno(),0o600);logs.append(log)
        return subprocess.Popen(['kubectl','exec','-n',ns,role+'-business','-c',role,'--','su','-','postgres','-c',command],stdin=subprocess.DEVNULL,stdout=log,stderr=log)
    def counter():
        sql='SELECT sum(counter) FROM crg_soak_'+run_id+'.fixture;'
        command="PGOPTIONS='-c statement_timeout=1000' /opt/postgresql/pgsql/bin/psql -XAtw -h127.0.0.1 -p5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c "+shlex.quote(sql)
        response=context['ex'](role,'su','-','postgres','-c',command,timeout=10).stdout.strip().splitlines()[-1]
        assert re.fullmatch(r'[0-9]+',response);return int(response)
    def read_json(p,limit=2*1024**2):
        st=p.lstat();assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_size<=limit
        return json.loads(p.read_bytes())
    def request_observer_stop():
        assert wait_root.is_dir() and not wait_root.is_symlink() and wait_root.resolve().is_relative_to(folder.resolve())
        marker={'schema':'crg-owned-wait-stop-v1','run_id':run_id,'pid1_start_ticks':identity['init_start_ticks'],'membership_sha256':member_sha,'requested_monotonic':time.monotonic(),'requested_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
        p=wait_root/'.stop-request';fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as stream:
            json.dump(marker,stream);stream.write('\n');stream.flush();os.fchown(stream.fileno(),wait_root.stat().st_uid,wait_root.stat().st_gid);os.fsync(stream.fileno())
        os.link(p,wait_root/'stop.json');p.unlink();result['observer_stop_request']=marker;persist()
    try:
        persist();controls_ok();copy_entry(entry,tools/'vendor-soak-load.py');copy_entry(observer_entry,tools/'wait-timeline.py')
        command='CRG_VENDOR_WAIT_TEST=disposable-loopback-only python '+shlex.quote(observer_entry)+' --run-id '+run_id+' --container-id '+identity['container_id']+' --pid1-start-ticks '+str(identity['init_start_ticks'])+' --membership-sha256 '+member_sha+' --worker '+shlex.quote(entry)+' --worker-sha256 '+result['worker_sha256']+' --seconds 600'
        observer_job=spawn('wait-observer.log',command);observer_identity=own_entry(observer_entry,observer_job);result['observer_host_instance']=observer_identity;persist()
        command='CRG_VENDOR_SOAK_TEST=disposable-loopback-only python '+shlex.quote(entry)+' --run-id '+run_id+' --seconds 120 --test-phase smoke'
        native_job=spawn('lock-native-worker.log',command);native_identity=own_entry(entry,native_job);result['worker_host_instance']=native_identity;persist()
        deadline=time.monotonic()+360
        while time.monotonic()<deadline:
            reserve();controls_ok()
            if native_job.poll() is not None or observer_job.poll() is not None:raise RuntimeError('diagnostic worker or observer exited during preparation')
            if native_path.exists() and read_json(native_path)['phase']=='running':break
            time.sleep(.5)
        else:raise RuntimeError('original worker preparation deadline')
        result['running_observed_monotonic']=time.monotonic();result['native_running_snapshot']=read_json(native_path)
        assert timeline_path.exists();header=json.loads(timeline_path.open('rb').readline())
        assert header['kind']=='header' and header['source_sha256']==result['timeline_sha256'] and header['worker_sha256']==result['worker_sha256'] and header['membership_sha256']==member_sha and header['pid1_start_ticks']==identity['init_start_ticks'] and (header['group_device'],header['group_inode'])==original_inode
        assert native_identity['pid'] != observer_identity['pid']
        record(key+'-new-observer-and-native-share-owned-container-identity',True);persist()
        until=time.monotonic()+10
        while time.monotonic()<until:controls_ok();reserve();time.sleep(.5)
        result['counter_before_lock']=counter();lock_started=time.monotonic();result['lock_requested_monotonic']=lock_started;persist()
        command=lock_command(run_id)
        holder_job=subprocess.Popen(['kubectl','exec','-n',ns,role+'-business','-c',role,'--','su','-','postgres','-c',command],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        stdout,stderr=holder_job.communicate(timeout=22);lock_ended=time.monotonic();assert len(stdout)<=4096 and len(stderr)<=4096
        backend_pids=[int(v) for v in stdout.decode().splitlines() if re.fullmatch(r'[0-9]+',v)]
        result.update(lock_holder_exit=holder_job.returncode,lock_holder_backend_pids=backend_pids,lock_ended_monotonic=lock_ended,lock_exec_elapsed_seconds=lock_ended-lock_started);persist()
        record(key+'-one-8s-transaction-held-only-own-synthetic-table',holder_job.returncode==0 and len(backend_pids)==1 and backend_pids[0]>1 and 8<=lock_ended-lock_started<=22)
        until=time.monotonic()+4
        while time.monotonic()<until:controls_ok();reserve();time.sleep(.5)
        result['counter_after_lock']=counter();persist()
        deadline=result['running_observed_monotonic']+240
        while native_job.poll() is None and time.monotonic()<deadline:
            controls_ok();reserve()
            if observer_job.poll() is not None:raise RuntimeError('observer exited before workload finished')
            time.sleep(1)
        if native_job.poll() is None:raise RuntimeError('original worker completion deadline')
        result['worker_exit']=native_job.wait(timeout=10);workload=read_json(native_path);result['workload']=workload;persist()
        events=workload.get('failure_diagnostics',{}).get('events',[]);sql_events=[v for v in events if v['kind']=='sql']
        deadlines={'sql_readiness_deadline','sql_result_deadline','sql_socket_deadline'}
        expected=workload['phase']=='failed' and result['worker_exit']!=0 and workload['requested_duration_seconds']==120 and workload['elapsed_seconds']>=120 and workload['threads_stopped'] and workload['payload_integrity'] and workload['primary_not_restarted'] and not workload['interrupted'] and workload['sql']['errors']>0 and workload['criteria']=={'sql_period_seconds':2,'api_period_seconds':5,'maximum_seconds':5,'p95_upper_bound_seconds':1,'maximum_errors':0,'minimum_scheduled_samples_fraction':.98}
        expected=expected and len(sql_events)==workload['sql']['errors'] and len(sql_events)>0 and all(v['stage']=='sql_query' and v['reason'] in deadlines and v['elapsed_seconds']>=4.99 and v['request_started_monotonic_seconds']<=lock_ended and v['request_finished_monotonic_seconds']>=lock_started for v in sql_events)
        record(key+'-full120-negative-keeps-original-SLA-and-records-SQL-deadline',expected);persist()
        request_observer_stop();result['observer_exit']=observer_job.wait(timeout=12)
        raw=timeline_path.read_bytes();assert len(raw)<=4*1024**2 and raw.endswith(b'\n');lines=raw.splitlines();assert all(len(v)+1<=16384 for v in lines);timeline=[json.loads(v) for v in lines];terminal=timeline[-1];samples=[v for v in timeline if v['kind']=='sample']
        holder=backend_pids[0];matches=[]
        for event in sql_events:
            found=[{'sample_sequence':s['sequence'],'pid':b['pid'],'blocker_pid':holder,'sample_started_monotonic':s['sample_started_monotonic'],'sample_finished_monotonic':s['sample_finished_monotonic'],'query_age_seconds':b['query_age_seconds']} for s in samples if s['sample_started_monotonic']<=event['request_finished_monotonic_seconds'] and s['sample_finished_monotonic']>=event['request_started_monotonic_seconds'] for b in s['backends'] if b['wait_type']=='Lock' and b['wait_event']=='relation' and holder in b['blocking_pids'] and b['pid']!=holder]
            matches.append({'request_attempt':event['attempt'],'matches':found})
        result.update(timeline_bytes=len(raw),timeline_sha256=hashlib.sha256(raw).hexdigest(),timeline_samples=len(samples),timeline_terminal=terminal,request_lock_matches=matches);persist()
        record(key+'-timeline-attributes-error-to-actual-relation-lock-holder',bool(matches) and all(v['matches'] for v in matches))
        memory_events=dict(v.split() for v in (group/'memory.events').read_text().splitlines());result['final_memory_events']={k:int(v) for k,v in memory_events.items()}
        baseline_events=samples[0]['group']['memory_events'];api=workload['api']
        record(key+'-post-lock-SQL-progress-and-API-continuity-with-no-OOM',result['counter_after_lock']>result['counter_before_lock'] and api['errors']==0 and api['max_seconds']<=5 and api['p95_bucket_upper_seconds']<=1 and api['sample_coverage']>=.98 and all(result['final_memory_events'][k]==baseline_events[k] for k in ['oom','oom_kill']))
        controls_ok();span=samples[-1]['sample_finished_monotonic']-samples[0]['sample_started_monotonic']
        bounded=result['observer_exit']==0 and terminal['kind']=='terminal' and terminal['phase']=='complete' and terminal['reason']=='explicit_own_stop_file' and terminal['backend_query_errors']==0 and terminal['samples']==len(samples)<=900 and len(samples)>=span/2*.90 and all(b['sample_started_monotonic']-a['sample_started_monotonic']<=8 for a,b in zip(samples,samples[1:])) and absent(observer_identity) and absent(native_identity)
        record(key+'-bounded-private-timeline-stopped-before-unchanged-guards',bounded)
        result['phase']='passed-negative-diagnostic-only';persist()
    except BaseException:
        result['phase']='failed';persist();raise
    finally:
        for p in [observer_identity,native_identity]:stop_exact(p)
        for job in [observer_job,native_job,holder_job]:
            if job is None:continue
            try:job.wait(timeout=12)
            except subprocess.TimeoutExpired:
                job.terminate()
                try:job.wait(timeout=5)
                except subprocess.TimeoutExpired:job.kill();job.wait(timeout=5)
        for log in logs:log.close()
        result['auxiliary_originals_absent']=all(p is None or absent(p) for p in [observer_identity,native_identity]);persist()
