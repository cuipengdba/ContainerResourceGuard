"""Read only the PostgreSQL processes in one declared, verified test leaf."""
from pathlib import Path,PurePosixPath
import datetime,json,os,re,time

def small(path,maximum):
    with path.open('rb') as stream:data=stream.read(maximum+1)
    if len(data)>maximum:raise ValueError('bounded proc read exceeded')
    return data.decode('utf-8',errors='replace').strip()

def group_path(row):
    text=row['group'];group=PurePosixPath(text);cid=row['container_id'];uid=row['pod_uid']
    if not re.fullmatch('[0-9a-f]{64}',cid) or not re.fullmatch('[0-9a-f-]{36}',uid):raise ValueError('invalid test identity')
    if '\\' in text or '..' in group.parts or str(group)!=text or not text.startswith('/sys/fs/cgroup/kubepods.slice/') or group.name!='cri-containerd-'+cid+'.scope' or ('pod'+uid.replace('-','_')) not in group.parent.name:raise ValueError('not the declared own container leaf')
    return Path(group)

def fields(proc):
    data=small(proc/'stat',4096);return data[data.rfind(')')+2:].split()

def process(pid,group,proc_root=Path('/proc'),readlink=os.readlink):
    proc=proc_root/str(pid);before=fields(proc);expected='0::/'+group.relative_to('/sys/fs/cgroup').as_posix()
    if small(proc/'cgroup',4096).splitlines()!=[expected]:return None
    if Path(readlink(proc/'exe')).name not in ['postgres','pg_ctl']:return None
    row={'pid':int(pid),'start_ticks':int(before[19]),'state':before[0],'parent_pid':int(before[1]),'program':Path(readlink(proc/'exe')).name}
    for name,maximum in [('wchan',256),('stack',4096),('syscall',256),('io',1024)]:
        try:row[name]=small(proc/name,maximum)
        except (OSError,ValueError) as error:row[name]={'unavailable':type(error).__name__}
    status=small(proc/'status',8192);row['status']={k:v.strip() for line in status.splitlines() if ':' in line for k,v in [line.split(':',1)] if k in ['NSpid','Threads','VmRSS','RssAnon','RssFile','VmSwap','voluntary_ctxt_switches','nonvoluntary_ctxt_switches']}
    row['standard_fds']={}
    for fd in ['0','1','2']:
        try:
            target=readlink(proc/'fd'/fd);match=re.fullmatch(r'(pipe|socket):\[([0-9]+)\]',target)
            row['standard_fds'][fd]={'kind':match[1],'inode':int(match[2])} if match else {'kind':'other','path_withheld':True}
        except OSError as error:row['standard_fds'][fd]={'unavailable':type(error).__name__}
    after=fields(proc)
    if before[19]!=after[19] or small(proc/'cgroup',4096).splitlines()!=[expected]:return None
    return row

def main(tools):
    plan=json.loads((tools/'plan.json').read_bytes());root=Path(plan['output']);case=plan['cases'][0];path=root/case/'report.json'
    assert root==Path('/var/tmp/crg-rebuild1060-results-20261113') and case=='dbs-20'
    output=root/'pg-process-observer.json';report={'schema':'crg-own-PG-startup-process-observation-v1','phase':'waiting-for-second-boot','started_epoch':time.time(),'read_only_no_cmdline_or_process_memory_or_fd_contents':True,'samples':[],'errors':[]};deadline=time.monotonic()+plan['criteria']['case_outer_containment_seconds']+60
    def save():
        data=(json.dumps(report,indent=2)+'\n').encode()
        if len(data)>8*1024**2:raise ValueError('diagnostic output bound exceeded')
        temp=output.with_suffix('.tmp');temp.write_bytes(data);os.replace(temp,output)
    save()
    try:
        while time.monotonic()<deadline:
            if (root/'driver-terminal.json').exists():report['phase']='driver-terminal';break
            try:
                current=json.loads(path.read_bytes());item=next(iter(current['roles'].values()));starts=item['starts']
                if len(starts)<2 or not all(starts[1].get(k) is not None for k in ['group','gate_epoch','init_pid','init_start_ticks','pod_uid','container_id']):time.sleep(2);continue
                row=starts[1];group=group_path(row)
                if not group.exists():report['phase']='second-boot-group-gone';break
                init=Path('/proc',str(row['init_pid']));assert int(fields(init)[19])==row['init_start_ticks'] and small(init/'cgroup',4096).splitlines()==['0::/'+str(group.relative_to('/sys/fs/cgroup'))]
                assert os.stat(init/'ns/pid').st_ino!=os.stat('/proc/self/ns/pid').st_ino
                sample={'epoch':time.time(),'elapsed_since_second_gate':time.time()-row['gate_epoch'],'group':str(group),'pod_uid':row['pod_uid'],'container_id':row['container_id'],'postgresql':[]}
                members=small(group/'cgroup.procs',16384).splitlines();assert len(members)<=256
                for member in members:
                    try:value=process(int(member),group)
                    except (FileNotFoundError,ProcessLookupError):continue
                    if value is not None:sample['postgresql'].append(value)
                if len(sample['postgresql'])>4:report['errors'].append({'error':'PG process sample exceeds4; remainder withheld','epoch':time.time()});sample['postgresql']=sample['postgresql'][:4]
                report['samples'].append(sample);report['phase']='observing-second-boot';save()
                if len(report['samples'])>=180:report['phase']='bounded-sample-count-ended';break
                time.sleep(5)
            except (FileNotFoundError,json.JSONDecodeError,StopIteration):time.sleep(.2)
        else:report['phase']='observation-deadline-ended'
    except BaseException as error:report['phase']='observation-error';report['errors'].append({'class':type(error).__name__})
    finally:report['ended_epoch']=time.time();save()

if __name__=='__main__':
    import sys
    main(Path(sys.argv[1]))
