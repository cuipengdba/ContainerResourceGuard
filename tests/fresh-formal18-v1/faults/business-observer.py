"""Own-container campaign observer. Test helper only; never writes cgroup/PG."""
from pathlib import Path
import datetime,hashlib,json,os,re,shlex,signal,stat,subprocess,time

def sha(raw):return hashlib.sha256(raw).hexdigest()
def ticks(pid):return int(Path('/proc',str(pid),'stat').read_bytes().rsplit(b')',1)[1].split()[19])
def absent(p):
    if p is None:return False
    try:return ticks(p['pid'])!=p['start_ticks']
    except (FileNotFoundError,ProcessLookupError):return True
def entry_matches(argv,entry):
    return len(argv)>=2 and argv[1]==entry.encode() and re.fullmatch(rb'python(?:[23](?:\.[0-9]+)?)?',argv[0].rsplit(b'/',1)[-1]) is not None
def read_json(path,limit=131072):
    info=path.lstat();assert stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_size<=limit
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        opened=os.fstat(stream.fileno());assert (opened.st_dev,opened.st_ino)==(info.st_dev,info.st_ino);raw=stream.read(limit+1)
    assert len(raw)<=limit;return json.loads(raw)
def find_entry(group,membership,entry):
    values=(group/'cgroup.procs').read_text().splitlines();assert len(values)<=128;found=[]
    for value in values:
        p=Path('/proc',value)
        try:
            before=ticks(value);argv=(p/'cmdline').read_bytes().split(b'\0')
            if entry_matches(argv,entry) and (p/'cgroup').read_text()==membership and ticks(value)==before:found.append({'pid':int(value),'start_ticks':before,'entry':entry})
        except (FileNotFoundError,ProcessLookupError):pass
    assert len(found)<=1,'ambiguous own auxiliary entry'
    return found[0] if found else None
def exact_stop(p,membership):
    if p is None or absent(p):return
    handle=os.pidfd_open(p['pid'])
    try:
        if absent(p):return
        process=Path('/proc',str(p['pid']));assert (process/'cgroup').read_text()==membership and entry_matches((process/'cmdline').read_bytes().split(b'\0'),p['entry'])
        assert ticks(p['pid'])==p['start_ticks'];signal.pidfd_send_signal(handle,signal.SIGTERM)
    finally:os.close(handle)
def timeline(path,partial=False):
    info=path.lstat();assert stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_size<=4194304
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        opened=os.fstat(stream.fileno());assert (opened.st_dev,opened.st_ino)==(info.st_dev,info.st_ino);raw=stream.read(4194305)
    assert len(raw)<=4194304
    lines=raw.splitlines()
    if not raw.endswith(b'\n'):
        assert partial;lines=lines[:-1]
    assert all(len(line)+1<=16384 for line in lines)
    return raw,[json.loads(line) for line in lines]

class Observer:
    def __init__(self,role,args,own,worker_sha,ex):
        assert role in ['dbs','hisdbs'] and re.fullmatch(r'[0-9]{12}',args.run_id) and args.seconds==600 and args.test_phase=='smoke'
        assert re.fullmatch(r'[0-9a-f]{64}',args.wait_timeline_sha256) and re.fullmatch(r'[0-9a-f]{64}',worker_sha)
        self.role=role;self.args=args;self.own=own;self.ex=ex;self.worker_sha=worker_sha;self.group=own['group'];self.membership=own['membership'];self.run=args.run_id
        self.folder=args.fixture_root/(role+'-business');self.root=self.folder/'postgresql/basebackup'/('crg-wait-'+self.run);self.path=self.root/'timeline.jsonl'
        self.entry='/tmp/crg-wait-timeline-'+self.run+'.py';self.worker_entry='/tmp/crg-soak-load-'+self.run+'.py';self.log_path=args.work_dir/(role+'-wait-observer.log');self.report_path=args.work_dir/(role+'-wait-session.json')
        assert not self.root.exists() and not self.report_path.exists() and not self.log_path.exists()
        self.group_identity=(self.group.stat().st_dev,self.group.stat().st_ino);self.job=self.log=None;self.identity=self.worker_identity=None;self.closed=False
        self.report={'schema':'crg-own-campaign-observer-v1','phase':'preparing','run_id':self.run,'role':role,'observer_source_sha256':args.wait_timeline_sha256,'worker_source_sha256':worker_sha,'group_device':self.group_identity[0],'group_inode':self.group_identity[1],'membership_sha256':sha(self.membership.encode()),'PID1':{'pid':own['main'][0],'start_ticks':own['main'][1]},'initial_controls':dict(own['controls']),'checks':[],'formal_original18_accepted':False}
        self.verify();self.persist()
    def persist(self):
        p=self.report_path.with_suffix('.candidate');raw=(json.dumps(self.report,indent=2)+'\n').encode();assert len(raw)<=131072
        fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        p.replace(self.report_path)
    def verify(self):
        assert (self.group.stat().st_dev,self.group.stat().st_ino)==self.group_identity
        for pid,start in [self.own['main'],self.own['agent'],self.own['cache']]:assert ticks(pid)==start and Path('/proc',str(pid),'cgroup').read_text()==self.membership
        assert {n:(self.group/n).read_text().strip() for n in self.own['controls']}==self.own['controls']
    def capture(self,entry,job):
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            self.verify();p=find_entry(self.group,self.membership,entry)
            if p is not None:return p
            if job.poll() is not None:raise RuntimeError('own auxiliary exited before capture')
            time.sleep(.1)
        raise RuntimeError('own auxiliary capture deadline')
    def start(self):
        self.verify();source=Path(__file__).parent/'wait-timeline.py';raw=source.read_bytes();assert sha(raw)==self.args.wait_timeline_sha256
        assert self.ex(self.role,'sha256sum',self.worker_entry).stdout.decode().split()[0]==self.worker_sha
        self.ex(self.role,'/bin/bash','-c','set -Ce; umask 077; cat > '+shlex.quote(self.entry)+'; chmod 0444 '+shlex.quote(self.entry),data=raw,timeout=15)
        assert self.ex(self.role,'sha256sum',self.entry).stdout.decode().split()[0]==self.args.wait_timeline_sha256
        cid=self.group.name.removeprefix('cri-containerd-').removesuffix('.scope');assert re.fullmatch(r'[0-9a-f]{64}',cid)
        command='CRG_VENDOR_WAIT_TEST=disposable-loopback-only python '+shlex.quote(self.entry)+' --run-id '+self.run+' --container-id '+cid+' --pid1-start-ticks '+str(self.own['main'][1])+' --membership-sha256 '+self.report['membership_sha256']+' --worker '+shlex.quote(self.worker_entry)+' --worker-sha256 '+self.worker_sha+' --seconds 1800'
        self.log=self.log_path.open('xb');os.fchmod(self.log.fileno(),0o600)
        self.job=subprocess.Popen(['kubectl','exec','-n',self.args.namespace,self.role+'-business','-c',self.role,'--','su','-','postgres','-c',command],stdin=subprocess.DEVNULL,stdout=self.log,stderr=self.log)
        self.identity=self.capture(self.entry,self.job);self.report['observer_host_instance']=dict(self.identity);self.persist()
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            self.check_alive()
            if self.path.exists():
                _,values=timeline(self.path,partial=True)
                if len(values)>=2 and values[0]['kind']=='header' and values[1]['kind']=='sample':
                    head=values[0];assert head['source_sha256']==self.args.wait_timeline_sha256 and head['worker_sha256']==self.worker_sha and head['pid1_start_ticks']==self.own['main'][1] and head['membership_sha256']==self.report['membership_sha256'] and (head['group_device'],head['group_inode'])==self.group_identity
                    assert values[1]['backend_query_phase']=='complete';self.report['admitted_before_worker_launch_monotonic']=time.monotonic();self.report['header']=head;self.report['phase']='observing';self.persist();return
            time.sleep(.1)
        raise RuntimeError('observer first own sample deadline')
    def capture_worker(self,job):
        self.worker_identity=self.capture(self.worker_entry,job);assert self.worker_identity['pid']!=self.identity['pid'];self.report['worker_host_instance']=dict(self.worker_identity);self.persist()
    def check_alive(self):
        self.verify()
        if self.job is not None and self.job.poll() is not None:raise RuntimeError('observer exited during campaign')
    def request_stop(self):
        self.verify();assert self.root.is_dir() and not self.root.is_symlink() and self.root.resolve().is_relative_to(self.folder.resolve())
        value={'schema':'crg-owned-wait-stop-v1','run_id':self.run,'pid1_start_ticks':self.own['main'][1],'membership_sha256':self.report['membership_sha256'],'requested_monotonic':time.monotonic(),'requested_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
        p=self.root/'.stop-request';fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as stream:json.dump(value,stream);stream.write('\n');stream.flush();os.fchown(stream.fileno(),self.root.stat().st_uid,self.root.stat().st_gid);os.fsync(stream.fileno())
        os.link(p,self.root/'stop.json');p.unlink();self.report['stop_request']=value;self.persist()
    def close(self):
        if self.closed:return
        self.closed=True;failure=None
        try:
            assert self.job is not None and self.identity is not None and self.worker_identity is not None
            # A last sample after campaign completion covers the whole native
            # window without changing the workload's exact duration or SLA.
            began=time.monotonic();deadline=began+8
            while time.monotonic()<deadline:
                self.check_alive();_,values=timeline(self.path,partial=True);samples=[v for v in values if v['kind']=='sample']
                if samples and samples[-1]['sample_started_monotonic']>=began:break
                time.sleep(.1)
            else:raise RuntimeError('post-campaign read-only sample deadline')
            self.request_stop();self.report['observer_exit']=self.job.wait(timeout=12)
            raw,values=timeline(self.path);head,terminal=values[0],values[-1];samples=[v for v in values if v['kind']=='sample'];span=samples[-1]['sample_finished_monotonic']-samples[0]['sample_started_monotonic']
            complete=(self.report['observer_exit']==0 and terminal['kind']=='terminal' and terminal['phase']=='complete' and terminal['reason']=='explicit_own_stop_file' and terminal['backend_query_errors']==0 and terminal['failure'] is None and terminal['samples']==len(samples)<=900 and span>=600 and len(samples)>=span/2*.90 and all(b['sample_started_monotonic']-a['sample_started_monotonic']<=8 for a,b in zip(samples,samples[1:])) and all(v['backend_query_phase']=='complete' for v in samples))
            self.report.update(timeline_sha256=sha(raw),timeline_bytes=len(raw),timeline_samples=len(samples),timeline_span_seconds=span,timeline_terminal=terminal)
            self.report['checks'].append({'name':'complete600-own-source-and-bounded-timeline','passed':bool(complete)})
            self.verify();clean=absent(self.identity) and absent(self.worker_identity)
            self.report['checks'].append({'name':'own-auxiliaries-stopped-before-unchanged-PID1-Agent-cache-controls','passed':clean})
            self.report['phase']='passed-diagnostic-only' if complete and clean else 'failed'
        except Exception as error:
            failure=type(error).__name__;self.report['phase']='failed';self.report['fixed_failure']={'stage':'observer_close','class':failure if failure in ['AssertionError','RuntimeError','TimeoutExpired','FileNotFoundError','ProcessLookupError','ValueError'] else 'other','reason':'bounded auxiliary verification failed'}
        finally:
            if self.identity is not None and not absent(self.identity):
                self.report['emergency_own_stop']=True;exact_stop(self.identity,self.membership)
            if self.job is not None:
                try:self.report['observer_exec_exit']=self.job.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    self.job.terminate()
                    try:self.job.wait(timeout=5)
                    except subprocess.TimeoutExpired:self.job.kill();self.job.wait(timeout=5)
                    self.report['observer_exec_cleanup_pending_original_Pod']=True;self.report['phase']='failed'
            if self.log is not None:self.log.close()
            self.report['observer_original_absent']=absent(self.identity);self.persist()
        return self.report
