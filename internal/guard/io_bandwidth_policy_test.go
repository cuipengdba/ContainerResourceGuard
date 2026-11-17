package guard

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func bandwidthMigrationFixture(t *testing.T, baseline string) (*Engine, *fakeFiles, Setting, func() Plan) {
	t.Helper()
	e, f := fixture(t)
	id := strings.Repeat("c", 64)
	e.DeviceLookup = func(string) (string, error) { return id, nil }
	path := filepath.Join(e.Env.Target, "io.max")
	f.data[path] = "8:0 " + baseline
	s := Setting{File: "io.max", Device: "8:0", DeviceIdentity: id, Value: "rbps=100 wbps=100 riops=10 wiops=11"}
	if r := e.Apply(Plan{Settings: []Setting{s}}); r.State != "managed" {
		t.Fatal(r)
	}
	plan := func() Plan {
		t.Helper()
		if err := os.MkdirAll(e.Env.Target, 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(f.data[path]), 0600); err != nil {
			t.Fatal(err)
		}
		p, resolve := siblingProfiles()
		p.Devices = p.Devices[:1]
		settings, _, warnings := percentageIO(Config{}, e.Env, e.Originals(), p, resolve, func(string, string) (bool, error) { return false, nil })
		if len(settings) != 1 || len(warnings) != 0 {
			t.Fatal(settings, warnings)
		}
		return Plan{Settings: settings}
	}
	return e, f, s, plan
}

func TestBandwidthPercentRestoresOwnedIOPSBaselineAndDisable(t *testing.T) {
	for _, baseline := range []string{"rbps=max wbps=max riops=max wiops=max", "rbps=900 wbps=800 riops=199 wiops=177"} {
		t.Run(baseline, func(t *testing.T) {
			e, f, s, plan := bandwidthMigrationFixture(t, baseline)
			want := clampIO("rbps=200 wbps=100 riops=max wiops=max", baseline)
			p := plan()
			if p.Settings[0].Value != want {
				t.Fatal("did not restore the pre-CRG IOPS baseline", p)
			}
			if r := e.Reconcile(p); r.State != "managed" || ioValue(f.data[filepath.Join(e.Env.Target, "io.max")], s.Device) != want || e.Journal.Mutations[s.Key()].Original != baseline {
				t.Fatal(r, e.Journal)
			}
			if r := e.Restore(); r.State != "restored" || ioValue(f.data[filepath.Join(e.Env.Target, "io.max")], s.Device) != baseline {
				t.Fatal("disable lost original four-axis controls", r)
			}
		})
	}
}

func TestBandwidthMigrationRefusesExternalReplacementObserveAndFailedIntent(t *testing.T) {
	for _, scenario := range []string{"external-IOPS", "external-BPS", "device-replaced", "observe", "intent-failure", "external-during-intent"} {
		t.Run(scenario, func(t *testing.T) {
			e, f, s, plan := bandwidthMigrationFixture(t, "rbps=max wbps=max riops=199 wiops=177")
			path := filepath.Join(e.Env.Target, "io.max")
			before := f.data[path]
			switch scenario {
			case "external-IOPS":
				f.data[path] = "8:0 rbps=100 wbps=100 riops=33 wiops=11"
			case "external-BPS":
				f.data[path] = "8:0 rbps=77 wbps=100 riops=10 wiops=11"
			case "device-replaced":
				e.DeviceLookup = func(string) (string, error) { return strings.Repeat("d", 64), nil }
			case "observe":
				e.Config.Mode = "observe"
			case "intent-failure":
				e.Persist = func(Journal) error { return errors.New("test fsync failure") }
			case "external-during-intent":
				e.Persist = func(Journal) error {
					f.data[path] = "8:0 rbps=100 wbps=100 riops=33 wiops=11"
					return nil
				}
			}
			p := plan()
			current := f.data[path]
			writes := len(f.writes)
			result := e.Reconcile(p)
			if scenario == "external-during-intent" {
				current = "8:0 rbps=100 wbps=100 riops=33 wiops=11"
			}
			if len(f.writes) != writes || f.data[path] != current || e.Journal.Mutations[s.Key()].Original != "rbps=max wbps=max riops=199 wiops=177" {
				t.Fatal("unsafe migration write", result, before, f.data[path])
			}
			if scenario == "observe" {
				if result.State != "observe" {
					t.Fatal(result)
				}
			} else if result.State != "degraded" {
				t.Fatal("failure was not visible", result)
			}
		})
	}
}

func TestBandwidthMigrationRecoversPendingWrite(t *testing.T) {
	for _, written := range []bool{false, true} {
		t.Run(map[bool]string{false: "before-write", true: "after-write"}[written], func(t *testing.T) {
			e, f, s, plan := bandwidthMigrationFixture(t, "rbps=max wbps=max riops=199 wiops=177")
			want := "rbps=200 wbps=100 riops=199 wiops=177"
			e.Journal.Mutations[s.Key()].Pending = want
			// Restart from the durable intent, not a shared in-memory pointer.
			raw, _ := json.Marshal(e.Journal)
			if err := json.Unmarshal(raw, &e.Journal); err != nil {
				t.Fatal(err)
			}
			if written {
				f.data[filepath.Join(e.Env.Target, "io.max")] = "8:0 " + want
			}
			if r := e.Reconcile(plan()); r.State != "managed" || ioValue(f.data[filepath.Join(e.Env.Target, "io.max")], "8:0") != want || e.Journal.Mutations[s.Key()].Pending != "" {
				t.Fatal(r, e.Journal)
			}
		})
	}
}

func TestLowProfileIOPSDoesNotSuppressValidBandwidthAndExternalIOPS(t *testing.T) {
	p, resolve := siblingProfiles()
	for i := range p.Devices {
		p.Devices[i].ReadIOPS, p.Devices[i].WriteIOPS = 1, 1
	}
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "io.max"), []byte("8:0 rbps=max wbps=max riops=39 wiops=17"), 0600); err != nil {
		t.Fatal(err)
	}
	s, _, w := percentageIO(Config{}, Environment{Target: dir}, nil, p, resolve, func(string, string) (bool, error) { return false, nil })
	if len(w) != 0 || len(s) != 1 || s[0].Value != "rbps=100 wbps=100 riops=39 wiops=17" {
		t.Fatal("IOPS diagnostic or external baseline lost", s, w)
	}
}
