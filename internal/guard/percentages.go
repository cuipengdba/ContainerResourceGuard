package guard

import (
	"errors"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// Each percentage has an independent default. Percent remains a deprecated
// compatibility input for already deployed configurations, never a new default.
type ResourcePercentages struct {
	CPUPercent        *float64 `json:"cpu_percent,omitempty"`
	MemoryPercent     *float64 `json:"memory_percent,omitempty"`
	IOPercent         *float64 `json:"io_percent,omitempty"`
	PidsPercent       *float64 `json:"pids_percent,omitempty"`
	CPUWeightPercent  *float64 `json:"cpu_weight_percent,omitempty"`
	IOWeightPercent   *float64 `json:"io_weight_percent,omitempty"`
	MemoryHighPercent *float64 `json:"memory_high_percent,omitempty"`
	MemorySwapPercent *float64 `json:"memory_swap_percent,omitempty"`
}

func (p ResourcePercentages) fields() map[string]*float64 {
	return map[string]*float64{"cpu_percent": p.CPUPercent, "memory_percent": p.MemoryPercent, "io_percent": p.IOPercent,
		"pids_percent": p.PidsPercent, "cpu_weight_percent": p.CPUWeightPercent, "io_weight_percent": p.IOWeightPercent,
		"memory_high_percent": p.MemoryHighPercent, "memory_swap_percent": p.MemorySwapPercent}
}

func (p ResourcePercentages) present() bool {
	for _, v := range p.fields() {
		if v != nil {
			return true
		}
	}
	return false
}

func (c *Config) ApplyPercentageOverrides(p ResourcePercentages) {
	if p.CPUPercent != nil {
		c.CPUPercent = p.CPUPercent
	}
	if p.MemoryPercent != nil {
		c.MemoryPercent = p.MemoryPercent
	}
	if p.IOPercent != nil {
		c.IOPercent = p.IOPercent
	}
	if p.PidsPercent != nil {
		c.PidsPercent = p.PidsPercent
	}
	if p.CPUWeightPercent != nil {
		c.CPUWeightPercent = p.CPUWeightPercent
	}
	if p.IOWeightPercent != nil {
		c.IOWeightPercent = p.IOWeightPercent
	}
	if p.MemoryHighPercent != nil {
		c.MemoryHighPercent = p.MemoryHighPercent
	}
	if p.MemorySwapPercent != nil {
		c.MemorySwapPercent = p.MemorySwapPercent
	}
}

func (c Config) independentPercentages() bool {
	return c.ResourceMode != "manual" && c.Percent == 0 && !c.percentPresent
}

func (c *Config) validatePercentages() error {
	if c.ResourceMode == "manual" {
		if c.Percent != 0 || c.percentPresent || c.ResourcePercentages.present() {
			return errors.New("manual resource_mode cannot include percentage parameters")
		}
		return nil
	}
	if c.Percent != 0 || c.percentPresent {
		if c.ResourcePercentages.present() {
			return errors.New("deprecated percent cannot be mixed with independent percentage parameters")
		}
		if math.IsNaN(c.Percent) || math.IsInf(c.Percent, 0) || c.Percent <= 0 || c.Percent > 100 {
			return errors.New("percent must be greater than 0 and at most 100")
		}
		return nil
	}
	if c.PidsMax != nil || c.CPUWeight != nil || c.IOWeight != nil || c.MemoryHigh != "" || c.MemorySwapMax != "" {
		return errors.New("independent percentage mode uses *_percent fields; absolute optional controls belong in manual mode")
	}
	for name, v := range c.ResourcePercentages.fields() {
		if v != nil && (math.IsNaN(*v) || math.IsInf(*v, 0) || *v > 100 || *v < 0 || *v == 0 && name != "memory_swap_percent") {
			return fmt.Errorf("%s must be finite and greater than 0 and at most 100 (memory_swap_percent also accepts 0)", name)
		}
	}
	for _, v := range []**float64{&c.CPUPercent, &c.MemoryPercent, &c.IOPercent, &c.PidsPercent, &c.CPUWeightPercent, &c.IOWeightPercent, &c.MemoryHighPercent, &c.MemorySwapPercent} {
		if *v == nil {
			n := float64(20)
			*v = &n
		}
	}
	return nil
}

func (c Config) corePercentages() (cpu, memory, io float64) {
	if !c.independentPercentages() {
		return c.Percent, c.Percent, c.Percent
	}
	value := func(v *float64) float64 {
		if v == nil {
			return 20
		}
		return *v
	}
	return value(c.CPUPercent), value(c.MemoryPercent), value(c.IOPercent)
}

// Expanded values are used only by planning. The stored configuration retains
// percentage intent so capacity changes and reload cannot silently freeze bytes.
func expandPercentageExtras(c Config, env Environment) (Config, []string) {
	if !c.independentPercentages() {
		return c, nil
	}
	var warnings []string
	weight := func(p *float64) *uint64 {
		n := uint64(math.Floor(*p * 100))
		if n < 1 {
			n = 1
		}
		return &n
	}
	c.CPUWeight, c.IOWeight = weight(c.CPUWeightPercent), weight(c.IOWeightPercent)
	if env.HostPidsMax != nil {
		n := scaleRate(*env.HostPidsMax, *c.PidsPercent)
		if n == 0 {
			n = 1
		}
		c.PidsMax = &n
	} else {
		warnings = append(warnings, "pids percent unmanaged: verified host pid_max unavailable")
	}
	if env.MemoryBytes > 0 {
		_, memory, _ := c.corePercentages()
		high := *c.MemoryHighPercent
		if high > memory {
			high = memory
			warnings = append(warnings, "memory_high_percent constrained by requested memory_percent")
		}
		n := scaleRate(env.MemoryBytes, high) / uint64(os.Getpagesize()) * uint64(os.Getpagesize())
		if n >= 16<<20 {
			c.MemoryHigh = strconv.FormatUint(n, 10) + "B"
		} else {
			warnings = append(warnings, "memory_high percent unmanaged: target below16MiB")
		}
	}
	if env.HostSwapBytes != nil {
		c.MemorySwapMax = strconv.FormatUint(scaleRate(*env.HostSwapBytes, *c.MemorySwapPercent), 10) + "B"
	} else {
		warnings = append(warnings, "swap percent unmanaged: verified host SwapTotal unavailable")
	}
	warnings = append(warnings, env.ExtraCapacityWarnings...)
	return c, warnings
}

func discoverPercentageCapacity(env *Environment) {
	proc := filepath.Dir(env.MemoryCapacitySource)
	if proc != "/proc" && proc != "/host/proc" {
		return
	}
	pidPath := filepath.Join(proc, "sys/kernel/pid_max")
	if raw, err := readPercentCapacity(pidPath); err == nil {
		if n, err := strconv.ParseUint(strings.TrimSpace(raw), 10, 64); err == nil && n > 0 && n <= math.MaxInt32 {
			env.HostPidsMax = &n
			env.PidsCapacitySource = pidPath
		}
	}
	if env.MemoryBytes == 0 {
		return
	}
	if raw, err := readPercentCapacity(env.MemoryCapacitySource); err == nil {
		seen := false
		for _, line := range strings.Split(raw, "\n") {
			f := strings.Fields(line)
			if len(f) == 0 || f[0] != "SwapTotal:" {
				continue
			}
			if seen || len(f) != 3 || f[2] != "kB" {
				env.HostSwapBytes = nil
				break
			}
			seen = true
			if n, err := strconv.ParseUint(f[1], 10, 64); err == nil && n <= math.MaxInt64/1024 {
				n *= 1024
				env.HostSwapBytes = &n
				env.SwapCapacitySource = env.MemoryCapacitySource
			}
		}
	}
}
