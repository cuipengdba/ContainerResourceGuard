//go:build linux

package guard

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestDiagnosticLinuxAliasesAndPrivateNewFile(t *testing.T) {
	root := t.TempDir()
	actual, alias := filepath.Join(root, "actual"), filepath.Join(root, "alias")
	if err := os.Mkdir(actual, 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(actual, alias); err != nil {
		t.Fatal(err)
	}
	c := Config{StateDir: alias, IOProfile: filepath.Join(actual, "profile.json")}
	if err := WriteDiagnosticFile(filepath.Join(actual, "journal.json"), c, DiagnosticBundle{}); err == nil {
		t.Fatal("state alias bypass")
	}
	path := filepath.Join(root, "diagnostic.json")
	if err := WriteDiagnosticFile(path, c, DiagnosticBundle{Schema: "crg-diagnostics-v1"}); err != nil {
		t.Fatal(err)
	}
	st, err := os.Stat(path)
	if err != nil || st.Mode().Perm() != 0600 {
		t.Fatal(st, err)
	}
	// State may not exist yet; an existing directory alias must not bypass it.
	c.StateDir = filepath.Join(alias, "future-state")
	if resolveDiagnosticGuardPath(c.StateDir) != filepath.Join(actual, "future-state") {
		t.Fatal("missing state path was not canonicalized")
	}
}

func TestLiveMemoryStatusDoesNotRewritePersistedSnapshot(t *testing.T) {
	root := t.TempDir()
	env := Environment{Target: root, Identity: "own-test-group"}
	c := Config{StateDir: filepath.Join(root, "state")}
	status := Status{TimeUTC: time.Now().UTC().Format(time.RFC3339), State: "observe", Mode: "observe", Plan: Plan{Environment: env}}
	path := filepath.Join(c.StateDir, "status.json")
	if err := AtomicJSON(path, status); err != nil {
		t.Fatal(err)
	}
	before, _ := os.ReadFile(path)
	if err := os.WriteFile(filepath.Join(root, "memory.current"), []byte("12345\n"), 0600); err != nil {
		t.Fatal(err)
	}
	v, err := ReadStatus(c, env)
	if err != nil || v.Memory == nil || v.Memory.CurrentBytes == nil || *v.Memory.CurrentBytes != 12345 {
		t.Fatal(v, err)
	}
	after, _ := os.ReadFile(path)
	if string(before) != string(after) {
		t.Fatal("status command wrote dynamic counters to disk")
	}
}
