package main

import (
	"flag"
	"strings"

	"github.com/cuipengdba/ContainerResourceGuard/internal/guard"
)

func cliPercentages(flags *flag.FlagSet, values map[string]*float64) guard.ResourcePercentages {
	var p guard.ResourcePercentages
	flags.Visit(func(v *flag.Flag) {
		key := strings.ReplaceAll(v.Name, "-", "_")
		value, ok := values[key]
		if !ok {
			return
		}
		switch key {
		case "cpu_percent":
			p.CPUPercent = value
		case "memory_percent":
			p.MemoryPercent = value
		case "io_percent":
			p.IOPercent = value
		case "pids_percent":
			p.PidsPercent = value
		case "cpu_weight_percent":
			p.CPUWeightPercent = value
		case "io_weight_percent":
			p.IOWeightPercent = value
		case "memory_high_percent":
			p.MemoryHighPercent = value
		case "memory_swap_percent":
			p.MemorySwapPercent = value
		}
	})
	return p
}
