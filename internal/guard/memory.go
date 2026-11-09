package guard

import (
	"errors"
	"fmt"
	"math"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

func (e *Engine) memoryUsed() (uint64, error) {
	v, err := e.Files.Read(filepath.Join(e.Env.Target, "memory.current"))
	if err != nil {
		return 0, fmt.Errorf("cannot read memory.current: %w", err)
	}
	n, err := strconv.ParseUint(strings.TrimSpace(v), 10, 64)
	if err != nil {
		return 0, errors.New("invalid memory.current")
	}
	return n, nil
}

func checkHeadroom(target string, used, reserve uint64) error {
	budget := maxNumber(target)
	margin := used/20 + (16 << 20)
	if used > budget || margin > budget-used || reserve > budget-used-margin {
		return fmt.Errorf("unsafe memory decrease: target=%s current=%d; require 5%% + 16 MiB headroom and growth reserve=%d", target, used, reserve)
	}
	return nil
}

func (e *Engine) memoryHeadroom(target string, reserve uint64) error {
	used, err := e.memoryUsed()
	if err != nil {
		return err
	}
	return checkHeadroom(target, used, reserve)
}

func (e *Engine) memoryPreflight(target string) error {
	first, err := e.memoryUsed()
	if err != nil {
		return err
	}
	if err = checkHeadroom(target, first, 0); err != nil {
		return err
	}
	before, _ := e.Files.Read(filepath.Join(e.Env.Target, "memory.events"))
	pause := e.Pause
	if pause == nil {
		pause = time.Sleep
	}
	pause(50 * time.Millisecond)
	second, err := e.memoryUsed()
	if err != nil {
		return err
	}
	var reserve uint64
	if second > first {
		growth := second - first
		// Reserve one second at the observed 50 ms growth rate. This is a
		// conservative snapshot, not a guarantee about future allocations.
		if growth > math.MaxUint64/20 {
			reserve = math.MaxUint64
		} else {
			reserve = growth * 20
		}
	}
	if err = checkHeadroom(target, second, reserve); err != nil {
		return err
	}
	after, _ := e.Files.Read(filepath.Join(e.Env.Target, "memory.events"))
	old := eventCounts(before)
	for k, n := range eventCounts(after) {
		if n > old[k] {
			return fmt.Errorf("unsafe memory decrease: memory.events %s increased during preflight", k)
		}
	}
	if text, err := e.Files.Read(filepath.Join(e.Env.Target, "memory.pressure")); err == nil {
		for _, line := range strings.Split(text, "\n") {
			f := strings.Fields(line)
			if len(f) < 2 {
				continue
			}
			for _, kv := range f[1:] {
				if !strings.HasPrefix(kv, "avg10=") {
					continue
				}
				n, err := strconv.ParseFloat(strings.TrimPrefix(kv, "avg10="), 64)
				if err != nil || math.IsNaN(n) || math.IsInf(n, 0) || n < 0 {
					return errors.New("invalid memory.pressure avg10")
				}
				if f[0] == "full" && n >= 1 || f[0] == "some" && n >= 10 {
					return fmt.Errorf("unsafe memory decrease: memory PSI %s avg10=%.2f%%", f[0], n)
				}
			}
		}
	}
	return nil
}

func eventCounts(text string) map[string]uint64 {
	r := map[string]uint64{}
	for _, line := range strings.Split(text, "\n") {
		f := strings.Fields(line)
		if len(f) != 2 {
			continue
		}
		switch f[0] {
		case "high", "max", "oom", "oom_kill":
			if n, err := strconv.ParseUint(f[1], 10, 64); err == nil {
				r[f[0]] = n
			}
		}
	}
	return r
}
