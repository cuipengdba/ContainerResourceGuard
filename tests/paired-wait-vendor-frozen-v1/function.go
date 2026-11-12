//go:build linux && amd64

package main

import (
	"errors"
	"fmt"
	"github.com/cilium/ebpf"
	"golang.org/x/sys/unix"
	"io"
	"os"
	"runtime"
	"strconv"
	"strings"
	"unsafe"
)

var functionNames = []string{"xfs_file_buffered_write", "iomap_file_buffered_write", "folio_wait_writeback", "balance_dirty_pages", "rwsem_down_write_slowpath"}

func functionPMU() (uint32, uint64, error) {
	raw, e := bounded("/sys/bus/event_source/devices/kprobe/type", 128)
	if e != nil {
		return 0, 0, errors.New("KPROBE_PMU_TYPE")
	}
	v, e := strconv.ParseUint(strings.TrimSpace(string(raw)), 10, 32)
	if e != nil || v == 0 {
		return 0, 0, errors.New("KPROBE_PMU_TYPE_VALUE")
	}
	raw, e = bounded("/sys/bus/event_source/devices/kprobe/format/retprobe", 128)
	if e != nil {
		return 0, 0, errors.New("KPROBE_PMU_RETURN_FORMAT")
	}
	s := strings.TrimSpace(string(raw))
	if !strings.HasPrefix(s, "config:") {
		return 0, 0, errors.New("KPROBE_PMU_RETURN_FORMAT")
	}
	bit, e := strconv.ParseUint(strings.TrimPrefix(s, "config:"), 10, 6)
	if e != nil {
		return 0, 0, errors.New("KPROBE_PMU_RETURN_BIT")
	}
	return uint32(v), uint64(1) << bit, nil
}
func addFunctionHooks(out []Hook) ([]Hook, error) {
	if _, _, e := functionPMU(); e != nil {
		return nil, e
	}
	raw, e := bounded("/sys/kernel/tracing/available_filter_functions", 32<<20)
	if e != nil {
		return nil, errors.New("FUNCTION_AVAILABILITY")
	}
	names := map[string]bool{}
	for _, line := range strings.Split(string(raw), "\n") {
		fields := strings.Fields(line)
		if len(fields) > 0 {
			names[fields[0]] = true
		}
	}
	for i, name := range functionNames {
		if !names[name] {
			return nil, fmt.Errorf("FUNCTION_UNAVAILABLE:%s", name)
		}
		for j, direction := range []string{"function_enter", "function_exit"} {
			out = append(out, Hook{Category: "function", Name: name, Call: name, Direction: direction, Type: uint32(201 + 2*i + j), SHA: digest(raw)})
		}
	}
	return out, nil
}

// Open the PMU directly: there is no tracefs fallback, symbol offset, target
// register access, pointer export or function return-value read.
func attachFunctionPMU(h Hook, program *ebpf.Program) (io.Closer, error) {
	allowed := false
	for _, name := range functionNames {
		allowed = allowed || h.Name == name
	}
	if !allowed || program.Type() != ebpf.Kprobe {
		return nil, errors.New("FUNCTION_ALLOWLIST")
	}
	kind, ret, e := functionPMU()
	if e != nil {
		return nil, e
	}
	symbol, e := unix.BytePtrFromString(h.Name)
	if e != nil {
		return nil, e
	}
	config := uint64(0)
	if h.Direction == "function_exit" {
		config = ret
	} else if h.Direction != "function_enter" {
		return nil, errors.New("FUNCTION_DIRECTION")
	}
	attr := unix.PerfEventAttr{Size: unix.PERF_ATTR_SIZE_VER1, Type: kind, Config: config, Ext1: uint64(uintptr(unsafe.Pointer(symbol)))}
	fd, e := unix.PerfEventOpen(&attr, -1, 0, -1, unix.PERF_FLAG_FD_CLOEXEC)
	runtime.KeepAlive(symbol)
	if e != nil {
		return nil, fmt.Errorf("FUNCTION_PMU_OPEN:%s:%w", h.Name, e)
	}
	f := os.NewFile(uintptr(fd), "own-temporary-function-perf")
	if e = unix.IoctlSetInt(fd, unix.PERF_EVENT_IOC_SET_BPF, program.FD()); e != nil {
		f.Close()
		return nil, errors.New("FUNCTION_SET_BPF")
	}
	if e = unix.IoctlSetInt(fd, unix.PERF_EVENT_IOC_ENABLE, 0); e != nil {
		f.Close()
		return nil, errors.New("FUNCTION_ENABLE")
	}
	return f, nil
}

// Entries and returns share a per-thread stack so nested different functions
// cannot overwrite an in-flight syscall or fabricate cross-function pairs.
// Any observed orphan, depth overflow, non-monotonic event or unfinished frame
// makes the diagnostic incomplete. Perf losses remain a separate criterion.
func pairFunctions(events []Event) ([]Pair, []string) {
	pairs := []Pair{}
	issues := []string{}
	stacks := map[uint32][]Event{}
	for _, event := range events {
		if event.Direction != "function_enter" && event.Direction != "function_exit" {
			continue
		}
		stack := stacks[event.TID]
		if event.Direction == "function_enter" {
			if len(stack) >= 64 {
				issues = append(issues, "function_depth_limit")
				delete(stacks, event.TID)
				continue
			}
			stacks[event.TID] = append(stack, event)
			continue
		}
		if len(stack) == 0 {
			issues = append(issues, "function_orphan_return:"+event.Call)
			continue
		}
		entry := stack[len(stack)-1]
		if entry.Call != event.Call || entry.PID != event.PID || entry.CgroupID != event.CgroupID || event.Mono < entry.Mono {
			issues = append(issues, "function_mismatched_return:"+event.Call)
			delete(stacks, event.TID)
			continue
		}
		pairs = append(pairs, Pair{entry, event, event.Mono - entry.Mono})
		stacks[event.TID] = stack[:len(stack)-1]
	}
	for _, stack := range stacks {
		if len(stack) > 0 {
			issues = append(issues, "function_unfinished_entry")
		}
	}
	return pairs, issues
}
