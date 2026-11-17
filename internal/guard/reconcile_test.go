package guard

import (
	"path/filepath"
	"testing"
)

func TestModeSwitchRestoresRemovedControlsButObserveNeverWrites(t *testing.T) {
	e, f := fixture(t)
	cpu := 2.0
	e.Config.ResourceMode = "manual"
	e.Config.Limits = &ManualLimits{CPUCores: &cpu, MemoryMax: "64MiB"}
	initial := Plan{Settings: []Setting{{File: "cpu.max", Value: "200000 100000"}, {File: "memory.max", Value: "67108864"}}}
	if r := e.Reconcile(initial); r.State != "managed" {
		t.Fatal(r)
	}
	writes := len(f.writes)
	e.Config.Mode = "observe"
	e.Config.Limits.MemoryMax = ""
	onlyCPU := Plan{Settings: []Setting{{File: "cpu.max", Value: "300000 100000"}}}
	r := e.Reconcile(onlyCPU)
	if r.State != "observe" || len(f.writes) != writes || len(e.Journal.Mutations) != 2 || r.Items[1].State != "retained" {
		t.Fatal(r)
	}
	e.Config.Mode = "enforce"
	r = e.Reconcile(onlyCPU)
	if r.State != "managed" || f.data[filepath.Join(e.Env.Target, "memory.max")] != "max" || len(e.Journal.Mutations) != 1 {
		t.Fatal(r)
	}
	if f.data[filepath.Join(e.Env.Target, "cpu.max")] != "300000 100000" || e.Journal.Mutations["cpu.max:"].Original != "max 100000" {
		t.Fatal("lost CPU original during mode switch")
	}
}

func TestRemovedUnsafeOrExternallyChangedLimitStaysVisible(t *testing.T) {
	e, f := fixture(t)
	cpu := 1.0
	e.Config.ResourceMode = "manual"
	e.Config.Limits = &ManualLimits{CPUCores: &cpu, MemoryMax: "128MiB"}
	mem := filepath.Join(e.Env.Target, "memory.max")
	f.data[mem] = "67108864"
	if r := e.Reconcile(Plan{Settings: []Setting{{File: "memory.max", Value: "134217728"}}}); r.State != "managed" {
		t.Fatal(r)
	}
	f.data[filepath.Join(e.Env.Target, "memory.current")] = "104857600"
	e.Config.Limits.MemoryMax = ""
	p := Plan{Settings: []Setting{{File: "cpu.max", Value: "100000 100000"}}}
	r := e.Reconcile(p)
	if r.State != "degraded" || f.data[mem] != "134217728" || r.Items[1].State != "skipped" || len(e.Journal.Mutations) != 2 {
		t.Fatal(r)
	}
	f.data[mem] = "100663296"
	r = e.Reconcile(p)
	if r.State != "degraded" || f.data[mem] != "100663296" || r.Items[1].State != "conflict" {
		t.Fatal("external removed limit overwritten", r)
	}
	calls := 0
	e.Persist = func(Journal) error { calls++; return nil }
	e.Reconcile(p)
	if calls != 0 {
		t.Fatal("unchanged known conflict repeatedly rewrote journal")
	}
}

func TestTransientMissingIOPlanNeverRestoresToUnlimited(t *testing.T) {
	e, f := fixture(t)
	e.Config.Percent = 20
	s := Setting{File: "io.max", Device: "253:0", Value: "rbps=1000 wbps=2000 riops=10 wiops=20"}
	if r := e.Reconcile(Plan{Settings: []Setting{s}}); r.State != "managed" {
		t.Fatal(r)
	}
	before := f.data[filepath.Join(e.Env.Target, "io.max")]
	r := e.Reconcile(Plan{Settings: []Setting{{File: "cpu.max", Value: "100000 100000"}}, Warnings: []string{"IO profile temporarily unavailable"}})
	if r.State != "degraded" || r.Items[1].State != "retained" || f.data[filepath.Join(e.Env.Target, "io.max")] != before {
		t.Fatal("missing profile silently removed the existing IO cap", r)
	}
}
