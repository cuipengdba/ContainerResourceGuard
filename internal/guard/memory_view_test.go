package guard

import (
	"path/filepath"
	"strings"
	"testing"
)

func TestMemorySnapshotKeepsOverlapsAndUnavailableDistinctFromZero(t *testing.T) {
	e, f := fixture(t)
	f.data[filepath.Join(e.Env.Target, "memory.current")] = "0"
	f.data[filepath.Join(e.Env.Target, "memory.swap.current")] = "0"
	f.data[filepath.Join(e.Env.Target, "memory.stat")] = "file 200\nanon 100\nshmem 50\nslab 90\nfuture_count 12\n"
	f.data[filepath.Join(e.Env.Target, "memory.events")] = "oom 0\nhigh 4\noom_kill 0\n"
	r := ReadMemorySnapshot(e.Env, f)
	if r.CurrentBytes == nil || *r.CurrentBytes != 0 || r.SwapCurrentBytes == nil || *r.SwapCurrentBytes != 0 || len(f.writes) != 0 {
		t.Fatal(r, f.writes)
	}
	if r.StatBytes["file"] != 200 || r.StatBytes["shmem"] != 50 || len(r.StatBytes) != 4 || r.Events["high"] != 4 {
		t.Fatal(r)
	}
	if _, ok := r.StatBytes["kernel"]; ok || !strings.Contains(strings.Join(r.Unavailable, ","), "memory.stat.kernel") || !strings.Contains(strings.Join(r.Unavailable, ","), "memory.pressure") {
		t.Fatal("missing kernel/PSI presented as available", r)
	}
}

func TestMemorySnapshotRejectsMalformedSelectedCounters(t *testing.T) {
	for _, text := range []string{"anon 1\nanon 2", "file -1", "kernel 18446744073709551616", "anon 1 extra"} {
		if _, err := parseSelectedCounts(text, memoryByteFields); err == nil {
			t.Fatal(text)
		}
	}
	e, f := fixture(t)
	f.data[filepath.Join(e.Env.Target, "memory.current")] = "not-a-number"
	r := ReadMemorySnapshot(e.Env, f)
	if r.CurrentBytes != nil || len(r.StatBytes) != 0 || len(r.Events) != 0 {
		t.Fatal(r)
	}
}

func TestMemoryPressureKeysAndValidation(t *testing.T) {
	raw := "some total=10 avg60=2.5 avg300=0 avg10=1\nfull avg10=0 avg60=0 avg300=0 total=0\n"
	r, err := parseMemoryPressure(raw)
	if err != nil || r["some"].Avg60 != 2.5 || r["some"].TotalMicros != 10 || len(r) != 2 {
		t.Fatal(r, err)
	}
	for _, bad := range []string{"", "some avg10=NaN avg60=0 avg300=0 total=0", "some avg10=101 avg60=0 avg300=0 total=0", "some avg10=0 avg60=0 total=0", raw + raw, "some avg10=0 avg10=1 avg60=0 avg300=0 total=0", "some avg10=0 avg60=0 avg300=0 total=-1"} {
		if _, err := parseMemoryPressure(bad); err == nil {
			t.Fatal(bad)
		}
	}
}
