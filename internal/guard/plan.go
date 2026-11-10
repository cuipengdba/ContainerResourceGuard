package guard

import (
	"encoding/hex"
	"errors"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

type DeviceProfile struct {
	Device    string `json:"device"`
	Identity  string `json:"identity"`
	ReadBPS   uint64 `json:"read_bps"`
	WriteBPS  uint64 `json:"write_bps"`
	ReadIOPS  uint64 `json:"read_iops"`
	WriteIOPS uint64 `json:"write_iops"`
}
type Profile struct {
	Version    int             `json:"version"`
	Method     string          `json:"method"`
	CreatedUTC string          `json:"created_utc"`
	Devices    []DeviceProfile `json:"devices"`
}
type Setting struct {
	File           string `json:"file"`
	Device         string `json:"device,omitempty"`
	DeviceIdentity string `json:"device_identity,omitempty"`
	Value          string `json:"value"`
}

func (s Setting) Key() string { return s.File + ":" + s.Device }

type Plan struct {
	Percentages  *ResourcePercentages `json:"percentages,omitempty"`
	Environment  Environment          `json:"environment"`
	Percent      float64              `json:"percent,omitempty"`
	ResourceMode string               `json:"resource_mode,omitempty"`
	Settings     []Setting            `json:"settings"`
	Warnings     []string             `json:"warnings,omitempty"`
	Devices      []DeviceCoverage     `json:"io_devices,omitempty"`
	Paths        []PathCoverage       `json:"data_paths,omitempty"`
}

func maxNumber(s string) uint64 {
	v, e := strconv.ParseUint(strings.TrimSpace(s), 10, 64)
	if e != nil {
		return math.MaxUint64
	}
	return v
}
func cpuCores(s string) float64 {
	f := strings.Fields(s)
	if len(f) != 2 || f[0] == "max" {
		return math.Inf(1)
	}
	a, e := strconv.ParseFloat(f[0], 64)
	b, x := strconv.ParseFloat(f[1], 64)
	if e != nil || x != nil || b <= 0 {
		return math.Inf(1)
	}
	return a / b
}

func BuildPlan(c Config, env Environment, original map[string]string) (Plan, error) {
	if err := c.Validate(); err != nil {
		return Plan{}, err
	}
	p := Plan{Environment: env, Percent: c.Percent, ResourceMode: c.ResourceMode}
	if c.independentPercentages() {
		values := c.ResourcePercentages
		p.Percentages = &values
	}
	expanded, extraWarnings := expandPercentageExtras(c, env)
	c = expanded
	p.Warnings = append(p.Warnings, extraWarnings...)
	if p.ResourceMode == "" {
		p.ResourceMode = "percent"
	}
	desiredCPU, desiredMem, wantCPU, wantMem := requestedResources(c, env)
	desiredMem = desiredMem / uint64(os.Getpagesize()) * uint64(os.Getpagesize())
	cpu, mem := desiredCPU, desiredMem
	// Never raise an existing external limit. For values CRG owns, use the saved baseline.
	for dir := env.Target; ; dir = filepath.Dir(dir) {
		a, _ := read(filepath.Join(dir, "cpu.max"))
		b, _ := read(filepath.Join(dir, "memory.max"))
		if dir == env.Target {
			if v, ok := original["cpu.max:"]; ok {
				a = v
			}
			if v, ok := original["memory.max:"]; ok {
				b = v
			}
		}
		cpu = math.Min(cpu, cpuCores(a))
		if v := maxNumber(b); v < mem {
			mem = v
		}
		if dir == filepath.Dir(dir) {
			break
		}
	}
	if env.EffectiveCPUs != "" {
		if n, e := CountCPUs(env.EffectiveCPUs); e == nil {
			cpu = math.Min(cpu, float64(n))
		}
	}
	if wantCPU && cpu < desiredCPU {
		p.Warnings = append(p.Warnings, "CPU constrained by existing limits/cpuset")
	}
	if wantMem && mem < desiredMem {
		p.Warnings = append(p.Warnings, "memory constrained by existing limits")
	}
	quota := uint64(cpu * 100000)
	if wantCPU && quota < 1000 {
		p.Warnings = append(p.Warnings, "CPU target below kernel minimum quota; CPU skipped")
	} else if wantCPU {
		p.Settings = append(p.Settings, Setting{File: "cpu.max", Value: fmt.Sprintf("%d 100000", quota)})
	}
	if wantMem && mem < 16<<20 {
		p.Warnings = append(p.Warnings, "memory target below 16 MiB; memory skipped")
	} else if wantMem {
		p.Settings = append(p.Settings, Setting{File: "memory.max", Value: strconv.FormatUint(mem, 10)})
	}
	if c.PidsMax != nil {
		n := *c.PidsMax
		for dir := env.Target; ; dir = filepath.Dir(dir) {
			v, _ := read(filepath.Join(dir, "pids.max"))
			if dir == env.Target {
				if saved, ok := original["pids.max:"]; ok {
					v = saved
				}
			}
			if limit := maxNumber(v); limit < n {
				n = limit
			}
			if dir == filepath.Dir(dir) {
				break
			}
		}
		if n < *c.PidsMax {
			p.Warnings = append(p.Warnings, "pids_max constrained by existing limits")
		}
		p.Settings = append(p.Settings, Setting{File: "pids.max", Value: strconv.FormatUint(n, 10)})
	}
	if c.CPUWeight != nil {
		p.Settings = append(p.Settings, Setting{File: "cpu.weight", Value: strconv.FormatUint(*c.CPUWeight, 10)})
	}
	if c.IOWeight != nil {
		p.Settings = append(p.Settings, Setting{File: "io.weight", Value: "default " + strconv.FormatUint(*c.IOWeight, 10)})
	}
	extraSettings, memoryWarnings, extraErr := memoryExtras(c, env, original, wantMem, desiredMem, mem)
	if extraErr != nil {
		return p, extraErr
	}
	p.Settings = append(p.Settings, extraSettings...)
	p.Warnings = append(p.Warnings, memoryWarnings...)
	if c.ResourceMode == "manual" {
		settings, devices, warnings := manualIO(c, env, original, manualDevice, relatedDevices)
		p.Settings = append(p.Settings, settings...)
		p.Devices = devices
		p.Warnings = append(p.Warnings, warnings...)
		p.Paths = pathCoverage(c.DataPaths, p.Settings)
		return p, nil
	}
	data, e := os.ReadFile(c.IOProfile)
	if e != nil {
		p.Warnings = append(p.Warnings, "IO unmanaged: profile unavailable: "+e.Error())
		p.Paths = pathCoverage(c.DataPaths, p.Settings)
		return p, nil
	}
	var profile Profile
	if e = Decode(data, &profile); e != nil {
		return p, fmt.Errorf("invalid IO profile: %w", e)
	}
	if profile.Version != 1 || len(profile.Devices) == 0 || profile.Method != "direct-sync-qdepth1-seq1m-random4k" {
		return p, errors.New("unsupported or empty IO profile")
	}
	seen := map[string]bool{}
	resolved := map[string]DeviceProfile{}
	for _, d := range profile.Devices {
		if d.ReadBPS == 0 || d.WriteBPS == 0 || d.ReadIOPS == 0 || d.WriteIOPS == 0 {
			return p, errors.New("IO profile rates must all be positive")
		}
		dev, e := resolveProfileDevice(d)
		if e != nil {
			p.Warnings = append(p.Warnings, "IO unmanaged: "+e.Error())
			p.Devices = append(p.Devices, DeviceCoverage{ProfileDevice: d.Device, State: "unavailable", Detail: e.Error()})
			continue
		}
		if seen[dev] {
			return p, errors.New("duplicate profile device")
		}
		seen[dev] = true
		resolved[dev] = d
	}
	for _, d := range profile.Devices {
		dev, err := resolveProfileDevice(d)
		if err != nil {
			continue
		}
		coverage := DeviceCoverage{ProfileDevice: d.Device, Device: dev, State: "planned", Detail: "all four calibrated dimensions; actual write/readback required"}
		stacked := false
		for other := range resolved {
			if other == dev {
				continue
			}
			related, err := relatedDevices(dev, other)
			if err != nil || related {
				stacked = true
				break
			}
		}
		if stacked {
			coverage.State, coverage.Detail = "skipped", "overlapping or unreadable device stack; use one calibrated layer per path"
			p.Devices = append(p.Devices, coverage)
			p.Warnings = append(p.Warnings, "IO unmanaged: "+dev+": "+coverage.Detail)
			continue
		}
		_, _, ioPercent := c.corePercentages()
		scale := func(n uint64) uint64 { return scaleRate(n, ioPercent) }
		if scale(d.ReadBPS) == 0 || scale(d.WriteBPS) == 0 || scale(d.ReadIOPS) == 0 || scale(d.WriteIOPS) == 0 {
			p.Warnings = append(p.Warnings, "IO unmanaged: percent below whole-unit BPS/IOPS minimum for device "+dev)
			coverage.State, coverage.Detail = "skipped", "percent below integer BPS/IOPS minimum"
			p.Devices = append(p.Devices, coverage)
			continue
		}
		value := fmt.Sprintf("rbps=%d wbps=%d riops=%d wiops=%d", scale(d.ReadBPS), scale(d.WriteBPS), scale(d.ReadIOPS), scale(d.WriteIOPS))
		// Keep stricter pre-existing limits for each dimension of this device.
		prev, _ := read(filepath.Join(env.Target, "io.max"))
		prev = ioValue(prev, dev)
		if v, ok := original["io.max:"+dev]; ok {
			prev = v
		}
		value = clampIO(value, prev)
		p.Settings = append(p.Settings, Setting{File: "io.max", Device: dev, DeviceIdentity: d.Identity, Value: value})
		p.Devices = append(p.Devices, coverage)
	}
	p.Paths = pathCoverage(c.DataPaths, p.Settings)
	for _, v := range p.Paths {
		if v.State != "planned" {
			p.Warnings = append(p.Warnings, "data path "+v.Path+": "+v.Detail)
		}
	}
	return p, nil
}

func scaleRate(n uint64, percent float64) uint64 {
	return uint64(math.Floor(float64(n) * percent / 100))
}

func resolveProfileDevice(d DeviceProfile) (string, error) {
	return resolveDevice(d, DeviceIdentity, func() ([]string, error) {
		entries, err := os.ReadDir("/sys/dev/block")
		if err != nil {
			return nil, err
		}
		names := make([]string, 0, len(entries))
		for _, v := range entries {
			names = append(names, v.Name())
		}
		return names, nil
	})
}

func resolveDevice(d DeviceProfile, identity func(string) (string, error), devices func() ([]string, error)) (string, error) {
	id, decodeErr := hex.DecodeString(d.Identity)
	if !validDevice(d.Device) || decodeErr != nil || len(id) != 32 {
		return "", errors.New("invalid profile device identity")
	}
	if id, e := identity(d.Device); e == nil && id == d.Identity {
		return d.Device, nil
	}
	entries, e := devices()
	if e != nil {
		return "", e
	}
	var matches []string
	for _, v := range entries {
		if id, e := identity(v); e == nil && id == d.Identity {
			matches = append(matches, v)
		}
	}
	if len(matches) != 1 {
		return "", errors.New("calibrated device missing or ambiguous; recalibrate explicitly")
	}
	return matches[0], nil
}
func ioValue(text, dev string) string {
	for _, line := range strings.Split(text, "\n") {
		f := strings.Fields(line)
		if len(f) > 1 && f[0] == dev {
			return canonicalIO(strings.Join(f[1:], " "))
		}
	}
	return "rbps=max wbps=max riops=max wiops=max"
}
func ioMap(v string) map[string]string {
	m := map[string]string{"rbps": "max", "wbps": "max", "riops": "max", "wiops": "max"}
	for _, s := range strings.Fields(v) {
		f := strings.SplitN(s, "=", 2)
		if len(f) == 2 {
			if _, ok := m[f[0]]; ok {
				m[f[0]] = f[1]
			}
		}
	}
	return m
}
func canonicalIO(v string) string {
	m := ioMap(v)
	return fmt.Sprintf("rbps=%s wbps=%s riops=%s wiops=%s", m["rbps"], m["wbps"], m["riops"], m["wiops"])
}
func clampIO(v, prev string) string {
	m, b := ioMap(v), ioMap(prev)
	for k, n := range m {
		if maxNumber(b[k]) < maxNumber(n) {
			m[k] = b[k]
		}
	}
	return canonicalIO(fmt.Sprintf("rbps=%s wbps=%s riops=%s wiops=%s", m["rbps"], m["wbps"], m["riops"], m["wiops"]))
}
