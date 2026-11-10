package main

import (
	"bytes"
	"errors"
	"testing"

	"github.com/cuipengdba/ContainerResourceGuard/internal/guard"
	"github.com/cuipengdba/ContainerResourceGuard/internal/runlog"
)

func TestUnsupportedCgroupIsLoggedNoOp(t *testing.T) {
	for _, version := range []string{"v1", "hybrid", "unknown", "v2"} {
		t.Run(version, func(t *testing.T) {
			var console bytes.Buffer
			log := runlog.New(t.TempDir(), &console)
			calls := 0
			allowed, err := checkCgroupSupport(log, func() (guard.CgroupCheck, error) {
				calls++
				return guard.CgroupCheck{Version: version, Allowed: version == "v2", Action: "skip", Reason: "test version gate"}, nil
			})
			if err != nil || allowed != (version == "v2") || calls != 1 || !bytes.Contains(console.Bytes(), []byte("cgroup_detected")) || !bytes.Contains(console.Bytes(), []byte(version)) {
				t.Fatal(allowed, err, console.String())
			}
		})
	}
	var console bytes.Buffer
	log := runlog.New(t.TempDir(), &console)
	if ok, err := checkCgroupSupport(log, func() (guard.CgroupCheck, error) {
		return guard.CgroupCheck{Version: "unknown"}, errors.New("proc unavailable")
	}); ok || err == nil || !bytes.Contains(console.Bytes(), []byte("proc unavailable")) {
		t.Fatal(ok, err)
	}
}
