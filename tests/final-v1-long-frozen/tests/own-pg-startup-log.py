"""Read this isolated run's CSV startup log without exporting unrelated rows."""
import csv
import datetime
import hashlib
import io
import os
from pathlib import Path,PurePosixPath
import re
import stat


def _read(path,maximum):
    before=path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>maximum:
        raise ValueError('not-one-bounded-regular-file')
    fd=os.open(str(path),os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
    with os.fdopen(fd,'rb') as stream:
        opened=os.fstat(stream.fileno())
        if (opened.st_dev,opened.st_ino)!=(before.st_dev,before.st_ino):raise ValueError('file-changed-before-read')
        raw=stream.read(maximum+1)
    after=path.lstat()
    if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) or len(raw)!=before.st_size:
        raise ValueError('file-changed-during-read')
    return raw


def collect(folder,run_id):
    """Only isolated fixture mount layout /opt/postgresql -> folder/postgresql.

    All records must belong to the same startup PID/date/window. Mixed logs,
    unsupported formats and unavailable files produce partial without log data.
    """
    result={'schema':'crg-own-PG-startup-CSV-v1','phase':'partial','issues':[]}
    try:
        if not re.fullmatch(r'[0-9]{8,14}',run_id):raise ValueError('invalid-run-id')
        folder=Path(folder);pg=folder/'postgresql';base=pg/'basebackup'/('crg-acceptance-'+run_id)
        startup=_read(base/'standby.log',65536)
        matches=re.findall(rb'(?m)^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)(?:\.\d+)? [^\n]*? \[(\d+)\] ',startup)
        if not matches or len({pid for when,pid in matches})!=1:raise ValueError('startup-identity-not-unique')
        when,pid=matches[0];started=datetime.datetime.strptime(when.decode(),'%Y-%m-%d %H:%M:%S')
        current=_read(base/'standby/current_logfiles',16384);lines=current.decode().splitlines()
        if len(lines)!=1:raise ValueError('not-one-log-destination')
        kind,name=lines[0].split(' ',1);value=PurePosixPath(name)
        if kind!='csvlog' or '..' in value.parts or not str(value).startswith('/opt/postgresql/pg_log/'):
            raise ValueError('unsupported-or-outside-log-destination')
        path=pg/value.relative_to('/opt/postgresql')
        if not path.resolve().is_relative_to(pg.resolve()):raise ValueError('log-path-escapes-fixture')
        raw=_read(path,2*1024**2);rows=list(csv.reader(io.StringIO(raw.decode(),newline=''),strict=True))
        if not rows or any(len(row)<14 or row[3]!=pid.decode() for row in rows):raise ValueError('mixed-or-malformed-startup-PID')
        for row in rows:
            stamp=datetime.datetime.strptime(row[0][:19],'%Y-%m-%d %H:%M:%S');delta=(stamp-started).total_seconds()
            if not 0<=delta<=90:raise ValueError('startup-time-window-mismatch')
        result.update(phase='complete',source_container_path=name,startup_PID=int(pid),startup_first_second=when.decode(),source_bytes=len(raw),source_sha256=hashlib.sha256(raw).hexdigest(),startup_stdout_sha256=hashlib.sha256(startup).hexdigest(),current_logfiles_sha256=hashlib.sha256(current).hexdigest(),records=len(rows),all_records_bound_to_own_startup=True,exact_utf8=raw.decode())
    except (OSError,ValueError,UnicodeError,csv.Error) as error:
        result['issues'].append('startup-log-unavailable-or-unqualified-'+type(error).__name__)
    return result
