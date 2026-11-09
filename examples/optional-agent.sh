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
    trap '[[ -z "$child" ]] || kill -TERM "$child" 2>/dev/null; [[ -z "$nap" ]] || kill -TERM "$nap" 2>/dev/null; wait 2>/dev/null; exit 0' TERM INT
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
