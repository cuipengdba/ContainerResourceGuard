package guard

import (
	"errors"
	"path/filepath"
	"testing"
	"time"
)

func recoveryFixture(t *testing.T) (*Engine, *fakeFiles, Plan, string) {
	t.Helper()
	engine, files := fixture(t)
	leaf := engine.Env.Target
	root := filepath.Dir(leaf)
	engine.verifyHierarchy = func(path string) error {
		if path == root {
			return nil
		}
		return errors.New("outside fixture cgroup filesystem")
	}
	engine.Config.MemoryHighRecovery = true
	control := filepath.Join(leaf, "memory.high")
	files.data[control] = "8388608"
	plan := Plan{Settings: []Setting{{File: "memory.high", Value: "4194304"}}}
	if status := engine.Reconcile(plan); status.State != "managed" {
		t.Fatalf("initial application: %+v", status)
	}
	files.data[control] = "max"
	return engine, files, plan, control
}

func finishedHigh(t *testing.T, engine *Engine) ItemStatus {
	t.Helper()
	select {
	case <-engine.MemoryHighRecoveryDone():
	case <-time.After(5 * time.Second):
		t.Fatal("worker did not finish")
	}
	status, ok := engine.PollMemoryHighRecovery()
	if !ok || len(status.Items) != 1 {
		t.Fatalf("missing finished transaction: %+v", status)
	}
	if err := validateJournal(engine.Journal); err != nil {
		t.Fatal(err)
	}
	return status.Items[0]
}

func TestMemoryHighRecoveryProtectsExternalValuesAndWriteIntent(t *testing.T) {
	const key = "memory.high:"
	for _, test := range []struct {
		name   string
		reason string
		change func(*Engine, *fakeFiles, string) func() error
	}{
		{"tighter hard cap", "memory_high_recovery_blocked", func(e *Engine, f *fakeFiles, _ string) func() error {
			f.data[filepath.Join(e.Env.Target, "memory.max")] = "2097152"
			return nil
		}},
		{"pending mutation", "memory_high_recovery_blocked", func(e *Engine, _ *fakeFiles, _ string) func() error {
			e.Journal.Mutations[key].Pending = "4194304"
			return nil
		}},
		{"identity change after intent", "memory_high_recovery_blocked", func(_ *Engine, _ *fakeFiles, _ string) func() error {
			calls := 0
			return func() error {
				calls++
				if calls == 1 {
					return nil
				}
				return errors.New("identity changed")
			}
		}},
		{"write error", "memory_high_recovery_failed", func(_ *Engine, f *fakeFiles, _ string) func() error {
			f.fail = errors.New("cgroup write rejected")
			return nil
		}},
		{"actual value changed after intent", "memory_high_recovery_blocked", func(e *Engine, f *fakeFiles, path string) func() error {
			e.Persist = func(journal Journal) error {
				if journal.Mutations[key].Pending != "" {
					f.data[path] = "2097152"
				}
				return nil
			}
			return nil
		}},
	} {
		t.Run(test.name, func(t *testing.T) {
			engine, files, plan, path := recoveryFixture(t)
			check := test.change(engine, files, path)
			if check == nil {
				check = func() error { return nil }
			}
			engine.ReconcileLive(plan, 1, check)
			item := finishedHigh(t, engine)
			mutation := engine.Journal.Mutations[key]
			if item.ReasonCode != test.reason || !mutation.Conflict || mutation.Original != "8388608" || len(files.writes) != 1 {
				t.Fatalf("unexpected recovery outcome: %+v, journal %+v, writes %v", item, mutation, files.writes)
			}
			if test.name == "write error" && mutation.Pending != "4194304" {
				t.Fatal("write failure lost the pending intent")
			}
		})
	}
}

type blockedHighWrite struct {
	*fakeFiles
	entered chan struct{}
	release chan struct{}
}

func (f blockedHighWrite) Write(path, value string) error {
	close(f.entered)
	<-f.release
	return f.fakeFiles.Write(path, value)
}

func TestMemoryHighRecoveryDoesNotWaitForKernelWrite(t *testing.T) {
	engine, files, plan, path := recoveryFixture(t)
	entered, release := make(chan struct{}), make(chan struct{})
	engine.Files = blockedHighWrite{files, entered, release}
	engine.ReconcileLive(plan, 3, func() error { return nil })
	select {
	case <-entered:
	case <-time.After(5 * time.Second):
		t.Fatal("the recovery did not reach the kernel write")
	}
	for range 3 {
		status := engine.ReconcileLive(plan, 3, func() error { return errors.New("unexpected second job") })
		if status.Items[0].ReasonCode != "memory_high_recovery_started" {
			t.Fatalf("unexpected status while worker owns writer: %+v", status)
		}
	}
	close(release)
	if item := finishedHigh(t, engine); item.ReasonCode != "memory_high_recovered" || files.data[path] != "4194304" || len(files.writes) != 2 {
		t.Fatalf("unexpected recovery: %+v", item)
	}
	files.data[path] = "max"
	engine.ReconcileLive(plan, 3, func() error { return nil })
	if item := finishedHigh(t, engine); item.ReasonCode != "memory_high_recovery_backoff" || files.data[path] != "max" || len(files.writes) != 2 {
		t.Fatalf("recurring drift was not held: %+v", item)
	}
}

func TestMemoryHighRecoveryCancelsQueuedWriteForNewGeneration(t *testing.T) {
	engine, files, plan, _ := recoveryFixture(t)
	checks := 0
	engine.ReconcileLive(plan, 4, func() error {
		checks++
		if checks == 2 {
			return CancelMemoryHighRecovery(errors.New("configuration source changed"))
		}
		return nil
	})
	item := finishedHigh(t, engine)
	mutation := engine.Journal.Mutations["memory.high:"]
	if item.ReasonCode != "memory_high_recovery_cancelled" || mutation.Pending != "" || mutation.Conflict || len(files.writes) != 1 {
		t.Fatalf("stale generation was not cancelled: %+v, %+v", item, mutation)
	}
}

func TestMemoryHighRecoveryKeepsInterruptedIntentAfterRestart(t *testing.T) {
	engine, files, plan, path := recoveryFixture(t)
	mutation := engine.Journal.Mutations["memory.high:"]
	mutation.Pending = "4194304"
	mutation.HighRecovery.Events = []MemoryHighEvent{{
		TimeUTC: time.Now().UTC().Format(time.RFC3339Nano), Generation: 1,
		Expected: "4194304", Reason: "memory_high_recovery_intent",
	}}
	files.data[path] = "4194304"
	engine.ReconcileLive(plan, 1, func() error { return nil })
	item := finishedHigh(t, engine)
	mutation = engine.Journal.Mutations["memory.high:"]
	if item.ReasonCode != "memory_high_recovery_blocked" || mutation.Pending != "4194304" || !mutation.Conflict || len(files.writes) != 1 {
		t.Fatalf("interrupted write was not preserved: %+v, %+v", item, mutation)
	}
}
