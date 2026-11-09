package guard

import (
	"fmt"
	"time"
)

type ProfileDeviceView struct {
	ProfileDevice string         `json:"profile_device"`
	Device        string         `json:"device,omitempty"`
	State         string         `json:"state"`
	Detail        string         `json:"detail,omitempty"`
	Quality       ProfileQuality `json:"quality"`
}
type ProfileView struct {
	Version    int                 `json:"version"`
	CreatedUTC string              `json:"created_utc"`
	Devices    []ProfileDeviceView `json:"devices"`
	Warnings   []string            `json:"warnings,omitempty"`
}

func LoadProfile(path string) (Profile, error) {
	var p Profile
	b, err := ReadBoundedFile(path)
	if err != nil {
		return p, err
	}
	if err = Decode(b, &p); err != nil {
		return p, err
	}
	return p, ValidateProfile(p)
}

// Only inspect named profiles and currently visible block-device identities.
// Never write a cgroup or enable a host IO scheduler/cost controller.
func InspectProfile(p Profile) (ProfileView, error) {
	return inspectProfile(p, time.Now(), resolveProfileDevice)
}
func inspectProfile(p Profile, now time.Time, resolve func(DeviceProfile) (string, error)) (ProfileView, error) {
	v := ProfileView{Version: p.Version, CreatedUTC: p.CreatedUTC}
	if err := ValidateProfile(p); err != nil {
		return v, err
	}
	created, err := time.Parse(time.RFC3339, p.CreatedUTC)
	if err != nil {
		v.Warnings = append(v.Warnings, "profile timestamp missing or invalid")
	} else if created.After(now.Add(5 * time.Minute)) {
		v.Warnings = append(v.Warnings, "profile creation time is in the future")
	} else if now.Sub(created) > 30*24*time.Hour {
		v.Warnings = append(v.Warnings, "profile older than 30 days; reassess after hardware or workload changes")
	}
	seen := map[string]bool{}
	for _, d := range p.Devices {
		i := ProfileDeviceView{ProfileDevice: d.Device, State: "resolved", Quality: Quality(d)}
		device, err := resolve(d)
		if err != nil {
			i.State, i.Detail = "unavailable", err.Error()
		} else if seen[device] {
			i.State, i.Detail = "ambiguous", "multiple entries resolve to the same device"
		} else {
			i.Device = device
			seen[device] = true
			i.Detail = "stable device identity matches; this does not establish current performance"
		}
		v.Devices = append(v.Devices, i)
	}
	v.Warnings = append(v.Warnings, fmt.Sprintf("%d device profiles inspected; calibration is an explicit local measurement, not physical capacity", len(v.Devices)))
	return v, nil
}
