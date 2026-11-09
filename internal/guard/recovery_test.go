package guard

import (
	"encoding/json"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

func TestPersistenceFailureMatrix(t *testing.T) {
	for _, failAt := range []int{1, 2} {
		t.Run(string(rune('0'+failAt)), func(t *testing.T) {
			e, f := fixture(t)
			var disk []byte
			calls := 0
			e.Persist = func(j Journal) error {
				calls++
				if calls == failAt {
					return errors.New("read-only/full state filesystem")
				}
				disk, _ = json.Marshal(j)
				return nil
			}
			p := Plan{Settings: []Setting{{File: "cpu.max", Value: "200000 100000"}}}
			r := e.Apply(p)
			if r.State != "degraded" {
				t.Fatal(r)
			}
			if failAt == 1 && len(f.writes) != 0 {
				t.Fatal("write without durable intent")
			}
			if len(disk) > 0 {
				if err := Decode(disk, &e.Journal); err != nil {
					t.Fatal(err)
				}
			}
			e.Persist = func(j Journal) error { return nil }
			if r := e.Restore(); r.State != "restored" {
				t.Fatal(r)
			}
			if f.data[filepath.Join(e.Env.Target, "cpu.max")] != "max 100000" {
				t.Fatal("original lost")
			}
		})
	}
}

func TestConcurrentExternalChangeDuringIntent(t *testing.T) {
	for _, restore := range []bool{false, true} {
		e, f := fixture(t)
		s := Setting{File: "cpu.max", Value: "200000 100000"}
		if restore {
			e.Apply(Plan{Settings: []Setting{s}})
		}
		e.Persist = func(Journal) error { f.data[filepath.Join(e.Env.Target, "cpu.max")] = "150000 100000"; return nil }
		var r Status
		if restore {
			r = e.Restore()
		} else {
			r = e.Apply(Plan{Settings: []Setting{s}})
		}
		if r.State != "degraded" || f.data[filepath.Join(e.Env.Target, "cpu.max")] != "150000 100000" {
			t.Fatal(r)
		}
	}
}

func TestMemoryPreflightGrowthPressureAndSlowPersist(t *testing.T) {
	for _, scenario := range []string{"growth", "psi", "events", "slow-persist", "safe"} {
		t.Run(scenario, func(t *testing.T) {
			e, f := fixture(t)
			e.Pause = func(time.Duration) {
				switch scenario {
				case "growth":
					f.data[filepath.Join(e.Env.Target, "memory.current")] = "41943040"
				case "events":
					f.data[filepath.Join(e.Env.Target, "memory.events")] = "high 1\nmax 0\noom 0\noom_kill 0"
				}
			}
			if scenario == "psi" {
				f.data[filepath.Join(e.Env.Target, "memory.pressure")] = "some avg10=12.00 avg60=0.00 total=100"
			}
			if scenario == "slow-persist" {
				e.Persist = func(Journal) error { f.data[filepath.Join(e.Env.Target, "memory.current")] = "64000000"; return nil }
			}
			r := e.Apply(Plan{Settings: []Setting{{File: "memory.max", Value: "67108864"}}})
			if scenario == "safe" {
				if r.Items[0].State != "applied" {
					t.Fatal(r)
				}
			} else if r.Items[0].State != "skipped" || len(f.writes) != 0 {
				t.Fatal(r)
			}
		})
	}
}

func TestStatusWriterBudget(t *testing.T) {
	writes := 0
	w := StatusWriter{Save: func(string, any) error { writes++; return nil }}
	now := time.Now()
	s := Status{TimeUTC: now.Format(time.RFC3339), State: "managed"}
	for i := 0; i < 300; i++ {
		s.TimeUTC = now.Add(time.Duration(i) * time.Second).Format(time.RFC3339)
		if _, err := w.Write(s, now.Add(time.Duration(i)*time.Second)); err != nil {
			t.Fatal(err)
		}
	}
	if writes != 1 {
		t.Fatalf("unchanged status writes=%d", writes)
	}
	if _, err := w.Write(s, now.Add(300*time.Second)); err != nil {
		t.Fatal(err)
	}
	s.State = "degraded"
	w.Write(s, now.Add(301*time.Second))
	if writes != 3 {
		t.Fatal(writes)
	}
	w.Save = func(string, any) error { return os.ErrPermission }
	s.State = "managed"
	if _, err := w.Write(s, now.Add(302*time.Second)); err == nil {
		t.Fatal("ignored write failure")
	}
}

func TestDeviceStackGraph(t *testing.T) {
	edges := map[string][]string{"253:0": {"8:2"}, "253:1": {"8:2"}, "8:2": {"8:0"}}
	parents := func(dev string) ([]string, error) { return edges[dev], nil }
	if ok, err := reaches("253:0", "8:0", parents); !ok || err != nil {
		t.Fatal(ok, err)
	}
	if ok, err := reaches("253:0", "253:1", parents); ok || err != nil {
		t.Fatal("siblings must not be treated as one layer", ok, err)
	}
	edges["8:0"] = []string{"253:0"}
	if ok, err := reaches("253:0", "9:0", parents); ok || err != nil {
		t.Fatal("cycle not bounded", ok, err)
	}
}

func TestProfileRemapsIdentityAndRejectsReplacedOrAmbiguous(t *testing.T) {
	id := strings.Repeat("a", 64)
	d := DeviceProfile{Device: "253:0", Identity: id}
	identities := map[string]string{"253:0": strings.Repeat("b", 64), "253:4": id}
	identity := func(dev string) (string, error) {
		if v, ok := identities[dev]; ok {
			return v, nil
		}
		return "", os.ErrNotExist
	}
	devices := func() ([]string, error) {
		var r []string
		for dev := range identities {
			r = append(r, dev)
		}
		return r, nil
	}
	if dev, err := resolveDevice(d, identity, devices); err != nil || dev != "253:4" {
		t.Fatal(dev, err)
	}
	delete(identities, "253:4")
	if _, err := resolveDevice(d, identity, devices); err == nil {
		t.Fatal("replacement reused old identity")
	}
	identities["253:4"], identities["253:5"] = id, id
	if _, err := resolveDevice(d, identity, devices); err == nil {
		t.Fatal("ambiguous identity accepted")
	}
}

func TestDecodeRejectsCorruptObjects(t *testing.T) {
	for _, raw := range []string{`null`, `[]`, `{"percent":20,"percent":30}`, `{"outer":{"x":1,"x":2}}`} {
		var out map[string]any
		if Decode([]byte(raw), &out) == nil {
			t.Fatal(raw)
		}
	}
	for _, v := range []string{"", "max\n0", "bad", "0"} {
		if validControl(Setting{File: "memory.max"}, v) {
			t.Fatal(v)
		}
	}
}

// The child really dies mid-operation. Regular temporary files model durable
// kernel values; actual cgroup enforcement is covered by isolated node tests.
func TestKilledProcessRecovery(t *testing.T) {
	if runtime.GOOS != "linux" {
		t.Skip("Linux directory fsync and SIGKILL durability test")
	}
	if os.Getenv("CRG_RECOVERY_CHILD") != "" {
		t.Skip("parent only")
	}
	stages := []string{"intent-before", "intent-after", "write-before", "write-after", "readback-before", "readback-after", "finalize-before", "finalize-after"}
	for _, operation := range []string{"apply", "restore"} {
		for _, stage := range stages {
			t.Run(operation+"-"+stage, func(t *testing.T) {
				root := t.TempDir()
				target := filepath.Join(root, "self")
				os.Mkdir(target, 0700)
				os.WriteFile(filepath.Join(target, "cpu.max"), []byte("max 100000"), 0600)
				e := diskEngine(t, root)
				if operation == "restore" {
					e.Apply(Plan{Settings: []Setting{{File: "cpu.max", Value: "200000 100000"}}})
				}
				cmd := exec.Command(os.Args[0], "-test.run=^TestRecoveryChild$")
				cmd.Env = append(os.Environ(), "CRG_RECOVERY_CHILD="+root, "CRG_RECOVERY_STAGE="+stage, "CRG_RECOVERY_OPERATION="+operation)
				out, err := cmd.CombinedOutput()
				if err == nil || strings.Contains(string(out), "FAIL") {
					t.Fatalf("child not killed as expected: %v %s", err, out)
				}
				e = diskEngine(t, root)
				if r := e.Restore(); r.State != "restored" {
					t.Fatal(r)
				}
				actual, _ := read(filepath.Join(target, "cpu.max"))
				if actual != "max 100000" {
					t.Fatalf("original lost: %s", actual)
				}
			})
		}
	}
}

type diskFiles struct {
	wrote bool
	hook  func(string)
}

func (f *diskFiles) Read(p string) (string, error) {
	if f.wrote {
		f.hook("readback-before")
	}
	v, e := read(p)
	if f.wrote {
		f.hook("readback-after")
	}
	return v, e
}
func (f *diskFiles) Write(p, v string) error {
	f.hook("write-before")
	e := os.WriteFile(p, []byte(v), 0600)
	f.wrote = true
	f.hook("write-after")
	return e
}
func diskEngine(t *testing.T, root string) *Engine {
	t.Helper()
	j := Journal{Version: 1, Identity: "test", Target: filepath.Join(root, "self"), Mutations: map[string]*Mutation{}}
	if b, e := os.ReadFile(filepath.Join(root, "journal.json")); e == nil {
		if e := Decode(b, &j); e != nil {
			t.Fatal(e)
		}
	}
	return &Engine{Config: Config{Mode: "enforce"}, Env: Environment{Target: j.Target, Identity: j.Identity}, Journal: j, Files: &diskFiles{hook: func(string) {}}, Persist: func(j Journal) error { return AtomicJSON(filepath.Join(root, "journal.json"), j) }}
}
func TestRecoveryChild(t *testing.T) {
	root := os.Getenv("CRG_RECOVERY_CHILD")
	if root == "" {
		t.Skip("child only")
	}
	stage := os.Getenv("CRG_RECOVERY_STAGE")
	hook := func(s string) {
		if s == stage {
			p, _ := os.FindProcess(os.Getpid())
			p.Kill()
			time.Sleep(time.Second)
			os.Exit(93)
		}
	}
	e := diskEngine(t, root)
	e.Files = &diskFiles{hook: hook}
	calls := 0
	e.Persist = func(j Journal) error {
		calls++
		label := "intent"
		if calls > 1 {
			label = "finalize"
		}
		hook(label + "-before")
		err := AtomicJSON(filepath.Join(root, "journal.json"), j)
		hook(label + "-after")
		return err
	}
	if os.Getenv("CRG_RECOVERY_OPERATION") == "restore" {
		e.Restore()
	} else {
		e.Apply(Plan{Settings: []Setting{{File: "cpu.max", Value: "200000 100000"}}})
	}
	t.Fatal("kill checkpoint not reached")
}
