#!/usr/bin/env python3
"""Exercise generated supervisor changes with independent business/cache processes."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('integrate',root/'scripts/integrate-supervisor.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
fixture='''#!/usr/bin/env bash
set -Eeuo pipefail
business_pid=
guard_pid=
stopping=0
stop_both() {
  if (( stopping )); then return; fi
  stopping=1
  trap - TERM INT
  [[ -z "$guard_pid" ]] || kill -TERM "$guard_pid" 2>/dev/null || :
  [[ -z "$guard_pid" ]] || wait "$guard_pid" 2>/dev/null || :
}
trap 'stop_both; exit 0' TERM INT
start_guard() {
  "$CCG_BIN" &
  guard_pid=$!
}
"$BUSINESS_START" &
business_pid=$!
start_guard
set +e
wait "$business_pid"
status=$?
stop_both
exit "$status"
'''
for bad in ('#!/bin/sh\nexec app\n',fixture.replace('stopping=0','stopping=1'),fixture+'# CRG OPTIONAL\n'):
    try: module.propose(bad)
    except ValueError:pass
    else:raise AssertionError('accepted unsupported/already-patched source')
with tempfile.TemporaryDirectory() as tmp:
    work=Path(tmp)
    original=work/'original.sh';original.write_text(fixture)
    out=work/'review'
    subprocess.run([sys.executable,str(root/'scripts/integrate-supervisor.py'),str(original),'--output-dir',str(out)],check=True,capture_output=True)
    assert original.read_text()==fixture and (out/'supervisor.original').read_text()==fixture
    proposed=out/'supervisor.proposed.sh'
    subprocess.run(['bash','-n',str(proposed)],check=True)
    for name,text in {'business':'echo BUSINESS_STARTED; sleep 0.5; echo BUSINESS_FINISHED; exit 37',
                      'cache':'echo CACHE_STARTED; exec sleep 60'}.items():
        file=work/name;file.write_text('#!/bin/bash\n'+text+'\n');file.chmod(0o755)
    (work/'config.json').write_text('{"percent":20}\n')
    for scenario in ('missing','denied','invalid','crash','hang','ignore-term'):
        agent=work/scenario
        if scenario!='missing':
            agent.write_text('#!/bin/bash\n'+('trap "" TERM; exec sleep 60' if scenario=='ignore-term' else 'exec sleep 60' if scenario=='hang' else 'exit 7')+'\n')
            agent.chmod(0o644 if scenario=='denied' else 0o755)
        env=dict(os.environ,CRG_HELPER_SCRIPT=str(root/'examples/optional-agent.sh'),CRG_BIN=str(agent),CRG_CONFIG=str(work/'config.json'),BUSINESS_START=str(work/'business'),CCG_BIN=str(work/'cache'))
        start=time.monotonic()
        p=subprocess.run(['bash',str(proposed)],env=env,text=True,capture_output=True,timeout=9)
        assert p.returncode==37,(scenario,p.returncode,p.stdout,p.stderr)
        assert all(s in p.stdout for s in ('BUSINESS_STARTED','BUSINESS_FINISHED','CACHE_STARTED')),p.stdout
        assert time.monotonic()-start<8
        print('PASS generated-patch-'+scenario+' business_exit=37 cache_started=true')
