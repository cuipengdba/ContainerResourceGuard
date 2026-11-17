package guard

import (
	"os"
	"path/filepath"
	"strconv"
	"testing"
)

func TestMemoryPercentAndManualTargetsOnlyPlanHigh(t *testing.T) {
	dir := t.TempDir()
	for file, value := range map[string]string{"cpu.max": "max 100000", "memory.max": "max", "memory.high": "max"} {
		if err := os.WriteFile(filepath.Join(dir, file), []byte(value), 0600); err != nil {
			t.Fatal(err)
		}
	}
	for _, raw := range []string{`{"memory_percent":30,"io_calibration":"off"}`, `{"resource_mode":"manual","limits":{"memory_high":"1GiB"}}`, `{"resource_mode":"manual","limits":{"memory_max":"1GiB"}}`} {
		var c Config
		if err := Decode([]byte(raw), &c); err != nil {
			t.Fatal(err)
		}
		p, err := BuildPlan(c, Environment{Target: dir, OnlineCPUs: 24, MemoryBytes: 64 << 30}, nil)
		if err != nil {
			t.Fatal(err)
		}
		found := 0
		for _, s := range p.Settings {
			if s.File == "memory.max" {
				t.Fatal("new hard cap", p)
			}
			if s.File == "memory.high" {
				found++
				want := uint64(1 << 30)
				if c.ResourceMode != "manual" {
					want = scaleRate(64<<30, 30) / uint64(os.Getpagesize()) * uint64(os.Getpagesize())
				}
				if s.Value != strconv.FormatUint(want, 10) {
					t.Fatal(s, want)
				}
			}
		}
		if found != 1 || p.MemoryPolicy != "high-reclaim-throttle" {
			t.Fatal(p)
		}
	}
	var c Config
	if Decode([]byte(`{"resource_mode":"manual","limits":{"memory_high":"1GiB","memory_max":"2GiB"}}`), &c) == nil && c.Validate() == nil {
		t.Fatal("ambiguous memory aliases accepted")
	}
}

func TestHighTargetHonorsExternalHighAndHardCaps(t *testing.T) {
	dir := t.TempDir()
	for file, value := range map[string]string{"memory.max": "1073741824", "memory.high": "536870912"} {
		if err := os.WriteFile(filepath.Join(dir, file), []byte(value), 0600); err != nil {
			t.Fatal(err)
		}
	}
	p, err := BuildPlan(Config{ResourceMode: "manual", Limits: &ManualLimits{MemoryHigh: "2GiB"}}, Environment{Target: dir}, nil)
	if err != nil || len(p.Settings) != 1 || p.Settings[0].File != "memory.high" || p.Settings[0].Value != "536870912" {
		t.Fatal(p, err)
	}
	if value, err := os.ReadFile(filepath.Join(dir, "memory.max")); err != nil || string(value) != "1073741824" {
		t.Fatal("external hard limit changed", string(value), err)
	}
}

func TestUpgradeRestoresOnlyOwnedLegacyHardCapBeforeHigh(t *testing.T) {
	e, f := fixture(t)
	hard := filepath.Join(e.Env.Target, "memory.max")
	high := filepath.Join(e.Env.Target, "memory.high")
	f.data[hard], f.data[high] = "1073741824", "max"
	f.data[filepath.Join(e.Env.Target, "memory.current")] = "805306368"
	s := Setting{File: "memory.max", Value: "1073741824"}
	e.Journal.Mutations[s.Key()] = &Mutation{Setting: s, Original: "2147483648", Applied: s.Value}
	e.Config.ResourceMode = "manual"
	e.Config.Limits = &ManualLimits{MemoryHigh: "512MiB"}
	p := Plan{MemoryPolicy: "high-reclaim-throttle", Settings: []Setting{{File: "memory.high", Value: "536870912"}}}
	r := e.Reconcile(p)
	if r.State != "managed" || f.data[hard] != "2147483648" || f.data[high] != "536870912" || len(f.writes) != 2 || f.writes[0] != hard || f.writes[1] != high {
		t.Fatal(r, f.data, f.writes)
	}
	if _, ok := e.Journal.Mutations["memory.max:"]; ok {
		t.Fatal("legacy hard cap still owned", e.Journal)
	}
}

func TestExternalHardCapConflictIsNeverRestoredOrHidden(t *testing.T) {
	e, f := fixture(t)
	hard := filepath.Join(e.Env.Target, "memory.max")
	f.data[hard] = "536870912"
	s := Setting{File: "memory.max", Value: "1073741824"}
	e.Journal.Mutations[s.Key()] = &Mutation{Setting: s, Original: "max", Applied: s.Value}
	if _, ok := e.Originals()[s.Key()]; ok {
		t.Fatal("external hard cap hidden by stale baseline")
	}
	r := e.Reconcile(Plan{})
	if r.State != "degraded" || f.data[hard] != "536870912" || len(f.writes) != 0 || !e.Journal.Mutations[s.Key()].Conflict {
		t.Fatal(r, f.writes)
	}
}

func TestMissingHighDoesNotFallBackToHardOrBlockCPU(t *testing.T) {
	e, f := fixture(t)
	r := e.Apply(Plan{Settings: []Setting{{File: "memory.high", Value: "67108864"}, {File: "cpu.max", Value: "100000 100000"}}})
	if r.State != "degraded" || r.Items[0].ReasonCode != "controller_read" || r.Items[1].State != "applied" || f.data[filepath.Join(e.Env.Target, "memory.max")] != "max" {
		t.Fatal(r)
	}
	if len(f.writes) != 1 || filepath.Base(f.writes[0]) != "cpu.max" {
		t.Fatal(f.writes)
	}
}

func TestRestoreHighBelowUsageIsNotHardCapPreflight(t *testing.T) {
	e, f := fixture(t)
	high := filepath.Join(e.Env.Target, "memory.high")
	f.data[high] = "134217728"
	if r := e.Apply(Plan{Settings: []Setting{{File: "memory.high", Value: "536870912"}}}); r.State != "managed" {
		t.Fatal(r)
	}
	f.data[filepath.Join(e.Env.Target, "memory.current")] = "805306368"
	if r := e.Restore(); r.State != "restored" || f.data[high] != "134217728" {
		t.Fatal(r)
	}
}
