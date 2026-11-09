package guard

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestConfigValidation(t *testing.T) {
	for _, raw := range []string{`{}`, `{"percent":0}`, `{"percent":101}`, `{"percent":-1}`, `{"percent":20,"cpu":2}`, `{"percent":20} {}`, `{"percent":20,"mode":"wrong"}`, `{"percent":20,"interval_seconds":-1}`} {
		var c Config
		e := Decode([]byte(raw), &c)
		if e == nil {
			e = c.Validate()
		}
		if e == nil {
			t.Fatalf("accepted invalid config %s", raw)
		}
	}
	var c Config
	if e := Decode([]byte(`{"percent":20}`), &c); e != nil {
		t.Fatal(e)
	}
	if e := c.Validate(); e != nil {
		t.Fatal(e)
	}
	if c.Percent != 20 || c.Mode != "enforce" {
		t.Fatal(c)
	}
}
func TestCountCPUs(t *testing.T) {
	for s, want := range map[string]int{"0-23": 24, "0-3,8-11": 8, "0-2,2": 3} {
		got, e := CountCPUs(s)
		if e != nil || got != want {
			t.Fatalf("%s %d %v", s, got, e)
		}
	}
	for _, s := range []string{"", "0foo", "3-1", "-1", "0-2-3", "0,"} {
		if _, e := CountCPUs(s); e == nil {
			t.Fatalf("accepted %q", s)
		}
	}
}
func TestResolveNamespaces(t *testing.T) {
	for _, x := range []struct{ cg, root, mp, want string }{
		{"/kubepods/pod/container", "/", "/sys/fs/cgroup", "/sys/fs/cgroup/kubepods/pod/container"},
		{"/", "/", "/sys/fs/cgroup", "/sys/fs/cgroup"},
		{"/pod/container", "/pod", "/cg", "/cg/container"},
		{"/a/container", "/a", "/space\\040cg", "/space cg/container"},
	} {
		cg := "0::" + x.cg
		mi := "1 2 0:25 " + x.root + " " + x.mp + " rw - cgroup2 cgroup rw"
		got, e := Resolve(cg, mi, cg)
		if e != nil || got != x.want {
			t.Fatalf("%+v got %s %v", x, got, e)
		}
	}
	if _, e := Resolve("0::/a", "1 2 0:25 / /cg rw - cgroup2 cgroup rw", "0::/b"); e == nil {
		t.Fatal("accepted foreign PID 1")
	}
	if _, e := Resolve("0::/../a", "1 2 0:25 / /cg rw - cgroup2 cgroup rw", "0::/../a"); e == nil {
		t.Fatal("accepted traversal")
	}
	if _, e := Resolve("2:cpu:/a", "", "2:cpu:/a"); e == nil {
		t.Fatal("accepted v1")
	}
}

type fakeFiles struct {
	data   map[string]string
	fail   error
	writes []string
}

func (f *fakeFiles) Read(p string) (string, error) {
	v, ok := f.data[p]
	if !ok {
		return "", os.ErrNotExist
	}
	return v, nil
}
func (f *fakeFiles) Write(p, v string) error {
	if f.fail != nil {
		return f.fail
	}
	f.writes = append(f.writes, p)
	if filepath.Base(p) == "io.max" {
		s := strings.Fields(v)
		f.data[p] = s[0] + " " + canonicalIO(strings.Join(s[1:], " "))
	} else {
		f.data[p] = v
	}
	return nil
}
func fixture(t *testing.T) (*Engine, *fakeFiles) {
	t.Helper()
	target := filepath.Join(t.TempDir(), "self")
	f := &fakeFiles{data: map[string]string{filepath.Join(target, "cpu.max"): "max 100000", filepath.Join(target, "memory.max"): "max", filepath.Join(target, "memory.current"): "1048576", filepath.Join(target, "io.max"): ""}}
	e := &Engine{Config: Config{Mode: "enforce"}, Env: Environment{Target: target, Identity: "self"}, Files: f, Journal: Journal{Version: 1, Identity: "self", Target: target, Mutations: map[string]*Mutation{}}, Persist: func(Journal) error { return nil }}
	return e, f
}
func TestApplyConflictRestore(t *testing.T) {
	e, f := fixture(t)
	s := Setting{File: "cpu.max", Value: "200000 100000"}
	p := Plan{Settings: []Setting{s}}
	if r := e.Apply(p); r.Items[0].State != "applied" {
		t.Fatal(r)
	}
	if len(f.writes) != 1 {
		t.Fatal(f.writes)
	}
	e.Apply(p)
	if len(f.writes) != 1 {
		t.Fatal("non-idempotent")
	}
	f.data[filepath.Join(e.Env.Target, "cpu.max")] = "100000 100000"
	if r := e.Apply(p); r.Items[0].State != "conflict" {
		t.Fatal(r)
	}
	if r := e.Restore(); r.State != "degraded" {
		t.Fatal("overwrote external setting", r)
	}
	if f.data[filepath.Join(e.Env.Target, "cpu.max")] != "100000 100000" {
		t.Fatal("external value changed")
	}
}
func TestRestoreAndPartialFailure(t *testing.T) {
	e, f := fixture(t)
	p := Plan{Settings: []Setting{{File: "cpu.max", Value: "100000 100000"}, {File: "memory.max", Value: "67108864"}, {File: "io.max", Device: "253:0", Value: "rbps=1000 wbps=2000 riops=10 wiops=20"}}}
	r := e.Apply(p)
	if r.State != "managed" {
		t.Fatal(r)
	}
	if r = e.Restore(); r.State != "restored" {
		t.Fatal(r)
	}
	if f.data[filepath.Join(e.Env.Target, "cpu.max")] != "max 100000" || f.data[filepath.Join(e.Env.Target, "memory.max")] != "max" {
		t.Fatal(f.data)
	}
	if len(e.Journal.Mutations) != 0 {
		t.Fatal(e.Journal)
	}
	f.fail = os.ErrPermission
	r = e.Apply(p)
	if r.State != "degraded" || r.Items[0].State != "skipped" {
		t.Fatal(r)
	}
}
func TestJournalFailurePreventsWrite(t *testing.T) {
	e, f := fixture(t)
	e.Persist = func(Journal) error { return errors.New("disk full") }
	r := e.Apply(Plan{Settings: []Setting{{File: "cpu.max", Value: "100000 100000"}}})
	if len(f.writes) != 0 || r.Items[0].State != "skipped" {
		t.Fatal(r)
	}
}
func TestMemoryBusyAndObserve(t *testing.T) {
	e, f := fixture(t)
	f.data[filepath.Join(e.Env.Target, "memory.current")] = "100000000"
	p := Plan{Settings: []Setting{{File: "memory.max", Value: "50000000"}}}
	if r := e.Apply(p); r.Items[0].State != "skipped" {
		t.Fatal(r)
	}
	if len(f.writes) != 0 {
		t.Fatal("unsafe memory decrease")
	}
	e.Config.Mode = "observe"
	if r := e.Apply(p); r.State != "observe" || len(f.writes) != 0 {
		t.Fatal(r)
	}
}
func TestPendingCrashRecovery(t *testing.T) {
	e, f := fixture(t)
	s := Setting{File: "cpu.max", Value: "100000 100000"}
	e.Journal.Mutations[s.Key()] = &Mutation{Setting: s, Original: "max 100000", Applied: "max 100000", Pending: s.Value}
	f.data[filepath.Join(e.Env.Target, s.File)] = s.Value
	if r := e.Apply(Plan{Settings: []Setting{s}}); r.Items[0].State != "applied" {
		t.Fatal(r)
	}
	if r := e.Restore(); r.State != "restored" {
		t.Fatal(r)
	}
}
func TestJournalCannotEscapeSelf(t *testing.T) {
	e, f := fixture(t)
	r := e.Apply(Plan{Settings: []Setting{{File: "../foreign/cpu.max", Value: "1000"}}})
	if r.Items[0].State != "skipped" || len(f.writes) != 0 {
		t.Fatal(r)
	}
}
func TestPlanPercentAndExistingLimits(t *testing.T) {
	dir := t.TempDir()
	for k, v := range map[string]string{"cpu.max": "max 100000", "memory.max": "max"} {
		if e := os.WriteFile(filepath.Join(dir, k), []byte(v), 0600); e != nil {
			t.Fatal(e)
		}
	}
	c := Config{Percent: 20, IOProfile: filepath.Join(dir, "absent.json")}
	env := Environment{Target: dir, OnlineCPUs: 24, MemoryBytes: 64 << 30}
	p, e := BuildPlan(c, env, nil)
	if e != nil {
		t.Fatal(e)
	}
	if p.Settings[0].Value != "480000 100000" {
		t.Fatal(p)
	}
	if maxNumber(p.Settings[1].Value) != uint64(float64(env.MemoryBytes)*.2)/uint64(os.Getpagesize())*uint64(os.Getpagesize()) {
		t.Fatal(p)
	}
	os.WriteFile(filepath.Join(dir, "cpu.max"), []byte("100000 100000"), 0600)
	p, e = BuildPlan(c, env, nil)
	if e != nil || p.Settings[0].Value != "100000 100000" {
		t.Fatal(p, e)
	}
	p, e = BuildPlan(c, env, map[string]string{"cpu.max:": "max 100000"})
	if e != nil || p.Settings[0].Value != "480000 100000" {
		t.Fatal("own previous limit clamped new percent", p, e)
	}
}
func TestIOPreservesStricterAndDeviceIsolation(t *testing.T) {
	if got := clampIO("rbps=1000 wbps=2000 riops=10 wiops=20", "rbps=500 wbps=max riops=4 wiops=max"); got != "rbps=500 wbps=2000 riops=4 wiops=20" {
		t.Fatal(got)
	}
	if got := ioValue("8:0 rbps=4 wbps=5 riops=6 wiops=7", "253:0"); got != "rbps=max wbps=max riops=max wiops=max" {
		t.Fatal(got)
	}
}
