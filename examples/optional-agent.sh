#!/usr/bin/env bash
# Source from your EXISTING supervisor. Do not enable errexit in the caller.
# This function always returns success. CRG failure cannot decide business status.
crg_start_optional() {
  local binary="${CRG_BIN:-/opt/crg/crg}" config="${CRG_CONFIG:-/etc/crg/config.json}"
  CRG_HELPER_PID=
  if [[ ! -x "$binary" || ! -r "$config" ]]; then
    printf '%s\n' 'CRG optional files unavailable; business continues' >&2 || :
    return 0
  fi
  (
    # Isolate shell options and errors from the business supervisor.
    set +e
    child= nap= delay=5
    stop_optional() {
      trap - TERM INT
      [[ -z "$nap" ]] || kill -TERM "$nap" 2>/dev/null
      if [[ -n "$child" ]]; then
        kill -TERM "$child" 2>/dev/null
        # Never let an auxiliary process ignoring TERM block business shutdown.
        for (( attempt=0; attempt<20; attempt++ )); do
          kill -0 "$child" 2>/dev/null || break
          sleep 0.1
        done
        kill -KILL "$child" 2>/dev/null
      fi
      exit 0
    }
    trap stop_optional TERM INT
    while :; do
      "$binary" run --config "$config" &
      child=$!
      wait "$child"
      child=
      sleep "$delay" & nap=$!
      wait "$nap"; nap=
      (( delay < 300 )) && delay=$((delay*2))
      (( delay > 300 )) && delay=300
    done
  ) &
  CRG_HELPER_PID=$!
  return 0
}
