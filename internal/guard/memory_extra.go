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

func externalMemoryCap(env Environment, file string, original map[string]string) uint64 {
	cap := uint64(math.MaxUint64)
	for dir := env.Target; ; dir = filepath.Dir(dir) {
		value, _ := read(filepath.Join(dir, file))
		if dir == env.Target {
			if saved, ok := original[file+":"]; ok {
				value = saved
			}
		}
		if n := maxNumber(value); n < cap {
			cap = n
		}
		if dir == filepath.Dir(dir) {
			break
		}
	}
	return cap
}

func memoryExtras(c Config, env Environment, original map[string]string, wantMem bool, requestedMem, effectiveMem uint64) ([]Setting, []string, error) {
	var settings []Setting
	var warnings []string
	page := uint64(os.Getpagesize())
	if c.MemoryHigh != "" {
		n, _ := ParseBytes(c.MemoryHigh)
		n = n / page * page
		if wantMem && n > requestedMem {
			return nil, nil, errors.New("memory_high exceeds requested memory budget; candidate rejected")
		}
		cap := externalMemoryCap(env, "memory.high", original)
		hard := externalMemoryCap(env, "memory.max", original)
		if wantMem && effectiveMem < hard {
			hard = effectiveMem
		}
		if hard < cap {
			cap = hard
		}
		if cap < n {
			n = cap
			warnings = append(warnings, "memory_high constrained by existing high/hard limit")
		}
		settings = append(settings, Setting{File: "memory.high", Value: strconv.FormatUint(n, 10)})
	}
	if c.MemorySwapMax != "" {
		n, _ := ParseBytes(c.MemorySwapMax)
		n = n / page * page
		if cap := externalMemoryCap(env, "memory.swap.max", original); cap < n {
			n = cap
			warnings = append(warnings, "memory_swap_max constrained by existing swap limit")
		}
		settings = append(settings, Setting{File: "memory.swap.max", Value: strconv.FormatUint(n, 10)})
	}
	return settings, warnings, nil
}

// Conservatively defer below-used swap decreases rather than forcing existing
// swapped pages back into already constrained RAM. Zero is allowed when unused.
func (e *Engine) swapHeadroom(target string) error {
	v, err := e.Files.Read(filepath.Join(e.Env.Target, "memory.swap.current"))
	if err != nil {
		return fmt.Errorf("cannot read memory.swap.current: %w", err)
	}
	used, err := strconv.ParseUint(strings.TrimSpace(v), 10, 64)
	if err != nil {
		return errors.New("invalid memory.swap.current")
	}
	budget := maxNumber(target)
	if used > budget {
		return fmt.Errorf("unsafe swap decrease: target=%s current=%d; existing swap retained", target, used)
	}
	if used > 0 {
		margin := used/20 + uint64(os.Getpagesize())
		if margin > budget-used {
			return fmt.Errorf("unsafe swap decrease: target=%s current=%d; require 5%% + one page headroom", target, used)
		}
	}
	return nil
}
