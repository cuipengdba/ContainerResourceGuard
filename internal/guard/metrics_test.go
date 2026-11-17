package guard

import (
	"errors"
	"fmt"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestMetricsDefaultOffFailureBoundedAndRecovery(t *testing.T) {
	e, f := fixture(t)
	c := Config{StateDir: t.TempDir()}
	attempts := 0
	fail := true
	w := MetricsWriter{Save: func(path string, b []byte) error {
		attempts++
		if path != filepath.Join(c.StateDir, "metrics.prom") || len(b) > MetricsMaxBytes {
			t.Fatal(path, len(b))
		}
		if fail {
			return errors.New("full filesystem")
		}
		return nil
	}}
	now := time.Now()
	if w.Write(c, e, Status{State: "managed"}, now) != nil || attempts != 0 {
		t.Fatal("metrics enabled by default")
	}
	c.MetricsEnabled = true
	if r := w.Write(c, e, Status{State: "managed"}, now); r.State != "unavailable" {
		t.Fatal(r)
	}
	for i := 1; i < 60; i++ {
		if r := w.Write(c, e, Status{State: "managed"}, now.Add(time.Duration(i)*time.Second)); r.State != "unavailable" {
			t.Fatal(r)
		}
	}
	if attempts != 1 || len(f.writes) != 0 {
		t.Fatal("repeated writes or controller side effects", attempts, f.writes)
	}
	fail = false
	if r := w.Write(c, e, Status{State: "managed"}, now.Add(time.Minute)); r.State != "ready" || attempts != 2 {
		t.Fatal(r, attempts)
	}
	// The optional collector error has no bearing on subsequent CPU control.
	if r := e.Apply(Plan{Settings: []Setting{{File: "cpu.max", Value: "50000 100000"}}}); r.State != "managed" {
		t.Fatal(r)
	}
	c.MetricsEnabled = false
	if r := w.Write(c, e, Status{}, now.Add(61*time.Second)); r != nil || attempts != 2 {
		t.Fatal(r, attempts)
	}
}

func TestMetricsRenderCountersUnitsUnknownsAndDeviceBound(t *testing.T) {
	e, f := fixture(t)
	f.data[filepath.Join(e.Env.Target, "cpu.stat")] = "usage_usec 2000000\nuser_usec 1500000\nsystem_usec 500000\nnr_periods 10\nnr_throttled 2\nthrottled_usec 125000"
	f.data[filepath.Join(e.Env.Target, "pids.current")] = "7"
	f.data[filepath.Join(e.Env.Target, "memory.stat")] = "anon 100\nfile 200\nshmem 50"
	var io strings.Builder
	for i := 0; i < 40; i++ {
		fmt.Fprintf(&io, "253:%d rbytes=123 wbytes=456 rios=1 wios=2\n", i)
	}
	f.data[filepath.Join(e.Env.Target, "io.stat")] = io.String()
	b, err := RenderMetrics(e, Status{State: "managed"}, time.Unix(123, 0))
	s := string(b)
	for _, want := range []string{"crg_metrics_sample_timestamp_seconds 123", "crg_cpu_usage_seconds_total 2.000000", "crg_cpu_throttled_seconds_total 0.125000", "crg_pids_current 7", `crg_collector_available{collector="memory_pressure"} 0`, `crg_io_read_bytes_total{device="253:0"} 123`, "crg_io_devices_omitted 8"} {
		if !strings.Contains(s, want) {
			t.Fatal(want, s)
		}
	}
	if err != nil || len(b) > MetricsMaxBytes || strings.Contains(s, e.Env.Target) || strings.Contains(s, `device="253:32"`) || strings.Contains(s, "crg_memory_pressure_seconds_total") {
		t.Fatal(string(b), err)
	}
	if len(f.writes) != 0 {
		t.Fatal("metrics changed controllers", f.writes)
	}
}

func TestMetricsFailureStateDoesNotForceEveryCycleStatusWrites(t *testing.T) {
	e, _ := fixture(t)
	c := Config{MetricsEnabled: true, StateDir: t.TempDir()}
	now := time.Now()
	writes := 0
	m := MetricsWriter{Save: func(string, []byte) error { return errors.New("denied") }}
	w := StatusWriter{Save: func(string, any) error { writes++; return nil }}
	for i := 0; i < 120; i++ {
		at := now.Add(time.Duration(i) * time.Second)
		s := Status{State: "managed", TimeUTC: at.Format(time.RFC3339)}
		s.Metrics = m.Write(c, e, s, at)
		if _, err := w.Write(s, at); err != nil {
			t.Fatal(err)
		}
	}
	if writes != 1 {
		t.Fatal("metrics error churned persisted status", writes)
	}
}
