//go:build linux && amd64

package main

import (
	"errors"
	"io"
	"os"
	"strconv"
	"strings"
)

// This budget covers perf mmap data and metadata pages only. It does not
// represent total Go heap, BPF map, program, or process memory consumption.
type PerfBudget struct {
	PageBytes       int    `json:"page_bytes"`
	DataPages       int    `json:"data_pages_per_CPU"`
	PossibleCPUs    uint32 `json:"possible_CPU_slots"`
	DataBytes       int    `json:"data_bytes_per_CPU"`
	MaximumMapped   uint64 `json:"maximum_possible_mapped_bytes"`
	Cap             uint64 `json:"mapped_budget_cap_bytes"`
	ActualRings     int    `json:"actual_mapped_rings"`
	ActualMapped    uint64 `json:"actual_mapped_bytes"`
	ReaderDataBytes int    `json:"reader_buffer_size_bytes"`
}

func perfBudget(page int, cpus uint32) (PerfBudget, error) {
	const capBytes uint64 = 16 * 1024 * 1024
	p := PerfBudget{PageBytes: page, DataPages: 32, PossibleCPUs: cpus, Cap: capBytes}
	if page < 4096 || page > 65536 || page&(page-1) != 0 || cpus == 0 {
		return p, errors.New("PERF_BUDGET_INPUT")
	}
	perCPU := uint64(page) * 33
	if uint64(cpus) > capBytes/perCPU {
		return p, errors.New("PERF_MAPPED_BUDGET_EXCEEDED")
	}
	p.DataBytes = page * 32
	p.MaximumMapped = perCPU * uint64(cpus)
	return p, nil
}

// Addresses are parsed locally solely to total this collector's own mappings.
// Neither addresses nor mapping contents are exported in the report.
func parsePerfMappings(raw []byte, expected uint64) (int, uint64, error) {
	count := 0
	var total uint64
	for _, line := range strings.Split(string(raw), "\n") {
		fields := strings.Fields(line)
		if len(fields) < 6 {
			continue
		}
		name := strings.Join(fields[5:], " ")
		if name != "/anon_inode:[perf_event]" && name != "anon_inode:[perf_event]" {
			continue
		}
		span := strings.Split(fields[0], "-")
		if len(span) != 2 {
			return 0, 0, errors.New("PERF_MMAP_FORMAT")
		}
		lo, e := strconv.ParseUint(span[0], 16, 64)
		if e != nil {
			return 0, 0, errors.New("PERF_MMAP_FORMAT")
		}
		hi, e := strconv.ParseUint(span[1], 16, 64)
		if e != nil || hi <= lo || hi-lo != expected {
			return 0, 0, errors.New("PERF_MMAP_SIZE")
		}
		count++
		if count > 4096 {
			return 0, 0, errors.New("PERF_MMAP_COUNT")
		}
		total += hi - lo
	}
	return count, total, nil
}

func ownPerfMappings(expected uint64) (int, uint64, error) {
	f, e := os.Open("/proc/self/maps")
	if e != nil {
		return 0, 0, errors.New("PERF_MMAP_READ")
	}
	defer f.Close()
	raw, e := io.ReadAll(io.LimitReader(f, 1024*1024+1))
	if e != nil || len(raw) > 1024*1024 {
		return 0, 0, errors.New("PERF_MMAP_BOUND")
	}
	return parsePerfMappings(raw, expected)
}
