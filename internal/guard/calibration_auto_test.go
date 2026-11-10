package guard

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestAutomaticIOReuseAndFaultBoundaries(t *testing.T) {
	selected := CalibrationSelection{Directory: "/data", Device: "8:1", Identity: strings.Repeat("a", 64), TotalBytes: 1 << 40, AvailableBytes: 1 << 39}
	profile := Profile{Version: 1, Method: ProfileMethod, Devices: []DeviceProfile{{Device: selected.Device, Identity: selected.Identity, ReadBPS: 1024, WriteBPS: 1024, ReadIOPS: 10, WriteIOPS: 10}}}
	for _, tc := range []struct{ name, want, fault string }{
		{"missing-profile", "calibrated", ""},
		{"cached-profile", "reused", "cached"},
		{"renumbered-device", "reused", "renumbered"},
		{"readonly-profile", "calibration_profile_unreadable", "unreadable"},
		{"corrupt-profile", "calibration_cached_profile_invalid", "corrupt"},
		{"inherited-cap", "calibration_existing_io_limit", "cap"},
		{"output-permission", "calibration_output_unwritable", "output"},
		{"measurement-failure", "calibration_measurement_failed", "measure"},
		{"device-swapped", "calibration_device_changed", "swap"},
		{"full-output", "calibration_profile_write_failed", "save"},
		{"no-filesystem", "calibration_no_eligible_filesystem", "select"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			dir := t.TempDir()
			c := Config{Percent: 20, IOProfile: filepath.Join(dir, "profile.json")}
			if err := c.Validate(); err != nil {
				t.Fatal(err)
			}
			target := filepath.Join(dir, "group")
			if err := os.Mkdir(target, 0700); err != nil {
				t.Fatal(err)
			}
			cap := ""
			if tc.fault == "cap" {
				cap = "253:9 rbps=1 wbps=max riops=max wiops=max"
			}
			if err := os.WriteFile(filepath.Join(target, "io.max"), []byte(cap), 0600); err != nil {
				t.Fatal(err)
			}
			if tc.fault == "output" {
				c.IOProfile = filepath.Join(target, "io.max", "cannot-create.json")
			}
			measured, saved := 0, 0
			s := prepareAutomaticIO(context.Background(), c, Environment{Target: target},
				func() (CalibrationSelection, error) {
					if tc.fault == "select" {
						return selected, errors.New("no eligible mount")
					}
					return selected, nil
				}, func(ctx context.Context, dir string, seconds, samples int) (Profile, error) {
					measured++
					if dir != selected.Directory || seconds != 3 || samples != 3 {
						t.Fatal("unexpected calibration policy")
					}
					if _, ok := ctx.Deadline(); !ok {
						t.Fatal("missing cancellation deadline")
					}
					if tc.fault == "measure" {
						return Profile{}, errors.New("direct IO not available")
					}
					p := profile
					p.Devices = append([]DeviceProfile(nil), profile.Devices...)
					if tc.fault == "swap" {
						p.Devices[0].Identity = strings.Repeat("b", 64)
					}
					return p, nil
				}, func(string) ([]byte, error) {
					switch tc.fault {
					case "cached", "renumbered":
						p := profile
						p.Devices = append([]DeviceProfile(nil), profile.Devices...)
						if tc.fault == "renumbered" {
							p.Devices[0].Device = "8:9"
						}
						return json.Marshal(p)
					case "corrupt":
						return []byte("{bad"), nil
					case "unreadable":
						return nil, os.ErrPermission
					default:
						return nil, os.ErrNotExist
					}
				}, func(path string, v any) error {
					saved++
					if tc.fault == "save" {
						return errors.New("no space")
					}
					if err := ValidateProfile(v.(Profile)); err != nil {
						t.Fatal(err)
					}
					return nil
				})
			if s == nil || (s.State != tc.want && s.ReasonCode != tc.want) {
				t.Fatalf("%+v", s)
			}
			if tc.want == "reused" && (measured != 0 || saved != 0) {
				t.Fatal("cache reuse performed IO")
			}
			if tc.want != "calibrated" && tc.fault != "save" && saved != 0 {
				t.Fatal("failure persisted a profile")
			}
			if tc.fault == "cap" || tc.fault == "output" || tc.fault == "unreadable" || tc.fault == "corrupt" {
				if measured != 0 {
					t.Fatal("precondition failure still benchmarked")
				}
			}
		})
	}
}

func TestAutomaticIONeverRunsForReadOnlyModes(t *testing.T) {
	for _, c := range []Config{{ResourceMode: "manual", Mode: "enforce"}, {ResourceMode: "percent", Mode: "observe"}, {ResourceMode: "percent", Mode: "enforce", IOCalibration: "off"}} {
		if got := prepareAutomaticIO(context.Background(), c, Environment{}, func() (CalibrationSelection, error) {
			t.Fatal("unexpected discovery")
			return CalibrationSelection{}, nil
		}, nil, nil, nil); got != nil {
			t.Fatal(got)
		}
	}
	c := Config{Percent: 20, IOCalibration: "sometimes"}
	if c.Validate() == nil {
		t.Fatal("accepted invalid automatic calibration mode")
	}
}
