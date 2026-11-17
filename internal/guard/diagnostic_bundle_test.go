package guard

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestDiagnosticBundlePositiveAllowlistAndSize(t *testing.T) {
	e, f := fixture(t)
	secret := "PRIVATE-password-token-environment-script-data"
	e.Env.Target = "/" + secret
	v := &StatusView{Status: Status{State: "degraded", Mode: "enforce", Error: secret, Plan: Plan{ResourceMode: "manual", Environment: e.Env, Warnings: []string{secret}}, Items: []ItemStatus{{Detail: secret}}}}
	for i := 0; i < 500; i++ {
		v.Actual = append(v.Actual, ItemStatus{Setting: Setting{File: "memory.max", Value: "536870912"}, State: "read", Detail: secret})
	}
	v.Actual = append(v.Actual, ItemStatus{Setting: Setting{File: secret, Value: secret}, State: secret})
	r := BuildDiagnosticBundle(e.Env, v, f)
	b, err := EncodeDiagnosticBundle(r)
	if err != nil || len(b) > DiagnosticMaxBytes || len(r.Controls) != 64 || r.OmittedControls != 437 || strings.Contains(string(b), secret) {
		t.Fatal(len(b), r.OmittedControls, err, string(b))
	}
}

func TestDiagnosticBundleWithoutStatusAndUntrustedControllerText(t *testing.T) {
	e, f := fixture(t)
	r := BuildDiagnosticBundle(e.Env, nil, f)
	if r.StatusAvailable || r.State != "unavailable" {
		t.Fatal(r)
	}
	v := &StatusView{Status: Status{State: "private-secret", Mode: "private-secret"}, Actual: []ItemStatus{{Setting: Setting{File: "cpu.max", Value: "private-secret"}, State: "private-secret"}}}
	b, err := EncodeDiagnosticBundle(BuildDiagnosticBundle(e.Env, v, f))
	if err != nil || strings.Contains(string(b), "private-secret") {
		t.Fatal(string(b), err)
	}
	r.Included = []string{strings.Repeat("x", DiagnosticMaxBytes)}
	if _, err := EncodeDiagnosticBundle(r); err == nil {
		t.Fatal("unbounded output")
	}
}

func TestDiagnosticCannotOverwriteOrCreateStateFiles(t *testing.T) {
	dir := t.TempDir()
	c := Config{StateDir: filepath.Join(dir, "state"), IOProfile: filepath.Join(dir, "profile.json")}
	if err := os.Mkdir(c.StateDir, 0700); err != nil {
		t.Fatal(err)
	}
	bundle := DiagnosticBundle{Schema: "crg-diagnostics-v1"}
	for _, path := range []string{filepath.Join(c.StateDir, "journal.json"), c.IOProfile} {
		if err := WriteDiagnosticFile(path, c, bundle); err == nil {
			t.Fatal("protected path accepted", path)
		}
		if _, err := os.Stat(path); !os.IsNotExist(err) {
			t.Fatal("protected file created", path, err)
		}
	}
	path := filepath.Join(dir, "diagnostic.json")
	// Windows can reject directory fsync after successful creation. Existing
	// data must still be protected there; Linux asserts durability separately.
	if err := WriteDiagnosticFile(path, c, bundle); runtime.GOOS == "linux" && err != nil {
		t.Fatal(err)
	}
	before, err := os.ReadFile(path)
	if err != nil || len(before) == 0 {
		t.Fatal(string(before), err)
	}
	if err := WriteDiagnosticFile(path, c, DiagnosticBundle{Schema: "replacement"}); err == nil {
		t.Fatal("existing destination accepted")
	}
	after, _ := os.ReadFile(path)
	if string(before) != string(after) {
		t.Fatal("existing file changed")
	}
}
