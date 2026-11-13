package guard

import (
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestMemoryExtrasValidationZeroSwapAndPlanCaps(t *testing.T) {
	for _, raw := range []string{`{"percent":20,"memory_high":"0B"}`, `{"percent":20,"memory_high":"15MiB"}`, `{"percent":20,"memory_swap_max":"-1"}`, `{"percent":20,"memory_swap_max":"1B"}`, `{"resource_mode":"manual","limits":{"memory_max":"1GiB"},"memory_high":"2GiB"}`} {
		var c Config
		if Decode([]byte(raw), &c) == nil && c.Validate() == nil {
			t.Fatal(raw)
		}
	}
	c := Config{Percent: 20, MemoryHigh: "512MiB", MemorySwapMax: "0B"}
	if err := c.Validate(); err != nil {
		t.Fatal(err)
	}
	s, w, err := memoryExtras(c, Environment{}, nil, true, 1<<30, 1<<30)
	if err != nil || len(w) != 0 || len(s) != 2 || s[0].Value != "536870912" || s[1].Value != "0" {
		t.Fatal(s, w, err)
	}
	_, _, err = memoryExtras(c, Environment{}, nil, true, 256<<20, 256<<20)
	if err == nil {
		t.Fatal("high exceeds requested percent memory budget")
	}
	original := map[string]string{"memory.high:": "268435456", "memory.swap.max:": "0"}
	c.MemorySwapMax = "1GiB"
	s, w, err = memoryExtras(c, Environment{}, original, false, 0, 0)
	if err != nil || len(w) != 2 || s[0].Value != "268435456" || s[1].Value != "0" {
		t.Fatal(s, w, err)
	}
}

func TestMemoryHighAndSwapApplyRestoreAndExternalConflict(t *testing.T) {
	e, f := fixture(t)
	cpu := 1.0
	e.Config.ResourceMode = "manual"
	e.Config.Limits = &ManualLimits{CPUCores: &cpu}
	e.Pause = func(time.Duration) {}
	high := filepath.Join(e.Env.Target, "memory.high")
	swap := filepath.Join(e.Env.Target, "memory.swap.max")
	f.data[high] = "max"
	f.data[swap] = "max"
	f.data[filepath.Join(e.Env.Target, "memory.swap.current")] = "0"
	e.Config.MemoryHigh = "512MiB"
	e.Config.MemorySwapMax = "0B"
	p := Plan{Settings: []Setting{{File: "memory.high", Value: "536870912"}, {File: "memory.swap.max", Value: "0"}}}
	if s := e.Reconcile(p); s.State != "managed" || f.data[high] != "536870912" || f.data[swap] != "0" {
		t.Fatal(s)
	}
	e.Config.MemoryHigh = ""
	e.Config.MemorySwapMax = ""
	if s := e.Reconcile(Plan{}); s.State != "managed" || f.data[high] != "max" || f.data[swap] != "max" || len(e.Journal.Mutations) != 0 {
		t.Fatal(s)
	}
	e.Config.MemoryHigh = "512MiB"
	e.Config.MemorySwapMax = "0B"
	e.Reconcile(p)
	f.data[high] = "805306368"
	if s := e.Reconcile(p); s.State != "degraded" || s.Items[0].State != "conflict" {
		t.Fatal(s)
	}
	if s := e.Restore(); s.State != "degraded" || f.data[high] != "805306368" {
		t.Fatal(s)
	}
}

func TestHighAllowsReclaimBelowUsageWhileSwapDecreaseStaysProtected(t *testing.T) {
	e, f := fixture(t)
	e.Pause = func(time.Duration) {}
	high := filepath.Join(e.Env.Target, "memory.high")
	swap := filepath.Join(e.Env.Target, "memory.swap.max")
	f.data[high] = "max"
	f.data[swap] = "max"
	f.data[filepath.Join(e.Env.Target, "memory.current")] = "524288000"
	f.data[filepath.Join(e.Env.Target, "memory.swap.current")] = "134217728"
	r := e.Apply(Plan{Settings: []Setting{{File: "memory.high", Value: "536870912"}, {File: "memory.swap.max", Value: "0"}}})
	if r.State != "degraded" || len(f.writes) != 1 || r.Items[0].State != "applied" || !strings.Contains(r.Items[1].Detail, "unsafe swap") {
		t.Fatal(r)
	}
	f.data[filepath.Join(e.Env.Target, "memory.current")] = "1048576"
	f.data[filepath.Join(e.Env.Target, "memory.swap.current")] = "0"
	r = e.Apply(Plan{Settings: []Setting{{File: "memory.high", Value: "536870912"}, {File: "memory.swap.max", Value: "0"}}})
	if r.State != "managed" || len(f.writes) != 2 {
		t.Fatal(r)
	}
}

func TestSwapGrowthAfterIntentAndRestoringOriginalZero(t *testing.T) {
	e, f := fixture(t)
	swap := filepath.Join(e.Env.Target, "memory.swap.max")
	used := filepath.Join(e.Env.Target, "memory.swap.current")
	f.data[swap] = "max"
	f.data[used] = "0"
	e.Persist = func(Journal) error { f.data[used] = "4096"; return nil }
	if s := e.Apply(Plan{Settings: []Setting{{File: "memory.swap.max", Value: "0"}}}); s.State != "degraded" || len(f.writes) != 0 {
		t.Fatal(s)
	}
	// New fixture owns an expanded budget whose true original was zero.
	e, f = fixture(t)
	swap = filepath.Join(e.Env.Target, "memory.swap.max")
	used = filepath.Join(e.Env.Target, "memory.swap.current")
	f.data[swap] = "0"
	f.data[used] = "0"
	if s := e.Apply(Plan{Settings: []Setting{{File: "memory.swap.max", Value: "536870912"}}}); s.State != "managed" {
		t.Fatal(s)
	}
	f.data[used] = "134217728"
	if s := e.Restore(); s.State != "degraded" || f.data[swap] != "536870912" {
		t.Fatal(s)
	}
	f.data[used] = "0"
	if s := e.Restore(); s.State != "restored" || f.data[swap] != "0" {
		t.Fatal(s)
	}
}
