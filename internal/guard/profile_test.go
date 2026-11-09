package guard

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"
)

func sampleProfile(n uint64) Profile {
	return Profile{Version: 1, Method: ProfileMethod, CreatedUTC: "2026-11-10T00:00:00Z", Devices: []DeviceProfile{{Device: "253:0", Identity: strings.Repeat("a", 64), ReadBPS: n * 100, WriteBPS: n * 80, ReadIOPS: n * 10, WriteIOPS: n * 5}}}
}

func TestRepeatedCalibrationMedianVariabilityAndCancellation(t *testing.T) {
	pass := 0
	measure := func(context.Context, string, int) (Profile, error) {
		n := []uint64{10, 100, 20}[pass]
		pass++
		return sampleProfile(n), nil
	}
	p, err := calibrateRepeated(context.Background(), "/test", 2, 3, measure)
	if err != nil || p.Version != 2 || p.Devices[0].ReadBPS != 2000 || len(p.Devices[0].Measurements) != 3 {
		t.Fatal(p, err)
	}
	q := Quality(p.Devices[0])
	if q.SpreadPercent["read_bps"] != 450 || len(q.Warnings) != 4 {
		t.Fatal(q)
	}
	p.Devices[0].ReadBPS++
	if ValidateProfile(p) == nil {
		t.Fatal("inconsistent aggregate accepted")
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	calls := 0
	_, err = calibrateRepeated(ctx, "/test", 1, 3, func(context.Context, string, int) (Profile, error) { calls++; return sampleProfile(1), nil })
	if !errors.Is(err, context.Canceled) || calls != 0 {
		t.Fatal(err, calls)
	}
	for _, count := range []int{0, 10} {
		if _, err := CalibrateRepeated(ctx, "/test", 1, count); err == nil {
			t.Fatal(count)
		}
	}
}

func TestRepeatedCalibrationRejectsChangedDeviceAndNoPartialProfile(t *testing.T) {
	pass := 0
	p, err := calibrateRepeated(context.Background(), "/test", 1, 2, func(context.Context, string, int) (Profile, error) {
		v := sampleProfile(10)
		if pass == 1 {
			v.Devices[0].Identity = strings.Repeat("b", 64)
		}
		pass++
		return v, nil
	})
	if err == nil || len(p.Devices) != 0 {
		t.Fatal(p, err)
	}
	p, err = calibrateRepeated(context.Background(), "/test", 1, 2, func(context.Context, string, int) (Profile, error) { return Profile{}, errors.New("disk error") })
	if err == nil || len(p.Devices) != 0 {
		t.Fatal(p, err)
	}
	if median([]uint64{40, 10, 30, 20}) != 20 {
		t.Fatal("even sample count did not select lower median")
	}
}

func TestProfileMergeIsExplicitAndPreservesLegacyQualityWarning(t *testing.T) {
	a, b := sampleProfile(10), sampleProfile(20)
	if _, err := MergeProfiles(a, b, false); err == nil {
		t.Fatal("implicit replacement accepted")
	}
	m, err := MergeProfiles(a, b, true)
	if err != nil || m.Version != 2 || len(m.Devices) != 1 || m.Devices[0].ReadBPS != 2000 || a.Devices[0].ReadBPS != 1000 {
		t.Fatal(m, err)
	}
	if len(Quality(m.Devices[0]).Warnings) == 0 {
		t.Fatal("legacy sample quality invented")
	}
	b.Devices[0].Identity = strings.Repeat("b", 64)
	b.Devices[0].Device = "253:1"
	m, err = MergeProfiles(a, b, false)
	if err != nil || len(m.Devices) != 2 {
		t.Fatal(m, err)
	}
	b.Devices = append(b.Devices, b.Devices[0])
	if ValidateProfile(b) == nil {
		t.Fatal("duplicate identity accepted")
	}
}

func TestProfileInspectionDoesNotConfuseIdentityWithPerformance(t *testing.T) {
	p := sampleProfile(10)
	p.CreatedUTC = "2020-01-01T00:00:00Z"
	v, err := inspectProfile(p, time.Date(2026, 11, 10, 0, 0, 0, 0, time.UTC), func(DeviceProfile) (string, error) { return "253:1", nil })
	if err != nil || v.Devices[0].Device != "253:1" || v.Devices[0].State != "resolved" || len(v.Warnings) < 2 || v.Devices[0].Quality.Samples != 0 {
		t.Fatal(v, err)
	}
	v, err = inspectProfile(p, time.Now(), func(DeviceProfile) (string, error) { return "", errors.New("replacement device") })
	if err != nil || v.Devices[0].State != "unavailable" {
		t.Fatal(v, err)
	}
}
