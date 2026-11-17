package guard

import (
	"errors"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func windowFixture(t *testing.T) (*Engine, *fakeFiles, *time.Time) {
	t.Helper()
	e, f := fixture(t)
	e.Config.MemoryStableSeconds, e.Config.IntervalSeconds = 2, 1
	e.Pause = func(time.Duration) {}
	f.data[filepath.Join(e.Env.Target, "memory.events")] = "high 0\nmax 0\noom 0\noom_kill 0\n"
	now := time.Unix(1000, 0)
	e.Now = func() time.Time { return now }
	return e, f, &now
}

func TestWindowRequiresSpacedHistoryWithoutWritingIntent(t *testing.T) {
	e, f, now := windowFixture(t)
	p := Plan{Settings: []Setting{{File: "memory.max", Value: "67108864"}}}
	persisted := 0
	e.Persist = func(Journal) error { persisted++; return nil }
	for i := 0; i < 10; i++ {
		r := e.Apply(p)
		if !MemoryWindowPending(r) || r.State != "degraded" {
			t.Fatal(r)
		}
	}
	*now = now.Add(time.Second)
	if r := e.Apply(p); !MemoryWindowPending(r) {
		t.Fatal(r)
	}
	if len(f.writes) != 0 || persisted != 0 {
		t.Fatal("waiting wrote a limit or durable intent", f.writes, persisted)
	}
	*now = now.Add(time.Second)
	if r := e.Apply(p); r.State != "managed" || r.Items[0].ReasonCode != "applied" {
		t.Fatal(r)
	}
	if len(f.writes) != 1 || persisted != 2 {
		t.Fatal("lost write-ahead/finalization", f.writes, persisted)
	}
}

func TestWindowResetsAfterGapPressureTargetOrObserve(t *testing.T) {
	for _, scenario := range []string{"gap", "backwards", "events", "pressure", "target", "observe", "missing-events", "malformed-events"} {
		t.Run(scenario, func(t *testing.T) {
			e, f, now := windowFixture(t)
			p := Plan{Settings: []Setting{{File: "memory.max", Value: "67108864"}}}
			e.Apply(p)
			*now = now.Add(time.Second)
			e.Apply(p)
			*now = now.Add(time.Second)
			switch scenario {
			case "gap":
				*now = now.Add(10 * time.Second)
			case "backwards":
				*now = now.Add(-10 * time.Second)
			case "events":
				f.data[filepath.Join(e.Env.Target, "memory.events")] = "high 1\nmax 0\noom 0\noom_kill 0"
			case "pressure":
				f.data[filepath.Join(e.Env.Target, "memory.pressure")] = "some avg10=20 avg60=1 avg300=1 total=1"
			case "target":
				p.Settings[0].Value = "100663296"
			case "observe":
				e.Config.Mode = "observe"
				e.Apply(p)
				e.Config.Mode = "enforce"
			case "missing-events":
				delete(f.data, filepath.Join(e.Env.Target, "memory.events"))
			case "malformed-events":
				f.data[filepath.Join(e.Env.Target, "memory.events")] = "high 0\nmax x\noom 0\noom_kill 0"
			}
			r := e.Apply(p)
			if r.State != "degraded" || len(f.writes) != 0 {
				t.Fatal("unsafe window survived change", r, f.writes)
			}
		})
	}
}

func TestWindowTrendAndPostIntentAllocation(t *testing.T) {
	e, f, now := windowFixture(t)
	p := Plan{Settings: []Setting{{File: "memory.max", Value: "67108864"}}}
	used := filepath.Join(e.Env.Target, "memory.current")
	f.data[used] = "1048576"
	e.Apply(p)
	*now = now.Add(time.Second)
	// Each individual 50ms sample is flat and has headroom, but the observed
	// cross-cycle growth projects another 39MiB into a remaining 24MiB budget.
	f.data[used] = "41943040"
	r := e.Apply(p)
	if r.Items[0].ReasonCode != "memory_safety" || len(f.writes) != 0 {
		t.Fatal(r)
	}
	f.data[used] = "1048576"
	for i := 0; i < 2; i++ {
		*now = now.Add(time.Second)
		e.Apply(p)
	}
	*now = now.Add(time.Second)
	e.Persist = func(Journal) error { f.data[used] = "62914560"; return nil }
	r = e.Apply(p)
	if r.Items[0].ReasonCode != "memory_safety" || len(f.writes) != 0 || e.Journal.Mutations["memory.max:"].Pending == "" {
		t.Fatal("post-intent safety or recoverability lost", r)
	}
}

func TestWindowRestoresLowerOriginalWithoutRepeatedJournalWrites(t *testing.T) {
	e, f, now := windowFixture(t)
	mem := filepath.Join(e.Env.Target, "memory.max")
	f.data[mem] = "67108864"
	if r := e.Apply(Plan{Settings: []Setting{{File: "memory.max", Value: "134217728"}}}); r.State != "managed" {
		t.Fatal("increase should not wait", r)
	}
	persisted := 0
	e.Persist = func(Journal) error { persisted++; return nil }
	for i := 0; i < 2; i++ {
		r := e.Restore()
		if !MemoryWindowPending(r) || f.data[mem] != "134217728" || persisted != 0 {
			t.Fatal(r, persisted)
		}
		*now = now.Add(time.Second)
	}
	if r := e.Restore(); r.State != "restored" || f.data[mem] != "67108864" || len(e.Journal.Mutations) != 0 {
		t.Fatal(r)
	}
}

func TestWindowRestartAndSlowRestorePersistence(t *testing.T) {
	e, f, now := windowFixture(t)
	mem := filepath.Join(e.Env.Target, "memory.max")
	f.data[mem] = "67108864"
	e.Apply(Plan{Settings: []Setting{{File: "memory.max", Value: "134217728"}}})
	e.Restore()
	*now = now.Add(time.Second)
	e.Restore()
	// A new process has its journal, never a borrowed in-memory safe window.
	e.memoryWindows = nil
	*now = now.Add(time.Second)
	if r := e.Restore(); !MemoryWindowPending(r) {
		t.Fatal(r)
	}
	*now = now.Add(time.Second)
	e.Restore()
	*now = now.Add(time.Second)
	e.Persist = func(Journal) error { f.data[filepath.Join(e.Env.Target, "memory.current")] = "62914560"; return nil }
	r := e.Restore()
	if r.Items[0].ReasonCode != "memory_safety" || f.data[mem] != "134217728" {
		t.Fatal("slow fsync invalidated restore guard", r)
	}
}

func TestMemoryWindowConfigurationAndReasonContract(t *testing.T) {
	for _, n := range []int{-1, 1, 3601} {
		c := Config{Percent: 20, MemoryStableSeconds: n}
		if c.Validate() == nil {
			t.Fatal("invalid window", n)
		}
	}
	for _, n := range []int{0, 2, 3600} {
		c := Config{Percent: 20, MemoryStableSeconds: n}
		if c.Validate() != nil {
			t.Fatal("valid window", n)
		}
	}
	e, f := fixture(t)
	p := Plan{Settings: []Setting{{File: "cpu.max", Value: "100000 100000"}}}
	f.fail = errors.New("secret-presentation-text")
	r := e.Apply(p)
	if r.Items[0].ReasonCode != "controller_write" {
		t.Fatal(r)
	}
	f.fail = nil
	if r = e.Apply(p); r.Items[0].ReasonCode != "applied" {
		t.Fatal(r)
	}
	f.data[filepath.Join(e.Env.Target, "cpu.max")] = "200000 100000"
	if r = e.Apply(p); r.Items[0].ReasonCode != "external_conflict" {
		t.Fatal(r)
	}
	if strings.Contains(r.Items[0].ReasonCode, "secret") {
		t.Fatal("reason must not come from arbitrary error text")
	}
}
