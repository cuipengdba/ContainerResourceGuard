//go:build linux && amd64

package main

import "testing"

func fe(tid uint32, call, direction string, mono uint64) Event {
	return Event{PID: 123, TID: tid, CgroupID: 456, Call: call, Direction: direction, Mono: mono}
}
func TestNestedAndInterleavedFunctionsPreserveAllFrames(t *testing.T) {
	events := []Event{fe(1, "write", "enter", 1), fe(1, "outer", "function_enter", 2), fe(1, "inner", "function_enter", 3), fe(2, "outer", "function_enter", 4), fe(1, "inner", "function_enter", 5), fe(1, "inner", "function_exit", 7), fe(2, "outer", "function_exit", 8), fe(1, "inner", "function_exit", 11), fe(1, "outer", "function_exit", 20), fe(1, "write", "exit", 21)}
	pairs, issues := pairFunctions(events)
	if len(issues) != 0 || len(pairs) != 4 {
		t.Fatal(pairs, issues)
	}
	for i, want := range []uint64{2, 4, 8, 18} {
		if pairs[i].Elapsed != want {
			t.Fatal(i, pairs[i])
		}
	}
}
func TestMissingOrMismatchedFramesNeverBecomeComplete(t *testing.T) {
	for name, events := range map[string][]Event{"missing-entry": {fe(1, "wait", "function_exit", 9)}, "missing-return": {fe(1, "wait", "function_enter", 1)}, "out-of-order-return": {fe(1, "outer", "function_enter", 1), fe(1, "inner", "function_enter", 2), fe(1, "outer", "function_exit", 9)}, "clock-regression": {fe(1, "wait", "function_enter", 9), fe(1, "wait", "function_exit", 1)}, "cross-cgroup": {fe(1, "wait", "function_enter", 1), {PID: 123, TID: 1, CgroupID: 999, Call: "wait", Direction: "function_exit", Mono: 9}}} {
		t.Run(name, func(t *testing.T) {
			pairs, issues := pairFunctions(events)
			if len(issues) == 0 || len(pairs) != 0 {
				t.Fatal(pairs, issues)
			}
		})
	}
}
func TestDepthBoundMakesStreamIncomplete(t *testing.T) {
	events := []Event{}
	for i := 0; i < 65; i++ {
		events = append(events, fe(1, "recursive", "function_enter", uint64(i+1)))
	}
	pairs, issues := pairFunctions(events)
	if len(pairs) != 0 || len(issues) == 0 {
		t.Fatal(pairs, issues)
	}
}
