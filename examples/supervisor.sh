#!/usr/bin/env bash
# Standalone EXAMPLE. Existing supervisors should source optional-agent.sh instead.
set +e
if (( $# == 0 )); then printf '%s\n' 'usage: supervisor.sh original-command [args...]' >&2; exit 2; fi
business_pid= CRG_HELPER_PID=
stop_children() {
  trap - TERM INT
  [[ -z "$business_pid" ]] || kill -TERM "$business_pid" 2>/dev/null
  [[ -z "$CRG_HELPER_PID" ]] || kill -TERM "$CRG_HELPER_PID" 2>/dev/null
  wait 2>/dev/null
}
trap 'stop_children; exit 143' TERM
trap 'stop_children; exit 130' INT
"$@" & business_pid=$!
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -r "$here/optional-agent.sh" ]]; then
  source "$here/optional-agent.sh"
  crg_start_optional || :
fi
while kill -0 "$business_pid" 2>/dev/null; do sleep 1 & wait $!; done
wait "$business_pid"; status=$?
business_pid=
stop_children
exit "$status"
