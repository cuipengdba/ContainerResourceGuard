package guard

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestReloadIndependentDefaultsCLIOverridesAndLastGoodPolicy(t *testing.T) {
	root := t.TempDir()
	file := filepath.Join(root, "config.json")
	cpu := float64(25)
	initial := Config{ResourcePercentages: ResourcePercentages{CPUPercent: &cpu}, StateDir: root, LogDir: filepath.Join(root, "cli-logs"), IOCalibration: "off"}
	w, err := NewConfigWatcher(file, initial, ConfigOverrides{ResourcePercentages: ResourcePercentages{CPUPercent: &cpu}, StateDir: root, LogDir: initial.LogDir})
	if err != nil {
		t.Fatal(err)
	}
	env := Environment{Target: root, OnlineCPUs: 24, MemoryBytes: 64 << 30}
	write := func(values map[string]any) {
		t.Helper()
		values["io_calibration"] = "off"
		b, err := json.Marshal(values)
		if err != nil {
			t.Fatal(err)
		}
		if err = os.WriteFile(file, b, 0600); err != nil {
			t.Fatal(err)
		}
		w.Poll(env, nil, false)
	}
	assertPolicy := func(memory, io float64, generation uint64) {
		t.Helper()
		c, m, i := w.Current.corePercentages()
		if c != 25 || m != memory || i != io || w.Current.LogDir != initial.LogDir || w.Revision.Generation != generation {
			t.Fatal(w.Current, w.Revision)
		}
		p, err := BuildPlan(w.Current, env, nil)
		if err != nil {
			t.Fatal(err)
		}
		for _, setting := range p.Settings {
			if setting.File != "cpu.max" && setting.File != "memory.high" && setting.File != "io.max" {
				t.Fatal("reload implicitly controls another resource", setting)
			}
		}
	}
	write(map[string]any{"cpu_percent": 35, "memory_percent": 30, "io_percent": 40, "log_dir": filepath.Join(root, "file-logs")})
	assertPolicy(30, 40, 2)
	hash := w.Revision.AcceptedHash
	for _, bad := range []map[string]any{{"io_percent": 101}, {"memory_percent": nil}, {"pids_percent": 20}, {"resource_mode": "manual", "limits": map[string]any{"cpu_cores": 1}}} {
		write(bad)
		if w.Revision.State != "rejected" || w.Revision.AcceptedHash != hash {
			t.Fatal("bad/mixed override discarded last good policy", w.Revision)
		}
		assertPolicy(30, 40, 2)
	}
	write(map[string]any{"io_percent": 50})
	assertPolicy(20, 50, 3)
	if w.Revision.State != "accepted" {
		t.Fatal(w.Revision)
	}
	write(map[string]any{})
	assertPolicy(20, 20, 4)
}
