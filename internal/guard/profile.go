package guard

import (
	"context"
	"errors"
	"fmt"
	"sort"
	"time"
)

const ProfileMethod = "direct-sync-qdepth1-seq1m-random4k"

type IOMeasurement struct {
	ReadBPS         uint64 `json:"read_bps"`
	WriteBPS        uint64 `json:"write_bps"`
	ReadIOPS        uint64 `json:"read_iops"`
	WriteIOPS       uint64 `json:"write_iops"`
	SecondsPerPhase int    `json:"seconds_per_phase"`
	CreatedUTC      string `json:"created_utc"`
}

type ProfileQuality struct {
	Samples       int                `json:"samples"`
	SpreadPercent map[string]float64 `json:"spread_percent,omitempty"`
	Warnings      []string           `json:"warnings,omitempty"`
}

func measurementRates(m IOMeasurement) []uint64 {
	return []uint64{m.ReadBPS, m.WriteBPS, m.ReadIOPS, m.WriteIOPS}
}
func deviceRates(d DeviceProfile) []uint64 {
	return []uint64{d.ReadBPS, d.WriteBPS, d.ReadIOPS, d.WriteIOPS}
}
func median(values []uint64) uint64 {
	sorted := append([]uint64(nil), values...)
	sort.Slice(sorted, func(i, j int) bool { return sorted[i] < sorted[j] })
	return sorted[(len(sorted)-1)/2] // Lower median is conservative for even counts.
}

func ValidateProfile(p Profile) error {
	if (p.Version != 1 && p.Version != 2) || len(p.Devices) == 0 || len(p.Devices) > 256 || p.Method != ProfileMethod {
		return errors.New("unsupported or empty IO profile")
	}
	seen := map[string]bool{}
	for _, d := range p.Devices {
		if !validDevice(d.Device) || !validIdentity(d.Identity) || seen[d.Identity] {
			return errors.New("invalid or duplicate IO profile identity")
		}
		seen[d.Identity] = true
		for _, n := range deviceRates(d) {
			if n == 0 {
				return errors.New("IO profile rates must all be positive")
			}
		}
		if len(d.Measurements) > 9 || p.Version == 1 && len(d.Measurements) > 0 {
			return errors.New("invalid measurement count/profile version")
		}
		for _, m := range d.Measurements {
			if m.SecondsPerPhase < 1 || m.SecondsPerPhase > 30 {
				return errors.New("invalid measurement phase duration")
			}
			if _, err := time.Parse(time.RFC3339, m.CreatedUTC); err != nil {
				return errors.New("invalid measurement timestamp")
			}
			for _, n := range measurementRates(m) {
				if n == 0 {
					return errors.New("measurement rates must all be positive")
				}
			}
		}
		if len(d.Measurements) > 0 {
			for axis, want := range deviceRates(d) {
				values := make([]uint64, 0, len(d.Measurements))
				for _, m := range d.Measurements {
					values = append(values, measurementRates(m)[axis])
				}
				if median(values) != want {
					return errors.New("profile aggregate differs from measurement median")
				}
			}
		}
	}
	return nil
}

func Quality(d DeviceProfile) ProfileQuality {
	q := ProfileQuality{Samples: len(d.Measurements)}
	if q.Samples < 3 {
		q.Warnings = append(q.Warnings, "fewer than three measurements; variability cannot be established reliably")
	}
	if q.Samples == 0 {
		return q
	}
	q.SpreadPercent = map[string]float64{}
	for axis, key := range []string{"read_bps", "write_bps", "read_iops", "write_iops"} {
		values := make([]uint64, 0, q.Samples)
		for _, m := range d.Measurements {
			values = append(values, measurementRates(m)[axis])
		}
		sort.Slice(values, func(i, j int) bool { return values[i] < values[j] })
		mid := median(values)
		if mid == 0 {
			q.Warnings = append(q.Warnings, "invalid zero sample")
			continue
		}
		spread := float64(values[len(values)-1]-values[0]) / float64(mid) * 100
		q.SpreadPercent[key] = spread
		if spread > 25 {
			q.Warnings = append(q.Warnings, key+" spread exceeds 25%; check device competition and repeat explicitly")
		}
	}
	return q
}

func CalibrateRepeated(ctx context.Context, directory string, seconds, samples int) (Profile, error) {
	return calibrateRepeated(ctx, directory, seconds, samples, Calibrate)
}

func calibrateRepeated(ctx context.Context, directory string, seconds, samples int, measure func(context.Context, string, int) (Profile, error)) (Profile, error) {
	p := Profile{Version: 2, Method: ProfileMethod, CreatedUTC: time.Now().UTC().Format(time.RFC3339)}
	if samples < 1 || samples > 9 {
		return p, errors.New("samples must be 1..9")
	}
	if seconds < 1 || seconds > 30 {
		return p, errors.New("seconds must be 1..30 per phase")
	}
	var d DeviceProfile
	for i := 0; i < samples; i++ {
		if err := ctx.Err(); err != nil {
			return p, err
		}
		s, err := measure(ctx, directory, seconds)
		if err != nil {
			return p, err
		}
		if err = ValidateProfile(s); err != nil {
			return p, err
		}
		if len(s.Devices) != 1 {
			return p, errors.New("each calibration pass must measure exactly one device")
		}
		v := s.Devices[0]
		if i == 0 {
			d = DeviceProfile{Device: v.Device, Identity: v.Identity}
		} else if d.Identity != v.Identity || d.Device != v.Device {
			return p, errors.New("device changed between samples; no profile accepted")
		}
		d.Measurements = append(d.Measurements, IOMeasurement{ReadBPS: v.ReadBPS, WriteBPS: v.WriteBPS, ReadIOPS: v.ReadIOPS, WriteIOPS: v.WriteIOPS, SecondsPerPhase: seconds, CreatedUTC: s.CreatedUTC})
	}
	values := make([]uint64, samples)
	aggregates := make([]uint64, 4)
	for axis := range aggregates {
		for i, m := range d.Measurements {
			values[i] = measurementRates(m)[axis]
		}
		aggregates[axis] = median(values)
	}
	d.ReadBPS, d.WriteBPS, d.ReadIOPS, d.WriteIOPS = aggregates[0], aggregates[1], aggregates[2], aggregates[3]
	p.Devices = []DeviceProfile{d}
	return p, ValidateProfile(p)
}

// Merge is an offline preview operation; caller explicitly chooses persistence.
func MergeProfiles(base, addition Profile, replace bool) (Profile, error) {
	if err := ValidateProfile(base); err != nil {
		return Profile{}, err
	}
	if err := ValidateProfile(addition); err != nil {
		return Profile{}, err
	}
	merged := Profile{Version: 2, Method: ProfileMethod, CreatedUTC: time.Now().UTC().Format(time.RFC3339), Devices: append([]DeviceProfile(nil), base.Devices...)}
	for _, d := range addition.Devices {
		found := false
		for i, old := range merged.Devices {
			if old.Identity == d.Identity {
				if !replace {
					return Profile{}, fmt.Errorf("identity %s already exists; explicit replacement required", d.Identity)
				}
				merged.Devices[i] = d
				found = true
				break
			}
		}
		if !found {
			merged.Devices = append(merged.Devices, d)
		}
	}
	return merged, ValidateProfile(merged)
}
