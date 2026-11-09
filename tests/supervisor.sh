#!/usr/bin/env bash
# Real processes: auxiliary failures/hangs must preserve original business exit.
set -euo pipefail
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
printf '{"percent":20}\n' > "$work/config.json"
cat > "$work/business" <<'SH'
#!/usr/bin/env bash
printf 'BUSINESS_STARTED\n'
sleep 2
printf 'BUSINESS_FINISHED\n'
exit 37
SH
chmod 0755 "$work/business"
for scenario in missing denied invalid crash hang; do
  agent="$work/$scenario"
  case "$scenario" in
    missing) : ;;
    denied) printf '#!/bin/sh\nexit 1\n' > "$agent"; chmod 0644 "$agent" ;;
    invalid|crash) printf '#!/bin/sh\nexit 7\n' > "$agent"; chmod 0755 "$agent" ;;
    hang) printf '#!/bin/sh\nexec sleep 60\n' > "$agent"; chmod 0755 "$agent" ;;
  esac
  started=$SECONDS
  set +e
  CRG_BIN="$agent" CRG_CONFIG="$work/config.json" timeout 10 bash "$repo/examples/supervisor.sh" "$work/business" > "$work/$scenario.log" 2>&1
  code=$?
  set -e
  [[ "$code" == 37 ]] || { cat "$work/$scenario.log"; printf 'FAIL %s exit=%s\n' "$scenario" "$code"; exit 1; }
  grep -q BUSINESS_STARTED "$work/$scenario.log"
  grep -q BUSINESS_FINISHED "$work/$scenario.log"
  (( SECONDS-started < 9 ))
  printf 'PASS optional-agent-%s business_exit=37\n' "$scenario"
done
