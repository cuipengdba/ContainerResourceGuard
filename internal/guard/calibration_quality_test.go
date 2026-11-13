package guard

import (
	"context"
	"encoding/json"
	"errors"
	"math"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestAutomaticIOReportsSelectedProfileQualityWithoutChangingBaseline(t *testing.T) {
	// This tests the injected save boundary, not platform-specific directory
	// fsync. The production AtomicJSON persistence checks remain separate.
	writeProfile := func(path string, value any) error {
		encoded, err := json.Marshal(value)
		if err != nil {
			return err
		}
		return os.WriteFile(path, encoded, 0600)
	}
	for _, tc := range []struct {
		name       string
		cached     bool
		legacy     bool
		variable   bool
		otherFirst bool
	}{
		{name: "fresh-variable", variable: true},
		{name: "fresh-stable"},
		{name: "cached-variable", cached: true, variable: true},
		{name: "cached-stable-selected-after-variable-device", cached: true, otherFirst: true},
		{name: "cached-legacy-has-no-invented-samples", cached: true, legacy: true},
		{name: "fresh-variable-merged-with-other-device", variable: true, otherFirst: true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			dir := t.TempDir()
			selected := CalibrationSelection{Directory: "/data", Device: "8:1", Identity: strings.Repeat("a", 64)}
			device := DeviceProfile{Device: selected.Device, Identity: selected.Identity, ReadBPS: 120, WriteBPS: 120, ReadIOPS: 120, WriteIOPS: 120}
			version := 2
			if tc.legacy {
				version = 1
			} else {
				for _, value := range []uint64{100, 120, 160} {
					if !tc.variable {
						value = 120
					}
					device.Measurements = append(device.Measurements, IOMeasurement{ReadBPS: value, WriteBPS: value, ReadIOPS: value, WriteIOPS: value, SecondsPerPhase: 3, CreatedUTC: "2026-11-13T00:00:00Z"})
				}
			}
			measuredProfile := Profile{Version: version, Method: ProfileMethod, CreatedUTC: "2026-11-13T00:00:00Z", Devices: []DeviceProfile{device}}
			prior := measuredProfile
			prior.Devices = nil
			if tc.otherFirst {
				other := device
				other.Device, other.Identity = "8:2", strings.Repeat("b", 64)
				other.Measurements = []IOMeasurement{{ReadBPS: 60, WriteBPS: 60, ReadIOPS: 60, WriteIOPS: 60, SecondsPerPhase: 3, CreatedUTC: "2026-11-13T00:00:00Z"}}
				other.ReadBPS, other.WriteBPS, other.ReadIOPS, other.WriteIOPS = 60, 60, 60, 60
				prior.Devices = append(prior.Devices, other)
			}
			if tc.cached {
				prior.Devices = append(prior.Devices, device)
			}
			path := filepath.Join(dir, "profile.json")
			var priorBytes []byte
			if len(prior.Devices) > 0 {
				if err := writeProfile(path, prior); err != nil {
					t.Fatal(err)
				}
				priorBytes, _ = os.ReadFile(path)
			}
			target := filepath.Join(dir, "group")
			if err := os.Mkdir(target, 0700); err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(filepath.Join(target, "io.max"), nil, 0600); err != nil {
				t.Fatal(err)
			}
			c := Config{IOProfile: path}
			if err := c.Validate(); err != nil {
				t.Fatal(err)
			}
			measurements, saves := 0, 0
			status := prepareAutomaticIO(context.Background(), c, Environment{Target: target},
				func() (CalibrationSelection, error) { return selected, nil },
				func(context.Context, string, int, int) (Profile, error) { measurements++; return measuredProfile, nil },
				ReadBoundedFile, func(name string, value any) error { saves++; return writeProfile(name, value) })
			wantState := "calibrated"
			if tc.cached {
				wantState = "reused"
				current, err := os.ReadFile(path)
				if err != nil || string(current) != string(priorBytes) || measurements != 0 || saves != 0 {
					t.Fatal("cache quality reporting changed or remeasured the saved baseline")
				}
			} else if measurements != 1 || saves != 1 {
				t.Fatal("fresh quality reporting changed the measurement/save policy")
			}
			if status.State != wantState || status.Quality == nil {
				t.Fatalf("missing accepted selected-device quality: %+v", status)
			}
			quality := status.Quality
			if tc.legacy {
				if quality.Samples != 0 || len(quality.SpreadPercent) != 0 || len(quality.Warnings) != 1 || !strings.Contains(quality.Warnings[0], "fewer than three") {
					t.Fatal("legacy aggregate invented quality measurements", quality)
				}
			} else {
				wantSpread, wantWarnings := 0.0, 0
				if tc.variable {
					wantSpread, wantWarnings = 50, 4
				}
				if quality.Samples != 3 || len(quality.SpreadPercent) != 4 || len(quality.Warnings) != wantWarnings {
					t.Fatal("wrong selected-device quality", quality)
				}
				for _, axis := range []string{"read_bps", "write_bps", "read_iops", "write_iops"} {
					if math.Abs(quality.SpreadPercent[axis]-wantSpread) > 1e-9 {
						t.Fatal("quality came from another device or changed dispersion", quality)
					}
					if tc.variable && !strings.Contains(strings.Join(quality.Warnings, ";"), axis+" spread exceeds 25%") {
						t.Fatal("variable baseline warning missing", axis)
					}
				}
			}
			stored, err := LoadProfile(path)
			if err != nil {
				t.Fatal(err)
			}
			found := false
			for _, value := range stored.Devices {
				if value.Identity == selected.Identity {
					found = true
					if value.ReadBPS != 120 || value.WriteBPS != 120 || value.ReadIOPS != 120 || value.WriteIOPS != 120 {
						t.Fatal("quality reporting changed aggregate rates")
					}
				}
			}
			if !found {
				t.Fatal("selected profile lost")
			}
			encoded, err := json.Marshal(map[string]any{"result": status})
			if err != nil || !strings.Contains(string(encoded), `"quality":{"samples":`) {
				t.Fatal("automatic_io_prepared log payload lost quality", string(encoded), err)
			}
		})
	}
}

func TestAutomaticIOFailedSaveDoesNotPublishAcceptedQuality(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "io.max"), nil, 0600); err != nil {
		t.Fatal(err)
	}
	selected := CalibrationSelection{Directory: "/data", Device: "8:1", Identity: strings.Repeat("a", 64)}
	p := Profile{Version: 1, Method: ProfileMethod, Devices: []DeviceProfile{{Device: selected.Device, Identity: selected.Identity, ReadBPS: 100, WriteBPS: 100, ReadIOPS: 100, WriteIOPS: 100}}}
	c := Config{IOProfile: filepath.Join(dir, "profile.json")}
	if err := c.Validate(); err != nil {
		t.Fatal(err)
	}
	status := prepareAutomaticIO(context.Background(), c, Environment{Target: dir},
		func() (CalibrationSelection, error) { return selected, nil },
		func(context.Context, string, int, int) (Profile, error) { return p, nil },
		func(string) ([]byte, error) { return nil, os.ErrNotExist },
		func(string, any) error { return errors.New("disk full") })
	encoded, err := json.Marshal(status)
	if status.State != "degraded" || status.ReasonCode != "calibration_profile_write_failed" || status.Quality != nil || err != nil || strings.Contains(string(encoded), `"quality"`) {
		t.Fatal("unpersisted measurement advertised as accepted baseline quality", status, string(encoded), err)
	}
}
