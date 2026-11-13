from pathlib import Path
import importlib.util,json,os,tempfile

spec=importlib.util.spec_from_file_location('daily',Path(__file__).with_name('daily-log-continuity.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
passed=[]
def line(day,event,**fields):return (json.dumps({'time':day+'T00:02:18.771783656+08:00','event':event,'fields':fields})+'\n').encode()
def check(name,operation,reject=False):
    try:operation()
    except (AssertionError,ValueError,KeyError):
        assert reject,name
    else:assert not reject,name
    passed.append(name)
with tempfile.TemporaryDirectory() as d:
    p=Path(d);old=p/'crg-2026-11-13.log';new=p/'crg-2026-11-14.log';start=lambda day:line(day,'agent_start',version='v1.0.0-preview.5',revision='ced')
    old.write_bytes(start('2026-11-13'));old.chmod(0o600);before=m.snapshot(p);old.write_bytes(old.read_bytes()+start('2026-11-13'))
    check('same-day-restart-appends',lambda:m.verify(before,p,'v1.0.0-preview.5','ced'))
    before=m.snapshot(p);new.write_bytes(line('2026-11-14','log_day_started')+start('2026-11-14'));new.chmod(0o600)
    check('cross-midnight-old-day-unchanged-new-agent-on-new-day',lambda:m.verify(before,p,'v1.0.0-preview.5','ced'))
    before=m.snapshot(p);new.write_bytes(new.read_bytes()+start('2026-11-14'))
    check('restart-after-quiet-midnight-old-and-new-files-already-present',lambda:m.verify(before,p,'v1.0.0-preview.5','ced'))
    before=m.snapshot(p);check('reject-no-append',lambda:m.verify(before,p,'v1.0.0-preview.5','ced'),True)
    new.write_bytes(new.read_bytes()+line('2026-11-14','agent_heartbeat'));check('reject-append-without-new-agent',lambda:m.verify(before,p,'v1.0.0-preview.5','ced'),True)
    new.write_bytes(new.read_bytes()+start('2026-11-14')+start('2026-11-14'));check('reject-two-new-agents',lambda:m.verify(before,p,'v1.0.0-preview.5','ced'),True)
    new.write_bytes(before[new.name]+start('2026-11-14'));old.write_bytes(line('2026-11-13','tampered'));check('reject-history-rewrite',lambda:m.verify(before,p,'v1.0.0-preview.5','ced'),True)
    old.write_bytes(before[old.name]);check('reject-wrong-source',lambda:m.verify(before,p,'v1.0.0-preview.5','wrong'),True)
    new.write_bytes(start('2026-11-13'));check('reject-event-in-wrong-daily-file',lambda:m.snapshot(p),True)
    new.write_bytes(start('2026-11-14'));new.unlink();old.unlink();check('reject-empty-directory',lambda:m.snapshot(p),True)
for value in ['2026-11-14T00:47:53.771783656+08:00','2026-11-14T00:47:53.1Z','2026-11-14T00:47:53-05:30']:
    check('accept-real-RFC3339Nano-'+value,lambda value=value:m.parse_timestamp(value))
for value in ['2026-02-30T00:47:53.771783656+08:00','2026-11-14T00:47:53.1234567890+08:00','2026-11-14T00:47:53+08:99','2026-11-14T00:47:53+24:00','2026-11-14T00:47:53']:
    check('reject-invalid-RFC3339Nano-'+value,lambda value=value:m.parse_timestamp(value),True)
print(json.dumps({'phase':'passed','count':len(passed),'checks':passed,'native_permissions_checked':os.name!='nt','production_code_changed':False}))
