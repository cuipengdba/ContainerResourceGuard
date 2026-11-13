//go:build linux && amd64

package main

import "testing"

func TestPerfBudgetRejectsOverBudgetBeforeAllocation(t *testing.T) {
	p, e := perfBudget(4096, 24)
	if e != nil || p.DataBytes != 131072 || p.MaximumMapped != 3244032 || p.Cap != 16777216 {
		t.Fatal(p, e)
	}
	for _, v := range []struct {
		page int
		cpus uint32
	}{{0, 24}, {5000, 24}, {4096, 0}, {4096, 125}, {65536, 24}, {4096, ^uint32(0)}} {
		if _, e := perfBudget(v.page, v.cpus); e == nil {
			t.Fatal("invalid or oversized perf mmap budget accepted", v)
		}
	}
	if p, e := perfBudget(4096, 124); e != nil || p.MaximumMapped > p.Cap {
		t.Fatal(p, e)
	}
}

func TestPerfMappingMeasurementNeverExportsAddresses(t *testing.T) {
	raw := []byte("1000-22000 rw-s 0000 00:0e 1 /anon_inode:[perf_event]\n30000-51000 rw-s 0000 00:0e 2 anon_inode:[perf_event]\n60000-61000 r--p 0000 00:00 0 /unrelated\n")
	n, total, e := parsePerfMappings(raw, 135168)
	if e != nil || n != 2 || total != 270336 {
		t.Fatal(n, total, e)
	}
	for _, bad := range []string{"1000-22001 rw-s 0 0 1 /anon_inode:[perf_event]", "bad-22000 rw-s 0 0 1 /anon_inode:[perf_event]", "22000-1000 rw-s 0 0 1 /anon_inode:[perf_event]"} {
		if _, _, e := parsePerfMappings([]byte(bad), 135168); e == nil {
			t.Fatal("bad mapping accepted")
		}
	}
}
