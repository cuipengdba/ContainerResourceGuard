//go:build linux && amd64

package main

// Full vendor qualification can spend360s preparing the original workload,
// run600s, and drain a failed native worker for120s. This is a collector-only
// bound; it does not change any of those original business deadlines.
const maximumDiagnosticSeconds = 1200

func validDiagnosticSeconds(seconds int) bool {
	return seconds >= 1 && seconds <= maximumDiagnosticSeconds
}
