"""Verify append across Agent restarts while allowing local-calendar rotation.

This short-lived fixture cannot cross the 30-day/1GB retention boundaries.
Never require a closed previous-day file to grow on the following day.
"""
from pathlib import Path
import datetime,json,os,re,stat

MAX_FILE=8*1024*1024
def snapshot(directory):
    directory=Path(directory);assert directory.is_dir() and not directory.is_symlink()
    paths=sorted(directory.glob('crg-*.log'));assert 1<=len(paths)<=3
    result={}
    for path in paths:
        assert re.fullmatch(r'crg-\d{4}-\d{2}-\d{2}\.log',path.name)
        before=path.lstat();assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=MAX_FILE
        if os.name!='nt':assert stat.S_IMODE(before.st_mode)==0o600
        fd=os.open(str(path),os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
        with os.fdopen(fd,'rb') as stream:
            opened=os.fstat(stream.fileno());assert (opened.st_dev,opened.st_ino)==(before.st_dev,before.st_ino)
            raw=stream.read(MAX_FILE+1)
        assert len(raw)<=MAX_FILE and raw.endswith(b'\n') and raw
        for line in raw.splitlines():
            event=json.loads(line);stamp=datetime.datetime.fromisoformat(event['time']);assert stamp.tzinfo is not None
            assert path.name=='crg-'+stamp.strftime('%Y-%m-%d')+'.log'
        result[path.name]=raw
    return result

def verify(previous,directory,version,revision):
    current=snapshot(directory);assert previous and set(previous).issubset(current)
    appended={}
    for name,raw in current.items():
        old=previous.get(name,b'');assert raw.startswith(old), 'PERSISTED_PREFIX_CHANGED'
        if len(raw)>len(old):appended[name]=raw[len(old):]
    assert appended,'NO_LOG_APPEND_OR_NEW_DAY'
    events=[json.loads(line) for raw in appended.values() for line in raw.splitlines()]
    starts=[v for v in events if v['event']=='agent_start'];assert len(starts)==1,'EXACTLY_ONE_NEW_AGENT_START_REQUIRED'
    assert starts[0]['fields']['version']==version and starts[0]['fields']['revision']==revision
    return {'historical_files_preserved':sorted(previous),'appended_files':sorted(appended),'new_daily_files':sorted(set(current)-set(previous)),'appended_bytes':sum(map(len,appended.values())),'new_agent_start':starts[0]['time'],'previous_day_growth_required':False}

def evaluate(previous,directory,version,revision):
    try:return {'passed':True,'log_continuity':verify(previous,directory,version,revision)}
    except (AssertionError,ValueError,KeyError,OSError) as error:return {'passed':False,'log_continuity_error':type(error).__name__+': '+str(error)}
