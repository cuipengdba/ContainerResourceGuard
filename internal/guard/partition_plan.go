package guard

import (
	"errors"
	"fmt"
	"path/filepath"
	"sort"
)

type profileBinding struct {
	profile DeviceProfile
	block   IOBlockDevice
}

func resolveProfileBinding(d DeviceProfile) (IOBlockDevice, error) {
	dev, err := resolveProfileDevice(d)
	if err != nil {
		return IOBlockDevice{}, err
	}
	b, err := ResolveIOBlockDevice(dev)
	if err == nil && b.Identity != d.Identity {
		err = errors.New("profile device changed while resolving its control target")
	}
	return b, err
}

// Sibling partitions share one whole-device cap in this container. Select the
// conservative bandwidth baseline, never sum caps or silently pick the last path.
func percentageIO(c Config, env Environment, original map[string]string, profile Profile,
	resolve func(DeviceProfile) (IOBlockDevice, error), related func(string, string) (bool, error)) (settings []Setting, devices []DeviceCoverage, warnings []string) {
	groups := map[string][]profileBinding{}
	for _, d := range profile.Devices {
		b, err := resolve(d)
		if err == nil && (!validDevice(b.Device) || !validDevice(b.ControlDevice) || b.Identity != d.Identity || !validIdentity(b.ControlIdentity)) {
			err = errors.New("invalid or changed filesystem/control identity")
		}
		if err != nil {
			devices = append(devices, DeviceCoverage{ProfileDevice: d.Device, State: "unavailable", Detail: err.Error()})
			warnings = append(warnings, "IO unmanaged: "+err.Error())
			continue
		}
		groups[b.ControlDevice] = append(groups[b.ControlDevice], profileBinding{d, b})
	}
	keys := make([]string, 0, len(groups))
	for key := range groups {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	_, _, percent := c.corePercentages()
	for _, key := range keys {
		members := groups[key]
		identity := members[0].block.ControlIdentity
		rates := deviceRates(members[0].profile)
		seen := map[string]bool{}
		reason := ""
		for _, m := range members {
			if m.block.ControlIdentity != identity || seen[m.block.Device] {
				reason = "duplicate filesystem or conflicting whole-device identity"
			}
			seen[m.block.Device] = true
			if len(members) > 1 && m.block.Partition == 0 {
				reason = "whole-device and partition profiles overlap; select one calibrated layer"
			}
			for axis, value := range deviceRates(m.profile) {
				if value < rates[axis] {
					rates[axis] = value
				}
			}
		}
		for _, other := range keys {
			if other == key {
				continue
			}
			if same, err := related(key, other); same || err != nil {
				reason = "overlapping or unreadable device stack; use one calibrated layer per path"
				break
			}
			if groups[other][0].block.ControlIdentity == identity {
				reason = "one stable control identity resolves to multiple devices"
			}
		}
		// Percentages target bandwidth only. Profile IOPS remain diagnostic;
		// preserve external IOPS, or the owned journal's pre-CRG baseline.
		for axis := 0; axis < 2; axis++ {
			rates[axis] = scaleRate(rates[axis], percent)
			if rates[axis] == 0 {
				reason = "percent below integer BPS minimum"
			}
		}
		for _, m := range members {
			coverage := DeviceCoverage{ProfileDevice: m.profile.Device, FilesystemDevice: m.block.Device, Device: key, State: "planned", Detail: "shared whole-device bandwidth cap; minimum calibrated read/write BPS; external/original IOPS retained; actual write/readback required"}
			if reason != "" {
				coverage.State, coverage.Detail = "skipped", reason
			}
			devices = append(devices, coverage)
		}
		if reason != "" {
			warnings = append(warnings, "IO unmanaged: "+key+": "+reason)
			continue
		}
		value := fmt.Sprintf("rbps=%d wbps=%d riops=max wiops=max", rates[0], rates[1])
		previous, _ := read(filepath.Join(env.Target, "io.max"))
		previous = ioValue(previous, key)
		if v, ok := original["io.max:"+key]; ok {
			previous = v
		}
		settings = append(settings, Setting{File: "io.max", Device: key, DeviceIdentity: identity, Value: clampIO(value, previous)})
	}
	return
}
