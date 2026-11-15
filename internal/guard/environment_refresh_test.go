package guard

import (
	"errors"
	"os"
	"reflect"
	"testing"
)

func TestRefreshEnvironmentUsesCurrentCapacityWithoutChangingOwnership(t *testing.T) {
	previous := Environment{CgroupVersion: "v2", Target: t.TempDir(), Identity: "same-container", OnlineCPUs: 8, MemoryBytes: 8 << 30, EffectiveCPUs: "0-7", CapacityWarnings: []string{"old"}}
	current := Environment{CgroupVersion: "v2", Target: previous.Target, Identity: previous.Identity, OnlineCPUs: 3, MemoryBytes: 4 << 30, EffectiveCPUs: "0-2", CPUCapacitySource: "/host/sys/devices/system/cpu/online", MemoryCapacitySource: "/host/proc/meminfo", CapacityWarnings: []string{"current"}}
	calls := 0
	actual, err := refreshEnvironment(previous, func() (Environment, error) { calls++; return current, nil })
	if err != nil || calls != 1 || !reflect.DeepEqual(actual, current) || previous.OnlineCPUs != 8 {
		t.Fatalf("stale or mixed environment: %#v %v", actual, err)
	}
}

func TestRefreshEnvironmentRejectsDiscoveryAndIdentityFailures(t *testing.T) {
	previous := Environment{Target: t.TempDir(), Identity: "same-container", OnlineCPUs: 8}
	if actual, err := refreshEnvironment(previous, func() (Environment, error) { return previous, os.ErrPermission }); !errors.Is(err, os.ErrPermission) || !reflect.DeepEqual(actual, Environment{}) {
		t.Fatalf("discovery failure reused stale values: %#v %v", actual, err)
	}
	for _, change := range []func(*Environment){func(e *Environment) { e.Identity = "replacement" }, func(e *Environment) { e.Target += "-replacement" }} {
		current := previous
		change(&current)
		if actual, err := refreshEnvironment(previous, func() (Environment, error) { return current, nil }); err == nil || !reflect.DeepEqual(actual, Environment{}) {
			t.Fatalf("different identity accepted: %#v %v", actual, err)
		}
	}
}

func TestRefreshEnvironmentDoesNotKeepPreviouslyTrustedCapacityOnSourceFailure(t *testing.T) {
	previous := Environment{CgroupVersion: "v2", Target: t.TempDir(), Identity: "same-container", OnlineCPUs: 8, MemoryBytes: 8 << 30}
	current := Environment{CgroupVersion: "v2", Target: previous.Target, Identity: previous.Identity, CapacityWarnings: []string{"CPU and memory sources are no longer verified"}}
	actual, err := refreshEnvironment(previous, func() (Environment, error) { return current, nil })
	if err != nil || actual.OnlineCPUs != 0 || actual.MemoryBytes != 0 {
		t.Fatalf("previously trusted capacity retained: %#v %v", actual, err)
	}
	plan, err := BuildPlan(Config{Percent: 20, IOProfile: "/missing"}, actual, nil)
	if err != nil {
		t.Fatal(err)
	}
	for _, setting := range plan.Settings {
		if setting.File == "cpu.max" || setting.File == "memory.high" || setting.File == "memory.max" {
			t.Fatalf("unverified basis used: %#v", setting)
		}
	}
}
