package guard

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestDualModesRejectAmbiguousAndUnsafeInput(t *testing.T) {
	valid := []string{`{"percent":20}`, `{"resource_mode":"percent","percent":30,"pids_max":1024,"cpu_weight":200}`, `{"resource_mode":"manual","limits":{"cpu_cores":1.5,"memory_max":"2GiB"}}`, `{"resource_mode":"manual","limits":{"io_read_bps":"10MB"},"data_paths":["/data"]}`}
	for _, raw := range valid {
		var c Config
		if err := Decode([]byte(raw), &c); err != nil {
			t.Fatal(raw, err)
		}
		if err := c.Validate(); err != nil {
			t.Fatal(raw, err)
		}
		b, err := json.Marshal(c)
		if err != nil {
			t.Fatal(err)
		}
		var copy Config
		if err = Decode(b, &copy); err != nil {
			t.Fatal(string(b), err)
		}
		if err = copy.Validate(); err != nil {
			t.Fatal("validated config cannot roundtrip", string(b), err)
		}
	}
	invalid := []string{`{"resource_mode":"unknown","percent":20}`, `{"resource_mode":"manual","percent":20,"limits":{"cpu_cores":2}}`, `{"resource_mode":"manual","percent":0,"limits":{"cpu_cores":2}}`, `{"percent":20,"limits":{"cpu_cores":2}}`, `{"resource_mode":"manual","limits":{}}`, `{"resource_mode":"manual","limits":{"cpu_cores":0}}`, `{"resource_mode":"manual","limits":{"cpu_cores":0.001}}`, `{"resource_mode":"manual","limits":{"memory_max":"1MiB"}}`, `{"resource_mode":"manual","limits":{"memory_max":"8GiB","memory_max":"9GiB"}}`, `{"resource_mode":"manual","limits":{"io_read_bps":"10MiB"}}`, `{"resource_mode":"manual","limits":{"io_read_bps":"10MiB/s"},"data_paths":["/data"]}`, `{"resource_mode":"manual","limits":{"io_read_iops":0},"data_paths":["/data"]}`, `{"percent":20,"pids_max":0}`, `{"percent":20,"pids_max":2147483648}`, `{"percent":20,"cpu_weight":0}`, `{"percent":20,"cpu_weight":10001}`}
	for _, raw := range invalid {
		var c Config
		err := Decode([]byte(raw), &c)
		if err == nil {
			err = c.Validate()
		}
		if err == nil {
			t.Fatal("accepted unsafe or ambiguous config", raw)
		}
	}
}

func TestManualQuantitiesAreExactAndBounded(t *testing.T) {
	for text, want := range map[string]uint64{"0B": 0, "1024": 1024, "1KiB": 1024, "2GiB": 2 << 30, "1GB": 1000000000, "9223372036854775807B": 9223372036854775807} {
		n, err := ParseBytes(text)
		if err != nil || n != want {
			t.Fatal(text, n, err)
		}
	}
	for _, text := range []string{"-1GiB", "01GiB", "1.5GiB", "1e9", "1M", "1mb", "1GiB/s", " 1GiB", "9223372036854775808", "9000000000000000TiB"} {
		if _, err := ParseBytes(text); err == nil {
			t.Fatal("accepted quantity", text)
		}
	}
}

func TestManualPlanOmitsUnrequestedResourcesAndPreservesExternalLimits(t *testing.T) {
	if _, err := BuildPlan(Config{ResourceMode: "manual"}, Environment{}, nil); err == nil {
		t.Fatal("unvalidated manual plan accepted missing limits")
	}
	root := t.TempDir()
	target := filepath.Join(root, "self")
	if err := os.Mkdir(target, 0700); err != nil {
		t.Fatal(err)
	}
	for file, value := range map[string]string{"cpu.max": "100000 100000", "memory.max": "1073741824", "pids.max": "200"} {
		if err := os.WriteFile(filepath.Join(target, file), []byte(value), 0600); err != nil {
			t.Fatal(err)
		}
	}
	cpu := 2.0
	pids := uint64(300)
	weight := uint64(200)
	c := Config{ResourceMode: "manual", Limits: &ManualLimits{CPUCores: &cpu}, PidsMax: &pids, CPUWeight: &weight}
	if err := c.Validate(); err != nil {
		t.Fatal(err)
	}
	env := Environment{Target: target, OnlineCPUs: 24, MemoryBytes: 64 << 30, EffectiveCPUs: "0-23"}
	p, err := BuildPlan(c, env, nil)
	if err != nil {
		t.Fatal(err)
	}
	values := map[string]string{}
	for _, s := range p.Settings {
		values[s.File] = s.Value
	}
	if len(p.Settings) != 3 || values["cpu.max"] != "100000 100000" || values["pids.max"] != "200" || values["cpu.weight"] != "200" {
		t.Fatal(p)
	}
	if _, ok := values["memory.max"]; ok {
		t.Fatal("unrequested memory managed")
	}
	if len(p.Warnings) != 2 {
		t.Fatal("manual mode should not warn about absent IO calibration", p.Warnings)
	}
	p, err = BuildPlan(c, env, map[string]string{"cpu.max:": "max 100000", "pids.max:": "max"})
	if err != nil {
		t.Fatal(err)
	}
	if p.Settings[0].Value != "200000 100000" || p.Settings[1].Value != "300" {
		t.Fatal("owned old limits prevented manual increase", p)
	}
}

func TestManualIOPathDedupClampingAndMissingCoverage(t *testing.T) {
	readIOPS := uint64(100)
	c := Config{ResourceMode: "manual", Limits: &ManualLimits{ReadBPS: "10MiB", ReadIOPS: &readIOPS}, DataPaths: []string{"/data", "/wal", "/unknown"}}
	root := t.TempDir()
	os.WriteFile(filepath.Join(root, "io.max"), []byte("253:0 rbps=1000 wbps=2000 riops=50 wiops=20"), 0600)
	resolve := func(path string) (string, string, error) {
		if path == "/unknown" {
			return "", "", os.ErrNotExist
		}
		return "253:0", strings.Repeat("a", 64), nil
	}
	settings, devices, warnings := manualIO(c, Environment{Target: root}, nil, resolve, func(string, string) (bool, error) { return false, nil })
	if len(settings) != 1 || len(devices) != 1 || len(warnings) != 1 {
		t.Fatal(settings, devices, warnings)
	}
	if settings[0].Value != "rbps=1000 wbps=2000 riops=50 wiops=20" {
		t.Fatal("external and omitted IO dimensions were raised", settings)
	}
	if settings[0].DeviceIdentity != strings.Repeat("a", 64) {
		t.Fatal("missing device binding")
	}
}

func TestManualIORejectsOverlappingOrUnverifiableDeviceStacks(t *testing.T) {
	c := Config{Limits: &ManualLimits{ReadBPS: "1MiB"}, DataPaths: []string{"/data", "/backup"}}
	resolve := func(path string) (string, string, error) {
		if path == "/data" {
			return "253:0", strings.Repeat("a", 64), nil
		}
		return "8:0", strings.Repeat("b", 64), nil
	}
	for _, broken := range []bool{false, true} {
		settings, devices, warnings := manualIO(c, Environment{}, nil, resolve, func(string, string) (bool, error) {
			if broken {
				return false, os.ErrPermission
			}
			return true, nil
		})
		if len(settings) != 0 || len(devices) != 2 || len(warnings) != 2 {
			t.Fatal(settings, devices, warnings)
		}
	}
}

func TestOptionalControlsRestoreAndRejectDangerousPidsDecrease(t *testing.T) {
	for _, scenario := range []string{"safe", "too-low", "missing-current", "slow-journal", "restore-too-low"} {
		t.Run(scenario, func(t *testing.T) {
			e, f := fixture(t)
			p := filepath.Join(e.Env.Target, "pids.max")
			current := filepath.Join(e.Env.Target, "pids.current")
			f.data[p] = "max"
			f.data[current] = "20"
			f.data[filepath.Join(e.Env.Target, "cpu.weight")] = "100"
			target := "100"
			if scenario == "too-low" {
				target = "32"
			}
			if scenario == "missing-current" {
				delete(f.data, current)
			}
			if scenario == "slow-journal" {
				e.Persist = func(Journal) error { f.data[current] = "99"; return nil }
			}
			if scenario == "restore-too-low" {
				f.data[p] = "60"
			}
			r := e.Apply(Plan{Settings: []Setting{{File: "pids.max", Value: target}}})
			if scenario != "safe" && scenario != "restore-too-low" {
				if r.Items[0].State != "skipped" || len(f.writes) != 0 {
					t.Fatal(r, f.writes)
				}
				return
			}
			if r.Items[0].State != "applied" {
				t.Fatal(r)
			}
			if scenario == "restore-too-low" {
				f.data[current] = "50"
				if r = e.Restore(); r.State != "degraded" || f.data[p] != "100" {
					t.Fatal(r)
				}
				return
			}
			if r = e.Apply(Plan{Settings: []Setting{{File: "cpu.weight", Value: "200"}}}); r.State != "managed" {
				t.Fatal(r)
			}
			if r = e.Restore(); r.State != "restored" || f.data[p] != "max" || f.data[filepath.Join(e.Env.Target, "cpu.weight")] != "100" {
				t.Fatal(r)
			}
		})
	}
}

func TestReplacementDeviceCannotInheritOrRestoreOwnedIO(t *testing.T) {
	e, f := fixture(t)
	id := strings.Repeat("a", 64)
	present := id
	e.DeviceLookup = func(string) (string, error) { return present, nil }
	s := Setting{File: "io.max", Device: "253:0", DeviceIdentity: id, Value: "rbps=1000 wbps=max riops=max wiops=max"}
	if r := e.Apply(Plan{Settings: []Setting{s}}); r.State != "managed" {
		t.Fatal(r)
	}
	writes := len(f.writes)
	present = strings.Repeat("b", 64)
	if r := e.Apply(Plan{Settings: []Setting{s}}); r.Items[0].State != "skipped" {
		t.Fatal(r)
	}
	if r := e.Restore(); r.State != "degraded" || len(f.writes) != writes {
		t.Fatal("restored to replacement", r)
	}
	s.DeviceIdentity = present
	if r := e.Apply(Plan{Settings: []Setting{s}}); r.Items[0].State != "conflict" || len(f.writes) != writes {
		t.Fatal("replacement inherited owned journal", r)
	}
	e.DeviceLookup = func(string) (string, error) { return "", errors.New("device removed") }
	if r := e.Restore(); r.State != "degraded" {
		t.Fatal(r)
	}
}

func TestRestoreRechecksExternalValueAfterMemorySampling(t *testing.T) {
	e, f := fixture(t)
	file := filepath.Join(e.Env.Target, "memory.max")
	f.data[file] = "67108864"
	if r := e.Apply(Plan{Settings: []Setting{{File: "memory.max", Value: "134217728"}}}); r.State != "managed" {
		t.Fatal(r)
	}
	e.Pause = func(time.Duration) { f.data[file] = "100663296" }
	if r := e.Restore(); r.State != "degraded" || f.data[file] != "100663296" {
		t.Fatal("external value overwritten after sampling", r)
	}
}
