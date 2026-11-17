package guard

import (
	"errors"
	"fmt"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

const MetricsInterval = time.Minute
const MetricsMaxBytes = 64 << 10

type MetricsStatus struct {
	State  string `json:"state"`
	Detail string `json:"detail"`
}

type MetricsWriter struct {
	Save        func(string, []byte) error
	lastAttempt time.Time
	lastError   error
	enabled     bool
}

// Metrics are optional observability, never a prerequisite for reconciliation.
// Errors are sticky until the next bounded retry; no per-cycle error writes.
func (w *MetricsWriter) Write(c Config, e *Engine, status Status, now time.Time) *MetricsStatus {
	if !c.MetricsEnabled {
		w.enabled = false
		return nil
	}
	if !w.enabled || now.Sub(w.lastAttempt) >= MetricsInterval {
		w.enabled = true
		w.lastAttempt = now
		data, err := RenderMetrics(e, status, now)
		if err == nil {
			save := w.Save
			if save == nil {
				save = volatileFile
			}
			err = save(filepath.Join(c.StateDir, "metrics.prom"), data)
		}
		w.lastError = err
	}
	if w.lastError != nil {
		return &MetricsStatus{State: "unavailable", Detail: "local metrics export failed; retry at most once per minute; resource reconciliation continues"}
	}
	return &MetricsStatus{State: "ready", Detail: "local metrics.prom export at most once per minute; inspect sample timestamp for freshness"}
}

func RenderMetrics(e *Engine, status Status, now time.Time) ([]byte, error) {
	var b strings.Builder
	fmt.Fprintln(&b, "# ContainerResourceGuard local metrics; overlapping IO/stat counters must not be summed.")
	fmt.Fprintf(&b, "crg_metrics_sample_timestamp_seconds %d\n", now.Unix())
	fmt.Fprintf(&b, "crg_agent_state{state=%q} 1\n", diagnosticState(status.State))
	available := func(name string, ok bool) {
		n := 0
		if ok {
			n = 1
		}
		fmt.Fprintf(&b, "crg_collector_available{collector=%q} %d\n", name, n)
	}
	m := ReadMemorySnapshot(e.Env, e.Files)
	available("memory_current", m.CurrentBytes != nil)
	if m.CurrentBytes != nil {
		fmt.Fprintf(&b, "crg_memory_current_bytes %d\n", *m.CurrentBytes)
	}
	available("swap_current", m.SwapCurrentBytes != nil)
	if m.SwapCurrentBytes != nil {
		fmt.Fprintf(&b, "crg_swap_current_bytes %d\n", *m.SwapCurrentBytes)
	}
	keys := make([]string, 0, len(m.StatBytes))
	for k := range m.StatBytes {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		fmt.Fprintf(&b, "crg_memory_stat_bytes{kind=%q} %d\n", k, m.StatBytes[k])
	}
	keys = keys[:0]
	for k := range m.Events {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		fmt.Fprintf(&b, "crg_memory_events_total{event=%q} %d\n", k, m.Events[k])
	}
	available("memory_pressure", len(m.Pressure) > 0)
	for _, kind := range []string{"some", "full"} {
		if v, ok := m.Pressure[kind]; ok {
			fmt.Fprintf(&b, "crg_memory_pressure_percent{scope=%q,window=%q} %g\n", kind, "10", v.Avg10)
			fmt.Fprintf(&b, "crg_memory_pressure_percent{scope=%q,window=%q} %g\n", kind, "60", v.Avg60)
			fmt.Fprintf(&b, "crg_memory_pressure_percent{scope=%q,window=%q} %g\n", kind, "300", v.Avg300)
			fmt.Fprintf(&b, "crg_memory_pressure_seconds_total{scope=%q} %.6f\n", kind, float64(v.TotalMicros)/1e6)
		}
	}
	cpuFields := []string{"usage_usec", "user_usec", "system_usec", "nr_periods", "nr_throttled", "throttled_usec"}
	text, err := e.Files.Read(filepath.Join(e.Env.Target, "cpu.stat"))
	cpu := map[string]uint64{}
	if err == nil {
		cpu, err = parseSelectedCounts(text, cpuFields)
	}
	_, hasUsage := cpu["usage_usec"]
	available("cpu", err == nil && hasUsage)
	for _, pair := range [][2]string{{"usage_usec", "crg_cpu_usage_seconds_total"}, {"user_usec", "crg_cpu_user_seconds_total"}, {"system_usec", "crg_cpu_system_seconds_total"}, {"throttled_usec", "crg_cpu_throttled_seconds_total"}} {
		if n, ok := cpu[pair[0]]; ok {
			fmt.Fprintf(&b, "%s %.6f\n", pair[1], float64(n)/1e6)
		}
	}
	for _, pair := range [][2]string{{"nr_periods", "crg_cpu_periods_total"}, {"nr_throttled", "crg_cpu_throttled_periods_total"}} {
		if n, ok := cpu[pair[0]]; ok {
			fmt.Fprintf(&b, "%s %d\n", pair[1], n)
		}
	}
	text, err = e.Files.Read(filepath.Join(e.Env.Target, "pids.current"))
	pids, parseErr := strconv.ParseUint(strings.TrimSpace(text), 10, 64)
	available("pids", err == nil && parseErr == nil)
	if err == nil && parseErr == nil {
		fmt.Fprintf(&b, "crg_pids_current %d\n", pids)
	}
	text, err = e.Files.Read(filepath.Join(e.Env.Target, "io.stat"))
	ioOK := err == nil
	devices := map[string]bool{}
	omitted := 0
	for _, line := range strings.Split(text, "\n") {
		f := strings.Fields(line)
		if len(f) == 0 {
			continue
		}
		if !validDevice(f[0]) || devices[f[0]] {
			ioOK = false
			continue
		}
		devices[f[0]] = true
		if len(devices) > 32 {
			omitted++
			continue
		}
		values := map[string]uint64{}
		for _, kv := range f[1:] {
			parts := strings.SplitN(kv, "=", 2)
			if len(parts) != 2 {
				ioOK = false
				continue
			}
			if parts[0] != "rbytes" && parts[0] != "wbytes" && parts[0] != "rios" && parts[0] != "wios" {
				continue
			}
			if _, duplicate := values[parts[0]]; duplicate {
				ioOK = false
				continue
			}
			n, x := strconv.ParseUint(parts[1], 10, 64)
			if x != nil {
				ioOK = false
				continue
			}
			values[parts[0]] = n
		}
		for _, pair := range [][2]string{{"rbytes", "crg_io_read_bytes_total"}, {"wbytes", "crg_io_write_bytes_total"}, {"rios", "crg_io_read_operations_total"}, {"wios", "crg_io_write_operations_total"}} {
			if n, ok := values[pair[0]]; ok {
				fmt.Fprintf(&b, "%s{device=%q} %d\n", pair[1], f[0], n)
			}
		}
	}
	available("io", ioOK)
	fmt.Fprintf(&b, "crg_io_devices_omitted %d\n", omitted)
	if b.Len() > MetricsMaxBytes {
		return nil, errors.New("metrics exceed 64KiB limit")
	}
	return []byte(b.String()), nil
}
