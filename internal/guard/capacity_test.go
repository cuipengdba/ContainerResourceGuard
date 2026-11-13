package guard

import (
	"errors"
	"os"
	"strings"
	"testing"
)

func TestMemTotalStrictUnitsDuplicatesAndOverflow(t *testing.T) {
	for _, raw := range []string{"", "MemTotal: 0 kB", "MemTotal: 32 MB", "MemTotal: -1 kB", "MemTotal: 18446744073709551615 kB", "MemTotal: 32 kB\nMemTotal: 64 kB"} {
		if _, err := parseMemTotal(raw); err == nil {
			t.Fatal(raw)
		}
	}
	if n, err := parseMemTotal("MemFree: 10 kB\nMemTotal: 65536 kB\n"); err != nil || n != 64<<20 {
		t.Fatal(n, err)
	}
}

func TestVirtualizedCapacitySkippedButManualAndIdentityRemainUsable(t *testing.T) {
	env := Environment{Target: "/self", Identity: "self"}
	read := func(path string) (string, error) {
		if strings.HasSuffix(path, "online") {
			return "0-23", nil
		}
		return "MemTotal: 1048576 kB", nil
	}
	verify := func(_ string, kind string) error {
		if kind == "memory" {
			return errors.New("fuse.lxcfs is not procfs")
		}
		return nil
	}
	discoverCapacity(&env, read, func(string) bool { return false }, verify)
	if env.MemoryBytes != 0 || env.OnlineCPUs != 24 || len(env.CapacityWarnings) != 1 || env.Identity != "self" {
		t.Fatal(env)
	}
	p, err := BuildPlan(Config{Percent: 20, IOProfile: "/missing"}, env, nil)
	if err != nil {
		t.Fatal(err)
	}
	for _, s := range p.Settings {
		if s.File == "memory.max" {
			t.Fatal("virtualized memory used as host total", s)
		}
	}
	cpu := 2.0
	p, err = BuildPlan(Config{ResourceMode: "manual", Limits: &ManualLimits{CPUCores: &cpu, MemoryMax: "512MiB"}}, env, nil)
	if err != nil || len(p.Settings) != 2 || p.Settings[1].Value != "536870912" {
		t.Fatal(p, err)
	}
}

func TestHostCapacityMountsSelectedAndUnverifiedOverrideNotSilentlyIgnored(t *testing.T) {
	env := Environment{}
	read := func(path string) (string, error) {
		if strings.HasSuffix(path, "online") {
			return "0-7", nil
		}
		return "MemTotal: 8388608 kB", nil
	}
	discoverCapacity(&env, read, func(string) bool { return true }, func(path, kind string) error {
		if !strings.HasPrefix(path, "/host/") {
			t.Fatal(path)
		}
		return nil
	})
	if env.OnlineCPUs != 8 || env.MemoryBytes != 8<<30 || len(env.CapacityWarnings) != 0 {
		t.Fatal(env)
	}
	discoverCapacity(&env, read, func(string) bool { return true }, func(string, string) error { return os.ErrPermission })
	if env.OnlineCPUs != 0 || env.MemoryBytes != 0 || len(env.CapacityWarnings) != 2 {
		t.Fatal(env)
	}
}
