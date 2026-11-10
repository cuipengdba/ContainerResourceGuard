package guard

import (
	"math"
	"os"
	"path/filepath"
	"strconv"
	"testing"
)

func TestIndependentDefaultsAndPartialConfiguration(t *testing.T) {
	for _, raw := range []string{`{}`, `{"cpu_percent":30,"io_percent":45}`} {
		var c Config
		if err := Decode([]byte(raw), &c); err != nil {
			t.Fatal(err)
		}
		if err := c.Validate(); err != nil {
			t.Fatal(err)
		}
		wantCPU, wantIO := 20., 20.
		if len(raw) > 2 {
			wantCPU, wantIO = 30, 45
		}
		cpu, mem, io := c.corePercentages()
		if cpu != wantCPU || mem != 20 || io != wantIO || c.Percent != 0 {
			t.Fatal(c)
		}
		for name, value := range c.ResourcePercentages.fields() {
			if value == nil {
				t.Fatal(name)
			}
			if name != "cpu_percent" && name != "io_percent" && *value != 20 {
				t.Fatal(name, *value)
			}
		}
		if err := c.Validate(); err != nil {
			t.Fatal("defaults are not idempotent", err)
		}
	}
}

func TestSeparatePercentRejectsAmbiguityAndKeepsLegacyAndManual(t *testing.T) {
	for _, raw := range []string{`{"cpu_percent":0}`, `{"memory_percent":null}`, `{"io_percent":101}`, `{"pids_percent":-1}`, `{"cpu_weight_percent":0}`, `{"memory_swap_percent":-1}`, `{"percent":20,"cpu_percent":30}`, `{"resource_mode":"manual","limits":{"memory_max":"1GiB"},"io_percent":20}`, `{"cpu_percent":20,"cpu_weight":100}`} {
		var c Config
		err := Decode([]byte(raw), &c)
		if err == nil {
			err = c.Validate()
		}
		if err == nil {
			t.Fatal("accepted", raw)
		}
	}
	for _, raw := range []string{`{"percent":30}`, `{"resource_mode":"manual","limits":{"memory_max":"1GiB"}}`} {
		var c Config
		if err := Decode([]byte(raw), &c); err != nil {
			t.Fatal(err)
		}
		if err := c.Validate(); err != nil {
			t.Fatal(err)
		}
		if c.ResourcePercentages.present() || c.PidsMax != nil || c.CPUWeight != nil || c.MemoryHigh != "" {
			t.Fatal("changed deployed/manual semantics", c)
		}
	}
	bad := math.NaN()
	c := Config{ResourcePercentages: ResourcePercentages{CPUPercent: &bad}}
	if c.Validate() == nil {
		t.Fatal("accepted NaN")
	}
}

func TestSeparatePercentActualPlanAndUpperConstraints(t *testing.T) {
	dir := t.TempDir()
	for file, value := range map[string]string{"cpu.max": "max 100000", "memory.max": "max", "pids.max": "max", "memory.high": "max", "memory.swap.max": "max"} {
		if err := os.WriteFile(filepath.Join(dir, file), []byte(value), 0600); err != nil {
			t.Fatal(err)
		}
	}
	pid, swap := uint64(4194304), uint64(8<<30)
	env := Environment{Target: dir, OnlineCPUs: 24, MemoryBytes: 64 << 30, HostPidsMax: &pid, HostSwapBytes: &swap}
	var c Config
	if err := Decode([]byte(`{"cpu_percent":30,"memory_percent":40,"io_percent":50,"io_calibration":"off"}`), &c); err != nil {
		t.Fatal(err)
	}
	p, err := BuildPlan(c, env, nil)
	if err != nil {
		t.Fatal(err)
	}
	values := map[string]string{}
	for _, s := range p.Settings {
		values[s.File] = s.Value
	}
	page := uint64(os.Getpagesize())
	quantity := func(total uint64, percent float64) string {
		return strconv.FormatUint(scaleRate(total, percent)/page*page, 10)
	}
	for k, want := range map[string]string{"cpu.max": "720000 100000", "memory.max": quantity(64<<30, 40), "pids.max": "838860", "cpu.weight": "2000", "io.weight": "default 2000", "memory.high": quantity(64<<30, 20), "memory.swap.max": quantity(8<<30, 20)} {
		if values[k] != want {
			t.Fatal(k, values[k], want)
		}
	}
	if p.Percentages == nil || *p.Percentages.IOPercent != 50 || p.Percent != 0 {
		t.Fatal(p)
	}
	// Reducing hard memory below the default high is a bounded high, not a
	// rejected entire configuration or an accidental increase of the hard cap.
	m := float64(10)
	c.MemoryPercent = &m
	p, err = BuildPlan(c, env, nil)
	if err != nil {
		t.Fatal(err)
	}
	for _, s := range p.Settings {
		if s.File == "memory.high" && s.Value != quantity(64<<30, 10) {
			t.Fatal(s)
		}
	}
	if err := os.WriteFile(filepath.Join(dir, "cpu.max"), []byte("200000 100000"), 0600); err != nil {
		t.Fatal(err)
	}
	p, err = BuildPlan(c, env, nil)
	if err != nil {
		t.Fatal(err)
	}
	for _, s := range p.Settings {
		if s.File == "cpu.max" && s.Value != "200000 100000" {
			t.Fatal("raised existing cap", s)
		}
	}
}
