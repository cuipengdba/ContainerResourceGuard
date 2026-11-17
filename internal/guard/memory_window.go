package guard

import (
	"errors"
	"fmt"
	"math"
	"path/filepath"
	"time"
)

type memoryWindow struct {
	target, current string
	seconds         int
	started, last   time.Time
	samples         int
	used            uint64
	events          map[string]uint64
}

// This history is deliberately not persisted: restart, target change, missing
// observations, pressure, and unsafe growth all require a fresh safe window.
func (e *Engine) memoryDecreasePreflight(file, target, current string) error {
	if err := e.memoryPreflight(target); err != nil {
		delete(e.memoryWindows, file)
		return reasonError("memory_safety", err)
	}
	if e.Config.MemoryStableSeconds == 0 {
		delete(e.memoryWindows, file)
		return nil
	}
	used, err := e.memoryUsed()
	if err != nil {
		delete(e.memoryWindows, file)
		return reasonError("memory_safety", err)
	}
	text, err := e.Files.Read(filepath.Join(e.Env.Target, "memory.events"))
	var events map[string]uint64
	if err == nil {
		events, err = parseSelectedCounts(text, []string{"high", "max", "oom", "oom_kill"})
		if err == nil && len(events) != 4 {
			err = errors.New("memory stable window requires high/max/oom/oom_kill counters")
		}
	}
	if err != nil {
		delete(e.memoryWindows, file)
		return reasonError("memory_safety", err)
	}
	// PSI remains optional on kernels without that interface. When provided,
	// parse all required fields strictly rather than treating bad text as zero.
	if text, readErr := e.Files.Read(filepath.Join(e.Env.Target, "memory.pressure")); readErr == nil {
		pressure, err := parseMemoryPressure(text)
		if err != nil {
			delete(e.memoryWindows, file)
			return reasonError("memory_safety", err)
		}
		if pressure["full"].Avg10 >= 1 || pressure["some"].Avg10 >= 10 {
			delete(e.memoryWindows, file)
			return reasonError("memory_safety", errors.New("memory pressure prevents stable window"))
		}
	}
	now := time.Now()
	if e.Now != nil {
		now = e.Now()
	}
	interval := e.Config.IntervalSeconds
	if interval < 1 {
		interval = 15
	}
	previous, ok := e.memoryWindows[file]
	reset := !ok || previous.target != target || previous.current != current || previous.seconds != e.Config.MemoryStableSeconds || now.Before(previous.last) || now.Sub(previous.last) > time.Duration(2*interval+1)*time.Second
	if !reset {
		for key, value := range events {
			if value != previous.events[key] {
				delete(e.memoryWindows, file)
				return reasonError("memory_safety", errors.New("memory events changed across stable-window observations"))
			}
		}
		elapsed := now.Sub(previous.last).Seconds()
		if elapsed > 0 && used > previous.used {
			growth := math.Ceil(float64(used-previous.used) / elapsed)
			reserve := uint64(math.MaxUint64)
			if growth < float64(uint64(math.MaxUint64)) {
				reserve = uint64(growth)
			}
			if err := checkHeadroom(target, used, reserve); err != nil {
				delete(e.memoryWindows, file)
				return reasonError("memory_safety", err)
			}
		}
	}
	if e.memoryWindows == nil {
		e.memoryWindows = map[string]memoryWindow{}
	}
	if reset {
		previous = memoryWindow{target: target, current: current, seconds: e.Config.MemoryStableSeconds, started: now, last: now, samples: 1, used: used, events: events}
	} else if now.Sub(previous.last) >= time.Second {
		previous.last, previous.used, previous.events = now, used, events
		previous.samples++
	}
	e.memoryWindows[file] = previous
	if previous.samples >= 3 && now.Sub(previous.started) >= time.Duration(e.Config.MemoryStableSeconds)*time.Second {
		return nil
	}
	// Stable text avoids per-cycle status/log writes merely for a countdown.
	return reasonError("memory_window", fmt.Errorf("waiting for memory stable window: require %ds and at least three spaced safe observations; no forced reclaim", e.Config.MemoryStableSeconds))
}
