package guard

import (
	"errors"
	"math"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// These are overlapping kernel counters, not parts that can be summed into a
// second "total". For example shmem is included in file, and slab in kernel.
var memoryByteFields = []string{"anon", "file", "kernel", "kernel_stack", "pagetables", "sec_pagetables", "percpu", "sock", "vmalloc", "shmem", "file_mapped", "file_dirty", "file_writeback", "anon_thp", "file_thp", "shmem_thp", "inactive_anon", "active_anon", "inactive_file", "active_file", "slab_reclaimable", "slab_unreclaimable", "slab", "hugetlb"}
var memoryEventFields = []string{"low", "high", "max", "oom", "oom_kill", "oom_group_kill", "sock_throttled"}

type PressureSample struct {
	Avg10       float64 `json:"avg10_percent"`
	Avg60       float64 `json:"avg60_percent"`
	Avg300      float64 `json:"avg300_percent"`
	TotalMicros uint64  `json:"total_microseconds"`
}

type MemorySnapshot struct {
	SampledUTC       string                    `json:"sampled_utc"`
	CurrentBytes     *uint64                   `json:"current_bytes"`
	SwapCurrentBytes *uint64                   `json:"swap_current_bytes"`
	StatBytes        map[string]uint64         `json:"stat_bytes"`
	Events           map[string]uint64         `json:"events"`
	Pressure         map[string]PressureSample `json:"pressure"`
	Unavailable      []string                  `json:"unavailable,omitempty"`
}

func parseSelectedCounts(text string, fields []string) (map[string]uint64, error) {
	wanted := map[string]bool{}
	for _, name := range fields {
		wanted[name] = true
	}
	result := map[string]uint64{}
	for _, line := range strings.Split(text, "\n") {
		f := strings.Fields(line)
		if len(f) == 0 || !wanted[f[0]] {
			continue
		}
		if _, duplicate := result[f[0]]; duplicate || len(f) != 2 {
			return nil, errors.New("invalid or duplicate selected counter")
		}
		n, err := strconv.ParseUint(f[1], 10, 64)
		if err != nil {
			return nil, errors.New("invalid selected counter")
		}
		result[f[0]] = n
	}
	return result, nil
}

func parseMemoryPressure(text string) (map[string]PressureSample, error) {
	result := map[string]PressureSample{}
	for _, line := range strings.Split(text, "\n") {
		f := strings.Fields(line)
		if len(f) == 0 || f[0] != "some" && f[0] != "full" {
			continue
		}
		if _, duplicate := result[f[0]]; duplicate {
			return nil, errors.New("duplicate memory pressure row")
		}
		values := map[string]string{}
		for _, field := range f[1:] {
			kv := strings.SplitN(field, "=", 2)
			if len(kv) != 2 || values[kv[0]] != "" {
				return nil, errors.New("invalid memory pressure field")
			}
			values[kv[0]] = kv[1]
		}
		var v PressureSample
		for name, dest := range map[string]*float64{"avg10": &v.Avg10, "avg60": &v.Avg60, "avg300": &v.Avg300} {
			n, err := strconv.ParseFloat(values[name], 64)
			if err != nil || math.IsNaN(n) || math.IsInf(n, 0) || n < 0 || n > 100 {
				return nil, errors.New("invalid memory pressure average")
			}
			*dest = n
		}
		var err error
		v.TotalMicros, err = strconv.ParseUint(values["total"], 10, 64)
		if err != nil {
			return nil, errors.New("invalid memory pressure total")
		}
		result[f[0]] = v
	}
	if len(result) == 0 {
		return nil, errors.New("no memory pressure samples")
	}
	return result, nil
}

// ReadMemorySnapshot is on-demand and read-only. It is deliberately outside the
// persisted loop status so volatile counters do not turn a quiet agent into a
// per-interval disk writer. Missing values remain unavailable, never fake zero.
func ReadMemorySnapshot(env Environment, files Files) MemorySnapshot {
	r := MemorySnapshot{SampledUTC: time.Now().UTC().Format(time.RFC3339), StatBytes: map[string]uint64{}, Events: map[string]uint64{}, Pressure: map[string]PressureSample{}}
	for name, dest := range map[string]**uint64{"memory.current": &r.CurrentBytes, "memory.swap.current": &r.SwapCurrentBytes} {
		text, err := files.Read(filepath.Join(env.Target, name))
		if err == nil {
			var n uint64
			n, err = strconv.ParseUint(strings.TrimSpace(text), 10, 64)
			if err == nil {
				*dest = &n
			}
		}
		if err != nil {
			r.Unavailable = append(r.Unavailable, name)
		}
	}
	for _, name := range []string{"memory.stat", "memory.events"} {
		fields, dest := memoryByteFields, &r.StatBytes
		if name == "memory.events" {
			fields, dest = memoryEventFields, &r.Events
		}
		text, err := files.Read(filepath.Join(env.Target, name))
		if err == nil {
			var counts map[string]uint64
			counts, err = parseSelectedCounts(text, fields)
			if err == nil && len(counts) > 0 {
				*dest = counts
			} else {
				err = errors.New("counters unavailable")
			}
		}
		if err != nil {
			r.Unavailable = append(r.Unavailable, name)
		}
	}
	for _, name := range []string{"anon", "file", "kernel", "hugetlb"} {
		if _, ok := r.StatBytes[name]; !ok {
			r.Unavailable = append(r.Unavailable, "memory.stat."+name)
		}
	}
	text, err := files.Read(filepath.Join(env.Target, "memory.pressure"))
	if err == nil {
		r.Pressure, err = parseMemoryPressure(text)
	}
	if err != nil {
		r.Pressure = map[string]PressureSample{}
		r.Unavailable = append(r.Unavailable, "memory.pressure")
	}
	return r
}
