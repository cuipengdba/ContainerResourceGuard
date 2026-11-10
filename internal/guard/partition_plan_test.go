package guard

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func siblingProfiles() (Profile, func(DeviceProfile) (IOBlockDevice, error)) {
	first := DeviceProfile{Device: "8:1", Identity: strings.Repeat("a", 64), ReadBPS: 1000, WriteBPS: 500, ReadIOPS: 100, WriteIOPS: 50}
	second := DeviceProfile{Device: "8:2", Identity: strings.Repeat("b", 64), ReadBPS: 500, WriteBPS: 1000, ReadIOPS: 50, WriteIOPS: 100}
	p := Profile{Version: 1, Method: ProfileMethod, Devices: []DeviceProfile{first, second}}
	return p, func(d DeviceProfile) (IOBlockDevice, error) {
		return IOBlockDevice{Device: d.Device, Identity: d.Identity, ControlDevice: "8:0", ControlIdentity: strings.Repeat("c", 64), Partition: 1}, nil
	}
}

func TestSiblingPartitionsShareConservativeCapAndOriginalClamp(t *testing.T) {
	p, resolve := siblingProfiles()
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "io.max"), []byte("8:0 rbps=70 wbps=max riops=max wiops=max"), 0600); err != nil {
		t.Fatal(err)
	}
	s, d, w := percentageIO(Config{}, Environment{Target: root}, nil, p, resolve, func(string, string) (bool, error) { return false, nil })
	if len(s) != 1 || len(d) != 2 || len(w) != 0 || s[0].Device != "8:0" || s[0].DeviceIdentity != strings.Repeat("c", 64) || s[0].Value != "rbps=70 wbps=100 riops=10 wiops=10" {
		t.Fatal("siblings got separate/additive caps or lost parent clamp", s, d, w)
	}
	s, _, _ = percentageIO(Config{}, Environment{Target: root}, map[string]string{"io.max:8:0": "rbps=90 wbps=max riops=max wiops=max"}, p, resolve, func(string, string) (bool, error) { return false, nil })
	if len(s) != 1 || s[0].Value != "rbps=90 wbps=100 riops=10 wiops=10" {
		t.Fatal("owned original not used", s)
	}
}

func TestPartitionPlanRejectsAmbiguityOverlapAndStaleBindings(t *testing.T) {
	for _, scenario := range []string{"whole-plus-partition", "identity-conflict", "duplicate-filesystem", "stack-overlap", "unreadable-stack", "stale-partition", "minimum"} {
		t.Run(scenario, func(t *testing.T) {
			p, base := siblingProfiles()
			resolve := func(d DeviceProfile) (IOBlockDevice, error) {
				b, err := base(d)
				if d.Device == "8:2" {
					switch scenario {
					case "whole-plus-partition":
						b.Partition = 0
					case "identity-conflict":
						b.ControlIdentity = strings.Repeat("d", 64)
					case "duplicate-filesystem":
						b.Device = "8:1"
					case "stack-overlap", "unreadable-stack":
						b.ControlDevice, b.ControlIdentity = "253:0", strings.Repeat("d", 64)
					}
				}
				if scenario == "stale-partition" {
					b.Identity = strings.Repeat("e", 64)
				}
				return b, err
			}
			if scenario == "minimum" {
				p.Devices[0].ReadIOPS = 1
			}
			related := func(string, string) (bool, error) {
				if scenario == "unreadable-stack" {
					return false, errors.New("unreadable stack")
				}
				return scenario == "stack-overlap", nil
			}
			settings, devices, warnings := percentageIO(Config{}, Environment{}, nil, p, resolve, related)
			if len(settings) != 0 || len(devices) != 2 || len(warnings) == 0 {
				t.Fatal("unsafe or ambiguous parent cap accepted", settings, devices, warnings)
			}
		})
	}
}

func TestSiblingCapsUseIOPercentageAndDoNotDependOnProfileOrder(t *testing.T) {
	p, resolve := siblingProfiles()
	io, cpu := 30.0, 80.0
	c := Config{ResourcePercentages: ResourcePercentages{IOPercent: &io, CPUPercent: &cpu}}
	for attempt := 0; attempt < 2; attempt++ {
		s, _, _ := percentageIO(c, Environment{}, nil, p, resolve, func(string, string) (bool, error) { return false, nil })
		if len(s) != 1 || s[0].Value != "rbps=150 wbps=150 riops=15 wiops=15" {
			t.Fatal("IO percentage or input order changed shared cap", s)
		}
		p.Devices[0], p.Devices[1] = p.Devices[1], p.Devices[0]
	}
}

func TestParentJournalRestoresWithoutPartitionAndRejectsReplacement(t *testing.T) {
	for _, replacement := range []bool{false, true} {
		e, f := fixture(t)
		id := strings.Repeat("c", 64)
		e.DeviceLookup = func(dev string) (string, error) {
			if dev != "8:0" {
				return "", os.ErrNotExist // Filesystem partition may no longer exist.
			}
			return id, nil
		}
		p := filepath.Join(e.Env.Target, "io.max")
		f.data[p] = "8:0 rbps=500 wbps=600 riops=70 wiops=80"
		s := Setting{File: "io.max", Device: "8:0", DeviceIdentity: id, Value: "rbps=100 wbps=100 riops=10 wiops=10"}
		if got := e.Apply(Plan{Settings: []Setting{s}}); got.Items[0].State != "applied" {
			t.Fatal(got)
		}
		if replacement {
			id = strings.Repeat("d", 64)
		}
		got := e.Restore()
		if replacement {
			if got.State != "degraded" || ioValue(f.data[p], "8:0") != s.Value {
				t.Fatal("replacement parent was mutated", got, f.data[p])
			}
		} else if got.State != "restored" || ioValue(f.data[p], "8:0") != "rbps=500 wbps=600 riops=70 wiops=80" {
			t.Fatal("original parent cap lost", got, f.data[p])
		}
	}
}
