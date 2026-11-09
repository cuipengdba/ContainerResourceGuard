package guard

import (
	"errors"
	"fmt"
	"strconv"
	"strings"
)

func parseMemTotal(text string) (uint64, error) {
	var result uint64
	for _, line := range strings.Split(text, "\n") {
		f := strings.Fields(line)
		if len(f) == 0 || f[0] != "MemTotal:" {
			continue
		}
		if result != 0 || len(f) != 3 || f[2] != "kB" {
			return 0, errors.New("invalid or duplicate MemTotal")
		}
		v, err := strconv.ParseUint(f[1], 10, 64)
		if err != nil || v == 0 || v > 1<<54 {
			return 0, errors.New("invalid MemTotal")
		}
		result = v * 1024
	}
	if result == 0 {
		return 0, errors.New("host MemTotal unavailable")
	}
	return result, nil
}

// Capacity failure is separate from cgroup identity failure. Manual limits and
// disable/restore remain possible; percent never uses a virtualized total.
func discoverCapacity(env *Environment, readSource func(string) (string, error), exists func(string) bool, verify func(string, string) error) {
	env.CPUCapacitySource = "/sys/devices/system/cpu/online"
	if exists("/host/sys/devices/system/cpu/online") {
		env.CPUCapacitySource = "/host/sys/devices/system/cpu/online"
	}
	env.MemoryCapacitySource = "/proc/meminfo"
	if exists("/host/proc/meminfo") {
		env.MemoryCapacitySource = "/host/proc/meminfo"
	}
	env.OnlineCPUs, env.MemoryBytes = 0, 0
	for _, kind := range []string{"cpu", "memory"} {
		source := env.CPUCapacitySource
		if kind == "memory" {
			source = env.MemoryCapacitySource
		}
		err := verify(source, kind)
		if err == nil {
			var data string
			data, err = readSource(source)
			if err == nil {
				if kind == "cpu" {
					env.OnlineCPUs, err = CountCPUs(data)
				} else {
					env.MemoryBytes, err = parseMemTotal(data)
				}
			}
		}
		if err != nil {
			env.CapacityWarnings = append(env.CapacityWarnings, fmt.Sprintf("host %s capacity unverified (%s): %v; percent dimension skipped", kind, source, err))
		}
	}
}
