#!/usr/bin/env python3
"""Generate a reviewable patch and byte-exact backup. Never modify the source."""
import argparse
import difflib
import hashlib
import json
import re
from pathlib import Path

START = '''# CRG OPTIONAL BEGIN
if [[ -r "${CRG_HELPER_SCRIPT:-/opt/crg/optional-agent.sh}" ]]; then
  source "${CRG_HELPER_SCRIPT:-/opt/crg/optional-agent.sh}" || :
  if declare -F crg_start_optional >/dev/null; then crg_start_optional || :; fi
fi
# CRG OPTIONAL END
'''
STOP = '''  # CRG OPTIONAL STOP BEGIN
  if declare -F crg_stop_optional >/dev/null; then crg_stop_optional || :; fi
  # CRG OPTIONAL STOP END
'''

def propose(text):
    if 'CRG OPTIONAL' in text:
        raise ValueError('already contains CRG integration; review existing patch')
    # Match the observed supervisor structure, not vendor start.sh or arbitrary
    # shell scripts. Refuse unknown versions instead of guessing insertion sites.
    anchors = ('business_pid=\nguard_pid=\nstopping=0\n',
               '"$BUSINESS_START" &\nbusiness_pid=$!\nstart_guard\n')
    if any(text.count(s) != 1 for s in anchors):
        raise ValueError('unsupported supervisor layout; manual integration required')
    kill_guard = re.compile(r'(?m)^  \[\[ -z "\$guard_pid" \]\] \|\| kill -TERM "\$guard_pid" 2>/dev/null \|\| (?:true|:)\n')
    if len(kill_guard.findall(text)) != 1:
        raise ValueError('unsupported supervisor shutdown; manual integration required')
    result = text.replace(anchors[0], 'business_pid=\nguard_pid=\nCRG_HELPER_PID=\nstopping=0\n')
    result = kill_guard.sub(lambda m:m.group(0)+STOP,result)
    result = result.replace(anchors[1], anchors[1] + START)
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('--output-dir', type=Path, required=True)
    a = p.parse_args()
    raw = a.source.read_bytes()
    if b'\r' in raw:
        p.error('source must use LF line endings; original is not changed')
    try:
        result = propose(raw.decode('utf-8'))
    except ValueError as e:
        p.error(str(e))
    # A fresh directory makes accidental overwrite of an earlier backup fail.
    a.output_dir.mkdir(parents=True, exist_ok=False)
    (a.output_dir / 'supervisor.original').write_bytes(raw)
    (a.output_dir / 'supervisor.proposed.sh').write_bytes(result.encode('utf-8'))
    patch = ''.join(difflib.unified_diff(raw.decode().splitlines(True), result.splitlines(True),
                                        fromfile='supervisor.original', tofile='supervisor.proposed.sh'))
    (a.output_dir / 'supervisor.patch').write_bytes(patch.encode('utf-8'))
    manifest = {'source_sha256': hashlib.sha256(raw).hexdigest(),
                'proposed_sha256': hashlib.sha256(result.encode()).hexdigest(),
                'source_modified': False,
                'review': 'Run bash -n, inspect patch, verify optional-failure tests before installation. '
                          'Keep the original for atomic rollback at the next planned restart.'}
    (a.output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    main()
