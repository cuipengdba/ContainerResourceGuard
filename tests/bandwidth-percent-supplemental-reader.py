"""Read-only supplement for the frozen 1129 runner's stale export directory.

Never changes the frozen job, original export, profile, configuration or logs.
Only four terminal, registered fixture directories are eligible.
"""
from pathlib import Path
import datetime,hashlib,json,os,re,stat

TOOLS=Path('/var/tmp/crg-bandwidth1129-tools-20261113')
ROOT=Path('/var/tmp/crg-bandwidth1129-results-20261113')
PLAN_SHA='b2c68f37f146991e32212b1ec8a3ad3f26869fd771d0956d82bd0daa528c0c5c'
JOB_SHA='3533a4d607b2af8db19b0185c0912423c3c8865037e1fe43790fe65f8483fe3a'
CASES=('dbs-20','hisdbs-20','dbs-30','hisdbs-30')
MAX_FILE=32*1024*1024
MAX_TOTAL=256*1024*1024
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def absent(row):
    try:return int(Path('/proc',str(row['pid']),'stat').read_bytes().rsplit(b')',1)[1].split()[19])!=row['start_ticks']
    except (FileNotFoundError,ProcessLookupError):return True

def read_regular(root,relative):
    path=root/relative
    assert not root.is_symlink() and root.is_dir(), 'ROOT_SHAPE'
    assert path.is_relative_to(root) and '..' not in path.relative_to(root).parts, 'PATH_SCOPE'
    for parent in path.parents:
        if parent==root:break
        assert parent.is_dir() and not parent.is_symlink(), 'PARENT_SHAPE'
    before=path.lstat();assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<=before.st_size<=MAX_FILE, 'FILE_SHAPE'
    fd=os.open(str(path),os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
    with os.fdopen(fd,'rb') as stream:
        opened=os.fstat(stream.fileno());assert (opened.st_dev,opened.st_ino)==(before.st_dev,before.st_ino), 'OPEN_IDENTITY'
        raw=stream.read(MAX_FILE+1)
    after=path.lstat();assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) and len(raw)==before.st_size, 'FILE_CHANGED'
    raw.decode('utf-8');return raw

def collect(root,coordinator):
    assert coordinator['phase'] in ['passed','failed'] and set(coordinator['cases'])==set(CASES), 'TERMINAL_FOUR_CASES'
    rows=[];reports={}
    for case in CASES:
        item=coordinator['cases'][case];assert item['phase'] in ['passed','failed'] and absent(item['driver']), 'DRIVER_TERMINAL'
        raw=read_regular(root,case+'/report.json');assert sha(raw)==item['report_sha256'], 'REPORT_DIGEST';report=json.loads(raw);role,percent=case.split('-');key='preview5-'+role+'-percent'+percent+'-startup';assert set(report['roles'])=={key}, 'ROLE_IDENTITY';reports[case]=sha(raw)
        prefix=case+'/'+key+'/'+role+'-business/'
        sources=[('config.json',prefix+'crg-config/config.json'),('io-profile.json',prefix+'crg-config/io-profile.json')]
        directory=root/prefix/'log/crg';assert directory.is_dir() and not directory.is_symlink(), 'LOG_DIRECTORY'
        logs=sorted(directory.glob('crg-*.log'));assert 1<=len(logs)<=3, 'DAILY_LOG_COUNT'
        for index,path in enumerate(logs):
            assert re.fullmatch(r'crg-\d{4}-\d{2}-\d{2}\.log',path.name), 'DAILY_LOG_NAME'
            sources.append(('daily-'+str(index)+'.log',path.relative_to(root).as_posix()))
        for suffix,relative in sources:
            raw=read_regular(root,relative);rows.append({'filename':case+'-'+suffix,'source_relative_path':relative,'bytes':len(raw),'sha256':sha(raw)})
    total=sum(v['bytes'] for v in rows);assert total<=MAX_TOTAL and 12<=len(rows)<=20 and len({v['filename'] for v in rows})==len(rows), 'TOTAL_BOUNDS'
    return {'schema':'crg-bandwidth1129-readonly-supplemental-index-v1','root':str(root),'job_sha256':JOB_SHA,'plan_sha256':PLAN_SHA,'artifacts':rows,'total_bytes':total,'complete':True,'original_case_report_sha256':reports,'reason':'Frozen runner uses preview4-role-percent-startup export folder; actual driver uses preview5-role-percentN-startup. Original evidence and failure history retained; no business rerun.'}

def main():
    praw=(TOOLS/'plan.json').read_bytes();assert sha(praw)==PLAN_SHA;plan=json.loads(praw);assert plan['job_sha256']==JOB_SHA and tuple(plan['cases'])==CASES and plan['output']==str(ROOT)
    assert all(sha((TOOLS/name).read_bytes())==h for name,h in plan['source_sha256'].items()), 'FROZEN_SOURCE_CHANGED'
    raw=(ROOT/'report.json').read_bytes();co=json.loads(raw);terminal=json.loads((TOOLS/'exit.json').read_bytes());assert terminal['phase']==co['phase'] and terminal['phase'] in ['passed','failed'] and terminal['artifact_index_complete'] and terminal['job_sha256']==co['job_sha256']==JOB_SHA and terminal['plan_sha256']==co['plan_sha256']==PLAN_SHA and terminal['exit']==(0 if co['phase']=='passed' else 1), 'MATRIX_NOT_TERMINAL'
    assert absent(json.loads((TOOLS/'launch.json').read_bytes())), 'RUNNER_STILL_PRESENT'
    result=collect(ROOT,co);result.update(node_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),coordinator_report_sha256=sha(raw),original_index_sha256=sha((TOOLS/'artifact-index.json').read_bytes()),remote_files_changed=False)
    print(json.dumps(result))

if __name__=='__main__':main()
