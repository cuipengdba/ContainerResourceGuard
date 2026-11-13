package guard

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type weightFiles struct{ *fakeFiles }

func (f weightFiles) Write(path, value string) error {
	if filepath.Base(path) != "io.weight" {
		return f.fakeFiles.Write(path, value)
	}
	if f.fail != nil {
		return f.fail
	}
	lines := []string{value}
	for _, line := range strings.Split(f.data[path], "\n") {
		if fields := strings.Fields(line); len(fields) > 0 && fields[0] != "default" {
			lines = append(lines, line)
		}
	}
	f.data[path] = strings.Join(lines, "\n")
	f.writes = append(f.writes, path)
	return nil
}

func TestIOWeightDefaultOwnershipAndOverridePreservation(t *testing.T) {
	e, f := fixture(t)
	e.Files = weightFiles{f}
	path := filepath.Join(e.Env.Target, "io.weight")
	f.data[path] = "default 100\n253:0 50"
	v := uint64(200)
	e.Config.IOWeight = &v
	p := Plan{Settings: []Setting{{File: "io.weight", Value: "default 200"}}}
	if s := e.Reconcile(p); s.State != "managed" || f.data[path] != "default 200\n253:0 50" {
		t.Fatal(s, f.data[path])
	}
	// An independent per-device override is outside the default entry we own.
	f.data[path] = "default 200\n253:0 400"
	e.Config.IOWeight = nil
	if s := e.Reconcile(Plan{}); s.State != "managed" || f.data[path] != "default 100\n253:0 400" {
		t.Fatal(s, f.data[path])
	}
	e.Config.IOWeight = &v
	e.Reconcile(p)
	f.data[path] = "default 300\n253:0 400"
	if s := e.Reconcile(p); s.State != "degraded" || s.Items[0].State != "conflict" {
		t.Fatal(s)
	}
	if s := e.Restore(); s.State != "degraded" || f.data[path] != "default 300\n253:0 400" {
		t.Fatal(s)
	}
}

func TestIOWeightValidationMissingControllerAndBoundedProfile(t *testing.T) {
	for _, n := range []uint64{0, 10001} {
		c := Config{Percent: 20, IOWeight: &n}
		if c.Validate() == nil {
			t.Fatal(n)
		}
	}
	for _, raw := range []string{"100", "default 0", "default 10001", "default 100\ndefault 200", "default 100 trailing"} {
		if _, err := defaultIOWeight(raw); err == nil {
			t.Fatal(raw)
		}
	}
	e, _ := fixture(t)
	if s := e.Apply(Plan{Settings: []Setting{{File: "io.weight", Value: "default 200"}}}); s.State != "degraded" || s.Items[0].State != "skipped" || len(e.Journal.Mutations) != 0 {
		t.Fatal(s)
	}
	file := filepath.Join(t.TempDir(), "large.json")
	os.WriteFile(file, []byte(strings.Repeat("x", MaxJSONBytes+1)), 0600)
	p, err := BuildPlan(Config{Percent: 20, IOProfile: file}, Environment{}, nil)
	if err != nil || !strings.Contains(strings.Join(p.Warnings, ";"), "exceeds 1MiB") {
		t.Fatal(p, err)
	}
}
