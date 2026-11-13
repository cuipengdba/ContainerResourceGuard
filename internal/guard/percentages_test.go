package guard

import (
	"os"
	"path/filepath"
	"strconv"
	"testing"
)

func TestThreeIndependentDefaultsAndValidation(t *testing.T) {
	for _, raw := range []string{`{}`, `{"cpu_percent":30,"io_percent":45}`} {
		var c Config
		if err := Decode([]byte(raw), &c); err != nil {
			t.Fatal(err)
		}
		if err := c.Validate(); err != nil {
			t.Fatal(err)
		}
		cpu, mem, io := c.corePercentages()
		wc, wi := 20., 20.
		if len(raw) > 2 {
			wc, wi = 30, 45
		}
		if cpu != wc || mem != 20 || io != wi || len(c.ResourcePercentages.fields()) != 3 || c.PidsMax != nil || c.CPUWeight != nil || c.IOWeight != nil || c.MemoryHigh != "" || c.MemorySwapMax != "" {
			t.Fatal(c)
		}
		if err := c.Validate(); err != nil {
			t.Fatal("non-idempotent defaults", err)
		}
	}
	for _, raw := range []string{`{"cpu_percent":0}`, `{"memory_percent":null}`, `{"io_percent":101}`, `{"pids_percent":20}`, `{"cpu_weight_percent":20}`, `{"io_weight_percent":20}`, `{"memory_high_percent":20}`, `{"memory_swap_percent":20}`, `{"percent":20,"cpu_percent":30}`, `{"resource_mode":"manual","io_percent":20}`, `{"cpu_weight":100}`} {
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
		if c.ResourcePercentages.present() {
			t.Fatal(c)
		}
	}
}

func TestThreePercentPlanDoesNotRequestOtherControllers(t *testing.T) {
	dir := t.TempDir()
	for file, value := range map[string]string{"cpu.max": "max 100000", "memory.max": "max", "pids.max": "123456", "cpu.weight": "77", "io.weight": "default 88", "memory.high": "max", "memory.swap.max": "0"} {
		if err := os.WriteFile(filepath.Join(dir, file), []byte(value), 0600); err != nil {
			t.Fatal(err)
		}
	}
	env := Environment{Target: dir, OnlineCPUs: 24, MemoryBytes: 64 << 30}
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
	wantMemory := strconv.FormatUint(scaleRate(64<<30, 40)/page*page, 10)
	if len(values) != 2 || values["cpu.max"] != "720000 100000" || values["memory.high"] != wantMemory || p.Percentages == nil || *p.Percentages.IOPercent != 50 {
		t.Fatal(p)
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
			t.Fatal("raised external cap", s)
		}
	}
}
