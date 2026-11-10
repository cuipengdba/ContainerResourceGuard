package guard

import (
	"bytes"
	"strings"
	"testing"
)

const testSupervisor = `#!/usr/bin/env bash
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
`

func TestSupervisorTemplateLeavesBusinessAndCacheAnchorsUnchanged(t *testing.T) {
	o := SupervisorOptions{Binary: "/opt/crg/bin/crg", Config: "/etc/crg/config.json", Helper: "/opt/crg/optional-agent.sh"}
	b, err := proposedSupervisor([]byte(testSupervisor), o)
	if err != nil {
		t.Fatal(err)
	}
	for _, s := range []string{"\"$BUSINESS_START\" &\nbusiness_pid=$!\nstart_guard\n# CRG OPTIONAL BEGIN", "wait \"$business_pid\"\nstatus=$?", "exit \"$status\"", "\"$CCG_BIN\" &\n  guard_pid=$!"} {
		if !bytes.Contains(b, []byte(s)) {
			t.Fatalf("business/cache logic changed: %q", s)
		}
	}
	if !bytes.Contains(b, []byte("CRG_BIN='/opt/crg/bin/crg'\nCRG_CONFIG='/etc/crg/config.json'")) {
		t.Fatal("persistent explicit paths missing")
	}
	for _, bad := range []string{"#!/bin/sh\nexec app\n", strings.Replace(testSupervisor, "stopping=0", "stopping=1", 1), testSupervisor + "# CRG OPTIONAL\n", strings.ReplaceAll(testSupervisor, "\n", "\r\n"), testSupervisor + "\x00", testSupervisor + "business_pid=\nguard_pid=\nstopping=0\n", strings.Replace(testSupervisor, "|| :\n  [[ -z \"$guard_pid\" ]] || wait", "|| false\n  [[ -z \"$guard_pid\" ]] || wait", 1)} {
		if _, err := proposedSupervisor([]byte(bad), o); err == nil {
			t.Fatal("unknown/ambiguous/invalid layout accepted")
		}
	}
}

func TestSupervisorLiteralCannotTurnPathIntoShellCode(t *testing.T) {
	if s := shellLiteral("/data/a'$(touch bad);b"); s != "'/data/a'\"'\"'$(touch bad);b'" {
		t.Fatal(s)
	}
}
