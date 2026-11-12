package guard

import (
	"errors"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
)

// Omitted manual dimensions are unmanaged, never implicitly unlimited.
type ManualLimits struct {
	CPUCores   *float64 `json:"cpu_cores,omitempty"`
	MemoryMax  string   `json:"memory_max,omitempty"`
	MemoryHigh string   `json:"memory_high,omitempty"`
	ReadBPS    string   `json:"io_read_bps,omitempty"`
	WriteBPS   string   `json:"io_write_bps,omitempty"`
	ReadIOPS   *uint64  `json:"io_read_iops,omitempty"`
	WriteIOPS  *uint64  `json:"io_write_iops,omitempty"`
}

var byteQuantity = regexp.MustCompile(`^(0|[1-9][0-9]*)(B|KiB|MiB|GiB|TiB|KB|MB|GB|TB)?$`)

func ParseBytes(s string) (uint64, error) {
	f := byteQuantity.FindStringSubmatch(s)
	if f == nil {
		return 0, errors.New("expected whole bytes with optional B/KiB/MiB/GiB/TiB/KB/MB/GB/TB unit")
	}
	n, err := strconv.ParseUint(f[1], 10, 64)
	if err != nil {
		return 0, err
	}
	m := map[string]uint64{"": 1, "B": 1, "KiB": 1 << 10, "MiB": 1 << 20, "GiB": 1 << 30, "TiB": 1 << 40, "KB": 1000, "MB": 1000000, "GB": 1000000000, "TB": 1000000000000}[f[2]]
	if n > math.MaxInt64/m {
		return 0, errors.New("byte quantity exceeds signed 64-bit controller range")
	}
	return n * m, nil
}

func (m ManualLimits) HasIO() bool {
	return m.ReadBPS != "" || m.WriteBPS != "" || m.ReadIOPS != nil || m.WriteIOPS != nil
}

// memory_max remains a configuration alias for upgrades, never a request to
// install a hard cap. The canonical manual name is memory_high.
func (m ManualLimits) memoryTarget() string {
	if m.MemoryHigh != "" {
		return m.MemoryHigh
	}
	return m.MemoryMax
}

func (m ManualLimits) Validate() error {
	if m.MemoryHigh != "" && m.MemoryMax != "" {
		return errors.New("specify limits.memory_high; do not combine it with legacy limits.memory_max")
	}
	if m.CPUCores == nil && m.memoryTarget() == "" && !m.HasIO() {
		return errors.New("manual limits must specify at least one dimension")
	}
	if m.CPUCores != nil && (math.IsNaN(*m.CPUCores) || math.IsInf(*m.CPUCores, 0) || *m.CPUCores < 0.01 || *m.CPUCores > 1048576) {
		return errors.New("cpu_cores must be finite and within 0.01..1048576")
	}
	for name, s := range map[string]string{"memory_max": m.MemoryMax, "memory_high": m.MemoryHigh, "io_read_bps": m.ReadBPS, "io_write_bps": m.WriteBPS} {
		if s == "" {
			continue
		}
		n, err := ParseBytes(s)
		if err != nil || n == 0 {
			return fmt.Errorf("%s must be a positive byte quantity", name)
		}
		if (name == "memory_max" || name == "memory_high") && n < 16<<20 {
			return fmt.Errorf("%s must be at least 16MiB", name)
		}
	}
	for _, n := range []*uint64{m.ReadIOPS, m.WriteIOPS} {
		if n != nil && (*n == 0 || *n > math.MaxInt64) {
			return errors.New("manual IOPS must be 1..9223372036854775807")
		}
	}
	return nil
}

func requestedResources(c Config, env Environment) (float64, uint64, bool, bool) {
	if c.ResourceMode != "manual" {
		cpu, memory, _ := c.corePercentages()
		return float64(env.OnlineCPUs) * cpu / 100, uint64(float64(env.MemoryBytes) * memory / 100), true, true
	}
	var cpu float64
	var mem uint64
	if c.Limits.CPUCores != nil {
		cpu = *c.Limits.CPUCores
	}
	if c.Limits.memoryTarget() != "" {
		mem, _ = ParseBytes(c.Limits.memoryTarget())
	}
	return cpu, mem, c.Limits.CPUCores != nil, c.Limits.memoryTarget() != ""
}

func manualDevice(path string) (string, string, error) {
	dev, err := fileDevice(path)
	if err != nil {
		return "", "", err
	}
	if _, err = os.Stat(filepath.Join("/sys/dev/block", dev)); err != nil {
		return "", "", errors.New("filesystem does not resolve to an exposed block device; no backend inferred")
	}
	device, err := ResolveIOBlockDevice(dev)
	if err != nil {
		return "", "", err
	}
	return device.ControlDevice, device.ControlIdentity, nil
}

func manualIO(c Config, env Environment, original map[string]string, resolve func(string) (string, string, error), related func(string, string) (bool, error)) (settings []Setting, devices []DeviceCoverage, warnings []string) {
	if !c.Limits.HasIO() {
		return
	}
	m := map[string]string{"rbps": "max", "wbps": "max", "riops": "max", "wiops": "max"}
	if c.Limits.ReadBPS != "" {
		n, _ := ParseBytes(c.Limits.ReadBPS)
		m["rbps"] = strconv.FormatUint(n, 10)
	}
	if c.Limits.WriteBPS != "" {
		n, _ := ParseBytes(c.Limits.WriteBPS)
		m["wbps"] = strconv.FormatUint(n, 10)
	}
	if c.Limits.ReadIOPS != nil {
		m["riops"] = strconv.FormatUint(*c.Limits.ReadIOPS, 10)
	}
	if c.Limits.WriteIOPS != nil {
		m["wiops"] = strconv.FormatUint(*c.Limits.WriteIOPS, 10)
	}
	resolved := map[string]string{}
	for _, path := range c.DataPaths {
		dev, id, err := resolve(path)
		if err != nil {
			warnings = append(warnings, "manual IO unmanaged for "+path+": "+err.Error())
			continue
		}
		if !validDevice(dev) || !validIdentity(id) {
			warnings = append(warnings, "manual IO unmanaged: invalid device identity for "+path)
			continue
		}
		if old, ok := resolved[dev]; ok && old != id {
			warnings = append(warnings, "manual IO device identity changed while resolving paths")
			return nil, nil, warnings
		}
		resolved[dev] = id
	}
	names := make([]string, 0, len(resolved))
	for dev := range resolved {
		names = append(names, dev)
	}
	sort.Strings(names)
	for _, dev := range names {
		coverage := DeviceCoverage{Device: dev, State: "planned", Detail: "manual shared whole-device limits from data_paths; no benchmark used"}
		stacked := false
		for _, other := range names {
			if dev == other {
				continue
			}
			same, err := related(dev, other)
			if same || err != nil {
				stacked = true
				break
			}
		}
		if stacked {
			coverage.State = "skipped"
			coverage.Detail = "overlapping or unreadable device stack"
			devices = append(devices, coverage)
			warnings = append(warnings, "manual IO unmanaged: "+dev+": "+coverage.Detail)
			continue
		}
		prev, _ := read(filepath.Join(env.Target, "io.max"))
		prev = ioValue(prev, dev)
		if v, ok := original["io.max:"+dev]; ok {
			prev = v
		}
		v := canonicalIO(fmt.Sprintf("rbps=%s wbps=%s riops=%s wiops=%s", m["rbps"], m["wbps"], m["riops"], m["wiops"]))
		settings = append(settings, Setting{File: "io.max", Device: dev, DeviceIdentity: resolved[dev], Value: clampIO(v, prev)})
		devices = append(devices, coverage)
	}
	return
}
