package guard

import (
	"context"
	"errors"
	"io"
	"sort"
	"time"
)

const ProfileMethod = "direct-sync-qdepth1-seq1m-random4k"

// Bound automatic profile reads without pulling in the later reload feature.
func ReadBoundedFile(path string) ([]byte, error) {
	f, err := openConfigFile(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	st, err := f.Stat()
	if err != nil {
		return nil, err
	}
	if !st.Mode().IsRegular() || st.Size() > 1<<20 {
		return nil, errors.New("profile must be a regular file no larger than 1MiB")
	}
	b, err := io.ReadAll(io.LimitReader(f, (1<<20)+1))
	if len(b) > 1<<20 {
		return nil, errors.New("profile grew beyond 1MiB")
	}
	return b, err
}

// The RC3 reader intentionally retains the v1 profile format. The IO development
// milestone adds v2 sample records; it is not silently backported here.
func ValidateProfile(p Profile) error {
	if p.Version != 1 || p.Method != ProfileMethod || len(p.Devices) == 0 || len(p.Devices) > 256 {
		return errors.New("unsupported or empty IO profile")
	}
	seen := map[string]bool{}
	for _, d := range p.Devices {
		if !validDevice(d.Device) || !validIdentity(d.Identity) || seen[d.Identity] || d.ReadBPS == 0 || d.WriteBPS == 0 || d.ReadIOPS == 0 || d.WriteIOPS == 0 {
			return errors.New("invalid or duplicate IO profile device/rates")
		}
		seen[d.Identity] = true
	}
	return nil
}

func CalibrateRepeated(ctx context.Context, directory string, seconds, samples int) (Profile, error) {
	p := Profile{Version: 1, Method: ProfileMethod, CreatedUTC: time.Now().UTC().Format(time.RFC3339)}
	if samples < 1 || samples > 9 || seconds < 1 || seconds > 30 {
		return p, errors.New("samples must be 1..9 and seconds 1..30 per phase")
	}
	var rates [4][]uint64
	var d DeviceProfile
	for i := 0; i < samples; i++ {
		one, err := Calibrate(ctx, directory, seconds)
		if err != nil {
			return p, err
		}
		if err = ValidateProfile(one); err != nil || len(one.Devices) != 1 {
			return p, errors.New("invalid calibration sample")
		}
		v := one.Devices[0]
		if i > 0 && (v.Device != d.Device || v.Identity != d.Identity) {
			return p, errors.New("device changed between samples")
		}
		d = v
		for axis, n := range []uint64{v.ReadBPS, v.WriteBPS, v.ReadIOPS, v.WriteIOPS} {
			rates[axis] = append(rates[axis], n)
		}
	}
	var med [4]uint64
	for axis, values := range rates {
		sort.Slice(values, func(i, j int) bool { return values[i] < values[j] })
		med[axis] = values[(len(values)-1)/2]
	}
	d.ReadBPS, d.WriteBPS, d.ReadIOPS, d.WriteIOPS = med[0], med[1], med[2], med[3]
	p.Devices = []DeviceProfile{d}
	return p, ValidateProfile(p)
}

func MergeProfiles(base, addition Profile, replace bool) (Profile, error) {
	if err := ValidateProfile(base); err != nil {
		return Profile{}, err
	}
	if err := ValidateProfile(addition); err != nil {
		return Profile{}, err
	}
	p := addition
	p.Devices = append([]DeviceProfile(nil), base.Devices...)
	for _, d := range addition.Devices {
		found := false
		for i, old := range p.Devices {
			if old.Identity == d.Identity {
				if !replace {
					return Profile{}, errors.New("matching identity requires explicit replacement")
				}
				p.Devices[i], found = d, true
				break
			}
		}
		if !found {
			p.Devices = append(p.Devices, d)
		}
	}
	return p, ValidateProfile(p)
}
