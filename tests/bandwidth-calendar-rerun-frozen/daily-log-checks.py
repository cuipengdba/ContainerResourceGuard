from pathlib import Path
import importlib.util,json,os,tempfile

spec=importlib.util.spec_from_file_location('daily',Path(__file__).with_name('daily-log-continuity.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
passed=[]
def line(day,event,**fields):return (json.dumps({'time':day+'T00:02:18+08:00','event':event,'fields':fields})+'\n').encode()
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
print(json.dumps({'phase':'passed','count':len(passed),'checks':passed,'native_permissions_checked':os.name!='nt','production_code_changed':False}))
