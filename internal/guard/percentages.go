package guard

import (
	"errors"
	"fmt"
	"math"
)

// Each percentage has an independent default. Percent remains a deprecated
// compatibility input for already deployed configurations, never a new default.
type ResourcePercentages struct {
	CPUPercent    *float64 `json:"cpu_percent,omitempty"`
	MemoryPercent *float64 `json:"memory_percent,omitempty"`
	IOPercent     *float64 `json:"io_percent,omitempty"`
}

func (p ResourcePercentages) fields() map[string]*float64 {
	return map[string]*float64{"cpu_percent": p.CPUPercent, "memory_percent": p.MemoryPercent, "io_percent": p.IOPercent}
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
		if v != nil && (math.IsNaN(*v) || math.IsInf(*v, 0) || *v > 100 || *v <= 0) {
			return fmt.Errorf("%s must be finite and greater than 0 and at most 100", name)
		}
	}
	for _, v := range []**float64{&c.CPUPercent, &c.MemoryPercent, &c.IOPercent} {
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
